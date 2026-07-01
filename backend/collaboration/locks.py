"""
Collaboration 意图锁核心
====================

是什么:Collaboration 的核心 —— Intent Lock 的声明、释放、扩展、过期检查。
做什么:
  - declare_intent:AI 改代码前声明意图;无冲突则建 active 锁占用文件,有冲突则建 waiting 锁并入队。
  - report_done:完成后释放锁,并提升各文件队列里的下一位。
  - extend_lock:把已持有的 active 锁扩展到更多文件。
  - check_files_locked:Git hook 用,检查 staged 文件是否都被请求者本人合法持有。
  - _expire_stale_locks:空闲超时自动过期。
不做什么:不管房间生命周期(rooms);队列存储在 queues,本模块只通过 _activate_lock 回调被 queues 调用。
对外暴露:declare_intent, report_done, extend_lock, touch_lock, get_lock, get_active_locks,
          get_waiting_locks,
          get_file_holder, check_files_locked, _activate_lock(供 queues 提升时调用),
          以及内部存储 _locks / _file_holders。

并发说明:M2 单进程内存模型,不加锁。多进程/分布式由后续 M3 relay 层处理。

Collaboration Copyright (c) 2026 P0luz. All rights reserved.
Proprietary. Commercial license required for any use; see LICENSE.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from .schema import IntentLock, LockStatus, now_iso

# 内存存储
_locks: dict[str, IntentLock] = {}                       # lock_id -> IntentLock
_file_holders: dict[str, dict[str, str]] = {}            # room_id -> {file: lock_id}


def _hold_files(room_id: str, lock_id: str, files: list[str]) -> None:
    """让某锁占用一批文件(写入 _file_holders)。占用语义集中在此,避免散落。"""
    holders = _file_holders.setdefault(room_id, {})
    for f in files:
        holders[f] = lock_id


def _release_files(room_id: str, lock_id: str, files: list[str]) -> None:
    """释放某锁占用的文件;仅释放确实由该锁持有的文件(避免误删他人占用)。"""
    holders = _file_holders.get(room_id, {})
    for f in files:
        if holders.get(f) == lock_id:
            del holders[f]


def _activate_lock(lock_id: str, file: str) -> Optional[dict]:
    """把一个 waiting 锁就该文件转为 active 并占用。queues.promote_next 提升时回调。

    返回提升结果 dict(供事件/反馈),锁不存在则返回 None。
    占用文件的语义统一走这里,queues 不直接改 _file_holders。
    """
    lock = _locks.get(lock_id)
    if lock is None:
        return None
    lock.status = LockStatus.ACTIVE
    lock.last_activity = now_iso()
    _hold_files(lock.room_id, lock_id, [file])
    return {
        "owner": lock.owner,
        "agent": lock.agent,
        "file": file,
        "lock_id": lock_id,
        "message": f"{file} is now clear. Please git pull --rebase, then re-declare intent.",
    }


def declare_intent(
    room_id: str,
    owner: str,
    agent: str,
    files: list[str],
    intent: str,
    repo: str = "",
    branch: str = "",
    base_commit: str = "",
) -> dict:
    """AI 改代码前必须调用,声明要改哪些文件及目的。

    返回:
      - {"status": "clear", "lock_id", "files", "warnings"}:无冲突,已持有。
      - {"status": "conflict", "lock_id", "conflicts", "message"}:有冲突,已建 waiting 锁并入队。
    """
    from .queues import enqueue  # 延迟导入,打破 locks<->queues 循环依赖

    _expire_stale_locks(room_id)

    conflicts: list[dict] = []
    for f in files:
        holder_lock_id = _file_holders.get(room_id, {}).get(f)
        if not holder_lock_id or holder_lock_id not in _locks:
            continue
        holder = _locks[holder_lock_id]
        # 只有"别人持有且仍在 active"才算冲突;自己的锁或非 active 不算
        if holder.owner != owner and holder.status == LockStatus.ACTIVE:
            conflicts.append({
                "file": f,
                "holder": {
                    "owner": holder.owner,
                    "agent": holder.agent,
                    "intent": holder.intent,
                    "lock_id": holder.lock_id,
                },
            })

    if conflicts:
        lock = IntentLock(
            room_id=room_id, owner=owner, agent=agent, repo=repo, branch=branch,
            base_commit=base_commit, files=list(files), intent=intent,
            status=LockStatus.WAITING,
        )
        _locks[lock.lock_id] = lock
        for c in conflicts:
            enqueue(room_id, c["file"], owner, agent, intent, lock.lock_id)
        return {
            "status": "conflict",
            "lock_id": lock.lock_id,
            "conflicts": conflicts,
            "message": "Files locked by others. You are in the queue. Call wait_for_clear to wait.",
        }

    # 无冲突:建 active 锁并占用全部文件
    lock = IntentLock(
        room_id=room_id, owner=owner, agent=agent, repo=repo, branch=branch,
        base_commit=base_commit, files=list(files), intent=intent,
        status=LockStatus.ACTIVE,
    )
    _locks[lock.lock_id] = lock
    _hold_files(room_id, lock.lock_id, files)
    return {"status": "clear", "lock_id": lock.lock_id, "files": list(files), "warnings": []}


def report_done(lock_id: str, summary: str = "") -> dict:
    """AI 改完后释放锁,并提升各文件队列里的下一位。"""
    from .queues import promote_next  # 延迟导入打破循环

    lock = _locks.get(lock_id)
    if lock is None:
        return {"status": "error", "message": "Lock not found"}

    lock.status = LockStatus.DONE
    _release_files(lock.room_id, lock_id, lock.files)

    promoted: list[dict] = []
    for f in lock.files:
        nxt = promote_next(lock.room_id, f)
        if nxt:
            promoted.append(nxt)

    return {"status": "done", "lock_id": lock_id, "summary": summary, "promoted": promoted}


def extend_lock(lock_id: str, additional_files: list[str], reason: str = "") -> dict:
    """把一个 active 锁扩展到更多文件。冲突文件不并入,返回 partial_conflict。"""
    lock = _locks.get(lock_id)
    if lock is None:
        return {"status": "error", "message": "Lock not found"}
    if lock.status != LockStatus.ACTIVE:
        return {"status": "error", "message": "Lock is not active"}

    extended: list[str] = []
    conflicts: list[dict] = []
    holders = _file_holders.get(lock.room_id, {})

    for f in additional_files:
        existing = holders.get(f)
        if existing and existing != lock_id and existing in _locks:
            holder = _locks[existing]
            if holder.status == LockStatus.ACTIVE:
                conflicts.append({
                    "file": f,
                    "holder": {
                        "owner": holder.owner,
                        "agent": holder.agent,
                        "intent": holder.intent,
                    },
                })
                continue
        if f not in lock.files:
            lock.files.append(f)
        extended.append(f)
        _hold_files(lock.room_id, lock_id, [f])

    lock.lock_version += 1
    lock.last_activity = now_iso()

    if conflicts:
        return {
            "status": "partial_conflict",
            "lock_id": lock_id,
            "extended_files": extended,
            "conflict_files": conflicts,
        }
    return {"status": "extended", "lock_id": lock_id, "files": list(lock.files)}


def touch_lock(lock_id: str) -> None:
    """刷新锁的最后活动时间(watcher 检测到文件变动时调用)。"""
    lock = _locks.get(lock_id)
    if lock is not None:
        lock.last_activity = now_iso()


def get_lock(lock_id: str) -> Optional[IntentLock]:
    """按 id 取锁。"""
    return _locks.get(lock_id)


def get_active_locks(room_id: str) -> list[IntentLock]:
    """取房间内所有 active 锁。"""
    return [l for l in _locks.values() if l.room_id == room_id and l.status == LockStatus.ACTIVE]


def get_waiting_locks(room_id: str) -> list[IntentLock]:
    """取房间内所有 waiting 锁,供状态查询和 push 闸门判断未解决冲突。"""
    return [l for l in _locks.values() if l.room_id == room_id and l.status == LockStatus.WAITING]


def get_file_holder(room_id: str, file: str) -> Optional[IntentLock]:
    """取某文件当前的持有锁,无则 None。"""
    lock_id = _file_holders.get(room_id, {}).get(file)
    if lock_id and lock_id in _locks:
        return _locks[lock_id]
    return None


def check_files_locked(room_id: str, files: list[str], requester: str) -> list[dict]:
    """Git hook 用:检查 staged 文件是否都被 requester 本人合法(active)持有。

    每个文件返回一条状态:no_lock / locked_by_other / lock_not_active / ok。
    """
    results: list[dict] = []
    for f in files:
        holder_lock_id = _file_holders.get(room_id, {}).get(f)
        if not holder_lock_id or holder_lock_id not in _locks:
            results.append({"file": f, "status": "no_lock"})
            continue
        lock = _locks[holder_lock_id]
        if lock.owner != requester:
            results.append({
                "file": f,
                "status": "locked_by_other",
                "holder": lock.owner,
                "agent": lock.agent,
                "intent": lock.intent,
            })
        elif lock.status != LockStatus.ACTIVE:
            results.append({"file": f, "status": "lock_not_active", "lock_status": lock.status.value})
        else:
            results.append({"file": f, "status": "ok"})
    return results


def _expire_stale_locks(room_id: str) -> None:
    """过期清理:active 锁空闲超过 idle_timeout_seconds 则自动转 expired 并释放文件。"""
    now = datetime.now(timezone.utc)
    for lock in list(_locks.values()):
        if lock.room_id != room_id or lock.status != LockStatus.ACTIVE:
            continue
        try:
            last = datetime.fromisoformat(lock.last_activity)
        except (ValueError, TypeError):
            # last_activity 异常时,显式跳过而非静默吞:刷新为现在,留待下次判断
            lock.last_activity = now_iso()
            continue
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        if (now - last).total_seconds() > lock.idle_timeout_seconds:
            lock.status = LockStatus.EXPIRED
            _release_files(room_id, lock.lock_id, lock.files)
