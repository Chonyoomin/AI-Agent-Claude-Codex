# Claude Code Task

## Phase
Phase 10E - External Workspace Bootstrap Runtime Initial Slice

## Objective
Implement the External Workspace Bootstrap Runtime Initial Slice for the agent loop. This slice should add the explicit bootstrap path for `empty_target` external workspaces under the approved Phase 10C contract, write only the allowed target-side canonical artifact set atomically, update the controller-owned attach record's bootstrap-state fields consistently, and refuse partial or malformed target states without widening into target-side cycle dispatch or external UI behavior.

## Context
Phase 10 continues the future product-features track. Phase 10D completed the controller-side attach/detach runtime path, and Phase 10E is the next implementation slice in the external-workspace path: the approved Phase 10C bootstrap contract now needs to become executable runtime behavior for `empty_target` workspaces without widening into target-side cycle dispatch or external UI control.

## Required work
- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 10 / 10E as active
- `.agent-loop/phase-plan.md` records Phase 10D as closed history and contains a `## Phase 10E - External Workspace Bootstrap Runtime Initial Slice` section with concrete objective, done criteria, and exclusions
- implement the explicit bootstrap runtime path in repo code:
  - bootstrap only `empty_target` workspaces under the approved Phase 10C contract and explicit operator opt-in
  - write exactly the five allowed target-side canonical bootstrap artifacts atomically, or roll back fully on failure
  - require the approved operator-provided bootstrap inputs, including bootstrap identity plus initial `Human Objective` and `Project Intent`
  - update the controller-owned `.agent-loop/external-target.json` attach record's `bootstrap_state` extension fields consistently with the approved Phase 10C schema
  - emit bootstrap audit lines consistent with the approved Phase 10B/10C contracts
  - refuse `partial_target`, `malformed_target`, missing-input, operator-identity mismatch, and atomicity-failure cases fail-closed
- preserve the shipped artifact/source-of-truth boundary:
  - controller-owned attach metadata remains controller-owned
  - target-side canonical artifacts remain target-owned
  - bootstrap must not silently activate a target-side phase
  - bootstrap must not invent advisory state as canonical truth
- preserve the shipped CLI-first workflow, planner/activation boundaries, approval semantics, halt/refusal vocabulary, checkpoint/resume behavior, cycle thresholds, and repo-artifact source-of-truth model
- update `README.md` so it reflects that Phase 10E is active and that the bootstrap runtime slice is now the implementation focus
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
- no target-side cycle dispatch implementation beyond the bounded bootstrap hooks required to leave a target at `awaiting_first_activation`
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
