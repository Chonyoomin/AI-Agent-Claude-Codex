# Claude Code Fix Task

## Phase
Fix Phase C4 - Run Mode Selector

## Objective
Resolve the Claude-owned C4 finding: the desktop Run Mode selector currently
copies a terminal recipe but does not apply the selected mode to canonical
runtime state.

## Finding To Fix

Clicking a Run Mode radio button must result in the selected existing approval
mode being applied through the canonical runtime owner. The UI currently only
copies a Phase 10Q recipe to the clipboard and still reports the old canonical
mode. This fails the C4 goal of allowing the operator to choose run behavior
from the desktop app.

## Required fix
- Route selection through an existing canonical library/runtime dispatch that
  safely applies the shipped approval-mode value, or add the smallest
  canonical-owned dispatch needed for this slice.
- After applying the selection, reread canonical state and render the actual
  applied plain-English mode.
- Preserve the existing closed mappings, plain-English labels, refusal
  handling, audit line, and fail-closed behavior.
- Keep raw runtime vocabulary and paths out of the default UI.
- Add focused tests proving selection changes canonical state.
- Add tests proving selection does not start, attach, bootstrap, advance, or
  bypass approval gates.
- If the canonical owner refuses the operation, render a bounded
  plain-English unavailable/refused state and emit the existing audit category.

## Constraints
- Read the actual repository state and CLAUDE.md before editing.
- Do not modify AGENTS.md or CLAUDE.md.
- Do not create a UI-only settings file, preference cache, recent-mode list, or
  hidden session state.
- Do not implement C5-C8 Start/Stop, automatic execution, or progress console.
- Do not add Git automation, network endpoints, or unrelated refactors.
- Do not fabricate or edit .agent-loop/codex-review.md.

## Required validation
- python -m unittest tests.test_desktop_app tests.test_documentation_consistency -q
- python -m unittest discover -s tests -q
- python scripts/agent_loop.py launch-desktop-app --controller-root . --headless

## Required output
Update .agent-loop/claude-summary.md using the required Claude Implementation
Summary format. Codex will re-review the resulting repository state.

