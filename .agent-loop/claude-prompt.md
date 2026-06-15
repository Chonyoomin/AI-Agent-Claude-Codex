# Claude Code Task

## Phase
Phase 9A - Autonomous Mode Contract And Safety Policy

## Objective
Implement the Autonomous Mode Contract And Safety Policy slice for the agent loop. This slice should define what the future fully autonomous PRD-to-product mode is allowed to do, what still requires explicit human approval, how the mode remains auditable from repo artifacts, and which safety boundaries and hard stops are preserved, without yet implementing orchestrator-driven autonomous PRD execution.

## Context
Implement the Autonomous Mode Contract And Safety Policy slice for the agent
loop. This slice should define what the future fully autonomous PRD-to-product
mode is allowed to do, what still requires explicit human approval, how the
mode remains auditable from repo artifacts, and which safety boundaries and
hard stops are preserved, without yet implementing orchestrator-driven
autonomous PRD execution.

## Required work
- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and
  `.agent-loop/loop-state.json` identify Phase 9 / 9A as active
- `.agent-loop/phase-plan.md` records Phase 8C as closed history and contains a
  `## Phase 9A - Autonomous Mode Contract And Safety Policy` section with
  concrete objective, done criteria, and exclusions
- the repository defines a concrete contract for the future fully autonomous
  PRD-to-product mode, including allowed actions, preserved hard stops, audit
  expectations, and explicit human-approval boundaries
- documentation distinguishes current shipped behavior from future roadmap items
  and does not present future capabilities as if they already exist
- the contract stays aligned with the shipped CLI-first workflow, artifact
  ownership model, halt/refusal vocabulary, checkpoint/resume behavior, and
  repo-artifact source-of-truth model
- the contract distinguishes future autonomous-mode behavior from currently
  shipped Phase 5 bounded `autonomous` behavior instead of collapsing them
  together
- focused validation or review coverage proves the docs match the actual repo
  state and do not claim unimplemented autonomous execution behavior
- `README.md` reflects that Phase 9A is active and that the autonomy contract /
  safety-policy definition is now the implementation focus

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
- no implementation of orchestrator-driven fully autonomous PRD execution
- no new runtime, planner, activator, evidence-collection, review-routing,
  checkpoint, continuation, memory, runtime-adapter, LangChain, or VS Code
  feature work beyond the narrow contract/planning slice
- no contract rewrites in `AGENTS.md` or `CLAUDE.md`
- no documentation that invents behavior the repo does not currently ship
- no collapsing of future roadmap items into present-tense product behavior
- no MCP support, external UI, concurrent-agent operation, or implementation of
  fully autonomous PRD-to-product execution in this slice
- no change to the Phase 2A Evidence Collection Contract
- no change to the Phase 3A Orchestrator Contract body
- no change to the Phase 4A Planning Contract body
- no change to `scripts/run_checks.sh`
- no Git automation

## Required output
After implementation, write `.agent-loop/claude-summary.md` using the required Claude Implementation Summary format.
