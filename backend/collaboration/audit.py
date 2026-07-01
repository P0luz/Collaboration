"""
Collaboration 调用审计
===================

是什么:记录 AI/MCP/API 对 Collaboration 协作工具的调用结果,用于 prompt 层验收与审计。
做什么:内存记录调用日志,按房间倒序查询,并导出 JSONL。
不做什么:不做持久化、不做鉴权、不保存源码内容。
对外暴露:record_call, get_call_logs, export_calls, export_events。

与 events.py 区别:events 是房间时间线,audit 是“agent 调了什么工具、结果如何”的证据链。

Collaboration Copyright (c) 2026 P0luz. All rights reserved.
Proprietary. Commercial license required for any use; see LICENSE.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from .schema import AuditRecord


_call_logs: dict[str, list[AuditRecord]] = {}
_MAX_CALL_LOGS = 1000


def record_call(
    room_id: str,
    actor: str,
    tool: str,
    result: str,
    *,
    agent: str = "",
    files: list[str] | None = None,
    payload: dict[str, Any] | None = None,
) -> AuditRecord:
    """记录一次协作工具调用;每个房间只保留最近 _MAX_CALL_LOGS 条。"""
    record = AuditRecord(
        room_id=room_id,
        actor=actor,
        agent=agent,
        tool=tool,
        result=result,
        files=list(files or []),
        payload=payload or {},
    )
    bucket = _call_logs.setdefault(room_id, [])
    bucket.append(record)
    if len(bucket) > _MAX_CALL_LOGS:
        del bucket[: len(bucket) - _MAX_CALL_LOGS]
    return record


def get_call_logs(room_id: str, limit: int = 50) -> list[AuditRecord]:
    """取最近调用日志,最新在前。"""
    return list(reversed(_call_logs.get(room_id, [])[-limit:]))


def export_calls(room_id: str, fmt: str = "jsonl") -> str:
    """导出调用审计日志。当前支持 JSONL,按时间正序输出。"""
    if fmt != "jsonl":
        raise ValueError("only jsonl audit export is supported")
    return "\n".join(
        json.dumps(asdict(record), ensure_ascii=False)
        for record in _call_logs.get(room_id, [])[-_MAX_CALL_LOGS:]
    )


def export_events(room_id: str, fmt: str = "jsonl") -> str:
    """兼容旧入口:导出调用审计日志。"""
    return export_calls(room_id, fmt=fmt)
