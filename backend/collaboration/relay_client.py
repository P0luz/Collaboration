"""
Collaboration Relay HTTP 客户端
=============================

是什么:面向 agent / 其它进程的 relay HTTP 客户端薄封装。
做什么:调用 relay connect/publish/events/snapshot/disconnect 端点,并为每个 room 维护 last_seq 游标。
不做什么:不保存源码,不做后台线程,不替代 relay 服务端;网络重试/鉴权属于后续 M3+。
对外暴露:RelayClient, RelayClientState。

Collaboration Copyright (c) 2026 P0luz. All rights reserved.
Proprietary. Commercial license required for any use; see LICENSE.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import httpx


@dataclass
class RelayClientState:
    """单个 room 的客户端同步状态。"""

    room_id: str
    last_seq: int = 0
    snapshot: Optional[dict] = None
    events: list[dict] = field(default_factory=list)


class RelayClient:
    """HTTP relay 客户端。测试可注入 FastAPI TestClient,生产默认使用 httpx.Client。"""

    def __init__(self, base_url: str = "http://localhost:8080", http_client: Optional[Any] = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.http = http_client or httpx.Client(base_url=self.base_url)
        self._owns_http = http_client is None
        self._states: dict[str, RelayClientState] = {}

    def connect(self, room_id: str, relay_url: str = "local://memory") -> dict:
        """连接 room relay,并初始化本地游标状态。"""
        result = self._post("/api/collaboration/relay/connect", {
            "room_id": room_id,
            "relay_url": relay_url,
        })
        self._states.setdefault(room_id, RelayClientState(room_id=room_id))
        return result

    def disconnect(self, room_id: str) -> dict:
        """断开 relay。保留 last_seq,便于后续重连继续增量拉取。"""
        return self._post("/api/collaboration/relay/disconnect", {"room_id": room_id})

    def sync(self, room_id: str) -> RelayClientState:
        """先拉快照,再按 last_seq 拉事件,用于客户端重连后的状态恢复。"""
        state = self._state(room_id)
        state.snapshot = self._get(f"/api/collaboration/relay/snapshot/{room_id}")
        self.poll_events(room_id)
        return self._copy_state(state)

    def publish(self, room_id: str, event: dict) -> dict:
        """向 relay 注入一条外部事件元数据。"""
        return self._post("/api/collaboration/relay/publish", {
            "room_id": room_id,
            "event": event,
        })

    def poll_events(self, room_id: str, limit: int = 100) -> RelayClientState:
        """从本地 last_seq 之后增量拉取事件,并更新游标。"""
        state = self._state(room_id)
        payload = self._get(
            f"/api/collaboration/relay/events/{room_id}",
            params={"since": state.last_seq, "limit": limit},
        )
        state.events = payload["events"]
        state.last_seq = payload["last_seq"]
        return self._copy_state(state)

    def last_seq(self, room_id: str) -> int:
        """返回 room 当前客户端游标。"""
        return self._state(room_id).last_seq

    def close(self) -> None:
        """关闭自持有的 httpx.Client。注入的客户端由调用方管理。"""
        if self._owns_http:
            self.http.close()

    def _state(self, room_id: str) -> RelayClientState:
        return self._states.setdefault(room_id, RelayClientState(room_id=room_id))

    @staticmethod
    def _copy_state(state: RelayClientState) -> RelayClientState:
        return RelayClientState(
            room_id=state.room_id,
            last_seq=state.last_seq,
            snapshot=state.snapshot,
            events=list(state.events),
        )

    def _get(self, path: str, params: Optional[dict] = None) -> dict:
        response = self.http.get(path, params=params)
        return self._json(response)

    def _post(self, path: str, payload: dict) -> dict:
        response = self.http.post(path, json=payload)
        return self._json(response)

    @staticmethod
    def _json(response: Any) -> dict:
        if response.status_code >= 400:
            raise RuntimeError(f"Relay HTTP error {response.status_code}: {response.text}")
        return response.json()
