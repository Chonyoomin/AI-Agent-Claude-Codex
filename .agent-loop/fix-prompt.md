# Claude Code Fix Task

## Objective
Fix the remaining Phase 7A gap so the VS Code task layer actually covers the evidence-collection operator flow the active task promises, rather than only validating already-existing artifacts.

## Context
Codex reviewed the current Phase 7A implementation from repo state. The task layer is structurally narrow and the focused test suite passes, but one contract-level gap remains.

`TASK.md` says this slice should add VS Code tasks for common operator flows "such as running the loop, collecting evidence, opening review artifacts, and other CLI-backed entrypoints." The current `.vscode/tasks.json` includes `validate-artifacts`, which only validates artifacts that already exist, but it does not expose the actual evidence-collection surface. In this repo, the evidence producer is still `scripts/run_checks.sh`, not `python scripts/agent_loop.py validate-artifacts`.

The tests and README currently lock in that narrower interpretation by treating the expected common task set as only the eight `agent_loop.py` subcommands. That means the suite passes while the implementation still misses one of the phase's named operator flows.

## Required fixes
- Add a VS Code task that exposes the actual evidence-collection flow using the shipped evidence command surface, while preserving the CLI-first contract and avoiding IDE-owned reimplementation.
- Keep the task layer thin and auditable: no shell-chaining, no inline scripting, no new orchestrator behavior, and no widening into unrelated VS Code integration scope.
- Update the focused Phase 7A tests so the expected common operator flow set includes the real evidence-collection task and verifies the corrected command mapping.
- Update `README.md` so the Phase 7A description and task list match the corrected implementation.
- Update `.agent-loop/claude-summary.md` so it accurately describes the final task set and exact validation commands run.

## Constraints
- Follow `CLAUDE.md`.
- Stay within Phase 7A scope.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not broaden into Phase 7B/7C work such as dashboards, inspection UX, reset UX, keybindings, launch configs, or VS Code-owned orchestration behavior.
- Preserve the existing Phase 5 and Phase 6 runtime semantics unchanged.
- Prefer the smallest safe fix that makes the shipped task set and tests match the active Phase 7A contract.

## Required output
After implementing the fix, update `.agent-loop/claude-summary.md` with the required summary format and include the exact validation commands you ran.
