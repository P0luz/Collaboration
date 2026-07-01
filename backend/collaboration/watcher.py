"""
Collaboration 文件监听
====================

是什么:文件系统监听器,检测 Git 工作区真实改动并联动 intent lock / event timeline。
做什么:扫描 repo 中的 changed files;改动命中 active 锁时刷新 lock.last_activity;
        改动无 active 锁时记录 UNCLAIMED_CHANGE 事件;可启动轻量后台轮询。
不做什么:不自动回滚文件,不解析语义冲突,不替代 Git hook 的最终门禁。
对外暴露:scan_once, start_watcher, stop_watcher,以及测试可重置的 _watchers / _reported_unclaimed。

里程碑:M4 的最小可用 watcher。当前采用 git status 轮询,后续可替换为 watchdog。

Collaboration Copyright (c) 2026 P0luz. All rights reserved.
Proprietary. Commercial license required for any use; see LICENSE.
"""

from __future__ import annotations

import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from . import events, locks
from .schema import EventType, LockStatus


@dataclass
class _WatcherHandle:
    repo_path: str
    interval_seconds: float
    stop_event: threading.Event
    thread: threading.Thread


_watchers: dict[str, _WatcherHandle] = {}
_reported_unclaimed: dict[tuple[str, str], set[str]] = {}


def _normalize_file(path: str) -> str:
    """把 Git 输出路径统一成 API 使用的正斜杠相对路径。"""
    return path.strip().replace("\\", "/")


def _parse_status_line(line: str) -> Optional[str]:
    """解析 `git status --porcelain` 单行,返回变更后的相对文件路径。"""
    if len(line) < 4:
        return None
    path = line[3:]
    if " -> " in path:
        path = path.split(" -> ", 1)[1]
    path = _normalize_file(path.strip('"'))
    return path or None


def _list_changed_files(repo_path: str) -> list[str]:
    """列出 repo 中已跟踪/未跟踪的变更文件。"""
    repo = Path(repo_path)
    result = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain", "--untracked-files=all"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    files: list[str] = []
    for line in result.stdout.splitlines():
        parsed = _parse_status_line(line)
        if parsed and parsed not in files:
            files.append(parsed)
    return files


def scan_once(room_id: str, repo_path: str, actor: str = "watcher") -> dict:
    """扫描一次 Git 工作区,刷新合法锁活动并记录未声明改动。"""
    changed_files = _list_changed_files(repo_path)
    repo_key = str(Path(repo_path).resolve())
    reported = _reported_unclaimed.setdefault((room_id, repo_key), set())
    changed_set = set(changed_files)
    reported.intersection_update(changed_set)

    touched_locks: list[dict] = []
    unclaimed_changes: list[str] = []

    for file in changed_files:
        holder = locks.get_file_holder(room_id, file)
        if holder is not None and holder.status == LockStatus.ACTIVE:
            if actor != "watcher" and holder.owner != actor:
                if file in reported:
                    continue
                events.record(room_id, EventType.UNCLAIMED_CHANGE, actor, {
                    "file": file,
                    "reason": "locked_by_other",
                    "holder": holder.owner,
                    "agent": holder.agent,
                    "intent": holder.intent,
                })
                reported.add(file)
                unclaimed_changes.append(file)
                continue
            locks.touch_lock(holder.lock_id)
            touched = {"file": file, "lock_id": holder.lock_id}
            if touched not in touched_locks:
                touched_locks.append(touched)
            reported.discard(file)
            continue

        if file in reported:
            continue
        events.record(room_id, EventType.UNCLAIMED_CHANGE, actor, {
            "file": file,
            "reason": "no_active_lock",
        })
        reported.add(file)
        unclaimed_changes.append(file)

    return {
        "status": "scanned",
        "room_id": room_id,
        "repo_path": repo_key,
        "changed_files": changed_files,
        "touched_locks": touched_locks,
        "unclaimed_changes": unclaimed_changes,
    }


def _watch_loop(room_id: str, repo_path: str, interval_seconds: float, stop_event: threading.Event) -> None:
    """后台轮询循环。异常被记录为事件,避免线程悄悄退出后没有痕迹。"""
    while not stop_event.is_set():
        try:
            scan_once(room_id, repo_path)
        except Exception as exc:  # pragma: no cover - 防御式兜底,单测覆盖 scan_once 主路径
            events.record(room_id, EventType.UNCLAIMED_CHANGE, "watcher", {
                "file": "",
                "reason": "watcher_error",
                "error": str(exc),
            })
        stop_event.wait(interval_seconds)


def start_watcher(room_id: str, repo_path: str, interval_seconds: float = 1.0) -> dict:
    """启动房间 watcher。重复启动会先停掉旧 watcher,再启动新线程。"""
    if interval_seconds <= 0:
        return {"status": "error", "message": "interval_seconds must be positive"}

    stop_watcher(room_id)
    stop_event = threading.Event()
    thread = threading.Thread(
        target=_watch_loop,
        args=(room_id, repo_path, interval_seconds, stop_event),
        name=f"collaboration-watcher-{room_id}",
        daemon=True,
    )
    _watchers[room_id] = _WatcherHandle(
        repo_path=str(Path(repo_path).resolve()),
        interval_seconds=interval_seconds,
        stop_event=stop_event,
        thread=thread,
    )
    thread.start()
    return {"status": "started", "room_id": room_id, "repo_path": _watchers[room_id].repo_path}


def stop_watcher(room_id: str) -> dict:
    """停止房间 watcher。不存在时保持幂等。"""
    handle = _watchers.pop(room_id, None)
    if handle is None:
        return {"status": "stopped", "room_id": room_id}
    handle.stop_event.set()
    handle.thread.join(timeout=max(handle.interval_seconds * 2, 0.5))
    return {"status": "stopped", "room_id": room_id}
