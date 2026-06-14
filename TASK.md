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

Phase 6N - Experimental LangGraph Runtime Mirror

## Phase Status

Phase 6M (Runtime Adapter Contract For Framework Evaluation) is closed after Codex review approval and human progression. Phase 6N is now active as the next Phase 6 slice. This sub-phase should add an opt-in experimental LangGraph-backed runtime mirror that exercises the Phase 6M adapter contract in code while preserving the shipped local orchestrator as the default runtime, keeping canonical repo artifacts authoritative, and refusing fail-closed on any divergence from the existing halt, checkpoint, memory, and approval-mode behavior.

## Active Task

Implement the first experimental LangGraph runtime mirror for Phase 6. This slice should add an opt-in framework-backed execution path that mirrors the shipped local orchestrator's state-machine behavior, halt/refusal vocabulary, checkpoint and continuation handling, durable-memory boundaries, audit signals, and approval-mode semantics while keeping the current local runtime as the default and preserving canonical repo-artifact precedence over any framework-managed state.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 6 / 6N as active
- `.agent-loop/phase-plan.md` records Phase 6M as closed history and contains a `## Phase 6N - Experimental LangGraph Runtime Mirror` section with `### Status` / `### Objective` / `### Definition of done` / `### Exclusions`
- `scripts/agent_loop.py` exposes an opt-in experimental LangGraph-backed runtime mirror or equivalent narrow alternate-runtime entry surface that is explicitly subordinate to the shipped local runtime and the Phase 6M adapter contract
- the experimental runtime preserves canonical repo-artifact truth for task / phase / loop-state / evidence / review / memory / checkpoint artifacts and refuses fail-closed on contradiction with framework-managed state
- the experimental runtime mirrors the shipped halt/refusal vocabulary, approval-mode behavior, checkpoint and continuation rules, durable-memory boundaries, and audit expectations closely enough to be evaluated against the local runtime
- the shipped local orchestrator remains the default runtime when no explicit alternate-runtime selection is provided
- focused tests cover runtime selection, default-runtime preservation, representative halt/refusal mirroring, checkpoint/continuation compatibility, and canonical-precedence preservation for the experimental mirror
- `README.md` reflects that Phase 6N is active and that experimental LangGraph runtime mirroring is now the implementation focus

## Next-Phase Gate

Do not start the next 6x sub-phase after Phase 6N until:

- this Phase 6N slice receives `APPROVED_FOR_HUMAN_REVIEW`
- the human explicitly approves moving to the next sub-phase
- Codex updates `TASK.md`, `.agent-loop/current-task.md`, and `.agent-loop/current-phase.md` for the next sub-phase

## Out Of Scope For Current Phase

- any broader autonomy model than the current Phase 5D runtime behavior
- implementing LangChain support-layer work, CrewAI evaluation, or broader multi-framework orchestration beyond the narrow LangGraph mirror needed for this slice
- changing current planner, activator, evidence-collection, review routing, checkpoint, continuation, memory, or prompt-integration semantics for the default local runtime beyond the narrow opt-in experimental mirror path
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
