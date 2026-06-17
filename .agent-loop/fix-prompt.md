# Claude Code Fix Task

## Phase
Phase 9C - Orchestrator-Driven Prompt Handoff

## Objective
Fix the remaining Phase 9C implementation gap so the slice actually removes
manual prompt transfer by dispatching the active Claude handoff path, instead of
only writing an advisory handoff descriptor.

## Context
Codex review found that the current Phase 9C implementation stops at writing
`.agent-loop/prompt-handoff.json` plus a `prompt handoff:` audit note. The
library function [`dispatch_prompt_handoff(...)`](scripts/agent_loop.py) writes
an advisory descriptor, and the CLI handler
[`cmd_dispatch_prompt_handoff(...)`](scripts/agent_loop.py) only prints the
descriptor path. The code's own block comment explicitly says it "never invokes
the Claude adapter directly" and that actual adapter invocation still lives in
the shipped cycle drivers.

That means the slice still requires manual copy/paste or some outside actor to
take the prompt and give it to Claude. In other words, the shipped behavior does
NOT yet satisfy the Phase 9C objective:

- "let the orchestrator dispatch the active Codex/Claude prompt handoff from
  canonical prompt artifacts"
- "remove manual prompt transfer"

Right now it only records which prompt WOULD be handed off.

## Required fixes
- extend Phase 9C so the orchestrator actually dispatches the active Claude
  prompt handoff from the canonical prompt artifact rather than only emitting an
  advisory descriptor
- keep the canonical prompt artifacts on disk as the source of truth; do not
  replace them with transient runtime-only state
- preserve the shipped ownership boundary:
  - no changes to the Phase 4 planner / activation separation
  - no widening into autonomous review/fix continuation (Phase 9D)
  - no automatic next-phase activation (Phase 9D / 9E)
- preserve the shipped Phase 5 approval semantics and Phase 6 continuation /
  checkpoint behavior
- keep the handoff auditable from repo artifacts and logs
- add focused tests proving:
  - the real handoff path reaches the Claude adapter or adapter seam
  - the dispatched prompt comes from the correct canonical prompt file for both
    implementation and fix modes
  - missing or malformed prompt artifacts still refuse cleanly
  - the handoff audit trail remains on disk
  - the implementation does not regress the existing review / strict / bounded
    autonomous behavior

## Constraints
- follow `CLAUDE.md`
- stay within Phase 9C scope
- do not modify `AGENTS.md` or `CLAUDE.md`
- do not collapse the handoff layer into autonomous review/fix or cross-phase
  execution
- prefer the smallest safe runtime fix that makes the slice satisfy its actual
  objective

## Required output
After applying the fix, update `.agent-loop/claude-summary.md` in the required
Claude Implementation Summary format and include the new validation results.
