# Claude Code Task

## Phase
Phase 10AH - Orchestration Graph And Phase-State Visualization Contract

## Objective
Define the contract for a bounded desktop orchestration-visualization surface so
the app can show live loop state as a graph or icon-based flow without
inventing UI-only truth or bypassing canonical artifact ownership.

## Context
`Phase 10AH` is now the active mainline slice. The prior slice, `Phase 10AG`,
shipped the first bounded desktop Codex conversation runtime. The next slice is
documentation/contract work for a future visualization surface that helps the
operator see how the orchestration is performing inside the desktop app.

This contract should make the visualization concrete enough for a later runtime
slice to implement without further design decisions, while preserving the
project's existing canonical-artifact-first, approval-gated, audit-aware model.

Work against the actual repo state. Do not rely on prior chat context.

## Required work
- author the `Phase 10AH` contract in the repo's canonical planning/docs
  artifacts
- define the bounded visualization vocabulary for at least:
  phase, sub-phase, current task, current loop-state status, review branch, fix
  branch, human-gated pause states, blocked/halted states, and artifact-backed
  progress
- define how a future desktop graph/node/icon-based flow view distinguishes
  canonical mirrors from advisory derived state
- define how a future visualization surface can show orchestration progress
  without creating a hidden desktop-only state plane, progress cache, or second
  controller
- define the safety, approval, audit, and source-of-truth boundaries this future
  visualization runtime must preserve
- add or update focused documentation-consistency coverage if the repo expects
  new phase/doc alignment tests
- update `README.md` to reflect the active phase and any new contract doc added

## Constraints
- Follow `CLAUDE.md`.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not implement the runtime graph/icon UI in this phase; this is a contract
  slice.
- Do not invent a hidden UI-only graph state store, progress cache, or
  background watcher.
- Do not bypass canonical artifact ownership, approval gates, audit boundaries,
  or the planner/activator separation.
- Prefer small, testable, reversible changes.

## Important guardrails
- The future visualization surface is a reporting layer over shipped canonical
  artifacts, not a second orchestrator.
- The contract must clearly separate canonical mirrors from advisory derived
  state.
- The contract should be concrete enough that a later runtime slice can build an
  N8N-like phase/orchestration view without guessing the data model or safety
  boundaries.

## Likely files
- `.agent-loop/phase-plan.md`
- `docs/`
- `README.md`
- `ROADMAP.md` if alignment is needed
- `tests/test_documentation_consistency.py`

## Required output
After implementation, write `.agent-loop/claude-summary.md` using the required
Claude Implementation Summary format and include the validation you ran.
