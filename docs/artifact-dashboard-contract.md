# Artifact Dashboard Contract

## Status

Phase 10J defines this contract. No artifact dashboard runtime,
analytics backend, diff viewer, history explorer, or approval-action
runtime ships in this slice. The contract below specifies the FIRST
external artifact dashboard surface for external-workspace mode:
which review summaries, diff views, progress history, approval
actions, token/cost reporting, and failure analytics the dashboard
MAY surface; which values are canonical mirrors versus advisory
derived state; which mutating operations remain CLI-only and MUST
NOT be silently triggered from the dashboard; how the dashboard MUST
defer to canonical repo artifacts on disk instead of creating a
competing control plane, state store, or alternate audit record; and
which boundaries are preserved from the shipped Phase 1 - 9 system,
the Phase 10A - 10F external-workspace slices, and the Phase 10G -
10I external UI surfaces. Implementation of an artifact dashboard
runtime is deferred to later Phase 10 sub-phases:

- Phase 10K: Artifact Dashboard Runtime Initial Slice (the bounded
  read-side dashboard that satisfies this contract by surfacing
  canonical review/diff/history/token/failure artifacts, plus
  copy-paste-only approval-action affordances; no mutation, no CLI
  dispatch from the dashboard beyond the existing Phase 10I
  library-call delegation surface)
- Phase 10L and later: additional dashboard capabilities tracked in
  `ROADMAP.md` (controlled-concurrency awareness, per-target
  activity stream extensions, advisory diff-rendering refinements)

## Scope

This document is the contract the future Phase 10K artifact
dashboard runtime MUST satisfy when it is implemented. It is NOT a
description of currently shipped runtime behavior. The shipped
repository today exposes the bounded external UI read-only status
surface (Phase 10H `view-external-status` + `build_external_ui_status_view(...)`)
and the bounded external UI run/resume controls surface (Phase 10I
`view-external-controls` + `invoke-external-control` +
`build_external_ui_control_view(...)`); every operator workflow
beyond those bounded reads runs through the shipped CLI
(`python scripts/agent_loop.py ...`) and every canonical artifact
write happens through the shipped library functions the CLI
dispatches to.

The dashboard contract is the load-bearing specification for "what
a future artifact dashboard MAY render", "which on-disk artifacts
it MAY read", "which values it MAY surface only as advisory
derived state", "which mutating operations the dashboard MUST NOT
silently trigger", and "how the dashboard MUST preserve the
canonical-artifact-first source-of-truth model". The contract pins
the read-only artifact set the dashboard is allowed to consume, the
six required dashboard surfaces (review summaries, diff views,
progress history, approval actions, token/cost reporting, failure
analytics), the canonical-vs-advisory mirror rule for each surface,
the CLI-only operation list, the refusal behavior, and the
boundaries the dashboard MUST preserve so a later Phase 10K runtime
slice can be implemented from this contract without further design
decisions and without collapsing the shipped CLI-first workflow
into a parallel dashboard control plane.

## Distinction From Shipped Artifacts And Surfaces

The artifact dashboard is NOT one of the existing shipped surfaces.
The shipped Phase 1 - 9 system, the Phase 10A - 10F
external-workspace slices, and the Phase 10G - 10I external UI
surfaces already define these distinct surface roles which the
dashboard contract MUST NOT overlap or replace:

- The shipped `python scripts/agent_loop.py ...` CLI is the
  canonical operator entry point for every mutating workflow. The
  dashboard MUST NOT replace, wrap, or shadow these CLI surfaces;
  the dashboard MAY display the canonical artifacts those CLI
  surfaces write but MUST NOT trigger them.
- The shipped Phase 10G external UI contract (`docs/external-ui-contract.md`)
  pins the load-bearing UI boundaries (canonical artifact read set,
  advisory-vs-canonical mirror rule, CLI-only operations,
  no-auto-fill operator identity, refusal behavior,
  source-of-truth preservation, safety boundaries, approval gates,
  audit expectations). The dashboard contract EXTENDS those
  boundaries to the six dashboard surfaces; it MUST NOT relax any
  of them. Every read-set / advisory-mirror / CLI-only /
  no-auto-fill / refusal / source-of-truth / safety / approval /
  audit rule in `docs/external-ui-contract.md` continues to apply
  to the dashboard verbatim.
- The shipped Phase 10H `view-external-status` surface is the
  canonical read-only status view. The dashboard MAY render the
  same view-model dict (returned by `build_external_ui_status_view(...)`)
  but MUST NOT invent a parallel status model.
- The shipped Phase 10I `view-external-controls` + `invoke-external-control`
  surfaces are the canonical bounded control affordance layer. The
  dashboard MAY render the same control registry (returned by
  `build_external_ui_control_view(...)`) and MAY delegate the same
  three library-callable read-only controls via the same
  `ExternalUiControlRefusal`-based refusal path. The dashboard
  MUST NOT introduce additional library-callable controls; the
  dashboard MUST NOT change the refusal vocabulary; the dashboard
  MUST NOT dispatch any mutating CLI subcommand on the operator's
  behalf.
- The shipped Phase 4C activator + the human-authored
  `APPROVED_FOR_ACTIVATION` token is the canonical path that
  activates a phase. The dashboard MUST NOT issue, forge,
  auto-fill, or prompt for that token in any dashboard form.
- The Phase 9G final human acceptance gate is the canonical path
  that records human acceptance via the shipped
  `record-final-acceptance` CLI. The dashboard MUST NOT record
  acceptance; the dashboard MAY display the on-disk acceptance
  artifact's contents as advisory.

## Dashboard Surfaces

The artifact dashboard MUST render exactly the following six
operator-facing surfaces. Every surface MUST distinguish canonical
mirrors (verbatim renderings of on-disk artifact values, attributed
to the source artifact, refreshed per poll) from advisory derived
state (dashboard-computed values from canonical mirrors that MUST
be marked as advisory). The dashboard MUST NOT introduce a seventh
surface, MUST NOT merge two of these surfaces into a single
"super-view" that hides which artifact is the source, and MUST NOT
silently skip a surface whose underlying artifacts are missing
(missing artifacts surface as advisory "not yet present" state,
not as a hidden surface).

### 1. Review Summaries

Source artifacts (canonical mirrors):

- `.agent-loop/claude-summary.md` (the per-cycle Claude
  Implementation Summary; Claude-owned, structured per the
  CLAUDE.md "Structured Summary Requirement" section)
- `.agent-loop/codex-review.md` (the per-cycle Codex review;
  Codex-owned, structured per the project review-format)
- `.agent-loop/fix-prompt.md` when present (the Codex-emitted fix
  prompt during a fix cycle)

What the dashboard MAY render:

- the full structured Markdown body of each artifact, with
  source-artifact attribution
- a per-cycle "review timeline" advisory derived state that orders
  the three artifacts by their last-modified UTC timestamp
- a one-line "current verdict" advisory derived state extracted
  from the most recent `codex-review.md` (`APPROVED_FOR_HUMAN_REVIEW` /
  `NEEDS_FIXES` / `FAILED_REQUIRES_HUMAN`); the canonical verdict
  remains the on-disk `codex-review.md` content

What the dashboard MUST NOT do:

- parse the agents' stdout/stderr for the verdict (canonical
  source-of-truth model: the on-disk artifact is authoritative)
- inline-edit any of the three artifacts; edits MUST happen
  through the shipped CLI (Claude / Codex re-invocation) or via
  an operator's direct text editor against the on-disk file
- silently merge `claude-summary.md` and `codex-review.md` into a
  combined "review record" that loses which agent emitted which
  section

### 2. Diff Views

Source artifacts (canonical mirrors):

- `.agent-loop/git-diff.patch` (the per-cycle git working-tree
  diff captured by `scripts/run_checks.sh`)
- `.agent-loop/git-status.log` (the per-cycle git status capture)

What the dashboard MAY render:

- the full text of `git-diff.patch` with syntax highlighting; the
  rendered text MUST be the verbatim file content, NOT a
  re-computed diff against the live working tree
- a per-file changed-lines summary as advisory derived state
- a per-file "added / removed / modified" classification as
  advisory derived state derived from the captured patch

What the dashboard MUST NOT do:

- invoke `git diff`, `git status`, or any other Git command from
  the dashboard process; the canonical capture is the on-disk
  patch file, not a live re-computation
- mutate Git history or working-tree state in either the
  controller or the target (the shipped no-Git-automation boundary
  applies to the dashboard in BOTH roots)
- render a "live diff" that would differ from the captured
  on-disk patch; the on-disk patch is the canonical record for
  the cycle Codex reviewed

### 3. Progress History

Source artifacts (canonical mirrors):

- `.agent-loop/loop-state.json` (the current per-cycle runtime
  state)
- `.agent-loop/phase-plan.md` (the append-only phase history; the
  canonical record of which sub-phases have closed)
- `.agent-loop/orchestrator.log` (the append-only audit log; the
  canonical record of orchestrator-emitted events)
- the per-phase Phase 6I distillation entries under
  `.agent-loop/memory/` when present

What the dashboard MAY render:

- the current loop-state `phase` / `sub_phase` / `task` /
  `cycle_count` / `status` / `last_verdict` / `approval_mode` /
  `awaiting_human_for` as canonical mirrors, each attributed to
  the source field in `loop-state.json`
- a "phase history timeline" advisory derived state assembled from
  the `## ` headers in `phase-plan.md`; each entry attributed to
  its phase-plan section
- the tail-N lines of `orchestrator.log` as canonical mirrors (no
  truncation / rewording / summarization that would lose the
  canonical line text)
- a per-phase advisory derived "duration" or "cycle count" hint
  computed from `phase-plan.md` + `orchestrator.log`; the canonical
  duration record remains the timestamps in the log lines themselves

What the dashboard MUST NOT do:

- mutate `loop-state.json`, `phase-plan.md`, or `orchestrator.log`;
  these are orchestrator- or planner-owned and the dashboard is
  strictly read-only against them
- introduce a parallel "progress history" store in a UI-side
  database; the canonical record is the on-disk artifacts and
  every dashboard rendering MUST refresh from those artifacts per
  poll cycle
- silently skip or filter audit lines (e.g. hiding `[orchestrator]
  HALT ...` lines as "noise"); the canonical audit record is
  complete and the dashboard rendering MUST be complete too

### 4. Approval Actions

Source artifacts (canonical mirrors):

- `.agent-loop/proposed-phase.md` (the Phase 4B planner output;
  the `## Approval` section's `APPROVED_FOR_ACTIVATION` token
  decides activation)
- `.agent-loop/final-acceptance.json` when present (the Phase 9G
  acceptance artifact)
- the Phase 10I `_EXTERNAL_UI_CONTROL_REGISTRY` (the registry of
  approval-relevant CLI actions: `plan`, `activate`,
  `record-final-acceptance`, etc.)

What the dashboard MAY render:

- the full proposed-phase body for human review (the proposal
  itself is the canonical record)
- the `## Approval` section's current text as a canonical mirror;
  the rendered "is approved" badge is advisory derived state
  computed from whether the literal `APPROVED_FOR_ACTIVATION` token
  appears on its own line inside a human-authored `## Approval`
  section whose body references the proposal's `## Label`
- the recorded acceptance artifact contents (when present) as a
  canonical mirror; "final accepted ago" is advisory derived state
- copy-paste-only command affordances for the approval-relevant
  CLI subcommands (`python scripts/agent_loop.py plan`, `... activate`,
  `... record-final-acceptance --accepted-by <NAME>`), reusing the
  Phase 10I `copy_paste` dispatch_mode classification

What the dashboard MUST NOT do:

- issue, forge, auto-fill, or prompt for the `APPROVED_FOR_ACTIVATION`
  token in any dashboard form (the human-edited
  `.agent-loop/proposed-phase.md` `## Approval` section remains the
  only path to the activation token)
- execute `plan`, `activate`, or `record-final-acceptance` on the
  operator's behalf (the dashboard MAY copy the equivalent CLI
  command to the operator's clipboard but MUST NOT spawn the
  subprocess)
- auto-fill `accepted_by` / `attached_by` / `bootstrapped_by` /
  `detached_by` operator-identity fields from browser session, OS
  username, or any persistent dashboard-side identity store
  (matching the shipped Phase 10B/10C/9G non-auto-fill invariants)
- record final acceptance from a dashboard button click; the
  shipped Phase 9G `record-final-acceptance` CLI + the
  `--accepted-by` operator identity remain the only path
- introduce a dashboard-side "approval workflow" (multi-step
  approval, role-based approval, expiring approvals, etc.) that
  competes with the human-edited proposed-phase + CLI flow; the
  canonical approval model is the on-disk token + the shipped CLI

### 5. Token / Cost Reporting

Source artifacts (canonical mirrors):

- the Phase 6F token-exhaustion checkpoint files when present
  (`.agent-loop/token-exhaustion-checkpoint*.json` and the Phase
  6G/6H continuation context)
- the Phase 9F capacity-retry-state file when present
  (`.agent-loop/capacity-retry-state.json`)
- the `cycle_count` / `max_cycles` / `status` fields in
  `loop-state.json`

What the dashboard MAY render:

- the captured continuation budget remaining (canonical mirror
  from the token-exhaustion checkpoint) and the recorded
  pre-suspension cycle context
- the capacity-retry-state's `attempt_count` / `max_attempts` /
  `suspended_status` / `last_attempt_at` as canonical mirrors
- an advisory "cycles used vs cap" hint (e.g. `2 of 3 used`)
  computed from `cycle_count` / `max_cycles`; the canonical record
  is the on-disk fields
- an advisory "current cycle is approaching the cap" warning
  computed from the same fields; canonical halt enforcement
  remains the shipped orchestrator's responsibility

What the dashboard MUST NOT do:

- compute or estimate token cost from agent stdout/stderr (no
  stdout parsing for cost; no model-pricing table baked into the
  dashboard); the canonical record is the orchestrator-emitted
  capacity-retry-state and token-exhaustion checkpoint
- enforce a "cost budget" by refusing to render or by silently
  pausing the orchestrator; the canonical halt mechanism is the
  shipped Phase 6F / 9F runtime
- introduce a dashboard-side telemetry pipe to an external
  metrics backend (no Prometheus, no Datadog, no third-party
  analytics SDK); the canonical record is the on-disk artifacts
  and the orchestrator's own audit log

### 6. Failure Analytics

Source artifacts (canonical mirrors):

- `.agent-loop/codex-review.md` (the per-cycle review; verdict and
  issues list)
- the Phase 6L repeated-failure synthesis output when present
  (under `.agent-loop/memory/`)
- the per-cycle evidence files
  (`.agent-loop/test-output.log`,
  `.agent-loop/lint-output.log`,
  `.agent-loop/typecheck-output.log`,
  `.agent-loop/build-output.log`)
- the `last_verdict` / `status` fields in `loop-state.json`

What the dashboard MAY render:

- the most recent verdict and the issues list from the latest
  `codex-review.md` as canonical mirrors
- the per-cycle evidence files' presence, byte size, and tail-N
  lines as canonical mirrors (with explicit source attribution
  per file)
- the Phase 6L repeated-failure synthesis entries as canonical
  mirrors when present
- an advisory "failure cluster" derived state grouping repeated
  `NEEDS_FIXES` verdicts by category (extracted from the review
  Issues structure); the canonical issue record remains the
  per-cycle codex-review.md
- an advisory "failure category" tag (e.g. "test failure",
  "lint failure", "type-check failure") derived from which
  evidence file the issue references

What the dashboard MUST NOT do:

- mutate any evidence file or memory entry (these are
  orchestrator- and Phase-6-owned)
- silently dedupe issues across cycles in a way that hides the
  per-cycle issue history; every cycle's review remains its own
  canonical record
- introduce a dashboard-side "issue tracker" with state separate
  from the on-disk artifacts; the canonical issue record is the
  per-cycle `codex-review.md` Issues section

## Advisory-Vs-Canonical Mirror Rule

Every value the dashboard renders is one of two categories:

- **Canonical mirror**: a dashboard rendering of a value that came
  from a canonical on-disk artifact, fetched fresh through a
  shipped library function or via a direct read of the on-disk
  file. The dashboard displays the value but MUST clearly
  attribute it to its source artifact and MUST NOT alter the value
  before display. Example: rendering `loop-state.json.status` as a
  status badge tagged "from `.agent-loop/loop-state.json`".
- **Advisory derived state**: a dashboard rendering of a value the
  dashboard computed from one or more canonical mirrors. The
  dashboard MUST mark these values as advisory and MUST NOT
  promote them to a source of truth. Example: a "2 of 3 cycles
  used" string the dashboard computed from `cycle_count` /
  `max_cycles` is advisory derived state; the canonical record is
  the loop-state fields themselves.

The dashboard MUST refresh canonical mirrors on every poll cycle
(and MUST NOT serve stale mirrors from an in-process cache past a
single poll cycle). The dashboard MUST NOT cross-merge canonical
mirrors from different snapshots into a single rendered view (e.g.
the dashboard MUST NOT show `loop-state.status` from snapshot T
and `loop-state.cycle_count` from snapshot T+1 in the same
rendered record); each rendered record carries one consistent
on-disk snapshot.

This rule is the same advisory-vs-canonical mirror rule the Phase
10G UI contract pins; the dashboard contract preserves it
verbatim and applies it to all six dashboard surfaces above.

## Operations That Remain CLI-Only

The dashboard MUST NOT issue, dispatch, proxy, auto-trigger,
queue, or schedule any of the following shipped operations. Every
one of these operations remains a human-initiated CLI invocation
through `python scripts/agent_loop.py ...`. The dashboard MAY
display a button or link that COPIES the equivalent CLI command to
the operator's clipboard for manual execution; the dashboard MUST
NOT execute the command on the operator's behalf.

Mutating operations (write canonical artifacts and / or persist
halt status):

- `attach-external-target`, `detach-external-target`,
  `verify-external-target` (Phase 10D/10E/10F external-workspace
  CLIs)
- `plan` (Phase 4B planner; writes `.agent-loop/proposed-phase.md`)
- `activate` (Phase 4C activator; rewrites planning artifacts +
  resets loop-state)
- `run`, `resume`, `auto-continue`,
  `run-long-run-continuation`, `run-capacity-reprobe` (all
  advance cycle state)
- `record-final-acceptance`, `record-token-exhaustion`,
  `record-capacity-halt`, `build-continuation-context`,
  `distill-phase-boundary-memory`, `load-optional-context`,
  `integrate-optional-context`, `synthesize-repeated-failures`,
  `intake-prd`, `dispatch-prompt-handoff`,
  `run-internal-review-fix-cycle`, `set-runtime-config`,
  `runtime-adapter-eval`, `langchain-support-eval`,
  `bootstrap-prompt`

Read-only operations the dashboard MAY render but MUST NOT execute
as CLI subprocesses on the operator's behalf:

- `inspect-external-target`, `inspect-artifacts`, `status`,
  `evaluate-final-acceptance`, `validate-artifacts`,
  `check-state`

Library-callable read-only operations the dashboard MAY delegate
through the shipped Phase 10I `invoke-external-control --control <ID>`
surface (no CLI subprocess, direct library-function call):

- `view-external-status` (delegates `build_external_ui_status_view(...)`)
- `view-external-controls` (delegates `build_external_ui_control_view(...)`)
- `inspect-external-target` (delegates `inspect_external_target_attach(...)`)

The dashboard MUST NOT introduce additional library-callable
controls beyond the three the Phase 10I registry already pins.
Extending the library-callable surface requires a future Phase 10
sub-phase that updates `_EXTERNAL_UI_CONTROL_REGISTRY`, the Phase
10I tests, and (if the new surface is dashboard-relevant) this
contract; the dashboard runtime alone MUST NOT widen the surface.

## Dashboard Identity And Operator Attribution

The dashboard MUST NOT auto-fill any operator identity field from
browser session state, environment variables, or any persistent
dashboard-side identity store. Every mutating CLI invocation the
operator launches via copy-paste from the dashboard continues to
require the operator to supply identity fields explicitly
(`--attached-by`, `--bootstrapped-by`, `--detached-by`,
`--accepted-by`, etc.), and the dashboard MUST NOT pre-populate
those fields. This mirrors the shipped Phase 10B `attached_by` /
Phase 10C `bootstrapped_by` / Phase 9G `accepted_by` "never
auto-filled from `$USER` / `whoami`" invariants, and matches the
Phase 10G UI contract's identity rules.

## Refusal Behavior

The artifact dashboard MUST refuse fail-closed (render an error
state, NOT silently proceed) in at least the following cases. The
specific dashboard error-state vocabulary will be defined by the
Phase 10K runtime slice that introduces the dashboard; this
contract pins the refusal-eligibility:

- a source artifact named in the six Dashboard Surfaces sections
  above is unreadable (not "missing"; missing artifacts surface
  as advisory "not yet present" state). The dashboard MUST surface
  the read failure as an error state and MUST NOT fabricate the
  artifact's content.
- a canonical artifact's signal-version marker
  (`attach_record_signal_version`, `bootstrap_signal_version`,
  `acceptance_signal_version`, `retry_signal_version`, etc.) is
  unrecognized by the shipped validators. The dashboard MUST
  surface the version mismatch as an error state and MUST NOT
  render the unrecognized record as if its schema were trusted.
- the controller-vs-target ownership boundary is violated (the
  dashboard tries to render a target-side artifact when no attach
  record is present or fresh). The dashboard MUST surface the
  Phase 10A same-root / nesting refusal, the Phase 10F freshness
  drift refusal, or the missing-attach-record state as an error
  state; the dashboard MUST NOT fall back to rendering controller-
  side state as if it were target-side.
- the Phase 4C activator's required `APPROVED_FOR_ACTIVATION`
  token is missing or malformed in `.agent-loop/proposed-phase.md`.
  The dashboard MUST NOT render the proposal as "approved" and
  MUST NOT offer a UI affordance to add the token.
- the `validate-artifacts` reporter (when the dashboard renders
  it via the read-only library call) reports a parse failure on
  any per-cycle artifact. The dashboard MUST surface the parse
  failure and MUST NOT render the malformed artifact as if it
  were valid.

Every dashboard error state MUST point the operator at a shipped
CLI remediation step. The dashboard MUST NOT offer a "fix"
affordance that would mutate canonical state.

## Source-Of-Truth Preservation

Canonical artifacts on disk remain authoritative; the dashboard is
a RENDERING surface, not a state store. The Phase 10G UI contract's
source-of-truth rules apply verbatim, plus the following
dashboard-specific clarifications:

- the dashboard MUST NOT introduce a dashboard-side database,
  key-value store, cache, or session store that holds canonical
  state separately from on-disk artifacts. A per-poll-cycle
  in-memory cache for rendering consistency is permitted; cache
  invalidation per poll is required.
- the dashboard MUST NOT introduce a dashboard-side notification
  queue, event-stream subscription, or webhook that would surface
  dashboard events before the canonical on-disk audit record is
  written. All dashboard-rendered activity derives from the on-disk
  `orchestrator.log` and per-cycle artifacts.
- the dashboard MUST NOT introduce a dashboard-side identity
  token, session token, or auth-bearer beyond what the operating
  system provides; the canonical "who did this" record remains the
  attached_by / bootstrapped_by / accepted_by / detached_by field
  in each canonical artifact.
- the dashboard MUST treat its own URL state as advisory: a
  deep-linked dashboard URL that names an artifact OR a loop-state
  field is a navigation hint; the rendered value MUST come from
  the on-disk artifact, not from the URL.
- the dashboard MUST NOT introduce a dashboard-side audit log that
  is cited as the canonical record of any operator action.
  Dashboard-side debugging logs are permitted but are purely
  advisory and MUST NOT replace `orchestrator.log` as the
  canonical record.

## Safety Boundaries

The future artifact dashboard MUST refuse to:

- commit, push, tag, branch, stash, reset, checkout, or otherwise
  mutate Git history or working-tree state in either the
  controller or the target (the shipped no-Git-automation
  boundary applies to the dashboard in BOTH roots, mirroring the
  Phase 10A - 10I contracts)
- modify `AGENTS.md`, `CLAUDE.md`, `ROADMAP.md`, `README.md`,
  `docs/external-ui-contract.md`,
  `docs/artifact-dashboard-contract.md`, any other docs/ contract
  file, or any source/instruction file in either root as a side
  effect of dashboard rendering
- write any canonical artifact (the same enumeration the Phase
  10G UI contract pins: `TASK.md`, `.agent-loop/loop-state.json`,
  `.agent-loop/external-target.json`,
  `.agent-loop/orchestrator.log`,
  `.agent-loop/claude-prompt.md`,
  `.agent-loop/claude-summary.md`,
  `.agent-loop/codex-review.md`,
  `.agent-loop/fix-prompt.md`,
  `.agent-loop/current-task.md`,
  `.agent-loop/current-phase.md`,
  `.agent-loop/phase-plan.md`,
  `.agent-loop/proposed-phase.md`,
  `.agent-loop/final-acceptance.json`, the Phase 2A evidence
  files, any Phase 6 memory entry, any Phase 9 descriptor, etc.)
  from the dashboard process
- silently widen autonomy by treating a dashboard button click as
  an implicit operator-identity assertion (no auto-fill of any
  `--*-by` identity flag from browser session, OS username, or
  any persistent dashboard-side identity store)
- silently activate a target-side phase from the dashboard; the
  shipped Phase 4C activator + `APPROVED_FOR_ACTIVATION` token
  remain the only path to per-target phase activation
- silently record final human acceptance from the dashboard; the
  shipped Phase 9G `record-final-acceptance` CLI + the
  `--accepted-by` operator identity remain the only path
- silently re-bootstrap a target from the dashboard; the shipped
  Phase 10E `attach-external-target --bootstrap` CLI + the
  required operator inputs remain the only path
- introduce concurrent-attach awareness, multi-target dashboard
  state, or controlled-concurrency scheduling in this contract
  (single-target, single-dashboard-session); a future Phase 10L /
  10M / 10N slice that introduces concurrency-aware behavior will
  extend this contract with an explicit concurrent schema

## Approval Gates

The dashboard contract preserves every shipped human-approval gate
(Phase 10A + 10B + 10C + 10D + 10E + 10F + 10G + 10H + 10I
enumeration):

- per-target phase activation continues to require the shipped
  Phase 4C activator + `APPROVED_FOR_ACTIVATION` token; the
  dashboard MUST NOT issue or auto-fill the token
- per-target `APPROVED_FOR_HUMAN_REVIEW` terminals continue to
  halt the target-side loop and require explicit human approval
  before the next phase begins. The dashboard MUST NOT
  short-circuit this; the dashboard MAY display the terminal
  state as a "ready for human approval" advisory badge
- the Phase 9G final human acceptance gate continues to require
  an explicit operator action on the target's canonical artifact
  set via the shipped `record-final-acceptance` CLI. The
  dashboard MUST NOT record acceptance from a button click
- selecting the Phase 9 fully autonomous PRD-to-product mode on
  a target is an explicit per-attach decision (the Phase 10B
  attach record carries `mode_selection.approval_mode`). The
  dashboard MUST NOT change the approval mode of an existing
  attach record; mode selection happens only at attach time via
  the shipped `attach-external-target --approval-mode ...` CLI
- the Phase 10F freshness assertion continues to be a fail-closed
  guard a human runs via `verify-external-target`. The dashboard
  MAY display the inspector's advisory drift report on every poll,
  but the canonical halt-status persistence remains the result
  of an operator-initiated CLI invocation

## Audit Expectations

A reviewer reading the controller's `.agent-loop/orchestrator.log`
plus the target's `.agent-loop/orchestrator.log` MUST be able to
reconstruct what the operator did, without needing access to any
dashboard-side log, event stream, session record, or telemetry
feed. Specifically:

- every mutating operation the operator triggers via copy-paste
  from the dashboard continues to produce its existing
  `[orchestrator] ...` audit line in the appropriate log when the
  operator runs the CLI in a shell. The dashboard MUST NOT
  swallow, rewrite, or reformat those lines in a way that loses
  information.
- a dashboard-initiated library-call delegation (via the shipped
  Phase 10I `invoke-external-control` surface) does NOT produce a
  canonical audit line - this is the Phase 10I behavior the
  dashboard inherits verbatim; the canonical record of which
  read-only inspector ran is the inspector's return value, not a
  canonical audit-log entry
- a refused dashboard operation (a dashboard-side render error, a
  dashboard-side freshness drift notification, a dashboard-side
  refusal to dispatch a mutating CLI) does NOT produce a canonical
  audit line; refusals are visible only in the dashboard's own
  rendering. Canonical halt-status persistence remains the result
  of a human-initiated CLI invocation
- the dashboard MAY introduce its own dashboard-side activity log
  (e.g. for debugging dashboard-side rendering issues) but that
  log is purely advisory and MUST NOT be cited as the canonical
  record of any operator action

## Dependencies On Later Phase 10 Slices

The dashboard contract is load-bearing for the following later
Phase 10 sub-phases:

- Phase 10K (Artifact Dashboard Runtime Initial Slice) satisfies
  this contract. The slice introduces the first dashboard
  rendering surface, defines the specific dashboard error-state
  vocabulary, and pins the polling cadence + the in-memory cache
  invalidation rules. Phase 10K MAY reuse the shipped Phase 10H /
  10I library functions verbatim; Phase 10K MUST NOT introduce
  any mutating dashboard surface beyond the bounded Phase 10I
  library-call delegation that already ships.
- Phase 10L and later (Controlled-Concurrency / Advanced Dashboard
  Capabilities) extends this contract with concurrent-attach
  awareness, per-target activity stream refinements, advisory
  diff-rendering refinements, and any other advanced capability;
  each extension lands in its own later Phase 10 sub-phase tracked
  in `ROADMAP.md`.

The dashboard contract is consumed by every prior Phase 10 slice
in the following sense: the canonical artifact set the dashboard
may read is exactly the set the Phase 10A - 10I slices produce +
the existing shipped Phase 1 - 9 artifact set. No new canonical
artifact is introduced by the dashboard contract; the dashboard
is a strict renderer of existing canonical state.

## Out Of Scope For Phase 10J

Phase 10J is documentation / contract only. The shipped Phase 1 -
9 runtime behavior is preserved unchanged by this slice; no
orchestrator, planner, activator, evidence-collection,
review-routing, checkpoint, continuation, memory, runtime-adapter,
LangChain, VS Code, Phase 9 autonomous-PRD, capacity-reprobe,
final-acceptance, or external-workspace runtime feature work is
introduced. No Phase 10G / 10H / 10I surface is changed. Adding
the artifact dashboard runtime that satisfies this contract is the
work of Phase 10K; controlled-concurrency awareness, the per-target
activity stream refinements, the advisory diff-rendering
refinements, and any other advanced dashboard capability each land
in their own later Phase 10 sub-phases tracked in `ROADMAP.md`.
