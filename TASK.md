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

Phase 5D - Autonomous Mode Initial Slice

## Phase Status

Phase 5C (Strict Mode Pauses) is closed and approved for human review. Phase 5D is now active as the third implementation slice for Phase 5. This sub-phase should implement the first narrow `autonomous` runtime continuation behavior defined in the Phase 5A contract while preserving the shipped `review` and `strict` behavior and without weakening any existing hard safety stops. The goal is to allow bounded automatic continuation through implementation, review, and fix cycles where the contract already allows it, while still requiring human approval for phase progression, hard-stop resolution, and any action that would broaden autonomy beyond the established safety model.

## Active Task

Implement the first `autonomous` approval-mode runtime behavior in `scripts/agent_loop.py`. This slice should add a narrow autonomous continuation path that can automatically proceed through normal implementation, Codex review handoff, and bounded fix cycles where the current contracts already allow auto-continuation; preserve the shipped `review` and `strict` behavior; fail closed on any hard-stop, malformed-artifact, or unresolved escalation path; and keep human approval mandatory before phase progression and any future Git action.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 5 / 5D as active
- `.agent-loop/phase-plan.md` marks Phase 5C complete history and contains a `## Phase 5D - Autonomous Mode Initial Slice` section with `### Status` / `### Objective` / `### Definition of done` / `### Exclusions`
- `scripts/agent_loop.py` implements a narrow `autonomous` runtime continuation path that can automatically proceed where the existing contracts already allow auto-continuation, without weakening hard safety stops
- `autonomous` mode automatically continues through normal implementation handoff, post-Claude/pre-review handoff, and bounded `NEEDS_FIXES` fix cycles only while the existing threshold and halt rules remain satisfied
- `strict` and `review` behavior remain unchanged in effect
- hard stops (`FAILED_REQUIRES_HUMAN`, malformed artifacts, `halted_*` states, unresolved threshold escalation) still fail closed and still require human intervention where the current contracts require it
- `.agent-loop/claude-done.json` continues to be a routing/timing artifact only and integrates correctly with the autonomous continuation path
- focused tests cover autonomous normal-cycle continuation, autonomous bounded fix-cycle continuation, refusal on hard-stop conditions, and non-regression of the shipped `review` and `strict` paths
- `README.md` reflects that Phase 5D is active and that `autonomous` is now the implementation focus

## Next-Phase Gate

Do not start the next 5x sub-phase after Phase 5D until:

- this Phase 5D slice receives `APPROVED_FOR_HUMAN_REVIEW`
- the human explicitly approves moving to the next sub-phase
- Codex updates `TASK.md`, `.agent-loop/current-task.md`, and `.agent-loop/current-phase.md` for the next sub-phase

## Out Of Scope For Current Phase

- any broader autonomy model than the narrow initial `autonomous` continuation path for existing allowed loop steps
- changing current planner, activator, adapter, or evidence-collection behavior beyond the narrow autonomous-mode continuation logic and its interaction with the shipped `review` and `strict` runtime state
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
