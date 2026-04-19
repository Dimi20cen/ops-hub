---
title: "Project Metadata Spec"
summary: "Expected behavior for lightweight project classification metadata."
read_when:
  - "Adding project metadata fields"
  - "Changing dashboard project scanability"
  - "Changing project classification behavior"
---

# Project Metadata Spec

## Goal

Project metadata should help the operator quickly understand what a project is and how it is exposed, without dragging portfolio-management logic into `ops-hub`.

## Project Surfaces

Projects may define `project_surfaces` as a list of supported surface labels.

Supported values:
- `source`
- `private_deploy`
- `public_demo`
- `public_deploy`

## Behavior Rules

- `project_surfaces` is optional.
- `project_surfaces` should default to an empty list.
- duplicate values should be removed while preserving the first meaningful order from the request.
- values should be normalized from trimmed lowercase strings before validation.
- unknown values should be rejected instead of being stored as free-text tags.

## UI Rules

- the dashboard should show project surfaces in both the project list and the selected project detail view.
- project surfaces are descriptive metadata only.
- project surfaces must not change health-check behavior, action routing, or deployment behavior on their own.
