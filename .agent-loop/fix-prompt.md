# Claude Code Fix Task

## Phase
Phase 10AG - Desktop Codex Conversation Surface Initial Slice

## Objective
Fix the shipped 10AG desktop Codex conversation callback so it uses the real
runtime safety-gate inputs and emits the promised audit trail.

## Context
Codex reviewed the current repo state and found two Claude-owned runtime defects
in the 10AG Tk callback path. `.agent-loop/codex-review.md` is the source of
truth for the findings and severity.

## Required fixes
- Wire the live desktop Send path in `scripts/agent_loop.py` to real runtime gate
  inputs instead of hardcoding `overlap_state="no_signal"` and
  `strict_mode_gate_pending=False`.
- The callback must derive the overlap-safe state from the shipped canonical
  runtime signal rather than inventing a desktop-only substitute, and must pass
  the real strict-mode pending state that would block resume.
- Emit the shipped desktop-codex-conversation audit line through the canonical
  orchestrator audit path on both success and refusal paths. Do not create a new
  audit file.
- Add or update focused tests in `tests/test_desktop_app.py` that would fail if
  the callback regresses back to hardcoded clean gate values or stops writing the
  audit entry.

## Constraints
- Stay within Phase 10AG scope. Do not add multi-intent dispatch for the other
  five intents.
- Do not create a new canonical artifact.
- Do not introduce hidden persistence for the advisory draft or operator
  identity.
- Preserve the existing closed intent vocabulary, closed refusal vocabulary, and
  read-only canonical mirror behavior.

## Required output
- Update `.agent-loop/claude-summary.md` with the concrete code changes, tests
  run, and any residual limitations that remain after the fix.
