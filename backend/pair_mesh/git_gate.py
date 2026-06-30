"""
Pair Mesh Git 闸门逻辑
=====================

是什么:Git hook 决策的纯逻辑层 —— 把 locks.check_files_locked 的结果翻译成
        "是否阻止 + 给人看的消息 + 给 AI 看的下一步动作"。
做什么:build_hook_feedback(results) 返回 HookFeedback;同一逻辑被 router 的 /hook/check 复用,
        避免"决策逻辑散落在 bash、router 两处"。
不做什么:不发起 HTTP、不读 git;那些由 scripts/pair-mesh-hooks/* 脚本负责。
        watcher 联动、真实 git diff 解析为 M4 范畴,此处仅决策。
对外暴露:build_hook_feedback(results) -> HookFeedback。

Collaboration (Pair Mesh) Copyright (c) 2026 P0luz. All rights reserved.
Proprietary. Commercial license required for any use; see LICENSE.
"""

from __future__ import annotations

from .schema import HookFeedback


def build_hook_feedback(results: list[dict]) -> HookFeedback:
    """根据 check_files_locked 的逐文件结果,构造统一的 Hook 反馈。

    results 每项形如 {"file", "status", ...},status ∈
    {ok, no_lock, locked_by_other, lock_not_active}。
    非 ok 项即为被阻止文件。
    """
    blocked = [r for r in results if r.get("status") != "ok"]
    if not blocked:
        return HookFeedback(blocked=False)

    lines = ["[Pair Mesh] commit 被阻止。", ""]
    holders: list[dict] = []
    for b in blocked:
        status = b.get("status")
        if status == "no_lock":
            lines.append(f"  - {b['file']}: 没有 intent lock")
        elif status == "locked_by_other":
            lines.append(f"  - {b['file']}: 被 {b['holder']} ({b.get('agent', '')}) 锁定")
            lines.append(f"    意图: {b.get('intent', '')}")
            holders.append({"file": b["file"], "owner": b["holder"], "agent": b.get("agent", "")})
        elif status == "lock_not_active":
            lines.append(f"  - {b['file']}: 锁状态为 {b.get('lock_status')},非 active")
    lines += [
        "",
        "请先调用 pair_mesh.wait_for_clear,等待释放后 git pull --rebase 再重新 declare_intent。",
    ]

    blocked_files = [b["file"] for b in blocked]
    return HookFeedback(
        blocked=True,
        reason="staged files not all held by requester",
        blocked_files=blocked_files,
        holders=holders,
        human_message="\n".join(lines),
        pair_mesh_action={
            "tool": "wait_for_clear",
            "args": {"files": blocked_files},
            "then": "git pull --rebase origin <branch>, then re-declare intent",
        },
    )
