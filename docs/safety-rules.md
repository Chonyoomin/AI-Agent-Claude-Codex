# Safety Rules

This playbook lists the safety boundaries the Agentic AI Coding Loop
enforces today. It describes only behavior that ships in the current
repository; future-roadmap items (see `ROADMAP.md`) are not covered.

For the architectural model see `docs/architecture.md`. For the per-mode
runtime contract see `docs/approval-modes.md`. For halt-to-recovery
mapping see `docs/halt-and-recovery.md`.

## Source of truth

Every load-bearing piece of state lives in a repo artifact under
`.agent-loop/` or the project root. Specifically:

- `.agent-loop/loop-state.json` is the canonical orchestrator state.
- `TASK.md` carries the human-readable active phase, task, outcome, and
  next-phase gate.
- `.agent-loop/current-phase.md` and `.agent-loop/current-task.md` are
  the per-cycle Codex-owned planning artifacts.
- `.agent-loop/phase-plan.md` is the historical phase record.
- `.agent-loop/codex-review.md` is the per-cycle Codex verdict.
- `.agent-loop/claude-summary.md` is the per-cycle Claude summary.
- `.agent-loop/orchestrator.log` carries every state transition and
  audit note in chronological order.

A repo where every artifact exists is reproducible; a repo where any
artifact is missing or malformed is not, and the orchestrator halts
fail-closed rather than guess.

## Git automation is forbidden

The orchestrator never invokes git outside the read-only `git status`
and `git diff HEAD` captures inside `scripts/run_checks.sh`. The system
will not:

- create commits or amend existing commits
- push, force-push, or open pull requests
- create, switch, rename, or delete branches
- stash, reset, checkout, clean, or tag
- modify the git config or `.git/` contents

Every commit and every push is an explicit human action. The orchestrator
captures evidence (the `git status` / `git diff HEAD` outputs plus the
per-check validation logs) under `.agent-loop/` so the operator has the
context to review before deciding what (if anything) to commit.

## Human gates at phase transitions

Phase activation requires an explicit `APPROVED_FOR_ACTIVATION` token in
a human-authored `## Approval` section of `.agent-loop/proposed-phase.md`
that references the proposal's `## Label`. The shipped activator refuses
to silently advance phases:

- token forgery (extra words on the line, alternate capitalization,
  surrounding characters) is refused
- stale-label approvals (approval section references a different
  proposal label) are refused
- missing or malformed proposal sections are refused with the matching
  halt status persisted

`python scripts/agent_loop.py activate` consumes the proposal atomically
or rolls back on any failure; partial activation writes never appear on
disk.

## Recovery-preserving halts

Every halt the orchestrator persists is recovery-preserving. The
canonical pattern:

- a structural failure raises `HaltError(<status>, <reason>)`
- the orchestrator persists the halt status in `loop-state.json`
- the failure never clobbers an existing recovery point (strict-mode
  gate state, token-exhaustion checkpoint, etc.)
- the operator inspects `python scripts/agent_loop.py status` for the
  matching recovery hint

A halt that would have to overwrite a prior recovery point uses the
recovery-preserving refusal pattern (stderr + log + exit 2) rather than
`_halt`, so the prior recovery point stays intact.

## Ownership boundaries

The artifact-ownership model in `CLAUDE.md` is the source of truth. In
brief:

- **Orchestrator-owned (read-only for Claude)**: `loop-state.json`,
  `orchestrator.log`, the six Phase 2A/2B evidence files (`git-status.log`,
  `git-diff.patch`, `test-output.log`, `lint-output.log`,
  `typecheck-output.log`, `build-output.log`).
- **Codex-owned**: `TASK.md`, `current-task.md`, `current-phase.md`,
  `phase-plan.md`, `claude-prompt.md`, `fix-prompt.md`, `codex-review.md`.
- **Claude-owned (per cycle)**: `claude-summary.md`. Everything else
  under the repo is Claude-routed implementation surface by default
  unless the active prompt reassigns it.

Routing mismatches (a Claude prompt that would require editing a Codex-
owned artifact) must be surfaced rather than silently edited. The same
applies in reverse for Codex.

## Validation distinguishes failure modes

`scripts/run_checks.sh` writes the Phase 2A Evidence Collection Contract
state vocabulary: `Passed`, `Failed`, `Not run`, `Inconclusive`. The
script's exit code is 0 iff every configured check is `Passed` or
`Not run`. The contract intentionally separates "validation failed"
from "validation not run" from "validation blocked by environment"; the
orchestrator never collapses these into a vague success claim.

## Audit trail

Every state transition, every adapter dispatch, every halt, and every
audit note (`runtime adapter:`, `langchain support:`, `phase-boundary
distillation:`, `token exhaustion recorded:`, `auto-continue chain hop
N begin`, etc.) lands in `.agent-loop/orchestrator.log`. The cycle
history is reconstructable from on-disk artifacts after the fact; no
load-bearing state lives only in transient process memory.

## What the safety model does NOT promise

- It does not promise to detect every kind of malicious or buggy code
  the implementation step produces. Code review (Codex) and human
  review at phase boundaries are the load-bearing review layers.
- It does not promise to roll back uncommitted disk state on every
  exception. The recovery-preserving halt patterns cover the named
  recovery points; an uncategorized exception leaves the repo in
  whatever state the failing operation left behind (typically
  reviewable via `git diff` plus the orchestrator log).
- It does not promise to keep advisory layers (memory retrieval,
  optional context, LangChain support) from leaking stale or noisy
  information into a prompt. Those layers are explicitly advisory;
  canonical artifacts always win.
- It does not promise behavior for Phase 9 (Fully Autonomous PRD-To-
  Product Mode) or Phase 10 (Future Product Features) - those are
  roadmap only, not shipped behavior. See `ROADMAP.md`.
