# Autonomy Contract And Safety Policy

## Status

Phase 9A defines this contract. The runtime that drives a fully autonomous
PRD-to-product mode is NOT yet implemented in this repository. The contract
below describes what the future selectable autonomous mode is allowed to do,
what still requires explicit human approval, how the mode remains auditable
from repo artifacts, and which boundaries are preserved from the shipped
Phase 1-8 system. Implementation of orchestrator-driven PRD execution is
deferred to later Phase 9 sub-phases:

- Phase 9B: PRD intake and decomposition
- Phase 9C: orchestrator-driven Codex/Claude prompt handoff
- Phase 9D: autonomous internal review/fix loop
- Phase 9E: long-run continuation and "done enough" detection
- Phase 9F: capacity-halt re-probe and automatic resume
- Phase 9G: final human acceptance and polish gate

## Scope

This document is the contract that the future fully autonomous PRD-to-product
mode must satisfy when it is implemented. It is NOT a description of currently
shipped runtime behavior. The shipped repository today provides:

- a CLI-driven local orchestrator (Phase 3) that runs one phase at a time
- a Phase 4 planning surface that proposes the next sub-phase from canonical
  state and refuses to auto-activate
- the three Phase 5 approval modes (`review`, `strict`, and the narrow
  intra-phase bounded `autonomous`)
- the Phase 6 durable-memory, checkpoint, and continuation layers
- the Phase 8A-8C operator documentation

The Phase 9 mode is an ADDITIONAL mode the user will be able to select
alongside the existing three; it does not replace `review`, `strict`, or
bounded `autonomous`.

## Distinction From Shipped Phase 5D `autonomous` Mode

The shipped Phase 5D `autonomous` approval mode is a narrow runtime
continuation path WITHIN an already-active phase. When `approval_mode =
"autonomous"`, the orchestrator bypasses the three Phase 5C strict-mode
human gates (`pre_claude_prompt`, `pre_fix_prompt`, `pre_codex_review`) and
runs the existing Codex / Claude implementation and fix cycles to completion
within the shipped `cycle_count` / `max_cycles` threshold. It does NOT plan
the next phase, propose a new sub-phase, decompose a PRD, or advance from
one approved phase to the next. The `APPROVED_FOR_HUMAN_REVIEW` terminal
still halts for human approval before phase progression.

The Phase 9 fully autonomous PRD-to-product mode is a DIFFERENT mode. It is
intended to take a PRD or product idea as input, decompose it into bounded
internal phases, drive each phase through implementation and review/fix
cycles, and advance from one approved phase to the next WITHOUT waiting for
per-phase human approval, halting only at the final human acceptance gate or
on the preserved hard stops below. The two modes share the same approval-
mode selector pattern but are not the same behavior: collapsing them into
one mode would violate the shipped Phase 5A contract that `autonomous`
never advances phases on its own.

## Allowed Actions In The Future Phase 9 Mode

Within a single autonomous PRD-to-product run, the mode is allowed to:

- accept a PRD or product brief as input and decompose it into bounded
  internal phases, tasks, risks, and acceptance criteria (Phase 9B)
- drive the orchestrator-side Codex-to-Claude prompt handoff for each
  derived phase without per-prompt manual transfer (Phase 9C)
- run automatic Codex review and autonomous Claude fix cycles within the
  shipped `cycle_count` / `max_cycles` threshold (Phase 9D)
- regenerate `.agent-loop/fix-prompt.md` from Claude-owned review findings
  after each review pass (Phase 9D)
- apply Codex-owned auto-fixes directly during the same review/fix loop
  through the shipped Phase 5E ownership-aware reconciliation (Phase 9D)
- automatically activate the next PRD-derived phase when the current phase
  reaches its terminal `APPROVED_FOR_HUMAN_REVIEW` state (Phase 9D / 9E)
- survive token / context exhaustion through the shipped Phase 6F / 6G
  continuation primitives without restarting the run from scratch
  (Phase 9E)
- treat Claude / Codex provider rate-limit or capacity exhaustion as a
  resumable external-capacity halt with bounded re-probe and resume
  (Phase 9F)
- stop only at the final human acceptance / polish gate when every
  PRD-derived phase has been completed, deferred, or blocked (Phase 9G)

## Preserved Hard Stops And Human Approval Boundaries

Even within a fully autonomous PRD-to-product run, the mode MUST preserve
the load-bearing safety boundaries the shipped system enforces today:

- never commits to Git; never pushes (no Git automation under any mode)
- the human-authored `APPROVED_FOR_ACTIVATION` token remains the only way
  the activator will write activation artifacts for an externally-authored
  proposal; the autonomous mode's own internally-derived next-phase
  activations are a separate Phase 9D path that the runtime work will
  define, and until Phase 9D ships the shipped `APPROVED_FOR_ACTIVATION`
  gate is preserved unchanged
- halts immediately on `FAILED_REQUIRES_HUMAN` and persists
  `halted_failed_requires_human` in `loop-state.json`
- halts immediately on `cycle_count >= max_cycles` for `NEEDS_FIXES` and
  persists `halted_max_cycles_reached`; the "materially changed /
  narrowed" judgment remains human-owned
- halts on every structural failure mode (malformed `claude-summary.md`,
  `codex-review.md`, `fix-prompt.md`, missing or malformed
  `loop-state.json`, unsupported `contract_version`, missing or malformed
  evidence)
- halts on operator SIGINT (`halted_human_stop`)
- requires an EXPLICIT final human acceptance / polish step (Phase 9G)
  before the run is treated as complete; the mode never declares product
  completion on its own
- preserves canonical repo artifacts as the source of truth; framework-
  managed state never overrides `TASK.md`, `.agent-loop/loop-state.json`,
  `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, or
  `.agent-loop/phase-plan.md` (Phase 6M contract)

## Audit Expectations

The fully autonomous PRD-to-product mode MUST remain auditable from repo
artifacts alone. A reviewer reading `.agent-loop/orchestrator.log`,
`.agent-loop/loop-state.json`, `.agent-loop/phase-plan.md`, the canonical
phase artifacts, the Phase 6 checkpoint entries, and the Phase 2A evidence
files MUST be able to reconstruct what the mode did, why it halted, and
which Codex / Claude handoffs occurred. Specifically:

- every internal phase advance is recorded as a phase activation in
  `phase-plan.md` and a `loop-state.json` reset to
  `awaiting_claude_implementation` with the next phase / sub-phase
- every internal Codex-to-Claude prompt handoff is recorded via the
  shipped `claude-done.json` routing signal and the per-cycle audit notes
- every internal review verdict is recorded in the corresponding
  `codex-review.md` cycle artifact, and each fix prompt is recorded in
  the corresponding `fix-prompt.md`
- every checkpoint / continuation hop is recorded under
  `.agent-loop/memory/checkpoint/` with the shipped Phase 6D body schema
- every capacity-halt re-probe and resume attempt is recorded with
  bounded metadata (attempt count, backoff window, observed capacity
  state) in the audit log
- every Codex-owned auto-fix application is recorded with the existing
  Phase 5E `review reconciliation:` summary line and the matching per-
  action audit note
- the final human acceptance / polish step is recorded as an explicit
  artifact write rather than inferred from the absence of further halts

## Safety Boundaries

The fully autonomous PRD-to-product mode MUST refuse to:

- commit, push, tag, branch, stash, reset, checkout, or otherwise mutate
  Git history or working-tree state
- modify `AGENTS.md`, `CLAUDE.md`, `ROADMAP.md`, or the Phase 3A
  orchestrator-protected files outside its assigned ownership
- author or modify Codex-owned planning artifacts during a single phase
  (the phase activation between phases is a deliberate explicit write
  set, not a runtime mutation)
- skip the final human acceptance / polish gate (Phase 9G)
- silently widen autonomy across runs; each run must carry an explicit
  selection of the autonomous mode in `loop-state.json` and the
  selection must be visible in `orchestrator.log` audit notes
- retry capacity-halt resumes forever; the mode must bound attempts
  and/or wait windows and fall back to a human-visible halt when capacity
  does not return within policy limits
- claim product completion without objective signals (every PRD-derived
  phase recorded as complete / deferred / blocked, validations passing
  where required, and the explicit completion artifact written)

## Out Of Scope For Phase 9A

Phase 9A is documentation-only. The shipped Phase 1-8 runtime behavior is
preserved unchanged by this slice; no orchestrator, planner, activator,
evidence-collection, review-routing, checkpoint, continuation, memory,
runtime-adapter, LangChain, or VS Code feature work is introduced. Adding
the runtime that satisfies this contract is the work of Phases 9B-9G.
