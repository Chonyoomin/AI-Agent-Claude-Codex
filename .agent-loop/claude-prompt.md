# Claude Code Task

## Phase
Phase 10F - External Target Validation And Refusal Hardening

## Objective
Implement External Target Validation And Refusal Hardening for the agent loop. This slice should strengthen external-workspace runtime safety by hardening target-root and attach-state validation, expanding malformed-artifact and stale-attach refusal coverage, and tightening controller/target consistency checks without widening into target-side cycle dispatch or external UI behavior.

## Context
Phase 10 continues the future product-features track. Phase 10E completed the bounded bootstrap-runtime path for `empty_target` external workspaces, and Phase 10F is the next safety-hardening slice in the external-workspace path: the shipped attach/bootstrap surfaces now need stronger validation and refusal handling around stale, inconsistent, or malformed external-target state before later target-side control surfaces are added.

## Required work
- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 10 / 10F as active
- `.agent-loop/phase-plan.md` records Phase 10E as closed history and contains a `## Phase 10F - External Target Validation And Refusal Hardening` section with concrete objective, done criteria, and exclusions
- harden the external-workspace runtime path in repo code:
  - strengthen validation around attached targets, target-root safety, and controller/target consistency
  - refuse stale attach state fail-closed when controller-owned attach metadata and target-side marker artifacts no longer agree
  - expand malformed-artifact coverage so structurally invalid or semantically inconsistent external-target state is rejected explicitly rather than tolerated or silently repaired
  - keep the existing attach/bootstrap ownership boundary intact: controller-owned attach metadata remains controller-owned and target-side canonical artifacts remain target-owned
  - preserve the shipped activation gate: hardening must not silently activate a target-side phase or collapse the Phase 4C activator + `APPROVED_FOR_ACTIVATION` boundary
- preserve the shipped artifact/source-of-truth boundary:
  - controller-owned attach metadata remains controller-owned
  - target-side canonical artifacts remain target-owned
  - the hardening layer must not silently activate a target-side phase
  - the hardening layer must not invent advisory state as canonical truth
- preserve the shipped CLI-first workflow, planner/activation boundaries, approval semantics, halt/refusal vocabulary, checkpoint/resume behavior, cycle thresholds, and repo-artifact source-of-truth model
- update `README.md` so it reflects that Phase 10F is active and that external-target validation/refusal hardening is now the implementation focus
- add focused validation sufficient to prove the hardening behavior is bounded, consistent with the approved contracts, and non-drifting

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
- no target-side cycle dispatch or multi-step run-control implementation
- no external UI, dashboard, or run-control implementation
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
