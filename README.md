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

The instruction contract, prompt formats, review formats, task and phase ownership rules, and safety model are in place. Phase 1 (Manual File-Based Loop), Phase 2A (Evidence Collection Contract), Phase 2B (`scripts/run_checks.sh`), Phase 3A (Orchestrator Contract), Phase 3B (initial Orchestrator MVP slice), Phase 3C (automated fix-cycle handling), and Phase 3D (subprocess-driven Claude/Codex adapters with manual-handoff fallback) are all complete and approved by the human. The project is currently in **Phase 3E - End-to-End MVP Verification**: actually running `python scripts/agent_loop.py run` against the repository's real `.agent-loop/` workflow and documenting the live outcome rather than relying only on synthetic harnesses. Two bounded live runs have been executed under real OS conditions - one pure manual-handoff run that halted at the Claude adapter step, and one subprocess-Claude + manual-handoff-Codex run that exercised the subprocess adapter path, executed `bash scripts/run_checks.sh` to refresh all six evidence files, and halted at the Codex adapter step. Both halts persisted contract-correct `halted_input_missing` statuses into `loop-state.json` and appended HALT lines to `.agent-loop/orchestrator.log`. The success path (`APPROVED_FOR_HUMAN_REVIEW`) and the fix-cycle path are still covered only by the prior phases' synthetic harnesses because the `codex` CLI is not installed in this environment and the locally-installed `claude` CLI is deliberately not invoked recursively. No operational bug was revealed by the live runs; `scripts/agent_loop.py` is unchanged from Phase 3D.

What the orchestrator now does: load and structurally validate `.agent-loop/loop-state.json`; check the orchestrator's declared `contract_version` support; refuse to start a normal cycle from any status other than `awaiting_claude_implementation`; select the subprocess Claude adapter when `AGENT_LOOP_CLAUDE_CMD` is set (otherwise fall back to manual handoff); run the normal cycle (Claude adapter -> `bash scripts/run_checks.sh` -> Codex adapter -> verdict parse); on `APPROVED_FOR_HUMAN_REVIEW`, persist completion and stop for human approval; on `FAILED_REQUIRES_HUMAN`, persist halt and stop; on `NEEDS_FIXES`, record the verdict, enforce the `cycle_count >= max_cycles` threshold (halt with `halted_max_cycles_reached`; no auto-continue), validate `.agent-loop/fix-prompt.md`, increment `cycle_count` and set `status = claude_fixing`, drive a full fix cycle (Claude adapter on `fix-prompt.md` -> claude-summary validation -> evidence re-capture -> evidence validation -> Codex adapter for the fix-cycle review -> verdict parse), and re-enter the verdict loop with the new verdict. Fail-closed mtime checks on both adapters carry over to subprocess and fix-cycle paths; a stale unchanged artifact, a non-zero subprocess exit, or a missing CLI binary halts with `halted_input_missing`. A `KeyboardInterrupt` persists `halted_human_stop`. A `null` `codex_version` (because the Codex adapter cannot self-report) leaves the field null and writes the contract-required note to `.agent-loop/orchestrator.log`.

Deferred to later 3x sub-phases: approval modes (Phase 5), editor integration (Phase 7), Git automation, parsing of Claude / Codex CLI output formats inside the core loop (the Phase 3A contract forbids that), streaming subprocess output to a TTY, and the contract's "materially changed / narrowed" cycle-extension judgment (the orchestrator enforces the threshold but does not decide whether to extend it; raising `max_cycles` or activating a new sub-phase is an explicit Codex- or human-owned action).

### Running The Orchestrator

Prerequisites: Python 3 and Bash on `PATH`.

```text
python scripts/agent_loop.py check-state           # load + validate loop-state.json
python scripts/agent_loop.py validate-artifacts    # run all per-cycle validators
python scripts/agent_loop.py run                   # execute one normal cycle + any auto fix cycles
```

Adapter configuration (env vars; all optional):

- `AGENT_LOOP_CLAUDE_CMD` - shell command that invokes Claude Code on the active prompt; when set, the subprocess Claude adapter is used and the prompt file content is piped to stdin with `cwd` set to the repository root. When unset, the orchestrator falls back to the manual-handoff Claude adapter (the human drives Claude Code by hand).
- `AGENT_LOOP_CODEX_CMD` - shell command that invokes Codex against the captured evidence; same selection behavior.
- `AGENT_LOOP_CLAUDE_MODEL` - explicit string the orchestrator records as `claude_version` in `.agent-loop/loop-state.json`. When unset, the subprocess Claude adapter falls back to the first token of the command (e.g. `claude`) so the contract's "Claude adapter cannot resolve a model identifier" halt does not fire spuriously.
- `AGENT_LOOP_CODEX_MODEL` - explicit string the orchestrator records as `codex_version`. When unset, the subprocess Codex adapter returns `model_id = None`; the orchestrator leaves `codex_version` null and writes the contract-required note to `.agent-loop/orchestrator.log` rather than fabricating a value.

Without any of these env vars, `run` falls back entirely to manual handoff and will pause and prompt the human at each step (Claude implementation, optional fix-cycle Claude invocations, and each Codex review). The orchestrator never writes any file outside `.agent-loop/loop-state.json` and the optional `.agent-loop/orchestrator.log`. A `NEEDS_FIXES` verdict at or past `max_cycles` halts the loop with `halted_max_cycles_reached`; resuming requires an explicit Codex- or human-owned change (raise `max_cycles`, reset `cycle_count`, or activate a new sub-phase).

The orchestrator only starts a normal cycle when `.agent-loop/loop-state.json` has `status = "awaiting_claude_implementation"`. After any halt (`halted_*` status) or after a prior cycle parked the loop in `awaiting_codex_review` / `phase_complete_awaiting_human_approval`, `run` will refuse to start until a human (or Codex, as part of activating a new sub-phase) edits `status` back to `awaiting_claude_implementation`. This is the contract's fail-closed start-state gate; the orchestrator emits `halted_input_missing` with a reason that names the current status when it refuses.
