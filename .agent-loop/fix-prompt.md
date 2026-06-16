# Claude Code Fix Task

## Phase
Phase 9B - PRD Intake And Decomposition

## Objective
Fix the remaining Phase 9B write-boundary bug in the PRD intake surface so the new advisory intake artifact cannot overwrite canonical repo-state artifacts or the source input file via `--output` / `output_path`.

## Context
Codex review found that the Phase 9B implementation currently enforces only an
"inside the repo" boundary for output overrides, not a safe advisory-artifact
boundary. In [`scripts/agent_loop.py`](scripts/agent_loop.py), the CLI handler
resolves `--output` through `_resolve_prd_intake_path(...)`, which rejects
absolute paths and `..` escapes but still accepts protected in-repo targets
such as `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`,
`.agent-loop/phase-plan.md`, `.agent-loop/loop-state.json`, or even the source
input file itself. The library function `intake_and_decompose_prd(...)` then
writes directly to that caller-supplied path with no second write-boundary
check. That means a normal operator invocation like
`python scripts/agent_loop.py intake-prd --input prd.json --output TASK.md`
would overwrite a canonical planning artifact with advisory JSON, and
`--output prd.json` would overwrite the source input file after it is read.

This violates the shipped Phase 9B contract and README wording that the slice
writes a single advisory artifact (`.agent-loop/prd-intake.json` by default,
or a safe override) while preserving repo-artifact source-of-truth boundaries
and never mutating the source input file.

## Required fixes
- tighten the Phase 9B output write boundary so the advisory intake artifact can
  only be written to a safe advisory location under `.agent-loop/`
- refuse fail-closed when `--output` / `output_path` targets canonical planning
  artifacts, protected runtime-state artifacts, or the same path as the source
  input file
- enforce the same boundary in the library function, not only in the CLI
  wrapper, so direct Python callers cannot bypass the safety contract
- add focused tests proving:
  - CLI refusal when `--output TASK.md`
  - CLI refusal when `--output .agent-loop/loop-state.json`
  - CLI refusal when `--output` matches the source input path
  - direct `intake_and_decompose_prd(...)` refusal on the same classes of bad
    output targets
  - the normal `.agent-loop/prd-intake.json` path and safe in-scope advisory
    overrides still succeed
- update README wording only if needed to keep the shipped boundary description
  exact after the fix

## Constraints
- follow `CLAUDE.md`
- stay within Phase 9B scope only
- do not modify `AGENTS.md` or `CLAUDE.md`
- do not widen the slice into Phase 9C-9G behavior
- do not alter the Phase 4 planner / Phase 4C activator ownership boundary
- do not route this through Codex-owned planning artifacts
- prefer the smallest safe fix

## Required output
After applying the fix, update `.agent-loop/claude-summary.md` in the required
Claude Implementation Summary format and include the new validation results.
