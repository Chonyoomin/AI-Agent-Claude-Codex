# Claude Code Fix Task

## Phase
Fix Phase C6 - Plain-English Run Console

## Objective
Resolve the Claude-owned C6 readiness-state finding without widening the phase.

## Finding To Fix

The C6 console reports "Ready to run" from canonical loop-state alone even when
the C5 Project, PRD, or Run Mode prerequisites are incomplete. This conflicts
with the guided setup contract and can tell the operator to press a disabled
Start Agent control.

## Required fix
- Make the C6 console use the same guided prerequisite state as C5.
- Render setup guidance whenever Project, PRD, or Run Mode is incomplete.
- Render ready only when all three prerequisites are satisfied and the
  canonical runtime is startable.
- Keep the mapping plain-English and hide raw runtime vocabulary by default.
- Add focused tests for missing, partial, and fully satisfied prerequisites.
- Preserve read-only behavior: no canonical writes, UI-only cache, watcher,
  timer, thread, or alternate state plane.
- Preserve all existing running, waiting, blocked, approval-required, and
  complete mappings.

## Constraints
- Read the actual repository state and CLAUDE.md before editing.
- Do not modify AGENTS.md or CLAUDE.md.
- Do not implement C7-C8 review, approval, or completion actions.
- Do not fabricate or edit .agent-loop/codex-review.md.
- Do not add unrelated refactors or Git automation.

## Required validation
- python -m unittest tests.test_desktop_app tests.test_documentation_consistency -q
- python -m unittest discover -s tests -q
- python scripts/agent_loop.py launch-desktop-app --controller-root . --headless

## Required output
Update .agent-loop/claude-summary.md using the required Claude Implementation
Summary format. Codex will re-review the resulting repository state.

