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

Phase 6 - Durable Memory and Optional Context Layer

## Active Sub-Phase

Phase 6I - Phase-Boundary Memory Distillation Initial Slice

## Phase Status

Phase 6H (Bounded Continuation Prompt Construction Initial Slice) is closed after Codex review approval and human progression. Phase 6I is now active as the next implementation slice for Phase 6 durable memory. This sub-phase should implement the first phase-boundary memory distillation layer on top of the shipped 6B/6C/6D/6E/6F/6G/6H memory, checkpoint, continuation, and continuation-context surfaces: distill durable summary/decision/failure knowledge at approved phase boundaries into append-mostly memory artifacts while preserving canonical task/state precedence and still deferring broader optional-context behavior.

## Active Task

Implement the Phase 6 phase-boundary memory distillation foundation in code. This slice should build a narrow, auditable distillation surface that writes durable memory entries from approved phase-boundary artifacts and recent review/evidence context, while preserving canonical task and loop-state precedence, existing Phase 5 approval-mode and strict-gate semantics, and still deferring broader optional-context expansion.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 6 / 6I as active
- `.agent-loop/phase-plan.md` records Phase 6H as closed history and contains a `## Phase 6I - Phase-Boundary Memory Distillation Initial Slice` section with `### Status` / `### Objective` / `### Definition of done` / `### Exclusions`
- `scripts/agent_loop.py` exposes a narrow phase-boundary memory distillation surface for approved phase transitions and related human-approved boundary events
- memory distillation writes append-mostly durable memory entries derived from canonical artifacts, bounded review/evidence context, and existing Phase 6 memory surfaces rather than raw transcript dumps
- distillation preserves canonical task/state precedence and refuses stale, contradictory, malformed, or unrecognized source inputs fail-closed
- distillation preserves the shipped Phase 5 approval-mode and strict-gate routing semantics and does not widen autonomy or bypass human gates
- no broader optional-context loading is enabled in this slice
- focused tests cover valid phase-boundary distillation, bounded source selection, refusal on malformed or contradictory distillation inputs, and preservation of canonical-artifact precedence
- `README.md` reflects that Phase 6I is active and that phase-boundary memory distillation is now the implementation focus

## Next-Phase Gate

Do not start the next 6x sub-phase after Phase 6I until:

- this Phase 6I slice receives `APPROVED_FOR_HUMAN_REVIEW`
- the human explicitly approves moving to the next sub-phase
- Codex updates `TASK.md`, `.agent-loop/current-task.md`, and `.agent-loop/current-phase.md` for the next sub-phase

## Out Of Scope For Current Phase

- any broader autonomy model than the current Phase 5D runtime behavior
- implementing repeated-failure memory synthesis beyond the narrow phase-boundary distillation helpers needed for this slice
- implementing broader optional context-file loading or retrieval expansion beyond the narrow phase-boundary distillation implementation needed for future Phase 6 work
- changing current planner, activator, adapter, evidence-collection, review routing, or phase-start prompt-bootstrap behavior beyond the narrow phase-boundary distillation implementation needed for future Phase 6 work
- editor integration (Phase 7)
- MCP support (future)
- recursive invocation of the locally installed `claude` CLI
- fabrication of `.agent-loop/codex-review.md` content (Codex-owned)
- any change to the Phase 2A Evidence Collection Contract
- any change to the Phase 3A Orchestrator Contract body
- any change to the Phase 4A Planning Contract body
- any change to `scripts/run_checks.sh`
- any change to `AGENTS.md` or `CLAUDE.md`
- adding any project-wide CI suite to the repository beyond focused approval-mode coverage
- Git automation (no commit, push, branch, stash, reset, checkout, tag)
