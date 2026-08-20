# Desktop First-Run Setup UX Contract

## Status

Fix Phase C1 defines this contract. No first-run setup runtime,
folder picker, PRD intake surface, run-mode selector, run
console, progress console, second controller, background
watcher, or UI-only state plane ships in this slice. The
contract below specifies the FIRST guided single-user desktop
UX for the "pick a folder, load a PRD, choose run behavior, and
run" workflow, aimed at one non-technical local operator who
dislikes terminals. It pins the top-level section vocabulary,
the plain-English state vocabulary, the advanced-detail hiding
rules, the refusal cases, and the source-of-truth boundaries
that the future Fix Phase C runtime slices MUST preserve.
Implementation of the runtime surfaces is deferred to:

- Fix Phase C2: Project Folder Picker And Classification Surface
- Fix Phase C3: PRD Intake UX
- Fix Phase C4: Run Mode Selector
- Fix Phase C5: Start / Stop Agent Control Surface
- Fix Phase C6: Plain-English Run Console
- Fix Phase C7: Review And Approval Surface
- Fix Phase C8: Completion And Handoff Summary

## Scope

This contract covers ONLY the guided single-user desktop UX for
selecting a project folder, loading a PRD, choosing run
behavior, starting / stopping the agent, and understanding
plain-English progress without terminal knowledge. It answers:

- which top-level sections the default view exposes and in what
  order (a closed set)
- which plain-English states the surface uses for setup, ready,
  running, waiting, blocked, approval-required, and complete
  (a closed set)
- which technical details are hidden by default and which
  appear only in an optional Advanced surface
- how the guided workflow maps back to the shipped canonical
  artifacts and shipped runtime helpers rather than a UI-only
  state store
- which refusal, approval, and audit boundaries the future
  runtime MUST preserve
- what MUST NOT be added under the banner of "first-run setup"
  (a second controller, a UI-only state plane, a hidden
  progress cache, an autonomous run driver, a network endpoint)

Everything outside that guided single-user surface is out of
scope. In particular:

- the actual Tkinter widget layout / folder picker library /
  PRD reader / run console renderer / progress bar library is
  a Fix Phase C2 through C8 implementation concern
- any MCP-side "guided setup" transport, network endpoint,
  WebSocket, or server-sent-event stream is out of scope for
  Fix Phase C1 AND for every Fix Phase C runtime slice (the
  shipped canonical artifacts + shipped runtime helpers remain
  the sole source of truth)
- any "autonomous run mode" where the desktop surface decides
  when to start / stop / advance the agent without an explicit
  operator gesture is out of scope for every slice under this
  contract

## Distinction From Shipped Artifacts And Surfaces

The shipped repository already ships the following canonical
artifacts and shipped surfaces that this contract MUST route
through rather than duplicate:

- `.agent-loop/loop-state.json` (orchestrator-owned runtime
  state per Phase 3A)
- `.agent-loop/current-phase.md`, `.agent-loop/current-task.md`,
  `.agent-loop/phase-plan.md`, `TASK.md`, `ROADMAP.md` (planning
  artifacts owned by Codex per the shipped Phase 3A / 4A
  contracts)
- `.agent-loop/codex-review.md` (Codex-authored review verdict
  + findings)
- `.agent-loop/fix-prompt.md` (Codex-authored repair prompt)
- `.agent-loop/claude-prompt.md` (Codex-authored implementation
  prompt handoff)
- `.agent-loop/claude-summary.md` (Claude-authored
  implementation summary)
- `.agent-loop/orchestrator.log` (orchestrator-owned audit
  trail per Phase 3A)
- the shipped Phase 10L desktop-app contract at
  `docs/desktop-app-contract.md`
- the shipped Phase 10AH orchestration visualization contract
  at `docs/desktop-orchestration-visualization-contract.md`
- the shipped Phase 10AF desktop Codex conversation contract
  at `docs/desktop-codex-conversation-contract.md`
- the shipped Fix Phase B1 / B2 / B3 desktop bootstrap UX
  (empty-target detection, bootstrap form, dispatch surface)
- the shipped Phase 10R Desktop App PRD Intake And Project
  Start Flow at `docs/external-workspace-bootstrap-contract.md`
- the shipped Phase 10Q Desktop App Run Profiles And Approval
  Controls
- the shipped Phase 10I library-callable control cap and
  `attach_external_target(...)` runtime boundary
- the shipped Phase 10AB / 10AC / 10AD controlled-concurrency
  contract at `docs/controlled-concurrency-contract.md`
- the shipped Phase 5A / 5B / 5C / 5D approval-mode runtime

The Fix Phase C1 surface is a GUIDED UX LAYER on top of those
shipped artifacts and surfaces. It NEVER introduces a competing
state store, NEVER mirrors a canonical artifact into a hidden
UI-only cache, NEVER lets the desktop UI write a canonical
artifact under a role it does not already own per the shipped
Phase 10AB map, and NEVER invents a parallel run-mode / run-
console / progress-tracking plane.

## Top-Level Section Vocabulary

The desktop first-run setup surface MUST expose a CLOSED
top-level section vocabulary. The Fix Phase C1 closed
vocabulary is:

- `Project` - operator picks a project folder for the guided
  workflow. This section surfaces the shipped Phase 10C /
  Fix Phase B1 folder classification (`existing_project`,
  `empty_folder`, `partial_target`, `malformed_target`) as
  plain-English next-step messaging. Materialises through the
  shipped folder-inspection helpers; NEVER invents a desktop-
  only folder-state store.
- `PRD` - operator loads a product-requirements document (or
  equivalent human objective) for the selected project. This
  section surfaces the shipped Phase 10R PRD intake path and
  the shipped Fix Phase B2 bootstrap `human_objective` /
  `project_intent` fields. Materialises through the shipped
  PRD intake surface; NEVER writes a canonical artifact
  directly.
- `Run Mode` - operator chooses run behavior from the shipped
  Phase 5A approval-mode closed enum (`review`, `strict`,
  `autonomous`) plus the shipped Phase 10Q run-profile options.
  This section surfaces plain-English descriptions of each
  mode; NEVER invents a new run mode outside the shipped
  closed enum.
- `Run` - operator starts / stops / resumes the agent. This
  section surfaces the shipped `run`, `resume`, `auto-continue`
  entrypoints as plain-English action buttons; NEVER invents a
  parallel dispatch path.
- `Progress` - operator monitors the guided run in plain-
  English. This section surfaces the shipped Phase 10AI
  orchestration-visualization view + the shipped Phase 10AG
  Codex conversation mirrors + the shipped Phase 7B artifact
  inspector as a plain-English progress console; NEVER
  introduces a parallel progress cache.

The vocabulary is CLOSED and ORDERED: `Project` MUST appear
first, then `PRD`, then `Run Mode`, then `Run`, then
`Progress`. A future runtime slice adding a section outside
this closed set is a contract widening and requires a fresh
contract slice.

## Plain-English State Vocabulary

The desktop first-run setup surface MUST expose a CLOSED
plain-English state vocabulary. Every visible surface state
maps to exactly one of these values:

- `setup` - the operator has not yet completed the guided
  workflow (Project / PRD / Run Mode all not yet chosen).
  Plain-English text: "Set up your project."
- `ready` - the operator has completed the guided workflow but
  has not yet started the agent. Plain-English text: "Ready to
  run."
- `running` - the agent is actively working. Plain-English
  text: "Working on your project."
- `waiting` - the agent is waiting on an external condition
  that is expected to resolve without operator input (for
  example, a shipped Phase 9F capacity-halt reprobe or a
  Phase 10AC overlap-safe recovery). Plain-English text:
  "Waiting a moment before continuing."
- `blocked` - the agent is halted and cannot continue without
  a shipped intervention (for example, a shipped `halted_*`
  status other than the strict-mode gates). Plain-English
  text: "Stopped. Needs help to continue."
- `approval_required` - the agent is paused at a shipped
  Phase 5A / 5C human gate (`pre_claude_prompt`,
  `pre_fix_prompt`, `pre_codex_review`,
  `phase_complete_awaiting_human_approval`, `halt_resolution`,
  or a strict-mode halt status). Plain-English text: "Waiting
  for your approval to continue."
- `complete` - the current shipped phase has landed at
  `phase_complete_awaiting_human_approval` OR the shipped
  Phase 9G human acceptance gate has fired. Plain-English
  text: "Done. Review the result."

The plain-English state vocabulary is CLOSED. The surface MUST
derive each value from the shipped canonical mirrors
(`loop-state.json` `status` + `awaiting_human_for`, plus the
shipped Phase 10AI advisory-derived `blocked_or_halted` /
`human_gate_pending` flags) rather than tracking a parallel UI-
only state variable.

## Guided Single-User Workflow

The default first-run flow MUST guide one non-technical local
operator through the following ordered steps, exactly one
active at a time:

1. `Project`: operator clicks "Choose folder" and picks a
   project directory using the OS-native folder picker (no
   typed path). The shipped Fix Phase B1 classification
   surfaces the folder state in plain English and offers the
   next-step action (attach the existing project, bootstrap
   an empty folder, or refuse a partial / malformed folder
   with plain-English recovery text).
2. `PRD`: operator clicks "Load PRD" and picks a PRD file (or
   pastes a short human-objective sentence for the shipped
   Fix Phase B2 bootstrap flow). The shipped PRD intake path
   validates the input; the surface refuses fail-closed on
   missing / empty / whitespace / embedded-double-quote input
   with plain-English text.
3. `Run Mode`: operator picks from the shipped Phase 5A closed
   enum (`review`, `strict`, `autonomous`) via a plain-English
   dropdown. Default MUST be `review` (safest); `strict` and
   `autonomous` MUST be one click away but MUST NOT be the
   default and MUST NOT be auto-selected from any source.
4. `Run`: the `Run` button becomes enabled once Project, PRD,
   and Run Mode are all chosen. Clicking `Run` dispatches
   through the shipped `run` / `resume` / `auto-continue`
   entrypoint per Run Mode. The `Stop` button surfaces the
   shipped halt / pause path.
5. `Progress`: while the agent is running the operator sees the
   plain-English state, a short human-readable summary of the
   most recent activity, and a shipped-mirror surface pointing
   to the canonical artifact where the operator can read more
   detail. Advanced technical detail is HIDDEN by default and
   only reachable through an explicit "Advanced" toggle.

At no point does the surface auto-advance from one step to the
next without an explicit operator gesture. At no point does the
surface auto-fill operator identity from OS state, environment
variables, browser session, or packaging-time identity.

## Advanced Detail Hiding Rules

The default first-run experience MUST HIDE the following
technical details behind an optional Advanced surface. Each
hidden item MAY appear ONCE in the shipped Advanced surface
(matching the shipped Phase 10AG / Phase 10AI Advanced-toggle
convention), but MUST NOT appear in any default surface:

- raw `loop-state.json` `status` / `awaiting_human_for`
  vocabulary
- raw shipped `halted_*` status names
- raw shipped `awaiting_human_for` names
  (`pre_claude_prompt`, `pre_fix_prompt`, `pre_codex_review`,
  `phase_complete_awaiting_human_approval`,
  `halt_resolution`, `token_exhaustion_continuation`)
- raw CLI subcommand names (`run`, `resume`, `auto-continue`,
  `record-final-acceptance`, `plan`, `activate`,
  `attach-external-target`)
- raw canonical artifact paths
  (`.agent-loop/codex-review.md`, `.agent-loop/fix-prompt.md`,
  `.agent-loop/claude-prompt.md`, etc.)
- raw shipped review verdicts (`APPROVED_FOR_HUMAN_REVIEW`,
  `NEEDS_FIXES`, `FAILED_REQUIRES_HUMAN`)
- raw shipped Phase 10AC overlap-safe detection aggregate
  values (`refused_pending_recovery`, `signal_detected`,
  `no_signal`, `unknown`)
- raw shipped audit-log lines
- raw shipped `attached_by` / `bootstrapped_by` /
  `accepted_by` identity field names
- shipped Phase 10AG closed intent / refusal vocabulary tokens
- shipped Phase 10AI graph node / edge / gate_category /
  status_icon vocabulary tokens
- terminal / CLI onboarding copy that the shipped Phase 10P
  Desktop App Operator Setup surface already covers

The Advanced surface MUST use exactly one operator-visible
toggle (the shipped "Advanced" toggle convention). It MUST NOT
be a separate window, a modal dialog, or a per-section drawer;
that would fragment the guided single-user flow. When the
operator clicks Advanced, every hidden detail becomes visible
inline; when they click Advanced again, it returns to the
default hidden state.

## Refusal Behavior

The future Fix Phase C2 through C8 runtime slices MUST refuse
fail-closed on every one of the following conditions, surfacing
an explicit plain-English refusal line naming the shipped rule
that was violated. No conditional "maybe" refusals, no silent
no-ops:

- top-level section outside the closed
  `PROJECT / PRD / RUN_MODE / RUN / PROGRESS` vocabulary
  (refused with `refused_section_outside_closed_vocabulary`)
- plain-English state outside the closed
  `SETUP / READY / RUNNING / WAITING / BLOCKED /
  APPROVAL_REQUIRED / COMPLETE` vocabulary (refused with
  `refused_state_outside_closed_vocabulary`)
- run mode outside the shipped Phase 5A closed enum
  `review / strict / autonomous` (refused with
  `refused_run_mode_outside_shipped_enum`)
- attempt to write ANY canonical artifact from the first-run
  setup surface, including `loop-state.json`,
  `orchestrator.log`, any planning artifact, `codex-review.md`,
  `fix-prompt.md`, `claude-prompt.md`, or `claude-summary.md`
  (refused with `refused_canonical_write_from_first_run_setup`)
- attempt to auto-advance any step of the guided workflow
  without an explicit operator gesture (refused with
  `refused_auto_advance_from_first_run_setup`)
- attempt to auto-fill operator identity, PRD content, or the
  human objective sentence from OS state, environment
  variables, browser session, or packaging-time identity
  (refused with `refused_auto_fill_operator_identity`)
- attempt to persist first-run setup state (project selection,
  PRD content, run-mode choice) to a UI-only side file (refused
  with `refused_ui_only_state_persistence`)
- attempt to expose a raw technical vocabulary token in the
  default (non-Advanced) surface (refused with
  `refused_technical_detail_in_default_surface`)
- attempt to bypass the shipped Phase 10L / 10M polling cadence
  with a background thread or timer (refused with
  `refused_background_watcher_beyond_cadence`)

Every refusal MUST include the offending value / section id /
state / mode, the shipped rule that was violated (with a docs
anchor citation matching the Phase 10AE auditability
convention), and the closed refusal category the future runtime
MUST expose.

Additionally, non-refusal operator cancellation gestures MUST
route through a bounded closed cancellation-category vocabulary
so every first-run operator gesture remains auditable through
`.agent-loop/orchestrator.log`. The Fix Phase C2 initial slice
ships one such category:

- operator closed the OS-native folder picker without choosing
  a folder (audited as `cancelled_folder_picker` via the shipped
  `_fix_phase_c2_format_audit_line(...)` writer; the audit line
  MUST NOT re-classify the current folder payload, MUST NOT
  clear the current classification / next-action display, and
  MUST NOT dispatch any attach / bootstrap / run action)

Future Fix Phase C runtime slices adding new cancellation
gestures MUST extend this closed vocabulary in the shipped
runtime constants (e.g. `FIX_PHASE_C2_REFUSAL_CATEGORIES` for
the Project section) rather than emitting an unaudited no-op.

## Approval Gates

The desktop first-run setup surface MUST preserve every shipped
approval gate verbatim. Specifically it MUST NOT:

- short-circuit the Phase 5A / 5C / 5D approval-mode gating.
  In `review` mode the Run button dispatches a single normal
  cycle; in `strict` mode the shipped strict-mode gate fires
  and requires explicit operator resume; in `autonomous` mode
  the shipped autonomous path runs without per-cycle approval
  but continues to honor every non-approval halt gate.
- short-circuit the Phase 4C activator +
  `APPROVED_FOR_ACTIVATION` human approval for any new-phase
  advance triggered from the first-run setup surface.
- short-circuit the Phase 9G human acceptance gate for any
  `record-final-acceptance` triggered from the first-run
  setup surface. The `Progress` section's `complete` state MUST
  route the operator through the shipped Phase 9G surface
  (including the required `--accepted-by <NAME>` operator
  identity typed per invocation, no auto-fill).
- short-circuit the Phase 10U MCP action guardrail per-tool
  approval policy for any MCP mutation triggered from the
  first-run setup surface.
- short-circuit the Phase 5F post-review prompt bootstrap for
  any Claude prompt handoff triggered from the first-run setup
  surface.

The first-run setup surface is a GUIDED UX LAYER; every
downstream action routes through the shipped surface that
already owns it (`run` for a new cycle, `resume` for a
strict-mode gate, `record-final-acceptance` for Phase 9G, the
shipped Phase 10AG Codex conversation panel for Codex
requests, the shipped Fix Phase B3 bootstrap dispatcher for a
new empty-folder project).

## Audit Expectations

Every operator gesture in the first-run setup surface MUST
audit through the shipped surfaces:

- `.agent-loop/orchestrator.log` receives a bounded audit line
  per the shipped Phase 3A orchestrator contract naming the
  first-run setup signal version, the section id (from the
  closed section vocabulary), the closed refusal category if
  the gesture refused, and the epoch-second timestamp. The
  audit line format follows the shipped Phase 10AG
  `_desktop_codex_conversation_format_audit_line` /
  Phase 10AI `_desktop_orchestration_visualization_format_audit_line`
  convention.
- the shipped canonical artifacts (`loop-state.json`,
  `current-phase.md`, `current-task.md`, `phase-plan.md`,
  `codex-review.md`, `claude-summary.md`, `claude-prompt.md`,
  `fix-prompt.md`, the shipped Phase 2A / 2B evidence
  artifacts) receive NO new audit obligation from this
  contract; the first-run setup surface only ROUTES through
  the shipped write paths that already exist.

The first-run setup surface MUST NOT introduce a separate
audit surface (a "first-run history" file, a per-session
gesture log, a UI-only event stream). The shipped
`.agent-loop/orchestrator.log` is the sole audit source of
truth.

## Source-Of-Truth Preservation (No Hidden UI Store)

The Fix Phase C1 contract preserves the shipped source-of-truth
model verbatim. Specifically the future Fix Phase C2 through C8
runtime slices MUST NOT introduce ANY of the following:

- a UI-only "first-run setup" JSON file, SQLite database,
  MessagePack blob, or any other persistent store
- a session state file that shadows `.agent-loop/loop-state.json`
  for the first-run setup surface's own state
- a "project selection" cache file that mirrors the operator's
  folder selection to disk under any name that is not a
  shipped canonical artifact
- a "PRD staging area" file that buffers PRD content before it
  lands in a shipped canonical artifact
- a "run mode preference" file that shadows the shipped
  Phase 5A approval-mode field in `loop-state.json`
- a browser-session identity cache, an MCP-side session
  cookie, or any cross-session identity persistence
- a "recents" list of previously-selected folders / PRDs /
  run modes (the operator uses the OS's native file browser to
  pick each time)
- an autofill / suggestion engine that derives folder path /
  PRD content / operator identity from OS state (`$USER`,
  `whoami`, recent-files, browser session, packaging-time
  identity)
- a background watcher / polling thread beyond the shipped
  Phase 10L / 10M polling cadence rules

The first-run setup surface's per-session in-memory state (the
current section, the current progress state, the current
plain-English display text) is RE-DERIVED on every poll tick
from the shipped canonical mirrors + advisory derivations. On
next session the operator sees a fresh derivation from the
current on-disk state and MUST NOT see any stale cached value.

## Ownership Boundary Preservation

The Fix Phase C1 surface preserves every shipped ownership
boundary verbatim. Specifically:

- Codex remains the SOLE writer of planning artifacts
  (`ROADMAP.md`, `TASK.md`, `.agent-loop/phase-plan.md`,
  `.agent-loop/current-phase.md`,
  `.agent-loop/current-task.md`), `codex-review.md`,
  `fix-prompt.md`, and `claude-prompt.md` per the shipped
  Phase 3A / 4A / 10AB contracts. The first-run setup surface
  NEVER writes these directly.
- Claude remains the SOLE writer of `claude-summary.md` and
  the shipped Claude-owned implementation surface (source,
  tests, non-planning docs). The first-run setup surface
  NEVER writes these directly.
- The orchestrator remains the SOLE writer of
  `loop-state.json`, `orchestrator.log`, and the shipped
  Phase 2A / 2B evidence artifacts. Any first-run setup
  gesture routed toward these is refused fail-closed with
  `refused_canonical_write_from_first_run_setup`.
- Human-owned decisions (final acceptance,
  `APPROVED_FOR_ACTIVATION` token,
  `APPROVED_FOR_HUMAN_REVIEW` verdict) remain human-authored.
  The first-run setup surface NEVER auto-generates any of them.

## Dependencies On Fix Phase C2 Through C8 (Runtime Implementation)

Fix Phase C2 through C8 will implement the runtime slices that
satisfy this contract. Each downstream slice is expected to
add:

- Fix Phase C2: bounded guided folder picker + shipped Phase
  10C / Fix Phase B1 classification surfaced in plain English;
  no path-typing input, no OS-state auto-fill.
- Fix Phase C3: bounded PRD intake picker + inline validation
  matching the shipped Fix Phase B2 refusal categories; no
  hidden PRD staging cache.
- Fix Phase C4: bounded run-mode selector wired to the shipped
  Phase 5A closed enum + Phase 10Q run profiles; default
  `review`, no auto-selection.
- Fix Phase C5: bounded Start / Stop / Resume control surface
  wired to the shipped `run`, `resume`, `auto-continue`, and
  halt entrypoints; no parallel dispatcher.
- Fix Phase C6: bounded plain-English run console derived from
  the shipped Phase 10AI orchestration visualization view +
  shipped Phase 10AG conversation mirrors + shipped Phase 7B
  artifact inspector; no separate progress cache.
- Fix Phase C7: bounded review-and-approval surface routing
  through the shipped Phase 5A / 5C / 5F / 9G approval gates;
  no bypass of any shipped gate.
- Fix Phase C8: bounded completion-and-handoff summary
  derived from the shipped `phase_complete_awaiting_human_approval`
  status + the shipped Phase 9G acceptance surface; no
  auto-generation of the acceptance token.

None of the Fix Phase C runtime slices will add: an
autonomous run driver, a UI-only state store, a network
transport, a background watcher, a new library-callable
control, or a new canonical artifact. This is a hard boundary;
a Fix Phase C runtime PR that includes any of those is
`NEEDS_FIXES`.

## Out Of Scope For Fix Phase C1

The Fix Phase C1 slice is contract-definition only. The
following are explicitly out of scope:

- any Tk panel implementation, widget layout, folder picker
  library, PRD reader, run console renderer, progress bar
  library, or `_launch_desktop_app_window(...)` addition
- any new library-callable control (the shipped Phase 10I
  three-control cap is preserved verbatim)
- any new canonical artifact (the shipped canonical set is
  preserved verbatim; no `first-run-setup.json`,
  `prd-staging.md`, `run-preferences.json`, or similar file)
- any change to the shipped Phase 2A / 3A / 4A / 5A / 6M /
  10L / 10M / 10O / 10AB / 10AC / 10AD / 10AF / 10AG / 10AH /
  10AI / Fix Phase B1 / B2 / B3 contracts
- any Git automation
- any framework-side integration (crewai / langgraph /
  langchain remain evaluation-only per the shipped Phase 10AE
  contract)
- any change to the shipped `EXTERNAL_TARGET_APPROVAL_MODES`
  closed enum, the shipped
  `PRIMARY_DESKTOP_BOOTSTRAP_FIELD_NAMES` closed enum, the
  shipped Phase 10AB `_DESKTOP_CONCURRENCY_OWNERSHIP_MAP`
  closed map, the shipped Phase 10AG
  `DESKTOP_CODEX_CONVERSATION_INTENT_IDS` /
  `DESKTOP_CODEX_CONVERSATION_REFUSAL_CATEGORIES` closed
  vocabulary, or the shipped Phase 10AI
  `PHASE_10AI_VISUALIZATION_VOCABULARY` /
  `PHASE_10AI_STATUS_CATEGORIES` /
  `PHASE_10AI_GATE_CATEGORIES` /
  `PHASE_10AI_REFUSAL_CATEGORIES` closed vocabulary
