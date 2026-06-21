# Claude Code Fix Task

## Phase
Phase 10 - Future Product Features (sub-phase: Phase 10B - External Target Attach Record Contract)

## Objective
Fix the remaining Phase 10 contract-alignment issues by correcting the stale future-phase mapping in the Phase 10A baseline contract and adding focused test coverage so the Phase 10A and Phase 10B dependency map cannot drift again.

## Context
Codex re-reviewed the current Phase 10B repo state and found two Claude-owned follow-ups:

1. `docs/external-workspace-contract.md` still uses the pre-reslice Phase 10 dependency map. Its `## Status` section says `Phase 10B` is "external workspace bootstrap and attach flow" and `Phase 10C` is runtime control/UI. That is now wrong relative to the active plan and shipped canonical artifacts: Phase 10B is the attach-record contract, Phase 10C is the bootstrap contract, Phase 10D is the attach/detach runtime, Phase 10E is the bootstrap runtime, Phase 10F is target-side cycle dispatch, and Phase 10G is the external UI/dashboard/run-control slice.

2. `tests/test_documentation_consistency.py` does not currently assert that the older Phase 10A baseline contract uses the current resliced Phase 10 dependency map. Because that guard is missing, the stale 10A phase-ordering text survived even though the new 10B doc and README tests passed.

## Required fixes
- update `docs/external-workspace-contract.md` so its future Phase 10 dependency list matches the current canonical slicing:
  - Phase 10B = External Target Attach Record Contract
  - Phase 10C = External Target Bootstrap Contract
  - Phase 10D = External Workspace Attach/Detach Runtime Initial Slice
  - Phase 10E = External Target Bootstrap Runtime
  - Phase 10F = Target-Side Cycle Dispatch
  - Phase 10G = External UI / Dashboard / Run-Control
- keep the Phase 10A contract narrow:
  - this is still documentation/contract only
  - no runtime implementation
  - no new CLI or Python runtime behavior
  - no contract rewrites in `AGENTS.md` or `CLAUDE.md`
- add or adjust focused documentation-consistency tests so the stale Phase 10A future-phase mapping would fail closed if it reappears
- preserve the existing Phase 10B contract and README content unless a very small supporting edit is required for internal consistency

## Constraints
- follow `CLAUDE.md`
- stay within Phase 10B fix scope
- do not modify `AGENTS.md` or `CLAUDE.md`
- prefer the smallest safe doc/test change that removes the stale dependency map and locks the corrected one in

## Required output
After applying the fix, update `.agent-loop/claude-summary.md` in the required Claude Implementation Summary format and include focused validation showing the corrected Phase 10A dependency map and the new consistency coverage both pass.
