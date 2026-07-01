"""商业化策略预留测试:plan 字段、人数上限、relay/audit 默认值。"""

import pytest

from backend.collaboration import policy


def test_free_plan_policy_defaults_to_two_participants():
    resolved = policy.resolve_room_policy(plan="free")

    assert resolved == {
        "plan": "free",
        "max_participants": 2,
        "relay_mode": "local",
        "audit_retention_days": 30,
        "policy_rules_enabled": True,
    }


def test_team_plan_policy_allows_ten_participants_and_saas_relay():
    resolved = policy.resolve_room_policy(plan="team", relay_mode="saas")

    assert resolved["plan"] == "team"
    assert resolved["max_participants"] == 10
    assert resolved["relay_mode"] == "saas"


def test_explicit_max_participants_overrides_plan_limit():
    resolved = policy.resolve_room_policy(plan="free", max_participants=4)

    assert resolved["plan"] == "free"
    assert resolved["max_participants"] == 4


def test_unknown_plan_is_rejected():
    with pytest.raises(ValueError, match="unknown plan"):
        policy.resolve_room_policy(plan="hobby")
