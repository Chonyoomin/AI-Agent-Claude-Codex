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

<<<<<<< Updated upstream
Phase 4E - Optional Planner Adapter

## Phase Status

Phase 4D (Planner-Orchestrator Integration) is closed and approved for human review. Phase 4E is now active and introduces an optional planner-adapter seam so planner execution is no longer hard-wired to direct in-process calls. The default path must preserve today's local behavior, while making planner invocation routable through a dedicated adapter boundary for both the `plan` command path and the post-approval planner refresh path. Activation remains a separate human-approved step.

## Active Task

Introduce an optional planner adapter so planner execution goes through a dedicated adapter boundary instead of direct hard-wired calls, while preserving the current planner behavior by default. Route both the `plan` command path and the post-approval planner refresh path through that seam, keep the planner's write boundary unchanged, add focused tests for the adapterized behavior, and update `README.md`.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/phase-plan.md` identify Phase 4 / 4E as active
- `.agent-loop/phase-plan.md` marks Phase 4D complete and contains a Phase 4E section with `### Status` / `### Objective` / `### Definition of done` / `### Exclusions`
- `scripts/agent_loop.py` routes planner invocation through a dedicated planner-adapter seam rather than direct hard-wired calls
- the default planner adapter preserves today's local behavior for both the `plan` CLI path and the post-approval planner refresh path
- the planner's existing write boundary remains unchanged under adapterization: only `.agent-loop/proposed-phase.md` and `.agent-loop/planner.log` may be written by planner execution, and activation remains separate from planning
- planner refusals and planner exceptions remain surfaced with the same fail-closed behavior already required by Phases 4B through 4D
- `tests/` contains focused coverage for the adapterized `plan` path, the adapterized post-approval planner path, and proof that the adapter seam does not widen planner or activation writes
- `README.md` reflects the Phase 4E active status and documents the optional planner-adapter behavior
- no changes to `AGENTS.md`, `CLAUDE.md`, `scripts/run_checks.sh`, the Phase 2A Evidence Collection Contract, the Phase 3A Orchestrator Contract body, or the Phase 4A Planning Contract body

## Next-Phase Gate

Do not start the next 4x sub-phase after Phase 4E until:

- this Phase 4E slice receives `APPROVED_FOR_HUMAN_REVIEW`
=======
Phase 5A - Approval Modes Contract

## Phase Status

Phase 4F (Alternate Planner Adapter Selection) is closed and approved for human review. Phase 5A is now active as a Codex-owned contract-definition slice for approval modes. This sub-phase should define, before implementation, the contract for `strict`, `review`, and `autonomous` approval behavior: trigger points, required pauses, allowed automatic continuations, artifact/state implications, and failure / escalation rules. No approval-mode implementation is active yet.

## Active Task

Define the Approval Modes Contract in `.agent-loop/phase-plan.md` before any Phase 5 implementation work begins. Specify the behavior of `strict`, `review`, and `autonomous` modes, including which steps require human approval, when Codex may send implementation or fix prompts, when Claude completion should hand control back to Codex for review, how the loop should pause or continue, and how the orchestrator should represent mode-related runtime state without weakening existing safety rules.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 5 / 5A as active
- `.agent-loop/phase-plan.md` marks Phase 4 complete history and contains a `## Phase 5A - Approval Modes Contract` section with `### Status` / `### Objective` / `### Definition of done` / `### Exclusions`
- the new Phase 5A section defines the contract for `strict`, `review`, and `autonomous` approval modes before any code implementing them is written
- the contract specifies when Codex may send implementation prompts, when Codex may send fix prompts, when Claude completion should hand the loop back for review, and when the loop must wait for human approval
- the contract specifies how approval-mode state interacts with existing loop-state / review / fix-cycle behavior without weakening current safety guarantees
- the contract names refusal / halt / escalation cases for invalid or unsafe mode-driven continuations
- `README.md` reflects that Phase 5A is the active contract-definition slice and that approval modes are not implemented yet
- no changes to `scripts/agent_loop.py`, `scripts/run_checks.sh`, the Phase 2A Evidence Collection Contract, the Phase 3A Orchestrator Contract body, or the Phase 4A Planning Contract body

## Next-Phase Gate

Do not start the next 5x implementation sub-phase until:

- this Phase 5A slice receives `APPROVED_FOR_HUMAN_REVIEW`
>>>>>>> Stashed changes
- the human explicitly approves moving to the next sub-phase
- Codex updates `TASK.md`, `.agent-loop/current-task.md`, and `.agent-loop/current-phase.md` for the next sub-phase

## Out Of Scope For Current Phase

<<<<<<< Updated upstream
- planner-driven activation from inside the orchestrator (planning may refresh `.agent-loop/proposed-phase.md`, but approval + activation remain a separate human step)
- approval mode implementation (Phase 5)
=======
- approval mode implementation code in `scripts/agent_loop.py` or any other runtime script
- changing current planner, activator, adapter, or evidence-collection behavior beyond documenting how future approval modes must interact with them
>>>>>>> Stashed changes
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
- adding any project-wide CI suite to the repository beyond focused planner-adapter coverage
- Git automation (no commit, push, branch, stash, reset, checkout, tag)
