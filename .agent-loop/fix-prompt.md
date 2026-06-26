# Claude Code Fix Task

## Objective
Fix only the current Claude-owned Phase 10I review issues found by Codex.

## Context
The latest Phase 10I implementation was reviewed by Codex and received the verdict `NEEDS_FIXES`.

Read:
- `CLAUDE.md`
- `.agent-loop/claude-prompt.md`
- `.agent-loop/codex-review.md`
- `.agent-loop/git-diff.patch`
- `.agent-loop/test-output.log`
- `.agent-loop/lint-output.log`
- `.agent-loop/typecheck-output.log`
- `.agent-loop/build-output.log`

## Required fixes
- Fix the Phase 10I contract violation where the external UI control path mutates canonical artifacts from the UI process.
  The current implementation in `scripts/agent_loop.py` writes `.agent-loop/orchestrator.log` on successful `invoke_external_ui_control(...)` delegation and routes refusal cases through `_halt(...)`, which persists `halted_input_missing` into `.agent-loop/loop-state.json` and writes canonical halt log lines.
  This must be corrected to satisfy the existing Phase 10G UI contract in `docs/external-ui-contract.md`: the UI must not write canonical artifacts it reads, must not call mutating or throwing helpers such as `_halt(...)`, and a refused UI-side operation must not produce a canonical audit line.
  Keep the Phase 10I surface bounded: `view-external-controls` remains read-only, `invoke-external-control --control <ID>` may still delegate only the allowed read-only library-call controls, and mutating or copy-paste-only controls must still be refused fail-closed from the operator’s perspective. But the refusal/success behavior needs to be implemented without mutating `.agent-loop/loop-state.json` or `.agent-loop/orchestrator.log`.
- Update or extend `tests/test_external_ui_controls.py` so the contract-preserving behavior is proven explicitly.
  Add/adjust coverage to show:
  - successful library-call delegation does not write `.agent-loop/orchestrator.log`
  - refused `invoke-external-control` attempts do not mutate `.agent-loop/loop-state.json`
  - refused `invoke-external-control` attempts do not write canonical audit lines
  - CLI exit behavior and user-visible refusal messaging remain intentional and tested
- Fix the stale README status text in `README.md`.
  The current README still contains an older Phase 10G paragraph that refers to “Future Phase 10H” and “Phase 10I” as upcoming. Rewrite only the stale forward-looking portion so the top-level project status is internally consistent with the shipped/current Phase 10H and active Phase 10I descriptions.

## Constraints
- Fix only the listed issues.
- Do not redesign unrelated code.
- Do not expand the product scope.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not edit `.agent-loop/loop-state.json` or `.agent-loop/orchestrator.log` by hand.
- Do not delete files unless explicitly required and approved.
- Preserve the original task objective.
- Update tests if behavior changes.
- Prefer minimal, targeted changes.

## Required output
After applying fixes, update `.agent-loop/claude-summary.md` using the required Claude Implementation Summary format.
