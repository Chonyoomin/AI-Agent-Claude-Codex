# Claude Code Task

## Phase
Phase 9F - Capacity-Halt Reprobe And Automatic Resume

## Objective
Implement the Capacity-Halt Reprobe And Automatic Resume slice for the agent loop. This slice should treat Claude/Codex token or rate-limit exhaustion as a resumable external-capacity halt, persist bounded retry metadata beside the existing checkpoint, wait with bounded backoff, re-probe availability, and resume the exact suspended step automatically when capacity returns without silently widening autonomy or retrying forever, while preserving the shipped planner/activation boundary, artifact source-of-truth model, and hard-stop behavior.

## Context
Implement the Capacity-Halt Reprobe And Automatic Resume slice for the agent
loop. This slice should treat Claude/Codex token or rate-limit exhaustion as a
resumable external-capacity halt, persist bounded retry metadata beside the
existing checkpoint, wait with bounded backoff, re-probe availability, and
resume the exact suspended step automatically when capacity returns without
silently widening autonomy or retrying forever, while preserving the shipped
planner/activation boundary, artifact source-of-truth model, and hard-stop
behavior.

## Required work
- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and
  `.agent-loop/loop-state.json` identify Phase 9 / 9F as active
- `.agent-loop/phase-plan.md` records Phase 9E as closed history and contains a
  `## Phase 9F - Capacity-Halt Reprobe And Automatic Resume` section with
  concrete objective, done criteria, and exclusions
- the repository ships a bounded capacity-halt re-probe and automatic-resume
  layer for Claude/Codex token or rate-limit exhaustion that extends the
  shipped Phase 6 continuation primitives and the Phase 9B/9C/9D/9E autonomous
  runtime
- the runtime persists auditable retry metadata beside the existing checkpoint,
  waits with bounded backoff, re-probes capacity availability, and resumes the
  exact suspended step automatically when capacity returns
- the new surface preserves the shipped artifact/source-of-truth boundary:
  canonical prompt, summary, review, fix, checkpoint, retry-state, and
  loop-state artifacts remain authoritative; advisory descriptors remain
  routing/timing artifacts only
- the new surface preserves the shipped CLI-first workflow,
  planner/activation boundaries, approval semantics, halt/refusal vocabulary,
  checkpoint/resume behavior, cycle thresholds, and repo-artifact
  source-of-truth model
- focused validation proves bounded capacity-halt retry behavior, refusal
  behavior, retry-budget/backoff behavior, and hard-stop preservation from repo
  artifacts and logs
- `README.md` reflects that Phase 9F is active and that capacity-halt re-probe
  / automatic resume are now the implementation focus

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
- no final human acceptance or polish automation (Phase 9G)
- no automatic next-phase activation behavior that bypasses or rewrites the
  shipped Phase 4 planner / activation separation, or that replaces canonical
  prompt/review/checkpoint artifacts with transient runtime-only state
- no regression of the shipped Phase 5 review, strict, bounded autonomous,
  reconciliation, or prompt-bootstrap behavior
- no regression of the shipped Phase 6 memory, checkpoint, continuation,
  runtime-adapter, or LangChain support-layer behavior beyond the narrow
  capacity-halt retry / automatic-resume seam
- no contract rewrites in `AGENTS.md` or `CLAUDE.md`
- no MCP support, external UI, or concurrent-agent operation in this slice
- no change to the Phase 2A Evidence Collection Contract
- no change to the Phase 3A Orchestrator Contract body
- no change to the Phase 4A Planning Contract body
- no Git automation

## Required output
After implementation, write `.agent-loop/claude-summary.md` using the required Claude Implementation Summary format.
