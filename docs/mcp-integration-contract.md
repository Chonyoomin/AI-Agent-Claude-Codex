# MCP Integration Contract And Safe Tool Boundary

## Status

Phase 10O defines this contract. No MCP server runtime, MCP tool
execution path, MCP-driven canonical-artifact write, MCP-driven
browser automation, MCP-driven app inspection, MCP policy engine,
networked tool orchestrator, or third-party MCP integration ships
in this slice. The contract below specifies the FIRST MCP
integration boundary for the agent loop: which tool categories the
shipped agent loop MAY consume from a future MCP server; which
ownership and routing rules every MCP tool MUST satisfy; which
refusal cases the future MCP runtime MUST honor; how the MCP
runtime MUST preserve the shipped evidence-review model, approval
gating, external-workspace boundaries, desktop/UI boundaries, and
the canonical-artifact-first model; how the MCP runtime MUST
distinguish read-only assistance from still-deferred
mutation-capable MCP actions; and which boundaries are preserved
from the shipped Phase 1 - 9 system, the Phase 10A - 10F
external-workspace slices, the Phase 10G - 10I external UI
surfaces, the Phase 10J - 10K artifact dashboard contract and
runtime, and the Phase 10L - 10N desktop app contract / runtime /
action-bridge slices. Implementation of MCP runtime support is
deferred to later Phase 10 sub-phases:

- Phase 10T: MCP Read-Only Assistance In Desktop App (the
  first MCP server consumer that fetches read-only advisory
  context from a configured MCP server, surfaces it as advisory
  derived state alongside canonical mirrors, and never mutates
  any canonical artifact)
- Phase 10U and later: bounded mutation-capable MCP actions plus
  the additional safety gates required before any non-read-only
  MCP-assisted runtime behavior is allowed, tracked in
  `ROADMAP.md`

## Scope

This document is the contract every future MCP-assisted runtime
slice MUST satisfy when it is implemented. It is NOT a description
of currently shipped runtime behavior. The shipped repository
today exposes ZERO MCP integration paths: the agent loop does NOT
consume any MCP server, the orchestrator does NOT invoke any MCP
tool, the planner does NOT delegate to any MCP tool, the
implementation cycle does NOT bind any MCP tool into Claude's or
Codex's context, the review cycle does NOT consume MCP-fetched
evidence, the external UI / dashboard / desktop surfaces do NOT
render any MCP-fetched value, and the runtime adapter / LangChain
support layer do NOT expose any MCP-callable surface. Every
canonical artifact write happens through the shipped library
functions the CLI dispatches to, and every read-side surface
reads on-disk canonical artifacts directly.

The MCP integration contract is the load-bearing specification for
"which MCP tool categories the future MCP runtime MAY surface",
"which on-disk canonical artifacts MCP tools MAY read", "which
MCP-fetched values MAY be rendered only as advisory derived
state", "which mutation-capable MCP actions are deferred to later
phases", "how the MCP runtime MUST preserve every shipped
evidence-review / approval-gate / ownership-boundary invariant",
"how the MCP runtime MUST refuse fail-closed on unsafe tool
categories or unsafe target surfaces", and "how the MCP runtime
MUST preserve the canonical-artifact-first source-of-truth model".
The contract pins the closed tool-category enumeration, the
read-only-vs-deferred-mutating boundary, the ownership-and-routing
rules, the browser/app inspection hook boundary, the policy-rule
hook boundary, the refusal vocabulary, and the safety / approval /
audit boundaries every future MCP runtime slice MUST preserve so
later Phase 10T+ slices can be implemented from this contract
without further design decisions and without collapsing the
shipped CLI-first, evidence-review-driven workflow into a parallel
MCP control plane.

## Distinction From Shipped Artifacts And Surfaces

The MCP integration is NOT one of the existing shipped surfaces.
The shipped Phase 1 - 9 system, the Phase 10A - 10F
external-workspace slices, the Phase 10G - 10I external UI
surfaces, the Phase 10J - 10K artifact dashboard contract and
runtime, and the Phase 10L - 10N desktop-app contract / runtime /
action-bridge slices already define these distinct surface roles
which the MCP integration contract MUST NOT overlap or replace:

- The shipped `python scripts/agent_loop.py ...` CLI is the
  canonical operator entry point for every mutating workflow. The
  MCP runtime MUST NOT replace, wrap, shadow, or auto-trigger
  these CLI surfaces; the MCP runtime MAY surface advisory
  context that helps an operator decide WHICH CLI subcommand to
  run, but MUST NOT execute them.
- The shipped Phase 2A Evidence Collection Contract pins which
  evidence files an orchestrator-driven cycle produces. MCP tools
  MUST NOT write any of those evidence files; MCP tools MAY read
  the on-disk evidence files as advisory context; MCP-fetched
  values MUST NOT substitute for the shipped evidence-collection
  output that Codex review consumes.
- The shipped Phase 3A Orchestrator Contract pins the canonical
  loop-state schema and the orchestrator's write-ownership rules.
  MCP tools MUST NOT write `.agent-loop/loop-state.json`,
  `.agent-loop/orchestrator.log`, or any other orchestrator-owned
  artifact.
- The shipped Phase 4A Planning Contract pins the planner's
  proposal authorship boundary and the activation gate. MCP tools
  MUST NOT author `.agent-loop/proposed-phase.md`, MUST NOT add
  or forge the `APPROVED_FOR_ACTIVATION` token, and MUST NOT
  trigger the Phase 4C activator on the operator's behalf.
- The shipped Phase 5A Approval Modes Contract pins the
  review / strict / autonomous approval-mode boundaries. MCP
  tools MUST NOT change the approval mode of an in-flight cycle,
  MUST NOT short-circuit a strict-mode pause, and MUST NOT widen
  the autonomous-mode boundary into MCP-assisted writes.
- The shipped Phase 6A Durable Memory Contract pins memory write
  ownership. MCP tools MUST NOT write into
  `.agent-loop/memory/`; MCP tools MAY read the on-disk memory
  tree as advisory context.
- The shipped Phase 9G Final Human Acceptance Gate pins the
  `record-final-acceptance` CLI as the only path that records
  human acceptance. MCP tools MUST NOT record acceptance, MUST
  NOT auto-fill `--accepted-by`, and MUST NOT widen the gate.
- The shipped Phase 10A - 10F external-workspace contracts pin
  controller-vs-target ownership, attach record schema,
  bootstrap rules, and the freshness check. MCP tools MUST NOT
  forge attach records, MUST NOT cross the controller/target
  boundary, and MUST NOT bypass the freshness check.
- The shipped Phase 10G UI contract pins the load-bearing UI
  boundaries (canonical artifact read set,
  advisory-vs-canonical mirror rule, CLI-only operations,
  no-auto-fill operator identity, refusal behavior,
  source-of-truth preservation, safety boundaries, approval
  gates, audit expectations). Every read-set / advisory-mirror /
  CLI-only / no-auto-fill / refusal / source-of-truth /
  safety / approval / audit rule in `docs/external-ui-contract.md`
  continues to apply to any MCP-fetched value the UI renders
  verbatim.
- The shipped Phase 10I `_EXTERNAL_UI_CONTROL_REGISTRY` caps the
  library-callable control surface at exactly three controls
  (`view-external-status`, `view-external-controls`,
  `inspect-external-target`). The MCP runtime MUST NOT introduce
  a fourth library-callable control nor a fourth MCP-callable
  shipped surface.
- The shipped Phase 10J - 10K artifact dashboard contract and
  runtime pin six dashboard surfaces and the canonical-mirror
  read set. MCP-fetched values MAY appear in the dashboard ONLY
  as advisory derived state tagged `[advisory]`, never as
  canonical mirrors.
- The shipped Phase 10L Desktop App Shell Contract pins the
  desktop process boundary, controller-root selection,
  refresh/polling cadence, artifact-opening behavior, and the
  library-call / CLI-spawn bridge. MCP integration MUST NOT
  bypass any of these boundaries; an MCP-assisted desktop
  rendering MUST go through the same shipped view library
  functions the Phase 10M runtime uses.
- The shipped Phase 10M - 10N desktop runtime and action-bridge
  surfaces pin the read-only and copy-paste-only operator
  affordance model. MCP-fetched values MAY surface alongside the
  shipped affordances ONLY as advisory derived state; MCP-fetched
  values MUST NOT alter the rendered command text, MUST NOT
  auto-fill any operator-identity placeholder, and MUST NOT
  silently dispatch a mutating CLI subcommand.

## MCP Tool Categories

The future MCP runtime MUST classify every MCP tool into exactly
one of the following closed categories before allowing the tool
to participate in any agent-loop cycle. The category determines
which boundaries the tool is subject to AND which later Phase 10
slice gates the tool's use.

### 1. Read-Only Advisory Context

Tools in this category fetch read-only context (documentation
lookups, library reference pages, schema descriptions, public API
metadata, code-search-style snippets) that may help the planner
choose between approaches or help the implementer understand a
target system. The fetched context is ALWAYS advisory derived
state per the Advisory-Vs-Canonical Mirror Rule below. Examples:

- a documentation MCP server that returns prose snippets from a
  public docs site
- a library-reference MCP server that returns API signatures or
  example usage
- a code-search MCP server that returns matching snippets from
  an indexed corpus
- a schema-inspection MCP server that returns the structure of
  an external JSON / YAML / proto schema the operator names

What this category MAY contribute to a cycle:

- additional advisory context inside Claude's implementation
  prompt or Codex's review prompt, surfaced under an explicit
  `[mcp-advisory]` tag so a reviewer can tell which lines are
  canonical vs MCP-fetched
- additional advisory context inside the Phase 10M desktop
  shell's rendered view, surfaced under an explicit
  `[mcp-advisory]` tag (matching the shipped `[advisory]` line
  tag the Phase 10K dashboard uses)
- additional advisory context inside the Phase 10K artifact
  dashboard's per-surface `advisory` section, never inside the
  `canonical_mirrors` section

What this category MUST NOT do:

- write any canonical artifact under any circumstance
- substitute for the shipped evidence-collection output (Phase
  2A); MCP-fetched test / lint / typecheck / build output is
  NEVER the canonical record
- substitute for the shipped Codex review (Phase 5A / 5B / 5C);
  MCP-fetched "code review" suggestions are NEVER the canonical
  review
- carry the `APPROVED_FOR_ACTIVATION` token or any operator-
  identity value across the MCP boundary
- silently advance loop-state or silently transition any cycle
  status

### 2. Browser/App Inspection (Read-Only)

Tools in this category fetch read-only inspection data from a
local browser, local desktop app, or local OS surface that the
operator explicitly authorizes per session. Examples:

- a browser DOM-inspection MCP tool that returns the structured
  text of a page the operator has open
- a screenshot MCP tool that captures the operator's screen for
  a specific window the operator selects
- an accessibility-tree inspection MCP tool that returns a11y
  metadata for an operator-selected element

What this category MAY contribute to a cycle:

- advisory derived state appearing in the rendered desktop view
  under an explicit `[mcp-advisory]` tag with the source
  inspection-tool name attributed
- advisory context inside Claude's implementation prompt when
  the operator explicitly attaches an inspection capture
  (similar to how the shipped Phase 6J optional-context-loader
  surfaces operator-attached files)

What this category MUST NOT do:

- run unattended in the background; every inspection MUST be
  initiated by an explicit operator action per session
- capture any value (cookies, browser session tokens, OS-level
  credentials, environment variables) that could be replayed to
  impersonate the operator; the future Phase 10T runtime slice
  MUST enumerate a closed list of capture-eligible fields and
  refuse fail-closed on any field outside that list
- persist inspection data across sessions; inspection captures
  are per-session and per-explicit-operator-action
- silently dispatch a mutating CLI subcommand based on an
  inspection finding

### 3. Deferred Mutation-Capable Tools

Tools in this category COULD in principle mutate canonical
artifacts, target-side state, external services, or external
infrastructure. This contract DEFERS every mutation-capable MCP
tool to a later Phase 10 slice (Phase 10U+); the FIRST MCP
runtime slice (Phase 10T) ships ONLY category 1 and category 2
tools. Examples of tools this contract explicitly defers:

- an MCP tool that writes / edits files on the controller or
  target root (any write path MUST go through the shipped CLI /
  library surfaces, never through MCP)
- an MCP tool that runs shell commands on the operator's machine
  (any shell execution MUST go through the shipped CLI surface
  or the operator's own shell, never through MCP)
- an MCP tool that opens network connections to third-party
  services, posts comments to GitHub / Slack / email, or invokes
  any external mutation API
- an MCP tool that installs packages, modifies system PATH,
  registers a system service, modifies a user's shell rc files,
  or otherwise alters the operator's machine state
- an MCP tool that interacts with cloud secrets stores, CI
  pipelines, deployment pipelines, or any production
  infrastructure

What this category MUST NOT do in the Phase 10T initial slice:

- ship at all; the Phase 10T runtime MUST refuse fail-closed on
  any MCP tool whose declared category is `deferred_mutating`
  and MUST surface the refusal as an explicit error state
  pointing the operator at the contract paragraph that defers
  the category

What later Phase 10U+ slices MUST add before enabling any tool
from this category:

- a mutation-capable MCP action contract that pins per-action
  approval gates, audit-log entry shape, refusal vocabulary,
  rollback behavior, and the exact subset of canonical artifacts
  (if any) the action MAY mutate
- an operator-identity model that requires explicit operator
  claim per mutation (matching the shipped Phase 10B
  `--attached-by` / Phase 10C `--bootstrapped-by` / Phase 9G
  `--accepted-by` placeholder model; never auto-filled from
  `$USER` / `whoami` / browser session / packaging-time
  identity)
- a closed enumeration of mutation-capable action ids with
  explicit per-action eligibility states derived from canonical
  loop-state.status (matching the Phase 10I controls registry
  pattern)
- explicit per-action audit-log notes recording which canonical
  artifact lines the mutation produced

## MCP Tool Ownership And Routing

Every MCP tool the future runtime consumes MUST be classified
into exactly one of the three categories above before any
agent-loop cycle is allowed to bind it into Claude's, Codex's, or
the desktop shell's context. The classification MUST be
recorded in a per-tool descriptor (matching the Phase 10I
control-registry descriptor shape) carrying at minimum:

- `id`: the MCP tool's canonical id
- `category`: one of `read_only_advisory`,
  `browser_app_inspection`, `deferred_mutating`
- `dispatch_mode`: `library_call` (delegates to a future MCP
  client library function) or `operator_invoked` (operator runs
  the tool themselves and pastes the output)
- `delegated_phase_10i_control_id`: when the tool is offered as
  a Phase 10I-style controls-view entry, the matching Phase 10I
  control id (or `null`); the MCP runtime MUST NOT widen the
  Phase 10I three-control library-callable cap
- `mutation_eligible`: bool; ALWAYS `false` in the Phase 10T
  initial slice
- `audit_note`: text describing the audit-log visibility the
  tool's use will produce
- `refusal_reason_template`: text the runtime uses when refusing
  the tool fail-closed

The runtime MUST refuse fail-closed on any MCP tool whose
descriptor is missing, malformed, or carries an unknown category
value.

## Read-Only Tool Boundary

For category 1 (read-only advisory context) and category 2
(browser/app inspection) tools, the MCP runtime MUST:

- surface every MCP-fetched value as advisory derived state
  tagged `[mcp-advisory]` in the rendered output, attributed to
  the source MCP tool id (matching the Phase 10K dashboard's
  per-line `[advisory]` attribution pattern)
- refresh MCP-fetched values per poll cycle (matching the
  Phase 10L per-poll-cycle cache invalidation rule); MUST NOT
  serve stale MCP values from an in-process cache past a single
  poll cycle
- preserve the canonical record on disk as the source of truth;
  MCP-fetched values MAY be displayed alongside canonical
  mirrors but MUST NOT replace, supplement, or contradict them
  in a way that hides which value is canonical
- propagate refusal vocabulary verbatim when an MCP tool returns
  an error or a malformed response; the runtime MUST NOT
  fabricate a substitute value
- enforce a bounded per-tool response size cap and refuse
  fail-closed on responses that exceed the cap (matching the
  Phase 6I distillation excerpt-byte-limit pattern)
- enforce a bounded per-cycle MCP-call count so a single cycle
  cannot saturate the MCP server; the cap is pinned by the
  future Phase 10T runtime slice

## Deferred Mutation-Capable Tool Boundary

For category 3 (deferred mutation-capable) tools, the Phase 10T
initial slice MUST refuse fail-closed unconditionally. The
runtime MUST NOT silently downgrade a `deferred_mutating` tool to
`read_only_advisory` based on a heuristic about whether the
tool "actually" mutates. Tool categorization is the tool author's
declared property; the runtime trusts the declaration and
refuses on any value other than the two read-only categories.

Adding any tool from this category requires a future Phase 10U+
slice that:

- updates this contract with the per-action mutation rules,
  approval gates, audit-log shape, and rollback behavior
- updates the per-tool descriptor registry with the action's
  closed eligibility set
- adds focused tests pinning the new boundary (positive: action
  is permitted under the specified state; negative: action is
  refused under every other state)
- preserves every shipped approval gate (Phase 4C activation
  token, Phase 9G acceptance, Phase 10B / 10C / 9G operator
  identity placeholders) verbatim

## Browser/App Inspection Hook Boundary

For category 2 (browser/app inspection) tools, the future MCP
runtime MUST enforce the following explicit boundaries:

- the operator MUST explicitly authorize each inspection session
  by name; the runtime MUST NOT auto-enable inspection based on
  a saved-session, a cookie, or any persistent OS-level
  permission grant
- the runtime MUST NOT capture any value that could be replayed
  to impersonate the operator (no cookies, no browser session
  tokens, no OS-level credentials, no environment variables, no
  SSH keys, no API keys, no clipboard contents beyond the
  explicit operator-selected paste, no clipboard auto-refresh)
- the runtime MUST NOT inject any value back into the inspected
  browser / app (no synthetic mouse events, no synthetic
  keystrokes, no form-fill); inspection is strictly READ-ONLY
  against the operator's existing browser / app state
- the runtime MUST NOT subscribe to OS-level event streams
  (keyboard hooks, screen-capture-without-explicit-action,
  microphone, camera); each capture is per-explicit-operator-
  action and per-session
- the runtime MUST NOT persist inspection captures across
  sessions; captures are in-memory advisory context for the
  current cycle ONLY
- the runtime MUST NOT silently dispatch a mutating CLI
  subcommand based on an inspection finding; mutating actions
  remain operator-CLI-invoked via the shipped Phase 10G CLI-only
  enumeration

## Policy Rule Hook Boundary

The future MCP runtime MAY surface a policy-rule hook that lets
the operator (or a Codex-owned policy pack) specify additional
refusal rules layered on top of this contract. Examples of
permitted policy rules:

- "refuse any MCP tool whose source domain is not on this
  per-operator allowlist"
- "refuse any MCP tool that returns more than N bytes per call"
- "refuse any MCP tool that has not been seen in the last 30
  days" (per-operator policy)

Boundaries the policy-rule hook MUST satisfy:

- policy rules are ADDITIVE only; a policy rule MAY refuse a
  tool the base contract would have allowed, but MUST NOT
  approve a tool the base contract refuses
- policy rules MUST NOT widen the read-only / deferred-mutation
  boundary; a policy rule cannot promote a `deferred_mutating`
  tool to a permitted category
- policy rules MUST NOT widen the Phase 10I library-callable
  three-control cap
- policy rules MUST NOT widen the no-auto-fill identity boundary
- policy rules MUST NOT silently dispatch any CLI subcommand
- policy rules MAY emit additional refusal messages that the
  runtime surfaces in the rendered output alongside the base
  contract's refusal vocabulary
- policy rules are advisory tooling layered on top of the
  contract; the contract is load-bearing, the policy rules are
  not

## Advisory-Vs-Canonical Mirror Rule

Every value the MCP runtime surfaces is one of two categories:

- **Canonical mirror (from a non-MCP source)**: a rendering of a
  value that came from a canonical on-disk artifact (loaded via
  a shipped library function or a direct read of an on-disk
  file). MCP integration does NOT add new canonical-mirror
  sources; the on-disk canonical-artifact set is unchanged.
- **MCP advisory derived state**: a rendering of a value that
  came from an MCP tool response. The runtime MUST mark these
  values as advisory and tagged `[mcp-advisory]` with the
  source MCP tool id attributed; the runtime MUST NOT promote
  these values to a source of truth.

The runtime MUST refresh MCP advisory values on every poll cycle
and MUST NOT serve stale MCP values past a single poll cycle
(matching the Phase 10L per-poll cache invalidation rule). The
runtime MUST NOT cross-merge MCP-fetched values from different
snapshots into a single rendered record.

This rule is the same advisory-vs-canonical mirror rule the
Phase 10G UI contract, the Phase 10J dashboard contract, and the
Phase 10L desktop-app contract pin; the MCP integration contract
preserves it verbatim and applies it to every MCP-rendered value.

## Operations That Remain CLI-Only

The MCP runtime MUST NOT issue, dispatch, proxy, auto-trigger,
queue, or schedule any of the following shipped operations on
the operator's behalf. The full Phase 10G / 10J / 10L CLI-only
enumeration applies verbatim to the MCP runtime. The MCP runtime
MAY surface advisory context that helps the operator decide
which CLI subcommand to run; the MCP runtime MUST NOT execute
the subcommand.

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

Read-only operations the MCP runtime MAY surface as advisory
context but MUST NOT execute on the operator's behalf:

- `inspect-external-target`, `inspect-artifacts`, `status`,
  `evaluate-final-acceptance`, `validate-artifacts`,
  `check-state`, `view-external-status`,
  `view-external-controls`, `view-artifact-dashboard`,
  `view-desktop-actions`

Library-callable read-only operations the MCP runtime MAY
delegate through the shipped Phase 10I
`invoke-external-control --control <ID>` surface (no CLI
subprocess, direct library-function call):

- `view-external-status`, `view-external-controls`,
  `inspect-external-target`

The MCP runtime MUST NOT introduce additional library-callable
controls beyond the three the Phase 10I registry already pins.
Extending the library-callable surface requires a future Phase 10
sub-phase that updates `_EXTERNAL_UI_CONTROL_REGISTRY`, the
Phase 10I tests, the Phase 10J dashboard contract, the Phase 10L
desktop-app contract, and this MCP contract in lockstep.

## MCP Identity And Operator Attribution

The MCP runtime MUST NOT auto-fill any operator identity field
from an MCP-fetched value, an MCP server session, a browser
session, an OS-level "current user" lookup (`whoami`, `$USER`),
a packaging-time-configured identity, a code-signing-bound
identity, or any persistent MCP-side identity store. Every
mutating CLI invocation the operator launches via MCP-surfaced
advisory context continues to require the operator to supply
identity fields explicitly (`--attached-by`,
`--bootstrapped-by`, `--detached-by`, `--accepted-by`), and the
MCP runtime MUST NOT pre-populate those fields based on
MCP-fetched values. This mirrors the shipped Phase 10B
`attached_by` / Phase 10C `bootstrapped_by` / Phase 9G
`accepted_by` "never auto-filled from `$USER` / `whoami`"
invariants, and matches the Phase 10G / 10J / 10L contracts'
identity rules.

## Refusal Behavior

The future MCP runtime MUST refuse fail-closed (render an error
state, NOT silently proceed) in at least the following cases.
The specific runtime error-state vocabulary will be defined by
the Phase 10T runtime slice; this contract pins the
refusal-eligibility:

- an MCP tool descriptor is missing, malformed, or carries an
  unknown `category` value. The runtime MUST surface the
  descriptor-validation failure as an error state and MUST NOT
  bind the tool into the cycle context.
- an MCP tool's declared category is `deferred_mutating`. The
  runtime MUST refuse the tool unconditionally and MUST surface
  the contract paragraph that defers the category (pointing the
  operator at this document's "Deferred Mutation-Capable Tool
  Boundary" section).
- an MCP tool response exceeds the bounded per-tool response
  size cap. The runtime MUST refuse and MUST NOT truncate-then-
  serve the response as if it were valid.
- an MCP-fetched value attempts to set a canonical loop-state
  field, write any canonical artifact, supply the
  `APPROVED_FOR_ACTIVATION` token, or supply any `--*-by`
  identity argument. The runtime MUST refuse and surface which
  boundary the MCP-fetched value attempted to cross.
- the per-cycle MCP-call count cap is exceeded. The runtime
  MUST refuse and surface the cap value.
- the operator-supplied policy rule refuses the tool. The
  runtime MUST surface both the policy rule's refusal message
  and the base contract's eligibility verdict (so the operator
  sees whether the refusal came from the contract or from the
  per-operator policy).
- the MCP server connection fails or returns a transport-level
  error. The runtime MUST surface the connection failure as an
  error state and MUST NOT fabricate a substitute response.
- the MCP server's TLS or transport authentication fails. The
  runtime MUST refuse fail-closed; MCP integration MUST NEVER
  silently downgrade to unauthenticated transport.

Every MCP refusal state MUST point the operator at a shipped CLI
remediation step (or, when the refusal is contract-level, at the
specific contract paragraph that pins the refusal). The MCP
runtime MUST NOT offer a "fix" affordance that would mutate
canonical state.

## Source-Of-Truth Preservation

Canonical artifacts on disk remain authoritative; MCP integration
is an ADVISORY context source, not a state store. The Phase 10G
UI contract's, the Phase 10J dashboard contract's, and the Phase
10L desktop-app contract's source-of-truth rules all apply
verbatim, plus the following MCP-specific clarifications:

- the MCP runtime MUST NOT introduce an MCP-side database,
  key-value store, cache, or session store that holds canonical
  state separately from on-disk artifacts. A per-poll-cycle
  in-memory cache for rendering consistency is permitted; cache
  invalidation per poll is required.
- the MCP runtime MUST NOT introduce an MCP-side notification
  queue, event-stream subscription, or webhook that would
  surface MCP events before the canonical on-disk audit record
  is written. All MCP-rendered activity remains advisory.
- the MCP runtime MUST NOT introduce an MCP-side identity
  token, session token, or auth-bearer that substitutes for the
  shipped operator-identity placeholders. The MCP transport MAY
  authenticate to an MCP server (that is a transport concern,
  not a canonical-identity concern); the canonical "who did
  this" record remains the attached_by / bootstrapped_by /
  accepted_by / detached_by field in each canonical artifact.
- the MCP runtime MUST treat its own configuration / saved
  server list as advisory; the rendered value of any MCP-fetched
  field MUST come from a fresh per-poll call, not from a stored
  snapshot of an earlier call.
- the MCP runtime MAY introduce its own MCP-side activity log
  (for debugging MCP rendering issues) but that log is purely
  advisory and MUST NOT be cited as the canonical record of any
  operator action.
- the MCP runtime MUST NOT introduce an MCP-side memory store
  separate from `.agent-loop/memory/`; the shipped Phase 6
  memory tree is the canonical record.

## Safety Boundaries

The future MCP runtime MUST refuse to:

- commit, push, tag, branch, stash, reset, checkout, or
  otherwise mutate Git history or working-tree state in either
  the controller or the target (the shipped no-Git-automation
  boundary applies to MCP integration in BOTH roots, mirroring
  the Phase 10A - 10N contracts)
- modify `AGENTS.md`, `CLAUDE.md`, `ROADMAP.md`, `README.md`,
  `docs/external-ui-contract.md`,
  `docs/artifact-dashboard-contract.md`,
  `docs/desktop-app-contract.md`,
  `docs/mcp-integration-contract.md`, any other docs/ contract
  file, or any source / instruction file in either root as a
  side effect of MCP-tool execution
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
  from the MCP runtime process
- silently widen autonomy by treating an MCP-fetched value as
  an implicit operator-identity assertion (no auto-fill of any
  `--*-by` identity flag from MCP-fetched values, MCP server
  session, browser session, OS username, or any persistent
  MCP-side identity store)
- silently activate a target-side phase from MCP context; the
  shipped Phase 4C activator + `APPROVED_FOR_ACTIVATION` token
  remain the only path to per-target phase activation
- silently record final human acceptance from MCP context; the
  shipped Phase 9G `record-final-acceptance` CLI + the
  `--accepted-by` operator identity remain the only path
- silently re-bootstrap a target from MCP context; the shipped
  Phase 10E `attach-external-target --bootstrap` CLI + the
  required operator inputs remain the only path
- bypass any shipped Phase 5 review / strict-mode / autonomous
  approval-mode boundary
- bypass any shipped Phase 6 memory, checkpoint, continuation,
  runtime-adapter, or LangChain support-layer boundary
- introduce mutation-capable MCP actions, controlled-concurrency
  awareness, multi-target MCP sessions, RAG layers, GitHub
  integration, packaging / code-signing / auto-update pipelines,
  policy-pack runtime layering, or any other capability beyond
  the bounded read-only context surface described above

## Approval Gates

The MCP integration contract preserves every shipped
human-approval gate (Phase 10A + 10B + 10C + 10D + 10E + 10F +
10G + 10H + 10I + 10J + 10K + 10L + 10M + 10N enumeration):

- per-target phase activation continues to require the shipped
  Phase 4C activator + `APPROVED_FOR_ACTIVATION` token; the MCP
  runtime MUST NOT issue or auto-fill the token
- per-target `APPROVED_FOR_HUMAN_REVIEW` terminals continue to
  halt the target-side loop and require explicit human approval
  before the next phase begins. The MCP runtime MUST NOT
  short-circuit this; the runtime MAY surface advisory context
  that helps the human decide
- the Phase 9G final human acceptance gate continues to require
  an explicit operator action on the target's canonical artifact
  set via the shipped `record-final-acceptance` CLI. The MCP
  runtime MUST NOT record acceptance
- the Phase 5 approval-mode boundaries (`review` / `strict` /
  `autonomous`) continue to apply verbatim. The MCP runtime MUST
  NOT change the active approval mode of an in-flight cycle, and
  MUST NOT widen the autonomous-mode boundary into MCP-assisted
  writes
- the Phase 10F freshness assertion continues to be a
  fail-closed guard a human runs via `verify-external-target`.
  The MCP runtime MAY surface the inspector's advisory drift
  report on every poll, but the canonical halt-status
  persistence remains the result of an operator-initiated CLI
  invocation

## Audit Expectations

A reviewer reading the controller's `.agent-loop/orchestrator.log`
plus the target's `.agent-loop/orchestrator.log` MUST be able to
reconstruct what the operator did, without needing access to any
MCP-side log, event stream, session record, or telemetry feed.
Specifically:

- every mutating operation the operator triggers through the
  shipped CLI continues to produce its existing
  `[orchestrator] ...` audit line in the appropriate log; the
  MCP runtime MUST NOT swallow, rewrite, or reformat those
  lines, and MUST NOT silently dispatch a mutating CLI
  subcommand on the operator's behalf
- an MCP-tool call MAY produce an MCP-side debug log entry, but
  that entry is purely advisory and MUST NOT be cited as the
  canonical record of any operator action. The canonical audit
  record remains the on-disk `orchestrator.log`
- a refused MCP-tool call (descriptor invalid, category refused,
  size cap exceeded, policy rule refused, transport failed) is
  visible only in the MCP runtime's own rendering; canonical
  halt-status persistence remains the result of a human-
  initiated CLI invocation
- the MCP runtime MAY surface a "this would have been audited
  as X" preview alongside an advisory affordance, but the
  preview is advisory and the canonical audit-log line only
  exists when the operator actually runs the shipped CLI

## Evidence-Review Preservation

The shipped Phase 2A Evidence Collection Contract and the shipped
Codex review cycle remain the canonical record of what each cycle
produced. MCP-fetched values MUST NOT:

- substitute for the on-disk `.agent-loop/test-output.log`,
  `.agent-loop/lint-output.log`,
  `.agent-loop/typecheck-output.log`, or
  `.agent-loop/build-output.log`; MCP-fetched test / lint /
  typecheck / build output is NEVER the canonical record Codex
  reviews
- substitute for `.agent-loop/git-diff.patch` or
  `.agent-loop/git-status.log`; MCP-fetched diff state is NEVER
  the canonical record
- substitute for `.agent-loop/claude-summary.md` (Claude-owned)
  or `.agent-loop/codex-review.md` (Codex-owned); MCP-fetched
  "summary" or "review" text is NEVER the canonical record
- modify the shipped `scripts/run_checks.sh` evidence-
  collection script; MCP integration runs separately from the
  evidence-collection step
- silently inject content into Claude's implementation prompt or
  Codex's review prompt without an `[mcp-advisory]` tag making
  the provenance explicit; a reviewer reading the prompt MUST
  be able to tell which lines are canonical vs MCP-fetched

The MCP runtime MAY surface advisory context (documentation
lookups, library reference, schema descriptions) that helps
Claude understand a target system or helps Codex spot a missing
test, but the canonical evidence (test logs, diff patches,
review verdict) remains the on-disk shipped artifact set.

## Dependencies On Later Phase 10 Slices

The MCP integration contract is load-bearing for the following
later Phase 10 sub-phases:

- Phase 10T (MCP Read-Only Assistance In Desktop App)
  satisfies this contract's read-only path. The slice
  introduces the first MCP server consumer (covering category
  1 and category 2 tools only), pins the per-tool descriptor
  schema, the bounded response-size cap, the per-cycle call
  count cap, the per-poll cache invalidation rule, and the
  `[mcp-advisory]` line-tag attribution. Phase 10T MAY surface
  advisory context inside Claude's prompt, Codex's prompt, the
  Phase 10K dashboard's `advisory` sections, and the Phase 10M
  desktop shell's rendered view; Phase 10T MUST NOT widen the
  Phase 10I library-callable cap, MUST NOT auto-fill any
  operator-identity, and MUST NOT introduce any
  `deferred_mutating` tool.
- Phase 10U and later: bounded mutation-capable MCP actions
  plus the additional safety gates required before any tool
  from category 3 is allowed (per-action approval gates, audit-
  log entry shape, closed eligibility enumeration, rollback
  behavior). Each later capability lands in its own Phase 10
  sub-phase tracked in `ROADMAP.md`.

The MCP integration contract is consumed by every prior Phase 10
slice in the following sense: the canonical artifact set MCP
tools MAY read is exactly the set the Phase 1 - 10N slices
already produce; no new canonical artifact is introduced by the
MCP contract. The MCP runtime is a strict ADVISORY layer over
existing canonical state.

## Out Of Scope For Phase 10O

Phase 10O is documentation / contract only. The shipped Phase 1 -
9 runtime behavior is preserved unchanged by this slice; no
orchestrator, planner, activator, evidence-collection,
review-routing, checkpoint, continuation, memory,
runtime-adapter, LangChain, VS Code, Phase 9 autonomous-PRD,
capacity-reprobe, final-acceptance, external-workspace, external
UI, dashboard, or desktop-app runtime feature work is introduced.
No Phase 10G / 10H / 10I / 10J / 10K / 10L / 10M / 10N surface
is changed. No MCP client library, MCP server adapter, MCP
runtime, MCP descriptor registry, MCP policy engine, browser
inspection runtime, app inspection runtime, RAG layer, GitHub
integration, packaging / code-signing / auto-update pipeline,
system-tray surface, or controlled-concurrency runtime ships in
this slice. No new CLI subcommand, no new library function, no
new halt status, no new canonical artifact, no Git automation,
no rewrite of `AGENTS.md` / `CLAUDE.md` / `ROADMAP.md` / the
Phase 2A / 3A / 4A contracts. Adding the MCP read-only
assistance runtime that satisfies this contract is the work of
Phase 10T; bounded mutation-capable MCP actions and any other
advanced MCP capability each land in their own later Phase 10
sub-phases tracked in `ROADMAP.md`.
