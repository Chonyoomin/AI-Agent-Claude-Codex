# Claude Code Task

## Phase
Phase 10D - External Workspace Attach/Detach Runtime Initial Slice

## Objective
Implement the External Workspace Attach/Detach Runtime Initial Slice for the agent loop. This slice should add the minimal runtime path that selects an external target, validates the approved ownership/path boundaries, writes and removes the controller-owned attach record under the approved contract, and records bounded attach/detach audit behavior without yet performing full target bootstrap automation.

## Context
Phase 10 continues the future product-features track. Phase 10D is the first implementation slice in the external-workspace path: the approved Phase 10A/10B/10C contracts now exist, and this slice should turn the minimal attach/detach path into executable runtime behavior without widening into full bootstrap runtime, target-side cycle dispatch, or external UI control.

## Required work
- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 10 / 10D as active
- `.agent-loop/phase-plan.md` records Phase 10C as closed history and contains a `## Phase 10D - External Workspace Attach/Detach Runtime Initial Slice` section with concrete objective, done criteria, and exclusions
- implement the minimal attach/detach runtime path in repo code:
  - select an external target through a bounded runtime surface
  - validate the approved Phase 10A ownership/path refusals before attach
  - write the controller-owned `.agent-loop/external-target.json` attach record according to the approved Phase 10B schema
  - remove the attach record on detach through an explicit bounded detach path
  - emit attach/detach audit lines consistent with the approved Phase 10A/10B/10C contracts
- preserve the shipped artifact/source-of-truth boundary:
  - controller-owned attach metadata remains controller-owned
  - target-side canonical artifacts remain target-owned
  - attach/detach must not silently activate a target-side phase
  - attach/detach must not invent advisory state as canonical truth
- preserve the shipped CLI-first workflow, planner/activation boundaries, approval semantics, halt/refusal vocabulary, checkpoint/resume behavior, cycle thresholds, and repo-artifact source-of-truth model
- update `README.md` so it reflects that Phase 10D is active and that the attach/detach runtime slice is now the implementation focus
- add focused validation sufficient to prove the runtime is bounded, consistent with the approved contracts, and non-drifting

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
- no bootstrap runtime implementation beyond the bounded hooks strictly required for Phase 10D attach/detach flow
- no target-side cycle dispatch implementation
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
