---
title: "Health Checks Spec"
summary: "Expected behavior for public and private project health checks."
read_when:
  - "Changing health check behavior"
  - "Changing host runner integration"
  - "Changing health summary logic"
---

# Health Checks Spec

## Goal

Health checks should tell a consumer whether a project appears reachable from the right execution path.

## Check Types

Each project can define:
- `health_public_url`
- `health_private_url`

## Execution Rules

Public health checks:
- run directly over HTTP from `ops-hub`

Private health checks:
- run through the deployment host runner when the host transport is `http` or `socket`
- fall back to direct HTTP only when there is no actionable host runner

Automatic health checks:
- may run server-side on a fixed interval
- should reuse the same project health-check logic and persisted snapshot fields as manual checks
- should not depend on dashboard page loads or browser polling

## Summary Rules

Project health summary is:
- `healthy` when both checks are healthy
- `unconfigured` when both checks are unconfigured
- `partial` when one check is healthy and the other is not
- `down` otherwise

## Unconfigured Rules

If a health URL is missing:
- the individual check status should be `unconfigured`
- the response should explain that no URL is configured
