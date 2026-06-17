# Claude Code Task

## Phase
Phase 9D - Autonomous Internal Review/Fix Loop

## Objective
Implement the Autonomous Internal Review/Fix Loop slice for the agent loop. This slice should let the orchestrator consume the Phase 9B/9C handoff artifacts, trigger Codex review automatically, route findings by owner, regenerate `.agent-loop/fix-prompt.md` when Claude-owned fixes are required, and continue bounded internal review/fix cycles without manual routing between agents, while preserving the shipped planner/activation boundary, artifact source-of-truth model, and hard-stop behavior.

## Context
Implement the Autonomous Internal Review/Fix Loop slice for the agent loop.
This slice should let the orchestrator consume the Phase 9B/9C handoff
artifacts, trigger Codex review automatically, route findings by owner,
regenerate `.agent-loop/fix-prompt.md` when Claude-owned fixes are required,
and continue bounded internal review/fix cycles without manual routing between
agents, while preserving the shipped planner/activation boundary, artifact
source-of-truth model, and hard-stop behavior.

## Required work
- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and
  `.agent-loop/loop-state.json` identify Phase 9 / 9D as active
- `.agent-loop/phase-plan.md` records Phase 9C as closed history and contains a
  `## Phase 9D - Autonomous Internal Review/Fix Loop` section with concrete
  objective, done criteria, and exclusions
- the repository ships a bounded autonomous internal review/fix loop that can,
  from canonical repo artifacts, run Codex review after Claude completion,
  classify findings by owner, and continue Claude fix cycles without manual
  prompt passing
- the loop preserves the shipped artifact/source-of-truth boundary: canonical
  prompt, summary, review, and fix artifacts remain on disk;
  `.agent-loop/claude-done.json` and `.agent-loop/prompt-handoff.json` remain
  routing/timing artifacts rather than substitutes for review evidence
- the runtime makes Codex-owned versus Claude-owned routing explicit and
  deterministic, including automatic `.agent-loop/fix-prompt.md` refresh only
  when Claude-owned fixes are required
- the new surface preserves the shipped CLI-first workflow,
  planner/activation boundaries, approval semantics, halt/refusal vocabulary,
  checkpoint/resume behavior, cycle thresholds, and repo-artifact
  source-of-truth model
- focused validation proves bounded autonomous review/fix continuation, refusal
  behavior, and hard-stop preservation from repo artifacts and logs
- `README.md` reflects that Phase 9D is active and that autonomous internal
  review/fix continuation is now the implementation focus

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
- no automatic next-phase activation, long-run completion heuristics,
  capacity-halt re-probe, or final acceptance automation (Phases 9E-9G)
- no autonomous review/fix behavior that bypasses or rewrites the shipped
  Phase 4 planner / activation separation, or that replaces canonical
  prompt/review artifacts with transient runtime-only state
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
