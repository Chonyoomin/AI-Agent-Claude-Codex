# Claude Code Fix Task

## Objective
Fix only the Claude-owned issues listed in `.agent-loop/codex-review.md` for Fix Phase A.

## Context
The latest Codex review for Fix Phase A returned `NEEDS_FIXES`. The active phase is `Fix Phase A - Automatic Local Claude/Codex Invocation Reliability`.

Read:
- `CLAUDE.md`
- `.agent-loop/claude-prompt.md`
- `.agent-loop/codex-review.md`
- `TASK.md`
- `.agent-loop/current-task.md`
- `.agent-loop/current-phase.md`
- `.agent-loop/phase-plan.md`
- `README.md`
- `docs/usage.md`
- `ROADMAP.md`

## Required fixes
- Issue 1 (`Owner: Claude`): implement the missing Fix Phase A adapter-contract surface.
  - Ship first-party wrapper support or wrapper templates for local Claude CLI and Codex CLI invocation.
  - Document the concrete operator-facing contract for `AGENT_LOOP_CLAUDE_CMD` and `AGENT_LOOP_CODEX_CMD`: expected cwd/repo-root behavior, which canonical artifact each command must produce, and what the orchestrator treats as success vs failure.
  - Update operator-facing docs so automatic local invocation is clearly separated from still-deferred fully autonomous PRD-to-product execution.
- Issue 2 (`Owner: Claude`): harden fresh-artifact validation in the subprocess adapters.
  - The adapter should require the target canonical artifact timestamp to advance relative to the pre-invocation file.
  - A successful wrapper exit that leaves the artifact missing, unchanged, or backdated/stale must fail closed.
- Issue 3 (`Owner: Claude`): add focused tests for the adapter contract.
  - Cover missing binaries or launch failures.
  - Cover successful exits that do not write the artifact.
  - Cover stale/backdated artifact writes being rejected.
  - Cover the intended repo-root / cwd assumption for configured wrappers.

## Constraints
- Fix only the listed issues.
- Do not redesign unrelated code.
- Do not expand the product scope beyond Fix Phase A.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not delete files unless explicitly required and approved.
- Preserve the existing manual-handoff fallback when adapter env vars are unset.
- Preserve the canonical-artifact model: `.agent-loop/claude-summary.md` and `.agent-loop/codex-review.md` remain the source of truth, not stdout parsing.
- Update tests if behavior changes.
- Prefer minimal, targeted changes.

## Required output
After applying fixes, update `.agent-loop/claude-summary.md` using the required Claude Implementation Summary format.
