# Release Readiness

This page defines the M8 readiness gate for Collaboration. It is the operator
checklist before sharing a build, handing work to another agent, or deploying a
self-hosted API.

## Command

Fast local gate:

```powershell
py -3.10 scripts/collaboration-release/readiness_check.py --json
```

Full gate, including the pytest suite:

```powershell
py -3.10 scripts/collaboration-release/readiness_check.py --with-pytest --json
```

## What It Checks

- required user and operator docs exist
- FastAPI health endpoint returns `{"service": "collaboration", "status": "ok"}`
- self-hosted relay smoke flow passes in-process
- Docker deployment packaging is present
- brand-boundary scan passes
- optional pytest suite passes

## Expected JSON Shape

```json
{
  "status": "pass",
  "summary": {
    "passed": 5,
    "failed": 0
  },
  "checks": [
    {"name": "required_docs", "status": "pass"},
    {"name": "app_health", "status": "pass"},
    {"name": "self_hosted_relay_smoke", "status": "pass"},
    {"name": "deployment_packaging", "status": "pass"},
    {"name": "brand_boundary", "status": "pass"}
  ]
}
```

## Deployment Notes

- Run the full gate before pushing release or handoff commits.
- `Dockerfile`, `docker-compose.yml`, and `.dockerignore` are part of the gate.
- Use the self-hosted relay smoke script against the actual API URL after the
  service is running.
- Keep relay payloads limited to room state, lock state, event metadata, and
  audit metadata.
- Authentication, TLS termination, tenancy, and billing are deployment concerns
  outside this M8 gate.
