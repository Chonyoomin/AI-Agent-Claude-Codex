# Claude Code Task

## Phase
Phase 6O - LangChain Support Layer

## Objective
Implement the LangChain support layer for Phase 6. This slice should add optional LangChain-based helpers only for prompt construction, selective retrieval, and tool abstraction layers while keeping the existing local orchestrator and the shipped Phase 6N LangGraph runtime mirror as the only runtime-control surfaces, preserving canonical repo-artifact precedence and avoiding any promotion of LangChain into a top-level orchestrator role.

## Context
Implement an optional LangChain-based support layer that can assist prompt
construction, selective retrieval, and tool abstraction without becoming the
top-level orchestrator. This slice should preserve the shipped local runtime as
the authoritative default control path, keep the shipped 6N LangGraph runtime
mirror subordinate and opt-in, preserve canonical repo-artifact precedence, and
refuse fail-closed on any attempt to let LangChain-managed state override
loop-state, checkpoints, memory, evidence, review artifacts, or phase/task
planning state.

## Required work
- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and
  `.agent-loop/loop-state.json` identify Phase 6 / 6O as active
- `.agent-loop/phase-plan.md` records Phase 6N as closed history and contains a
  `## Phase 6O - LangChain Support Layer` section with concrete objective, done
  criteria, and exclusions
- `scripts/agent_loop.py` exposes a narrow optional LangChain support-layer
  surface only for prompt construction, selective retrieval, and tool
  abstraction, not as the top-level orchestrator or runtime owner
- the LangChain support layer preserves canonical repo-artifact precedence over
  LangChain-managed state and refuses fail-closed when LangChain state
  contradicts canonical task, loop-state, checkpoint, memory, review, or
  evidence artifacts
- the LangChain support layer preserves the shipped halt/refusal vocabulary,
  approval-mode behavior, checkpoint/continuation handling, durable-memory
  boundaries, and audit-note expectations where it touches existing runtime
  surfaces
- the shipped local orchestrator remains the default runtime when no explicit
  support-layer selection is made, and the shipped 6N LangGraph runtime mirror
  remains opt-in and non-default
- focused tests cover support-layer activation boundaries, default-runtime
  preservation, canonical-precedence preservation, representative refusal
  behavior, and proof that LangChain does not become a top-level runtime
  controller
- `README.md` reflects that Phase 6O is active and that LangChain support-layer
  work is now the implementation focus

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
- no promotion of LangChain into the top-level orchestrator, runtime owner, or
  phase-transition controller
- no CrewAI evaluation or broader delegated-role multi-agent framework work in
  this slice
- no broader autonomy model than the shipped Phase 5D runtime behavior
- no change to the Phase 2A Evidence Collection Contract
- no change to the Phase 3A Orchestrator Contract body beyond the narrow
  support-layer integration needed here
- no change to the Phase 4A Planning Contract body
- no regression of the shipped Phase 5 review, strict, autonomous,
  reconciliation, or prompt-bootstrap runtime behavior
- no arbitrary repo-file ingestion, semantic retrieval expansion, or broader
  RAG/runtime behavior beyond the narrow LangChain support layer needed here
- no change to `AGENTS.md` or `CLAUDE.md`
- no Phase 7 editor integration
- no Git automation

## Required output
After implementation, write `.agent-loop/claude-summary.md` using the required Claude Implementation Summary format.
