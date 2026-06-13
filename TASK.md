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

Phase 6L - Repeated-Failure Memory Synthesis Initial Slice

## Phase Status

Phase 6K (Optional Context Prompt Integration Initial Slice) is closed after Codex review approval and human progression. Phase 6L is now active as the next implementation slice for Phase 6 durable memory and optional context support. This sub-phase should synthesize repeated-failure memory in a narrow, auditable way: distill recurring review/fix failure patterns into durable failure knowledge from bounded canonical artifacts and existing loop-state evidence, preserve canonical task/state/checkpoint precedence, keep failure memory explicitly advisory, and still defer arbitrary repo ingestion, broader framework-backed context behavior, and any widening of autonomy.

## Active Task

Implement the Phase 6 repeated-failure memory synthesis foundation in code. This slice should distill recurring review/fix failure patterns into durable advisory failure knowledge through a narrow, auditable synthesis path that reads only bounded canonical artifacts and existing loop-state context, preserves canonical task and loop-state precedence, existing Phase 5 approval-mode and strict-gate semantics, and still defers arbitrary repo ingestion, broader optional-context expansion, and wider autonomy.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 6 / 6L as active
- `.agent-loop/phase-plan.md` records Phase 6K as closed history and contains a `## Phase 6L - Repeated-Failure Memory Synthesis Initial Slice` section with `### Status` / `### Objective` / `### Definition of done` / `### Exclusions`
- `scripts/agent_loop.py` exposes a narrow repeated-failure memory synthesis surface for active-phase use
- repeated-failure synthesis reads only bounded canonical artifacts and existing loop-state context, and does not treat raw logs, arbitrary repo files, or whole transcripts as durable memory input
- synthesized failure memory remains subordinate to canonical task / phase / loop-state / checkpoint artifacts and does not override Phase 5 approval-mode or strict-gate decisions
- repeated-failure synthesis is explicitly advisory, provenance-carrying, and append-mostly within the existing memory model
- malformed, contradictory, unreadable, unsupported, out-of-bound, or ineligible repeated-failure synthesis inputs refuse fail-closed
- no arbitrary repo-file ingestion, broader optional-context loading, or broader framework-backed context behavior is enabled in this slice
- focused tests cover valid repeated-failure synthesis, refusal on malformed-or-contradictory inputs, bounded source selection, and canonical-precedence preservation
- `README.md` reflects that Phase 6L is active and that repeated-failure memory synthesis is now the implementation focus

## Next-Phase Gate

Do not start the next 6x sub-phase after Phase 6L until:

- this Phase 6L slice receives `APPROVED_FOR_HUMAN_REVIEW`
- the human explicitly approves moving to the next sub-phase
- Codex updates `TASK.md`, `.agent-loop/current-task.md`, and `.agent-loop/current-phase.md` for the next sub-phase

## Out Of Scope For Current Phase

- any broader autonomy model than the current Phase 5D runtime behavior
- implementing arbitrary repo-file ingestion, semantic retrieval, or broader optional context-file loading beyond the narrow repeated-failure synthesis needed for this slice
- changing current planner, activator, adapter, evidence-collection, or review routing behavior beyond the narrow repeated-failure memory synthesis needed for future Phase 6 work
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
