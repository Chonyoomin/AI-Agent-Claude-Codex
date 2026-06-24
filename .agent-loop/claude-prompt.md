# Claude Code Task

## Phase
Fix Phase A - Automatic Local Claude/Codex Invocation Reliability

## Objective
Implement Fix Phase A for the agent loop. This slice should define and validate the real local adapter contract for `AGENT_LOOP_CLAUDE_CMD` and `AGENT_LOOP_CODEX_CMD`, provide first-party wrapper support or templates for invoking both CLIs automatically, and prove that the shipped intra-phase loop can run without manual prompt transfer when those adapter commands are configured correctly.

## Context
Fix Phase A is a targeted remediation slice, not a renumbering of the main roadmap. The goal is to close the gap between the shipped adapter seams and the desired real-world workflow where local Claude and Codex invocation can run automatically on a configured machine. This slice should improve the existing local invocation path without claiming that fully autonomous PRD-to-product execution is already solved.

## Required work
- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Fix Phase A as active
- `.agent-loop/phase-plan.md` records Phase 10H as closed history and contains a `## Fix Phase A - Automatic Local Claude/Codex Invocation Reliability` section with concrete objective, done criteria, and exclusions
- define and implement the concrete local adapter contract for `AGENT_LOOP_CLAUDE_CMD` and `AGENT_LOOP_CODEX_CMD`:
  - document what each command must do
  - define which canonical artifact each command must produce
  - preserve fail-closed behavior when a command exits but does not produce a fresh artifact
  - preserve repo-root and working-directory assumptions explicitly rather than implicitly
- add first-party wrapper support or wrapper templates for local Claude CLI and Codex CLI invocation so the orchestrator can drive both tools without manual prompt transfer
- add focused validation for:
  - missing binaries
  - wrapper commands that exit without writing fresh artifacts
  - stale artifact writes
  - working-directory or repo-root mismatch assumptions
- update operator-facing documentation so it clearly distinguishes:
  - automatic local Claude/Codex invocation within the existing phase loop
  - the still-separate fully autonomous PRD-to-product mode

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
- no fully autonomous phase-to-phase PRD execution
- no automatic next-phase activation behavior that bypasses the shipped Phase 4 planner / activation separation
- no mutating external UI work beyond the completed 10H read-only slice
- no concurrent Codex/Claude overlap execution work
- no MCP integration, RAG layer, GitHub integration, or model-policy extensibility work
- no change to the Phase 2A Evidence Collection Contract
- no change to the Phase 3A Orchestrator Contract body
- no change to the Phase 4A Planning Contract body
- no Git automation

## Required output
After implementation, write `.agent-loop/claude-summary.md` using the required Claude Implementation Summary format.
