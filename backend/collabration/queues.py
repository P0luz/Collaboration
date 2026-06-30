"""
Collabration 文件排队
==================

是什么:文件级排队。约束 —— 同一文件同一时刻只能有一个 active holder,其余排队等待。
做什么:enqueue 入队、promote_next 在持有者释放后提升队首、查询队列。
不做什么:不直接修改锁状态/文件占用表;提升时通过 locks._activate_lock 回调,
          把"激活锁并占用文件"的语义留在 locks 里(单一来源)。
对外暴露:enqueue, promote_next, get_queue, get_all_queues,以及内部存储 _queues。

Collabration Copyright (c) 2026 P0luz. All rights reserved.
Proprietary. Commercial license required for any use; see LICENSE.
"""

from __future__ import annotations

from typing import Optional

from .schema import QueueEntry

# room_id -> file -> [QueueEntry](按入队顺序,index 0 为队首)
_queues: dict[str, dict[str, list[QueueEntry]]] = {}


def enqueue(room_id: str, file: str, owner: str, agent: str, intent: str, lock_id: str) -> QueueEntry:
    """把一个等待者加入某文件的队尾,position 为其当前排位。"""
    file_queues = _queues.setdefault(room_id, {})
    q = file_queues.setdefault(file, [])
    entry = QueueEntry(
        file=file, owner=owner, agent=agent, intent=intent,
        position=len(q), lock_id=lock_id,
    )
    q.append(entry)
    return entry


def promote_next(room_id: str, file: str) -> Optional[dict]:
    """当前 holder 释放该文件后,提升队首等待者为 active holder。

    队空返回 None;否则弹出队首、重排剩余 position,并回调 locks 激活其锁。
    若队首关联的锁已不存在(异常态),跳过它继续找下一个,避免卡死整条队列。
    """
    from .locks import _activate_lock  # 延迟导入打破 queues<->locks 循环

    q = _queues.get(room_id, {}).get(file)
    if not q:
        return None

    while q:
        entry = q.pop(0)
        for i, e in enumerate(q):  # 重排剩余排位
            e.position = i
        result = _activate_lock(entry.lock_id, file)
        if result is not None:
            return result
        # 锁已消失:这条作废,继续提升下一个
    return None


def get_queue(room_id: str, file: str) -> list[QueueEntry]:
    """取某文件的等待队列(副本不保证,只读用)。"""
    return _queues.get(room_id, {}).get(file, [])


def get_all_queues(room_id: str) -> dict[str, list[QueueEntry]]:
    """取房间内所有文件的队列。"""
    return _queues.get(room_id, {})
