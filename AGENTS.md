# AGENTS.md

## Purpose

This repo is `ops-hub`: a small, agent-friendly control plane for projects and hosts.

## Working Rules

- Keep the scope tight: projects, hosts, health checks, and actions.
- Do not add portfolio publishing, analytics, dashboards, or unrelated utilities unless explicitly requested.
- Prefer boring, explicit interfaces over clever abstractions.
- Keep route files thin. Business logic belongs in `app/domain/`.
- Keep storage details in `app/storage/`.
- Preserve stable machine-readable response shapes once they are documented in `docs/contracts.md`.
- When adding docs under `docs/`, include frontmatter with:

```md
---
title: ""
summary: ""
read_when:
  -
---
```

## Documentation Map

- Start with `README.md` for repo orientation.
- Read `VISION.md` for stable direction.
- Read `docs/contracts.md` before changing external behavior.
- Read `docs/specs/` before changing feature behavior.
- Read `docs/decisions/` before undoing an intentional design choice.

## Coding Preferences

- Optimize for clarity over brevity.
- Use clear names that make sense to a new developer.
- Keep new interfaces agent-friendly: predictable JSON, stable fields, and explicit errors.
- Avoid mixing computed fields with stored fields unless the boundary is documented.
