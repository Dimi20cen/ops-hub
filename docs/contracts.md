---
title: "External Contracts"
summary: "Stable behaviors that CLI and API consumers of ops-hub can rely on."
read_when:
  - "Changing API response shapes"
  - "Changing CLI output semantics"
  - "Adding or removing supported actions"
---

# External Contracts

This document defines what consumers of `ops-hub` can rely on.

## Supported Project Actions

`ops-hub` supports exactly these action names:
- `deploy`
- `start`
- `restart`
- `stop`
- `logs`

## Action Request Contract

HTTP:
- `POST /projects/{slug}/actions`
- request body includes:
  - `action`
  - `dry_run`

CLI:
- `python ops_hub.py projects action <project_slug> <action_name>`
- optional flags:
  - `--dry-run`
  - `--json`

## Action Response Contract

Project action responses return these fields:
- `ok`
- `action`
- `project_slug`
- `host_slug`
- `execution_mode`
- `dry_run`
- `command`
- `cwd`
- `exit_code`
- `stdout`
- `stderr`
- `ran_at`

## Execution Mode Contract

`execution_mode` is one of:
- `local`
- `runner_http`
- `runner_socket`

## Dry-Run Contract

When `dry_run` is `true`:
- no command should be executed
- no host runner command should be triggered
- the response should still describe what would happen

## CLI Contract

The CLI supports:
- human-readable output by default
- machine-readable output with `--json`

`--json` output should remain valid JSON and should not include extra log lines.

## Scope Contract

`ops-hub` owns:
- hosts
- projects
- health checks
- project actions

It does not own:
- portfolio publishing
- analytics
- unrelated local tools

## Cached Health Contract

`GET /projects` returns the latest persisted health snapshot fields:
- `last_health_summary`
- `last_health_checked_at`
- `last_health_result`

It does not promise a live health check on every read.

Live project health runs only when:
- `POST /projects/{slug}/health-check` is called
- the automatic health scheduler performs a sweep

## Host Response Contract

`GET /hosts` returns stored host fields plus:
- `runner_health`

`runner_health` is computed response data and is not part of the persisted host record.
