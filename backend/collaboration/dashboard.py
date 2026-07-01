"""
Collaboration Dashboard helpers
===============================

What it is: a tiny read-only projection layer for the M3 dashboard.
What it does: combines room, participant, lock, queue, event, and relay state
              into one payload and renders a minimal HTML view.
What it does not do: mutate collaboration state, authenticate users, or replace
                     the future Savoir-Fair frontend integration.
Exports: build_dashboard_data, render_dashboard_html.

Collaboration Copyright (c) 2026 P0luz. All rights reserved.
Proprietary. Commercial license required for any use; see LICENSE.
"""

from __future__ import annotations

from dataclasses import asdict
from html import escape
from typing import Optional

from . import events, locks, queues, relay, rooms


def build_dashboard_data(room_id: str, event_limit: int = 25) -> Optional[dict]:
    """Build a read-only dashboard payload for one room."""
    room = rooms.get_room(room_id)
    if room is None:
        return None

    participants = [asdict(p) for p in rooms.get_participants(room_id)]
    active_locks = [asdict(lock) for lock in locks.get_active_locks(room_id)]
    waiting_locks = [asdict(lock) for lock in locks.get_waiting_locks(room_id)]
    queue_state = {
        file: [asdict(entry) for entry in entries]
        for file, entries in queues.get_all_queues(room_id).items()
    }
    recent_events = [asdict(event) for event in events.get_events(room_id, event_limit)]

    return {
        "room": asdict(room),
        "relay": relay.connection_status(room_id),
        "summary": {
            "participants": len(participants),
            "active_locks": len(active_locks),
            "waiting_locks": len(waiting_locks),
            "queued_files": len(queue_state),
            "events": len(recent_events),
        },
        "participants": participants,
        "active_locks": active_locks,
        "waiting_locks": waiting_locks,
        "queues": queue_state,
        "events": recent_events,
    }


def render_dashboard_html(data: dict) -> str:
    """Render the dashboard payload as a small self-contained HTML page."""
    room = data["room"]
    relay_state = data["relay"]
    summary = data["summary"]

    participants = "".join(
        _row([
            participant["name"],
            participant.get("agent", ""),
            participant.get("branch", ""),
            "online" if participant.get("online") else "offline",
        ])
        for participant in data["participants"]
    ) or _empty_row(4)

    active_locks = "".join(
        _row([
            lock["owner"],
            lock.get("agent", ""),
            ", ".join(lock.get("files", [])),
            lock.get("intent", ""),
        ])
        for lock in data["active_locks"]
    ) or _empty_row(4)

    waiting_locks = "".join(
        _row([
            lock["owner"],
            lock.get("agent", ""),
            ", ".join(lock.get("files", [])),
            lock.get("intent", ""),
        ])
        for lock in data["waiting_locks"]
    ) or _empty_row(4)

    queue_rows = "".join(
        _row([
            file,
            entry["owner"],
            entry.get("agent", ""),
            str(entry.get("position", "")),
            entry.get("intent", ""),
        ])
        for file, entries in data["queues"].items()
        for entry in entries
    ) or _empty_row(5)

    event_rows = "".join(
        _row([
            event.get("created_at", ""),
            event.get("actor", ""),
            event.get("event_type", ""),
            _format_payload(event.get("payload", {})),
        ])
        for event in data["events"]
    ) or _empty_row(4)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Collaboration Dashboard - Room {escape(room["room_id"])}</title>
  <style>
    :root {{
      color-scheme: light;
      font-family: Inter, Segoe UI, Arial, sans-serif;
      background: #f6f8fa;
      color: #1f2328;
    }}
    body {{
      margin: 0;
      padding: 24px;
    }}
    main {{
      max-width: 1180px;
      margin: 0 auto;
    }}
    header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
      gap: 16px;
      margin-bottom: 20px;
    }}
    h1 {{
      margin: 0;
      font-size: 28px;
      font-weight: 700;
    }}
    h2 {{
      margin: 28px 0 10px;
      font-size: 18px;
    }}
    .meta {{
      color: #59636e;
      font-size: 14px;
    }}
    .summary {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 10px;
      margin-bottom: 18px;
    }}
    .metric {{
      border: 1px solid #d0d7de;
      border-radius: 8px;
      background: #ffffff;
      padding: 12px;
    }}
    .metric strong {{
      display: block;
      font-size: 24px;
      line-height: 1.1;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: #ffffff;
      border: 1px solid #d0d7de;
      border-radius: 8px;
      overflow: hidden;
      table-layout: fixed;
    }}
    th, td {{
      padding: 10px 12px;
      border-bottom: 1px solid #d8dee4;
      text-align: left;
      vertical-align: top;
      overflow-wrap: anywhere;
      font-size: 14px;
    }}
    th {{
      background: #f0f3f6;
      font-weight: 600;
    }}
    tr:last-child td {{
      border-bottom: 0;
    }}
  </style>
</head>
<body>
<main>
  <header>
    <div>
      <h1>Collaboration Dashboard</h1>
      <div class="meta">Room {escape(room["room_id"])} | Relay: {escape(relay_state["mode"])} | Repo: {escape(room.get("repo_remote", ""))}</div>
    </div>
    <div class="meta">connected: {str(relay_state["connected"]).lower()} | last seq: {escape(str(relay_state["last_seq"]))}</div>
  </header>

  <section class="summary">
    {_metric("Participants", summary["participants"])}
    {_metric("Active Locks", summary["active_locks"])}
    {_metric("Waiting Locks", summary["waiting_locks"])}
    {_metric("Queued Files", summary["queued_files"])}
    {_metric("Events", summary["events"])}
  </section>

  <h2>Participants</h2>
  {_table(["Name", "Agent", "Branch", "Status"], participants)}

  <h2>Active Locks</h2>
  {_table(["Owner", "Agent", "Files", "Intent"], active_locks)}

  <h2>Waiting Locks</h2>
  {_table(["Owner", "Agent", "Files", "Intent"], waiting_locks)}

  <h2>Queues</h2>
  {_table(["File", "Owner", "Agent", "Position", "Intent"], queue_rows)}

  <h2>Timeline</h2>
  {_table(["Created", "Actor", "Type", "Payload"], event_rows)}
</main>
</body>
</html>"""


def _metric(label: str, value: int) -> str:
    return f'<div class="metric"><strong>{escape(str(value))}</strong>{escape(label)}</div>'


def _table(headers: list[str], rows: str) -> str:
    head = "".join(f"<th>{escape(header)}</th>" for header in headers)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>"


def _row(values: list[str]) -> str:
    cells = "".join(f"<td>{escape(str(value))}</td>" for value in values)
    return f"<tr>{cells}</tr>"


def _empty_row(columns: int) -> str:
    return f'<tr><td colspan="{columns}">None</td></tr>'


def _format_payload(payload: dict) -> str:
    return ", ".join(f"{key}={value}" for key, value in payload.items())
