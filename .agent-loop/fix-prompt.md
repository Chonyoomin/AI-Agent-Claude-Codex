# Claude Code Fix Task

## Phase
Phase 10 - Future Product Features (sub-phase: Phase 10C - External Workspace Bootstrap Contract)

## Objective
Fix the remaining Phase 10C contract-alignment issues by correcting the cross-contract Phase 10C title drift and tightening the README wording so it does not overstate bootstrap's long-term write ownership.

## Context
Codex re-reviewed the current Phase 10C repo state and found two Claude-owned follow-ups:

1. Cross-contract title drift: older Phase 10 documents still refer to Phase 10C as `External Target Bootstrap Contract`, while the active canonical phase title is `External Workspace Bootstrap Contract`. This drift currently appears in:
   - `docs/external-workspace-contract.md`
   - `docs/external-target-attach-record-contract.md`
   The active task artifacts, phase plan, roadmap, README, and new Phase 10C doc already use `External Workspace Bootstrap Contract`. The layered contract stack should use one canonical Phase 10C title everywhere.

2. README overstatement: the new Phase 10C paragraph in `README.md` says the five canonical artifacts may be written by bootstrap "and ONLY by bootstrap". That overstates the contract. The Phase 10C contract constrains what the bootstrap surface may write, but those same target-side canonical artifacts are later rewritten by normal target-side flows such as the Phase 4C activator and later runtime behavior. The README should describe the bootstrap write boundary accurately without implying bootstrap is the only runtime that may ever touch those files.

## Required fixes
- update the stale Phase 10C title references so the layered contract stack uses the same canonical sub-phase title everywhere:
  - `docs/external-workspace-contract.md`
  - `docs/external-target-attach-record-contract.md`
- update the Phase 10C README paragraph so it says bootstrap may write exactly the five canonical artifacts during bootstrap, without claiming bootstrap is the only runtime that may ever write them afterward
- add or adjust focused documentation-consistency coverage so both regressions would fail closed if they reappear:
  - stale `External Target Bootstrap Contract` references where the canonical title should now be `External Workspace Bootstrap Contract`
  - the misleading README wording that overstates bootstrap's long-term write ownership
- preserve Phase 10C scope:
  - documentation/contract only
  - no runtime implementation
  - no new CLI or Python behavior
  - no contract rewrites in `AGENTS.md` or `CLAUDE.md`

## Constraints
- follow `CLAUDE.md`
- stay within Phase 10C fix scope
- do not modify `AGENTS.md` or `CLAUDE.md`
- prefer the smallest safe doc/test change that removes the drift and locks the corrected wording in

## Required output
After applying the fix, update `.agent-loop/claude-summary.md` in the required Claude Implementation Summary format and include focused validation showing the corrected Phase 10C title alignment and README wording both pass with the new consistency coverage.
