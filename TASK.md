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

Phase 6O - LangChain Support Layer

## Phase Status

Phase 6N (Experimental LangGraph Runtime Mirror) is closed after Codex review approval and human progression. Phase 6O is now active as the next Phase 6 slice. This sub-phase should add optional LangChain-based support only for prompt construction, selective retrieval, and tool abstraction layers while preserving the shipped local orchestrator and the 6N runtime-adapter seam as the authoritative top-level runtime surfaces.

## Active Task

Implement the LangChain support layer for Phase 6. This slice should add optional LangChain-based helpers only for prompt construction, selective retrieval, and tool abstraction layers while keeping the existing local orchestrator and the shipped Phase 6N LangGraph runtime mirror as the only runtime-control surfaces, preserving canonical repo-artifact precedence and avoiding any promotion of LangChain into a top-level orchestrator role.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 6 / 6O as active
- `.agent-loop/phase-plan.md` records Phase 6N as closed history and contains a `## Phase 6O - LangChain Support Layer` section with `### Status` / `### Objective` / `### Definition of done` / `### Exclusions`
- `scripts/agent_loop.py` exposes a narrow optional LangChain support layer only for prompt construction, selective retrieval, and tool abstraction surfaces, without promoting LangChain to the top-level orchestrator
- the LangChain support layer preserves canonical repo-artifact truth for task / phase / loop-state / evidence / review / memory / checkpoint artifacts and remains subordinate to the shipped local runtime plus the shipped 6N runtime-adapter seam
- the LangChain support layer preserves the shipped halt/refusal vocabulary, approval-mode behavior, checkpoint and continuation rules, durable-memory boundaries, and audit expectations where it touches existing Phase 6 surfaces
- the shipped local orchestrator remains the default runtime and LangChain remains optional support-only behavior when no explicit support-layer selection is provided
- focused tests cover support-layer selection or activation boundaries, canonical-precedence preservation, refusal behavior, and proof that LangChain does not become a top-level runtime controller
- `README.md` reflects that Phase 6O is active and that LangChain support-layer work is now the implementation focus

## Next-Phase Gate

Do not start the next 6x sub-phase after Phase 6O until:

- this Phase 6O slice receives `APPROVED_FOR_HUMAN_REVIEW`
- the human explicitly approves moving to the next sub-phase
- Codex updates `TASK.md`, `.agent-loop/current-task.md`, and `.agent-loop/current-phase.md` for the next sub-phase

## Out Of Scope For Current Phase

- any broader autonomy model than the current Phase 5D runtime behavior
- promoting LangChain into the top-level orchestrator, runtime owner, or phase-transition controller
- CrewAI evaluation or broader multi-framework orchestration beyond the narrow LangChain support layer needed for this slice
- changing current planner, activator, evidence-collection, review routing, checkpoint, continuation, memory, or prompt-integration semantics for the default local runtime beyond the narrow optional LangChain support path
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
