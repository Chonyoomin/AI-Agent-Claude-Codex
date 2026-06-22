# External Target Attach Record Contract

## Status

Phase 10B defines this contract. The attach/detach runtime that writes,
reads, and refreshes the controller-owned attach record is NOT yet
implemented. The contract below specifies the schema-stable fields the
attach record MUST carry, how canonicalized target paths and controller
identity are represented, what audit / refusal / stale-detection metadata
must be persisted, which fields are canonical versus advisory, and which
later Phase 10 runtime slices depend on the record. Implementation of the
attach / detach runtime is deferred to later Phase 10 sub-phases:

- Phase 10C: external target bootstrap contract (target-side canonical
  artifact set bring-up; refusal behavior when bootstrap is incomplete)
- Phase 10D: attach / detach runtime (the CLI + library that writes and
  reads the attach record this contract defines)
- Phase 10E: target bootstrap runtime (the CLI + library that satisfies
  the Phase 10C contract)
- Phase 10F and later: target-side cycle dispatch, run-control,
  concurrent execution, MCP integration, RAG layer, GitHub integration,
  model-policy extensibility (each its own later Phase 10 sub-phase
  tracked in `ROADMAP.md`)

## Scope

This document is the contract the future Phase 10D attach / detach runtime
must satisfy when it writes the controller-owned attach record. It is NOT
a description of currently shipped runtime behavior. The shipped
repository today has no attach record on disk; the controller and target
roots are the same directory (the shipped self-targeting mode the Phase
10A contract preserves).

The attach record is the controller-owned source of truth for "which
target is the controller currently attached to, when, by whom, in which
mode, with what bootstrap state, against which controller identity". The
contract below pins its schema, write boundary, validation, and refusal
behavior so a later Phase 10D runtime slice can be implemented from this
contract without further design decisions.

## Distinction From Other Shipped Artifacts

The attach record is NOT one of the existing canonical artifacts. The
shipped Phase 1 - 9 system already defines these distinct artifact roles
which the attach record MUST NOT overlap or replace:

- `.agent-loop/loop-state.json` is per-target orchestrator state. The
  attach record does not store target-side `phase`, `sub_phase`, `task`,
  `cycle_count`, `status`, `last_verdict`, or any field the shipped
  Phase 3A Orchestrator Contract names. The attach record points AT the
  target whose `loop-state.json` is canonical; it never substitutes
  for it.
- `.agent-loop/orchestrator.log` is the per-target audit trail.
  Controller-side attach events are recorded in the CONTROLLER's
  orchestrator log; the attach record is the structured single-document
  source of truth that the audit log lines reference.
- `.agent-loop/capacity-retry-state.json` (Phase 9F) and
  `.agent-loop/final-acceptance.json` (Phase 9G) are target-side
  per-cycle artifacts. The attach record is controller-side and
  per-attach (not per-cycle).
- `.agent-loop/claude-done.json` (Phase 5B) is a routing signal, not
  proof of correctness; the attach record is canonical for "is the
  controller currently attached" rather than advisory.
- `.agent-loop/external-target.json` is the name the Phase 10A
  contract assigned to this controller-owned attach record. This Phase
  10B contract is the schema specification for that file.

## Canonical Location

The attach record lives at `.agent-loop/external-target.json` in the
CONTROLLER repository. It is written and read by the controller; it is
never written by the target. The path is fixed by the Phase 10A contract
and not configurable: a per-attach override (e.g. `--attach-record-path`)
would split the source of truth across multiple files and is explicitly
forbidden by this contract.

When no external target is attached, the file is absent from disk. An
empty or partially-written file is a refusal condition, not a "not
attached" signal: absence and presence-but-incomplete are distinct cases
(see `## Refusal Behavior` below).

## Required Fields

The attach record MUST be a single JSON object with the following
top-level fields, all required and all schema-stable across releases:

- `attach_record_signal_version` (string): the literal
  `"phase-10b-v1"`. Bumping this string is a deliberate contract change
  that the orchestrator must refuse fail-closed if it does not recognize.
  This mirrors the shipped `retry_signal_version = "phase-9f-v1"` and
  `acceptance_signal_version = "phase-9g-v1"` pattern.
- `attached_at` (string): UTC ISO-8601 timestamp of when the attach was
  performed (e.g. `"2026-06-21T17:42:08Z"`). Written once on attach;
  never mutated by detach (detach removes the file).
- `attached_by` (string): the canonical record of WHO attached. Non-empty
  string, capped at 200 characters (matches the shipped
  `FINAL_ACCEPTANCE_MAX_ACCEPTED_BY_LENGTH` cap so a single bounded-
  string vocabulary applies across attach and acceptance). The value is
  operator-supplied (CLI flag or attach-time prompt); the runtime MUST
  NOT auto-fill from environment variables like `$USER` because the
  attach-record must reflect the operator's deliberate identity claim,
  not an implicit machine identity.
- `target_path_canonical` (string): the operator-supplied target root
  AFTER `Path.resolve()` canonicalization. This is the load-bearing
  source of truth for "which directory the controller is currently
  attached to". The runtime MUST resolve and store this value at
  attach time (not the raw operator-supplied string) so a later
  staleness probe can re-canonicalize and compare; the operator's raw
  input is captured separately so a refusal message can reproduce
  exactly what the operator typed.
- `target_path_raw` (string): the operator-supplied target root BEFORE
  canonicalization. Captured for audit / refusal-message reproducibility
  only; the runtime MUST NOT use this field for any path comparison.
- `controller_path_canonical` (string): the controller root AFTER
  `Path.resolve()` canonicalization (i.e. the result of
  `find_repo_root()` against the running orchestrator). Used by the
  staleness probe to verify the same controller still owns the attach
  and to refuse fail-closed when a stale attach record names a
  controller path that no longer matches the running orchestrator.
- `controller_identity` (object): a structured identifier for the
  controller that performed the attach. Required sub-fields:
  - `controller_identity.repo_signature` (string): a stable opaque
    identifier the controller can re-derive on demand (suggested:
    SHA-256 of the canonicalized controller path, hex-encoded). The
    runtime MUST NOT use the controller's working-tree state (file
    mtimes, uncommitted changes, etc.) so the signature is stable
    across implementation-cycle file edits.
  - `controller_identity.orchestrator_version` (string): the
    `ORCHESTRATOR_VERSION` constant the running orchestrator reports
    (e.g. the shipped `"phase-3d-v0"`). Matches the existing
    `loop-state.orchestrator_version` field's vocabulary.
  - `controller_identity.contract_version` (string): the
    `loop-state.contract_version` value the controller is running at
    attach time (e.g. the shipped `"phase-3a-v2"`). Captured so a
    stale-attach probe can refuse fail-closed when the running
    controller has since bumped its contract version past what the
    attach record was written under.
- `mode_selection` (object): the explicit per-attach mode selection.
  Required sub-fields:
  - `mode_selection.approval_mode` (string): one of the shipped Phase
    5A approval modes (`"review"`, `"strict"`, `"autonomous"`) OR the
    explicit `"phase_9_autonomous_prd"` marker indicating the future
    Phase 9 fully autonomous PRD-to-product mode the autonomy contract
    defines. The runtime MUST refuse fail-closed when the value is any
    other string; the four-value set is the complete enumeration this
    contract defines.
  - `mode_selection.selected_at` (string): UTC ISO-8601 timestamp of
    when the mode was selected. Equal to `attached_at` when the
    operator selects the mode at attach time; a future Phase 10F
    runtime slice may allow per-attach mode changes by bumping this
    timestamp and writing a new attach record (no in-place mode flip).
  - `mode_selection.selected_by` (string): WHO selected the mode (same
    200-char bounded vocabulary as `attached_by`). The runtime MUST
    enforce equality with `attached_by` in this Phase 10B contract;
    later slices that allow mode flips will introduce a separate
    `mode_flip_record` artifact rather than mutating this field.
- `bootstrap_state` (object): the bootstrap-state record (the Phase 10C
  bootstrap contract pins the field-level schema; Phase 10B defines the
  top-level enumeration the attach record must carry). Required
  sub-fields:
  - `bootstrap_state.status` (string): one of
    `"target_canonical_set_present"` (the target already had the full
    canonical artifact set at attach time; no bootstrap was performed)
    or `"target_canonical_set_bootstrapped"` (the operator opted into
    bootstrap and the canonical artifact set was created at attach
    time). The runtime MUST refuse fail-closed when the value is any
    other string; the partial-canonical-set + no-opt-in case never
    produces an attach record in the first place (the Phase 10A
    contract makes that case a pre-attach refusal).
  - `bootstrap_state.bootstrapped_at` (string or null): UTC ISO-8601
    timestamp when bootstrap was performed; `null` when no bootstrap
    was performed (i.e. `status == "target_canonical_set_present"`).
  - `bootstrap_state.bootstrapped_by` (string or null): WHO performed
    the bootstrap; `null` when no bootstrap was performed.
- `stale_attach_detection` (object): inputs the staleness probe uses
  to refuse fail-closed on a controller / target divergence the
  operator did not intend. Required sub-fields:
  - `stale_attach_detection.target_marker_files_at_attach` (list of
    strings): the canonical artifact paths the controller observed
    present on the target at attach time (suggested: the same
    canonical artifact set the Phase 10A contract names for the
    target). The probe re-reads these paths on every controller
    invocation and refuses fail-closed when the on-disk set has
    diverged (e.g. the target's `TASK.md` was deleted out from under
    the attach, or the target was move-renamed).
  - `stale_attach_detection.target_path_canonical_at_attach` (string):
    captured at attach time so the probe can compare against a fresh
    canonicalization. Equal to `target_path_canonical` when the
    attach is fresh; a later detach + re-attach overwrites both. The
    duplication is intentional: a future contract amendment may need
    to evolve the canonical-path representation, and keeping the
    attach-time snapshot separate from the live field lets the
    runtime detect the divergence without losing either value.
  - `stale_attach_detection.controller_path_canonical_at_attach`
    (string): captured at attach time; mirrors the target-side field
    above for the controller path.
- `audit` (object): structured audit metadata for the attach event.
  Required sub-fields:
  - `audit.attach_log_line` (string): the literal text that was
    appended to the CONTROLLER's `.agent-loop/orchestrator.log` at
    attach time, captured here so a reviewer can reconstruct the
    audit trail from either the log or the attach record alone (the
    two MUST agree byte-for-byte for this single line).
  - `audit.refusal_history` (list of objects, possibly empty): a
    bounded list of prior attach attempts that refused fail-closed
    on this attach session. Each entry is
    `{"attempted_at": <ISO-8601>, "refusal_status": <halt_status>,
    "refusal_reason": <bounded string>}`. The list is capped at 32
    entries; entries beyond the cap are dropped from the head (newest
    32 kept). Operators with no refusal history get an empty list,
    not a missing field.
- `canonical_precedence_note` (string): the literal
  `ATTACH_RECORD_CANONICAL_PRECEDENCE_NOTE` reminder string the
  runtime hardcodes. Matches the shipped
  `FINAL_ACCEPTANCE_CANONICAL_PRECEDENCE_NOTE` and
  `CAPACITY_RETRY_CANONICAL_PRECEDENCE_NOTE` pattern so every
  controller-owned Phase 9 / 10 artifact carries the same
  load-bearing reminder that canonical artifacts win over advisory
  descriptors.

The contract intentionally does NOT define optional / advisory fields in
this slice. A future Phase 10D runtime slice that needs to record
additional advisory data MUST add the field to this contract as a
schema-stable extension (signal-version bump) rather than write
undeclared fields into the attach record.

## Canonical Versus Advisory Fields

Every required field above is CANONICAL for the attach: the runtime MUST
treat each field's value as load-bearing for the attach-record
validation, refusal, and staleness probes. There are no advisory fields
in the Phase 10B attach record.

The attach record itself is canonical at the controller-side ownership
boundary the Phase 10A contract pins (controller owns the attach
record; target owns its own per-target canonical artifact set). A
future external UI / dashboard (Phase 10G or later) that surfaces attach
metadata MUST treat the on-disk attach record as authoritative and any
in-process cache or notification stream as advisory.

## Path Canonicalization

The runtime MUST use `Path.resolve()` (or its language equivalent) on
every operator-supplied target / controller path BEFORE the path is
stored, compared, or refused. Specifically:

- `target_path_canonical` is computed by calling `Path.resolve()` on
  the operator-supplied target root at attach time. The result is
  what the runtime stores.
- `target_path_raw` captures the literal operator input (after stripping
  trailing whitespace; no other normalization). It exists solely for
  refusal-message reproducibility.
- `controller_path_canonical` is computed by calling `Path.resolve()`
  on the result of `find_repo_root()` against the running orchestrator
  at attach time. The shipped `find_repo_root()` is the authoritative
  controller-root discovery primitive; the attach record MUST NOT
  re-implement it.
- All path comparisons (same-root refusal, nesting refusal,
  staleness probe, controller-identity continuity) operate on the
  canonicalized values. Raw paths MUST NOT participate in any safety
  check.

A symlink whose canonical resolution coincides with the controller root
fails the same-root refusal. A relative path supplied at attach time is
canonicalized against the current working directory at attach time, and
the canonicalized value is what the staleness probe later compares
against: a subsequent attach attempt from a different working directory
that resolves to the same canonical path is treated as the same target.

## Audit Expectations

A reviewer reading the controller's `.agent-loop/orchestrator.log` plus
the on-disk attach record MUST be able to reconstruct what the attach
did, when, by whom, in which mode, with what bootstrap state, and which
prior attempts (if any) refused fail-closed before the successful
attach landed. Specifically:

- the controller writes one `external target: attached ...` audit line
  per attach event, naming the canonicalized target path, the
  controller identity, the selected mode, the bootstrap state, and the
  `attached_by` value. The literal text of that line MUST land in
  `audit.attach_log_line` so the two sources agree.
- every refusal-mode pre-attach attempt logs a separate
  `external target: refused ...` audit line naming the refusal status
  and reason. Those lines are not duplicated into the attach record (no
  attach record exists on a refusal) but their text MUST match the
  vocabulary the attach record's `audit.refusal_history` uses if and
  when the attach finally succeeds.
- the controller's `.agent-loop/orchestrator.log` line for the
  successful attach MUST include the literal `attach_record_path`
  value (`.agent-loop/external-target.json`) so a reviewer can trace
  the audit line back to the persisted record.

## Refusal Behavior

The runtime that writes the attach record MUST refuse fail-closed in at
least the following cases. Each refusal corresponds to a specific halt
status; Phase 10B introduces no new halt status of its own (every
refusal here maps onto a shipped halt-vocabulary term or onto a
forward-referenced `halted_external_target_*` status the Phase 10C
bootstrap contract or the Phase 10D attach runtime will introduce paired
with a `docs/halt-and-recovery.md` update at that time):

- the attach record file already exists on disk (controller is already
  attached) and the operator did not pass an explicit detach-first
  signal. The refusal uses the Phase 10A contract's `already attached`
  vocabulary; the existing record is left untouched.
- the attach record file is partially written (parses as malformed
  JSON, or parses as JSON but is missing any required field, or has
  the wrong type on any required field, or has an
  `attach_record_signal_version` the running orchestrator does not
  recognize). The refusal preserves the partial file on disk so an
  operator can inspect it; the operator must explicitly delete the
  partial file to retry, which leaves a manual audit trail.
- the operator-supplied target root canonicalizes to the same path as
  the controller root (the Phase 10A `same as the controller root`
  refusal).
- the operator-supplied target root canonicalizes to a path nested
  inside the controller root (the Phase 10A `nested inside the
  controller` refusal).
- the operator did not supply `attached_by`, supplied an empty
  `attached_by`, or supplied an `attached_by` exceeding the 200-char
  bound.
- the operator-supplied `mode_selection.approval_mode` is not one of
  the four declared values.
- the operator-supplied `bootstrap_state.status` is not one of the two
  declared values (or `status == "target_canonical_set_bootstrapped"`
  is paired with `bootstrapped_at == null` or `bootstrapped_by ==
  null`, or `status == "target_canonical_set_present"` is paired with
  non-null bootstrap timestamps).
- the controller identity sub-object is missing a required sub-field,
  has a wrong type on a required sub-field, or names an
  `orchestrator_version` / `contract_version` the running orchestrator
  does not recognize.
- the staleness probe (run on every controller invocation while the
  attach record is present) detects that `target_path_canonical` no
  longer matches the on-disk target (target moved or renamed), or
  detects that one or more
  `stale_attach_detection.target_marker_files_at_attach` paths are no
  longer present on the target, or detects that
  `controller_path_canonical` no longer matches the running
  orchestrator's controller root. Each is a separate refusal-reason
  string in `audit.refusal_history` (and in the corresponding
  `orchestrator.log` line) so the operator can tell them apart.

## Approval Gates

The attach-record contract preserves every shipped human-approval gate
(Phase 10A enumeration):

- writing the attach record is itself an explicit operator action; the
  controller MUST NOT auto-attach on startup or on any background
  event.
- the attach record's `mode_selection.approval_mode` is explicit and
  operator-supplied; defaulting it to `"autonomous"` or
  `"phase_9_autonomous_prd"` without operator input is a refusal.
- per-target phase activation continues to require the shipped Phase
  4C activator + `APPROVED_FOR_ACTIVATION` token; the attach record
  does NOT activate a target-side phase.
- per-target `APPROVED_FOR_HUMAN_REVIEW` terminals continue to halt
  the target-side loop and require explicit human approval before the
  next phase begins.
- the Phase 9G final human acceptance gate continues to require an
  explicit operator action on the target's canonical artifact set;
  the attach record never records final acceptance and never bypasses
  the Phase 9G gate.

## Source-Of-Truth Preservation

Canonical artifacts on disk remain authoritative; the attach record is
controller-owned canonical for "which target is the controller attached
to right now" and nothing more:

- the attach record is canonical for the attach metadata it carries
  (target path, controller identity, mode selection, bootstrap state,
  audit, refusal history).
- the target's `.agent-loop/loop-state.json` remains canonical for
  the target's phase / sub_phase / task / cycle_count / status /
  last_verdict / awaiting_human_for; the attach record MUST NOT
  cache or shadow these fields.
- the target's `.agent-loop/orchestrator.log` remains canonical for
  the per-target audit trail; the attach record's audit subsection
  records only controller-side attach events.
- the controller's `.agent-loop/orchestrator.log` is canonical for
  the controller-side audit history (every attach / refusal /
  staleness event lands there); the attach record duplicates the
  single successful attach line into `audit.attach_log_line` for
  byte-for-byte cross-reference.

## Safety Boundaries

The future attach record writer MUST refuse to:

- commit, push, tag, branch, stash, reset, checkout, or otherwise
  mutate Git history or working-tree state in either the controller
  or the target (the shipped no-Git-automation boundary applies to
  BOTH roots, mirroring the Phase 10A contract).
- modify `AGENTS.md`, `CLAUDE.md`, `ROADMAP.md`, or any
  controller-owned contract file as a side effect of writing the
  attach record.
- write any field outside the schema this contract enumerates.
  Undeclared fields are a contract change, not a runtime extension.
- read or write any path on the target side as part of writing the
  attach record (the attach record is controller-side only; target-
  side artifact reads belong to the Phase 10C bootstrap contract and
  the Phase 10D / 10E attach / bootstrap runtime slices, not to the
  attach-record write).
- write a partial attach record on a failure (the runtime MUST write
  atomically: write to a temporary path and rename into place, or
  refuse to start the write if atomicity cannot be guaranteed).
- silently widen autonomy by defaulting `mode_selection.approval_mode`
  to `"autonomous"` or `"phase_9_autonomous_prd"` without operator
  input.
- silently auto-fill `attached_by` from `$USER`, `whoami`, or any
  other environment-supplied identity. The operator MUST supply the
  value explicitly.
- introduce concurrent attaches in this contract (single-target,
  single-attach-record); a future Phase 10 slice that introduces
  concurrent attaches MUST extend this contract with an explicit
  multi-attach schema.

## Dependencies On Later Phase 10 Slices

The attach record's schema is load-bearing for the following later
Phase 10 sub-phases:

- Phase 10C (External Workspace Bootstrap Contract) reads
  `bootstrap_state.status` to decide whether the bootstrap runtime
  must run at attach time, and writes the values back into the
  attach record's `bootstrap_state` sub-object before the attach
  record is finalized.
- Phase 10D (Attach / Detach Runtime) writes the attach record on
  attach and removes it on detach; the detach runtime MUST refuse
  fail-closed when the attach record's `controller_path_canonical`
  does not match the running orchestrator (a controller-mismatch
  detach would leave the original controller pointing at a target
  the other controller already released).
- Phase 10E (Target Bootstrap Runtime) satisfies the Phase 10C
  contract and writes the `bootstrap_state.bootstrapped_at` /
  `bootstrapped_by` values when a bootstrap is performed.
- Phase 10F (Target-Side Cycle Dispatch) reads
  `target_path_canonical` and `mode_selection.approval_mode` to
  route a target-side cycle through the shipped Phase 5 approval-
  mode runtime semantics (per-target, not at the controller level).
- Phase 10G (External UI / Dashboard / Run-Control) reads the full
  attach record as the source of truth for "which target is
  attached, in which mode, since when, by whom" and surfaces those
  values advisory-only to the UI.

## Out Of Scope For Phase 10B

Phase 10B is documentation / contract only. The shipped Phase 1 - 9
runtime behavior is preserved unchanged by this slice; no
orchestrator, planner, activator, evidence-collection, review-routing,
checkpoint, continuation, memory, runtime-adapter, LangChain, VS Code,
Phase 9 autonomous-PRD, capacity-reprobe, final-acceptance, or
external-workspace feature work is introduced. Adding the runtime
that writes / reads / refreshes the attach record this contract
defines is the work of Phases 10D and later; adding the bootstrap
contract that the `bootstrap_state` sub-object delegates to is the
work of Phase 10C.
