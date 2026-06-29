# Claude Code Task

## Phase
Phase 10R - Desktop App PRD Intake And Project Start Flow

## Objective
Implement Phase 10R for the agent loop. This slice should add the first desktop PRD-intake and project-start workflow so an operator can create or select a target project, attach a PRD or product brief, choose the target folder, and start a run without manually preparing prompt artifacts by hand.

## Context
Implement the Desktop App PRD Intake And Project Start Flow slice for the
agent loop. This slice should add the first desktop workflow for creating or
selecting a target project, attaching a PRD or product brief, choosing the
target folder, and starting a run without requiring the operator to manually
prepare prompt artifacts by hand.

## Required work
- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`,
  and `.agent-loop/loop-state.json` identify Phase 10 / 10R as active
- `.agent-loop/phase-plan.md` records Phase 10Q as closed history and contains
  a `## Phase 10R - Desktop App PRD Intake And Project Start Flow` section
  with concrete objective, done criteria, and exclusions
- the repository adds the first desktop workflow for creating or selecting a
  target project, attaching a PRD or product brief, choosing the target
  folder, and starting a run without requiring the operator to manually
  prepare prompt artifacts by hand
- the workflow maps back to canonical runtime state and existing bounded
  mutating surfaces rather than introducing a hidden UI-only state store or a
  parallel orchestration plane
- the phase preserves the shipped controller-vs-target boundary, no-auto-fill
  identity rules, approval semantics, canonical-artifact-first model, and
  existing CLI/runtime contracts instead of silently mutating in-flight loop
  state
- focused validation proves the PRD-intake and project-start flow is bounded,
  auditable, and does not widen into MCP runtime execution, RAG runtime,
  packaging, or controlled-concurrency work
- `README.md` reflects that Phase 10R is active and that desktop PRD intake
  and project start are now the implementation focus

## Constraints
- Follow `CLAUDE.md`.
- Stay within the current task scope.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not rewrite unrelated files.
- Do not delete files unless explicitly instructed.
- Prefer small, testable, reversible changes.
- Add or update tests when behavior changes.

Out of scope for this phase (from `TASK.md` and `phase-plan.md`):
- no MCP runtime integration, no tool-execution path, and no networked tool
  orchestration in this slice
- no hidden background control plane, no parallel config plane, and no bypass
  of the shipped CLI/library/runtime boundaries
- no silent mutation of in-flight loop-state approval_mode or other canonical
  fields outside explicit approved mutating surfaces
- no RAG, policy-pack, packaging, system-tray, or controlled-concurrency
  runtime work
- no automatic next-phase activation behavior that bypasses or rewrites the
  shipped Phase 4 planner / activation separation, or that replaces canonical
  prompt/review/checkpoint artifacts with transient runtime-only state
- no rewrite of current shipped behavior just to make future desktop or
  autonomy work easier
- no regression of the shipped Phase 5 review, strict, bounded autonomous,
  reconciliation, or prompt-bootstrap behavior
- no regression of the shipped Phase 6 memory, checkpoint, continuation,
  runtime-adapter, or LangChain support-layer behavior
- no contract rewrites in `AGENTS.md` or `CLAUDE.md`
- no change to the Phase 2A Evidence Collection Contract
- no change to the Phase 3A Orchestrator Contract body
- no change to the Phase 4A Planning Contract body
- no Git automation

## Required output
After implementation, write `.agent-loop/claude-summary.md` using the required Claude Implementation Summary format.
