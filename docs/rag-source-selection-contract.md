# RAG Source Selection Contract And Desktop UX

## Phase
Phase 10V (`RAG Source Selection Contract And Desktop UX`).

## Purpose

Pin the contract under which repo-local docs, PRDs, notes,
standards, and other knowledge sources MAY be surfaced to the
operator from the desktop app as RAG sources. The contract
applies to:

- which repo-local paths are eligible to surface
- how provenance is exposed per source
- how freshness is derived from on-disk file metadata
- how the retrieved excerpt is labeled relative to canonical
  artifact content
- which operator-side approval requirements gate selection
- which closed enablement states a selection-UX surface MAY
  expose
- how the desktop UX MUST refuse fail-closed when operator
  inputs are unmet

This document is the source of truth for the bounded
`build_desktop_rag_source_selection_view(...)` library function
and the matching `view-desktop-rag-source-selection` CLI
subcommand shipped in Phase 10V. The contract is closed: any
future runtime slice that ACTUALLY retrieves source content MUST
preserve every closed enumeration value, the advisory-vs-
canonical mirror rule, and the source-of-truth preservation rule.

## Scope

In scope:

- The closed set of source types eligible to surface in the
  desktop RAG source selection UX.
- The closed per-source descriptor shape used in the in-process
  Python registry.
- The closed provenance categories applied per source.
- The closed advisory-labeling rules that govern how retrieved
  content MUST be tagged.
- The closed freshness state machine derived from on-disk
  last-modified mtime.
- The closed approval requirements gating per-source selection.
- The closed three-state enablement state machine
  (`disabled_by_default` / `enabled_pending_runtime` /
  `refused_until_policy_update`).
- The refusal vocabulary surfaced when selection cannot proceed.
- The source-of-truth preservation rule (no persisted RAG-side
  state plane).

Out of scope (deferred to a future Phase 10 runtime slice):

- The actual retrieval transport (chunking, ranking, snippet
  extraction).
- The actual embeddings pipeline or vector index.
- Background watchers that re-index sources outside operator-
  initiated control.
- Any persisted retrieval cache, hit log, query history, or
  embeddings store on disk.
- Any new library-callable control beyond the existing Phase
  10I three (the cap stays at `view-external-status` /
  `view-external-controls` / `inspect-external-target`).

Forbidden everywhere:

- Reading source CONTENT in this slice. Only `Path.stat()`
  metadata (existence, mtime, size) is consulted.
- Spawning a subprocess to surface sources or stat them.
- Opening a network socket from the selection UX.
- Mutating any canonical artifact
  (`.agent-loop/loop-state.json`, `.agent-loop/orchestrator.log`,
  `.agent-loop/external-target.json`,
  `.agent-loop/runtime-config.json`, `TASK.md`,
  `proposed-phase.md`, `claude-prompt.md`, `claude-summary.md`,
  `codex-review.md`, `fix-prompt.md`, `current-task.md`,
  `current-phase.md`, `phase-plan.md`, `prd-intake.json`,
  `final-acceptance.json`, any Phase 2A evidence file, any
  Phase 6 memory entry).
- Appending to `.agent-loop/orchestrator.log` or advancing
  loop-state from the selection UX.
- Auto-filling operator identity from `$USER`, `whoami`, a
  packaging-time-configured identity, or any persistent RAG-side
  identity store.
- Introducing a RAG-side database, preference store, recents
  list, identity token, session token, or any other persisted
  control plane.
- Widening the Phase 10I three-control library-callable cap.

## Source Types (closed enum)

`RAG_SOURCE_TYPES` enumerates the bounded set of source types a
descriptor MAY claim:

- `repo_local_docs`
- `repo_local_prds`
- `repo_local_notes`
- `repo_local_standards`
- `repo_local_evidence`

A descriptor whose `source_type` is not in this set is refused
fail-closed by the descriptor validator. Future slices MAY
extend this enum only by explicitly editing the constant in
`scripts/agent_loop.py` AND the matching test in
`tests/test_desktop_rag_source_selection.py`.

## Provenance Categories (closed enum)

`RAG_PROVENANCE_CATEGORIES` enumerates the bounded set of
provenance categories applied per source:

- `checked_in_documentation` (e.g. `README.md`, `docs/`)
- `checked_in_planning_artifact` (e.g. `TASK.md`,
  `.agent-loop/phase-plan.md`)
- `checked_in_standard` (e.g. `AGENTS.md`, `CLAUDE.md`)
- `operator_supplied_notes` (e.g. local-only notes, review
  scratchpad)
- `transient_evidence` (e.g. `.agent-loop/git-diff.patch`, any
  Phase 2A evidence file)

A descriptor whose `provenance` is not in this set is refused
fail-closed.

## Advisory Labeling Rules (closed enum)

`RAG_ADVISORY_LABELING_RULES` enumerates the bounded set of
advisory-labeling rules a descriptor MAY claim:

- `advisory_only_no_canonical_substitution`: the retrieved
  excerpt is `[rag-advisory]` only and NEVER substitutes for
  the canonical artifact content read directly.
- `advisory_with_provenance_required`: same as above, plus the
  future runtime slice MUST surface the source's path AND
  last_modified UTC alongside any retrieved value so a reviewer
  can verify provenance.
- `refused_until_policy_update`: the source is refused fail-
  closed at the labeling-rule level: a future runtime slice
  MUST NOT surface its content as advisory until the rule is
  re-classified by an explicit policy-update slice. Sources
  whose `advisory_label_rule` is this value short-circuit the
  enablement-state computation to `refused_until_policy_update`
  regardless of operator input.

A descriptor whose `advisory_label_rule` is not in this set is
refused fail-closed.

## Freshness State Machine (closed enum)

`RAG_FRESHNESS_STATES` enumerates the bounded set of freshness
states a source MAY surface:

- `fresh`: source exists; on-disk last-modified mtime is within
  `RAG_SOURCE_FRESHNESS_STALE_THRESHOLD_SECONDS` of the
  per-poll `time.time()`.
- `stale`: source exists; on-disk last-modified mtime is older
  than the threshold.
- `missing`: source does not exist at the controller-root-
  resolved canonical path.
- `unknown`: source exists but `Path.stat()` failed with an
  `OSError`, OR the computed `now_ts - mtime_ts` is negative
  (clock skew / future mtime).

`RAG_SOURCE_FRESHNESS_STALE_THRESHOLD_SECONDS` is currently set
to 30 days (`30 * 24 * 3600`). A future runtime slice MAY refine
the threshold per source type without widening the closed enum.

Freshness is derived per-poll: each call to
`build_desktop_rag_source_selection_view(...)` recomputes the
freshness probe via `Path.stat()`; the view NEVER caches
freshness across polls.

## Approval Requirements (closed enum)

`RAG_SOURCE_APPROVAL_REQUIREMENTS` enumerates the bounded set
of approval requirements gating per-source selection:

- `operator_acknowledged_advisory_labeling`: the operator has
  explicitly acknowledged the per-source advisory-labeling rule
  this session. Acknowledgement MUST be a per-session operator
  action and MUST NOT be pre-acknowledged from any prior
  session or saved preference.
- `operator_supplied_identity`: the operator has supplied an
  explicit identity value this session. Per the Phase 10S
  contract identity MUST NOT be auto-filled from `$USER`,
  `whoami`, a packaging-time-configured identity, or any
  persistent RAG-side identity store.
- `approval_mode_supports_selection`: the controller's
  `loop-state.json.approval_mode` is in
  `RAG_SOURCE_PERMITTED_APPROVAL_MODES = {review, autonomous}`.
  Strict mode (Phase 5C strict-mode pause semantics) refuses
  selection fail-closed.
- `phase_10v_runtime_available`: the Phase 10V retrieval
  runtime is shipped and reachable. Hard-coded `False` in this
  slice; a future runtime slice MUST flip this flag to
  actually enable retrieval.
- `source_path_present_in_repo`: the source's canonical path
  exists on disk at the controller-root-resolved location.
  Derived per-poll from the freshness probe.

A descriptor whose `approval_requirements` contains an entry
not in this enum is refused fail-closed.

## Permitted Approval Modes (closed set)

`RAG_SOURCE_PERMITTED_APPROVAL_MODES = {review, autonomous}`.
Strict mode refuses selection fail-closed. This mirrors the
Phase 10T / 10U permitted-mode set so the selection boundary
stays consistent with the other MCP / RAG surfaces.

## Enablement State Machine (closed enum)

`RAG_SOURCE_ENABLEMENT_STATES` enumerates the bounded set of
enablement states a source MAY surface:

- `disabled_by_default`: every runtime-side requirement is
  satisfied but at least one operator-side requirement is not.
  The operator can clear this state by supplying the missing
  operator-side inputs (acknowledgement, identity, etc.).
- `enabled_pending_runtime`: every approval requirement is
  satisfied; the source is contract-eligible for retrieval but
  the actual transport ships in a future runtime slice. The
  selection-UX surface MAY render this as a copy-paste action
  (matching the Phase 10N action-bridge model).
- `refused_until_policy_update`: at least one runtime-side
  requirement is not satisfied (`phase_10v_runtime_available`,
  `source_path_present_in_repo`) OR the source's
  `advisory_label_rule == "refused_until_policy_update"`. This
  state cannot be cleared by operator input alone; a future
  policy-update slice or runtime slice MUST flip the relevant
  boundary.

This is the default state for every source in this slice
because `phase_10v_runtime_available` is hard-coded `False`.

## Per-Source Descriptor Shape

Every entry in `_DESKTOP_RAG_SOURCE_SELECTION_REGISTRY` MUST
carry every field below. The validator refuses fail-closed via
HaltError on any missing required field, wrong-typed value, or
unknown closed-enumeration member.

Required string fields:

- `id`: unique source identifier.
- `display_name`: operator-visible source name.
- `source_type`: closed enum member from `RAG_SOURCE_TYPES`.
- `provenance`: closed enum member from
  `RAG_PROVENANCE_CATEGORIES`.
- `advisory_label_rule`: closed enum member from
  `RAG_ADVISORY_LABELING_RULES`.
- `path_canonical_rel`: the source's path relative to the
  controller root. MUST be a POSIX-style relative path.
- `description`: operator-visible description.
- `deferred_runtime_marker`: operator-visible note describing
  that actual retrieval is deferred to a future runtime slice.
- `refusal_reason_template`: operator-visible refusal reason
  used when selection cannot proceed.

Required list fields:

- `approval_requirements`: ordered tuple of
  `RAG_SOURCE_APPROVAL_REQUIREMENTS` members.
- `selection_steps`: ordered tuple of
  `{type: "cli" | "manual_edit", content: str}` step
  descriptors. Reuses the shipped
  `DESKTOP_RUN_PROFILE_STEP_TYPES = ("cli", "manual_edit")`
  enumeration verbatim.

## View Builder

`build_desktop_rag_source_selection_view(controller_root, *,
operator_inputs=None)` returns a per-call structured view dict:

- `view_signal_version`: literal `"phase-10v-v1"`.
- `controller_path_canonical`: resolved controller root.
- `current_loop_state_status`: controller's loop-state.status
  (or None when missing / malformed).
- `controller_loop_state_approval_mode`: controller's
  loop-state.approval_mode.
- `phase_10v_runtime_available`: literal `False`.
- `freshness_stale_threshold_seconds`: literal
  `RAG_SOURCE_FRESHNESS_STALE_THRESHOLD_SECONDS`.
- `operator_inputs`: per-poll mirror of normalized operator
  inputs.
- `source_types`, `provenance_categories`,
  `advisory_labeling_rules`, `freshness_states`,
  `enablement_states`, `approval_requirements`: closed
  enumeration mirrors.
- `sources`: list of per-source descriptors (one per registry
  entry) carrying `id`, `display_name`, `source_type`,
  `provenance`, `advisory_label_rule`, `path_canonical_rel`,
  `path_canonical` (controller-root-resolved POSIX path),
  `source_path_present_in_repo`, `last_modified_utc`,
  `size_bytes`, `freshness_state`, `description`,
  `approval_requirements`, `approval_state`,
  `enablement_state`, `enablement_reason`, `selection_steps`,
  `command`, `clipboard_payload`, `deferred_runtime_marker`,
  `refusal_reason_template`, `dispatch_mode='copy_paste'`,
  `category='rag_source_selection_ux'`.
- `precedence_note`: literal
  `DESKTOP_RAG_SOURCE_SELECTION_PRECEDENCE_NOTE`.

The view builder NEVER writes, NEVER mutates any canonical
artifact, NEVER spawns a subprocess, NEVER opens a network
socket, NEVER reads source CONTENT (only `Path.stat()` is
consulted), NEVER invokes `_halt(...)`, NEVER widens the Phase
10I library-callable cap, NEVER persists a retrieval cache.

A HaltError raised by the shipped `load_loop_state(...)`
validator soft-fails the view (the view stays operable; the
`current_loop_state_status` and
`controller_loop_state_approval_mode` fields surface as `None`)
per the Phase 10L "MUST NOT propagate validator HaltErrors as
canonical halt persistence" rule.

## Source-Of-Truth Preservation

- Per-session operator inputs (identity, acknowledged source
  ids) are held in-memory only. Closing the desktop window OR
  the CLI process MUST discard every value.
- The selection-UX surface MUST NOT persist a per-operator
  preference store, recents list, query history, or
  acknowledgement log to disk.
- The selection-UX surface MUST NOT auto-fill operator identity
  from `$USER`, `whoami`, a packaging-time-configured identity,
  an MCP server session, a browser session, or any persistent
  RAG-side identity store.
- The Phase 10I three-control library-callable cap MUST be
  preserved exactly: ZERO new library-callable controls are
  introduced.
- The Phase 10S `deferred_mutating_class` MCP boundary and the
  Phase 10T `refused_deferred_runtime` short-circuit are not
  affected by this slice.

## Refusal Behavior

When `--controller-root` is omitted the CLI handler returns
exit 2 with `[desktop-rag-source-selection] REFUSED:
--controller-root is required ...` on stderr. When the
controller root is missing required markers (AGENTS.md /
CLAUDE.md / TASK.md / .agent-loop/) the handler returns exit 2
with `[desktop-rag-source-selection] REFUSED: controller root
... is missing required markers ...` on stderr.

Once the controller-root selection succeeds the handler
follows the Phase 7C reporter pattern: always exits 0 on report
content. The rendered view surfaces per-requirement refusal
reasons inline with `[refused]` attribution tags so a reviewer
can see exactly which requirements remain unmet without parsing
JSON.

## Out-Of-Scope Reaffirmation

This slice does NOT introduce:

- any actual retrieval transport, chunking pipeline, ranking,
  snippet extraction, embeddings pipeline, vector index, or
  background watcher
- any persisted retrieval cache, hit log, query history, or
  embeddings store on disk
- any new library-callable control beyond the Phase 10I three
- any subprocess spawn, network socket open, content read, or
  canonical artifact write
- any GitHub integration, packaging / code-signing / auto-
  update pipeline, system-tray surface, or controlled-
  concurrency runtime
- any rewrite of the Phase 2A / 3A / 4A contracts, the Phase
  10G UI contract, the Phase 10H status surface, the Phase 10I
  controls layer, the Phase 10J dashboard contract, the Phase
  10K dashboard runtime, the Phase 10L desktop-app contract,
  the Phase 10M desktop runtime, the Phase 10N desktop action
  bridge, the Phase 10O MCP integration contract, the Phase
  10P desktop setup runtime, the Phase 10Q run-profiles
  runtime, the Phase 10R project-start runtime, the Phase 10S
  MCP server selection UX contract, the Phase 10T MCP read-
  only assistance surface, or the Phase 10U MCP action
  guardrails surface
- any Git automation
