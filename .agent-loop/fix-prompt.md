# Claude Code Fix Task

## Objective
Fix only the current Claude-owned Phase 10P review issues found by Codex.

## Context
The latest Phase 10P implementation was reviewed by Codex and received the
verdict `NEEDS_FIXES`.

Read:
- `CLAUDE.md`
- `.agent-loop/claude-prompt.md`
- `.agent-loop/codex-review.md`
- `scripts/agent_loop.py`
- `tests/test_desktop_setup.py`
- `tests/test_desktop_app.py`
- `README.md`
- `docs/desktop-app-contract.md`

## Required fixes
- Integrate the new Phase 10P desktop setup/onboarding surface into the shipped
  desktop app runtime instead of leaving it only as a separate CLI reporter.
  The current `build_desktop_setup_view(...)` / `render_desktop_setup_text(...)`
  / `cmd_view_desktop_setup(...)` surface exists, but `assemble_desktop_app_view(...)`
  and `render_desktop_app_text(...)` still only expose the older Phase 10H /
  10I / 10K views. Update the desktop app runtime so Phase 10P actually ships
  a desktop-app onboarding surface consistent with the phase objective, while
  preserving the existing non-mutation boundaries and the bounded desktop-app
  contract.
- Fix adapter onboarding so an adapter is not reported as fully `ok` merely
  because `AGENT_LOOP_CLAUDE_CMD` or `AGENT_LOOP_CODEX_CMD` is non-empty.
  Add bounded validation that distinguishes a truly resolvable/configured local
  adapter command from a junk or non-runnable command string, without widening
  into subprocess execution, shell evaluation, network IO, or hidden config
  writes. The setup surface should not claim automatic local invocation is
  configured when the command cannot realistically be invoked.
- Add or update focused tests for both fixes:
  - desktop app runtime/view coverage proving the setup surface is included in
    the shipped desktop app surface
  - adapter validation coverage proving invalid/non-resolvable command values
    do not surface as `ok`
- Update `README.md` as needed so the 10P description matches the shipped
  implementation after the fixes.

## Constraints
- Fix only the listed issues.
- Do not redesign later phases such as 10Q, 10R, 10T, or 10U.
- Do not introduce a hidden persisted config plane.
- Do not add subprocess spawning, shell execution, network IO, or canonical
  artifact writes to satisfy adapter validation.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not edit `.agent-loop/loop-state.json` or `.agent-loop/orchestrator.log`
  by hand.
- Do not delete files unless explicitly required and approved.
- Preserve the original Phase 10P objective and existing Phase 10L/10M/10N
  non-mutation boundaries.
- Prefer minimal, targeted changes.

## Required output
After applying fixes, update `.agent-loop/claude-summary.md` using the required
Claude Implementation Summary format.
