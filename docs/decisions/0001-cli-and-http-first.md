---
title: "ADR 0001: CLI and HTTP First"
summary: "Records the decision to make ops-hub agent-friendly through simple interfaces instead of heavyweight integration layers."
read_when:
  - "Questioning why there is a CLI"
  - "Considering MCP or custom agent integrations"
  - "Adding new external interfaces"
---

# ADR 0001: CLI and HTTP First

## Status

Accepted

## Context

`ops-hub` is meant to be useful for both humans and coding agents.

Agent-friendly systems work best when they expose:
- clear commands
- stable JSON
- explicit docs
- simple transport layers

It is easy to overcomplicate this by jumping straight into custom agent protocols and special integration layers.

## Decision

`ops-hub` will prefer:
- HTTP for service access
- CLI for direct terminal use
- Markdown docs for instructions and contracts

It will not require MCP or another agent-specific integration to be useful.

## Consequences

Positive:
- easier for humans to inspect and use
- easier for coding agents to discover and automate
- lower complexity

Negative:
- some richer agent workflows may need an additional layer later
- interface discipline matters more because the basics are the product
