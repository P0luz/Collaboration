"""
Collaboration M6 rehearsal evidence helpers
===========================================

What it is: a read-only projection that turns dashboard/audit/hook state into
            M6 rehearsal report evidence suggestions.
What it does: builds a compact evidence bundle and keeps raw dashboard data.
What it does not do: mutate collaboration state, run agents, or mark reports pass/fail.
Exports: build_rehearsal_evidence.

Collaboration Copyright (c) 2026 P0luz. All rights reserved.
Proprietary. Commercial license required for any use; see LICENSE.
"""

from __future__ import annotations

from typing import Optional

from . import dashboard


def build_rehearsal_evidence(room_id: str, limit: int = 50) -> Optional[dict]:
    """Build a read-only M6 evidence bundle for one room."""
    data = dashboard.build_dashboard_data(room_id, event_limit=limit)
    if data is None:
        return None

    audit_records = list(reversed(data.get("audit", [])))  # oldest -> newest for summaries
    clear_declare = _find_call(audit_records, "declare_intent", "clear")
    conflict_declare = _find_call(audit_records, "declare_intent", "conflict")
    wait_call = _find_call(audit_records, "wait_for_clear")
    done_call = _find_call(audit_records, "report_done", "done")
    hook_block = _find_call(audit_records, "hook_check", "blocked")

    suggested_evidence = {
        "room_setup": {
            "repo_remote": data["room"].get("repo_remote", ""),
            "branch": _branch_summary(data.get("participants", [])),
            "dashboard_url": f"/api/collaboration/dashboard/{room_id}",
        },
        "declare_conflict_wait": {
            "declare_result": _call_summary(clear_declare),
            "conflict_result": _call_summary(conflict_declare),
            "wait_result": _call_summary(wait_call),
            "audit_excerpt": _audit_excerpt([clear_declare, conflict_declare, wait_call]),
        },
        "report_done_handoff": {
            "report_done_result": _call_summary(done_call),
            "promoted_owner": _promoted_owner(data, done_call),
            "pull_rebase_excerpt": "manual: record git pull --rebase before continuing",
        },
        "hook_blocked_recovery": {
            "hook_result": _call_summary(hook_block),
            "collaboration_action": _action_tool(hook_block),
            "recovery_result": "manual: record recovery action and retry result",
        },
    }

    return {
        "room_id": room_id,
        "summary": data["summary"],
        "suggested_evidence": suggested_evidence,
        "manual_required": [
            "collaborative_task_completed",
            "retrospective",
        ],
        "raw": {
            "events": data.get("events", []),
            "audit": data.get("audit", []),
            "hook_feedback": data.get("hook_feedback", []),
        },
    }


def _find_call(records: list[dict], tool: str, result: str | None = None) -> dict | None:
    for record in records:
        if record.get("tool") != tool:
            continue
        if result is not None and record.get("result") != result:
            continue
        return record
    return None


def _call_summary(record: dict | None) -> str:
    if not record:
        return ""
    actor = record.get("actor", "") or "unknown"
    result = record.get("result", "")
    files = ", ".join(record.get("files", []))
    if files:
        return f"{actor}: {result} ({files})"
    return f"{actor}: {result}"


def _audit_excerpt(records: list[dict | None]) -> str:
    parts = []
    for record in records:
        if not record:
            continue
        parts.append(
            f"{record.get('tool', '')}:{record.get('result', '')}:"
            f"{record.get('actor', '')}"
        )
    return " | ".join(parts)


def _branch_summary(participants: list[dict]) -> str:
    branches = sorted({
        participant.get("branch", "")
        for participant in participants
        if participant.get("branch", "")
    })
    return ", ".join(branches)


def _promoted_owner(data: dict, done_call: dict | None) -> str:
    done_actor = (done_call or {}).get("actor", "")
    for lock in data.get("active_locks", []):
        owner = lock.get("owner", "")
        if owner and owner != done_actor:
            return owner
    return ""


def _action_tool(record: dict | None) -> str:
    if not record:
        return ""
    action = record.get("payload", {}).get("action", {})
    if isinstance(action, dict):
        return action.get("tool", "")
    return ""
