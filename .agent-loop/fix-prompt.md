# Claude Code Fix Task

## Objective
Fix only the current Claude-owned Phase 10R review issues found by Codex.

## Context
The latest Phase 10R implementation was reviewed by Codex and received the
verdict `NEEDS_FIXES`.

Read:
- `CLAUDE.md`
- `.agent-loop/claude-prompt.md`
- `.agent-loop/codex-review.md`
- `scripts/agent_loop.py`
- `tests/test_desktop_project_start.py`
- `tests/test_desktop_app.py`
- `README.md`
- `docs/desktop-app-contract.md`
- `TASK.md`
- `.agent-loop/phase-plan.md`

## Required fixes
- Fix the project-start attach-state routing bug. Right now, when
  `inspect_external_target_attach(...)` refuses on a malformed or unreadable
  attach record, `build_desktop_project_start_view(...)` soft-fails that state
  to `attached=False`, which incorrectly makes
  `attach_or_select_target_project` eligible again even though the canonical
  `attach-external-target` path still refuses when an attach record exists.
  Update the Phase 10R desktop project-start surface so malformed/unreadable
  attach-record states fail closed instead of advertising an attach path that
  the canonical CLI cannot actually take.
- Fix the active-phase gating bug on
  `start_first_phase_via_plan_activate`. The current implementation derives
  `has_active_phase` from the controller repository's own
  `.agent-loop/loop-state.json`, which makes the affordance ineligible whenever
  the controller itself is already on an active phase like `Phase 10R`, even if
  the attached target project is fresh and is exactly what the operator wants
  to start. Update the Phase 10R workflow so "start the target project's first
  phase" is evaluated against the correct project-start state instead of the
  controller repo's own current phase bookkeeping.
- Add or update focused tests for both fixes:
  - coverage proving malformed/unreadable attach-record states do not surface a
    false-positive eligible attach path
  - coverage proving the first-phase-start affordance is gated against the
    correct target/project-start state rather than the controller repo's own
    active phase state
- Update `README.md` as needed so the 10R description matches the shipped
  implementation after the fixes.

## Constraints
- Fix only the listed issues.
- Do not redesign later phases such as 10S, 10T, or 10U.
- Do not introduce a hidden persisted control plane.
- Do not silently mutate in-flight `loop-state.json` approval state or other
  canonical controller fields outside approved canonical write paths.
- Do not add subprocess spawning, shell execution, network IO, or canonical
  artifact writes beyond the shipped bounded desktop/runtime contracts.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not edit `.agent-loop/loop-state.json` or `.agent-loop/orchestrator.log`
- by hand.
- Do not delete files unless explicitly required and approved.
- Preserve the original Phase 10R objective and existing Phase 10L/10M/10N
  non-mutation boundaries.
- Prefer minimal, targeted changes.

## Required output
After applying fixes, update `.agent-loop/claude-summary.md` using the required
Claude Implementation Summary format.
