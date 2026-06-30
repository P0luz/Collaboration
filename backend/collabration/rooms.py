"""
Collabration 房间管理
==================

是什么:房间与参与者的生命周期管理。
做什么:创建房间、加入/离开房间、心跳保活、查询房间与参与者。
不做什么:不管意图锁/排队(见 locks/queues);不持久化(内存存储,M2 阶段)。
对外暴露:create_room, join_room, leave_room, heartbeat, get_room, get_participants,
          get_all_rooms,以及内部存储 _rooms / _participants(测试用 reset)。

存储说明:内存字典,进程级单例。后续可替换 SQLite/Redis,接口保持不变。

Collabration Copyright (c) 2026 P0luz. All rights reserved.
Proprietary. Commercial license required for any use; see LICENSE.
"""

from __future__ import annotations

from typing import Optional

from .schema import Participant, Room, now_iso

# 内存存储(M2 阶段;后续可换 SQLite/Redis)
_rooms: dict[str, Room] = {}
_participants: dict[str, dict[str, Participant]] = {}  # room_id -> {name: Participant}


def create_room(room_id: str, repo_remote: str = "", max_participants: int = 10) -> Room:
    """创建房间。若已存在同名房间则覆盖其元数据并清空参与者表(显式幂等)。"""
    room = Room(room_id=room_id, repo_remote=repo_remote, max_participants=max_participants)
    _rooms[room_id] = room
    _participants[room_id] = {}
    return room


def join_room(room_id: str, name: str, agent: str = "", branch: str = "") -> dict:
    """参与者加入房间。房间不存在或已满时返回 error 状态(不抛异常,便于 API 直接回传)。"""
    if room_id not in _rooms:
        return {"status": "error", "message": f"Room {room_id} not found"}

    room = _rooms[room_id]
    # 已在房间内的重复 join 视为更新,不计入满员判断
    if name not in room.participants and len(room.participants) >= room.max_participants:
        return {"status": "error", "message": "Room is full"}

    if name not in room.participants:
        room.participants.append(name)

    _participants.setdefault(room_id, {})[name] = Participant(
        name=name, agent=agent, branch=branch
    )

    return {"status": "joined", "room_id": room_id, "participants": list(room.participants)}


def leave_room(room_id: str, name: str) -> dict:
    """参与者离开房间。对不存在的房间/参与者保持幂等,返回 left。"""
    if room_id in _rooms and name in _rooms[room_id].participants:
        _rooms[room_id].participants.remove(name)
    _participants.get(room_id, {}).pop(name, None)
    return {"status": "left"}


def heartbeat(room_id: str, name: str) -> dict:
    """刷新参与者心跳与在线状态。不在房间内时返回 error。"""
    bucket = _participants.get(room_id)
    if bucket and name in bucket:
        bucket[name].last_heartbeat = now_iso()
        bucket[name].online = True
        return {"status": "ok"}
    return {"status": "error", "message": "Not in room"}


def get_room(room_id: str) -> Optional[Room]:
    """按 id 取房间,不存在返回 None。"""
    return _rooms.get(room_id)


def get_participants(room_id: str) -> list[Participant]:
    """取房间内所有参与者对象,房间不存在返回空列表。"""
    return list(_participants.get(room_id, {}).values())


def get_all_rooms() -> list[Room]:
    """取所有房间。"""
    return list(_rooms.values())
