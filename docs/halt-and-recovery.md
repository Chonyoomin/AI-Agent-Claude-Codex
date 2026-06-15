# Halt and Recovery Playbook

This playbook lists every operator-visible halt status the orchestrator
persists today and the matching recovery path. It mirrors the
`STATUS_RECOVERY_HINTS` map in `scripts/agent_loop.py`; that map is the
source of truth, this doc is the operator-facing reference.

For the architectural context see `docs/architecture.md`. For the
per-mode approval contract see `docs/approval-modes.md`. For the safety
boundaries see `docs/safety-rules.md`.

## How to use this playbook

1. Run `python scripts/agent_loop.py status` to see the active
   `status`, `awaiting_human_for`, and a one-line recovery hint.
2. Find the matching section below. The "Recovery" subsection lists
   the specific command(s) or manual steps that move the cycle
   forward.
3. If the printed hint disagrees with this doc, trust the hint -
   `STATUS_RECOVERY_HINTS` is canonical and may have been updated
   without this doc being rerendered. Surface the drift.

## In-flight cycle states

These statuses indicate the orchestrator is mid-cycle between adapter
handoffs. An operator typically observes them only when the loop is
actually running; if you see one in a stale repo (no orchestrator
process is alive) the cycle was interrupted.

### `claude_implementing`

**Meaning.** The Claude implementation adapter is running for the
current cycle.

**Recovery.** Inspect with
`python scripts/agent_loop.py check-state` and
`python scripts/agent_loop.py inspect-artifacts`; the next handoff is
`bash scripts/run_checks.sh` followed by Codex review. If the
underlying Claude adapter process crashed, the cycle can be re-driven
by re-running `python scripts/agent_loop.py run` once the operator has
cleaned up any partial state.

### `claude_fixing`

**Meaning.** The Claude fix adapter is running for the current cycle.

**Recovery.** Same inspect/handoff pattern as `claude_implementing`.

### `evidence_capture`

**Meaning.** `scripts/run_checks.sh` is running to capture the per-
cycle evidence files (Phase 2A/2B Evidence Collection Contract).

**Recovery.** Inspect with
`python scripts/agent_loop.py inspect-artifacts`; when the evidence
files are present, re-run `python scripts/agent_loop.py run` to
continue into Codex review.

### `awaiting_codex_review`

**Meaning.** Claude completion is signaled
(`.agent-loop/claude-done.json`) and the orchestrator is waiting for
Codex to write `.agent-loop/codex-review.md`.

**Recovery.** Codex authors the review file. Once it is on disk, the
orchestrator's next `run` invocation will branch on the verdict.

### `awaiting_claude_implementation`

**Meaning.** A fresh implementation prompt is staged at
`.agent-loop/claude-prompt.md` (the Phase 5F bootstrap output) and the
cycle is ready for Claude.

**Recovery.** Drive the next cycle: `python scripts/agent_loop.py run`.

## Strict-mode gates (Phase 5C)

These statuses fire only under `approval_mode = "strict"`. Each pause
persists the halt status plus `awaiting_human_for = <gate name>` in
`loop-state.json`; no checkpoint artifact is written for the strict-
mode gates.

### `halted_awaiting_human_pre_claude_prompt`

**Meaning.** Strict-mode gate before a new implementation prompt
dispatches to Claude.

**Recovery.** After human review, run
`python scripts/agent_loop.py resume`. The shipped resume restores the
ready-to-continue status and dispatches Claude with the staged prompt.

### `halted_awaiting_human_pre_fix_prompt`

**Meaning.** Strict-mode gate before a new fix prompt dispatches to
Claude.

**Recovery.** After human review, run
`python scripts/agent_loop.py resume`. Resume routes to the fix-cycle
continuation matched by the persisted halt status.

### `halted_awaiting_human_pre_codex_review_normal`

**Meaning.** Strict-mode gate on an implementation cycle, after Claude
completion and evidence validation but before Codex review begins.

**Recovery.** After human review, run
`python scripts/agent_loop.py resume`. Resume routes to the
implementation-cycle Codex-review continuation so Claude is NOT
re-invoked and `cycle_count` is NOT re-incremented.

### `halted_awaiting_human_pre_codex_review_fix`

**Meaning.** Strict-mode gate on a fix cycle, after Claude completion
and evidence validation but before Codex review begins.

**Recovery.** After human review, run
`python scripts/agent_loop.py resume`. Resume routes to the fix-cycle
Codex-review continuation.

## Token-exhaustion (Phase 6F / 6G)

### `halted_awaiting_token_exhaustion_continuation`

**Meaning.** The cycle was suspended because the active Claude or
Codex adapter ran out of token / context budget. The shipped Phase 6D
writer persists a checkpoint under `.agent-loop/memory/checkpoint/`
capturing the pre-suspension cycle context plus a bounded continuation
budget.

**Recovery.** Two options:

- `python scripts/agent_loop.py auto-continue` chains up to
  `AUTO_CONTINUE_MAX_HOPS = 4` bounded continuation hops until the
  cycle clears the halt naturally or a refusal stops the chain.
- `python scripts/agent_loop.py resume` consumes one continuation hop
  and decrements the budget; useful for stepped recovery when the
  operator wants to inspect between hops.

The Phase 6F checkpoint persists `continuation_budget`; both `resume`
and `auto-continue` refuse fail-closed once the budget reaches zero.

## Operator interrupt

### `halted_human_stop`

**Meaning.** A human SIGINT (or equivalent) interrupted the cycle.
The orchestrator catches `KeyboardInterrupt`, persists this status
best-effort, and exits with code 3.

**Recovery.** Inspect with `python scripts/agent_loop.py check-state`
to see where the cycle was, then re-run
`python scripts/agent_loop.py run` when ready.

## Structural halts

These statuses indicate a contract violation - usually a missing,
malformed, or stale repo artifact - that the orchestrator refuses to
work around. Each requires an underlying fix before the cycle can
proceed.

### `halted_input_missing`

**Meaning.** A required input file or field is missing or malformed.
The accompanying reason names the specific input.

**Recovery.** Inspect with
`python scripts/agent_loop.py inspect-artifacts` to see which Phase 7B
inspection-target artifact is absent, fix the underlying issue (Codex
regenerates the planning artifact, the operator regenerates the
evidence file, etc.), and re-run the failing command.

### `halted_contract_version_mismatch`

**Meaning.** `loop-state.json`'s `contract_version` is unsupported by
the running orchestrator. The shipped orchestrator declares a fixed
supported set; an out-of-band edit or a future-version state file
would trip this halt.

**Recovery.** Reconcile the loop-state contract version with the
running orchestrator. Inspect the supported set in
`scripts/agent_loop.py` (`SUPPORTED_CONTRACT_VERSIONS`) and either
roll the loop-state forward or run the matching orchestrator version.

### `halted_review_malformed`, `halted_review_parse_failed`

**Meaning.** `.agent-loop/codex-review.md` does not parse as a valid
verdict per the Phase 5E contract.

**Recovery.** Codex must rewrite the review per the required Codex
Review Format documented in `AGENTS.md`.

### `halted_summary_malformed`

**Meaning.** `.agent-loop/claude-summary.md` does not parse as a valid
summary per the required Claude Implementation Summary format.

**Recovery.** Re-run the implementation cycle (or the matching fix
cycle) to regenerate the summary. The summary format is documented in
`CLAUDE.md`.

### `halted_evidence_incomplete`

**Meaning.** One or more of the six Phase 2A/2B evidence files is
missing, stale, or fails the per-file structural validator.

**Recovery.** Run `bash scripts/run_checks.sh` to regenerate the
evidence set, then re-run
`python scripts/agent_loop.py run` to continue the cycle.

### `halted_evidence_script_unavailable`

**Meaning.** The orchestrator tried to invoke the evidence script but
the script was missing, not executable, or refused at the OS level.

**Recovery.** Verify `scripts/run_checks.sh` is present and
executable. On Windows hosts running through Git Bash, verify the
shebang and the file's CRLF/LF line endings.

## Terminal halts (human required)

### `halted_failed_requires_human`

**Meaning.** Codex returned the `FAILED_REQUIRES_HUMAN` verdict. The
shipped planner refuses to propose the next phase from this halt
status and from `last_verdict == FAILED_REQUIRES_HUMAN`, so no
operator CLI command will unblock the cycle.

**Recovery.** Manual operator intervention:

1. Read `.agent-loop/codex-review.md` for the failure reasoning.
2. Read `.agent-loop/claude-summary.md` for the cycle's stated work.
3. Read the captured evidence under `.agent-loop/` for the validation
   state.
4. Triage the failure outside the loop (manual fix, design decision,
   etc.).
5. Codex (the planning agent) authors a fresh activation prompt for a
   new or revised phase. Approval and activation then follow the
   normal Phase 4C path.

### `halted_max_cycles_reached`

**Meaning.** `cycle_count` reached `max_cycles` without an
`APPROVED_FOR_HUMAN_REVIEW`. The shipped planner refuses to propose
the next phase from any `halted_*` status and from
`cycle_count >= max_cycles` on `NEEDS_FIXES`, so no operator CLI
command will unblock the cycle.

**Recovery.** Manual operator intervention:

1. Read `.agent-loop/codex-review.md` and `.agent-loop/claude-summary.md`.
2. Decide whether the phase should be re-tried with a larger
   `max_cycles` (a Codex-owned re-activation that raises the cap) or
   superseded with a different phase scope.
3. Either way, a fresh Codex-owned activation prompt is required; no
   direct CLI command unblocks the halt.

## Terminal success

### `phase_complete_awaiting_human_approval`

**Meaning.** The cycle reached an `APPROVED_FOR_HUMAN_REVIEW` verdict.
The orchestrator persists this status plus
`awaiting_human_for = "phase_complete_awaiting_human_approval"` and
stops. **This is the success path.**

**Recovery / next step.** Human reviews the diff and the canonical
artifacts, then Codex generates the next-phase proposal via
`python scripts/agent_loop.py plan`. Approval follows the Phase 4C
contract (a human-authored `## Approval` section containing
`APPROVED_FOR_ACTIVATION` on its own line referencing the proposal
label), then `python scripts/agent_loop.py activate` consumes the
proposal and starts the next phase.

## When the hint disagrees with this doc

`STATUS_RECOVERY_HINTS` in `scripts/agent_loop.py` is canonical. If the
hint printed by `status` disagrees with this playbook, trust the
hint. The `tests/test_status_recovery.py` and
`tests/test_documentation_consistency.py` test suites guard the
canonical map and the doc respectively, but the canonical map is the
source of truth a future runtime change updates first.
