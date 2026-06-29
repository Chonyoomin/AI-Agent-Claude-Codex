# TASK.md

## Human Objective

Build the Agentic AI Coding Loop project from start to finish as a phase-gated local orchestration system where:

- Codex plans the work, updates task state, reviews implementation, and generates fix prompts
- Claude Code implements only the active phase
- the local orchestrator captures evidence and enforces loop state
- each phase stops for human approval before the next phase begins
- the system never auto-commits or auto-pushes

## Project Intent

The goal is to let a human provide the desired outcome once, then have the Codex and Claude loop carry the project forward phase by phase with review, fixes, and human gating between phases.

## Active Phase

Phase 10 - Future Product Features

## Active Sub-Phase

Phase 10R - Desktop App PRD Intake And Project Start Flow

## Phase Status

Phase 10Q is complete and approved to advance. Phase 10R is now active as the next mainline slice focused on adding the first desktop workflow for creating or selecting a target project, attaching a PRD or product brief, choosing the target folder, and starting a run without manual prompt-artifact preparation.

## Active Task

Implement Phase 10R for the agent loop. This slice should add the first desktop PRD-intake and project-start workflow so an operator can create or select a target project, attach a PRD or product brief, choose the target folder, and start a run without manually preparing prompt artifacts by hand.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 10 / 10R as active
- `.agent-loop/phase-plan.md` records Phase 10Q as closed history and contains a `## Phase 10R - Desktop App PRD Intake And Project Start Flow` section with concrete objective, done criteria, and exclusions
- the repository adds the first desktop workflow for creating or selecting a target project, attaching a PRD or product brief, choosing the target folder, and starting a run without requiring the operator to manually prepare prompt artifacts by hand
- the workflow maps back to canonical runtime state and existing bounded mutating surfaces rather than introducing a hidden UI-only state store or a parallel orchestration plane
- the phase preserves the shipped controller-vs-target boundary, no-auto-fill identity rules, approval semantics, canonical-artifact-first model, and existing CLI/runtime contracts instead of silently mutating in-flight loop state
- focused validation proves the PRD-intake and project-start flow is bounded, auditable, and does not widen into MCP runtime execution, RAG runtime, packaging, or controlled-concurrency work

## Next-Phase Gate

Do not widen the desktop app beyond PRD intake and project start flow until:

- Phase 10R receives `APPROVED_FOR_HUMAN_REVIEW`
- the human approves the desktop PRD-intake and project-start slice
- any MCP runtime, RAG runtime, policy-pack, packaging, or controlled-concurrency work is activated through its own later phase instead of being folded into this slice

## Out Of Scope For Current Phase

- any MCP runtime integration, tool execution path, or networked tool orchestration beyond the approved Phase 10R PRD-intake and project-start surface
- any hidden background control plane or second orchestrator that bypasses the shipped Python runtime
- any automatic next-phase activation behavior that bypasses or rewrites the shipped Phase 4 planner / activation separation
- any claim that fully autonomous PRD-to-product execution is already solved
- any external-workspace target dispatch beyond the shipped attach/bootstrap/runtime surfaces, concurrent Codex/Claude overlap execution, MCP runtime implementation, RAG layer, or model-policy extensibility work
- any rewrite of current shipped behavior just to make future autonomy work easier
- rewriting contracts in `AGENTS.md` or `CLAUDE.md`
- inventing unreviewable autonomous behavior that the repo does not currently ship just to simplify the implementation
- collapsing later Phase 10 PRD intake, MCP runtime, RAG, policy-pack, packaging, or concurrency work into this slice
- implementation of end-to-end fully autonomous PRD-to-product execution
- fabrication of `.agent-loop/codex-review.md` content (Codex-owned)
- any change to the Phase 2A Evidence Collection Contract
- any change to the Phase 3A Orchestrator Contract body
- any change to the Phase 4A Planning Contract body
- any change to `scripts/run_checks.sh`
- adding any project-wide CI suite beyond focused validation for the desktop PRD-intake and project-start surfaces
- Git automation (no commit, push, branch, stash, reset, checkout, tag)
