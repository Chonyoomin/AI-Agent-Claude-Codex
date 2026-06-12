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

Phase 6H - Bounded Continuation Prompt Construction Initial Slice

## Phase Status

Phase 6G (Automatic Continuation Chaining Initial Slice) is closed after Codex review approval and human progression. Phase 6H is now active as the next implementation slice for Phase 6 durable memory. This sub-phase should implement the first bounded continuation-prompt construction layer on top of the shipped 6B/6C/6D/6E/6F/6G memory and checkpoint surfaces: construct resume-safe continuation prompt context from canonical task/state artifacts plus the active checkpoint, relevant evidence, and bounded durable memory, while still deferring phase-boundary memory distillation and broader optional-context behavior.

## Active Task

Implement the Phase 6 bounded continuation-prompt construction foundation in code. This slice should build a narrow, auditable continuation prompt/context surface from canonical task and loop-state artifacts, the active checkpoint, bounded evidence, and selectively retrieved durable memory, while preserving existing Phase 5 approval-mode and strict-gate semantics and still deferring broader memory distillation or optional-context expansion.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 6 / 6H as active
- `.agent-loop/phase-plan.md` records Phase 6G as closed history and contains a `## Phase 6H - Bounded Continuation Prompt Construction Initial Slice` section with `### Status` / `### Objective` / `### Definition of done` / `### Exclusions`
- `scripts/agent_loop.py` exposes a narrow continuation prompt/context construction surface for interrupted Claude or Codex work
- continuation prompt construction pulls from canonical task/state artifacts plus the active checkpoint, bounded evidence, and selectively retrieved durable memory rather than raw transcript history
- continuation prompt construction enforces bounded inclusion rules and refuses stale, contradictory, malformed, or unrecognized continuation inputs fail-closed
- continuation prompt construction preserves the shipped Phase 5 approval-mode and strict-gate routing semantics and does not widen autonomy or bypass human gates
- no phase-boundary memory distillation or broader optional-context loading is enabled in this slice
- focused tests cover valid continuation prompt construction, bounded evidence and memory inclusion, stale-or-contradictory checkpoint refusal, and preservation of canonical-artifact precedence
- `README.md` reflects that Phase 6H is active and that bounded continuation prompt construction is now the implementation focus

## Next-Phase Gate

Do not start the next 6x sub-phase after Phase 6H until:

- this Phase 6H slice receives `APPROVED_FOR_HUMAN_REVIEW`
- the human explicitly approves moving to the next sub-phase
- Codex updates `TASK.md`, `.agent-loop/current-task.md`, and `.agent-loop/current-phase.md` for the next sub-phase

## Out Of Scope For Current Phase

- any broader autonomy model than the current Phase 5D runtime behavior
- implementing phase-boundary memory distillation or repeated-failure memory synthesis beyond the narrow continuation prompt construction helpers needed for this slice
- implementing broader optional context-file loading or retrieval expansion beyond the narrow continuation prompt construction implementation needed for future Phase 6 work
- changing current planner, activator, adapter, evidence-collection, review routing, or phase-start prompt-bootstrap behavior beyond the narrow continuation prompt construction implementation needed for future Phase 6 work
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
