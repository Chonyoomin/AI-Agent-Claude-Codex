# Agentic AI Coding Loop

Agentic AI Coding Loop is a local orchestration project for running a controlled, phase-gated build-review-fix workflow between Codex and Claude Code.

Codex acts as the planner, task-state manager, reviewer, validator, and fix-prompt generator. Claude Code acts as the implementation agent for the active phase only. A local orchestrator manages prompts, artifacts, validation logs, and loop state. A human approves movement between phases and separately approves any eventual commit.

## Goal

Reduce manual copy/paste between Codex and Claude Code while keeping the workflow auditable, scoped, and safe.

## MVP

The first version focuses on a small local loop:

- read a human-provided objective
- let Codex maintain `TASK.md` and active phase state
- generate a focused Claude implementation prompt
- let Claude implement the requested phase
- capture Claude's structured summary
- capture `git diff` and `git status`
- run validation commands and save logs
- let Codex review the prompt, summary, diff, and logs
- generate a fix prompt if needed
- stop after each approved phase until the human starts the next one

## Workflow

This section describes the intended end-to-end workflow once the orchestrator (Phase 3) is built. Until then, the same loop runs by hand - see `## Running The Loop Manually (Phase 1)` below.

1. Human provides the project objective or updates the desired outcome.
2. Codex updates `TASK.md`, `.agent-loop/current-task.md`, and `.agent-loop/current-phase.md` for the active phase.
3. Codex writes `.agent-loop/claude-prompt.md`.
4. Claude Code implements only the active phase and writes `.agent-loop/claude-summary.md`.
5. The orchestrator captures diff, status, and validation logs.
6. Codex writes `.agent-loop/codex-review.md` with one verdict:
   - `APPROVED_FOR_HUMAN_REVIEW`
   - `NEEDS_FIXES`
   - `FAILED_REQUIRES_HUMAN`
7. If fixes are required, Codex writes `.agent-loop/fix-prompt.md`.
8. Claude applies targeted fixes within the same phase.
9. The loop repeats until the phase is approved, escalated, or reaches max cycles.
10. When a phase is approved, the system stops until the human starts the next phase.
11. The system never commits without separate human approval.

## Repository Files

Top-level project files:

- `README.md`: public project overview
- `AGENTS.md`: operating rules, review standards, and artifact formats
- `CLAUDE.md`: Claude Code implementation contract
- `ROADMAP.md`: phased delivery plan
- `TASK.md`: Codex-maintained task and phase record derived from the human objective

Loop artifacts:

```text
.agent-loop/
  phase-plan.md
  current-task.md
  current-phase.md
  claude-prompt.md
  claude-summary.md
  git-diff.patch
  git-status.log
  test-output.log
  lint-output.log
  typecheck-output.log
  build-output.log
  codex-review.md
  fix-prompt.md
  loop-state.json
```

## Safety

- no auto-commit
- no auto-push
- no hidden validation failures
- no trusting summary text over actual diffs and logs
- no phase advancement without human approval
- no final commit without human approval

## Ownership Rules

- Claude Code is the default implementation editor for code, tests, scripts, configuration, and other non-state repository files during an active phase
- Codex should normally route implementation changes to Claude Code and edit directly only when the issue has been intentionally assigned to Codex
- planning-state hygiene issues should be treated as Codex-resolved and fixed directly by Codex
- `.agent-loop/loop-state.json`, `.agent-loop/orchestrator.log`, and the evidence files are owned by the orchestrator or the scripts that generate them; they must not be fabricated by hand outside explicitly assigned implementation work
- if ownership is ambiguous, the change should be routed to Claude Code or escalated for human clarification rather than guessed
- when continuing an active implementation phase, Codex should first summarize the remaining implementation gap, classify it as Claude-resolved or Codex-resolved, and if it is Claude-resolved write the precise Claude Code task prompt before implementation proceeds
- when the human starts a new phase or sub-phase, Codex should first provide a rundown of what will be implemented, split the work into Codex-resolved and Claude-resolved responsibilities, send the Claude-resolved portion as a precise Claude Code task prompt, and then perform only the Codex-resolved portion directly

## Running The Loop Manually (Phase 1)

While the orchestrator is not yet built, the loop runs by hand against the artifact formats defined in `AGENTS.md`. One full manual cycle:

1. Codex updates `TASK.md`, `.agent-loop/current-task.md`, and `.agent-loop/current-phase.md` for the active phase.
2. Codex writes the implementation prompt to `.agent-loop/claude-prompt.md` using the required Claude task format.
3. A human pastes that prompt into Claude Code.
4. Claude Code implements only the active phase and writes `.agent-loop/claude-summary.md` using the required Claude implementation summary format.
5. A human captures evidence into `.agent-loop/`:
   - `git diff > .agent-loop/git-diff.patch`
   - `git status > .agent-loop/git-status.log`
   - test, lint, typecheck, and build output to `.agent-loop/test-output.log`, `.agent-loop/lint-output.log`, `.agent-loop/typecheck-output.log`, `.agent-loop/build-output.log` (or record "Not run" explicitly).
6. A human pastes the prompt, summary, diff, and logs into Codex.
7. Codex writes `.agent-loop/codex-review.md` with exactly one verdict: `APPROVED_FOR_HUMAN_REVIEW`, `NEEDS_FIXES`, or `FAILED_REQUIRES_HUMAN`.
8. If the verdict is `NEEDS_FIXES`, Codex writes `.agent-loop/fix-prompt.md` and the cycle repeats from step 3 within `max_cycles`.
9. The cycle stops for human approval before any commit, and again before the next phase begins.

`.agent-loop/loop-state.json` records the active phase, task, cycle count, max cycles, and last verdict by hand.

## Current Status

The instruction contract, prompt formats, review formats, task and phase ownership rules, and safety model are in place. Phase 1 (Manual File-Based Loop), Phase 2A (Evidence Collection Contract), Phase 2B (`scripts/run_checks.sh`), Phase 3 (Scripted Orchestrator MVP, delivered as sub-phases 3A through 3E), Phase 4A (Planning Contract), Phase 4B (Planner Initial Slice; the `plan` subcommand), Phase 4C (Planner Activation Writes; the `activate` subcommand), Phase 4D (Planner-Orchestrator Integration; the contained post-approval planner refresh), Phase 4E (Planner Adapter Seam; routing both planner call sites through `make_planner_adapter()`), Phase 4F (Planner Adapter Selection; adding one alternate adapter path while preserving the planner write boundary), and Phase 5A (Approval Modes Contract) are complete; the historical sub-phase record is preserved in `.agent-loop/phase-plan.md`. The project is currently in **Phase 5B - Review Mode Initial Slice**: the first implementation slice for approval modes, making `review` the explicit default runtime mode, adding the first machine-readable `.agent-loop/claude-done.json` handoff artifact, and preserving the current baseline loop behavior while deferring `strict` and `autonomous` runtime branching.

The operator flow across Phase 4B + Phase 4C is:

1. Run `python scripts/agent_loop.py plan` to generate `.agent-loop/proposed-phase.md`. The planner enforces every Phase 4A refusal condition (unresolved `NEEDS_FIXES`, `FAILED_REQUIRES_HUMAN`, any `halted_*` status, orchestrator-in-flight statuses, `cycle_count >= max_cycles` on `NEEDS_FIXES`, stale evidence, unreadable evidence headers, prior approved proposal carrying `APPROVED_FOR_ACTIVATION`, malformed `loop-state.json`) and the bounded-scope rules (max 10 files, max 1 contract revision, testable Definition-of-done bullet, no vague Objective language, cycle-size estimate <= 3 without justification, no `active-in-flight` / `pending` dependency, no label collision against historical sub-phases, no `APPROVED_FOR_ACTIVATION` token authored by the planner itself, `## Exclusions` enumerating later 4x / 5+ sub-phases). The planner writes only `.agent-loop/proposed-phase.md` and a `note:`-style line in `.agent-loop/planner.log`.
2. A human reviews the proposal and, if accepted, appends a `## Approval` section to `.agent-loop/proposed-phase.md`. The approval section must contain the literal `APPROVED_FOR_ACTIVATION` token on its own line within the section AND must reference the proposal's `## Label` text. Token forgery (extra words on the line, alternate capitalization, surrounding characters) and stale-label approvals are refused at activation time.
3. Run `python scripts/agent_loop.py activate` to consume the approved proposal. The activator parses the proposal, verifies the approval requirements exactly, refuses cleanly on every failure mode (missing `## Approval` section, malformed token, label mismatch, missing/unreadable proposal, missing/malformed `loop-state.json`, empty required-proposal-section bodies), and on success performs ONLY the Phase 4A activation writes: rewriting `TASK.md`'s `## Active Phase` / `## Active Sub-Phase` / `## Phase Status` / `## Active Task` / `## Phase Outcome Required Now` / `## Next-Phase Gate` / `## Out Of Scope For Current Phase` (preserving `## Human Objective` and `## Project Intent` verbatim); rewriting `.agent-loop/current-task.md` and `.agent-loop/current-phase.md`; updating `.agent-loop/phase-plan.md`'s `## Active Phase` line, closing the previously-active sub-phase's `### Status` opening line as a transition note, and APPENDING a new sub-phase section that mirrors the activated proposal; resetting `.agent-loop/loop-state.json` to `status = awaiting_claude_implementation`, `cycle_count = 0`, `last_verdict = null`, `last_verdict_phase = null` with `phase` / `sub_phase` / `task` set from the approved proposal and `max_cycles` / `contract_version` / `claude_version` / `codex_version` / `orchestrator_version` preserved per the Phase 3A write-ownership rules; and appending a `note:`-style approval-source line (file path, mtime, literal approval line) to `.agent-loop/planner.log`. The activator exits 0 on success and 2 on any refusal; refusals never partially write any activation file.
4. Phase 4D integration (shipped): after the orchestrator persists a terminal `APPROVED_FOR_HUMAN_REVIEW` verdict in `_handle_verdict_loop`, it invokes the standalone planner exactly once to refresh `.agent-loop/proposed-phase.md`, then logs a single `note:`-style line to `.agent-loop/orchestrator.log` recording the planner's exit code. The hook is fully contained: a planner refusal (exit 2) is logged but does not convert the already-approved cycle into a halt, and any unexpected exception from planner code is caught and logged as a `note:` line rather than allowed to crash or halt the cycle. The orchestrator still returns 0 after the terminal approval in all of those cases. The hook never auto-activates a proposal and never widens the planner's write boundary (only `.agent-loop/proposed-phase.md` and `.agent-loop/planner.log` may be written by the planner call); approval and activation remain the separate, human-controlled `activate` step described above.

Phase 4E adds a planner-adapter seam. Both the `plan` path (step 1) and the post-approval planner refresh (step 4) now dispatch planner execution through `make_planner_adapter().run(...)` instead of calling the planner in-process directly. The default adapter (`LocalPlannerAdapter`) runs the same in-process planner, so behavior, refusal handling, the exception-containment guarantees on the post-approval path, and the planner's write boundary (`.agent-loop/proposed-phase.md` and `.agent-loop/planner.log` only) are all unchanged; the seam exists so a later slice can supply an alternate planner adapter without touching the call sites. The adapter is purely a dispatch boundary: it never widens the planner write boundary and never activates a proposal. Activation stays the separate, human-controlled `activate` step - planning (proposal generation and refresh) and activation remain distinct.

Focused tests live in:
- `tests/test_planner.py` covering the Phase 4A refusal paths, bounded-scope validation, and proposal-generation success path
- `tests/test_planner_activation.py` covering the activation success path, approval-signal refusals, required-input refusals, and activation rollback behavior
- `tests/test_planner_integration.py` covering the Phase 4D post-approval hook: a successful planner invocation after terminal approval, a planner-refusal path that still leaves the orchestrator returning 0, an unexpected-planner-exception path that is logged and still leaves the orchestrator returning 0, and a proof that the integration path performs no activation-owned writes
- `tests/test_planner_adapter.py` covering the Phase 4E adapter seam: the default factory returns the in-process `LocalPlannerAdapter`, the adapter delegates to `run_planner` and preserves the success behavior, the `plan` path and the post-approval refresh both dispatch through the seam, the post-approval path still contains an adapter exception, and the adapterized `plan` path performs no activation-owned writes and does not touch `loop-state.json`
- `tests/test_planner_adapter_selection.py` covering the Phase 4F adapter-selection behavior: local fallback selection, alternate adapter selection, planner-boundary enforcement with rollback on out-of-bound writes, and the continued separation between planning and activation

Deferred to later phases generally: additional approval-modes implementation beyond the current 5B `review`-mode slice, optional context and tool layer (Phase 6), editor integration (Phase 7), and documentation / project polish (Phase 8). Phase 4D was the first slice that intentionally extended the Phase 3 orchestrator surface with the contained post-approval planner hook; Phases 4E and 4F completed the planner-adapter seam and one alternate adapter path while keeping the planner write boundary and the separate human-controlled approval/activation steps unchanged.
