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

Phase 6G - Automatic Continuation Chaining Initial Slice

## Phase Status

Phase 6F (Token Exhaustion Continuation Initial Slice) is closed after Codex review approval and human progression. Phase 6G is now active as the next implementation slice for Phase 6 durable memory. This sub-phase should implement the first automatic continuation-chaining runtime on top of the shipped token-exhaustion continuation layer: automatically continue from a valid token-exhaustion checkpoint within bounded policy, preserve existing Phase 5 approval-mode and strict-gate semantics, and still defer phase-boundary memory distillation and broader optional-context behavior.

## Active Task

Implement the Phase 6 automatic continuation-chaining foundation in code. This slice should automatically continue from eligible token-exhaustion interruptions using the shipped checkpoint continuation state, enforce bounded continuation attempts and fail-closed validation, preserve existing Phase 5 approval-mode and strict-gate semantics, and still defer broader memory distillation or optional-context expansion.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 6 / 6G as active
- `.agent-loop/phase-plan.md` records Phase 6F as closed history and contains a `## Phase 6G - Automatic Continuation Chaining Initial Slice` section with `### Status` / `### Objective` / `### Definition of done` / `### Exclusions`
- the implementation can automatically continue from eligible token-exhaustion interruptions without requiring a separate manual `resume` invocation for each hop
- automatic continuation chaining consumes the shipped checkpoint continuation state and remains bounded by continuation budget and explicit refusal conditions
- continuation chaining preserves the shipped Phase 5 approval-mode and strict-gate routing semantics and does not widen autonomy or bypass human gates
- stale, contradictory, malformed, unrecognized, or budget-exhausted continuation checkpoints still refuse fail-closed
- no phase-boundary memory distillation or broader optional-context loading is enabled in this slice
- focused tests cover valid automatic continuation chaining, bounded multi-hop continuation, exhausted-budget refusal, unsupported-stage refusal, and preservation of canonical-artifact precedence
- `README.md` reflects that Phase 6G is active and that automatic continuation chaining is now the implementation focus

## Next-Phase Gate

Do not start the next 6x sub-phase after Phase 6G until:

- this Phase 6G slice receives `APPROVED_FOR_HUMAN_REVIEW`
- the human explicitly approves moving to the next sub-phase
- Codex updates `TASK.md`, `.agent-loop/current-task.md`, and `.agent-loop/current-phase.md` for the next sub-phase

## Out Of Scope For Current Phase

- any broader autonomy model than the current Phase 5D runtime behavior
- implementing phase-boundary memory distillation or repeated-failure memory synthesis beyond the narrow automatic continuation-chaining helpers needed for this slice
- implementing broader optional context-file loading or retrieval expansion beyond the narrow automatic continuation-chaining implementation needed for future Phase 6 work
- changing current planner, activator, adapter, evidence-collection, review routing, or phase-start prompt-bootstrap behavior beyond the narrow continuation-chaining implementation needed for future Phase 6 work
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
