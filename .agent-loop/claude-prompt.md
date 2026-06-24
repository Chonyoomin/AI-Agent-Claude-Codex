# Claude Code Task

## Phase
Phase 10H - Minimal External UI Read-Only Status Surface

## Objective
Implement the Minimal External UI Read-Only Status Surface for the agent loop. This slice should add a thin external UI that can select an attached target, read the approved controller-side and target-side canonical artifacts, render active phase/task/status and related read-only views, and preserve the 10G advisory-vs-canonical, CLI-only, and source-of-truth boundaries without yet adding run/resume controls or any canonical-artifact writes from the UI.

## Context
Phase 10 continues the future product-features track. Phase 10G completed the documentation-first UI contract slice for external-workspace mode, and Phase 10H is the first runtime slice that must satisfy that contract: a bounded read-only external UI viewer over approved canonical artifacts, without introducing mutating UI controls, a competing source of truth, or any bypass of the shipped CLI-first workflow.

## Required work
- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 10 / 10H as active
- `.agent-loop/phase-plan.md` records Phase 10G as closed history and contains a `## Phase 10H - Minimal External UI Read-Only Status Surface` section with concrete objective, done criteria, and exclusions
- implement the bounded read-only external UI runtime in repo code:
  - allow selecting an attached target and loading only the approved controller-side and target-side canonical artifacts from the 10G contract
  - render active phase/task/status and related read-only views from those artifacts
  - preserve the canonical mirror vs advisory-derived-state boundary in the rendered UI
  - preserve CLI-only operations as non-executing UI affordances only, such as copyable commands or guidance text
  - preserve refusal behavior and source-of-truth precedence when artifacts are missing, stale, or malformed
- preserve the shipped artifact/source-of-truth boundary:
  - controller-owned attach metadata remains controller-owned
  - target-side canonical artifacts remain target-owned
  - the read-only UI must not silently activate a target-side phase
  - the read-only UI must not invent advisory state as canonical truth
- preserve the shipped CLI-first workflow, planner/activation boundaries, approval semantics, halt/refusal vocabulary, checkpoint/resume behavior, cycle thresholds, and repo-artifact source-of-truth model
- update `README.md` so it reflects that Phase 10H is active and that the minimal external UI read-only status surface is now the implementation focus
- add focused validation sufficient to prove the read-only UI is bounded, consistent with the approved 10G contract, and non-drifting

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
- no mutating external UI control, dashboard action surface, or run/resume implementation beyond the bounded read-only viewer
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
