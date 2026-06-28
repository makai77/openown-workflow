# AI Interaction

How to work here. Architecture rules and commands are in `AGENTS.md`.

## MCP tools available this session

- **Context7** — use before implementing any unfamiliar API (Django 6, DRF, pytest-django,
  Vite). Call it with `use context7` or resolve a library with `resolve-library-id` then
  `get-library-docs`. Never paste outdated patterns from memory when current docs are one
  call away.
- **Playwright** — use to verify both happy paths (applicant + reviewer) and the forbidden
  direct-call case (applicant → reviewer endpoint → 403) against `http://localhost:8000`.
  Restrict to localhost and the deployed URL only.

## Before writing code

- Name the Playbook section you're implementing ("Playbook §5.2") in your plan first.
- For anything beyond a trivial edit, state the plan and get agreement before coding.
- Read the relevant `OpenOwnership_Assignment_B_Engineering_Playbook.md` section for
  exact code, and `Engineering_Principles_and_Architecture.md` for the rationale.
  Don't reinvent a pattern the spec already defines. Use Context7 to verify API details
  before writing; don't rely on training-data memory for version-sensitive calls.

## While working

- One working slice at a time (commit plan is Playbook §10.5). Each slice leaves tests green.
- Run the full pre-commit gate from `AGENTS.md` before each commit — don't skip it
  because a change "looks small."
- When debugging: unit tests first → `manage.py check` → `makemigrations --check` → logs.

## Behavior

- Never weaken authorization or delete a test to make something pass. If a test fails,
  the code is wrong — not the test.
- If a request looks out of scope (queues, file handling, notifications, generic workflow
  engines), stop and ask rather than building it.
- Be direct about trade-offs and uncertainty. Flag anything you're guessing at; never
  present a guess as a verified fact.

## When you finish a slice

Report: what changed, what behavior changed, which tests you added/ran, any remaining risk.
Then stop — don't auto-start the next slice without confirmation.
