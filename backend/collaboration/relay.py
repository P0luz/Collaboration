"""
Collaboration Relay 通信
======================

是什么:跨进程/跨机器同步的 relay 抽象层,当前提供 local relay 事件流与状态快照。
做什么:connect 建立房间 relay 连接;publish 把事件元数据写入递增事件流;
        subscribe 按 seq 拉取新事件;snapshot 导出 participants / locks / queues 当前状态。
不做什么:不传输源码内容,不做 WebSocket/HTTP 网络服务,不做持久化。远程 relay 是 M3 后续替换点。
对外暴露:connect, disconnect, publish, subscribe, snapshot,以及测试可重置的内部存储。

里程碑:M3 的 local-first 最小底座。

Collaboration Copyright (c) 2026 P0luz. All rights reserved.
Proprietary. Commercial license required for any use; see LICENSE.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .schema import now_iso


@dataclass
class RelayConnection:
    room_id: str
    relay_url: str
    mode: str
    connected_at: str


_connections: dict[str, RelayConnection] = {}
_event_streams: dict[str, list[dict]] = {}
_next_seq: dict[str, int] = {}


def _mode_from_url(relay_url: str) -> str:
    if relay_url.startswith("local://"):
        return "local"
    if relay_url.startswith(("http://", "https://", "ws://", "wss://")):
        return "remote"
    return "unknown"


def connect(relay_url: str, room_id: str) -> dict:
    """连接 relay。当前 local 模式在内存中维护事件流,远程 URL 只记录连接元数据。"""
    connection = RelayConnection(
        room_id=room_id,
        relay_url=relay_url,
        mode=_mode_from_url(relay_url),
        connected_at=now_iso(),
    )
    _connections[room_id] = connection
    _event_streams.setdefault(room_id, [])
    _next_seq.setdefault(room_id, 1)
    return {"status": "connected", **asdict(connection)}


def disconnect(room_id: str) -> dict:
    """断开 relay 连接。事件流保留,便于测试和后续重连读取。"""
    _connections.pop(room_id, None)
    return {"status": "disconnected", "room_id": room_id}


def connection_status(room_id: str) -> dict:
    """返回 relay 连接元数据,供 Dashboard 等只读状态面板使用。"""
    connection = _connections.get(room_id)
    last_seq = _next_seq.get(room_id, 1) - 1
    if connection is None:
        return {
            "connected": False,
            "room_id": room_id,
            "relay_url": "",
            "mode": "none",
            "connected_at": "",
            "last_seq": last_seq,
        }
    return {"connected": True, **asdict(connection), "last_seq": last_seq}


def publish(room_id: str, event: dict) -> dict:
    """发布一条事件元数据。未 connect 的房间显式跳过,避免误以为已同步。"""
    if room_id not in _connections:
        return {"status": "skipped", "reason": "relay_not_connected", "room_id": room_id}

    seq = _next_seq.get(room_id, 1)
    envelope = {
        "seq": seq,
        "room_id": room_id,
        "event": dict(event),
    }
    _event_streams.setdefault(room_id, []).append(envelope)
    _next_seq[room_id] = seq + 1
    return {"status": "published", "room_id": room_id, "seq": seq}


def subscribe(room_id: str, since: int = 0, limit: int = 100) -> dict:
    """拉取 seq 大于 since 的事件。返回顺序为从旧到新,便于客户端顺序应用。"""
    stream = _event_streams.get(room_id, [])
    events = [item for item in stream if item["seq"] > since][:limit]
    last_seq = stream[-1]["seq"] if stream else since
    return {"room_id": room_id, "events": events, "last_seq": last_seq}


def snapshot(room_id: str) -> dict:
    """导出房间当前状态快照,供 relay 客户端重连后恢复状态。"""
    from . import locks, queues, rooms

    room = rooms.get_room(room_id)
    return {
        "room": asdict(room) if room else None,
        "participants": [asdict(p) for p in rooms.get_participants(room_id)],
        "active_locks": [asdict(l) for l in locks.get_active_locks(room_id)],
        "waiting_locks": [asdict(l) for l in locks.get_waiting_locks(room_id)],
        "queues": {
            file: [asdict(entry) for entry in entries]
            for file, entries in queues.get_all_queues(room_id).items()
        },
    }
