# External Workspace Controller Contract

## Status

Phase 10A defines this contract. The runtime that lets this controller
repository safely target a different workspace or repository is NOT yet
implemented. The contract below describes how the future external-workspace
controller mode is allowed to resolve, attach to, bootstrap, drive, and refuse
operations against a target workspace, what stays controller-owned versus
target-owned, where canonical `.agent-loop/` artifacts live in each mode, and
which boundaries are preserved from the shipped Phase 1 - 9 system.
Implementation of the external-workspace runtime is deferred to later Phase 10
sub-phases:

- Phase 10B: external workspace bootstrap and attach flow
- Phase 10C: external workspace runtime control (UI / dashboard / run control)
- Phase 10D and later: additional external-workspace capabilities tracked in
  `ROADMAP.md` (concurrent Codex / Claude execution, MCP integration, RAG
  layer, GitHub integration, model-policy extensibility)

## Scope

This document is the contract the future external-workspace controller mode
must satisfy when it is implemented. It is NOT a description of currently
shipped runtime behavior. The shipped repository today operates in a single
mode: this repository (the controller repository) IS the target; the
orchestrator reads from and writes to `.agent-loop/` inside the same repo it
runs from, and every canonical artifact (`TASK.md`,
`.agent-loop/loop-state.json`, the per-cycle prompt / summary / review /
fix-prompt artifacts, the Phase 6 memory and checkpoint entries, the Phase
9F capacity-retry-state artifact, the Phase 9G final-acceptance artifact)
lives inside the same controller repository.

The future Phase 10 external-workspace mode is an ADDITIONAL operating mode
in which the controller repository drives a SEPARATE target workspace or
repository on the same machine. The shipped self-targeting mode is preserved
unchanged; the external-workspace mode is opt-in and never replaces it.

## Distinction From Shipped Self-Targeting Mode

The shipped self-targeting mode treats one directory as BOTH controller and
target. There is no path-resolution step: `find_repo_root()` walks upward
from the script location looking for `TASK.md` + `AGENTS.md` + `.agent-loop/`
markers; the resulting directory is where every canonical artifact lives.
The shipped Phase 4 planner / Phase 4C activator boundary, the Phase 5
approval-mode runtime semantics, the Phase 6 memory / checkpoint /
continuation layers, the Phase 9B - 9G autonomous-PRD runtime, the
`scripts/run_checks.sh` capture surface, and the canonical-artifact source
of truth all assume this single-root layout.

The future Phase 10 external-workspace mode is a DIFFERENT mode. The
controller repository remains the home of the orchestrator binary, the
planner / activator code, the operator documentation, the runtime adapter
boundary, the safety / approval contracts, and the test suite. A SEPARATE
target workspace or repository (selected by the operator at attach time)
holds the per-target canonical artifacts the orchestrator operates on. The
two roots are explicitly distinct: collapsing them into one would silently
let a Phase 10 run modify the controller repo itself (Codex-owned planning,
shipped contract documents, the orchestrator source) which the shipped
safety boundaries forbid.

## Controller-Owned Artifacts

The CONTROLLER repository owns and authoritatively ships:

- `scripts/agent_loop.py` (the orchestrator, planner, activator, adapter
  factories, autonomous-PRD runtime, capacity-reprobe surface, final-
  acceptance surface)
- `scripts/run_checks.sh` (the Phase 2A evidence-capture script)
- `AGENTS.md`, `CLAUDE.md`, `ROADMAP.md`, `README.md` (governance contracts)
- `TASK.md` of the controller repo (the controller's own active phase /
  task / outcome record)
- `.agent-loop/` of the controller repo (the controller's own canonical
  artifact set; the orchestrator continues to use this set when running
  in shipped self-targeting mode and when running a controller-self-test)
- `docs/` (operator documentation, including this contract)
- `tests/` (focused test suite that locks in the shipped behavior)

The future Phase 10 runtime MUST NOT modify any of the controller-owned
files above as a side effect of operating against an external target.
Updating controller-owned files remains a controller-repo change that
goes through the shipped phase-gated review workflow.

## Target-Owned Artifacts

A TARGET workspace or repository (selected by the operator at attach time)
owns its own per-target canonical artifact set. The future Phase 10 runtime
operates on the TARGET's artifact set, not the controller's:

- the target's `TASK.md` (the active phase / task / outcome record FOR THE
  TARGET WORKSPACE)
- the target's `.agent-loop/current-task.md`,
  `.agent-loop/current-phase.md`, `.agent-loop/phase-plan.md` (Codex-owned
  per-target planning artifacts)
- the target's `.agent-loop/claude-prompt.md`,
  `.agent-loop/claude-summary.md`, `.agent-loop/codex-review.md`,
  `.agent-loop/fix-prompt.md` (per-cycle artifacts for the target)
- the target's `.agent-loop/loop-state.json` (orchestrator state for the
  target)
- the target's `.agent-loop/orchestrator.log` (audit trail for the target)
- the target's evidence files written by `scripts/run_checks.sh` when run
  against the target's working tree (`.agent-loop/git-status.log`,
  `.agent-loop/git-diff.patch`, `.agent-loop/test-output.log`,
  `.agent-loop/lint-output.log`, `.agent-loop/typecheck-output.log`,
  `.agent-loop/build-output.log`)
- the target's Phase 6 memory subtree (`.agent-loop/memory/`)
- the target's Phase 9B PRD-intake artifact (`.agent-loop/prd-intake.json`)
- the target's Phase 9C prompt-handoff descriptor
  (`.agent-loop/prompt-handoff.json`)
- the target's Phase 9D review-fix-loop descriptor
  (`.agent-loop/review-fix-loop.json`)
- the target's Phase 9E long-run-continuation descriptor
  (`.agent-loop/long-run-continuation.json`)
- the target's Phase 9F capacity-retry-state artifact
  (`.agent-loop/capacity-retry-state.json`)
- the target's Phase 9G final-acceptance artifact
  (`.agent-loop/final-acceptance.json`)

The future Phase 10 runtime MUST keep the target's canonical artifact set
authoritative for the target; advisory descriptors (Phase 9C / 9D / 9E
routing/timing artifacts) remain advisory in the target as they are in the
shipped self-targeting mode.

## Path Resolution

The future Phase 10 runtime MUST resolve the target root from EXPLICIT
operator input, not from implicit cwd traversal or environment heuristics.
The contract requires:

- the target root is supplied by the operator (CLI flag, attach-time prompt,
  or operator-authored attach descriptor) and recorded in a controller-owned
  attach record before any target-side artifact is read or written
- the controller refuses to operate against a target root that is the same
  directory as the controller root (the two roots must be distinct
  filesystem paths after canonicalization)
- the controller refuses to operate against a target root that does not
  itself look like a workspace (the runtime MUST validate the presence of
  the target's `TASK.md` or initialize it via an explicit bootstrap step,
  never silently create a fresh target on a path the operator did not
  designate as such)
- the controller refuses to operate against a target root located inside
  the controller repository (no nesting; a target whose canonical path is
  a descendant of the controller root would collapse the controller /
  target boundary)
- the controller MUST canonicalize the operator-supplied path
  (`Path.resolve()` or equivalent) before any safety check so a relative
  path or a symlink cannot bypass the same-root / nesting refusals

The shipped self-targeting mode keeps its existing `find_repo_root()`
behavior unchanged: when the operator does not select an external target,
the orchestrator operates on the controller repo itself.

## Attach And Bootstrap

When the operator first attaches the controller to a target workspace, the
future Phase 10 runtime MUST:

- write a controller-owned attach record (suggested location:
  `.agent-loop/external-target.json` in the CONTROLLER repo) that names the
  canonicalized target root, the attach timestamp, the operator who
  performed the attach, and an attach-signal version marker. The attach
  record is the operator-visible source of truth for "which target is the
  controller currently driving"
- refuse the attach if the target is already attached to another controller
  (detected via a target-side attach descriptor written under the target's
  `.agent-loop/`) so the same target cannot be driven by two controllers
  at once
- bootstrap missing target-side canonical artifacts (`TASK.md`,
  `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`,
  `.agent-loop/phase-plan.md`, `.agent-loop/loop-state.json`) only when the
  operator explicitly opts into bootstrap; a target whose canonical set is
  partially present is refused fail-closed rather than auto-completed
- never bootstrap a target by copying the controller's own canonical
  artifacts; the controller's phase / task state is its own and is not
  load-bearing for a target run
- preserve the shipped Phase 4 planner / Phase 4C activator boundary inside
  the target: any target-side phase activation must go through the shipped
  activator with the human-authored `APPROVED_FOR_ACTIVATION` token, the
  attach step never activates a target-side phase on its own
- explicitly record the attach in the controller's `orchestrator.log` (or
  an equivalent controller-owned audit log) so the attach is auditable
  from controller-owned artifacts alone

The reverse operation (detach) MUST clear the controller-owned attach
record and any target-side attach descriptor, leaving both roots in a
coherent state that another attach could resume from.

## Refusal Behavior

The future Phase 10 runtime MUST refuse fail-closed in at least the
following cases (the runtime never silently advances or fabricates target
state):

- the operator did not select a target root (no CLI flag, no attach record,
  no fallback path); the runtime refuses with an explicit "no target
  selected" message rather than defaulting to the controller root
- the operator-supplied target root is the same as the controller root
  after canonicalization
- the operator-supplied target root is nested inside the controller root
- the target root is not a directory, is not readable, or is not writable
  by the running user
- the target's canonical artifact set is partially present (some required
  files missing, others present) and bootstrap was not explicitly opted
  into
- the target is already attached to another controller (the target-side
  attach descriptor names a different controller path)
- the controller's attach record is missing, malformed, or names a target
  whose canonicalized path no longer matches the on-disk target
- the operator attempted to attach a second target while the controller
  still has an in-flight cycle for the currently-attached target (no
  concurrent-target execution under this contract)
- the target's `loop-state.json` `contract_version` is not supported by
  the running orchestrator
- the target's `loop-state.json` carries any `halted_*` status the
  shipped runtime would refuse to advance past automatically

The refusal vocabulary MUST reuse the shipped halt / refusal terms where
applicable (`halted_contract_version_mismatch`, `halted_input_missing`,
etc.) and introduce new `halted_external_target_*` statuses only when no
shipped status fits. Any new status MUST be documented in
`docs/halt-and-recovery.md` BEFORE the corresponding Phase 10 runtime slice
ships.

## Approval Gates

The future Phase 10 runtime MUST preserve every shipped human-approval
gate:

- the attach step itself is an explicit operator action (CLI invocation
  with the target path) rather than an autonomous controller decision
- the detach step is an explicit operator action
- per-target phase activation goes through the shipped Phase 4C activator
  with the human-authored `APPROVED_FOR_ACTIVATION` token; the attach
  step never activates a target-side phase
- per-target `APPROVED_FOR_HUMAN_REVIEW` terminals continue to halt the
  target-side loop and require explicit human approval before the next
  phase begins (the shipped review / strict / autonomous mode semantics
  apply per-target, not at the controller level)
- the Phase 9G final human acceptance gate continues to require an
  explicit operator action to record acceptance against the target's
  canonical artifact set
- selecting Phase 9 fully autonomous PRD-to-product mode on a target is
  an explicit per-attach decision that lands in the target's
  `loop-state.json` and the controller's audit log, never an implicit
  default

## Source-Of-Truth Preservation

Canonical artifacts on disk remain authoritative; any controller-side
metadata about the external target is advisory unless explicitly promoted
by this contract:

- the controller's attach record (`.agent-loop/external-target.json` in
  the controller repo) is canonical for "which target is the controller
  attached to right now"
- the target's `.agent-loop/loop-state.json` is canonical for "what phase
  the target is on, what its cycle count is, what its last verdict was";
  the controller MUST NOT cache or shadow these fields in a way that
  could disagree with the target's on-disk state
- the target's `.agent-loop/orchestrator.log` is canonical for the
  per-target audit trail; the controller's own audit log records attach
  / detach / refusal events but never substitutes for the target's
  per-cycle audit history
- any external UI surface, dashboard, or notification stream (Phase 10C
  and later) is advisory only; the underlying canonical artifacts win
  on disagreement

## Safety Boundaries

The future Phase 10 external-workspace mode MUST refuse to:

- commit, push, tag, branch, stash, reset, checkout, or otherwise mutate
  Git history or working-tree state in either the controller or the target
  (the shipped no-Git-automation boundary applies to BOTH roots)
- modify `AGENTS.md`, `CLAUDE.md`, `ROADMAP.md`, or any controller-owned
  contract file as a side effect of operating against a target
- author or modify the target's Codex-owned planning artifacts during a
  single phase (phase activation between phases is a deliberate explicit
  write set, not a runtime mutation)
- collapse the controller / target boundary by writing target-side
  artifacts into the controller root or vice versa
- silently widen autonomy across attaches; each attach must carry an
  explicit selection of the operating mode in the attach record and the
  selection must be visible in the controller's audit log
- skip the final human acceptance / polish gate (Phase 9G) on the target
- introduce concurrent Codex / Claude execution against the same target
  or across multiple targets in this contract (deferred to a later Phase
  10 slice; the contract here is single-target, single-in-flight-cycle)
- introduce MCP integration, external UI, or any other roadmap-only
  capability in this contract (each is its own later Phase 10 slice)

## Out Of Scope For Phase 10A

Phase 10A is documentation / contract only. The shipped Phase 1 - 9
runtime behavior is preserved unchanged by this slice; no orchestrator,
planner, activator, evidence-collection, review-routing, checkpoint,
continuation, memory, runtime-adapter, LangChain, VS Code, Phase 9
autonomous-PRD, capacity-reprobe, or final-acceptance feature work is
introduced. Adding the runtime that satisfies this contract is the work
of Phases 10B and later.
