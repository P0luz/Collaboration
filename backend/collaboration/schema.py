"""
Collaboration 数据模型
==================

是什么:Collaboration 全部领域数据结构的单一定义处。
做什么:定义房间(Room)、参与者(Participant)、意图锁(IntentLock)、排队项(QueueEntry)、
        事件(Event)、调用审计(AuditRecord)、Hook 反馈(HookFeedback),
        以及两个枚举(LockStatus / EventType)。
不做什么:不含任何业务逻辑(创建/冲突/排队逻辑分别在 rooms/locks/queues 里);不做持久化。
对外暴露:LockStatus, EventType, Room, Participant, IntentLock, QueueEntry, Event,
          AuditRecord, HookFeedback,以及工具函数 now_iso()。

设计说明:时间统一用 UTC aware 的 ISO8601 字符串存储(now_iso),避免 naive/aware 比较出错。

Collaboration Copyright (c) 2026 P0luz. All rights reserved.
Proprietary. Commercial license required for any use; see LICENSE.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


def now_iso() -> str:
    """返回当前 UTC 时间的 aware ISO8601 字符串。所有时间字段统一走这里。"""
    return datetime.now(timezone.utc).isoformat()


class LockStatus(str, Enum):
    """意图锁状态。继承 str 便于 JSON 序列化与直接比较。"""

    ACTIVE = "active"      # 当前持有,正在改
    WAITING = "waiting"    # 因冲突在排队等待
    DONE = "done"          # 已完成释放
    EXPIRED = "expired"    # 空闲超时自动过期
    CONFLICT = "conflict"  # 声明时即冲突(瞬时态,一般转 WAITING)


class EventType(str, Enum):
    """房间内关键操作的事件类型,用于审计日志与 Dashboard。"""

    ROOM_CREATED = "room_created"
    PARTICIPANT_JOINED = "participant_joined"
    PARTICIPANT_LEFT = "participant_left"
    INTENT_DECLARED = "intent_declared"
    INTENT_CONFLICT = "intent_conflict"
    LOCK_EXTENDED = "lock_extended"
    LOCK_RELEASED = "lock_released"
    LOCK_EXPIRED = "lock_expired"
    WAITING_STARTED = "waiting_started"
    WAITING_CLEARED = "waiting_cleared"
    UNCLAIMED_CHANGE = "unclaimed_change"
    HOOK_BLOCKED = "hook_blocked"
    MESSAGE_SENT = "message_sent"


@dataclass
class Room:
    """一个协作房间,对应一个仓库的一次协作会话。"""

    room_id: str
    repo_remote: str = ""
    participants: list[str] = field(default_factory=list)
    max_participants: int = 10
    created_at: str = field(default_factory=now_iso)


@dataclass
class Participant:
    """房间内的一个参与者(人 + 其 AI agent)。"""

    name: str
    agent: str = ""          # "Claude Code", "Codex", etc.
    machine_id: str = ""
    online: bool = True
    branch: str = ""
    head_commit: str = ""
    last_heartbeat: str = field(default_factory=now_iso)


@dataclass
class IntentLock:
    """意图锁:某人声明"我要改这些文件,目的是 X"后产生的占用记录。"""

    lock_id: str = field(default_factory=lambda: f"lock_{uuid.uuid4().hex[:12]}")
    room_id: str = ""
    owner: str = ""
    agent: str = ""
    repo: str = ""
    branch: str = ""
    base_commit: str = ""
    files: list[str] = field(default_factory=list)
    intent: str = ""
    status: LockStatus = LockStatus.ACTIVE
    lock_version: int = 1
    created_at: str = field(default_factory=now_iso)
    last_activity: str = field(default_factory=now_iso)
    idle_timeout_seconds: int = 300  # 5 分钟无活动自动过期


@dataclass
class QueueEntry:
    """文件排队项:某文件被占用时,后来者进入该文件的等待队列。"""

    queue_id: str = field(default_factory=lambda: f"q_{uuid.uuid4().hex[:8]}")
    file: str = ""
    owner: str = ""
    agent: str = ""
    intent: str = ""
    position: int = 0
    lock_id: str = ""  # 关联的 waiting lock
    created_at: str = field(default_factory=now_iso)


@dataclass
class Event:
    """一条审计事件。"""

    event_id: str = field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:10]}")
    room_id: str = ""
    event_type: EventType = EventType.INTENT_DECLARED
    actor: str = ""
    payload: dict = field(default_factory=dict)
    created_at: str = field(default_factory=now_iso)


@dataclass
class AuditRecord:
    """AI/MCP/API 调用日志,用于 prompt 层验收和长期审计。"""

    audit_id: str = field(default_factory=lambda: f"audit_{uuid.uuid4().hex[:10]}")
    room_id: str = ""
    actor: str = ""
    agent: str = ""
    tool: str = ""
    result: str = ""
    files: list[str] = field(default_factory=list)
    payload: dict = field(default_factory=dict)
    created_at: str = field(default_factory=now_iso)


@dataclass
class HookFeedback:
    """Git hook 拦截时的反馈,同时面向人类和 AI。

    collaboration_action 示例:
        {
            "tool": "wait_for_clear",
            "args": {"file": "backend/routes/mcp.py"},
            "then": "git pull --rebase && re-declare intent",
        }
    """

    blocked: bool = False
    reason: str = ""
    blocked_files: list[str] = field(default_factory=list)
    holders: list[dict] = field(default_factory=list)
    human_message: str = ""
    collaboration_action: dict = field(default_factory=dict)
