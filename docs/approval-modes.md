# Approval Modes

This playbook describes the three shipped approval modes
(`review`, `strict`, `autonomous`) and how to drive each one. It covers
what each mode does, when to use it, how to switch, and what each mode
preserves. It describes only behavior that ships in the current
repository.

For the safety model see `docs/safety-rules.md`. For halt-by-halt
recovery steps see `docs/halt-and-recovery.md`. For the architectural
context see `docs/architecture.md`.

## The contract

The approval mode is recorded in `.agent-loop/loop-state.json` under
`approval_mode`. The three allowed values are:

- `review` (default on activation)
- `strict`
- `autonomous`

A pre-existing non-`review` mode is preserved across phase activation;
otherwise activation sets `review` and clears
`awaiting_human_for`. The contract is the Phase 5A Approval Modes
Contract; the orchestrator refuses any other value as
`halted_input_missing`.

## `review` mode (default)

**What it does.** One cycle runs end-to-end. Codex returns a verdict.
On `APPROVED_FOR_HUMAN_REVIEW` the orchestrator persists
`phase_complete_awaiting_human_approval` plus
`awaiting_human_for = "phase_complete_awaiting_human_approval"` and
halts so a human can review before any next-phase activation.
`NEEDS_FIXES` drives bounded automated fix cycles up to `max_cycles`.
`FAILED_REQUIRES_HUMAN` halts immediately.

**Per-cycle handoff.** After Claude returns a fresh
`.agent-loop/claude-summary.md` and evidence capture succeeds, the
orchestrator writes `.agent-loop/claude-done.json` as a routing /
timing signal carrying `signal_version`, `phase`, `sub_phase`, `task`,
`cycle_count`, `mode` (`"implementation"` or `"fix"`),
`source_prompt_path`, and `status = "ready_for_codex_review"`. It never
substitutes for the canonical summary, diff, or evidence; it is purely
a handoff signal. Each new prompt issuance clears any stale
`claude-done.json`.

**When to use it.** Default. Use `review` when you want every cycle to
run automatically, with human approval gating only the phase boundary.

**Recovery.** See `docs/halt-and-recovery.md` for per-halt steps.

## `strict` mode

**What it does.** Adds three human checkpoints inside each cycle (Phase
5C contract). The orchestrator pauses at:

1. **`pre_claude_prompt`** - before a new implementation prompt
   dispatches to Claude. Halt status:
   `halted_awaiting_human_pre_claude_prompt`.
2. **`pre_fix_prompt`** - before a new fix prompt dispatches to Claude.
   Halt status: `halted_awaiting_human_pre_fix_prompt`.
3. **`pre_codex_review`** - after Claude completion and evidence
   validation but before Codex review begins. Persists in two halt-
   status flavors so resume can route to the correct continuation:
   `halted_awaiting_human_pre_codex_review_normal` (implementation
   cycle) and `halted_awaiting_human_pre_codex_review_fix` (fix cycle).

At each gate the orchestrator writes `awaiting_human_for = <gate name>`
plus the matching halt status in a single atomic write, logs a `note:`
line to `.agent-loop/orchestrator.log`, and exits cleanly with code 2.

**Resume.** After the human reviews the paused step, run
`python scripts/agent_loop.py resume`. The shipped resume refuses
unless `status` is one of the four strict-gate halts, then clears
`awaiting_human_for`, restores a ready-to-continue status, and
dispatches to the continuation matched by the persisted halt status so
no earlier work is re-done and the next gate (if any) still fires.

**Note on checkpoint artifacts.** Strict-mode halts do NOT write
strict-gate checkpoint artifacts under
`.agent-loop/memory/checkpoint/`. The state needed to resume is the
persisted halt status plus `awaiting_human_for` in
`loop-state.json`. Token-exhaustion (Phase 6F) is the only path that
writes checkpoint artifacts.

**When to use it.** Use `strict` when you want a human gate at every
adapter handoff, e.g. for a sensitive phase, a new operator learning
the loop, or a regulated-change scenario.

**Recovery.** See `docs/halt-and-recovery.md` for the per-gate hint and
the matching resume command.

## `autonomous` mode

**What it does.** Bypasses each of the three strict-mode gates with an
auditable `autonomous mode: bypassing <gate> gate at <where>` note to
`.agent-loop/orchestrator.log`. The orchestrator continues directly
through the implementation step, the Claude-completion-to-Codex-review
handoff, and bounded `NEEDS_FIXES` fix cycles within the existing
`cycle_count` / `max_cycles` threshold.

**Hard stops preserved.** Every shipped hard stop still fires under
`autonomous`:

- `FAILED_REQUIRES_HUMAN` halts immediately.
- Malformed evidence or summaries fail closed with the matching
  structural halt.
- `cycle_count >= max_cycles` on `NEEDS_FIXES` halts.
- `APPROVED_FOR_HUMAN_REVIEW` still persists
  `phase_complete_awaiting_human_approval` and
  `awaiting_human_for = phase_complete_awaiting_human_approval` because
  the Phase 5A contract requires human approval before phase
  progression. **Autonomy never auto-progresses phases.**

**When to use it.** Use `autonomous` when the operator trusts the
phase to run unattended through the cycle interior and only wants to
review at the phase boundary. The shipped `review` and `strict`
behavior is unaffected by selecting `autonomous`.

**Recovery.** Identical to `review` for hard stops; the strict-mode
gates simply do not fire.

## Switching modes

The approval mode is a field on `loop-state.json` set by the activation
step. The shipped activator writes `approval_mode = "review"` on
activation unless a pre-existing non-`review` mode is present
(Codex-owned planning state can set it on a proposal). Operators do
not typically flip the mode mid-phase; doing so requires editing
`loop-state.json` and is the operator's responsibility to keep
internally consistent (e.g. an in-flight `halted_awaiting_human_pre_*`
status assumes `strict` mode).

## What the modes preserve

All three modes preserve:

- the Phase 3A Orchestrator Contract (one cycle at a time, evidence
  always captured, verdict always one of three)
- the halt vocabulary and refusal semantics
- the artifact ownership boundaries (Codex / Claude / orchestrator)
- the no-Git-automation rule
- the recovery-preserving halt pattern

## What the modes do NOT promise

- `autonomous` does NOT mean fully autonomous PRD-to-product. Phase 9
  (Fully Autonomous PRD-To-Product Mode) is roadmap-only; the shipped
  `autonomous` mode is the narrow strict-gate-bypass slice described
  above.
- None of the modes can advance phases without human approval.
- None of the modes commit, push, or modify git state.
