"""
Collaboration 事件记录
==================

是什么:房间内关键操作的审计日志(声明/冲突/释放/扩展/消息等)。
做什么:record 追加事件,get_events 倒序取最近 N 条。每房间环形保留最近 _MAX_EVENTS 条。
不做什么:不做持久化(内存);不做查询过滤(只按房间+条数)。
对外暴露:record, get_events,以及内部存储 _events、上限 _MAX_EVENTS。

Collaboration Copyright (c) 2026 P0luz. All rights reserved.
Proprietary. Commercial license required for any use; see LICENSE.
"""

from __future__ import annotations

from typing import Optional

from .schema import Event, EventType

_events: dict[str, list[Event]] = {}  # room_id -> [Event](按时间顺序)
_MAX_EVENTS = 500


def record(room_id: str, event_type: EventType, actor: str, payload: Optional[dict] = None) -> Event:
    """追加一条事件;超过上限时丢弃最旧的,只保留最近 _MAX_EVENTS 条。"""
    event = Event(room_id=room_id, event_type=event_type, actor=actor, payload=payload or {})
    bucket = _events.setdefault(room_id, [])
    bucket.append(event)
    if len(bucket) > _MAX_EVENTS:
        del bucket[: len(bucket) - _MAX_EVENTS]
    _publish_to_relay(event)
    return event


def get_events(room_id: str, limit: int = 50) -> list[Event]:
    """取房间最近 limit 条事件,最新在前(倒序)。"""
    return list(reversed(_events.get(room_id, [])[-limit:]))


def _publish_to_relay(event: Event) -> None:
    """把事件元数据广播给 relay。relay 未连接时会显式跳过。"""
    from . import relay

    relay.publish(event.room_id, {
        "event_id": event.event_id,
        "type": event.event_type.value,
        "actor": event.actor,
        "payload": event.payload,
        "created_at": event.created_at,
    })
