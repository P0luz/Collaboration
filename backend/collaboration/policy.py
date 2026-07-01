"""
Collaboration policy rules
==========================

What it is: the configurable policy layer for plan defaults and room limits.
What it does: resolves room policy fields such as plan, participant cap,
              relay mode, audit retention, and policy-rule enablement.
What it does not do: billing, authentication, entitlement checks, or persistence.
Exports: resolve_room_policy, get_plan_policy, get_policy, set_policy.

M7 note: this is commercial-readiness metadata only. It reserves policy fields
without implementing payment or account management.

Collaboration Copyright (c) 2026 P0luz. All rights reserved.
Proprietary. Commercial license required for any use; see LICENSE.
"""

from __future__ import annotations

from typing import Optional


PLAN_POLICIES: dict[str, dict] = {
    "free": {
        "max_participants": 2,
        "relay_mode": "local",
        "audit_retention_days": 30,
        "policy_rules_enabled": True,
    },
    "team": {
        "max_participants": 10,
        "relay_mode": "saas",
        "audit_retention_days": 90,
        "policy_rules_enabled": True,
    },
    "pro": {
        "max_participants": 10,
        "relay_mode": "saas",
        "audit_retention_days": 180,
        "policy_rules_enabled": True,
    },
    "enterprise": {
        "max_participants": 50,
        "relay_mode": "private",
        "audit_retention_days": 365,
        "policy_rules_enabled": True,
    },
}


PLAN_CATALOG: dict[str, dict] = {
    "free": {
        "label": "Free",
        "positioning": "Local validation for two participants",
        "included": [
            "local or self-hosted relay",
            "basic intent locks",
            "watcher and hook enforcement",
        ],
        "reserved": [],
    },
    "team": {
        "label": "Team",
        "positioning": "Small team coordination with managed relay metadata",
        "included": [
            "managed relay metadata path",
            "shared dashboard",
            "basic audit events",
        ],
        "reserved": ["billing integration"],
    },
    "pro": {
        "label": "Pro",
        "positioning": "Governance evidence and longer audit retention",
        "included": [
            "AI behavior checks",
            "audit log review",
            "risk-rule templates",
        ],
        "reserved": ["weekly conflict reports"],
    },
    "enterprise": {
        "label": "Enterprise",
        "positioning": "Private relay and compliance-oriented governance",
        "included": [
            "private relay",
            "audit export",
            "custom retention",
        ],
        "reserved": [
            "SSO or directory integration",
            "custom hook policy",
            "compliance reports",
        ],
    },
}


def get_plan_policy(plan: str = "free") -> dict:
    """Return a copy of the policy defaults for a known plan."""
    normalized = (plan or "free").lower()
    if normalized not in PLAN_POLICIES:
        raise ValueError(f"unknown plan: {plan}")
    return dict(PLAN_POLICIES[normalized])


def list_plan_catalog() -> dict:
    """Return v5.2 commercial packaging metadata without billing behavior."""
    plans = []
    for plan, defaults in PLAN_POLICIES.items():
        packaging = PLAN_CATALOG[plan]
        plans.append({
            "plan": plan,
            "label": packaging["label"],
            "positioning": packaging["positioning"],
            "max_participants": defaults["max_participants"],
            "relay_mode": defaults["relay_mode"],
            "audit_retention_days": defaults["audit_retention_days"],
            "policy_rules_enabled": defaults["policy_rules_enabled"],
            "included": list(packaging["included"]),
            "reserved": list(packaging["reserved"]),
        })
    return {
        "billing_implemented": False,
        "relay_transmits_source_code": False,
        "plans": plans,
    }


def resolve_room_policy(
    plan: str = "free",
    max_participants: Optional[int] = None,
    relay_mode: str | None = None,
    audit_retention_days: int | None = None,
    policy_rules_enabled: bool | None = None,
) -> dict:
    """Resolve plan defaults plus explicit room-level overrides."""
    normalized = (plan or "free").lower()
    resolved = get_plan_policy(normalized)
    if max_participants is not None:
        if max_participants <= 0:
            raise ValueError("max_participants must be positive")
        resolved["max_participants"] = max_participants
    if relay_mode:
        resolved["relay_mode"] = relay_mode
    if audit_retention_days is not None:
        if audit_retention_days <= 0:
            raise ValueError("audit_retention_days must be positive")
        resolved["audit_retention_days"] = audit_retention_days
    if policy_rules_enabled is not None:
        resolved["policy_rules_enabled"] = policy_rules_enabled
    return {"plan": normalized, **resolved}


def get_policy(room_id: str) -> dict:
    """Return the active policy metadata for a room."""
    from . import rooms

    room = rooms.get_room(room_id)
    if room is None:
        return resolve_room_policy()
    return {
        "plan": room.plan,
        "max_participants": room.max_participants,
        "relay_mode": room.relay_mode,
        "audit_retention_days": room.audit_retention_days,
        "policy_rules_enabled": room.policy_rules_enabled,
    }


def set_policy(room_id: str, policy: dict) -> None:
    """Update policy metadata on an existing in-memory room."""
    from . import rooms

    room = rooms.get_room(room_id)
    if room is None:
        raise ValueError(f"room not found: {room_id}")
    resolved = resolve_room_policy(
        plan=policy.get("plan", room.plan),
        max_participants=policy.get("max_participants", room.max_participants),
        relay_mode=policy.get("relay_mode", room.relay_mode),
        audit_retention_days=policy.get("audit_retention_days", room.audit_retention_days),
        policy_rules_enabled=policy.get("policy_rules_enabled", room.policy_rules_enabled),
    )
    room.plan = resolved["plan"]
    room.max_participants = resolved["max_participants"]
    room.relay_mode = resolved["relay_mode"]
    room.audit_retention_days = resolved["audit_retention_days"]
    room.policy_rules_enabled = resolved["policy_rules_enabled"]
