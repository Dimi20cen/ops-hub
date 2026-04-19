---
title: "Hosts Spec"
summary: "Expected behavior for host records, runner validation, and runner health visibility."
read_when:
  - "Changing host validation rules"
  - "Changing host response shapes"
  - "Changing runner health visibility"
---

# Hosts Spec

## Goal

Hosts describe where projects live and how `ops-hub` can reach host-side runners.

## Validation Rules

When a host is created or updated:
- `slug` is required
- `title` is required
- `transport` must be `none`, `http`, or `socket`
- `http` hosts require both `runner_url` and `token_env_var`
- `socket` hosts require `runner_socket_path`
- transport-specific runner fields should be cleared when they do not apply

## Response Rules

`GET /hosts` returns:
- stored host fields from the host registry
- a computed `runner_health` object

`runner_health` is observed at read time and is not persisted into the host store.

## Runner Health Rules

Runner health visibility:
- uses `GET /health` on the configured host runner
- should work over both `http` and Unix `socket` transports
- should report `unconfigured` when the host has no runner
- should report `down` when the runner is unreachable or returns an error
- should report `healthy` when the runner responds successfully
