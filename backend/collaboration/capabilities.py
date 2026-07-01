"""
Room capability metadata
========================

What it is: a read-only projection of room policy, relay status, and available
            Collaboration features.
What it does: lets clients and agents discover which M7 readiness surfaces are
              available for a room without mutating room state.
What it does not do: billing, authorization, persistence, or entitlement checks.
Exports: build_capabilities.

Collaboration Copyright (c) 2026 P0luz. All rights reserved.
Proprietary. Commercial license required for any use; see LICENSE.
"""

from __future__ import annotations

from . import policy, relay, rooms


RELAY_SUPPORT = {
    "local": True,
    "self_hosted": True,
    "saas": True,
    "private": True,
}


def build_capabilities(room_id: str) -> dict | None:
    """Return room capability metadata, or None when the room is missing."""
    room = rooms.get_room(room_id)
    if room is None:
        return None

    room_policy = policy.get_policy(room_id)
    relay_status = relay.connection_status(room_id)

    return {
        "room_id": room_id,
        "policy": room_policy,
        "relay": {
            "mode": room_policy["relay_mode"],
            "connected": relay_status["connected"],
            "connection_mode": relay_status["mode"],
            "last_seq": relay_status["last_seq"],
            "supports": dict(RELAY_SUPPORT),
        },
        "features": {
            "intent_locks": True,
            "watcher": True,
            "relay": True,
            "audit_log": True,
            "audit_export": True,
            "dashboard": True,
            "rehearsal_evidence": True,
            "brand_boundary_check": True,
            "policy_rules": room_policy["policy_rules_enabled"],
        },
    }
