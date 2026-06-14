# Claude Code Fix Task

## Objective
Fix the remaining Phase 6O canonical-state validation bug so the LangChain tool registry refuses malformed `loop-state.json` through the shipped validator path instead of returning partial canonical state to a support-layer consumer.

## Context
Codex re-reviewed the active Phase 6O implementation. The overall shape is in scope and the focused plus full suites pass, but one Claude-owned bug remains in the tool-registry read path.

`LangChainToolRegistry.invoke("read_loop_state")` currently returns `load_loop_state(state_path)` directly. That only parses JSON; it does not enforce `validate_loop_state(...)` or `check_contract_version(...)`. As a result, malformed-but-parseable canonical state can leak through the support layer instead of refusing fail-closed with the shipped halt vocabulary. A direct repro with a `.agent-loop/loop-state.json` containing only `{"phase": "P"}` returns `{"phase": "P"}` instead of halting.

## Required fixes
- Route the `read_loop_state` tool-registry path through the shipped structural validator chain, not just the JSON loader.
- Preserve the existing halt vocabulary by reusing the shipped `HaltError` behavior rather than inventing a new status.
- Add focused tests covering at least:
- `LangChainToolRegistry.invoke("read_loop_state")` on malformed-but-parseable loop-state
- the refusal status / reason shape for that case
- any updated success-path expectation if the implementation changes the returned object
- Update `.agent-loop/claude-summary.md` so it accurately describes the final post-fix behavior and the exact validation commands run.

## Constraints
- Follow `CLAUDE.md`.
- Stay within Phase 6O scope.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not broaden into real LangChain package wiring, CrewAI work, or runtime-control-plane changes.
- Preserve the existing read-only and default-off behavior of the 6O support layer.
- Prefer the smallest safe fix.

## Required output
After implementing the fix, update `.agent-loop/claude-summary.md` with the required summary format and include the exact validation commands you ran.
