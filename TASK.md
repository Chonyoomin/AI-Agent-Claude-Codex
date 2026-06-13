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

Phase 6K - Optional Context Prompt Integration Initial Slice

## Phase Status

Phase 6J (Optional Context File Loading Initial Slice) is closed after Codex review approval and human progression. Phase 6K is now active as the next implementation slice for Phase 6 durable memory and optional context support. This sub-phase should integrate the shipped 6J declared optional-context payload into prompt/context construction in a narrow, auditable way: consume only the existing bounded advisory payload, preserve canonical task/state/checkpoint precedence, keep optional context explicitly advisory, and still defer repeated-failure synthesis, arbitrary repo ingestion, and broader framework-backed context behavior.

## Active Task

Implement the Phase 6 optional-context prompt-integration foundation in code. This slice should connect the shipped declared optional-context payload to prompt/context construction through a narrow, auditable integration path that reads only the existing bounded .agent-loop/optional-context.json artifact, preserves canonical task and loop-state precedence, existing Phase 5 approval-mode and strict-gate semantics, and still defers repeated-failure synthesis, arbitrary repo ingestion, and broader optional-context expansion.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 6 / 6K as active
- `.agent-loop/phase-plan.md` records Phase 6J as closed history and contains a `## Phase 6K - Optional Context Prompt Integration Initial Slice` section with `### Status` / `### Objective` / `### Definition of done` / `### Exclusions`
- `scripts/agent_loop.py` exposes a narrow optional-context prompt/context integration surface for active-phase use
- prompt/context construction can consume the shipped `.agent-loop/optional-context.json` payload only when it is structurally valid, current-phase compatible, and explicitly advisory; malformed, contradictory, missing-required-field, unreadable, or unsupported payloads refuse fail-closed
- integrated optional context remains subordinate to canonical task / phase / loop-state / checkpoint artifacts and does not override Phase 5 approval-mode or strict-gate decisions
- integrated optional context remains explicitly bounded and provenance-carrying; the slice does not re-open raw repo files or silently expand beyond the shipped 6J payload
- no repeated-failure synthesis, arbitrary repo-file ingestion, or broader framework-backed context loading is enabled in this slice
- focused tests cover valid optional-context prompt/context integration, advisory precedence preservation, malformed-or-contradictory payload refusal, and bounded inclusion behavior
- `README.md` reflects that Phase 6K is active and that optional-context prompt integration is now the implementation focus

## Next-Phase Gate

Do not start the next 6x sub-phase after Phase 6K until:

- this Phase 6K slice receives `APPROVED_FOR_HUMAN_REVIEW`
- the human explicitly approves moving to the next sub-phase
- Codex updates `TASK.md`, `.agent-loop/current-task.md`, and `.agent-loop/current-phase.md` for the next sub-phase

## Out Of Scope For Current Phase

- any broader autonomy model than the current Phase 5D runtime behavior
- implementing repeated-failure memory synthesis in this slice
- implementing arbitrary repo-file ingestion, semantic retrieval, or broader optional context-file loading beyond the narrow 6J payload integration needed for this slice
- changing current planner, activator, adapter, evidence-collection, or review routing behavior beyond the narrow optional-context prompt/context integration needed for future Phase 6 work
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
