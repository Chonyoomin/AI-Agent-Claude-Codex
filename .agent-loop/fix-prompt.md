# Claude Code Fix Task

## Objective
Fix only the current Claude-owned Phase 10K review issues found by Codex.

## Context
The latest Phase 10K implementation was reviewed by Codex and received the verdict `NEEDS_FIXES`.

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
- Fix the contract/runtime mismatch in the Phase 10K `progress_history` surface.
  The approved Phase 10J contract says Progress History's canonical sources include the per-phase Phase 6I distillation entries under `.agent-loop/memory/` when present. The current `scripts/agent_loop.py` implementation only mirrors `loop-state.json`, `phase-plan.md`, and `orchestrator.log`.
  Update the Phase 10K runtime so the `progress_history` surface actually incorporates the Phase 6I distillation memory entries in a bounded, contract-preserving way. Keep the surface read-only, preserve the canonical-mirror vs advisory distinction, and add focused tests proving this coverage.
- Fix the contract/runtime mismatch in the Phase 10K `token_cost` surface.
  The approved Phase 10J contract says Token / Cost Reporting should mirror the Phase 6F token-exhaustion checkpoint files and continuation context in addition to `capacity-retry-state.json` and loop-state cycle fields. The current implementation only mirrors `capacity-retry-state.json` plus loop-state.
  Update the Phase 10K runtime so the `token_cost` surface includes the token-exhaustion checkpoint / continuation-context information the contract requires, in a bounded read-only form, and add focused tests proving this coverage.
- Fix the contract/runtime mismatch in the Phase 10K `failure_analytics` surface.
  The approved Phase 10J contract says Failure Analytics includes the Phase 6L repeated-failure synthesis entries under `.agent-loop/memory/` and the `last_verdict` / `status` fields from `loop-state.json` as canonical inputs. The current implementation only mirrors `codex-review.md` and the four evidence files.
  Update the Phase 10K runtime so the `failure_analytics` surface includes the repeated-failure synthesis entries and loop-state failure context the contract requires, and add focused tests proving this coverage.
- Keep the fixes bounded to Phase 10K.
  Do not widen the dashboard into advanced runtime work, new mutating controls, new library-callable controls, or any broader Phase 10 feature. This is a contract-conformance fix for the existing six-surface dashboard runtime.
- Update `README.md` only if needed to keep the Phase 10K description accurate after the runtime/test fixes.

## Constraints
- Fix only the listed issues.
- Do not redesign unrelated code.
- Do not expand the product scope.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not edit `.agent-loop/loop-state.json` or `.agent-loop/orchestrator.log` by hand.
- Do not delete files unless explicitly required and approved.
- Preserve the original task objective.
- Update focused tests to prove the repaired contract coverage.
- Prefer minimal, targeted changes.

## Required output
After applying fixes, update `.agent-loop/claude-summary.md` using the required Claude Implementation Summary format.
