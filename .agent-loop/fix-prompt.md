# Claude Code Fix Task

## Phase
Phase 9 - Fully Autonomous PRD-To-Product Mode (sub-phase: Phase 9F - Capacity-Halt Reprobe And Automatic Resume)

## Objective
Fix the remaining Phase 9F runtime gaps so the shipped capacity-halt surface is actually integrated into the autonomous runtime and performs a meaningful bounded availability re-probe instead of only exposing a standalone helper with an always-success default probe.

## Context
Codex re-reviewed the current Phase 9F repo state and found two remaining implementation bugs:

1. The new Phase 9F surface is not wired into any real autonomous runtime path yet. `reprobe_capacity_and_resume(...)` exists and the `run-capacity-reprobe` CLI handler can invoke it manually, but the shipped runtime still has no production path that plants `halted_capacity_unavailable` from a real Claude/Codex capacity event and no Phase 9E/9F continuation path that automatically consumes that halt. The code comments and Claude summary explicitly mark adapter-side capacity detection and Phase 9E integration as deferred, which conflicts with the active 9F task and done criteria that say this slice should extend the shipped Phase 9B/9C/9D/9E autonomous runtime and automatically resume the exact suspended step when capacity returns.

2. The shipped default capacity probe is a stub that always returns `True`. That means the default operator/runtime path does not actually re-probe availability at all: after the backoff delay it resumes unconditionally on the first attempt. This does not satisfy the phase contract’s “re-probe availability” requirement and turns the shipped CLI surface into “sleep then resume” rather than a real bounded capacity check.

## Required fixes
- integrate the Phase 9F capacity-halt seam into the actual autonomous runtime rather than leaving it as a manual standalone helper
- make the runtime able to enter and consume `halted_capacity_unavailable` from a real production path without relying on hand-edited loop-state
- preserve hard-stop boundaries:
  - no Phase 9G final human acceptance automation
  - no automatic next-phase activation
  - no rewrite of the Phase 4 planner / activation separation
- replace the always-true default probe behavior with a real shipped bounded probe path, or otherwise make the shipped default operator/runtime path refuse until a real probe surface is configured instead of pretending capacity is available
- keep canonical artifacts authoritative:
  - `loop-state.json`, checkpoints, retry-state, prompt/review artifacts, and logs remain the source of truth
  - `.agent-loop/capacity-retry-state.json` remains advisory retry metadata rather than a parallel control plane
- add focused tests proving:
  - a real runtime path can plant `halted_capacity_unavailable` from a production flow and later consume it through Phase 9F without manual loop-state editing
  - the long-run/autonomous path resumes through the new capacity-halt seam instead of stopping permanently at a generic halted state
  - the shipped default probe path does not silently auto-succeed without a real availability check
  - malformed or stale retry-state and bounded-attempt exhaustion still refuse fail-closed

## Constraints
- follow `CLAUDE.md`
- stay within Phase 9F scope
- do not modify `AGENTS.md` or `CLAUDE.md`
- do not rewrite unrelated phases or contracts
- prefer the smallest safe runtime change that closes the real 9F contract gaps

## Required output
After applying the fix, update `.agent-loop/claude-summary.md` in the required Claude Implementation Summary format and include the new validation results.
