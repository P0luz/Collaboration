# Deployment

This guide covers the current M8 deployment path for Collaboration. It is scoped
to a local or self-hosted FastAPI service. SaaS relay, billing, SSO, and tenancy
remain future deployment layers.

## Local Python

```powershell
py -3.10 -m pip install -r requirements.txt
py -3.10 -m uvicorn backend.collaboration.app:app --host 127.0.0.1 --port 8080
```

Health check:

```powershell
Invoke-RestMethod http://localhost:8080/
```

## Docker Compose

```powershell
docker compose up --build
```

The service listens on `http://localhost:8080` and exposes the same API as the
local Python process.

## Release Gate

Run the full local release gate before handing off a build:

```powershell
py -3.10 scripts/collaboration-release/readiness_check.py --with-pytest --json
```

The gate verifies required docs, app health, self-hosted relay smoke, brand
boundary compliance, and the pytest suite.

## Self-Hosted Relay Smoke

After the API is running, verify the relay path:

```powershell
py -3.10 scripts/collaboration-relay/self_hosted_smoke.py `
  --base-url http://localhost:8080 `
  --room-id deployment-smoke `
  --relay-mode self_hosted `
  --relay-url local://memory `
  --json
```

## Hook Environment

For repositories using the Git hooks:

```powershell
$env:COLLABORATION_URL = "http://localhost:8080"
$env:COLLABORATION_ROOM = "Collaboration"
$env:COLLABORATION_USER = "<agent-or-developer-name>"
```

The relay path only carries room state, lock state, event metadata, and audit
metadata. It must not transmit source code contents.
