# Claude Code Task

## Phase
Phase 8B - Safety, Approval, And Operational Playbooks

## Objective
Implement the Safety, Approval, And Operational Playbooks slice for the agent loop. This slice should document the shipped halt reasons, approval modes, recovery paths, and troubleshooting guidance in operator-facing playbooks while preserving the current runtime behavior and avoiding any documentation that promises unshipped automation, hidden capabilities, or alternate sources of truth.

## Context
Implement the Safety, Approval, And Operational Playbooks slice for the agent
loop. This slice should document the shipped halt reasons, approval modes,
recovery paths, and troubleshooting guidance in operator-facing playbooks while
preserving the current runtime behavior and avoiding any documentation that
promises unshipped automation, hidden capabilities, or alternate sources of
truth.

## Required work
- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and
  `.agent-loop/loop-state.json` identify Phase 8 / 8B as active
- `.agent-loop/phase-plan.md` records Phase 8A as closed history and contains a
  `## Phase 8B - Safety, Approval, And Operational Playbooks` section with
  concrete objective, done criteria, and exclusions
- the repository ships operator-facing safety, approval, halt, recovery, and
  troubleshooting playbooks that explain the shipped behavior from a clean
  clone without requiring prior chat context
- documentation distinguishes current shipped behavior from future roadmap items
  and does not present future capabilities as if they already exist
- operator docs remain aligned with the CLI-first workflow, approval semantics,
  halt/refusal vocabulary, recovery boundaries, and repo-artifact
  source-of-truth model
- focused validation or review coverage proves the docs match the actual repo
  state and do not claim unimplemented behavior
- `README.md` reflects that Phase 8B is active and that safety / approval /
  operational playbooks are now the implementation focus

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
- no new runtime, planner, activator, evidence-collection, review-routing,
  checkpoint, continuation, memory, runtime-adapter, LangChain, or VS Code
  feature work
- no contract rewrites in `AGENTS.md` or `CLAUDE.md`
- no documentation that invents behavior the repo does not currently ship
- no collapsing of future roadmap items into present-tense product behavior
- no MCP support, external UI, concurrent-agent operation, or fully autonomous
  PRD-to-product mode in this slice
- no change to the Phase 2A Evidence Collection Contract
- no change to the Phase 3A Orchestrator Contract body
- no change to the Phase 4A Planning Contract body
- no change to `scripts/run_checks.sh`
- no Git automation

## Required output
After implementation, write `.agent-loop/claude-summary.md` using the required Claude Implementation Summary format.
