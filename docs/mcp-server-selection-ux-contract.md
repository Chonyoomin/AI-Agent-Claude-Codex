# MCP Server Selection UX Contract

## Status

Phase 10S defines this contract. No MCP server runtime, MCP tool
execution path, MCP descriptor registry, MCP server selection
runtime, MCP-driven canonical-artifact write, networked tool
orchestrator, or third-party MCP integration ships in this slice.
The contract below specifies the FIRST MCP server selection UX
boundary for the desktop app: which fields a desktop server-entry
row MUST surface, which permission classes the desktop surface MUST
distinguish, which read-only-vs-deferred-mutating capability labels
the desktop surface MUST attach to each server entry, which
per-server safety copy the desktop surface MUST render before any
enablement affordance, which operator approval requirements MUST be
satisfied before MCP enablement becomes user-facing, and how the
selection UX MUST stay strictly advisory (no MCP runtime fetch, no
networked call, no canonical artifact write) until a later Phase 10
runtime slice lands. Implementation of MCP runtime support is
deferred to later Phase 10 sub-phases:

- Phase 10T: MCP Read-Only Assistance In Desktop App (the first
  MCP server consumer that fetches read-only advisory context from
  a configured MCP server, surfaces it as advisory derived state
  alongside canonical mirrors, and never mutates any canonical
  artifact); satisfies the selection UX's `read_only_advisory_class`
  / `browser_inspection_class` enablement paths
- Phase 10U and later: bounded mutation-capable MCP actions plus
  the additional safety gates required before any non-read-only
  MCP-assisted runtime behavior is allowed; satisfies the selection
  UX's deferred `deferred_mutating_class` enablement path; tracked
  in `ROADMAP.md`

## Scope

This document is the contract every future MCP server selection
surface MUST satisfy when it is implemented. It is NOT a
description of currently shipped runtime behavior. The shipped
repository today exposes ZERO MCP integration paths and ZERO MCP
server selection surfaces: the desktop app does NOT enumerate any
MCP server, the desktop app does NOT render any MCP capability
label, the desktop app does NOT render any MCP enablement
affordance, and no shipped CLI subcommand selects, enables,
disables, persists, or otherwise mutates an MCP server list.
Adding the MCP server selection UX itself is the work of a later
Phase 10 sub-phase tracked in `ROADMAP.md`; this slice is the
prerequisite documentation contract that pins the rendering rules,
permission classes, safety copy, and approval gates that later
runtime MUST satisfy.

The MCP server selection UX contract is the load-bearing
specification for "which fields a server entry row MUST carry",
"which permission classes the UX MUST distinguish", "which
capability labels MUST be attached to each entry", "which per-server
safety copy MUST be rendered alongside each entry", "which approval
requirements MUST be satisfied before an enablement affordance is
surfaced", "how the selection UX MUST stay strictly advisory until a
runtime slice lands", "how the selection UX MUST refuse fail-closed
on malformed descriptors or unknown permission classes", and "how
the selection UX MUST preserve every shipped evidence-review /
approval-gate / ownership-boundary invariant". The contract pins
the closed permission-class enumeration, the per-server-entry
descriptor shape, the read-only-vs-deferred-mutating label rules,
the per-server safety copy rules, the approval-gate enumeration,
the refusal vocabulary, the source-of-truth preservation rules, and
the deferred-runtime boundary every future MCP server selection
surface MUST preserve so later Phase 10T+ runtime slices can wire
the actual MCP runtime against this contract without further design
decisions and without collapsing the shipped CLI-first,
evidence-review-driven workflow into a parallel MCP control plane.

## Relationship To Phase 10O MCP Integration Contract

This contract is a UX-side companion to the Phase 10O
`docs/mcp-integration-contract.md` runtime / safety contract. The
Phase 10O contract pins WHAT a future MCP runtime MAY do (which
tool categories it MAY consume, which boundaries every MCP tool
MUST satisfy, which refusal cases the runtime MUST honor). The
Phase 10S contract pins HOW the desktop app MUST PRESENT the set
of available MCP servers to the operator BEFORE any enablement
affordance is surfaced. The two contracts MUST be read together;
the Phase 10S permission-class enumeration is layered on top of the
Phase 10O tool-category enumeration, and every safety boundary the
Phase 10O contract pins continues to apply to any selection UX the
Phase 10S contract gates.

Specifically:

- The Phase 10O contract's three tool categories
  (`read_only_advisory`, `browser_app_inspection`,
  `deferred_mutating`) define what an individual MCP tool MAY do.
  The Phase 10S contract's three permission classes
  (`read_only_advisory_class`, `browser_inspection_class`,
  `deferred_mutating_class`) define what an MCP SERVER (which may
  expose multiple tools) MAY do as a whole; an MCP server's
  permission class is the maximum-privilege category any of its
  declared tools belongs to. A server that declares ANY
  `deferred_mutating` tool is itself in the
  `deferred_mutating_class` for selection-UX purposes, and the
  desktop surface MUST refuse to surface an enablement affordance
  for that server until a later Phase 10U+ runtime slice lands.
- The Phase 10O contract's per-tool descriptor schema
  (`id` / `category` / `dispatch_mode` /
  `delegated_phase_10i_control_id` / `mutation_eligible` /
  `audit_note` / `refusal_reason_template`) MUST be readable by the
  Phase 10S server-entry rendering pipeline so the desktop surface
  can derive a server's permission class from its declared tools.
- The Phase 10O contract's refusal vocabulary
  (descriptor-missing / descriptor-malformed / unknown-category /
  deferred-mutating-refused / response-size-cap-exceeded /
  policy-rule-refused / transport-failed) MUST appear in the
  Phase 10S selection UX as advisory derived state alongside the
  server entry, so an operator inspecting the selection list can
  see why a given server cannot currently be enabled.
- The Phase 10O contract's approval gates (Phase 4C activation
  token, Phase 9G acceptance, Phase 10B / 10C / 9G operator-identity
  placeholders) all apply verbatim to any selection-UX-surfaced
  enablement affordance; the selection UX MUST NOT introduce a
  fourth approval gate or shortcut any of the existing ones.

## Distinction From Shipped Artifacts And Surfaces

The MCP server selection UX is NOT one of the existing shipped
surfaces. The shipped Phase 1 - 9 system, the Phase 10A - 10F
external-workspace slices, the Phase 10G - 10I external UI
surfaces, the Phase 10J - 10K artifact dashboard contract and
runtime, the Phase 10L - 10N desktop-app contract / runtime /
action-bridge slices, the Phase 10O MCP integration contract, the
Phase 10P desktop setup runtime, the Phase 10Q desktop run-profiles
runtime, and the Phase 10R desktop project-start runtime already
define these distinct surface roles which the MCP server selection
UX contract MUST NOT overlap or replace:

- The shipped `python scripts/agent_loop.py ...` CLI is the
  canonical operator entry point for every mutating workflow. The
  MCP server selection UX MUST NOT replace, wrap, shadow, or
  auto-trigger these CLI surfaces; the selection UX MAY surface
  per-server advisory metadata that helps an operator decide which
  MCP server they would like enabled, but MUST NOT enable the
  server itself (enablement is the work of a later Phase 10T+
  runtime slice).
- The shipped Phase 2A Evidence Collection Contract pins which
  evidence files an orchestrator-driven cycle produces. The
  selection UX MUST NOT write any of those evidence files; the
  selection UX MUST NOT cite an MCP-server descriptor as a
  substitute for canonical evidence.
- The shipped Phase 3A Orchestrator Contract pins the canonical
  loop-state schema and the orchestrator's write-ownership rules.
  The selection UX MUST NOT write `.agent-loop/loop-state.json`,
  `.agent-loop/orchestrator.log`, or any other orchestrator-owned
  artifact.
- The shipped Phase 4A Planning Contract pins the planner's
  proposal authorship boundary and the activation gate. The
  selection UX MUST NOT author `.agent-loop/proposed-phase.md`,
  MUST NOT add or forge the `APPROVED_FOR_ACTIVATION` token, and
  MUST NOT trigger the Phase 4C activator on the operator's behalf
  in response to any selection event.
- The shipped Phase 5A Approval Modes Contract pins the
  review / strict / autonomous approval-mode boundaries. The
  selection UX MUST NOT change the approval mode of an in-flight
  cycle as a side effect of any selection event, MUST NOT
  short-circuit a strict-mode pause, and MUST NOT widen the
  autonomous-mode boundary into MCP-assisted enablement.
- The shipped Phase 9G Final Human Acceptance Gate pins the
  `record-final-acceptance` CLI as the only path that records
  human acceptance. The selection UX MUST NOT record acceptance,
  MUST NOT auto-fill `--accepted-by`, and MUST NOT widen the gate.
- The shipped Phase 10A - 10F external-workspace contracts pin
  controller-vs-target ownership, attach record schema, bootstrap
  rules, and the freshness check. The selection UX MUST NOT
  forge attach records, MUST NOT cross the controller / target
  boundary, and MUST NOT bypass the freshness check.
- The shipped Phase 10G UI contract pins the load-bearing UI
  boundaries (canonical artifact read set,
  advisory-vs-canonical mirror rule, CLI-only operations,
  no-auto-fill operator identity, refusal behavior,
  source-of-truth preservation, safety boundaries, approval
  gates, audit expectations). Every read-set / advisory-mirror /
  CLI-only / no-auto-fill / refusal / source-of-truth / safety /
  approval / audit rule in `docs/external-ui-contract.md` MUST
  continue to apply to any MCP server selection surface verbatim.
- The shipped Phase 10I `_EXTERNAL_UI_CONTROL_REGISTRY` caps the
  library-callable control surface at exactly three controls
  (`view-external-status`, `view-external-controls`,
  `inspect-external-target`). The MCP server selection UX MUST
  NOT introduce a fourth library-callable control nor a fourth
  MCP-callable shipped surface.
- The shipped Phase 10J - 10K artifact dashboard contract and
  runtime pin six dashboard surfaces and the canonical-mirror
  read set. The selection UX MAY appear inside the dashboard ONLY
  as advisory derived state tagged `[advisory]`, never as a
  canonical mirror.
- The shipped Phase 10L Desktop App Shell Contract pins the
  desktop process boundary, controller-root selection,
  refresh / polling cadence, artifact-opening behavior, and the
  library-call / CLI-spawn bridge. The selection UX MUST NOT
  bypass any of these boundaries; the selection rendering MUST
  go through the same shipped view-library pattern the Phase 10M
  runtime uses.
- The shipped Phase 10M - 10N desktop runtime and action-bridge
  surfaces pin the read-only and copy-paste-only operator
  affordance model. The selection UX MUST surface per-server
  metadata as advisory derived state ONLY; any future enablement
  affordance MUST follow the Phase 10N copy-paste-only model and
  MUST NOT silently dispatch a mutating CLI subcommand.
- The shipped Phase 10P desktop setup runtime pins the operator
  setup surface (controller-root selection, target attach
  inspection, adapter env reporting, runtime config mirror,
  wrapper templates, local tools). The selection UX MUST NOT
  collapse into the setup surface; the two surfaces are distinct
  and the selection UX MUST be rendered as its own section.
- The shipped Phase 10Q desktop run-profiles runtime pins the
  approval-mode / autonomy / run-policy surface. The selection
  UX MUST NOT change the active approval mode as a side effect
  of any selection event.
- The shipped Phase 10R desktop project-start runtime pins the
  attach / detach / intake-PRD / bootstrap-prompt / first-phase
  workflow. The selection UX MUST NOT auto-attach a target, MUST
  NOT auto-intake a PRD, MUST NOT auto-bootstrap a prompt, and
  MUST NOT auto-activate a phase in response to any selection
  event.

## Server Entry Descriptor Shape

Every MCP server entry the selection UX surfaces MUST be backed by
a per-server descriptor carrying at minimum the following fields.
The descriptor MUST be read-only from the selection UX's
perspective; the selection UX MUST NOT mutate, append to, or
otherwise persist a modified descriptor to disk.

- `id`: the MCP server's canonical id, stable across cycles
- `display_name`: a short human-readable label rendered in the
  selection list
- `source_url`: the MCP server's source URL (documentation site,
  source repository, or vendor page) so the operator can inspect
  the server before considering enablement; the selection UX MUST
  render the URL as inert text (no auto-fetch, no auto-open) and
  the operator MUST decide whether to open it
- `permission_class`: exactly one of
  `read_only_advisory_class`, `browser_inspection_class`,
  `deferred_mutating_class` (see "Permission Classes" below)
- `capability_categories`: a closed non-empty list of
  Phase 10O tool categories the server declares
  (`read_only_advisory`, `browser_app_inspection`,
  `deferred_mutating`); the selection UX MUST surface this list as
  per-server capability labels so the operator can see exactly
  which categories the server's tools fall into
- `safety_copy`: a per-server safety-copy block (see "Per-Server
  Safety Copy" below) the desktop surface MUST render alongside
  the server entry before any enablement affordance is offered
- `approval_requirements`: a closed list of approval-gate ids the
  operator MUST satisfy before any enablement affordance for the
  server is rendered as eligible (see "Approval Requirements"
  below)
- `enablement_state`: exactly one of
  `disabled_by_default`, `enabled_pending_runtime`,
  `refused_deferred_runtime` (see "Enablement State Machine"
  below); the selection UX MUST default every server to
  `disabled_by_default` until a future runtime slice lands
- `deferred_runtime_marker`: a literal string the desktop surface
  MUST render alongside any server whose `permission_class` is
  `deferred_mutating_class`, pointing the operator at the
  Phase 10U+ slice that will eventually allow enablement; the
  marker MUST NOT be omitted on a deferred-mutating server entry
- `refusal_reason_template`: text the selection UX uses when
  refusing the entry fail-closed (matching the Phase 10O contract's
  `refusal_reason_template` field on a per-tool descriptor)

The selection UX MUST refuse fail-closed on any server descriptor
that is missing one of the required fields, carries a wrong-typed
value, carries an unknown `permission_class`, or carries an
unknown `capability_categories` member. The refusal MUST point the
operator at this contract paragraph that pins the descriptor shape
(see "Refusal Behavior" below).

## Permission Classes

The selection UX MUST classify every MCP server into exactly one
of the following three closed permission classes before allowing
the entry to be surfaced as eligible for enablement. The class is
the maximum-privilege Phase 10O tool category any of the server's
declared tools belongs to; a server's class is the upper bound on
what the server may do as a whole, not a description of any single
tool.

### 1. `read_only_advisory_class`

Servers whose declared tools all fall in Phase 10O category 1
(read-only advisory context: documentation lookups, library
reference, schema descriptions, code-search snippets, etc.). The
selection UX MUST render the server with a `[read-only-advisory]`
label and a per-server safety-copy block stating that the server
fetches read-only context, never writes any canonical artifact,
and that the operator can choose to enable it via the future
Phase 10T runtime slice. The server's `enablement_state` default
in the selection UX is `disabled_by_default`.

### 2. `browser_inspection_class`

Servers whose declared tools include Phase 10O category 2
(browser / app inspection, read-only) and no category 3 tools. The
selection UX MUST render the server with a `[browser-inspection]`
label, a per-server safety-copy block stating that inspection
captures are per-explicit-operator-action and per-session, that
the server captures NO replayable credentials (no cookies / browser
session tokens / OS credentials / environment variables), that the
server NEVER injects events back into the inspected target, and
that the server NEVER persists captures across sessions. The
server's `enablement_state` default in the selection UX is
`disabled_by_default`.

### 3. `deferred_mutating_class`

Servers whose declared tools include ANY Phase 10O category 3 tool
(deferred mutation-capable: file writes, shell execution, network
mutation, package install, system service registration, cloud /
CI / deployment integration, etc.). The selection UX MUST render
the server with a `[deferred-mutating]` label, a `[refused]` tag
on every enablement affordance, the per-server
`deferred_runtime_marker` pointing the operator at the Phase 10U+
slice that will eventually allow enablement, and a per-server
safety-copy block stating that the desktop surface MUST NOT
surface a working enablement affordance for the server in the
Phase 10T initial slice. The server's `enablement_state` default
in the selection UX is `refused_deferred_runtime`. The selection
UX MUST NOT promote a `deferred_mutating_class` server to either
of the other two classes based on a heuristic about whether the
server "actually" mutates; the permission class is the descriptor
author's declared property and the selection UX trusts the
declaration.

## Capability Category Labels

Independent of the server's permission class, the selection UX
MUST render the per-tool Phase 10O category labels for every tool
the server declares so the operator can see exactly which
categories the server's tools fall into:

- `[capability: read-only-advisory]` per Phase 10O category 1
- `[capability: browser-app-inspection]` per Phase 10O category 2
- `[capability: deferred-mutating]` per Phase 10O category 3

The capability label list is ordered, deduplicated, and MUST be
visible alongside the server's permission class label so a reader
can verify the server's class against the union of its tool
categories. A server whose tool list includes a category 3 tool
MUST surface the `[capability: deferred-mutating]` label even when
the server's other tools are category 1 / category 2; the
permission class is the maximum-privilege category and the label
list is the full enumeration.

## Per-Server Safety Copy

The selection UX MUST render a per-server safety-copy block
alongside every server entry before any enablement affordance is
offered. The block is operator-facing copy designed to make the
boundary explicit; the block is NOT load-bearing operator-identity
text and the selection UX MUST NOT auto-derive its content from
any operator-fetched value. The required content per permission
class:

### Safety copy for `read_only_advisory_class`

- a one-line summary of what the server fetches
- an explicit statement that the server NEVER writes any canonical
  artifact (Phase 2A evidence, loop-state.json, orchestrator.log,
  external-target.json, claude-prompt.md, claude-summary.md,
  codex-review.md, fix-prompt.md, current-task.md,
  current-phase.md, phase-plan.md, proposed-phase.md,
  final-acceptance.json, any Phase 6 memory entry, any Phase 9
  descriptor)
- an explicit statement that all fetched values are surfaced as
  `[mcp-advisory]` derived state per the Phase 10O
  advisory-vs-canonical mirror rule
- an explicit pointer at the Phase 10T runtime slice that would
  eventually enable the server

### Safety copy for `browser_inspection_class`

- a one-line summary of what the server inspects
- an explicit statement that inspection is strictly READ-ONLY
  against the operator's existing browser / app state; the server
  MUST NOT inject events
- an explicit statement that inspection captures are
  per-explicit-operator-action and per-session
- an explicit statement that the server captures NO replayable
  credentials (no cookies / browser session tokens / OS-level
  credentials / environment variables / SSH keys / API keys /
  clipboard auto-refresh)
- an explicit statement that inspection captures are NEVER
  persisted across sessions
- an explicit pointer at the Phase 10T runtime slice that would
  eventually enable the server

### Safety copy for `deferred_mutating_class`

- a one-line summary of which mutating capabilities the server
  declares (file writes, shell execution, network mutation, etc.)
- an explicit statement that the desktop surface MUST NOT surface
  a working enablement affordance for the server in the Phase 10T
  initial slice
- an explicit pointer at the Phase 10U+ slice that will define the
  per-action approval gates, audit-log entry shape, refusal
  vocabulary, and rollback behavior required before enablement
- an explicit statement that no value the server returns MAY be
  treated as canonical operator identity, canonical evidence,
  canonical review verdict, or canonical artifact content

The selection UX MUST render the safety-copy block alongside the
server entry; the operator MUST be able to read the safety copy
before any enablement affordance is surfaced as eligible.

## Approval Requirements

The selection UX MUST gate every enablement affordance behind a
closed list of approval requirements. The list is descriptor-
declared per `approval_requirements`; the selection UX MUST refuse
to surface an enablement affordance as eligible until every listed
requirement is satisfied. The closed enumeration:

- `operator_acknowledged_safety_copy`: the operator has explicitly
  acknowledged the per-server safety-copy block. The selection UX
  MUST render the acknowledgement as a per-session operator action
  (matching the Phase 10N copy-paste-only model: an explicit
  operator click / explicit operator keypress); the selection UX
  MUST NOT pre-acknowledge based on a prior session, a saved
  preference, or any persistent operator-side state
- `operator_supplied_identity`: the operator has supplied an
  explicit identity value (matching the shipped Phase 10B
  `--attached-by` / Phase 10C `--bootstrapped-by` / Phase 9G
  `--accepted-by` placeholder model; never auto-filled from `$USER`
  / `whoami` / browser session / packaging-time identity / MCP
  server session). The selection UX MUST render the identity field
  as an empty operator-supplied field and MUST NOT pre-populate it
- `approval_mode_supports_enablement`: the in-flight cycle's
  loop-state.approval_mode is a value where enablement is
  contract-permitted. The selection UX MUST refuse fail-closed in
  `strict` mode (matching the shipped Phase 5C strict-mode pause
  semantics) and MUST NOT widen the autonomous-mode boundary into
  MCP-assisted enablement
- `phase_10t_runtime_available`: the Phase 10T MCP read-only
  assistance runtime is shipped and reachable. The selection UX
  MUST refuse fail-closed when this is False (i.e. every cycle
  before the Phase 10T runtime lands; this contract pins the
  refusal so the selection UX cannot accidentally render a working
  enablement affordance against a non-shipped runtime). For a
  `deferred_mutating_class` server the requirement is
  `phase_10u_runtime_available` instead, which is False until the
  Phase 10U+ runtime lands
- `policy_rule_permits_enablement`: the operator-supplied or
  Codex-owned policy rule (if any) does NOT refuse the enablement
  per the Phase 10O policy-rule additive boundary. The selection
  UX MUST surface both the policy rule's refusal message and the
  base contract's eligibility verdict so the operator sees whether
  the refusal came from the contract or from the policy

The selection UX MUST render the approval-requirement list
alongside every enablement affordance so the operator can see
which requirements remain unsatisfied. The selection UX MUST NOT
combine the requirements into a single boolean "ready" flag; each
requirement MUST be visible individually.

## Enablement State Machine

The selection UX MUST track every server's `enablement_state` as
exactly one of three closed values; the selection UX MUST NOT
introduce a fourth state.

- `disabled_by_default`: the server is visible in the selection
  list but NOT enabled. The selection UX MAY render an enablement
  affordance once every `approval_requirements` entry is
  satisfied. This is the default state for every
  `read_only_advisory_class` and `browser_inspection_class` server
  in the Phase 10S selection UX
- `enabled_pending_runtime`: the operator has satisfied every
  `approval_requirements` entry AND the selection UX has surfaced
  the enablement affordance, but the actual MCP runtime slice
  (Phase 10T for `read_only_advisory_class` /
  `browser_inspection_class`; Phase 10U+ for
  `deferred_mutating_class`) has not yet shipped. The selection UX
  MUST clearly mark this state so the operator understands that
  enablement is queued, not active
- `refused_deferred_runtime`: the server is in
  `deferred_mutating_class` (or the `phase_10t_runtime_available`
  / `phase_10u_runtime_available` requirement is unsatisfied) and
  the selection UX MUST NOT surface a working enablement
  affordance. The selection UX MUST render the `[refused]` tag
  alongside the server entry, render the per-server
  `deferred_runtime_marker`, and point the operator at the future
  Phase 10 slice that would allow enablement

The selection UX MUST NOT persist `enablement_state` to a hidden
per-operator preference store; the state is derived per-poll from
the descriptor + the approval-requirement state + the
runtime-availability checks. The selection UX MUST NOT introduce
an MCP-side database, key-value store, or session store to hold
selection state separately from on-disk artifacts (matching the
Phase 10O source-of-truth preservation rule).

## Selection-UX Rendering Rules

The desktop surface that renders the selection list MUST follow
these rules:

- the surface MUST render one row per server descriptor in a
  closed deterministic order (the descriptor's `id` ordering or
  the descriptor file's declaration ordering; the surface MUST NOT
  reorder rows based on a per-operator preference, an MCP-fetched
  value, or any persistent UI-side state)
- the surface MUST render the server's `display_name`, `id`,
  `source_url` (as inert text), `permission_class` label, full
  `capability_categories` label list, `enablement_state` tag,
  and full `safety_copy` block on every row
- the surface MUST render the row with a per-line tag matching the
  Phase 10G / 10J / 10L attribution vocabulary: `[advisory]` for
  every derived field, `[mcp-server]` for the server descriptor
  fields, `[refused]` for any unmet approval requirement or
  permission-class refusal, `[deferred-runtime]` for the
  per-server `deferred_runtime_marker`
- the surface MUST NOT render an enablement affordance for a row
  unless every `approval_requirements` entry is satisfied AND the
  server's `enablement_state` is not `refused_deferred_runtime`
- the surface MUST NOT auto-fetch the server's source URL, MUST
  NOT auto-open the URL in a browser, and MUST NOT pre-populate
  the operator-identity field
- the surface MUST refresh the rendered state per poll cycle
  (matching the Phase 10L per-poll-cycle cache invalidation rule);
  the surface MUST NOT serve stale `enablement_state` from an
  in-process cache past a single poll cycle
- the surface MUST NOT cross-merge server entries from different
  descriptor sources into a single row

## Operations That Remain CLI-Only

The MCP server selection UX MUST NOT issue, dispatch, proxy,
auto-trigger, queue, or schedule any of the shipped mutating CLI
operations on the operator's behalf. The full Phase 10G / 10J /
10L / 10O CLI-only enumeration applies verbatim to the selection
UX. The selection UX MAY surface advisory context that helps the
operator decide which CLI subcommand to run after enabling a
server; the selection UX MUST NOT execute the subcommand.

Mutating operations (write canonical artifacts and/or persist
halt status):

- `attach-external-target`, `detach-external-target`,
  `verify-external-target`
- `plan`, `activate`
- `run`, `resume`, `auto-continue`,
  `run-long-run-continuation`, `run-capacity-reprobe`
- `record-final-acceptance`, `record-token-exhaustion`,
  `record-capacity-halt`, `build-continuation-context`,
  `distill-phase-boundary-memory`, `load-optional-context`,
  `integrate-optional-context`, `synthesize-repeated-failures`,
  `intake-prd`, `dispatch-prompt-handoff`,
  `run-internal-review-fix-cycle`, `set-runtime-config`,
  `runtime-adapter-eval`, `langchain-support-eval`,
  `bootstrap-prompt`

Read-only operations the selection UX MAY surface as advisory
context but MUST NOT execute on the operator's behalf:

- `inspect-external-target`, `inspect-artifacts`, `status`,
  `evaluate-final-acceptance`, `validate-artifacts`,
  `check-state`, `view-external-status`,
  `view-external-controls`, `view-artifact-dashboard`,
  `view-desktop-actions`, `view-desktop-setup`,
  `view-desktop-run-profiles`, `view-desktop-project-start`

Library-callable read-only operations the selection UX MAY delegate
through the shipped Phase 10I
`invoke-external-control --control <ID>` surface (no CLI subprocess,
direct library-function call):

- `view-external-status`, `view-external-controls`,
  `inspect-external-target`

The selection UX MUST NOT introduce additional library-callable
controls beyond the three the Phase 10I registry already pins.
Extending the library-callable surface requires a future Phase 10
sub-phase that updates `_EXTERNAL_UI_CONTROL_REGISTRY`, the
Phase 10I tests, the Phase 10J dashboard contract, the Phase 10L
desktop-app contract, the Phase 10O MCP integration contract, and
this contract in lockstep.

## Identity And Operator Attribution

The selection UX MUST NOT auto-fill any operator identity field
from an MCP-fetched value, an MCP server session, a browser
session, an OS-level "current user" lookup (`whoami`, `$USER`),
a packaging-time-configured identity, a code-signing-bound
identity, or any persistent MCP-side identity store. Every
enablement affordance the selection UX surfaces continues to
require the operator to supply identity fields explicitly
(matching the shipped Phase 10B `attached_by` / Phase 10C
`bootstrapped_by` / Phase 9G `accepted_by` "never auto-filled from
`$USER` / `whoami`" invariants), and the selection UX MUST NOT
pre-populate those fields based on MCP-fetched values, a stored
prior session, or any saved per-operator preference.

## Refusal Behavior

The selection UX MUST refuse fail-closed (render an error state,
NOT silently proceed) in at least the following cases. The
specific runtime error-state vocabulary will be defined by the
later Phase 10 runtime slice that wires the selection surface;
this contract pins the refusal-eligibility:

- an MCP server descriptor is missing one of the required fields,
  carries a wrong-typed value, carries an unknown
  `permission_class`, or carries an unknown
  `capability_categories` member. The selection UX MUST surface
  the descriptor-validation failure as an error state and MUST NOT
  render the row as eligible for enablement
- an MCP server's `permission_class` is `deferred_mutating_class`.
  The selection UX MUST render the `[refused]` tag, render the
  `deferred_runtime_marker`, and surface this contract paragraph
  pointing the operator at the Phase 10U+ slice that defers the
  permission class
- an `approval_requirements` entry is unsatisfied. The selection
  UX MUST render the specific unsatisfied requirement and MUST NOT
  silently proceed
- the `phase_10t_runtime_available` (or
  `phase_10u_runtime_available`) requirement is False. The
  selection UX MUST refuse the enablement affordance and MUST
  point the operator at the canonical roadmap entry for the
  pending runtime slice
- the operator-supplied policy rule refuses the enablement. The
  selection UX MUST surface both the policy rule's refusal message
  and the base contract's eligibility verdict
- the selection UX is asked to enable a server outside the
  Phase 10S contract (e.g. via a hypothetical future CLI flag that
  attempts to short-circuit the approval requirements). The
  selection UX MUST refuse and surface this contract paragraph

Every selection-UX refusal state MUST point the operator at a
shipped CLI remediation step (or, when the refusal is
contract-level, at the specific contract paragraph that pins the
refusal). The selection UX MUST NOT offer a "fix" affordance that
would mutate canonical state.

## Source-Of-Truth Preservation

Canonical artifacts on disk remain authoritative; the MCP server
selection UX is an ADVISORY rendering surface, not a state store.
The Phase 10G UI contract's, the Phase 10J dashboard contract's,
the Phase 10L desktop-app contract's, and the Phase 10O MCP
integration contract's source-of-truth rules all apply verbatim,
plus the following selection-UX-specific clarifications:

- the selection UX MUST NOT introduce an MCP-side database,
  key-value store, cache, or session store that holds selection
  state separately from on-disk artifacts. A per-poll-cycle
  in-memory cache for rendering consistency is permitted; cache
  invalidation per poll is required
- the selection UX MUST NOT introduce a per-operator MCP-server
  enablement preference store, recents list, favorites list, or
  enablement history; the surface is per-poll-derived
- the selection UX MUST NOT introduce an MCP-side notification
  queue, event-stream subscription, or webhook surfacing selection
  events
- the selection UX MUST NOT introduce an MCP-side identity token,
  session token, or auth-bearer that substitutes for the shipped
  operator-identity placeholders
- the selection UX MUST treat the per-server descriptor list as
  read-only inputs; the rendered value of any selection-UX field
  MUST come from a fresh per-poll read of the descriptors, not
  from a stored snapshot of an earlier read
- the selection UX MAY introduce its own selection-UX-side debug
  log (for diagnosing rendering issues) but that log is purely
  advisory and MUST NOT be cited as the canonical record of any
  operator action

## Safety Boundaries

The future MCP server selection UX MUST refuse to:

- commit, push, tag, branch, stash, reset, checkout, or otherwise
  mutate Git history or working-tree state in either the
  controller or the target (the shipped no-Git-automation boundary
  applies to the selection UX in BOTH roots, mirroring the
  Phase 10A - 10O contracts)
- modify `AGENTS.md`, `CLAUDE.md`, `ROADMAP.md`, `README.md`,
  `docs/external-ui-contract.md`,
  `docs/artifact-dashboard-contract.md`,
  `docs/desktop-app-contract.md`,
  `docs/mcp-integration-contract.md`,
  `docs/mcp-server-selection-ux-contract.md`, any other docs/
  contract file, or any source / instruction file in either root
  as a side effect of any selection-UX rendering or selection
  event
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
  from the selection UX process
- silently widen autonomy by treating a selection-UX click,
  selection-UX keypress, or selection-UX rendered value as an
  implicit operator-identity assertion (no auto-fill of any
  `--*-by` identity flag from selection-UX events, MCP server
  session, browser session, OS username, or any persistent
  MCP-side identity store)
- silently activate a target-side phase from any selection event;
  the shipped Phase 4C activator + `APPROVED_FOR_ACTIVATION`
  token remain the only path to per-target phase activation
- silently record final human acceptance from any selection event;
  the shipped Phase 9G `record-final-acceptance` CLI + the
  `--accepted-by` operator identity remain the only path
- silently re-bootstrap a target from any selection event; the
  shipped Phase 10E `attach-external-target --bootstrap` CLI +
  the required operator inputs remain the only path
- bypass any shipped Phase 5 review / strict-mode / autonomous
  approval-mode boundary
- bypass any shipped Phase 6 memory, checkpoint, continuation,
  runtime-adapter, or LangChain support-layer boundary
- introduce mutation-capable selection events, controlled-
  concurrency awareness, multi-target selection sessions, RAG
  layers, GitHub integration, packaging / code-signing /
  auto-update pipelines, policy-pack runtime layering, or any
  other capability beyond the bounded advisory rendering surface
  described above

## Approval Gates

The MCP server selection UX contract preserves every shipped
human-approval gate (Phase 10A + 10B + 10C + 10D + 10E + 10F +
10G + 10H + 10I + 10J + 10K + 10L + 10M + 10N + 10O + 10P + 10Q +
10R enumeration):

- per-target phase activation continues to require the shipped
  Phase 4C activator + `APPROVED_FOR_ACTIVATION` token; the
  selection UX MUST NOT issue or auto-fill the token
- per-target `APPROVED_FOR_HUMAN_REVIEW` terminals continue to
  halt the target-side loop and require explicit human approval
  before the next phase begins. The selection UX MUST NOT
  short-circuit this; the surface MAY render advisory context that
  helps the human decide
- the Phase 9G final human acceptance gate continues to require an
  explicit operator action on the target's canonical artifact set
  via the shipped `record-final-acceptance` CLI. The selection UX
  MUST NOT record acceptance
- the Phase 5 approval-mode boundaries (`review` / `strict` /
  `autonomous`) continue to apply verbatim; the
  `approval_mode_supports_enablement` requirement above is the
  selection-UX-side mirror of this boundary
- the Phase 10F freshness assertion continues to be a fail-closed
  guard a human runs via `verify-external-target`; the selection
  UX MUST NOT silently re-attach or re-verify a target as a side
  effect of any selection event

## Audit Expectations

A reviewer reading the controller's `.agent-loop/orchestrator.log`
plus the target's `.agent-loop/orchestrator.log` MUST be able to
reconstruct what the operator did, without needing access to any
selection-UX-side log, MCP-side log, event stream, session
record, or telemetry feed. Specifically:

- every mutating operation the operator triggers through the
  shipped CLI continues to produce its existing
  `[orchestrator] ...` audit line in the appropriate log; the
  selection UX MUST NOT swallow, rewrite, or reformat those
  lines, and MUST NOT silently dispatch a mutating CLI subcommand
  on the operator's behalf in response to a selection event
- a selection-UX render or selection-UX click MAY produce a
  selection-UX-side debug entry, but that entry is purely advisory
  and MUST NOT be cited as the canonical record of any operator
  action. The canonical audit record remains the on-disk
  `orchestrator.log`
- a refused selection-UX enablement (descriptor invalid, permission
  class refused, approval requirement unsatisfied, runtime
  unavailable, policy rule refused) is visible only in the
  selection UX's own rendering; canonical halt-status persistence
  remains the result of a human-initiated CLI invocation
- the selection UX MAY surface a "this would have been audited as
  X" preview alongside an advisory affordance, but the preview is
  advisory and the canonical audit-log line only exists when the
  operator actually runs the shipped CLI

## Evidence-Review Preservation

The shipped Phase 2A Evidence Collection Contract and the shipped
Codex review cycle remain the canonical record of what each cycle
produced. The selection UX MUST NOT:

- substitute for the on-disk `.agent-loop/test-output.log`,
  `.agent-loop/lint-output.log`,
  `.agent-loop/typecheck-output.log`, or
  `.agent-loop/build-output.log`; a selection-UX rendering of an
  MCP server entry is NEVER the canonical record
- substitute for `.agent-loop/git-diff.patch` or
  `.agent-loop/git-status.log`; a selection-UX rendering is NEVER
  the canonical record
- substitute for `.agent-loop/claude-summary.md` (Claude-owned) or
  `.agent-loop/codex-review.md` (Codex-owned); a selection-UX
  rendering is NEVER the canonical record
- modify the shipped `scripts/run_checks.sh` evidence-collection
  script; the selection UX runs separately from the
  evidence-collection step
- silently inject content into Claude's implementation prompt or
  Codex's review prompt without an `[mcp-advisory]` tag making the
  provenance explicit; a reviewer reading the prompt MUST be able
  to tell which lines are canonical vs MCP-fetched

## Dependencies On Later Phase 10 Slices

The MCP server selection UX contract is load-bearing for the
following later Phase 10 sub-phases:

- Phase 10T (MCP Read-Only Assistance In Desktop App) wires the
  first MCP runtime against this contract. The slice MUST honor
  the per-server descriptor shape pinned above, MUST surface every
  per-server entry with the closed permission-class label and full
  capability-category label list, MUST render the per-server
  safety-copy block before any enablement affordance, MUST gate
  every enablement affordance behind the closed approval-requirement
  list, MUST refuse fail-closed on any descriptor whose
  `permission_class` is `deferred_mutating_class`, and MUST NOT
  widen the Phase 10I library-callable cap. Phase 10T satisfies the
  `read_only_advisory_class` and `browser_inspection_class`
  enablement paths.
- Phase 10U and later: bounded mutation-capable MCP actions plus
  the additional safety gates required before any
  `deferred_mutating_class` server is allowed to be enabled.
  Each later capability lands in its own Phase 10 sub-phase
  tracked in `ROADMAP.md`; each MUST update this contract with
  the per-action approval gates, audit-log entry shape, refusal
  vocabulary, rollback behavior, and the closed eligibility set
  before any enablement affordance for the class is surfaced as
  eligible.

The selection UX contract is consumed by every prior Phase 10
slice in the following sense: the canonical artifact set the
selection UX MAY render alongside its per-server entries is
exactly the set the Phase 1 - 10R slices already produce; no new
canonical artifact is introduced by this contract. The selection
UX is a strict ADVISORY rendering layer over existing canonical
state plus per-server descriptors.

## Out Of Scope For Phase 10S

Phase 10S is documentation / contract only. The shipped Phase 1 -
9 runtime behavior is preserved unchanged by this slice; no
orchestrator, planner, activator, evidence-collection,
review-routing, checkpoint, continuation, memory,
runtime-adapter, LangChain, VS Code, Phase 9 autonomous-PRD,
capacity-reprobe, final-acceptance, external-workspace, external
UI, dashboard, desktop-app, MCP integration, desktop setup,
desktop run-profiles, or desktop project-start runtime feature
work is introduced. No Phase 10G / 10H / 10I / 10J / 10K / 10L /
10M / 10N / 10O / 10P / 10Q / 10R surface is changed. No MCP
client library, MCP server adapter, MCP runtime, MCP descriptor
registry, MCP server selection runtime, MCP policy engine,
browser inspection runtime, app inspection runtime, RAG layer,
GitHub integration, packaging / code-signing / auto-update
pipeline, system-tray surface, or controlled-concurrency runtime
ships in this slice. No new CLI subcommand, no new library
function, no new halt status, no new canonical artifact, no Git
automation, no rewrite of `AGENTS.md` / `CLAUDE.md` / `ROADMAP.md`
/ the Phase 2A / 3A / 4A contracts / `scripts/run_checks.sh`.
Adding the MCP server selection runtime that satisfies this
contract is the work of Phase 10T (for the
`read_only_advisory_class` / `browser_inspection_class`
enablement paths) and Phase 10U+ (for the
`deferred_mutating_class` enablement path); each lands in its own
later Phase 10 sub-phase tracked in `ROADMAP.md`.
