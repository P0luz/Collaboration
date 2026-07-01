# v5.2 Acceptance

This page is the final v5.2 acceptance map for Collaboration. It connects the
implementation, tests, deployment packaging, product-tier metadata, and readiness
gate into one handoff path.

## Command

```powershell
py -3.10 scripts/collaboration-release/v52_acceptance.py --json
```

Expected summary:

```json
{
  "status": "pass",
  "summary": {
    "passed": 8,
    "failed": 0
  }
}
```

## Milestones

| Milestone | Proof |
|-----------|-------|
| M1 | Clean base, license boundary, and brand-boundary scanner |
| M2 | Local room, intent lock, queue, and API protocol |
| M3 | Relay metadata sync and relay client |
| M4 | Watcher plus Git hook enforcement |
| M5 | AI behavior checks, prompt acceptance, and audit log |
| M6 | Real rehearsal evidence and dashboard review |
| M7 | Commercial metadata, capabilities, product tiers, and relay paths |
| M8 | README, deployment packaging, readiness gate, and handoff docs |

## Release Handoff

Run these before a handoff or release branch:

```powershell
py -3.10 scripts/collaboration-release/v52_acceptance.py --json
py -3.10 scripts/collaboration-release/readiness_check.py --with-pytest --json
```

The acceptance report is static evidence mapping. The readiness check runs the
local smoke paths and optionally the full pytest suite.
