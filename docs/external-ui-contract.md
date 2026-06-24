# Minimal External UI Contract

## Status

Phase 10G defines this contract. No external UI runtime, dashboard,
or operator-facing control surface ships in this slice. The
contract below specifies the FIRST external operator UI surface for
external-workspace mode: which canonical controller-side and
target-side artifacts a minimal external UI may read, which
UI-visible values are advisory mirrors rather than canonical truth,
which operations remain CLI-only and must not be silently triggered
from a UI surface, how the UI must defer to canonical repo
artifacts on disk instead of creating a competing control plane or
state store, and which boundaries are preserved from the shipped
Phase 1 - 9 system and the Phase 10A - 10F external-workspace
slices. Implementation of an external UI runtime is deferred to
later Phase 10 sub-phases:

- Phase 10H: External UI Read-Only Surface Initial Slice (the
  bounded read-only viewer that satisfies this contract by
  rendering canonical attach-record metadata, per-target
  loop-state, and operator-runnable CLI command transcripts; no
  mutation, no CLI dispatch from the UI)
- Phase 10I and later: additional external-workspace UI
  capabilities tracked in `ROADMAP.md` (concurrent-attach
  awareness, per-target activity stream, advisory diff viewer)

## Scope

This document is the contract the future Phase 10H minimal
external UI runtime must satisfy when it is implemented. It is
NOT a description of currently shipped runtime behavior. The
shipped repository today has no external UI surface; every
operator workflow runs through the shipped CLI
(`python scripts/agent_loop.py ...`) and every canonical artifact
write happens through the shipped library functions the CLI
dispatches to.

The UI contract is the load-bearing specification for "what a
future minimal external UI MAY render", "which on-disk artifacts
it MAY read", "which values it MAY surface only as advisory
mirrors of canonical state", and "which mutating operations the UI
MUST NOT silently trigger". The contract pins the read-only
artifact set the UI is allowed to consume, the advisory-vs-canonical
mirror rule, the CLI-only operation list, the refusal behavior, and
the boundaries the UI MUST preserve so a later Phase 10H runtime
slice can be implemented from this contract without further design
decisions and without collapsing the shipped CLI-first workflow into
a parallel UI control plane.

## Distinction From Shipped Artifacts And Surfaces

The minimal external UI is NOT one of the existing shipped
surfaces. The shipped Phase 1 - 9 system and the Phase 10A - 10F
external-workspace slices already define these distinct surface
roles which the UI contract MUST NOT overlap or replace:

- The shipped `python scripts/agent_loop.py ...` CLI is the
  canonical operator entry point for every mutating workflow
  (attach, detach, bootstrap, plan, activate, run, resume,
  auto-continue, record-final-acceptance, verify-external-target,
  etc.). The UI MUST NOT replace, wrap, or shadow these CLI
  surfaces; the UI MAY display the canonical artifacts those CLI
  surfaces write but MUST NOT trigger them.
- The shipped Phase 4C activator + the human-authored
  `APPROVED_FOR_ACTIVATION` token is the canonical path that
  activates a phase. The UI MUST NOT issue, forge, auto-fill, or
  prompt for that token in any UI form; activation continues to
  require the human-edited `.agent-loop/proposed-phase.md`
  approval section read by the shipped activator.
- The Phase 9G final human acceptance gate is the canonical path
  that records human acceptance via the shipped
  `record-final-acceptance` CLI. The UI MUST NOT record
  acceptance; the UI MAY display the on-disk acceptance
  artifact's contents as advisory.
- The Phase 10A controller contract defines the controller-vs-target
  ownership boundary. The UI MUST preserve that boundary:
  controller-owned attach metadata is rendered by the UI as
  controller-side; target-side canonical artifacts are rendered
  as target-side; the UI MUST NOT silently copy values across
  the boundary.
- The Phase 10F `inspect-external-target` CLI subcommand is the
  canonical read-only inspector that surfaces schema validity and
  freshness state. The UI MAY render the inspector's report; the
  UI MUST NOT invent its own staleness, schema-validity, or
  freshness verdict independent of the inspector's library
  function.
- The Phase 10F `verify-external-target` CLI subcommand is the
  canonical shipped fail-closed verifier that persists
  `halted_external_target_stale_attach` into `loop-state.json` on
  drift. The UI MUST NOT call this CLI from a UI button,
  silently dispatch it on a polling tick, or otherwise
  side-effect halt-status persistence; the UI MAY display the
  resulting `loop-state.status` value as advisory after a
  human-driven CLI invocation.

## Canonical Artifacts The Minimal UI May Read

The minimal external UI MAY read the following canonical artifacts
and render their contents (or excerpts) for the operator. Every
artifact on this list is read-only from the UI's perspective; the
UI MUST NOT write to any of them and MUST NOT cache them in a way
that would let UI-rendered state diverge from on-disk state for
longer than a single poll cycle.

Controller-side (read from the controller repository):

- `.agent-loop/external-target.json` (the Phase 10B attach record;
  the canonical record of "which target is the controller
  currently attached to and under what mode")
- `.agent-loop/loop-state.json` (the controller's own per-cycle
  runtime state; canonical for phase / sub_phase / task /
  cycle_count / status / last_verdict / approval_mode /
  awaiting_human_for)
- `.agent-loop/orchestrator.log` (the controller's append-only
  audit log; the UI MAY display the tail-N lines as advisory
  activity but MUST NOT truncate, rewrite, or summarize the log
  in a way that loses the canonical line text)
- `.agent-loop/proposed-phase.md` (the Phase 4B planner output;
  the UI MAY render the proposal sections for human review but
  MUST NOT auto-fill the `## Approval` section)
- `.agent-loop/current-task.md` and
  `.agent-loop/current-phase.md` (the Codex-owned per-cycle
  planning artifacts)
- `.agent-loop/claude-prompt.md`, `.agent-loop/claude-summary.md`,
  `.agent-loop/codex-review.md`, `.agent-loop/fix-prompt.md` (the
  per-cycle prompt / summary / review / fix-prompt artifacts;
  the UI MAY render the rendered Markdown for the operator)
- the controller's `TASK.md` (the canonical Human Objective /
  Project Intent / Active Phase / Active Sub-Phase / Phase
  Status / Active Task / Phase Outcome Required Now / Next-Phase
  Gate / Out Of Scope For Current Phase planning record)
- `.agent-loop/final-acceptance.json` when present (the Phase 9G
  acceptance artifact; the UI MAY render the recorded
  acceptance metadata but MUST NOT record acceptance from the UI)

Target-side (read from the target repository, only when an attach
record is present and fresh):

- the target's `.agent-loop/loop-state.json`
- the target's `.agent-loop/orchestrator.log` (tail-N lines as
  advisory activity)
- the target's `TASK.md` (Codex-owned planning record)
- the target's `.agent-loop/current-task.md` and
  `.agent-loop/current-phase.md`

The UI MUST NOT read any other on-disk artifact in either root,
and MUST NOT follow symlinks or hand-supplied paths outside the
two canonicalized roots the attach record names. Reading is
through the shipped library validators
(`load_loop_state(...)`, `_validate_external_target_attach_record_schema(...)`,
the Phase 10F `inspect_external_target_attach(...)` aggregator,
etc.); the UI MUST NOT re-parse on-disk JSON / Markdown with its
own parser that could disagree with the shipped validators on
malformed input.

## Advisory-Vs-Canonical Mirror Rule

Every value the UI renders is one of two categories:

- **Canonical mirror**: a UI rendering of a value that came from a
  canonical on-disk artifact, fetched fresh through a shipped
  library function. The UI displays the value but MUST clearly
  attribute it to its source artifact and MUST NOT alter the
  value before display. Example: rendering
  `loop-state.json.status` as a status badge tagged
  "from `.agent-loop/loop-state.json`".
- **Advisory derived state**: a UI rendering of a value the UI
  computed from one or more canonical mirrors. The UI MUST mark
  these values as advisory and MUST NOT promote them to a source
  of truth. Example: a "last activity ~3 minutes ago" string the
  UI computed from the last line of `orchestrator.log` is
  advisory derived state; the canonical activity record is the
  log file itself.

The UI MUST refresh canonical mirrors on every poll cycle (and
MUST NOT serve stale mirrors from an in-process cache past a
single poll cycle). The UI MUST NOT cross-merge canonical mirrors
from different snapshots into a single rendered view (e.g. the UI
MUST NOT show `loop-state.status` from snapshot T and
`loop-state.cycle_count` from snapshot T+1 in the same rendered
record); each rendered record carries one consistent on-disk
snapshot.

Canonical-vs-advisory examples the UI MUST treat correctly:

- the attach record's `bootstrap_state.status` is canonical (from
  `external-target.json`); a UI "is bootstrapped" badge derived
  from it is advisory derived state.
- the target loop-state's `status` field is canonical (from the
  target's `loop-state.json`); a UI "running" / "halted" /
  "awaiting human" label derived from it is advisory derived
  state.
- the Phase 10F freshness probe's `is_fresh` field is canonical
  for that probe call (from the library function); a UI "stale
  attach detected" notification derived from it is advisory
  derived state, and the canonical halt-status persistence
  remains the responsibility of the `verify-external-target`
  CLI a human runs.
- the Phase 9G acceptance artifact's `accepted_by` and
  `accepted_at` are canonical; a UI "final-accepted ago" label
  derived from them is advisory derived state.

## Operations That Remain CLI-Only

The UI MUST NOT issue, dispatch, proxy, auto-trigger, queue, or
schedule any of the following shipped operations. Every one of
these operations remains a human-initiated CLI invocation through
`python scripts/agent_loop.py ...`. The UI MAY display a button or
link that COPIES the equivalent CLI command to the operator's
clipboard for manual execution; the UI MUST NOT execute the
command on the operator's behalf.

Mutating operations (write canonical artifacts and / or persist
halt status):

- `attach-external-target` (writes the Phase 10B attach record)
- `detach-external-target` (removes the attach record)
- `verify-external-target` (calls the Phase 10F throwing
  freshness assertion which persists
  `halted_external_target_stale_attach` to `loop-state.json` via
  `_halt` on drift)
- `plan` (Phase 4B planner; writes `.agent-loop/proposed-phase.md`)
- `activate` (Phase 4C activator; rewrites planning artifacts +
  resets loop-state)
- `run` (Phase 3A orchestrator; advances cycles)
- `resume`, `auto-continue`, `run-long-run-continuation`,
  `run-capacity-reprobe` (all advance cycle state)
- `record-final-acceptance` (Phase 9G acceptance writer)
- `record-token-exhaustion`, `record-capacity-halt`,
  `build-continuation-context`, `distill-phase-boundary-memory`,
  `load-optional-context`, `integrate-optional-context`,
  `synthesize-repeated-failures`, `intake-prd`,
  `dispatch-prompt-handoff`, `run-internal-review-fix-cycle`,
  `set-runtime-config`, `runtime-adapter-eval`,
  `langchain-support-eval`, `bootstrap-prompt`

Read-only operations the UI MAY render but MUST NOT execute on
the operator's behalf:

- `inspect-external-target` (the Phase 10F aggregator inspector
  reporter; the UI MAY render the same report via the library
  function `inspect_external_target_attach(...)` directly,
  without dispatching the CLI subprocess)
- `inspect-artifacts`, `status`, `evaluate-final-acceptance`,
  `validate-artifacts`, `check-state` (Phase 7B / 7C / 9G read-
  only reporters; same library-vs-CLI distinction)

The UI MAY call the shipped library functions directly (e.g.
`inspect_external_target_attach(controller_root)`,
`compute_status_summary(...)`, `evaluate_final_acceptance(...)`,
the freshness probe's non-throwing companion) because those
functions are read-only and produce no canonical-artifact side
effect. The UI MUST NOT call any throwing or mutating library
function (e.g. `assert_external_target_attach_fresh(...)`,
`attach_external_target(...)`, `detach_external_target(...)`,
`bootstrap_external_target(...)`, `save_loop_state(...)`,
`_halt(...)`).

## UI Identity And Operator Attribution

The UI MUST NOT auto-fill any operator identity field from
browser session state, environment variables, or any persistent
UI-side identity store. Every mutating CLI invocation the operator
launches via copy-paste from the UI continues to require the
operator to supply identity fields explicitly (`--attached-by`,
`--bootstrapped-by`, `--detached-by`, `--accepted-by`, etc.), and
the UI MUST NOT pre-populate those fields. This mirrors the
shipped Phase 10B `attached_by` / Phase 10C `bootstrapped_by` /
Phase 9G `accepted_by` "never auto-filled from `$USER` / `whoami`"
invariants.

## Refusal Behavior

The minimal external UI MUST refuse fail-closed (render an error
state, NOT silently proceed) in at least the following cases. The
specific UI error-state vocabulary will be defined by the Phase
10H runtime slice that introduces the UI; this contract pins the
refusal-eligibility:

- the attach record is missing, unreadable, or fails the shipped
  `_validate_external_target_attach_record_schema(...)` validator.
  The UI MUST surface the structural failure as an error state
  and MUST NOT fabricate a "no attach record" badge or otherwise
  hide the failure.
- the attach record's freshness probe reports drift (target dir
  removed, marker files missing, controller-path drift,
  target-canonical-path drift). The UI MUST surface the drift
  state and MUST NOT silently re-read the stale snapshot as if
  it were fresh.
- the target root names a directory the UI process cannot read
  (filesystem permission denial). The UI MUST NOT fall back to
  rendering controller-side state as if it were target-side.
- the canonical artifact's signal-version marker
  (`attach_record_signal_version`, `bootstrap_signal_version`,
  `acceptance_signal_version`, etc.) is unrecognized by the
  shipped validators. The UI MUST surface the version mismatch
  as an error state and MUST NOT render the unrecognized record
  as if its schema were trusted.
- the Phase 4C activator's required `APPROVED_FOR_ACTIVATION`
  token is missing or malformed in `.agent-loop/proposed-phase.md`.
  The UI MUST NOT render the proposal as "approved" and MUST NOT
  offer a UI affordance to add the token.
- the target's canonical path canonicalizes to (or nests inside)
  the controller's canonical path. The UI MUST surface the
  Phase 10A same-root / nesting refusal and MUST NOT render the
  attach as valid.

Every UI error state MUST point the operator at a shipped CLI
remediation step (run `inspect-external-target`, run
`verify-external-target`, run `detach-external-target` then re-
attach, edit `.agent-loop/proposed-phase.md`, etc.). The UI MUST
NOT offer a "fix" affordance that would mutate canonical state.

## Source-Of-Truth Preservation

Canonical artifacts on disk remain authoritative; the UI is a
RENDERING surface, not a state store:

- the UI MUST NOT introduce a UI-side database, key-value store,
  cache, or session store that holds canonical state separately
  from on-disk artifacts.
- the UI MAY hold a per-poll-cycle in-memory cache of fetched
  canonical mirrors (so a single rendered page is consistent),
  but the cache MUST be invalidated on every poll and MUST NOT
  survive a UI process restart in a way that would let the UI
  serve a stale value after the underlying on-disk state has
  changed.
- the UI MUST NOT introduce a UI-side notification queue,
  event-stream subscription, or webhook that would surface UI
  events before the canonical on-disk audit record is written.
  All UI-rendered activity derives from the on-disk
  `orchestrator.log` and per-cycle artifacts.
- the UI MUST NOT introduce a UI-side identity token, session
  token, or auth-bearer beyond what the operating system
  provides; the canonical "who did this" record remains the
  attached_by / bootstrapped_by / accepted_by / detached_by
  field in each canonical artifact.
- the UI MUST treat its own URL state as advisory: a deep-linked
  UI URL that names an attach record OR a target loop-state
  field is a navigation hint; the rendered value MUST come from
  the on-disk artifact, not from the URL.

## Safety Boundaries

The future minimal external UI MUST refuse to:

- commit, push, tag, branch, stash, reset, checkout, or
  otherwise mutate Git history or working-tree state in either
  the controller or the target (the shipped
  no-Git-automation boundary applies to the UI in BOTH roots,
  mirroring the Phase 10A / 10B / 10C / 10D / 10E / 10F
  contracts).
- modify `AGENTS.md`, `CLAUDE.md`, `ROADMAP.md`, `README.md`,
  `docs/external-ui-contract.md`, any other docs/ contract file,
  or any source/instruction file in either root as a side
  effect of UI rendering.
- write any canonical artifact (`TASK.md`,
  `.agent-loop/loop-state.json`, `.agent-loop/external-target.json`,
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
  from the UI process.
- silently widen autonomy by treating a UI button click as an
  implicit operator-identity assertion (the UI MUST NOT
  auto-fill `--attached-by` / `--bootstrapped-by` /
  `--accepted-by` / `--detached-by` from browser session, OS
  username, or any persistent UI-side identity store).
- silently activate a target-side phase from the UI; the
  shipped Phase 4C activator + `APPROVED_FOR_ACTIVATION` token
  remain the only path to per-target phase activation.
- silently record final human acceptance from the UI; the
  shipped Phase 9G `record-final-acceptance` CLI + the
  `--accepted-by` operator identity remain the only path.
- silently re-bootstrap a target from the UI; the shipped
  Phase 10E `attach-external-target --bootstrap` CLI + the
  required operator inputs remain the only path.
- introduce concurrent attach awareness in this contract
  (single-target, single-UI-session); a future Phase 10I
  slice that introduces concurrent attaches will extend this
  contract with an explicit concurrent-UI schema.

## Approval Gates

The UI contract preserves every shipped human-approval gate
(Phase 10A + 10B + 10C + 10D + 10E + 10F enumeration):

- per-target phase activation continues to require the shipped
  Phase 4C activator + `APPROVED_FOR_ACTIVATION` token; the UI
  MUST NOT issue or auto-fill the token.
- per-target `APPROVED_FOR_HUMAN_REVIEW` terminals continue to
  halt the target-side loop and require explicit human approval
  before the next phase begins. The UI MUST NOT short-circuit
  this; the UI MAY display the terminal state as a "ready for
  human approval" advisory badge.
- the Phase 9G final human acceptance gate continues to require
  an explicit operator action on the target's canonical artifact
  set via the shipped `record-final-acceptance` CLI. The UI MUST
  NOT record acceptance from a button click.
- selecting the Phase 9 fully autonomous PRD-to-product mode on
  a target is an explicit per-attach decision (the Phase 10B
  attach record carries `mode_selection.approval_mode`). The UI
  MUST NOT change the approval mode of an existing attach
  record; mode selection happens only at attach time via the
  shipped `attach-external-target --approval-mode ...` CLI.
- the Phase 10F freshness assertion continues to be a fail-closed
  guard a human runs via `verify-external-target`. The UI MAY
  display the inspector's advisory drift report on every poll,
  but the canonical halt-status persistence remains the result
  of an operator-initiated CLI invocation.

## Audit Expectations

A reviewer reading the controller's `.agent-loop/orchestrator.log`
plus the target's `.agent-loop/orchestrator.log` MUST be able to
reconstruct what the operator did, without needing access to any
UI-side log, event stream, session record, or telemetry feed.
Specifically:

- every mutating operation the operator triggers continues to
  produce its existing `[orchestrator] ...` audit line in the
  appropriate log. The UI MUST NOT swallow, rewrite, or
  reformat those lines in a way that loses information.
- the UI MAY introduce its own UI-side activity log (e.g. for
  debugging UI-side rendering issues) but that log is purely
  advisory and MUST NOT be cited as the canonical record of
  any operator action.
- a refused operation (a UI-side render error, a UI-side
  freshness drift notification) does NOT produce a canonical
  audit line; refusals are visible only by rendering the
  inspector's advisory report. Canonical halt-status
  persistence remains the result of a CLI invocation.

## Dependencies On Later Phase 10 Slices

The UI contract is load-bearing for the following later Phase
10 sub-phases:

- Phase 10H (External UI Read-Only Surface Initial Slice)
  satisfies this contract. The slice introduces the first
  rendering surface, defines the specific UI error-state
  vocabulary, and pins the polling cadence and the in-memory
  cache invalidation rules.
- Phase 10I and later (Advanced External UI Capabilities)
  extends this contract with concurrent-attach awareness, a
  per-target activity stream, and an advisory diff viewer; each
  extension lands in its own later Phase 10 sub-phase tracked
  in `ROADMAP.md`.

The UI contract is consumed by every prior Phase 10 slice in the
following sense: the canonical artifact set the UI may read is
exactly the set the Phase 10A - 10F slices produce + the existing
shipped Phase 1 - 9 artifact set. No new canonical artifact is
introduced by the UI contract; the UI is a strict renderer of
existing canonical state.

## Out Of Scope For Phase 10G

Phase 10G is documentation / contract only. The shipped Phase 1 -
9 runtime behavior is preserved unchanged by this slice; no
orchestrator, planner, activator, evidence-collection, review-
routing, checkpoint, continuation, memory, runtime-adapter,
LangChain, VS Code, Phase 9 autonomous-PRD, capacity-reprobe,
final-acceptance, or external-workspace runtime feature work is
introduced. Adding the read-only UI runtime that satisfies this
contract is the work of Phase 10H; concurrent-attach awareness,
the per-target activity stream, the advisory diff viewer, and any
other advanced UI capability each land in their own later Phase 10
sub-phase tracked in `ROADMAP.md`.
