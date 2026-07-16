# Desktop Orchestration Graph And Phase-State Visualization Contract

## Status

Phase 10AH defines this contract. No visualization runtime, graph
view, icon-based flow view, node/edge renderer, progress cache,
UI-only orchestration state plane, background watcher, or second
controller ships in this slice. The contract below specifies the
FIRST desktop surface that will let the operator SEE the live
orchestration state as a bounded graph or icon-based flow from
inside the shipped desktop app without inventing a competing
control plane, a hidden progress cache, or a UI-only truth store.
It pins the closed visualization vocabulary, the canonical-mirror-
vs-advisory-derived-state rule, the closed node / edge / status
enumeration, the refusal cases, the approval gates, the audit
expectations, and the source-of-truth boundaries the future
runtime slice MUST preserve. Implementation of the visualization
runtime is deferred to:

- Phase 10AI: Desktop Orchestration Visualization Runtime Initial
  Slice (the first shipped desktop surface that renders a bounded
  graph / icon-based flow of the live orchestration state from
  the shipped canonical artifacts, refuses fail-closed on every
  boundary this contract enumerates, and NEVER mutates any
  canonical artifact).

## Scope

This contract covers ONLY the desktop-side visualization surface
that reports the live orchestration state as a graph or icon-
based flow. It answers:

- which orchestration state values are in scope for a bounded
  visualization vocabulary (a closed set)
- which visualization values are canonical mirrors of shipped on-
  disk artifacts vs advisory derived state
- how a future desktop graph / node / icon-based flow view
  represents phase, sub-phase, task, loop-state status, review
  branch, fix branch, human-gated pause states, blocked / halted
  states, and artifact-backed progress
- how the visualization refreshes without introducing a hidden
  UI-only state plane, a progress cache, a background watcher
  beyond the shipped polling cadence, or a second orchestrator
- which refusal, approval, and audit boundaries the future
  runtime MUST preserve
- what MUST NOT be added under the banner of "orchestration
  visualization" (a second controller, a UI-only progress store,
  a graph-side canonical write path, an autonomous orchestration
  driver)

Everything outside that reporting surface is out of scope. In
particular:

- the actual Tkinter widget layout / node rendering library /
  edge routing algorithm / icon set is a Phase 10AI
  implementation concern
- any MCP-side "graph" transport, network endpoint, WebSocket,
  server-sent-event stream, or persistent socket connection is
  out of scope for Phase 10AH AND for Phase 10AI (the shipped
  canonical artifacts are the sole read source)
- any "autonomous progression mode" where the visualization
  surface decides when to advance the phase or trigger a Codex
  invocation is out of scope for both slices
- any Git-side graph (branch topology, commit graph) or CI-side
  pipeline graph is out of scope; this contract covers ONLY the
  shipped `.agent-loop/` orchestration state

## Distinction From Shipped Artifacts And Surfaces

The shipped repository already ships the following canonical
artifacts and shipped surfaces that this contract MUST report
FROM without duplicating or shadowing:

- `.agent-loop/loop-state.json` (orchestrator-owned runtime
  state per Phase 3A: `phase`, `sub_phase`, `task`, `status`,
  `cycle_count`, `max_cycles`, `last_verdict`,
  `last_verdict_phase`, `approval_mode`, `awaiting_human_for`)
- `.agent-loop/current-phase.md`, `.agent-loop/current-task.md`,
  `.agent-loop/phase-plan.md`, `TASK.md`, `ROADMAP.md` (planning
  artifacts owned by Codex per the shipped Phase 3A / 4A
  contracts)
- `.agent-loop/codex-review.md` (Codex-authored review verdict +
  findings)
- `.agent-loop/fix-prompt.md` (Codex-authored repair prompt for
  Claude)
- `.agent-loop/claude-prompt.md` (Codex-authored implementation
  prompt handoff for Claude)
- `.agent-loop/claude-summary.md` (Claude-authored implementation
  summary)
- `.agent-loop/orchestrator.log` (orchestrator-owned audit trail
  per Phase 3A)
- the shipped Phase 2A / 2B evidence artifacts
  (`.agent-loop/git-status.log`, `.agent-loop/git-diff.patch`,
  `.agent-loop/test-output.log`, `.agent-loop/lint-output.log`,
  `.agent-loop/typecheck-output.log`,
  `.agent-loop/build-output.log`)
- the shipped Phase 10L desktop-app contract at
  `docs/desktop-app-contract.md` that pins the desktop shell as
  a read-only reporter over the shipped Python runtime
- the shipped Phase 10K artifact-dashboard contract at
  `docs/artifact-dashboard-contract.md` that pins the closed
  per-artifact per-line attribution convention
- the shipped Phase 10AF desktop Codex conversation contract at
  `docs/desktop-codex-conversation-contract.md` that pins the
  advisory-vs-canonical mirror rule
- the shipped Phase 10AB (Controlled Concurrent Operation
  Contract), the shipped Phase 10AC (Overlap-Safe Detection),
  and the shipped Phase 10AD (Codex-Owned Concurrent Work)
  controlled-concurrency contract at
  `docs/controlled-concurrency-contract.md` that pins per-
  artifact `owner_role` and refuses fail-closed on role
  violation
- the shipped Phase 10AG desktop Codex conversation runtime
  panel inside `_launch_desktop_app_window(...)` which is the
  precedent bounded reporting surface this visualization slice
  extends

The Phase 10AH surface is a REPORTING SURFACE over those shipped
artifacts. It NEVER introduces a competing state store, NEVER
mirrors a canonical artifact into a hidden UI-only cache, NEVER
lets the visualization panel write a canonical artifact, and
NEVER auto-advances phase, sub-phase, task, verdict, or approval
state.

## In-Scope Visualization Vocabulary

The desktop orchestration visualization surface MUST expose a
CLOSED set of orchestration state values. The Phase 10AH closed
vocabulary is:

- `phase` - the current mainline phase id (e.g. `Phase 10`).
  Canonical mirror of `.agent-loop/loop-state.json` field
  `phase` (and of `.agent-loop/current-phase.md`).
- `sub_phase` - the current bounded sub-phase id (e.g.
  `Phase 10AH - Orchestration Graph And Phase-State Visualization
  Contract`). Canonical mirror of
  `.agent-loop/loop-state.json` field `sub_phase` (and of
  `.agent-loop/current-phase.md`).
- `task` - the current active task summary (a human-readable
  sentence describing the active task, e.g. "Define the contract
  for a bounded desktop orchestration-visualization surface ..."
  as written to `.agent-loop/loop-state.json` by the shipped
  Phase 3A / 4A planner and mirrored into
  `.agent-loop/current-task.md`). Canonical mirror of
  `.agent-loop/loop-state.json` field `task` (and of the
  `## Task` block in `.agent-loop/current-task.md`). The
  visualization surface renders this string verbatim; it is
  NOT a task-id token and MUST NOT be re-derived, truncated
  into a slug, or reformatted.
- `loop_state_status` - the current shipped Phase 3A / 5C loop
  state status (one of `awaiting_claude_implementation`,
  `awaiting_codex_review`, `awaiting_fix_prompt`,
  `awaiting_claude_fix`, `awaiting_codex_re_review`,
  `phase_complete_awaiting_human_approval`, `halted_*` variants
  including the strict-mode gate halts, the token-exhaustion
  halt, the overlap-unsafe halt, and the human-acceptance halt).
  Canonical mirror of `.agent-loop/loop-state.json` field
  `status`.
- `approval_mode` - the current shipped Phase 5A / 5B / 5C / 5D
  approval mode (`review`, `strict`, `autonomous`). Canonical
  mirror of `.agent-loop/loop-state.json` field `approval_mode`.
- `cycle_count` / `max_cycles` - the shipped Phase 3A cycle
  progress markers. Canonical mirror of
  `.agent-loop/loop-state.json` fields `cycle_count` and
  `max_cycles`.
- `awaiting_human_for` - the current shipped Phase 5A / 5C human
  gate marker (`pre_claude_prompt`, `pre_fix_prompt`,
  `pre_codex_review`, `phase_complete_awaiting_human_approval`,
  `halt_resolution`). Canonical mirror of
  `.agent-loop/loop-state.json` field `awaiting_human_for`.
- `last_verdict` / `last_verdict_phase` - the shipped Phase 5B
  post-review verdict marker (`APPROVED_FOR_HUMAN_REVIEW`,
  `NEEDS_FIXES`, `FAILED_REQUIRES_HUMAN`). Canonical mirror of
  `.agent-loop/loop-state.json` fields `last_verdict` and
  `last_verdict_phase`.
- `review_branch_active` - advisory derived state: `True` when
  the loop is on the normal-cycle review path (loop-state
  `status` is in the shipped normal-cycle status set OR
  `last_verdict` names an approved review), `False` otherwise.
  Derived from the canonical mirror; NEVER an independent write.
- `fix_branch_active` - advisory derived state: `True` when the
  loop is on the fix-cycle path (loop-state `status` is in the
  shipped fix-cycle status set OR `.agent-loop/fix-prompt.md`
  exists AND its mtime is newer than
  `.agent-loop/claude-summary.md`'s mtime). Derived from the
  canonical mirror; NEVER an independent write.
- `human_gate_pending` - advisory derived state: `True` when
  `awaiting_human_for` names any shipped human gate OR when
  loop-state `status` is in the shipped strict-mode-halt set
  (`halted_awaiting_human_pre_claude_prompt`,
  `halted_awaiting_human_pre_fix_prompt`,
  `halted_awaiting_human_pre_codex_review_normal`,
  `halted_awaiting_human_pre_codex_review_fix`). Derived from
  the canonical mirror; NEVER an independent write.
- `blocked_or_halted` - advisory derived state: `True` when
  loop-state `status` starts with `halted_` OR when the shipped
  Phase 10AC overlap-safe detection aggregate is
  `refused_pending_recovery` OR when the shipped Phase 9F
  capacity-halt reprobe reports a token-exhaustion halt.
  Derived from the canonical mirror + the shipped Phase 10AC
  view; NEVER an independent write.
- `artifact_backed_progress` - advisory derived state: an
  ordered dict listing the presence (and mtime) of each shipped
  canonical artifact (`claude-summary.md`, `codex-review.md`,
  `claude-prompt.md`, `fix-prompt.md`, `phase-plan.md`,
  `current-phase.md`, `current-task.md`, the shipped Phase 2A /
  2B evidence artifacts). Derived from `Path.stat()` only;
  NEVER an independent write; NEVER reads BODY content beyond
  what the shipped Phase 7B inspector already reads.

The vocabulary is CLOSED. A visualization value outside this set
MUST be refused fail-closed by the future runtime; the operator
sees an explicit refusal naming the closed vocabulary rather
than a silent no-op.

## Canonical Mirror Vs Advisory Derived State

Every displayed value in the future visualization surface MUST
carry an explicit attribution tag distinguishing its source
category, matching the shipped Phase 10AF advisory-vs-canonical
mirror convention:

- CANONICAL MIRROR (`[canonical mirror]`) - the on-disk value
  read verbatim from a shipped canonical artifact. The surface
  MUST name the source file path in every mirror line. The on-
  disk file is the source of truth; the desktop mirror is
  advisory. Applies to: `phase`, `sub_phase`, `task`,
  `loop_state_status`, `approval_mode`, `cycle_count`,
  `max_cycles`, `awaiting_human_for`, `last_verdict`,
  `last_verdict_phase`.
- ADVISORY DERIVED STATE (`[visualization-advisory]`) - a value
  the visualization surface COMPUTES from one or more canonical
  mirrors. The surface MUST name the source mirrors the value
  was derived from. The derived value is ADVISORY and NEVER a
  canonical write. Applies to: `review_branch_active`,
  `fix_branch_active`, `human_gate_pending`,
  `blocked_or_halted`, `artifact_backed_progress`.

The visualization surface MUST NOT introduce a THIRD category
(e.g. a "predicted next state" that shadows either). If a
future value is neither a canonical mirror nor a derivation
from canonical mirrors, it does NOT belong on this surface.

## Node / Edge / Status Model For The Future Graph View

The future Phase 10AI graph view MUST use a CLOSED node and edge
model derived from the visualization vocabulary above:

- NODES represent orchestration state values from the closed
  vocabulary. Each node MUST carry an id (matching one of the
  vocabulary keys), a `source_category` (`canonical_mirror` or
  `visualization_advisory`), a `source_artifacts` list (the
  shipped canonical artifact paths this node reads from), and a
  `current_value` (the mirror / advisory value at read time).
- EDGES represent the shipped orchestration transitions between
  state values that the shipped Phase 3A / 5A / 5C / 5D / 10AC
  contracts already define. Each edge MUST carry a `from_node`
  id, a `to_node` id, a `transition_id` (matching one of the
  shipped transition names in the phase-plan history or the
  Phase 3A cycle contract), a `gate_category` (one of
  `no_gate`, `approval_gate`, `evidence_gate`,
  `overlap_safe_gate`, `strict_mode_gate`, `human_acceptance_
  gate`, `token_exhaustion_gate`), and an `edge_source_category`
  (always `canonical_mirror` because every transition is
  defined by a shipped contract).
- STATUS ICONS represent the closed set of shipped status
  categories (`in_progress`, `awaiting_review`,
  `awaiting_human`, `halted`, `complete`). Each status icon MUST
  carry an id (matching one of the five categories) and a
  `source_mirror` field naming the canonical artifact that
  drove the classification.

The node / edge / status model is CLOSED. A future runtime MUST
NOT introduce a node id, edge id, gate category, or status
category outside this closed model without a fresh contract
slice extending the vocabulary.

## Refresh And Cadence

The future Phase 10AI visualization runtime MUST refresh through
the shipped Phase 10L / 10M polling cadence rules. Specifically:

- the visualization panel MUST refresh on the same poll tick as
  the shipped Phase 10AG canonical mirror panel and the shipped
  Phase 10K artifact dashboard panel
- the visualization panel MUST NOT introduce a separate
  background thread, timer, or watcher beyond the shipped poll
  cadence
- the visualization panel MUST NOT cache derived state across
  poll ticks (each tick re-derives from the fresh canonical
  mirror; stale advisory state is a hard bug)
- the visualization panel MUST NOT re-read a canonical artifact
  more than once per poll tick (the shipped Phase 10L reader
  cadence is preserved)

## Refusal Behavior

The future Phase 10AI runtime MUST refuse fail-closed on every
one of the following conditions, surfacing an explicit refusal
line naming the shipped rule that was violated. No conditional
"maybe" refusals, no silent no-ops:

- attempt to display a value outside the closed
  `PHASE_10AH_ORCHESTRATION_VISUALIZATION_VOCABULARY`
  (refused with `refused_value_outside_closed_vocabulary`)
- attempt to display a node with a `source_category` other than
  `canonical_mirror` or `visualization_advisory` (refused with
  `refused_source_category_outside_closed_vocabulary`)
- attempt to display an edge with a `gate_category` outside the
  closed shipped gate vocabulary (refused with
  `refused_gate_category_outside_closed_vocabulary`)
- attempt to display a status icon with an id outside the closed
  five-category set (refused with
  `refused_status_category_outside_closed_vocabulary`)
- attempt to write ANY canonical artifact from the visualization
  panel, including `loop-state.json`, `orchestrator.log`, any
  planning artifact, `codex-review.md`, `fix-prompt.md`,
  `claude-prompt.md`, or `claude-summary.md` (refused with
  `refused_canonical_write_from_visualization`; the
  visualization surface is READ-ONLY)
- attempt to auto-advance phase, sub-phase, task, verdict, or
  approval-mode from the visualization panel (refused with
  `refused_auto_progression_from_visualization`)
- attempt to auto-fill an operator identity from OS state,
  environment variables, browser session, or any packaging-time
  identity source (the shipped no-auto-fill boundary is
  preserved verbatim; refused with
  `refused_auto_fill_operator_identity`)
- attempt to persist derived visualization state to disk under
  any name (the derived state is per-poll-tick; refused with
  `refused_advisory_persistence`)
- attempt to bypass the shipped Phase 10L / 10M polling cadence
  with a background thread or timer (refused with
  `refused_background_watcher_beyond_cadence`)

Every refusal MUST include the value / node id / edge id / status
id it refused (from the closed vocabulary), the shipped rule that
was violated (with a docs anchor citation matching the Phase 10AE
auditability convention), and the closed refusal category the
future runtime MUST expose.

## Approval Gates

The desktop orchestration visualization surface MUST preserve
every shipped approval gate verbatim. Specifically it MUST NOT:

- short-circuit the Phase 5A / 5C / 5D approval-mode gating for
  any downstream action derived from the visualization
- short-circuit the Phase 4C activator + `APPROVED_FOR_ACTIVATION`
  human approval for any downstream phase-advance derived from
  the visualization
- short-circuit the Phase 9G human acceptance gate for any
  downstream `record-final-acceptance` derived from the
  visualization
- short-circuit the Phase 10U MCP action guardrail per-tool
  approval policy for any downstream MCP mutation derived from
  the visualization
- short-circuit the Phase 5F post-review prompt bootstrap for
  any downstream Claude-prompt handoff derived from the
  visualization

The visualization surface is a REPORTING SURFACE ONLY. It
NEVER triggers a downstream action; every downstream action
routes through the shipped surface that already owns it
(`resume` for strict-mode gates, `record-final-acceptance` for
Phase 9G, the shipped Phase 10AG Codex conversation panel for
Codex requests, the shipped Phase 4C activator for phase
advance, etc.).

## Audit Expectations

Every visualization poll tick MUST audit through the shipped
surfaces:

- `.agent-loop/orchestrator.log` receives a bounded audit line
  per the shipped Phase 3A orchestrator contract naming the
  visualization signal version, the epoch-second timestamp, and
  the closed refusal category if the poll tick refused any
  displayed value. The audit line format follows the shipped
  Phase 10AG `_desktop_codex_conversation_format_audit_line`
  convention.
- the shipped canonical artifacts (`loop-state.json`,
  `current-phase.md`, `current-task.md`, `phase-plan.md`,
  `codex-review.md`, `claude-summary.md`, `claude-prompt.md`,
  `fix-prompt.md`, the shipped Phase 2A / 2B evidence artifacts)
  receive NO new audit obligation from this contract; the
  visualization surface is READ-ONLY.

The visualization panel MUST NOT introduce a separate audit
surface (a "visualization history" file, a per-session poll log,
a UI-only event stream). The shipped `.agent-loop/orchestrator.
log` is the sole audit source of truth.

## Source-Of-Truth Preservation (No Hidden UI Store)

The Phase 10AH contract preserves the shipped source-of-truth
model verbatim. Specifically the future Phase 10AI runtime MUST
NOT introduce ANY of the following:

- a UI-only "orchestration graph" JSON file, SQLite database,
  MessagePack blob, or any other persistent store
- a session state file that shadows `.agent-loop/loop-state.json`
  for the visualization panel's own state
- a "progress cache" file that mirrors the derived visualization
  state to disk
- a "pending transitions" queue file that buffers advisory
  transitions before they land in a canonical artifact
- a browser-session identity token cache, an MCP-side session
  cookie, or any cross-session identity persistence
- a "recents" list of previous poll ticks / node values (the
  operator uses `git log`, `.agent-loop/phase-plan.md`, and the
  shipped `.agent-loop/orchestrator.log` tail to review history)
- an autofill / suggestion engine that derives operator identity
  from OS state (`$USER`, `whoami`, browser session, packaging-
  time identity)
- a background watcher / polling thread beyond the shipped
  Phase 10L / 10M polling cadence rules
- a graph-layout cache, a positional cache, an animation state
  store, or any other UI-only cross-tick persistence

The visualization panel's per-session in-memory state (the
current node values, the current edge activations, the current
status icons) is RE-DERIVED on every poll tick from the fresh
canonical mirror + advisory derivation. On next session the
operator sees a fresh derivation from the current on-disk state
and MUST NOT see any stale cached value.

## Ownership Boundary Preservation

The Phase 10AH surface preserves every shipped ownership
boundary verbatim. Specifically:

- Codex remains the SOLE writer of planning artifacts
  (`ROADMAP.md`, `TASK.md`, `.agent-loop/phase-plan.md`,
  `.agent-loop/current-phase.md`,
  `.agent-loop/current-task.md`), `codex-review.md`,
  `fix-prompt.md`, and `claude-prompt.md` per the shipped
  Phase 3A / 4A / 10AB contracts. The visualization panel NEVER
  writes these directly and NEVER derives a value that would
  contradict these.
- Claude remains the SOLE writer of `claude-summary.md` and the
  shipped Claude-owned implementation surface (source, tests,
  non-planning docs). The visualization panel NEVER writes these
  directly.
- The orchestrator remains the SOLE writer of `loop-state.json`,
  `orchestrator.log`, and the shipped Phase 2A / 2B evidence
  artifacts. The visualization panel NEVER writes these
  directly.
- Human-owned decisions (final acceptance,
  `APPROVED_FOR_ACTIVATION` token,
  `APPROVED_FOR_HUMAN_REVIEW` verdict) remain human-authored.
  The visualization panel NEVER auto-generates any of them and
  NEVER derives a status icon that pre-empts the human decision.

## Dependencies On Phase 10AI (Runtime Implementation)

Phase 10AI will implement the runtime that satisfies this
contract. The Phase 10AI runtime is expected to add:

- a closed visualization-vocabulary constant matching the
  fifteen values named above (the ten canonical-mirror keys
  `phase`, `sub_phase`, `task`, `loop_state_status`,
  `approval_mode`, `cycle_count`, `max_cycles`,
  `awaiting_human_for`, `last_verdict`, `last_verdict_phase`,
  plus the five advisory-derived keys `review_branch_active`,
  `fix_branch_active`, `human_gate_pending`,
  `blocked_or_halted`, `artifact_backed_progress`)
- a closed node / edge / status-category constant matching the
  model named above
- a pure visualization-view builder (Tk-free, unit-testable)
  that reads the shipped canonical mirrors + advisory
  derivations and returns a bounded view dict shaped exactly to
  the closed vocabulary
- a pure per-node refusal classifier (Tk-free) that refuses
  fail-closed on any of the enumerated refusal categories
- a Tk panel that renders the closed vocabulary as a graph /
  icon-based flow, following the Phase 10L polling / attribution-
  tag conventions and the Phase 10AF `[canonical mirror]` /
  `[visualization-advisory]` attribution tag conventions
- a bounded audit-line formatter reusing the shipped Phase
  10AG `_desktop_codex_conversation_format_audit_line`
  convention

Phase 10AI will NOT add: a graph-side canonical write path, an
autonomous orchestration driver, a UI-only state store, a
network transport, an MCP-side "graph" endpoint, or a graph-
layout cache. This is a hard boundary; a Phase 10AI PR that
includes any of those is `NEEDS_FIXES`.

## Out Of Scope For Phase 10AH

The Phase 10AH slice is contract-definition only. The following
are explicitly out of scope:

- any Tk panel implementation, widget layout, graph-rendering
  library dependency, icon-set selection, or
  `_launch_desktop_app_window(...)` addition
- any new library-callable control (the shipped Phase 10I
  three-control cap is preserved verbatim)
- any new canonical artifact (the shipped canonical set is
  preserved verbatim; no `visualization-state.json`,
  `graph-layout.json`, or similar file)
- any change to the shipped Phase 2A / 3A / 4A / 5A / 6M /
  10L / 10M / 10O / 10AB / 10AC / 10AD / 10AF / 10AG contracts
- any Git automation
- any framework-side integration (crewai / langgraph /
  langchain remain evaluation-only per the shipped Phase 10AE
  contract)
- any change to the shipped `EXTERNAL_TARGET_APPROVAL_MODES`
  closed enum, the shipped
  `PRIMARY_DESKTOP_BOOTSTRAP_FIELD_NAMES` closed enum, the
  shipped Phase 10AB `_DESKTOP_CONCURRENCY_OWNERSHIP_MAP`
  closed map, or the shipped Phase 10AG
  `DESKTOP_CODEX_CONVERSATION_INTENT_IDS` /
  `DESKTOP_CODEX_CONVERSATION_REFUSAL_CATEGORIES` closed
  vocabulary
