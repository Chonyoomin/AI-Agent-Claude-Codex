# Claude Code Fix Task

## Phase
Phase 9C - Orchestrator-Driven Prompt Handoff

## Objective
Fix the remaining Phase 9C operator-surface mismatch so the
`dispatch-prompt-handoff` CLI help text accurately describes the shipped runtime
behavior.

## Context
The Phase 9C runtime gap is fixed in code: `dispatch_prompt_handoff(...)` now
actually invokes `make_claude_adapter().invoke(...)` by default, records the
adapter outcome in `.agent-loop/prompt-handoff.json`, and the focused tests pass.

But the CLI help text for `dispatch-prompt-handoff` in
[`scripts/agent_loop.py`](scripts/agent_loop.py) is still stale. It currently
claims the command "Writes only the descriptor and a `prompt handoff:` audit-log
line", which is no longer true for the default path. The default path now
dispatches through the Claude adapter unless the operator opts out with
`--no-invoke`.

That means an operator reading `python scripts/agent_loop.py
dispatch-prompt-handoff --help` still gets pre-fix behavior described back to
them even though the runtime has changed.

## Required fixes
- update the `dispatch-prompt-handoff` argparse help text so it accurately
  describes the shipped default behavior:
  - the command dispatches the active canonical prompt through the Claude
    adapter by default
  - it writes `.agent-loop/prompt-handoff.json`
  - it records `prompt handoff:` audit lines
  - `--no-invoke` is the explicit descriptor-only / dry-run path
- keep the Phase 9C scope narrow; do not widen into Phase 9D autonomy
- preserve the existing runtime behavior exactly; this is an operator-surface
  and documentation-alignment fix, not a new behavior change
- add or update focused tests if needed so the operator-facing help surface is
  covered and cannot drift silently again

## Constraints
- follow `CLAUDE.md`
- stay within Phase 9C scope
- do not modify `AGENTS.md` or `CLAUDE.md`
- do not change the runtime semantics that were just fixed

## Required output
After applying the fix, update `.agent-loop/claude-summary.md` in the required
Claude Implementation Summary format and include the new validation results.
