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

Phase 5 - Approval Modes

## Active Sub-Phase

Phase 5B - Review Mode Initial Slice

## Phase Status

Phase 5A (Approval Modes Contract) is closed and approved for human review. Phase 5B is now active as the first implementation slice for Phase 5. This sub-phase should implement the `review` approval mode as the explicit default runtime behavior, add the first machine-readable Claude completion handoff signal, and keep `strict` and `autonomous` deferred. The goal is to make the current baseline loop behavior explicit in runtime state and artifacts without broadening autonomy yet.

## Active Task

Implement the initial Approval Modes runtime slice in `scripts/agent_loop.py` by adding explicit `review`-mode behavior and the first `.agent-loop/claude-done.json` handoff artifact. This slice should add `approval_mode` / `awaiting_human_for` runtime-state support, default new Phase 5+ runtime state to `review`, have Claude completion produce a machine-readable `ready_for_codex_review` signal tied to the current prompt or fix prompt, and preserve today's effective loop behavior for prompt issuance, review timing, evidence capture, verdict handling, and phase gating.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 5 / 5B as active
- `.agent-loop/phase-plan.md` marks Phase 5A complete history and contains a `## Phase 5B - Review Mode Initial Slice` section with `### Status` / `### Objective` / `### Definition of done` / `### Exclusions`
- `scripts/agent_loop.py` adds explicit `approval_mode` / `awaiting_human_for` runtime-state handling for the `review` mode path without changing the existing baseline safety behavior
- new or reset Phase 5+ runtime state defaults `approval_mode` to `review` and keeps `awaiting_human_for = null` when no human gate is active
- Claude completion produces `.agent-loop/claude-done.json` with the contract-required baseline fields and `status = ready_for_codex_review`, and stale completion signals are cleared / replaced on new prompt issuance
- the orchestrator uses the completion signal as a routing artifact only; Codex review still depends on `.agent-loop/claude-summary.md`, diff, and validation evidence
- `review` mode preserves the existing prompt, evidence-capture, review, fix-cycle, and phase-gating behavior rather than broadening autonomy
- focused tests cover the new runtime-state defaults, the `claude-done.json` handoff behavior, stale-signal protection, and non-regression of the current review-mode loop
- `README.md` reflects that Phase 5B is active and that only the `review` mode initial slice is implemented

## Next-Phase Gate

Do not start the next 5x sub-phase after Phase 5B until:

- this Phase 5B slice receives `APPROVED_FOR_HUMAN_REVIEW`
- the human explicitly approves moving to the next sub-phase
- Codex updates `TASK.md`, `.agent-loop/current-task.md`, and `.agent-loop/current-phase.md` for the next sub-phase

## Out Of Scope For Current Phase

- implementation of `strict` mode or `autonomous` mode runtime behavior
- changing current planner, activator, adapter, or evidence-collection behavior beyond the narrow `review`-mode runtime-state and Claude-completion handoff work
- durable memory, token-reset continuation, checkpoint-resume logic, and continuation chaining (Phase 6)
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
