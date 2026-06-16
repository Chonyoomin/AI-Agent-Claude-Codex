# Claude Code Fix Task

## Objective
Fix the remaining Phase 9A README drift so the active-phase references in the
public project overview no longer contradict the current 9A repo state.

## Context
Codex reviewed the current Phase 9A implementation from repo state. The new
autonomy contract doc exists, the focused documentation-consistency suite
passes, and the full test suite passes. One Claude-owned README defect still
remains:

1. `README.md` still contains stale Phase 8C active-state wording in the
   later historical summary prose. In particular, the deferred/future-work
   sentence still says:

   `post-Phase-8 roadmap work after the active Phase 8C final README alignment
   / clean-clone polish slice is complete`

   even though the same README already says Phase 9A is the current active
   sub-phase. This leaves the README internally contradictory about which phase
   is active.

The existing `ReadmePointsAtAutonomyContractDocTests` coverage only blocks the
specific stale sentence `"Phase 8C final README alignment and clean-clone
polish is now active"` and therefore missed this different stale-active-8C
phrase.

## Required fixes
- Correct the stale active-phase wording in `README.md` so every active-phase
  reference is consistent with Phase 9A being the current active sub-phase.
- Extend the focused documentation-consistency coverage so this broader stale
  Phase 8C active-state wording also fails closed on regression. The current
  README guard is too narrow.
- Update `.agent-loop/claude-summary.md` so it accurately describes the final
  fix and the exact validation commands run.

## Constraints
- Follow `CLAUDE.md`.
- Stay within Phase 9A scope.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not edit Codex-owned planning artifacts such as `.agent-loop/phase-plan.md`,
  `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, or
  `.agent-loop/codex-review.md`.
- Do not broaden into runtime implementation, planner work, activator changes,
  evidence-collection changes, checkpoint changes, continuation changes, or any
  other non-documentation Phase 9 runtime work.
- Preserve the shipped contracts and describe only behavior that already exists
  in the repo.
- Prefer the smallest safe README/test fix that removes the active-phase
  contradiction.

## Required output
After implementing the fix, update `.agent-loop/claude-summary.md` with the
required summary format and include the exact validation commands you ran.
