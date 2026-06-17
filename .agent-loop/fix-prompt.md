# Claude Code Fix Task

## Phase
Phase 9D - Autonomous Internal Review/Fix Loop

## Objective
Fix the remaining Phase 9D runtime gaps so the autonomous internal review/fix
loop actually behaves like a bounded autonomous continuation by default and
refuses stale or mismatched Phase 9C handoff descriptors instead of accepting
any non-empty file.

## Context
Codex re-reviewed the Phase 9D implementation from current repo state and found
two remaining runtime bugs:

1. The loop's default `max_inner_cycles = 1` does not complete one full
   autonomous review/fix continuation on the common `NEEDS_FIXES` path. The
   implementation performs one Codex review, dispatches one Claude fix prompt,
   then exits because the `for i in range(inner_cap)` loop is exhausted. With
   the shipped default, the command stops immediately after the first fix
   dispatch instead of autonomously reviewing the result of that fix. That means
   the default path does not satisfy the slice's claimed bounded autonomous
   continuation behavior.

2. Phase 9D only checks that `.agent-loop/prompt-handoff.json` exists and is
   non-empty. It does not validate the descriptor's signal version or confirm
   that the handoff matches the active loop-state phase / sub-phase / task /
   cycle context. A stale or hand-edited Phase 9C descriptor can therefore be
   consumed as if it were the current handoff, which weakens the canonical
   artifact routing contract Phase 9D claims to preserve.

## Required fixes
- make the default autonomous path complete a meaningful bounded review/fix
  continuation on the common `NEEDS_FIXES` path rather than stopping
  immediately after the first fix dispatch
- keep the Phase 9D scope narrow:
  - no Phase 9E automatic next-phase activation
  - no Phase 9F capacity re-probe
  - no Phase 9G final acceptance automation
- validate the Phase 9C handoff descriptor structurally before entering Phase
  9D:
  - require the expected signal version
  - require the active phase / sub-phase alignment with loop-state
  - require the task / cycle context to be consistent enough that stale
    descriptors are refused fail-closed
- preserve the existing canonical artifact model and ownership boundaries
- add focused tests proving:
  - the default 9D path does not stop prematurely after the first
    `NEEDS_FIXES` dispatch
  - stale or mismatched handoff descriptors are refused
  - the valid current-descriptor path still succeeds

## Constraints
- follow `CLAUDE.md`
- stay within Phase 9D scope
- do not modify `AGENTS.md` or `CLAUDE.md`
- do not widen into automatic next-phase activation or broader Phase 9E+ work
- prefer the smallest safe runtime fix that resolves the two bugs

## Required output
After applying the fix, update `.agent-loop/claude-summary.md` in the required
Claude Implementation Summary format and include the new validation results.
