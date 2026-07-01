# Collaboration

Collaboration is a local-first FastAPI service for coordinating multiple coding
agents in one repository. It provides intent locks, file queues, watcher and Git
hook enforcement, relay metadata sync, audit logs, dashboard data, and readiness
checks for deployment paths.

## Quick Start

```powershell
py -3.10 -m pip install -r requirements.txt
py -3.10 -m uvicorn backend.collaboration.app:app --host 127.0.0.1 --port 8080
```

Health check:

```powershell
Invoke-RestMethod http://localhost:8080/
```

Run tests:

```powershell
py -3.10 -m pytest tests/ -q
```

## Readiness

Before handing the project to another user, agent, or deployment target, run:

```powershell
py -3.10 scripts/collaboration-release/readiness_check.py --with-pytest --json
```

For a self-hosted relay smoke check against a running API:

```powershell
py -3.10 scripts/collaboration-relay/self_hosted_smoke.py `
  --base-url http://localhost:8080 `
  --relay-mode self_hosted `
  --relay-url local://memory `
  --json
```

## Core Docs

- [Git Workflow](docs/collaboration/GIT_WORKFLOW.md)
- [MCP Rules](docs/collaboration/MCP_RULES.md)
- [Self-Hosted Relay](docs/collaboration/SELF_HOSTED_RELAY.md)
- [Release Readiness](docs/collaboration/RELEASE_READINESS.md)
- [License Boundary](docs/collaboration/LICENSE_BOUNDARY.md)

## Boundary

Collaboration moves room state, lock state, event metadata, and audit metadata.
It does not transmit source code through relay paths. Any use requires a
commercial license; see [LICENSE](LICENSE).
