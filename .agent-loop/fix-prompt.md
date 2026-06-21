# Claude Code Fix Task

## Phase
Phase 10 - Future Product Features (sub-phase: Phase 10A - External Workspace Controller Contract)

## Objective
Align the new Phase 10A external-workspace contract surfaces with the actual shipped Phase 9E artifact name so the contract does not teach a non-existent descriptor path.

## Context
Codex re-reviewed the current Phase 10A repo state and found one remaining documentation-contract mismatch:

1. The new external-workspace contract names the Phase 9E target-owned descriptor as `.agent-loop/long-run-loop.json`, and the new README Phase 10A paragraph repeats the same name. That path is not a shipped artifact. The actual Phase 9E descriptor path in the repo is `.agent-loop/long-run-continuation.json` (`LONG_RUN_CONTINUATION_OUTPUT_REL` in `scripts/agent_loop.py`), and the existing documentation-consistency tests already lock that real name in for Phase 9E. As written, the new Phase 10A contract teaches future implementers and operators to reason about the wrong canonical artifact name.

## Required fixes
- update the Phase 10A documentation surfaces so they use the real shipped Phase 9E descriptor path:
  - `docs/external-workspace-contract.md`
  - `README.md`
- add or adjust focused documentation-consistency coverage so this exact Phase 9E artifact-name mismatch would fail closed if it reappears
- preserve the Phase 10A scope:
  - documentation/contract only
  - no runtime implementation
  - no new CLI or Python behavior
  - no contract rewrites in `AGENTS.md` or `CLAUDE.md`
- keep the surrounding contract text intact unless a small supporting edit is required for internal consistency

## Constraints
- follow `CLAUDE.md`
- stay within Phase 10A scope
- do not modify `AGENTS.md` or `CLAUDE.md`
- prefer the smallest safe doc/test change that removes the wrong `.agent-loop/long-run-loop.json` artifact name

## Required output
After applying the fix, update `.agent-loop/claude-summary.md` in the required Claude Implementation Summary format and include focused validation showing the corrected Phase 9E artifact path is now used consistently.
