# Product Tiers

This page documents the v5.2 commercial packaging metadata for Collaboration.
It is product-positioning and capability metadata only. Billing, accounts,
entitlements, SSO, tenancy, and payment enforcement are not implemented in this
repository.

## Catalog API

```powershell
Invoke-RestMethod http://localhost:8080/api/collaboration/plans
```

The endpoint returns:

- `billing_implemented=false`
- `relay_transmits_source_code=false`
- `plans[]` with plan defaults, included capabilities, and reserved future
  capabilities

## Plans

| Plan | Participants | Relay | Audit Retention | Packaging |
|------|--------------|-------|-----------------|-----------|
| Free | 2 | local | 30 days | Local validation, intent locks, watcher and hook enforcement |
| Team | 10 | saas | 90 days | Managed relay metadata path, shared dashboard, basic audit events |
| Pro | 10 | saas | 180 days | AI behavior checks, audit review, risk-rule templates |
| Enterprise | 50 | private | 365 days | Private relay, audit export, custom retention |

## Reserved Enterprise Capabilities

- SSO or directory integration
- custom hook policy
- compliance reports

## Product Boundary

Collaboration sells confidence and evidence for multi-agent coding governance:
every agent declares intent, conflicts queue instead of overwriting work, Git
hooks enforce the protocol, and audit metadata can be exported. The relay path
must carry metadata only and must not carry source code contents.
