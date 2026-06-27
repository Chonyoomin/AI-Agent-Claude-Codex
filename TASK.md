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

Phase 10Q - Desktop App Run Profiles And Approval Controls

## Phase Status

Phase 10P is complete and approved to advance. Phase 10Q is now active as the next mainline slice focused on adding a first-class desktop surface for selecting run profiles, approval mode, autonomy level, and PRD-to-completion vs bounded-run execution policies without introducing hidden UI-only state.

## Active Task

Implement Phase 10Q for the agent loop. This slice should add the first desktop run-profile and approval-controls surface so an operator can inspect and deliberately choose approval mode, autonomy level, PRD-to-completion vs bounded-run mode, and related execution policies through explicit controls that map back to canonical runtime state instead of hidden desktop-only settings.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 10 / 10Q as active
- `.agent-loop/phase-plan.md` records Phase 10P as closed history and contains a `## Phase 10Q - Desktop App Run Profiles And Approval Controls` section with concrete objective, done criteria, and exclusions
- the repository adds the first desktop run-profile and approval-controls surface that lets an operator inspect and deliberately choose approval mode, autonomy level, PRD-to-completion vs bounded-run execution policy, and related guardrails through explicit desktop controls
- the controls map back to canonical runtime state or clearly bounded existing mutating surfaces rather than introducing hidden UI-only settings or a parallel configuration plane
- the phase preserves the shipped controller-vs-target boundary, no-auto-fill identity rules, approval semantics, canonical-artifact-first model, and existing CLI/runtime contracts instead of silently mutating in-flight loop state
- focused validation proves the run-profile and approval-controls surface is bounded, auditable, and does not widen into PRD intake, MCP runtime execution, RAG runtime, packaging, or controlled-concurrency work

## Next-Phase Gate

Do not widen the desktop app beyond run profiles and approval controls until:

- Phase 10Q receives `APPROVED_FOR_HUMAN_REVIEW`
- the human approves the desktop run-profile and approval-controls slice
- any PRD intake, MCP runtime, RAG runtime, policy-pack, packaging, or controlled-concurrency work is activated through its own later phase instead of being folded into this slice

## Out Of Scope For Current Phase

- any PRD intake flow, MCP runtime integration, tool execution path, or networked tool orchestration beyond the approved Phase 10Q run-profile and approval-controls surface
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
- adding any project-wide CI suite beyond focused validation for the desktop run-profile and approval-controls surfaces
- Git automation (no commit, push, branch, stash, reset, checkout, tag)
