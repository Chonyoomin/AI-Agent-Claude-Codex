# Desktop App Shell Contract

## Status

Phase 10L defines this contract. No desktop app runtime, native
window, packaging step, code-signing pipeline, auto-update pipeline,
or system tray surface ships in this slice. The contract below
specifies the FIRST native desktop-app shell over the shipped Python
runtime and the shipped Phase 10G - 10K external UI surfaces: which
desktop toolkit / process model the shell MUST use; how the operator
selects the controller root the shell renders against; how the shell
makes attach state visible; the refresh / polling cadence and bounds
the shell MUST respect; how the shell MAY open canonical artifacts
in the operator's existing native editor; how the shell bridges to
the shipped Python orchestrator / view surfaces without introducing
a competing control plane, alternate state store, or hidden
mutation path; and which boundaries are preserved from the shipped
Phase 1 - 9 system, the Phase 10A - 10F external-workspace slices,
the Phase 10G - 10I external UI surfaces, and the Phase 10J - 10K
artifact dashboard contract and runtime. Implementation of the
desktop app runtime is deferred to later Phase 10 sub-phases:

- Phase 10M: Desktop App Shell Runtime Initial Slice (the first
  native window that opens against a chosen controller root, polls
  the shipped Phase 10H / 10I / 10K view library functions, and
  renders their bounded view-model dicts; no mutation, no
  background orchestration, no second source of truth)
- Phase 10N and later: additional desktop capabilities tracked in
  `ROADMAP.md` (controlled-concurrency awareness, multi-target
  desktop sessions, packaging / code-signing / auto-update, native
  system-tray reminders)

## Scope

This document is the contract the future Phase 10M desktop app
runtime MUST satisfy when it is implemented. It is NOT a description
of currently shipped runtime behavior. The shipped repository today
exposes the bounded external UI read-only status surface (Phase 10H
`view-external-status` + `build_external_ui_status_view(...)`), the
bounded external UI run/resume controls surface (Phase 10I
`view-external-controls` + `invoke-external-control` +
`build_external_ui_control_view(...)`), and the bounded artifact
dashboard runtime (Phase 10K `view-artifact-dashboard` +
`build_artifact_dashboard_view(...)`); every operator workflow
beyond those bounded reads runs through the shipped CLI
(`python scripts/agent_loop.py ...`) and every canonical artifact
write happens through the shipped library functions the CLI
dispatches to.

The desktop-app contract is the load-bearing specification for "what
a future desktop app MAY render", "which on-disk artifacts it MAY
read", "which shipped library functions it MAY delegate to", "how
the operator selects the controller root", "what refresh cadence the
shell MUST respect", "how the shell MAY open canonical artifacts in
the operator's native editor", "which mutating operations the
desktop shell MUST NOT silently trigger", and "how the shell MUST
preserve the canonical-artifact-first source-of-truth model". The
contract pins the desktop process boundary, the toolkit constraints,
the controller-root selection flow, the attach-visibility rule, the
refresh / polling cadence and bounds, the artifact-opening behavior,
the explicit refusal cases, the no-second-source-of-truth invariant,
and the boundaries the desktop shell MUST preserve so a later
Phase 10M runtime slice can be implemented from this contract
without further design decisions and without collapsing the shipped
CLI-first workflow into a parallel desktop control plane.

## Distinction From Shipped Artifacts And Surfaces

The desktop app shell is NOT one of the existing shipped surfaces.
The shipped Phase 1 - 9 system, the Phase 10A - 10F
external-workspace slices, the Phase 10G - 10I external UI
surfaces, and the Phase 10J - 10K artifact dashboard contract and
runtime already define these distinct surface roles which the
desktop-app contract MUST NOT overlap or replace:

- The shipped `python scripts/agent_loop.py ...` CLI is the
  canonical operator entry point for every mutating workflow. The
  desktop shell MUST NOT replace, wrap, or shadow these CLI
  surfaces; the desktop shell MAY display the canonical artifacts
  those CLI surfaces write but MUST NOT trigger them.
- The shipped Phase 10G external UI contract (`docs/external-ui-contract.md`)
  pins the load-bearing UI boundaries (canonical artifact read set,
  advisory-vs-canonical mirror rule, CLI-only operations,
  no-auto-fill operator identity, refusal behavior,
  source-of-truth preservation, safety boundaries, approval gates,
  audit expectations). The desktop-app contract EXTENDS those
  boundaries to the desktop process; it MUST NOT relax any of them.
  Every read-set / advisory-mirror / CLI-only / no-auto-fill /
  refusal / source-of-truth / safety / approval / audit rule in
  `docs/external-ui-contract.md` continues to apply to the desktop
  shell verbatim.
- The shipped Phase 10H `view-external-status` surface is the
  canonical read-only status view. The desktop shell MAY render the
  same view-model dict (returned by `build_external_ui_status_view(...)`)
  but MUST NOT invent a parallel status model.
- The shipped Phase 10I `view-external-controls` +
  `invoke-external-control` surfaces are the canonical bounded
  control affordance layer. The desktop shell MAY render the same
  control registry (returned by `build_external_ui_control_view(...)`)
  and MAY delegate the same three library-callable read-only
  controls via the same `ExternalUiControlRefusal`-based refusal
  path. The desktop shell MUST NOT introduce additional
  library-callable controls; the desktop shell MUST NOT change the
  refusal vocabulary; the desktop shell MUST NOT dispatch any
  mutating CLI subcommand on the operator's behalf.
- The shipped Phase 10J artifact dashboard contract and the shipped
  Phase 10K artifact dashboard runtime (`docs/artifact-dashboard-contract.md`,
  `view-artifact-dashboard` + `build_artifact_dashboard_view(...)`)
  pin the six dashboard surfaces (review summaries, diff views,
  progress history, approval actions, token/cost reporting, failure
  analytics) and the bounded read-side enumeration of the canonical
  source artifacts each surface MAY mirror. The desktop shell MAY
  render the same view-model dict and MUST NOT invent a parallel
  dashboard model, MUST NOT widen the dashboard's canonical
  artifact read set, MUST NOT introduce a seventh dashboard
  surface, and MUST NOT add a mutating dashboard control.
- The shipped Phase 4C activator + the human-authored
  `APPROVED_FOR_ACTIVATION` token is the canonical path that
  activates a phase. The desktop shell MUST NOT issue, forge,
  auto-fill, or prompt for that token in any desktop form.
- The Phase 9G final human acceptance gate is the canonical path
  that records human acceptance via the shipped
  `record-final-acceptance` CLI. The desktop shell MUST NOT record
  acceptance; the desktop shell MAY display the on-disk acceptance
  artifact's contents as advisory.

## Desktop Process Boundary And Toolkit

The desktop shell MUST be a thin local-only native window process
hosted by the operator's machine. It MUST NOT introduce a remote
server, a hosted SaaS endpoint, or a shared multi-user backend.
Specifically:

- the desktop process MUST run on the same machine as the
  controller repository and MUST access the controller root via the
  operating system's local filesystem only. It MUST NOT open a
  network socket that exposes the controller's `.agent-loop/`
  artifacts to another machine.
- the desktop process MUST NOT bundle, fork, or auto-start a
  background daemon that mutates canonical artifacts. The shipped
  CLI remains the only mutating writer; any cycle work the operator
  triggers from the desktop continues to spawn the shipped CLI
  process via copy-paste or the bounded Phase 10I library-call
  delegation.
- the desktop process MUST be locally inspectable: an operator
  reading the desktop process's command line MUST see the shipped
  Python interpreter invoking the shipped library functions, or the
  desktop binary invoking the shipped CLI via the operator's own
  shell; the desktop MUST NOT call a closed third-party binary that
  bypasses the shipped Python layer.
- the choice of native toolkit (Electron, Tauri, Qt, native AppKit /
  Win32 / GTK, etc.) is intentionally NOT pinned by this contract;
  the Phase 10M runtime slice MAY pick any toolkit that satisfies
  every other invariant below, including the local-only,
  read-mostly, CLI-first, no-second-state-store rules.
- if the toolkit ships a renderer process separate from the main
  process (the common Electron / Tauri pattern), the renderer MUST
  NOT have direct filesystem write access to any canonical
  artifact; all canonical writes continue to flow through the
  shipped CLI, and the renderer MAY only read canonical artifacts
  through a bounded main-process bridge that mirrors the shipped
  Phase 10H / 10I / 10K view library functions.

## Controller-Root Selection Flow

The desktop shell MUST require explicit operator selection of the
controller root before rendering any canonical artifact. The shell
MUST NOT silently pick a default root from a recent-history list,
an OS-level "current working directory", an environment variable,
or a packaging-time configured path. Specifically:

- the operator selects the controller root via a native folder
  picker. The shell MUST display the absolute path of the selected
  folder so the operator can confirm before any read happens.
- the shell MUST validate the selected folder is a controller
  repository (presence of `AGENTS.md`, `CLAUDE.md`, `TASK.md`, and
  `.agent-loop/`) before rendering any view. A folder that fails
  this check MUST surface as an explicit refusal (see Refusal
  Behavior); the shell MUST NOT silently fall back to the previous
  controller root.
- the shell MUST remember at most one currently selected controller
  root for the duration of the shell process. The shell MAY
  persist a recently-selected list as a navigation convenience, but
  that list is advisory only and MUST NOT auto-load a controller
  root at shell startup.
- the operator MAY switch the controller root mid-session via the
  folder picker; the shell MUST treat a switch as a clean reset
  (discard the prior session's in-memory render cache, re-validate
  the new root, re-poll the shipped view library functions). The
  shell MUST NOT cross-merge artifacts from two different
  controller roots into a single rendered view.
- the shell MUST NOT auto-create the controller root, the
  `.agent-loop/` directory, or any canonical artifact when the
  selected folder is missing one. Creating the controller root
  remains an operator-driven `git init` / clone step plus the
  shipped Phase 4C activation flow.

## Attach Visibility

The desktop shell MUST surface the controller's external-target
attach state through the shipped Phase 10F inspector report and the
shipped Phase 10H status view. Specifically:

- the shell MUST display whether an attach record is present, fresh,
  schema-valid, and refused-vs-accepted, using the inspector's
  existing fields (`attached` / `schema_valid` / `schema_violations`
  / `freshness`). The shell MUST NOT invent an alternate attach
  schema or re-compute these fields from raw `external-target.json`.
- when an attach is present and fresh, the shell MAY render the
  target-side `loop-state.json` / `TASK.md` / `current-task.md` /
  `current-phase.md` as canonical mirrors, attributed to the
  target-root path. When the attach is missing, stale, or
  schema-violating, the shell MUST surface the appropriate Phase
  10G refusal vocabulary and MUST NOT silently render target-side
  state as if it were controller-side.
- the shell MUST NOT auto-trigger `attach-external-target`,
  `detach-external-target`, `verify-external-target`, or
  `attach-external-target --bootstrap` on the operator's behalf;
  these remain copy-paste-only or operator-CLI-invoked.
- when the desktop shell concurrently renders multiple controller
  roots in separate windows or tabs (a Phase 10N+ capability), the
  per-window attach visibility MUST remain isolated; the shell MUST
  NOT cross-leak attach records between windows.

## Refresh / Polling Rules

The desktop shell MUST poll the shipped view library functions on a
bounded cadence and MUST NOT introduce a parallel event-stream,
file-watcher, or webhook subscription that surfaces dashboard state
ahead of the canonical on-disk audit record. Specifically:

- the default poll cadence MUST be conservative (at least 2 seconds
  between polls of the same view library function for an idle
  controller; at least 1 second under operator-driven refresh).
  Faster polling is permitted only when the operator explicitly
  requests it and the shell MUST display the active cadence in the
  shell window.
- each poll MUST refresh canonical mirrors from the shipped view
  library functions; the shell MUST NOT serve stale mirrors from an
  in-process cache past a single poll cycle. A per-poll-cycle
  in-memory cache for rendering consistency is permitted; cache
  invalidation per poll is required.
- a per-window OS-level file-system watch on `.agent-loop/` is
  permitted as a polling optimization (the watch fires; the shell
  re-polls the shipped view library functions). The watch MUST
  NOT bypass the shipped view library functions and read raw JSON
  / Markdown directly: every rendered value continues to flow
  through `build_external_ui_status_view(...)` /
  `build_external_ui_control_view(...)` /
  `build_artifact_dashboard_view(...)` so the shell stays inside
  the shipped contract surface.
- the shell MUST NOT introduce a long-poll, server-sent-event, or
  WebSocket subscription that fans dashboard activity out to a
  remote endpoint. The desktop shell is local-only.
- when the controller is in a halted or paused state (`halted_*`,
  `phase_complete_awaiting_human_approval`, the four Phase 5C
  strict-gate halts, `HALTED_TOKEN_EXHAUSTION`, etc.), the shell
  MAY back off its poll cadence (e.g. one poll every 5 seconds);
  the shell MUST NOT silently advance loop-state or silently
  resume in response to a halt.

## Artifact-Opening Behavior

The desktop shell MAY offer one-click affordances that open a
canonical on-disk artifact in the operator's existing native editor.
Artifact-opening is read-only from the shell's perspective: opening
the file in an external editor does NOT mutate the file from the
shell process, and the operator's subsequent edits (if any) flow
through whatever editor the operator chose. Specifically:

- the shell MUST resolve each artifact path against the currently
  selected controller root (or target root, when an attach is fresh
  and the operator has selected a target-side artifact). The shell
  MUST NOT silently open an artifact from a previously selected
  controller root after the operator switches roots.
- the shell MUST use the operating system's default file-open
  mechanism (e.g. `xdg-open` on Linux, `open` on macOS, the Windows
  shell association). The shell MUST NOT bundle its own editor; the
  shell MUST NOT prompt the operator for a third-party online
  editor service.
- the shell MUST NOT auto-stage, auto-format, or auto-rewrite an
  artifact as a side effect of opening it. The shell MUST NOT
  invoke `git add`, `git stash`, or any other Git command as a
  side effect of opening an artifact (the shipped no-Git-automation
  boundary applies to the desktop shell in both controller and
  target roots).
- the shell MAY offer an "open enclosing folder" affordance for
  the controller root or the target root; this is a navigation
  convenience and MUST NOT modify the folder's contents.
- the shell MUST NOT silently open a Codex-owned planning artifact
  (`.agent-loop/current-task.md`, `.agent-loop/current-phase.md`,
  `.agent-loop/phase-plan.md`) for editing as a side effect of any
  dashboard render. Codex-owned artifacts are read-only from the
  desktop shell's perspective; the operator MAY still open them in
  an editor manually, but the shell MUST NOT initiate that flow as
  an automatic action.
- the shell MUST NOT silently open `.agent-loop/codex-review.md` or
  `.agent-loop/orchestrator.log` for editing; these remain Codex-
  owned and orchestrator-owned respectively per the shipped
  CLAUDE.md / AGENTS.md ownership rules.

## Bridge To Shipped Python Orchestrator And View Surfaces

The desktop shell MUST bridge to the shipped Python orchestrator
and view surfaces in exactly one of two ways. The shell MUST NOT
re-implement the shipped library functions in a non-Python language
or bypass them via direct on-disk reads. Specifically:

- **Library-call bridge (preferred for read-only surfaces)**: the
  shell hosts a Python sub-process that imports `agent_loop` and
  invokes the shipped view library functions
  (`build_external_ui_status_view(...)`,
  `build_external_ui_control_view(...)`,
  `build_artifact_dashboard_view(...)`,
  `invoke_external_ui_control(...)` for the three library-callable
  controls, `inspect_external_target_attach(...)` via the same
  Phase 10I delegation). The shell renders the returned dict
  verbatim; advisory-vs-canonical mirror tagging is preserved
  exactly. The shell MUST NOT mutate the dict before render and
  MUST NOT inject additional fields.
- **CLI-spawn bridge (for mutating workflows)**: the shell
  displays a copy-paste affordance for each mutating CLI
  subcommand. The operator copies the command and runs it in their
  own shell. The shell MUST NOT silently `Popen` the mutating
  subcommand on the operator's behalf, MUST NOT auto-fill any
  `--*-by` operator-identity argument, and MUST NOT capture the
  spawned CLI's stdout as a canonical record (the shipped audit
  artifacts on disk remain the canonical record).
- the library-call bridge MUST NOT spawn a long-lived Python daemon
  that holds open `.agent-loop/` file handles across polls. Each
  poll is a fresh function call so the shipped library functions'
  per-call freshness semantics are preserved.
- the bridge MUST NOT introduce a custom IPC protocol, named pipe,
  or socket that bypasses the shipped library functions. The
  shipped view library functions are the only bridge contract.
- the shell MAY display the bridge's Python version and the
  shipped `agent_loop` module path in a debug pane for operator
  troubleshooting; the shell MUST NOT silently switch between
  multiple Python interpreters at runtime without surfacing the
  switch.

## Advisory-Vs-Canonical Mirror Rule

Every value the desktop shell renders is one of two categories:

- **Canonical mirror**: a shell rendering of a value that came from
  a canonical on-disk artifact, fetched fresh through a shipped
  library function. The shell displays the value but MUST clearly
  attribute it to its source artifact (matching the shipped Phase
  10H / 10I / 10K renderer attribution conventions) and MUST NOT
  alter the value before display. Example: rendering
  `loop-state.json.status` as a status badge tagged "from
  `.agent-loop/loop-state.json`".
- **Advisory derived state**: a shell rendering of a value the
  shell computed from one or more canonical mirrors. The shell
  MUST mark these values as advisory and MUST NOT promote them to
  a source of truth. Example: a "2 of 3 cycles used" string the
  shell computed from `cycle_count` / `max_cycles` is advisory
  derived state; the canonical record is the loop-state fields
  themselves.

The shell MUST refresh canonical mirrors on every poll cycle (and
MUST NOT serve stale mirrors from an in-process cache past a single
poll cycle). The shell MUST NOT cross-merge canonical mirrors from
different snapshots into a single rendered view (e.g. the shell
MUST NOT show `loop-state.status` from snapshot T and
`loop-state.cycle_count` from snapshot T+1 in the same rendered
record); each rendered record carries one consistent on-disk
snapshot.

This rule is the same advisory-vs-canonical mirror rule the Phase
10G UI contract and the Phase 10J dashboard contract pin; the
desktop-app contract preserves it verbatim and applies it to every
desktop-rendered surface.

## Operations That Remain CLI-Only

The desktop shell MUST NOT issue, dispatch, proxy, auto-trigger,
queue, or schedule any of the following shipped operations. Every
one of these operations remains a human-initiated CLI invocation
through `python scripts/agent_loop.py ...`. The shell MAY display
a button or link that COPIES the equivalent CLI command to the
operator's clipboard for manual execution; the shell MUST NOT
execute the command on the operator's behalf.

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

Read-only operations the desktop shell MAY render but MUST NOT
execute as CLI subprocesses on the operator's behalf:

- `inspect-external-target`, `inspect-artifacts`, `status`,
  `evaluate-final-acceptance`, `validate-artifacts`,
  `check-state`, `view-external-status`, `view-external-controls`,
  `view-artifact-dashboard`

Library-callable read-only operations the desktop shell MAY
delegate through the shipped Phase 10I
`invoke-external-control --control <ID>` surface (no CLI subprocess,
direct library-function call):

- `view-external-status` (delegates `build_external_ui_status_view(...)`)
- `view-external-controls` (delegates `build_external_ui_control_view(...)`)
- `inspect-external-target` (delegates `inspect_external_target_attach(...)`)

The desktop shell MUST NOT introduce additional library-callable
controls beyond the three the Phase 10I registry already pins.
Extending the library-callable surface requires a future Phase 10
sub-phase that updates `_EXTERNAL_UI_CONTROL_REGISTRY`, the Phase
10I tests, the Phase 10J dashboard contract, and this desktop-app
contract; the desktop shell runtime alone MUST NOT widen the
surface.

## Desktop Identity And Operator Attribution

The desktop shell MUST NOT auto-fill any operator identity field
from browser session state, environment variables, an OS-level
"current user" lookup (`whoami`, `$USER`), a packaging-time
configured identity, a code-signing-bound identity, or any
persistent desktop-side identity store. Every mutating CLI
invocation the operator launches via copy-paste from the desktop
shell continues to require the operator to supply identity fields
explicitly (`--attached-by`, `--bootstrapped-by`, `--detached-by`,
`--accepted-by`, etc.), and the desktop shell MUST NOT pre-populate
those fields. This mirrors the shipped Phase 10B `attached_by` /
Phase 10C `bootstrapped_by` / Phase 9G `accepted_by` "never
auto-filled from `$USER` / `whoami`" invariants, and matches the
Phase 10G UI contract's and the Phase 10J dashboard contract's
identity rules.

## Refusal Behavior

The desktop shell MUST refuse fail-closed (render an error state,
NOT silently proceed) in at least the following cases. The specific
shell error-state vocabulary will be defined by the Phase 10M
runtime slice that introduces the shell; this contract pins the
refusal-eligibility:

- the operator-selected folder is missing `AGENTS.md`, `CLAUDE.md`,
  `TASK.md`, or `.agent-loop/`. The shell MUST surface the
  controller-root validation failure as an error state and MUST
  NOT silently render anything against the invalid folder.
- a source artifact named in the shipped Phase 10H / 10I / 10K
  view models is unreadable (not "missing"; missing artifacts
  surface as advisory "not yet present" state). The shell MUST
  surface the read failure as an error state and MUST NOT
  fabricate the artifact's content.
- a canonical artifact's signal-version marker
  (`attach_record_signal_version`, `bootstrap_signal_version`,
  `acceptance_signal_version`, `retry_signal_version`,
  `phase-10h-v1`, `phase-10i-v1`, `phase-10k-v1`, etc.) is
  unrecognized by the shipped validators. The shell MUST surface
  the version mismatch as an error state and MUST NOT render the
  unrecognized record as if its schema were trusted.
- the controller-vs-target ownership boundary is violated (the
  shell tries to render a target-side artifact when no attach
  record is present or fresh). The shell MUST surface the Phase
  10A same-root / nesting refusal, the Phase 10F freshness drift
  refusal, or the missing-attach-record state as an error state;
  the shell MUST NOT fall back to rendering controller-side state
  as if it were target-side.
- the Phase 4C activator's required `APPROVED_FOR_ACTIVATION`
  token is missing or malformed in `.agent-loop/proposed-phase.md`.
  The shell MUST NOT render the proposal as "approved" and MUST
  NOT offer a UI affordance to add the token.
- the shipped view library function raises a `HaltError` (the
  read-side soft-failure path the shipped Phase 10K dashboard
  enforces). The shell MUST surface the HaltError's reason as an
  error state and MUST NOT re-raise the HaltError as a canonical
  halt persistence.
- the Python sub-process the bridge uses fails to import
  `agent_loop`. The shell MUST surface the import failure as an
  error state pointing the operator at the shipped clean-clone
  setup; the shell MUST NOT silently fall back to direct on-disk
  reads.

Every desktop shell error state MUST point the operator at a
shipped CLI remediation step. The shell MUST NOT offer a "fix"
affordance that would mutate canonical state.

## Source-Of-Truth Preservation

Canonical artifacts on disk remain authoritative; the desktop shell
is a RENDERING surface, not a state store. The Phase 10G UI
contract's source-of-truth rules and the Phase 10J dashboard
contract's source-of-truth rules both apply verbatim, plus the
following desktop-specific clarifications:

- the desktop shell MUST NOT introduce a shell-side database,
  key-value store, cache, or session store that holds canonical
  state separately from on-disk artifacts. A per-poll-cycle
  in-memory cache for rendering consistency is permitted; cache
  invalidation per poll is required.
- the desktop shell MUST NOT introduce a shell-side notification
  queue, event-stream subscription, or webhook that would surface
  shell events before the canonical on-disk audit record is
  written. All shell-rendered activity derives from the on-disk
  `orchestrator.log` and per-cycle artifacts.
- the desktop shell MUST NOT introduce a shell-side identity
  token, session token, or auth-bearer beyond what the operating
  system provides; the canonical "who did this" record remains the
  attached_by / bootstrapped_by / accepted_by / detached_by field
  in each canonical artifact.
- the desktop shell MUST treat its own window state as advisory: a
  deep-linked desktop URL or navigation path that names an
  artifact OR a loop-state field is a navigation hint; the
  rendered value MUST come from the on-disk artifact, not from
  the URL or navigation state.
- the desktop shell MUST NOT introduce a shell-side audit log that
  is cited as the canonical record of any operator action.
  Shell-side debugging logs are permitted but are purely advisory
  and MUST NOT replace `orchestrator.log` as the canonical record.
- the desktop shell MUST NOT introduce a shell-side packaged
  database of memory entries, checkpoints, or continuation
  contexts; the Phase 6 memory / checkpoint / continuation tree
  under `.agent-loop/memory/` remains the canonical record.

## Safety Boundaries

The future desktop app shell MUST refuse to:

- commit, push, tag, branch, stash, reset, checkout, or otherwise
  mutate Git history or working-tree state in either the
  controller or the target (the shipped no-Git-automation boundary
  applies to the desktop shell in BOTH roots, mirroring the Phase
  10A - 10K contracts)
- modify `AGENTS.md`, `CLAUDE.md`, `ROADMAP.md`, `README.md`,
  `docs/external-ui-contract.md`,
  `docs/artifact-dashboard-contract.md`,
  `docs/desktop-app-contract.md`, any other docs/ contract file,
  or any source/instruction file in either root as a side effect
  of desktop shell rendering
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
  from the desktop shell process
- silently widen autonomy by treating a desktop button click as an
  implicit operator-identity assertion (no auto-fill of any
  `--*-by` identity flag from browser session, OS username, a
  packaging-time-configured identity, or any persistent
  desktop-side identity store)
- silently activate a target-side phase from the desktop shell;
  the shipped Phase 4C activator + `APPROVED_FOR_ACTIVATION`
  token remain the only path to per-target phase activation
- silently record final human acceptance from the desktop shell;
  the shipped Phase 9G `record-final-acceptance` CLI + the
  `--accepted-by` operator identity remain the only path
- silently re-bootstrap a target from the desktop shell; the
  shipped Phase 10E `attach-external-target --bootstrap` CLI +
  the required operator inputs remain the only path
- introduce concurrent-attach awareness, multi-target desktop
  state, packaging / code-signing / auto-update pipelines, or
  controlled-concurrency scheduling in this contract (single-
  target, single-desktop-session); a future Phase 10N+ slice that
  introduces concurrency-aware behavior, packaging, or
  auto-update will extend this contract with explicit schemas

## Approval Gates

The desktop-app contract preserves every shipped human-approval
gate (Phase 10A + 10B + 10C + 10D + 10E + 10F + 10G + 10H + 10I +
10J + 10K enumeration):

- per-target phase activation continues to require the shipped
  Phase 4C activator + `APPROVED_FOR_ACTIVATION` token; the
  desktop shell MUST NOT issue or auto-fill the token
- per-target `APPROVED_FOR_HUMAN_REVIEW` terminals continue to
  halt the target-side loop and require explicit human approval
  before the next phase begins. The desktop shell MUST NOT
  short-circuit this; the shell MAY display the terminal state
  as a "ready for human approval" advisory badge
- the Phase 9G final human acceptance gate continues to require
  an explicit operator action on the target's canonical artifact
  set via the shipped `record-final-acceptance` CLI. The desktop
  shell MUST NOT record acceptance from a button click
- selecting the Phase 9 fully autonomous PRD-to-product mode on
  a target is an explicit per-attach decision (the Phase 10B
  attach record carries `mode_selection.approval_mode`). The
  desktop shell MUST NOT change the approval mode of an existing
  attach record; mode selection happens only at attach time via
  the shipped `attach-external-target --approval-mode ...` CLI
- the Phase 10F freshness assertion continues to be a fail-closed
  guard a human runs via `verify-external-target`. The desktop
  shell MAY display the inspector's advisory drift report on every
  poll, but the canonical halt-status persistence remains the
  result of an operator-initiated CLI invocation

## Audit Expectations

A reviewer reading the controller's `.agent-loop/orchestrator.log`
plus the target's `.agent-loop/orchestrator.log` MUST be able to
reconstruct what the operator did, without needing access to any
desktop-side log, event stream, session record, or telemetry feed.
Specifically:

- every mutating operation the operator triggers via copy-paste
  from the desktop shell continues to produce its existing
  `[orchestrator] ...` audit line in the appropriate log when the
  operator runs the CLI in a shell. The desktop shell MUST NOT
  swallow, rewrite, or reformat those lines in a way that loses
  information.
- a desktop-shell-initiated library-call delegation (via the
  shipped Phase 10I `invoke-external-control` surface) does NOT
  produce a canonical audit line - this is the Phase 10I behavior
  the desktop shell inherits verbatim; the canonical record of
  which read-only inspector ran is the inspector's return value,
  not a canonical audit-log entry
- a refused desktop shell operation (a shell-side render error, a
  shell-side freshness drift notification, a shell-side refusal
  to dispatch a mutating CLI) does NOT produce a canonical audit
  line; refusals are visible only in the desktop shell's own
  rendering. Canonical halt-status persistence remains the result
  of a human-initiated CLI invocation
- the desktop shell MAY introduce its own shell-side activity log
  (e.g. for debugging shell-side rendering issues) but that log is
  purely advisory and MUST NOT be cited as the canonical record of
  any operator action

## Dependencies On Later Phase 10 Slices

The desktop-app contract is load-bearing for the following later
Phase 10 sub-phases:

- Phase 10M (Desktop App Shell Runtime Initial Slice) satisfies
  this contract. The slice introduces the first native desktop
  window, defines the specific shell error-state vocabulary, pins
  the toolkit and process model, and pins the polling cadence +
  the in-memory cache invalidation rules. Phase 10M MAY reuse the
  shipped Phase 10H / 10I / 10K library functions verbatim; Phase
  10M MUST NOT introduce any mutating desktop surface beyond the
  bounded Phase 10I library-call delegation that already ships.
- Phase 10N and later (Controlled-Concurrency, Multi-Target
  Desktop Sessions, Packaging / Code-Signing / Auto-Update, Native
  System-Tray Reminders) extends this contract with
  concurrent-attach awareness, per-target window refinements,
  packaging and distribution pipelines, auto-update behavior, and
  any other advanced capability; each extension lands in its own
  later Phase 10 sub-phase tracked in `ROADMAP.md`.

The desktop-app contract is consumed by every prior Phase 10 slice
in the following sense: the canonical artifact set the desktop
shell may read is exactly the set the Phase 10A - 10I slices
produce plus the Phase 10J - 10K dashboard's bounded read set, plus
the existing shipped Phase 1 - 9 artifact set. No new canonical
artifact is introduced by the desktop-app contract; the desktop
shell is a strict renderer of existing canonical state.

## Out Of Scope For Phase 10L

Phase 10L is documentation / contract only. The shipped Phase 1 -
9 runtime behavior is preserved unchanged by this slice; no
orchestrator, planner, activator, evidence-collection,
review-routing, checkpoint, continuation, memory, runtime-adapter,
LangChain, VS Code, Phase 9 autonomous-PRD, capacity-reprobe,
final-acceptance, or external-workspace runtime feature work is
introduced. No Phase 10G / 10H / 10I / 10J / 10K surface is
changed. No new CLI subcommand, no new library function, no new
halt status, no new canonical artifact, no Git automation, no
rewrite of `AGENTS.md` / `CLAUDE.md` / `ROADMAP.md` / the Phase 2A
/ 3A / 4A contracts. Adding the desktop app runtime that satisfies
this contract is the work of Phase 10M; controlled-concurrency
awareness, multi-target desktop sessions, packaging /
code-signing / auto-update pipelines, native system-tray reminders,
and any other advanced desktop capability each land in their own
later Phase 10 sub-phases tracked in `ROADMAP.md`.
