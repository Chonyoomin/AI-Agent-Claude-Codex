# Claude Code Task

## Phase
Phase 10M - Desktop App Read-Only Runtime Initial Slice

## Objective
Implement Phase 10M for the agent loop. This slice should build the first local read-only desktop app that opens against a chosen controller root, renders the shipped Phase 10H status view, Phase 10I controls view, and Phase 10K artifact dashboard view, and preserves the canonical-artifact-first model without introducing hidden orchestration or mutation paths.

## Context
Implement the Desktop App Read-Only Runtime Initial Slice for the agent loop.
This slice should build the first local desktop app that opens against a chosen
controller root, renders the shipped Phase 10H status view, Phase 10I controls
view, and Phase 10K artifact dashboard view, and preserves the canonical-
artifact-first model without introducing hidden orchestration or mutation
paths.

## Required work
- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`,
  and `.agent-loop/loop-state.json` identify Phase 10 / 10M as active
- `.agent-loop/phase-plan.md` records Phase 10L as closed history and contains
  a `## Phase 10M - Desktop App Read-Only Runtime Initial Slice` section with
  concrete objective, done criteria, and exclusions
- the repository ships the first local desktop app runtime that opens against
  an operator-selected controller root and renders the shipped Phase 10H
  status, Phase 10I controls, and Phase 10K artifact dashboard views
- the desktop runtime preserves the Phase 10L contract boundaries: local-only
  process, canonical-artifact-first rendering, bounded refresh/poll behavior,
  advisory-vs-canonical tagging, and no second source of truth
- the desktop runtime remains read-only apart from the already-shipped Phase
  10I three-control library-call delegation surface and does not dispatch
  mutating CLI operations on the operator's behalf
- focused validation proves the desktop runtime is bounded, reads the shipped
  Python view surfaces rather than re-implementing them, and does not widen
  into hidden orchestration, action-bridge behavior, concurrency runtime, or
  other later Phase 10 work
- `README.md` reflects that Phase 10M is active and that the read-only desktop
  runtime is now the implementation focus

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
- no mutating desktop action dispatch beyond the already-shipped Phase 10I
  three-control read-only delegation surface
- no packaging, installer, code-signing, auto-update, or system-tray work yet
- no multi-target desktop sessions or controlled-concurrency work
- no hidden background UI-side orchestration or second source of truth
- no MCP integration, RAG layer, GitHub integration, or model-policy
  extensibility work
- no automatic next-phase activation behavior that bypasses or rewrites the
  shipped Phase 4 planner / activation separation, or that replaces canonical
  prompt/review/checkpoint artifacts with transient runtime-only state
- no rewrite of current shipped behavior just to make future desktop-app,
  concurrency, or autonomy work easier
- no regression of the shipped Phase 5 review, strict, bounded autonomous,
  reconciliation, or prompt-bootstrap behavior
- no regression of the shipped Phase 6 memory, checkpoint, continuation,
  runtime-adapter, or LangChain support-layer behavior
- no contract rewrites in `AGENTS.md` or `CLAUDE.md`
- no change to the Phase 2A Evidence Collection Contract
- no change to the Phase 3A Orchestrator Contract body
- no change to the Phase 4A Planning Contract body
- no Git automation

## Required output
After implementation, write `.agent-loop/claude-summary.md` using the required Claude Implementation Summary format.
