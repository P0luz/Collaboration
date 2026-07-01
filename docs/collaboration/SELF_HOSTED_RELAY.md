# Self-Hosted Relay

This guide defines the M7 self-hosted relay path for Collaboration. It is a
deployment and verification path, not a separate billing or entitlement system.

## Boundary

- The relay path only moves room state, lock state, event metadata, and audit
  metadata.
- It must not transmit source code contents.
- A self-hosted deployment can use `relay_mode=self_hosted` with the current
  local in-memory relay, or point `relay_url` at a future remote relay service.
- Clients should read `GET /api/collaboration/capabilities/{room}` before
  showing relay, audit export, or dashboard actions.

## Smoke Check

Run this after starting a self-hosted Collaboration API:

```powershell
py -3.10 scripts/collaboration-relay/self_hosted_smoke.py `
  --base-url http://localhost:8080 `
  --room-id self-hosted-relay-smoke `
  --relay-mode self_hosted `
  --relay-url local://memory `
  --json
```

The smoke check verifies:

- room creation with `relay_mode=self_hosted`
- relay connection
- intent declaration and release
- capabilities metadata
- relay event streaming
- audit JSONL export

Expected result:

```json
{
  "status": "pass",
  "summary": {
    "passed": 7,
    "failed": 0
  }
}
```

## Minimal Client Flow

1. `POST /api/collaboration/room/create`
2. `POST /api/collaboration/relay/connect`
3. `GET /api/collaboration/capabilities/{room}`
4. `POST /api/collaboration/intent/declare`
5. `POST /api/collaboration/intent/done`
6. `GET /api/collaboration/relay/events/{room}?since=0`
7. `GET /api/collaboration/audit/{room}/export?fmt=jsonl`

## Operator Notes

- Use `COLLABORATION_URL` and `COLLABORATION_ROOM` with the git hooks when
  pointing a repository at a self-hosted API.
- Keep `COLLABORATION_USER` stable per agent or developer so audit records are
  attributable.
- For production deployment, put authentication and TLS in front of the API.
  M7 reserves the relay path; it does not implement auth, tenancy, or billing.
