"""
Collaboration FastAPI Router
========================

是什么:Collaboration 的 HTTP API 层,把 rooms/locks/queues/events/relay 暴露成 REST 端点。
做什么:房间(create/join/leave/heartbeat)、意图锁(declare/done/extend/wait_for_clear)、
        状态查询(status/queue/events)、relay(connect/publish/events/snapshot/disconnect)、
        消息(message)、Git hook 检查(hook/check)。
        每个写操作顺带记录一条 event。
不做什么:不含业务逻辑(全部委托给各 utils 模块);不做鉴权(M2 阶段)。
对外暴露:router(APIRouter,prefix=/api/collaboration)。

序列化说明:dataclass 用 dataclasses.asdict 转 dict;LockStatus/EventType 继承 str,可直接 JSON 化。

Collaboration Copyright (c) 2026 P0luz. All rights reserved.
Proprietary. Commercial license required for any use; see LICENSE.
"""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from . import dashboard, events, git_gate, locks, queues, relay, rooms
from .schema import EventType

router = APIRouter(prefix="/api/collaboration", tags=["collaboration"])


# ── Request Models ──────────────────────────────────────────────

class CreateRoomRequest(BaseModel):
    room_id: str
    repo_remote: str = ""
    max_participants: int = 10


class JoinRoomRequest(BaseModel):
    room_id: str
    name: str
    agent: str = ""
    branch: str = ""


class DeclareIntentRequest(BaseModel):
    room_id: str
    owner: str
    agent: str = ""
    files: list[str]
    intent: str
    repo: str = ""
    branch: str = ""
    base_commit: str = ""


class ReportDoneRequest(BaseModel):
    lock_id: str
    summary: str = ""


class ExtendLockRequest(BaseModel):
    lock_id: str
    additional_files: list[str]
    reason: str = ""


class WaitForClearRequest(BaseModel):
    room_id: str
    files: list[str]


class SendMessageRequest(BaseModel):
    room_id: str
    sender: str
    message: str


class HookCheckRequest(BaseModel):
    room_id: str
    requester: str
    staged_files: list[str]


class RelayConnectRequest(BaseModel):
    room_id: str
    relay_url: str = "local://memory"


class RelayDisconnectRequest(BaseModel):
    room_id: str


class RelayPublishRequest(BaseModel):
    room_id: str
    event: dict


# ── Room ────────────────────────────────────────────────────────

@router.post("/room/create")
def api_create_room(req: CreateRoomRequest) -> dict:
    room = rooms.create_room(req.room_id, req.repo_remote, req.max_participants)
    events.record(room.room_id, EventType.ROOM_CREATED, "system")
    return {"status": "created", "room": asdict(room)}


@router.post("/room/join")
def api_join_room(req: JoinRoomRequest) -> dict:
    result = rooms.join_room(req.room_id, req.name, req.agent, req.branch)
    if result.get("status") == "joined":
        events.record(req.room_id, EventType.PARTICIPANT_JOINED, req.name)
    return result


@router.post("/room/leave")
def api_leave_room(req: JoinRoomRequest) -> dict:
    result = rooms.leave_room(req.room_id, req.name)
    events.record(req.room_id, EventType.PARTICIPANT_LEFT, req.name)
    return result


@router.post("/room/heartbeat")
def api_heartbeat(req: JoinRoomRequest) -> dict:
    return rooms.heartbeat(req.room_id, req.name)


# ── Intent Lock ─────────────────────────────────────────────────

@router.post("/intent/declare")
def api_declare_intent(req: DeclareIntentRequest) -> dict:
    result = locks.declare_intent(
        room_id=req.room_id, owner=req.owner, agent=req.agent,
        files=req.files, intent=req.intent, repo=req.repo,
        branch=req.branch, base_commit=req.base_commit,
    )
    event_type = (
        EventType.INTENT_DECLARED if result["status"] == "clear" else EventType.INTENT_CONFLICT
    )
    events.record(req.room_id, event_type, req.owner, {
        "files": req.files, "intent": req.intent, "result": result["status"],
    })
    return result


@router.post("/intent/done")
def api_report_done(req: ReportDoneRequest) -> dict:
    lock = locks.get_lock(req.lock_id)  # 释放前取房间,因释放后状态变 done 仍可读
    result = locks.report_done(req.lock_id, req.summary)
    if lock:
        events.record(lock.room_id, EventType.LOCK_RELEASED, lock.owner, {
            "lock_id": req.lock_id, "summary": req.summary,
        })
    return result


@router.post("/intent/extend")
def api_extend_lock(req: ExtendLockRequest) -> dict:
    result = locks.extend_lock(req.lock_id, req.additional_files, req.reason)
    lock = locks.get_lock(req.lock_id)
    if lock:
        events.record(lock.room_id, EventType.LOCK_EXTENDED, lock.owner, {
            "lock_id": req.lock_id, "additional_files": req.additional_files,
            "result": result["status"],
        })
    return result


@router.post("/intent/wait_for_clear")
def api_wait_for_clear(req: WaitForClearRequest) -> dict:
    """轮询型查询:返回这些文件当前是否仍被他人占用,供 AI 决定是否继续等待。

    M2 为非阻塞:每个文件返回 cleared / held(含持有者)。AI 侧自行轮询。
    """
    statuses = []
    all_clear = True
    for f in req.files:
        holder = locks.get_file_holder(req.room_id, f)
        if holder is None:
            statuses.append({"file": f, "status": "cleared"})
        else:
            all_clear = False
            statuses.append({
                "file": f, "status": "held",
                "holder": holder.owner, "agent": holder.agent, "intent": holder.intent,
            })
    return {"all_clear": all_clear, "files": statuses}


# ── Status ──────────────────────────────────────────────────────

@router.get("/status/{room_id}")
def api_check_status(room_id: str) -> dict:
    room = rooms.get_room(room_id)
    if not room:
        raise HTTPException(404, "Room not found")
    return {
        "room": asdict(room),
        "participants": [asdict(p) for p in rooms.get_participants(room_id)],
        "active_locks": [asdict(l) for l in locks.get_active_locks(room_id)],
        "waiting_locks": [asdict(l) for l in locks.get_waiting_locks(room_id)],
        "queues": {
            file: [asdict(e) for e in entries]
            for file, entries in queues.get_all_queues(room_id).items()
        },
    }


@router.get("/queue/{room_id}/{file:path}")
def api_get_queue(room_id: str, file: str) -> dict:
    q = queues.get_queue(room_id, file)
    return {"file": file, "queue": [asdict(e) for e in q]}


@router.get("/events/{room_id}")
def api_get_events(room_id: str, limit: int = 50) -> dict:
    return {"events": [asdict(e) for e in events.get_events(room_id, limit)]}


# ── Dashboard ──────────────────────────────────────────────────────────────

@router.get("/dashboard/{room_id}/data")
def api_dashboard_data(room_id: str, limit: int = 25) -> dict:
    data = dashboard.build_dashboard_data(room_id, event_limit=limit)
    if data is None:
        raise HTTPException(404, "Room not found")
    return data


@router.get("/dashboard/{room_id}", response_class=HTMLResponse)
def api_dashboard(room_id: str) -> HTMLResponse:
    data = dashboard.build_dashboard_data(room_id)
    if data is None:
        raise HTTPException(404, "Room not found")
    return HTMLResponse(dashboard.render_dashboard_html(data))


# ── Relay ───────────────────────────────────────────────────────

@router.post("/relay/connect")
def api_relay_connect(req: RelayConnectRequest) -> dict:
    if not rooms.get_room(req.room_id):
        raise HTTPException(404, "Room not found")
    return relay.connect(req.relay_url, req.room_id)


@router.post("/relay/disconnect")
def api_relay_disconnect(req: RelayDisconnectRequest) -> dict:
    return relay.disconnect(req.room_id)


@router.post("/relay/publish")
def api_relay_publish(req: RelayPublishRequest) -> dict:
    if not rooms.get_room(req.room_id):
        raise HTTPException(404, "Room not found")
    return relay.publish(req.room_id, req.event)


@router.get("/relay/events/{room_id}")
def api_relay_events(room_id: str, since: int = 0, limit: int = 100) -> dict:
    if not rooms.get_room(room_id):
        raise HTTPException(404, "Room not found")
    return relay.subscribe(room_id, since=since, limit=limit)


@router.get("/relay/snapshot/{room_id}")
def api_relay_snapshot(room_id: str) -> dict:
    if not rooms.get_room(room_id):
        raise HTTPException(404, "Room not found")
    return relay.snapshot(room_id)


# ── Message ─────────────────────────────────────────────────────

@router.post("/message")
def api_send_message(req: SendMessageRequest) -> dict:
    events.record(req.room_id, EventType.MESSAGE_SENT, req.sender, {"message": req.message})
    return {"status": "sent"}


# ── Hook Check ──────────────────────────────────────────────────

@router.post("/hook/check")
def api_hook_check(req: HookCheckRequest) -> dict:
    """Git pre-commit hook 调用:检查 staged files 是否都被请求者合法持有。

    决策逻辑统一委托给 git_gate.build_hook_feedback(单一真源)。
    """
    results = locks.check_files_locked(req.room_id, req.staged_files, req.requester)
    feedback = git_gate.build_hook_feedback(results)

    if not feedback.blocked:
        return {"blocked": False, "results": results}

    events.record(req.room_id, EventType.HOOK_BLOCKED, req.requester, {
        "blocked_files": feedback.blocked_files,
    })

    return {
        "blocked": True,
        "results": [r for r in results if r["status"] != "ok"],
        "human_message": feedback.human_message,
        "COLLABORATION_ACTION": feedback.collaboration_action,
    }
