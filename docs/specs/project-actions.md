---
title: "Project Actions Spec"
summary: "Expected behavior for project action execution and dry-run support."
read_when:
  - "Changing action execution logic"
  - "Adding a new project action"
  - "Changing dry-run behavior"
---

# Project Actions Spec

## Goal

Project actions let a consumer operate a project in a predictable way.

## Supported Actions

Supported action names:
- `deploy`
- `start`
- `restart`
- `stop`
- `logs`

Each action maps to one configured command field on the project record.

## Resolution Rules

When an action is requested:
- resolve the command field from the action name
- fail if the command field is empty
- resolve the deployment host if one is configured
- use a host runner when the host transport is `http` or `socket`
- run locally when the host transport is `none` or no deployment host is configured

## Dry-Run Rules

When `dry_run` is `true`:
- resolve the same command and execution mode as a real run
- do not execute the command
- do not call a host runner
- return the normal action response shape with `dry_run: true`

## Failure Rules

An action should fail when:
- the action name is unsupported
- the project does not exist
- the configured command is empty
- the deployment host slug is unknown

## Output Rules

Action responses should always include:
- action metadata
- execution mode
- command
- cwd
- stdout
- stderr
- timestamp

This applies to both HTTP and CLI consumers.
