# Claude Code Fix Task

## Phase
Phase 10AI - Orchestration Graph And Performance View Initial Slice

## Objective
Finish the 10AI runtime so it actually materializes a bounded graph/icon
orchestration view, and fix the stale README vocabulary-count summary.

## Context
Codex reviewed the current 10AI implementation and found two Claude-owned issues
in the shipped runtime/docs. `.agent-loop/codex-review.md` is the source of
truth for the findings and severity.

## Required fixes
- Upgrade the shipped 10AI runtime from a flat text-only value dump to an actual
  bounded graph/icon-based orchestration view consistent with the 10AH contract
  and the 10AI phase objective.
- The runtime should materialize the node/edge/status model in a real runtime
  form, not just list the values in a `tk.Text` widget. Keep it bounded and
  canonical-artifact-first; do not add a hidden graph-state store or second
  controller.
- Add or tighten focused tests so a future regression back to a plain textual
  inspector would fail review.
- Fix the stale README line that still calls the visualization vocabulary
  "eleven-value" even though the shipped set is 15 values.

## Constraints
- Stay within Phase 10AI scope. Do not widen into downstream action dispatch,
  autonomous progression, or a new control plane.
- Do not modify `AGENTS.md` or `CLAUDE.md`.
- Do not invent a hidden UI-only graph state store, progress cache, layout
  cache, animation state store, or background watcher.
- Preserve the Phase 10I library-callable control cap and the Phase 10L/10M poll
  cadence boundaries.

## Required output
- Update `.agent-loop/claude-summary.md` with the concrete runtime/doc/test fixes
  and the validation you ran.
