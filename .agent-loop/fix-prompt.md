# Claude Code Fix Task

## Objective
Fix only the current Claude-owned Phase 10W review issues found by Codex.

## Context
The latest Phase 10W implementation was reviewed by Codex and received the
verdict `NEEDS_FIXES`.

Read:
- `CLAUDE.md`
- `.agent-loop/claude-prompt.md`
- `.agent-loop/codex-review.md`
- `scripts/agent_loop.py`
- `tests/test_desktop_rag_retrieval_controls.py`
- `README.md`
- `TASK.md`
- `.agent-loop/phase-plan.md`

## Required fixes
- Fix the Phase 10W desktop retrieval-eligibility mismatch in
  `scripts/agent_loop.py`. The desktop retrieval controls currently enable a
  source button without considering whether the operator has supplied a valid
  non-empty query, even though the real `run-local-rag-retrieval` runtime
  refuses `query_empty`. Make the desktop retrieval-controls surface and live
  `_refresh()` button enablement match the actual runtime contract so a button
  does not advertise a runnable path that the shipped runtime will immediately
  refuse.
- Add focused regression coverage in
  `tests/test_desktop_rag_retrieval_controls.py` for the query-sensitive
  eligibility behavior. The tests should fail if a source is marked
  `retrieval_eligible=True` or a retrieval button becomes enabled while the live
  query is empty or otherwise invalid for the actual retrieval runtime.
- Fix the Phase 10W refusal-vocabulary mismatch. Either make
  `retrieve_local_rag_excerpts(...)` actually emit `source_path_missing` on the
  missing-source path, or remove/adjust the enum and docs so the shipped refusal
  contract matches the real runtime exactly. Preserve a closed refusal
  vocabulary and add focused tests that anchor whichever behavior you keep.
- Update `README.md` so the 10W desktop retrieval-controls paragraph accurately
  describes the shipped eligibility and refusal behavior after the code fix.
- Keep the fix inside the approved Phase 10W boundaries. Do not add remote
  retrieval, vector databases, hosted services, background daemons/watchers,
  hidden persistence, or any widening of the Phase 10I library-callable cap.

## Constraints
- Fix only the listed issues.
- Do not redesign later phases such as 10X or beyond.
- Do not introduce remote retrieval transport, embeddings/vector indexing,
  hidden background ingestion, subprocess dispatch, network IO, or canonical
  artifact writes outside the shipped bounded Phase 10W contracts.
- Do not silently mutate in-flight `loop-state.json` approval state or other
  canonical controller fields outside approved canonical write paths.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not edit `.agent-loop/loop-state.json` or
  `.agent-loop/orchestrator.log` by hand.
- Do not delete files unless explicitly required and approved.
- Preserve the original Phase 10W objective and the shipped Phase 10I / 10L /
  10O / 10V boundary rules.
- Prefer minimal, targeted changes.

## Required output
After applying fixes, update `.agent-loop/claude-summary.md` using the required
Claude Implementation Summary format.
