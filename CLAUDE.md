# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

@AGENTS.md

## Project context (all loaded now)

- @context/project-overview.md — the workflow, roles, scope
- @context/coding-standards.md — the engineering rules in detail
- @context/ai-interaction.md — how to work here, commands, pre-commit gate
- @context/current-feature.md — what we're building right now

## Large reference docs — read on demand, NOT imported

- `OpenOwnership_Assignment_B_Engineering_Playbook.md` — full build spec: code, schema, API, tests, deploy
- `Engineering_Principles_and_Architecture.md` — the why behind every rule

Open the relevant section when you need exact code or rationale. Name the section
you're implementing (e.g. "Playbook §5") in your plan before writing code.

## Hard stop (also hook-enforced)

Never assign `application.status = ...` outside `applications/services/workflow.py`.
Use the existing service function instead.
