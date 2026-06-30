"""
Collaboration Relay 通信(M3 占桩)
==============================

是什么:跨机/跨进程的消息中继层,让不在同一台机器的参与者共享房间状态。
做什么:【M3 未实现】计划:把本地内存状态变更广播到 relay 服务,并接收他人变更;
        替代 M2 的单进程内存模型,支撑真正的远程多人协作。
不做什么:当前阶段(M2)所有状态都在单进程内存,无跨机通信。仅占位。
对外暴露:connect / publish / subscribe(当前为显式 NotImplemented 占位)。

里程碑:M3。

Collaboration Copyright (c) 2026 P0luz. All rights reserved.
Proprietary. Commercial license required for any use; see LICENSE.
"""

from __future__ import annotations


def connect(relay_url: str, room_id: str) -> None:
    """连接 relay 服务(M3)。当前未实现。"""
    raise NotImplementedError("relay 属于 M3,尚未实现")


def publish(room_id: str, event: dict) -> None:
    """向 relay 广播事件(M3)。当前未实现。"""
    raise NotImplementedError("relay 属于 M3,尚未实现")
