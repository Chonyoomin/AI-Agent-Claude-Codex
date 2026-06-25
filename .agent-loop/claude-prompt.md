# Claude Code Task

## Phase
Phase 10I - Minimal External UI Run/Resume Controls

## Objective
Implement Phase 10I for the agent loop. This slice should add bounded run/resume/inspect controls to the external UI on top of the shipped Phase 10H read-only surface, while preserving the CLI-first contract, canonical repo artifacts as the source of truth, and all existing approval and ownership boundaries.

## Context
Phase 10I builds directly on the shipped Phase 10H read-only external UI status surface. The goal is to let an operator trigger the already-shipped run/resume/inspect flows from the external UI in a bounded way without turning the UI into a general-purpose control plane or displacing repo artifacts on disk as the source of truth.

## Required work
- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 10 / 10I as active
- `.agent-loop/phase-plan.md` records Phase 10H and Fix Phase A as closed history and contains a `## Phase 10I - Minimal External UI Run/Resume Controls` section with concrete objective, done criteria, and exclusions
- add bounded external UI controls for the already-shipped run/resume/inspect flows on top of the Phase 10H read-only status surface
- preserve the shipped CLI-first workflow and make clear which UI actions are delegating to existing runtime surfaces rather than inventing a new control plane
- preserve the shipped artifact/source-of-truth boundary so repo artifacts on disk remain authoritative over any UI cache, session state, rendered status summary, or in-memory view model
- preserve the shipped approval semantics, halt/refusal vocabulary, checkpoint/resume behavior, controller-vs-target ownership boundaries, and the Phase 4C activator + `APPROVED_FOR_ACTIVATION` activation gate
- add focused validation proving the new bounded control surface is consistent with the approved Phase 10G/10H boundaries and reflected accurately in planning/docs/runtime surfaces

## Constraints
- Follow `CLAUDE.md`.
- Stay within the current task scope.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not rewrite unrelated files.
- Do not delete files unless explicitly instructed.
- Prefer small, testable, reversible changes.
- Add or update focused tests when behavior changes.

Out of scope for this phase (from `TASK.md` and `phase-plan.md`):
- no artifact dashboard, analytics, diff viewer, history explorer, or broader dashboard work
- no controlled-concurrency, overlap-safe detection, or concurrent Codex/Claude execution work
- no MCP integration, RAG layer, GitHub integration, or model-policy extensibility work
- no automatic next-phase activation behavior that bypasses the shipped Phase 4 planner / activation separation
- no change to the Phase 2A Evidence Collection Contract
- no change to the Phase 3A Orchestrator Contract body
- no change to the Phase 4A Planning Contract body
- no Git automation

## Required output
After implementation, write `.agent-loop/claude-summary.md` using the required Claude Implementation Summary format.
