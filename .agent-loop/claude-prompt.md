# Claude Code Task

## Phase
Phase 9C - Orchestrator-Driven Prompt Handoff

## Objective
Implement the Orchestrator-Driven Prompt Handoff slice for the agent loop. This slice should let the orchestrator dispatch the active Codex/Claude prompt handoff from canonical prompt artifacts and capture the resulting handoff audit trail without requiring manual copy/paste, while preserving the shipped planner/activation boundary, review ownership model, and per-phase human gate.

## Context
Implement the Orchestrator-Driven Prompt Handoff slice for the agent loop. This
slice should let the orchestrator dispatch the active Codex/Claude prompt
handoff from canonical prompt artifacts and capture the resulting handoff audit
trail without requiring manual copy/paste, while preserving the shipped
planner/activation boundary, review ownership model, and per-phase human gate.

## Required work
- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and
  `.agent-loop/loop-state.json` identify Phase 9 / 9C as active
- `.agent-loop/phase-plan.md` records Phase 9B as closed history and contains a
  `## Phase 9C - Orchestrator-Driven Prompt Handoff` section with concrete
  objective, done criteria, and exclusions
- the repository ships an orchestrator-driven prompt-handoff surface that can
  dispatch the active Codex/Claude prompt cycle from canonical prompt artifacts
  without manual copy/paste
- the handoff layer preserves the shipped prompt/source-of-truth boundary:
  canonical prompt artifacts remain on disk, `.agent-loop/claude-done.json`
  remains a routing signal, and the handoff does not replace the review/fix
  artifact model with transient runtime-only state
- the new surface preserves the shipped CLI-first workflow,
  planner/activation boundaries, approval semantics, halt/refusal vocabulary,
  checkpoint/resume behavior, and repo-artifact source-of-truth model
- missing or malformed prompt artifacts are refused cleanly rather than
  producing an ambiguous or partial handoff
- focused validation covers successful handoff dispatch, refusal behavior, and
  audit-trail capture from repo artifacts and logs
- `README.md` reflects that Phase 9C is active and that orchestrator-driven
  prompt handoff is now the implementation focus

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
- no autonomous review/fix execution, automatic next-phase activation,
  long-run completion heuristics, capacity-halt re-probe, or final acceptance
  automation (Phases 9D-9G)
- no prompt-handoff behavior that bypasses or rewrites the shipped Phase 4
  planner / activation separation, or that replaces canonical prompt artifacts
  with transient runtime-only state
- no regression of the shipped Phase 5 review, strict, bounded autonomous,
  reconciliation, or prompt-bootstrap behavior
- no regression of the shipped Phase 6 memory, checkpoint, continuation,
  runtime-adapter, or LangChain support-layer behavior
- no contract rewrites in `AGENTS.md` or `CLAUDE.md`
- no MCP support, external UI, or concurrent-agent operation in this slice
- no change to the Phase 2A Evidence Collection Contract
- no change to the Phase 3A Orchestrator Contract body
- no change to the Phase 4A Planning Contract body
- no Git automation

## Required output
After implementation, write `.agent-loop/claude-summary.md` using the required Claude Implementation Summary format.
