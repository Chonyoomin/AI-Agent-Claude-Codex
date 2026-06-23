# External Workspace Bootstrap Contract

## Status

Phase 10C defines this contract. The Phase 10E runtime slice implements
the bootstrap runtime that satisfies this contract: the
`bootstrap_external_target(...)` library function plus the `--bootstrap`
opt-in surface on `attach_external_target(...)` and the
`attach-external-target` CLI now write the canonical target-side
artifact set under the Phase 10C invariants, persist the Phase 10C
extension fields back into the Phase 10B attach record, and refuse
fail-closed on every contract-listed refusal case. The Phase 10E slice
also introduces the `halted_external_target_bootstrap_input_missing`
and `halted_external_target_bootstrap_atomicity_failure` halt statuses
documented in `docs/halt-and-recovery.md`. The contract below specifies
how target-side `.agent-loop` initialization may occur in
external-workspace mode, which target states the runtime must refuse
fail-closed, which canonical artifacts may be created by bootstrap and
with which initial contents, what operator opt-in is required, what
bootstrap-state metadata must be persisted into the Phase 10B attach
record, and which boundaries are preserved from the shipped Phase 1 - 9
system and the Phase 10A / 10B contracts. Implementation of additional
external-workspace surfaces is deferred to later Phase 10 sub-phases:

- Phase 10D: External Workspace Attach/Detach Runtime Initial Slice
  (shipped; consumes the bootstrap contract during attach by either
  confirming the target's canonical set is already present or invoking
  the Phase 10E bootstrap runtime to satisfy this contract before
  writing the attach record's `bootstrap_state` sub-object)
- Phase 10E: External Target Bootstrap Runtime (shipped; the
  `bootstrap_external_target(...)` library function plus the
  `--bootstrap` opt-in surface on `attach-external-target` satisfy
  this contract by writing the target-side canonical artifact set
  with the initial contents this contract pins)
- Phase 10F: Target-Side Cycle Dispatch (consumes the
  fully-bootstrapped target through the shipped Phase 5 approval-mode
  runtime semantics)
- Phase 10G: External UI / Dashboard / Run-Control (advisory external
  surfaces over the bootstrap-state record and per-target loop-state)
- Phase 10H and later: additional external-workspace capabilities
  tracked in `ROADMAP.md`

## Scope

This document is the contract the future Phase 10E bootstrap runtime
must satisfy when it initializes a target-side `.agent-loop` canonical
artifact set, and the contract the future Phase 10D attach/detach
runtime must consult before writing the Phase 10B attach record's
`bootstrap_state` sub-object. It is NOT a description of currently
shipped runtime behavior. The shipped repository today has no
external-workspace bootstrap surface; the controller and target roots
are the same directory (the shipped self-targeting mode the Phase 10A
contract preserves), and the controller's own `.agent-loop/` canonical
set is initialized by the shipped Phase 4C activator + human
`APPROVED_FOR_ACTIVATION` token flow, not by any bootstrap path.

The bootstrap contract is the load-bearing specification for "what
counts as a target the external-workspace runtime may operate on, what
counts as a target the runtime must refuse fail-closed, and what counts
as a target the runtime may initialize on operator opt-in". The
contract pins the pre-bootstrap target-state vocabulary, the canonical
artifact set the bootstrap may write, the initial contents of each
artifact, the operator opt-in / refusal behavior, the bootstrap-state
field schema that satisfies the Phase 10B attach record's delegation,
and the refusal vocabulary so a later Phase 10E runtime slice can be
implemented from this contract without further design decisions.

## Distinction From Other Shipped Artifacts

The bootstrap surface is NOT one of the existing canonical artifacts.
The shipped Phase 1 - 9 system and the Phase 10A / 10B contracts
already define these distinct artifact roles which the bootstrap
contract MUST NOT overlap or replace:

- The Phase 4C activator + `APPROVED_FOR_ACTIVATION` human-approval
  token is the canonical path that resets / advances a
  `.agent-loop/loop-state.json` between sub-phases in the
  self-targeting mode. The bootstrap runtime is NOT a Phase 4C
  activator: bootstrap initializes a target's canonical set at
  attach-time before any per-target phase activation has occurred.
  Per-target phase activation continues to require the Phase 4C
  activator + the human-authored `APPROVED_FOR_ACTIVATION` token.
- The Phase 10A controller contract defines the controller-vs-target
  ownership boundary and names `.agent-loop/external-target.json` as
  the controller-owned attach-record path. The bootstrap contract
  does NOT redefine the attach record; it specifies the schema of the
  attach record's `bootstrap_state` sub-object and the runtime
  preconditions the attach runtime must check.
- The Phase 10B attach-record contract pins the on-disk shape of the
  controller-owned attach record at `.agent-loop/external-target.json`
  and delegates the `bootstrap_state` sub-object's field-level schema
  to this Phase 10C contract. The bootstrap contract satisfies that
  delegation; it does NOT modify the attach record's other top-level
  fields.
- The shipped Phase 5F automatic phase-start prompt-bootstrap path
  (which writes `.agent-loop/claude-prompt.md` after activation) is
  a separate per-cycle prompt-bootstrap surface; it is NOT this
  Phase 10C target-canonical-set bootstrap surface. The vocabulary
  collision is intentional in the codebase, but the two surfaces
  operate at different layers (per-cycle prompt vs per-attach target
  initialization) and must not be conflated.

## Canonical Artifact Set The Bootstrap May Write

The bootstrap runtime MAY write exactly the following target-side
canonical artifacts when (and only when) the operator has explicitly
opted into bootstrap and the pre-bootstrap target state is the
empty-target state (see `## Pre-Bootstrap Target States` below):

- the target's `TASK.md` (Codex-owned planning artifact carrying the
  target's Human Objective, Project Intent, Active Phase, Active
  Sub-Phase, Phase Status, Active Task, Phase Outcome Required Now,
  Next-Phase Gate, and Out Of Scope sections; the bootstrap runtime
  writes the minimum-required initial contents this contract pins
  below)
- the target's `.agent-loop/current-task.md` (Codex-owned per-cycle
  planning artifact)
- the target's `.agent-loop/current-phase.md` (Codex-owned per-cycle
  planning artifact)
- the target's `.agent-loop/phase-plan.md` (Codex-owned historical
  phase record)
- the target's `.agent-loop/loop-state.json` (orchestrator-owned
  runtime state)

The bootstrap runtime MUST NOT write any other target-side artifact.
Specifically, the bootstrap surface MUST NOT write:

- any per-cycle Claude / Codex artifact (`.agent-loop/claude-prompt.md`,
  `.agent-loop/claude-summary.md`, `.agent-loop/codex-review.md`,
  `.agent-loop/fix-prompt.md`); these are per-cycle artifacts that
  cycle execution writes, not artifacts the target needs at attach
  time
- any Phase 2A evidence file (`.agent-loop/git-status.log`,
  `.agent-loop/git-diff.patch`, `.agent-loop/test-output.log`,
  `.agent-loop/lint-output.log`, `.agent-loop/typecheck-output.log`,
  `.agent-loop/build-output.log`); these are owned by
  `scripts/run_checks.sh` against the target's working tree
- the target's `.agent-loop/orchestrator.log`; this is initialized
  empty by the first orchestrator invocation against the target, not
  by bootstrap
- any Phase 6 memory subtree entry under `.agent-loop/memory/`
- any Phase 9B PRD-intake / 9C prompt-handoff / 9D review-fix-loop /
  9E long-run-continuation / 9F capacity-retry-state / 9G
  final-acceptance descriptor
- any controller-side artifact in the controller repository
  (including the Phase 10B attach record at
  `.agent-loop/external-target.json`); the attach record is written
  by the Phase 10D attach runtime against the bootstrap-state values
  this contract returns, not by the bootstrap runtime itself
- `AGENTS.md`, `CLAUDE.md`, `ROADMAP.md`, `README.md`, `.gitignore`,
  `.gitattributes`, or any source / instruction file in EITHER root

## Initial Contents Of Each Canonical Artifact

When the bootstrap runtime writes a canonical artifact, it MUST use the
following minimum-required initial contents. The contents are pinned by
this contract so a later Phase 10E runtime slice can write the artifact
without further design decisions and so a reviewer can predict the
on-disk shape of a freshly bootstrapped target.

- `TASK.md`: a Codex-owned planning skeleton carrying the operator-
  supplied Human Objective (no default; the operator MUST supply this
  value at attach time as part of opting into bootstrap), the
  operator-supplied Project Intent (no default), an empty Active
  Phase / Active Sub-Phase / Phase Status / Active Task / Phase
  Outcome Required Now / Next-Phase Gate (each explicitly marked
  `(to be set by first Phase 4C activation)` so a reviewer sees the
  artifact is awaiting first activation), and a single Out Of Scope
  bullet `(to be set by first Phase 4C activation)`. The bootstrap
  runtime MUST NOT invent an active phase / task; the target's first
  phase activation goes through the shipped Phase 4C activator with
  the human-authored `APPROVED_FOR_ACTIVATION` token after bootstrap.
- `.agent-loop/current-task.md`: a Codex-owned planning skeleton
  carrying `# Current Task` plus a single `## Status` body
  `Awaiting first Phase 4C activation; bootstrap initialized the
  target on <UTC ISO-8601 timestamp> on behalf of <bootstrapped_by>.`
- `.agent-loop/current-phase.md`: a Codex-owned planning skeleton
  carrying `# Current Phase` plus a single body line
  `Awaiting first Phase 4C activation`.
- `.agent-loop/phase-plan.md`: a Codex-owned planning skeleton
  carrying `# Phase Plan` plus a single `## Active Phase` body
  `Awaiting first Phase 4C activation`. No historical sub-phase
  entries; the target has no history yet.
- `.agent-loop/loop-state.json`: a JSON object carrying the
  orchestrator's shipped initial-state vocabulary: `phase` = `null`,
  `sub_phase` = `null`, `task` = `null`, `status` =
  `awaiting_first_activation` (a new status the Phase 10E bootstrap
  runtime slice will introduce paired with a
  `docs/halt-and-recovery.md` update at that time; until that slice
  ships, no other shipped status is appropriate for a target that
  has not been activated yet), `cycle_count` = `0`, `max_cycles` =
  the shipped Phase 3A default (`3`), `last_verdict` = `null`,
  `last_verdict_phase` = `null`, `contract_version` = the running
  controller's `contract_version` (so the Phase 3A version-aware
  refusal still fires correctly), `claude_version` = `null`,
  `codex_version` = `null`, `orchestrator_version` = the running
  controller's `ORCHESTRATOR_VERSION`, `approval_mode` =
  `mode_selection.approval_mode` from the operator's attach-time
  selection (the Phase 10B attach record's mode selection drives the
  target's initial approval mode), and `awaiting_human_for` = `null`.

The initial contents are deliberate minimums. The bootstrap runtime
MUST NOT write any additional field, any default beyond the values
listed above, or any speculative phase activation. A reviewer reading
a freshly bootstrapped target's canonical set MUST see "this target
exists, has been bootstrapped, and is waiting for its first Phase 4C
activation" - nothing more.

## Pre-Bootstrap Target States

The bootstrap runtime classifies every operator-supplied target root
into exactly one of four pre-bootstrap states. The classification is
deterministic, fail-closed, and based on canonical-artifact presence
only (the bootstrap runtime MUST NOT consult any other signal):

- **empty_target**: the target root exists as a writable directory,
  the target's `.agent-loop/` directory may or may not exist, and
  ZERO of the canonical artifacts listed in `## Canonical Artifact
  Set The Bootstrap May Write` are present on disk. This is the only
  state in which the bootstrap runtime MAY write the canonical set
  (and only with explicit operator opt-in; see `## Operator Opt-In`
  below). If the `.agent-loop/` directory is absent, the bootstrap
  runtime MAY create it atomically as part of the bootstrap write
  set; if it is present and contains other files (Phase 6 memory
  entries, Phase 9 descriptors, etc.), see `partial_target` below.
- **partial_target**: SOME canonical artifacts are present and OTHERS
  are missing. This state is ALWAYS refused fail-closed; the
  bootstrap runtime MUST NOT auto-complete a partial set. The
  refusal preserves the partial state on disk so the operator can
  inspect it; the operator must explicitly resolve the partial state
  (either by deleting the present artifacts to reduce the target to
  `empty_target`, or by manually completing the canonical set to
  reduce the target to `full_target`) before re-attempting bootstrap
  or attach. The same refusal fires if the `.agent-loop/` directory
  is absent but `TASK.md` is present at the target root, or
  vice-versa, or if any non-canonical file under `.agent-loop/` is
  present without all canonical files (e.g. a Phase 6 memory entry
  with no `loop-state.json` to anchor it).
- **full_target**: ALL canonical artifacts listed above are present
  on disk AND each parses through the shipped Phase 3A schema
  validators (e.g. `loop-state.json` is valid JSON with the required
  fields, `TASK.md` has the required sections, etc.). In this state
  the bootstrap runtime MUST NOT write any artifact; the attach
  runtime records `bootstrap_state.status =
  "target_canonical_set_present"` (the Phase 10B enumeration value
  for "no bootstrap was performed") in the attach record. A
  `full_target` is what the attach runtime hopes to find on every
  attach attempt that the operator did not opt into bootstrap for.
- **malformed_target**: ALL canonical artifacts are present on disk
  BUT one or more fails the shipped Phase 3A schema validators (e.g.
  `loop-state.json` parses as JSON but is missing required keys,
  `TASK.md` is missing required sections, `phase-plan.md` is empty,
  etc.). This state is ALWAYS refused fail-closed; bootstrap MUST
  NOT overwrite an existing canonical artifact under any
  circumstance, even if the existing artifact is malformed. The
  operator must explicitly repair or delete the malformed
  artifact(s) before re-attempting bootstrap or attach. This is the
  contract's load-bearing "bootstrap never overwrites" guarantee.

The four states are exhaustive: every operator-supplied target root
that has been validated against the Phase 10A path-resolution refusals
(target root is a directory, is readable/writable, is not the
controller root, is not nested inside the controller root) maps onto
exactly one of these four states. A fifth case (the target root itself
does not exist, is not a directory, is not readable/writable) is
caught by the Phase 10A pre-classification refusals and never reaches
the bootstrap-state classifier.

## Operator Opt-In

Bootstrap MUST NOT proceed without explicit operator opt-in. Implicit
opt-in (defaulting to bootstrap when the target is empty, inferring
opt-in from CLI flags that mean something else, etc.) is a refusal.
Specifically:

- The Phase 10D attach runtime MUST require a separate `--bootstrap`
  CLI flag (or equivalent attach-time prompt confirmation) before
  passing the bootstrap-runtime invocation. The flag MUST default
  to off; an operator who does not pass it gets the no-bootstrap
  attach path (which refuses fail-closed on any state other than
  `full_target`).
- The opt-in MUST carry an operator identity (the `bootstrapped_by`
  value the bootstrap runtime persists into the attach record's
  `bootstrap_state.bootstrapped_by` field). The runtime MUST NOT
  auto-fill `bootstrapped_by` from `$USER` / `whoami` / any
  environment variable (this mirrors the Phase 10B
  `attached_by` non-auto-fill rule). The operator MUST supply the
  value explicitly via CLI flag (`--bootstrapped-by NAME` or
  equivalent) or attach-time prompt.
- The opt-in MUST carry the operator-supplied initial
  `TASK.md.Human Objective` and `TASK.md.Project Intent` values
  the bootstrap runtime writes into the target's `TASK.md`
  skeleton. The runtime MUST NOT invent a default for either
  field; missing or empty values are a refusal.
- The opt-in MUST be paired with the same `attached_by` value the
  Phase 10B attach record requires; the bootstrap runtime MUST
  refuse fail-closed if `bootstrapped_by != attached_by` so the
  attach and the bootstrap are recorded as a single operator
  action rather than a split-identity attribution.
- The opt-in flag is per-attach (the operator decides at every
  attach whether bootstrap may proceed); there is no persistent
  controller-side opt-in setting that defaults bootstrap on across
  attaches.

## Bootstrap-State Field Schema

The Phase 10B attach-record contract pins the top-level
`bootstrap_state` enumeration (`{"target_canonical_set_present",
"target_canonical_set_bootstrapped"}`) and the matched
`bootstrapped_at` / `bootstrapped_by` timestamp / identity fields.
This Phase 10C contract extends the schema with the following
additional required sub-fields that the bootstrap runtime MUST write
into the attach record when `bootstrap_state.status ==
"target_canonical_set_bootstrapped"` (i.e. bootstrap was performed):

- `bootstrap_state.bootstrap_signal_version` (string): the literal
  `"phase-10c-v1"`. Bumping this string is a deliberate contract
  change that the orchestrator must refuse fail-closed if it does
  not recognize. Mirrors the shipped Phase 9F / 9G / Phase 10B
  signal-version pattern.
- `bootstrap_state.pre_bootstrap_target_state` (string): the
  pre-bootstrap target-state classification the runtime observed
  before writing any artifact. MUST equal `"empty_target"` when
  bootstrap proceeded (the only state where bootstrap is allowed);
  other values are reserved for future contract amendments that
  permit bootstrap from additional states (none are permitted
  today).
- `bootstrap_state.artifacts_written` (list of strings): the
  canonicalized repo-relative paths of every target-side canonical
  artifact the bootstrap runtime wrote. MUST be a sorted list of
  exactly the five paths the bootstrap runtime is allowed to write
  (`TASK.md`, `.agent-loop/current-task.md`,
  `.agent-loop/current-phase.md`, `.agent-loop/phase-plan.md`,
  `.agent-loop/loop-state.json`); any other set is a refusal both
  at write time and at attach-record validation time.
- `bootstrap_state.initial_loop_state_status` (string): the
  `status` value the bootstrap runtime wrote into the target's
  `loop-state.json` (MUST equal `"awaiting_first_activation"` per
  the initial-contents pin above).
- `bootstrap_state.initial_human_objective_excerpt` (string): a
  bounded-string excerpt of the operator-supplied Human Objective
  the bootstrap runtime wrote into the target's `TASK.md`. Capped
  at 200 chars (matches the shipped `attached_by` / `accepted_by`
  bounded-string vocabulary). The excerpt is captured so a
  reviewer can audit the bootstrap-time intent without reading the
  target's `TASK.md` directly.
- `bootstrap_state.bootstrap_log_line` (string): the literal text
  that was appended to the CONTROLLER's `.agent-loop/orchestrator.log`
  at bootstrap time, captured here so a reviewer can reconstruct
  the bootstrap audit trail from either the log or the attach
  record alone (the two MUST agree byte-for-byte for this single
  line). Mirrors the Phase 10B `audit.attach_log_line` pattern.

When `bootstrap_state.status == "target_canonical_set_present"` (i.e.
no bootstrap was performed), the Phase 10C extension fields above are
all `null`. The Phase 10B contract's `bootstrapped_at` /
`bootstrapped_by` fields are also `null` in this case (the Phase 10B
contract already pins that invariant).

## Refusal Behavior

The bootstrap runtime MUST refuse fail-closed in at least the following
cases. Each refusal maps onto a halt status; the Phase 10E runtime slice
that introduces the bootstrap runtime will define the specific
`halted_external_target_bootstrap_*` statuses paired with a
`docs/halt-and-recovery.md` update at that time. The refusal cases this
contract enumerates are:

- the operator did not pass `--bootstrap` (or equivalent opt-in) and
  the pre-bootstrap target state is anything other than `full_target`.
  The refusal message MUST name the observed pre-bootstrap state so
  the operator can decide whether to opt into bootstrap or to repair
  the target manually.
- the operator passed `--bootstrap` and the pre-bootstrap target state
  is `partial_target`. Bootstrap MUST NOT auto-complete a partial
  canonical set; the operator must explicitly resolve the partial
  state before re-attempting.
- the operator passed `--bootstrap` and the pre-bootstrap target state
  is `malformed_target`. Bootstrap MUST NOT overwrite an existing
  canonical artifact even if the operator opts in; the operator must
  explicitly repair or delete the malformed artifact(s) before
  re-attempting. This is the load-bearing "bootstrap never overwrites"
  guarantee.
- the operator passed `--bootstrap` and the pre-bootstrap target state
  is `full_target`. Bootstrap is unnecessary; the attach runtime
  proceeds with `bootstrap_state.status =
  "target_canonical_set_present"` and the bootstrap runtime is not
  invoked. (The CLI MUST treat this as a no-op for bootstrap purposes
  rather than an error; the operator's `--bootstrap` flag is honored
  by the runtime checking whether bootstrap is needed.)
- the operator passed `--bootstrap` but did not supply
  `bootstrapped_by`, supplied an empty `bootstrapped_by`, or supplied
  a `bootstrapped_by` exceeding the 200-char bound.
- the operator passed `--bootstrap` but did not supply the initial
  `TASK.md.Human Objective` or `TASK.md.Project Intent` values, or
  supplied an empty value for either.
- the operator passed `--bootstrap` but `bootstrapped_by !=
  attached_by` (the bootstrap and the attach must record the same
  operator identity).
- the bootstrap write would fail atomicity (the runtime MUST write
  every canonical artifact atomically via temp-write + rename or
  refuse to start the write). Partial writes on disk are NEVER
  acceptable; on any write failure the runtime MUST roll back every
  artifact already written in the same bootstrap call and leave the
  target in `empty_target` state.
- the target root canonicalizes to the controller root (the Phase 10A
  same-root refusal still applies at bootstrap time, not only at
  attach time).
- the target root is nested inside the controller root (the Phase 10A
  nesting refusal still applies at bootstrap time).
- the target root is not a writable directory.

## Approval Gates

The bootstrap contract preserves every shipped human-approval gate
(Phase 10A + 10B enumeration):

- bootstrap is an explicit operator action via a separate opt-in flag;
  the runtime MUST NOT auto-bootstrap on attach.
- per-target phase activation continues to require the shipped Phase
  4C activator + `APPROVED_FOR_ACTIVATION` token; bootstrap initializes
  the target's canonical set but does NOT activate the first phase.
  The bootstrapped target sits at `loop-state.status =
  "awaiting_first_activation"` until the operator runs the shipped
  activator against the target.
- per-target `APPROVED_FOR_HUMAN_REVIEW` terminals continue to halt
  the target-side loop and require explicit human approval before the
  next phase begins. Bootstrap does NOT short-circuit this.
- the Phase 9G final human acceptance gate continues to require an
  explicit operator action on the target's canonical artifact set;
  bootstrap never records final acceptance.
- selecting the Phase 9 fully autonomous PRD-to-product mode on a
  target is an explicit per-attach decision (the Phase 10B attach
  record carries `mode_selection.approval_mode`); bootstrap honors
  whichever mode the operator selected but never widens autonomy past
  the explicit selection.

## Audit Expectations

A reviewer reading the controller's `.agent-loop/orchestrator.log` plus
the Phase 10B attach record's `bootstrap_state` sub-object MUST be able
to reconstruct what the bootstrap did, when, by whom, against which
pre-bootstrap target state, and which canonical artifacts were written.
Specifically:

- the controller writes one `external target: bootstrapped ...` audit
  line per bootstrap event, naming the canonicalized target path, the
  pre-bootstrap target state, the operator identity, and the list of
  canonical artifacts written. The literal text of that line MUST land
  in `bootstrap_state.bootstrap_log_line` so the two sources agree
  byte-for-byte (mirrors the Phase 10B `audit.attach_log_line`
  pattern).
- every refusal-mode bootstrap attempt logs a separate
  `external target: bootstrap refused ...` audit line naming the
  refusal status and reason. Refusals never produce a partial bootstrap
  on disk; the audit trail is the only persistent record of a refused
  bootstrap attempt.
- the bootstrap-success audit line MUST include the literal
  `bootstrap_signal_version` value (`"phase-10c-v1"`) so a reviewer
  can correlate the log against the contract version that produced
  it.

## Source-Of-Truth Preservation

Canonical artifacts on disk remain authoritative; the bootstrap runtime
extends the canonical set rather than introducing advisory state:

- the bootstrap runtime writes ONLY canonical target-side artifacts;
  it does NOT write any advisory descriptor or in-process cache.
- the Phase 10B attach record remains canonical for the attach
  metadata; the `bootstrap_state` sub-object is the canonical record
  of "was bootstrap performed, by whom, when, against which
  pre-bootstrap state, writing which artifacts".
- the target's `.agent-loop/loop-state.json` remains canonical for
  the target's phase / sub_phase / task / cycle_count / status / etc.
  once activation begins; the bootstrap-state record never shadows
  these fields.
- any external UI surface, dashboard, or notification stream (Phase
  10G and later) that surfaces bootstrap metadata MUST treat the
  on-disk attach record and target-side canonical artifacts as
  authoritative and any in-process cache or notification stream as
  advisory.

## Safety Boundaries

The future bootstrap runtime MUST refuse to:

- commit, push, tag, branch, stash, reset, checkout, or otherwise
  mutate Git history or working-tree state in either the controller
  or the target (the shipped no-Git-automation boundary applies to
  BOTH roots, mirroring the Phase 10A / 10B contracts).
- modify `AGENTS.md`, `CLAUDE.md`, `ROADMAP.md`, `README.md`, or any
  controller-owned contract file as a side effect of bootstrapping a
  target.
- overwrite any existing target-side canonical artifact (the
  load-bearing "bootstrap never overwrites" guarantee; even a
  malformed canonical artifact MUST NOT be overwritten by bootstrap).
- write any target-side artifact outside the five canonical paths
  this contract enumerates. Per-cycle Claude / Codex artifacts,
  Phase 2A evidence files, Phase 6 memory entries, Phase 9
  descriptors, and the target's `.agent-loop/orchestrator.log` are
  out of scope for bootstrap (each is initialized by its
  responsible runtime surface, not by bootstrap).
- write the controller's own canonical artifacts into the target (the
  Phase 10A "never copy controller's canonical artifacts into a
  target" rule).
- write a partial canonical set on a failure (atomic write or
  rollback; never partial).
- silently widen autonomy by defaulting bootstrap on or by
  auto-filling `bootstrapped_by` from environment-supplied identity.
- proceed with bootstrap when `attached_by != bootstrapped_by` (the
  attach and the bootstrap must record the same operator identity in
  a single attach session).
- introduce concurrent bootstraps in this contract (single-target,
  single-bootstrap-per-attach); a future Phase 10 slice that
  introduces concurrent attaches will extend this contract with an
  explicit concurrent-bootstrap schema.

## Dependencies On Later Phase 10 Slices

The bootstrap contract is load-bearing for the following later Phase
10 sub-phases:

- Phase 10D (Attach / Detach Runtime) consumes this contract during
  attach. On every attach attempt, the attach runtime classifies the
  pre-bootstrap target state per `## Pre-Bootstrap Target States` and
  branches: a `full_target` produces the no-bootstrap attach path
  (`bootstrap_state.status = "target_canonical_set_present"`); an
  `empty_target` with operator opt-in invokes the Phase 10E
  bootstrap runtime; a `partial_target` or `malformed_target`
  refuses fail-closed regardless of opt-in. The attach runtime
  records the bootstrap-state extension fields this contract
  enumerates into the Phase 10B attach record's `bootstrap_state`
  sub-object before finalizing the attach.
- Phase 10E (External Target Bootstrap Runtime) satisfies this
  contract. The runtime introduces a new
  `halted_external_target_bootstrap_*` halt-status family (specific
  values determined by the Phase 10E slice) paired with a
  `docs/halt-and-recovery.md` update at that time. The runtime
  honors every refusal case this contract enumerates and the
  atomic-or-rollback write guarantee.
- Phase 10F (Target-Side Cycle Dispatch) consumes a
  fully-bootstrapped target (i.e. a target whose `loop-state.status`
  has advanced from `awaiting_first_activation` to a normal cycle
  status via the shipped Phase 4C activator + `APPROVED_FOR_ACTIVATION`
  flow). The dispatch runtime does NOT bootstrap; it requires the
  target to have been bootstrapped + activated already.
- Phase 10G (External UI / Dashboard / Run-Control) surfaces
  bootstrap-state metadata advisory-only from the canonical attach
  record.

## Out Of Scope For Phase 10C

Phase 10C is documentation / contract only. The shipped Phase 1 - 9
runtime behavior is preserved unchanged by this slice; no
orchestrator, planner, activator, evidence-collection, review-routing,
checkpoint, continuation, memory, runtime-adapter, LangChain, VS Code,
Phase 9 autonomous-PRD, capacity-reprobe, final-acceptance, or
external-workspace feature work is introduced. Adding the runtime that
writes the target-side canonical set this contract defines is the work
of Phase 10E; consuming this contract during attach is the work of
Phase 10D; documenting the new `halted_external_target_bootstrap_*`
halt statuses in `docs/halt-and-recovery.md` is the work of the Phase
10E slice that introduces them. The
`awaiting_first_activation` `loop-state.status` value this contract
references is also introduced by Phase 10E (the bootstrap runtime is
the only writer of that value); no shipped status fits a target that
has been bootstrapped but never activated, so a new status is
required.
