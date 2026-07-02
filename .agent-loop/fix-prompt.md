# Claude Code Fix Task

## Objective
Fix only the current Claude-owned Phase 10Z review issues found by Codex.

## Context
The latest Phase 10Z implementation was reviewed by Codex and received the
verdict `NEEDS_FIXES`.

Read:
- `CLAUDE.md`
- `.agent-loop/claude-prompt.md`
- `.agent-loop/codex-review.md`
- `.agent-loop/phase-plan.md`
- `scripts/agent_loop.py`
- `tests/test_desktop_selection.py`
- `README.md`
- `TASK.md`

## Required fixes
- Fix the Phase 10Z desktop selection affordance mismatch. In current repo
  state, `build_desktop_selection_controls(...)` sets every control
  `enabled=False` because `phase_10z_runtime_available=False`, and the Tk shell
  renders those disabled buttons directly. But the implementation comments and
  README describe these controls as the operator's copy-to-clipboard request
  template path in the deferred-runtime slice. The shipped GUI therefore does
  not expose the only advertised action.
- Align the runtime and documentation in one direction. Either:
  1. Keep the controls clickable for clipboard-copy while preserving the Phase
     10Z non-mutating boundary and making it explicit that the click copies a
     request template only, not an executable runtime action.
  2. Or keep the controls disabled, but then update the behavior, comments,
     README text, and tests so the phase no longer claims the operator can copy
     the template from the desktop app in this slice.
- Add focused regression coverage for the chosen behavior. The tests should
  fail if the desktop app behavior and the documented/descriptor semantics drift
  again.
- Keep the fix inside the approved Phase 10Z boundaries. Do not add an actual
  model/policy/template selection runtime, hidden mutation path, background
  control plane, packaging, or concurrency work.

## Constraints
- Fix only the listed issues.
- Do not redesign later phases such as 10AA+.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not edit `.agent-loop/loop-state.json` or
  `.agent-loop/orchestrator.log` by hand.
- Do not widen the Phase 10I three-control library-callable cap.
- Preserve the selection UX as a read-only, canonical-artifact-derived contract
  slice.
- Prefer minimal, targeted changes.

## Required output
After applying fixes, update `.agent-loop/claude-summary.md` using the required
Claude Implementation Summary format.
