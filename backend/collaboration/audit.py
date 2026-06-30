"""
Collaboration 审计导出(预留占桩)
=============================

是什么:把 events 记录的审计事件导出/持久化,用于事后追溯与合规。
做什么:【未实现】计划:把内存 events 落盘(JSONL/SQLite),提供按时间/参与者/类型的查询导出。
不做什么:当前阶段 events 仅在内存环形保留最近 500 条;本模块仅占位。
对外暴露:export_events(当前为显式 NotImplemented 占位)。

里程碑:预留。与 events.py 区别:events 是运行时记录,audit 是导出与长期留存。

Collaboration Copyright (c) 2026 P0luz. All rights reserved.
Proprietary. Commercial license required for any use; see LICENSE.
"""

from __future__ import annotations


def export_events(room_id: str, fmt: str = "jsonl") -> str:
    """导出房间审计事件(预留)。当前未实现。"""
    raise NotImplementedError("audit 为预留模块,尚未实现")
