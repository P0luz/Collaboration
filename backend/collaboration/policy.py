"""
Collaboration 策略规则(预留占桩)
=============================

是什么:协作策略的可配置规则层(谁能改哪些目录、超时时长、最大并发锁等)。
做什么:【未实现】计划:把当前硬编码的规则(idle_timeout=300、max_participants=10 等)
        集中到可配置策略,按房间/仓库定制。
不做什么:当前阶段规则散落在 schema 默认值里;本模块仅占位,标记未来收敛方向。
对外暴露:get_policy / set_policy(当前为显式 NotImplemented 占位)。

里程碑:预留(M3+)。

Collaboration Copyright (c) 2026 P0luz. All rights reserved.
Proprietary. Commercial license required for any use; see LICENSE.
"""

from __future__ import annotations


def get_policy(room_id: str) -> dict:
    """取房间策略(预留)。当前未实现。"""
    raise NotImplementedError("policy 为预留模块,尚未实现")


def set_policy(room_id: str, policy: dict) -> None:
    """设置房间策略(预留)。当前未实现。"""
    raise NotImplementedError("policy 为预留模块,尚未实现")
