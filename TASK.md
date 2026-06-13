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

Phase 6J - Optional Context File Loading Initial Slice

## Phase Status

Phase 6I (Phase-Boundary Memory Distillation Initial Slice) is closed after Codex review approval and human progression. Phase 6J is now active as the next implementation slice for Phase 6 durable memory and optional context support. This sub-phase should implement the first declared optional-context file loading layer on top of the shipped 6B/6C/6D/6E/6F/6G/6H/6I memory, checkpoint, continuation, continuation-context, and distillation surfaces: load only explicitly declared in-repo context files into bounded advisory payloads while preserving canonical task/state precedence and still deferring repeated-failure synthesis, arbitrary repo ingestion, and broader framework-backed context behavior.

## Active Task

Implement the Phase 6 optional-context file loading foundation in code. This slice should build a narrow, auditable loader that validates an explicit declaration of in-repo context files and emits bounded advisory context payloads from those files, while preserving canonical task and loop-state precedence, existing Phase 5 approval-mode and strict-gate semantics, and still deferring repeated-failure synthesis, arbitrary repo ingestion, and broader optional-context expansion.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 6 / 6J as active
- `.agent-loop/phase-plan.md` records Phase 6I as closed history and contains a `## Phase 6J - Optional Context File Loading Initial Slice` section with `### Status` / `### Objective` / `### Definition of done` / `### Exclusions`
- `scripts/agent_loop.py` exposes a narrow optional-context file declaration and loading surface for active-phase use
- optional context loading accepts only explicitly declared in-repo files, reads bounded advisory excerpts, and records provenance to the source paths rather than silently ingesting arbitrary repo files
- optional context loading preserves canonical task/state precedence and refuses stale, contradictory, malformed, unreadable, out-of-bound, or unrecognized source inputs fail-closed
- optional context loading preserves the shipped Phase 5 approval-mode and strict-gate routing semantics and does not widen autonomy or bypass human gates
- no repeated-failure synthesis, arbitrary repo-file ingestion, or broader framework-backed context loading is enabled in this slice
- focused tests cover valid optional-context loading, declaration/path validation, excerpt bounding, malformed-or-unreadable input refusal, and preservation of canonical-artifact precedence
- `README.md` reflects that Phase 6J is active and that optional-context file loading is now the implementation focus

## Next-Phase Gate

Do not start the next 6x sub-phase after Phase 6J until:

- this Phase 6J slice receives `APPROVED_FOR_HUMAN_REVIEW`
- the human explicitly approves moving to the next sub-phase
- Codex updates `TASK.md`, `.agent-loop/current-task.md`, and `.agent-loop/current-phase.md` for the next sub-phase

## Out Of Scope For Current Phase

- any broader autonomy model than the current Phase 5D runtime behavior
- implementing repeated-failure memory synthesis in this slice
- implementing arbitrary repo-file ingestion, semantic retrieval, or broader optional context-file loading beyond the narrow declared-file loader needed for this slice
- changing current planner, activator, adapter, evidence-collection, review routing, or phase-start prompt-bootstrap behavior beyond the narrow optional-context loading implementation needed for future Phase 6 work
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
