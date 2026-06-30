"""
Collaboration 独立应用入口
======================

是什么:把 Collaboration router 挂到一个独立 FastAPI app 上,供本项目单独运行/测试。
做什么:创建 FastAPI 实例,include collaboration router,提供 / 健康检查。
不做什么:不绑定任何宿主项目;不做鉴权/CORS 之外的中间件(M2 阶段)。
对外暴露:app(FastAPI 实例),create_app()。

运行:uvicorn backend.collaboration.app:app --port 8080

设计说明:Collaboration 是独立服务,自带 app 入口;接入其它项目时也可只 include router。

Collaboration Copyright (c) 2026 P0luz. All rights reserved.
Proprietary. Commercial license required for any use; see LICENSE.
"""

from __future__ import annotations

from fastapi import FastAPI

from .router import router as collaboration_router


def create_app() -> FastAPI:
    """构建并返回配置好的 FastAPI 应用。"""
    application = FastAPI(title="Collaboration", version="0.1.0")
    application.include_router(collaboration_router)

    @application.get("/")
    def health() -> dict:
        return {"service": "collaboration", "status": "ok"}

    return application


app = create_app()
