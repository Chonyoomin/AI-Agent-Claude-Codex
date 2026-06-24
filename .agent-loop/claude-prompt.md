# Claude Code Task

## Phase
Phase 10G - Minimal External UI Contract

## Objective
Define the Minimal External UI Contract for the agent loop. This slice should specify the first external operator UI surface for external-workspace mode: which canonical artifacts it may read, which actions remain CLI-only, how advisory UI state must defer to repo artifacts on disk, and what safety/approval boundaries must remain intact before any UI runtime is implemented.

## Context
Phase 10 continues the future product-features track. Phase 10F completed the bounded validation/refusal-hardening slice for external targets, and Phase 10G is the next planning/contract slice in the external-workspace path: before any UI runtime exists, the repo needs a clear contract for the first external operator UI surface, its advisory-vs-canonical boundaries, and how it preserves the shipped CLI-first workflow instead of creating a parallel control plane.

## Required work
- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 10 / 10G as active
- `.agent-loop/phase-plan.md` records Phase 10F as closed history and contains a `## Phase 10G - Minimal External UI Contract` section with concrete objective, done criteria, and exclusions
- define the external UI contract in repo docs/planning surfaces:
  - specify which canonical controller-side and target-side artifacts a minimal external UI may read
  - specify which values a UI may render only as advisory mirrors rather than canonical truth
  - specify which operations remain CLI-only and must not be silently triggered from a UI surface
  - specify how the UI must preserve controller-vs-target ownership boundaries, approval gates, and halt/refusal semantics
  - specify how the UI must defer to canonical repo artifacts on disk instead of creating a competing control plane or state store
- preserve the shipped artifact/source-of-truth boundary:
  - controller-owned attach metadata remains controller-owned
  - target-side canonical artifacts remain target-owned
  - the UI contract must not silently activate a target-side phase
  - the UI contract must not invent advisory state as canonical truth
- preserve the shipped CLI-first workflow, planner/activation boundaries, approval semantics, halt/refusal vocabulary, checkpoint/resume behavior, cycle thresholds, and repo-artifact source-of-truth model
- update `README.md` so it reflects that Phase 10G is active and that the minimal external UI contract is now the planning focus
- add focused validation sufficient to prove the contract is bounded, internally consistent with approved external-workspace slices, and non-drifting

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
- no external UI runtime, dashboard, or run-control implementation beyond the documentation-first contract
- no target-side cycle dispatch, autonomous multi-target orchestration, or external control plane that can mutate canonical artifacts outside the shipped CLI surfaces
- no concurrent Codex/Claude execution implementation, MCP integration, RAG layer, GitHub integration, or model-policy extensibility work
- no automatic next-phase activation behavior that bypasses or rewrites the shipped Phase 4 planner / activation separation, or that replaces canonical prompt/review/checkpoint artifacts with transient runtime-only state
- no regression of the shipped Phase 5 review, strict, bounded autonomous, reconciliation, or prompt-bootstrap behavior
- no regression of the shipped Phase 6 memory, checkpoint, continuation, runtime-adapter, or LangChain support-layer behavior
- no contract rewrites in `AGENTS.md` or `CLAUDE.md`
- no change to the Phase 2A Evidence Collection Contract
- no change to the Phase 3A Orchestrator Contract body
- no change to the Phase 4A Planning Contract body
- no Git automation

## Required output
After implementation, write `.agent-loop/claude-summary.md` using the required Claude Implementation Summary format.
