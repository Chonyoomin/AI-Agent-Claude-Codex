# Claude Code Fix Task

## Objective
Fix the remaining Phase 8C README drift so the public project overview does not
describe orchestrator-owned loop state as something recorded "by hand."

## Context
Codex reviewed the current Phase 8C implementation from repo state. The new
clean-clone section is in place, the focused README validation coverage passes,
and the full test suite passes. One Claude-owned README defect still remains:

1. `README.md` still says, immediately after the top-level `## Workflow`
   section, that:

   `.agent-loop/loop-state.json` records the active phase, task, cycle count,
   max cycles, and last verdict by hand.`

   That wording is no longer accurate relative to the shipped system. In the
   current repo state:
   - `.agent-loop/loop-state.json` is an orchestrator-owned runtime artifact
   - the shipped activator and orchestrator write and update it during normal
     operation
   - the manual-by-hand workflow is preserved only as a fallback in
     `## Running The Loop Manually (Phase 1)`, not as the default meaning of
     the top-level workflow / repository overview

   So the README still contains a stale Phase-1-era framing point that
   contradicts the shipped ownership/runtime model described elsewhere in the
   same file and in the Phase 8A/8B docs.

## Required fixes
- Correct the `README.md` sentence about `.agent-loop/loop-state.json` so it
  describes the shipped ownership/runtime model accurately instead of saying the
  file is recorded "by hand."
- Extend the focused documentation-consistency coverage so this specific README
  drift fails closed on regression. The current Phase 8C tests catch stale
  orchestrator-not-built wording and missing operator-doc pointers, but they do
  not currently fail if the README reintroduces this stale loop-state sentence.
- Update `.agent-loop/claude-summary.md` so it accurately describes the final
  fix and the exact validation commands run.

## Constraints
- Follow `CLAUDE.md`.
- Stay within Phase 8C scope.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not edit Codex-owned planning artifacts such as `.agent-loop/phase-plan.md`,
  `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, or
  `.agent-loop/codex-review.md`.
- Do not broaden into new runtime, planner, activator, evidence-collection,
  review-routing, checkpoint, continuation, memory, runtime-adapter, LangChain,
  or VS Code behavior.
- Preserve the shipped contracts and describe only behavior that already exists
  in the repo.
- Prefer the smallest safe documentation/test fix that makes the README
  contract-accurate relative to the current runtime and ownership model.

## Required output
After implementing the fix, update `.agent-loop/claude-summary.md` with the
required summary format and include the exact validation commands you ran.
