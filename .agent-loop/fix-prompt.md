# Claude Code Fix Task

## Objective
Bring Phase 6N into alignment with the active contract by turning the experimental LangGraph runtime mirror into a real opt-in runtime path and by adding the missing default-off persisted runtime-selection mechanism under `.agent-loop/`.

## Context
Codex re-reviewed the active Phase 6N repo state and found two Claude-owned contract gaps.

1. The current implementation adds `runtime-adapter-eval`, `resolve_runtime_adapter_id(...)`, `LocalRuntimeAdapter`, `LangGraphExperimentalRuntimeAdapter`, and `make_runtime_adapter(...)`, but the main runtime entry points still bypass that seam. `cmd_run(...)` still calls `run_normal_cycle(repo_root)` directly, `cmd_resume(...)` still dispatches only between `run_token_exhaustion_resume(repo_root)` and `run_strict_resume(repo_root)`, and `cmd_auto_continue(...)` still calls `run_auto_continue(repo_root)` directly. The 6N phase contract says the repo should expose an opt-in alternate runtime path, not only an evaluation command.

2. The active contract inherited from Phase 6M still requires the alternate runtime to remain behind a default-off persisted flag/config surface in `.agent-loop/`. The current code only reads `--runtime` and `AGENT_LOOP_RUNTIME`, and both `README.md` and `.agent-loop/claude-summary.md` explicitly say no runtime-config file exists yet.

## Required fixes
- Add a narrow real runtime-selection path for Phase 6N. The safest shape is to wire runtime resolution into the actual operator entry points that matter for this slice while keeping `local` as the default and keeping all existing behavior byte-equivalent when no alternate runtime is selected.
- Preserve the current local runtime as the default path. An unset selection must still run the shipped local orchestrator exactly as before.
- Make the alternate path genuinely opt-in and runtime-backed rather than review-only. If the mirror is still intentionally evaluation-only, then the phase/task/README/summary must be narrowed to match that weaker contract instead of overstating the shipped behavior. Prefer fixing the implementation rather than weakening the contract unless the code constraints make that impossible.
- Implement the missing persisted default-off runtime-selection mechanism under `.agent-loop/` required by the 6M contract. This can be a small runtime-config artifact or equivalent canonical file, but it must be repo-local, default off, validated fail-closed, and documented.
- Update focused tests to cover the real selected runtime path and the persisted config/feature-flag behavior, including default preservation and refusal behavior.
- Refresh `README.md` and `.agent-loop/claude-summary.md` so they describe the post-fix behavior exactly and do not claim deferred behavior as shipped.

## Constraints
- Follow `CLAUDE.md`.
- Stay within Phase 6N scope.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not weaken canonical artifact precedence, halt vocabulary, approval semantics, checkpoint handling, or durable-memory boundaries.
- Keep the local runtime as the default when no explicit persisted or operator selection is made.
- Prefer minimal, testable changes over broad refactors.

## Required output
After implementing the fixes, update `.agent-loop/claude-summary.md` with the required summary format and include the exact validation commands you ran.
