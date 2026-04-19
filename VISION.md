# VISION.md

`ops-hub` exists to be a small, reliable control plane for operating personal projects.

## Stable Direction

- Own projects and hosts as the source of truth.
- Expose health checks and project actions cleanly.
- Be easy for both humans and coding agents to use.
- Prefer CLI + HTTP + Markdown over heavyweight custom integrations.
- Keep the architecture understandable to a new developer without tribal knowledge.

## What This Repo Is

- a project registry
- a host registry
- a health-check surface
- an action runner interface

## What This Repo Is Not

- a portfolio publishing system
- a dashboard for unrelated personal tools
- an analytics product
- a generic automation junk drawer

## Quality Bar

- Interfaces should be explicit and predictable.
- Dangerous actions should support inspection before execution.
- Docs should explain intent, contracts, and decisions without turning into bureaucracy.
