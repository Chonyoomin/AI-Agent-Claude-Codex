# Claude Code Task

## Phase
Phase 10T - MCP Read-Only Assistance In Desktop App

## Objective
Implement Phase 10T for the agent loop. This slice should add the first
user-selectable MCP read-only assistance surfaces in the desktop app so
operators can enable approved context-gathering tools from the desktop app
without mutating canonical artifacts or bypassing evidence review.

## Context
Implement the MCP Read-Only Assistance In Desktop App slice for the agent
loop. This slice should add the first user-selectable MCP read-only assistance
surfaces so operators can enable approved context-gathering tools from the
desktop app without mutating canonical artifacts or bypassing evidence review.

## Required work
- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`,
  and `.agent-loop/loop-state.json` identify Phase 10 / 10T as active
- `.agent-loop/phase-plan.md` records Phase 10S as closed history and contains
  a `## Phase 10T - MCP Read-Only Assistance In Desktop App` section with
  concrete objective, done criteria, and exclusions
- add the first user-selectable MCP read-only assistance surfaces so operators
  can enable approved context-gathering tools from the desktop app without
  mutating canonical artifacts or bypassing evidence review
- follow the shipped Phase 10O MCP integration contract and Phase 10S MCP
  server selection UX contract, preserving the read-only versus deferred-
  mutating boundary and the canonical-artifact-first model
- preserve approval gating, evidence review, external-workspace boundaries,
  desktop/UI boundaries, and the Phase 10I library-callable cap instead of
  introducing hidden automation or a parallel state store
- add focused validation proving the first MCP read-only assistance surface is
  bounded, auditable, and does not widen into mutation-capable MCP actions,
  RAG runtime, packaging, or controlled-concurrency work
- `README.md` reflects that Phase 10T is active and that MCP read-only
  assistance in the desktop app is now the implementation focus

## Constraints
- Follow `CLAUDE.md`.
- Stay within the current task scope.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not rewrite unrelated files.
- Do not delete files unless explicitly instructed.
- Prefer small, testable, reversible changes.
- Add or update tests when behavior changes.

Out of scope for this phase (from `TASK.md` and `phase-plan.md`):
- no mutation-capable MCP actions, no MCP-driven writes to canonical
  artifacts, and no bypass of the shipped CLI/library/runtime boundaries
- no RAG, GitHub, policy-pack, packaging, system-tray, or controlled-
  concurrency runtime work
- no automatic next-phase activation behavior that bypasses or rewrites the
  shipped Phase 4 planner / activation separation
- no claim that fully autonomous PRD-to-product execution is already solved
- no rewrite of current shipped behavior just to make future MCP or autonomy
  work easier
- no contract rewrites in `AGENTS.md` or `CLAUDE.md`
- no change to the Phase 2A Evidence Collection Contract
- no change to the Phase 3A Orchestrator Contract body
- no change to the Phase 4A Planning Contract body
- no change to `scripts/run_checks.sh`
- no Git automation

## Required output
After implementation, write `.agent-loop/claude-summary.md` using the required
Claude Implementation Summary format.
