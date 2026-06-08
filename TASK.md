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

Phase 5E - Post-Review Artifact Reconciliation

## Phase Status

Phase 5D (Autonomous Mode Initial Slice) is closed and approved for human review. Phase 5E is now active as the fourth implementation slice for Phase 5. This sub-phase should implement post-review artifact reconciliation so Codex-owned artifact issues are corrected automatically after review, Claude-owned issues are synchronized into `.agent-loop/fix-prompt.md`, and the markdown/state artifact set remains coherent before the loop proceeds. The goal is to reduce recurring drift between review output, fix prompts, phase-state artifacts, and public status documentation without weakening ownership boundaries or allowing silent edits to Claude-owned implementation files.

## Active Task

Implement post-review artifact reconciliation in `scripts/agent_loop.py`. This slice should classify review findings into Codex-owned vs Claude-owned follow-up, automatically correct supported Codex-owned markdown/state/prompt/review artifact issues, regenerate `.agent-loop/fix-prompt.md` from Claude-owned findings, and refuse/stop when reconciliation would require ambiguous routing or would touch Claude-owned implementation work.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 5 / 5E as active
- `.agent-loop/phase-plan.md` marks Phase 5D complete history and contains a `## Phase 5E - Post-Review Artifact Reconciliation` section with `### Status` / `### Objective` / `### Definition of done` / `### Exclusions`
- `scripts/agent_loop.py` implements post-review artifact reconciliation for `NEEDS_FIXES` and other review outcomes where Codex-owned artifacts need direct correction
- supported Codex-owned follow-up may automatically update coherent markdown/state/prompt/review artifacts without touching Claude-owned implementation files
- Claude-owned findings are synchronized into `.agent-loop/fix-prompt.md` in the required format, derived directly from the current Codex review findings
- reconciliation refuses/halts when ownership is ambiguous, when a requested Codex-owned action is unsupported, or when the requested correction would overwrite Claude-owned implementation work
- the shipped `review`, `strict`, and `autonomous` runtime behavior from Phases 5B, 5C, and 5D remain unchanged in effect
- focused tests cover mixed-owner review findings, supported Codex-owned artifact auto-fixes, generated Claude fix prompts, refusal on unsupported/ambiguous reconciliation, and non-regression of the shipped approval-mode paths
- `README.md` reflects that Phase 5E is active and that post-review artifact reconciliation is now the implementation focus

## Next-Phase Gate

Do not start the next 5x sub-phase after Phase 5E until:

- this Phase 5E slice receives `APPROVED_FOR_HUMAN_REVIEW`
- the human explicitly approves moving to the next sub-phase
- Codex updates `TASK.md`, `.agent-loop/current-task.md`, and `.agent-loop/current-phase.md` for the next sub-phase

## Out Of Scope For Current Phase

- any broader autonomy model than the current Phase 5D runtime behavior
- changing current planner, activator, adapter, or evidence-collection behavior beyond the narrow post-review reconciliation logic and its interaction with the shipped approval-mode runtime state
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
