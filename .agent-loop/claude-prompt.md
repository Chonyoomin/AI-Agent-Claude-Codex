# Claude Code Task

## Phase
Phase 10AG - Desktop Codex Conversation Surface Initial Slice

## Objective
Implement the first bounded desktop-side Codex interaction surface so the
operator can compose an in-app Codex request, inspect Codex response mirrors,
and route approved Codex-owned actions through the shipped adapter/artifact
model instead of separate chat windows.

## Context
`Phase 10AG` is now the active mainline slice. `Phase 10AF` defined the
desktop Codex conversation contract: closed intent vocabulary, refusal
vocabulary, canonical routing rules, advisory-vs-canonical mirrors, and
approval/audit boundaries. This slice is the first runtime that materializes
that contract into the shipped desktop app.

The implementation must stay bounded. It should expose a real desktop-side
interaction surface, but it must not widen into an autonomous chat runtime, a
hidden queue/cache, a second orchestrator, or direct desktop-side canonical
writes outside the shipped adapter/artifact model.

Work against the actual repo state. Do not rely on prior chat context.

## Required work
- implement the first bounded desktop Codex conversation surface in the shipped
  desktop app
- allow the operator to compose in-app Codex requests aligned to the Phase 10AF
  closed request vocabulary
- surface Codex responses in a bounded way as advisory/canonical mirrors
  consistent with the Phase 10AF contract
- route approved Codex-owned actions through the shipped adapter/artifact model
  instead of direct hidden desktop mutation
- preserve refusal behavior, approval gates, overlap-safe boundaries, audit
  expectations, and canonical-artifact-first behavior
- add or update focused tests for the new desktop surface
- update `README.md` if the current implementation focus or shipped operator
  behavior changes

## Constraints
- Follow `CLAUDE.md`.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not invent a hidden UI-only request queue, reply cache, session state
  plane, or background chat driver.
- Do not implement a networked Codex server, WebSocket, SSE stream, or MCP-side
  "codex chat" endpoint.
- Do not bypass the shipped ownership model, evidence review flow, approval
  gates, or adapter boundaries.
- Prefer small, testable, reversible changes.

## Important guardrails
- The desktop Codex surface is a routing layer over the shipped artifacts and
  adapters, not a separate autonomous control plane.
- Claude-owned follow-up must still become prompt/fix-prompt handoff, not a
  hidden direct mutation path.
- Orchestrator-owned targets must still refuse fail-closed.
- Keep the surface operator-usable, but bounded.

## Likely files
- `scripts/agent_loop.py`
- `tests/test_desktop_app.py`
- `tests/test_documentation_consistency.py`
- `README.md`
- `docs/desktop-codex-conversation-contract.md`

## Required output
After implementation, write `.agent-loop/claude-summary.md` using the required
Claude Implementation Summary format and include the validation you ran.
