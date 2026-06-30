# Claude Code Fix Task

## Objective
Fix only the current Claude-owned Phase 10V review issues found by Codex.

## Context
The latest Phase 10V implementation was reviewed by Codex and received the
verdict `NEEDS_FIXES`.

Read:
- `CLAUDE.md`
- `.agent-loop/claude-prompt.md`
- `.agent-loop/codex-review.md`
- `scripts/agent_loop.py`
- `tests/test_desktop_rag_source_selection.py`
- `tests/test_desktop_app.py`
- `README.md`
- `docs/rag-source-selection-contract.md`
- `TASK.md`
- `.agent-loop/phase-plan.md`

## Required fixes
- Fix the Phase 10V descriptor-validation gap in
  `scripts/agent_loop.py`. The contract and docs say
  `path_canonical_rel` must be a POSIX-style relative path, but
  `_desktop_rag_source_selection_validate_descriptor(...)` does not
  enforce that invariant. Harden the validator so malformed future
  registry entries cannot point outside the controller root via
  absolute paths or parent-directory traversal, while preserving the
  current bounded repo-local source model.
- Add focused tests in `tests/test_desktop_rag_source_selection.py`
  that fail if `path_canonical_rel` is absolute, escapes the
  controller root, or otherwise violates the repo-relative POSIX-path
  contract described in `docs/rag-source-selection-contract.md`.
- Fix the Phase 10V README overstatement. The current README says the
  shipped five-entry registry lets tests exercise every closed branch,
  but the real shipped registry only guarantees coverage of every
  `source_type`; the `advisory_label_rule ==
  "refused_until_policy_update"` branch is covered only by a mutated
  test spec, not by a shipped registry entry. Update `README.md` so
  it accurately describes the registry and test coverage without
  overstating runtime or registry guarantees.
- Keep the fix inside the approved Phase 10V boundaries. Do not add
  actual RAG retrieval transport, chunking, ranking, embeddings,
  vector indexing, content reads, background watchers, network IO,
  subprocess dispatch, hidden persisted state, or any widening of the
  Phase 10I library-callable cap.

## Constraints
- Fix only the listed issues.
- Do not redesign later phases such as 10W or beyond.
- Do not introduce actual RAG runtime behavior, content retrieval,
  embeddings/indexing, new CLI/library surfaces outside the approved
  Phase 10V scope, or any hidden persisted control plane.
- Do not silently mutate in-flight `loop-state.json` approval state or
  other canonical controller fields outside approved canonical write
  paths.
- Do not add subprocess spawning, shell execution, network IO, or
  canonical artifact writes beyond the shipped bounded desktop/runtime
  contracts.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not edit `.agent-loop/loop-state.json` or
  `.agent-loop/orchestrator.log` by hand.
- Do not delete files unless explicitly required and approved.
- Preserve the original Phase 10V objective and the shipped Phase 10I
  / 10L / 10O / 10S / 10T / 10U boundary rules.
- Prefer minimal, targeted changes.

## Required output
After applying fixes, update `.agent-loop/claude-summary.md` using the required
Claude Implementation Summary format.
