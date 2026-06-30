"""
Pair Mesh 包入口
=================

是什么:Pair Mesh 的后端核心包,实现"多人 AI 协作治理层"——通用、独立,可接入任意项目。
做什么:对外暴露 rooms / locks / queues / events 等子模块,以及 FastAPI router。
不做什么:不负责聊天、模型推理、流式、RAG;不绑定任何特定宿主项目。
对外暴露:子模块(schema/rooms/locks/queues/events/router/app)。

Collaboration (Pair Mesh) Copyright (c) 2026 P0luz. All rights reserved.
Proprietary. Commercial license required for any use; see LICENSE.
"""

__all__ = [
    "schema",
    "rooms",
    "locks",
    "queues",
    "events",
    "router",
    "app",
]
