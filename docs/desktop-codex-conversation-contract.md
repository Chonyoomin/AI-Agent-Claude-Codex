# Desktop Codex Conversation And Intervention Contract

## Status

Phase 10AF defines this contract. No desktop conversation runtime,
chat/intervention panel, request queue, reply cache, background
watcher, MCP-side "Codex chat" endpoint, or hidden UI-only
operator state plane ships in this slice. The contract below
specifies the FIRST desktop surface that lets the operator route
an operator-to-Codex request from inside the shipped desktop app
without inventing a competing control plane, a hidden request
queue, or a UI-only reply store. It pins the closed intent
vocabulary, the canonical-artifact routing rules, the advisory-
vs-canonical mirror rule, the Claude-owned-vs-Codex-owned follow-
up rule, the refusal cases, the approval gates, and the audit
expectations that the future Phase 10AG runtime slice MUST
preserve. Implementation of the desktop conversation runtime is
deferred to:

- Phase 10AG: Desktop Codex Conversation And Intervention Runtime
  Initial Slice (the first shipped desktop panel that composes
  operator-to-Codex requests, materialises them into the shipped
  canonical artifacts per this contract, surfaces Codex responses
  as advisory mirrors of the shipped canonical artifacts, and
  refuses fail-closed on every boundary this contract enumerates).

## Scope

This contract covers ONLY the operator-to-Codex request/reply
routing surface exposed inside the shipped desktop app. It
answers:

- which operator intents are in scope for a desktop-side
  Codex-request surface (a closed vocabulary)
- how a desktop-composed request maps back to the shipped
  canonical artifacts rather than to a UI-only queue
- how the surface distinguishes an advisory request composition
  (an in-progress operator draft) from a canonical mutation of a
  shipped artifact
- how the surface distinguishes a Claude-owned follow-up (an
  implementation prompt handoff) from a Codex-owned follow-up
  (a review, classification, or planning update)
- which refusal, approval, and audit boundaries the future
  runtime MUST preserve
- what MUST NOT be added under the banner of "Codex conversation"
  (a second orchestrator, a hidden UI-only reply cache, a
  desktop-side identity token store, an autonomous chat driver)

Everything outside that request/reply routing surface is out of
scope. In particular:

- the actual Tkinter panel / widget layout / message-list
  scroll-view is a Phase 10AG implementation concern
- any MCP-side "codex" transport, network endpoint, WebSocket,
  server-sent-event stream, or persistent socket connection is
  out of scope for Phase 10AF AND for Phase 10AG (Codex remains
  invoked via the shipped local adapter contract, not via a new
  server)
- any "autonomous chat mode" where the desktop panel decides
  when to invoke Codex without operator approval is out of scope
  for both slices

## Distinction From Shipped Artifacts And Surfaces

The shipped repository already ships the following canonical
artifacts and shipped surfaces that this contract MUST route
through rather than duplicate:

- `.agent-loop/claude-prompt.md` (Claude-owned implementation
  prompt handoff, written by the shipped Phase 4C activator +
  Phase 5F post-review prompt bootstrap surface)
- `.agent-loop/fix-prompt.md` (Codex-authored repair prompt for
  Claude, written by the shipped Codex review path)
- `.agent-loop/codex-review.md` (Codex-authored review verdict +
  findings, written by the shipped Codex reviewer)
- `.agent-loop/claude-summary.md` (Claude-authored implementation
  summary, written by the shipped Claude implementer)
- `.agent-loop/current-phase.md`, `.agent-loop/current-task.md`,
  `.agent-loop/phase-plan.md`, `TASK.md`, `ROADMAP.md` (planning
  artifacts owned by Codex per the shipped Phase 3A / 4A
  contracts)
- `.agent-loop/loop-state.json` (orchestrator-owned runtime
  state per Phase 3A)
- `.agent-loop/orchestrator.log` (orchestrator-owned audit trail
  per Phase 3A)
- the shipped Phase 10L desktop-app contract at
  `docs/desktop-app-contract.md`
  that pins the desktop shell as a read-only reporter over the
  shipped Python runtime
- the shipped Phase 10O MCP integration contract at
  `docs/mcp-integration-contract.md`
  that pins the closed MCP tool categories and refusal cases
- the shipped Phase 10AB (Controlled Concurrent Operation
  Contract), Phase 10AC (Overlap-Safe Detection), and
  Phase 10AD (Codex-Owned Concurrent Work) controlled-
  concurrency contract at
  `docs/controlled-concurrency-contract.md`
  that pins per-artifact `owner_role` and refuses fail-closed
  on role violation

The Phase 10AF surface is a ROUTING SURFACE over those shipped
artifacts. It NEVER introduces a competing state store, NEVER
mirrors a canonical artifact into a hidden UI-only cache, and
NEVER lets the desktop panel write a canonical artifact under a
role it does not already own per the shipped Phase 10AB map.

## In-Scope Operator Intent Vocabulary

The desktop Codex conversation surface MUST expose a CLOSED set
of operator intents. The Phase 10AF closed vocabulary is:

- `request_codex_review` - ask Codex to review the current
  branch / commit / uncommitted diff and produce a
  `codex-review.md` verdict + findings. Materialises through the
  shipped Codex review path (`AGENT_LOOP_CODEX_CMD` per the
  local-adapter contract or the shipped ManualHandoff adapter).
- `request_codex_issue_classification` - ask Codex to
  classify a set of issues (from a previous review, a linked
  GitHub issue, or a Claude summary block) by owner
  (Claude-owned, Codex-owned, human-owned) and by category
  (planning, review, ownership routing, canonical-artifact
  mutation, external dependency). Codex returns an advisory
  classification that the operator can act on; the classification
  itself is NEVER a canonical artifact write.
- `request_codex_roadmap_update` - ask Codex to update
  `ROADMAP.md` / `TASK.md` / `.agent-loop/phase-plan.md` /
  `.agent-loop/current-phase.md` / `.agent-loop/current-task.md`
  to reflect a planned scope change. Codex remains the sole
  writer of those artifacts; the desktop surface COMPOSES the
  request but Codex EXECUTES the write through the shipped
  planning path.
- `request_codex_targeted_repo_change` - ask Codex to make a
  targeted change to a Codex-owned repo file (e.g. an
  orchestrator-owned Phase 3A helper, a Codex-review-authored
  `codex-review.md` block, a planning artifact update). Codex
  evaluates the request, refuses out-of-scope changes, and
  performs the change through the shipped Codex path if in
  scope.
- `request_codex_claude_prompt_authorship` - ask Codex to
  author a fresh `.agent-loop/claude-prompt.md` for a new phase
  or to update an existing one to reflect a scope refinement.
  This materialises through the shipped Phase 4C activator +
  Phase 5F post-review prompt bootstrap surface (Codex writes;
  Claude reads).
- `request_codex_fix_prompt_authorship` - ask Codex to author
  or update `.agent-loop/fix-prompt.md` in response to a Claude
  summary or a specific finding set. Materialises through the
  shipped Codex review path.

The vocabulary is CLOSED. A desktop-side intent outside this set
MUST be refused fail-closed by the future runtime; the operator
sees an explicit refusal naming the closed vocabulary rather
than a silent no-op.

## Routing To Canonical Artifacts

Every desktop-composed request MUST materialise through one of
the shipped canonical artifacts before Codex sees it. The
Phase 10AF closed routing map is:

- `request_codex_review` -> Codex invocation through the shipped
  `AGENT_LOOP_CODEX_CMD` local adapter (per
  `docs/local-adapter-contract.md`)
  OR through the shipped ManualHandoff adapter.
  Input: the shipped diff / evidence bundle (already written by
  `scripts/run_checks.sh`) plus the shipped `claude-summary.md`.
  Output: Codex writes `.agent-loop/codex-review.md` per the
  shipped review contract.
- `request_codex_issue_classification` -> Codex invocation
  through the same adapter. Input: an operator-composed message
  referencing the shipped `codex-review.md` findings or an
  external issue link. Output: Codex writes an advisory
  classification into the SAME `codex-review.md` (or an
  operator-approved dedicated advisory field within it); the
  classification is surfaced in the desktop panel as an
  advisory mirror of that canonical artifact.
- `request_codex_roadmap_update` -> Codex invocation. Input: an
  operator-composed message describing the intended scope
  change. Output: Codex writes / updates `ROADMAP.md`,
  `TASK.md`, `.agent-loop/phase-plan.md`, `.agent-loop/current-
  phase.md`, or `.agent-loop/current-task.md` per the shipped
  Phase 3A / 4A contracts. The desktop panel NEVER writes any
  of these files directly.
- `request_codex_targeted_repo_change` -> Codex invocation.
  Input: an operator-composed message naming the target file
  and the intended change. Output: Codex either refuses (if the
  target is Claude-owned, orchestrator-owned, or out of scope)
  and writes the refusal into `.agent-loop/codex-review.md`, or
  performs the change through the shipped Codex path and audits
  the change into `.agent-loop/orchestrator.log` via the
  shipped audit surface.
- `request_codex_claude_prompt_authorship` -> Codex invocation.
  Output: Codex writes `.agent-loop/claude-prompt.md` per the
  shipped Phase 4C activator + Phase 5F post-review prompt
  bootstrap surface.
- `request_codex_fix_prompt_authorship` -> Codex invocation.
  Output: Codex writes `.agent-loop/fix-prompt.md` per the
  shipped Codex review path.

There is NO closed intent that lets the desktop panel write a
canonical artifact directly. Every canonical write MUST route
through the shipped adapter that already owns the write
(`AGENT_LOOP_CODEX_CMD` for Codex-owned artifacts,
`AGENT_LOOP_CLAUDE_CMD` for Claude-owned artifacts).

## Advisory-Vs-Canonical Mirror Rule

The desktop conversation panel WILL display two categories of
content that look alike but MUST be distinguished:

- ADVISORY REQUEST COMPOSITION (the in-progress operator draft;
  the message the operator has typed but not yet sent; the
  materialisation preview): held ONLY in-memory in the shipped
  Tkinter surface for the current session. NEVER persisted to
  disk. NEVER carried across sessions. NEVER visible to Codex
  until the operator explicitly clicks "Send" and the surface
  materialises the request through the shipped adapter.

- CANONICAL RESPONSE MIRROR (the Codex response after it has
  landed in a shipped canonical artifact): displayed as a
  READ-ONLY mirror of the on-disk file's current contents. The
  desktop panel MUST refresh the mirror per the shipped Phase
  10L polling cadence rules (`docs/desktop-app-contract.md`).
  The on-disk file is the source of truth; the desktop mirror
  is advisory. Every mirror line MUST carry either a
  `[canonical mirror]` attribution tag naming the source file
  (matching the shipped Phase 10K / 10L convention) or a
  `[codex-conversation-advisory]` tag naming the in-progress
  operator draft.

The desktop panel MUST NOT introduce a THIRD category (e.g. a
"local edit that Codex has not yet seen") that shadows either.
If the operator wants to keep a draft across sessions they use
the OS's native editor to save it to disk under a name that is
NOT a shipped canonical artifact.

## Claude-Owned Vs Codex-Owned Follow-Up

Every operator intent in the closed vocabulary above is a
Codex-owned intent (Codex is the actor). The desktop panel
NEVER lets the operator "ask Claude" from this surface. Claude
implementation work remains a `.agent-loop/claude-prompt.md` /
`.agent-loop/fix-prompt.md` handoff, driven by the shipped
Phase 4C / Phase 5F path.

When a Codex response indicates that follow-up implementation is
needed, that follow-up MUST become:

- Codex-owned follow-up if the target artifact is Codex-owned
  per the shipped Phase 10AB `_DESKTOP_CONCURRENCY_OWNERSHIP_MAP`
  (planning artifacts, `codex-review.md`, `fix-prompt.md`,
  `claude-prompt.md`, roadmap docs, `TASK.md`). Codex performs
  the write through the shipped adapter.
- Claude-owned follow-up if the target artifact is Claude-owned
  (`claude-summary.md`, implementation source, tests). In this
  case Codex authors a `.agent-loop/claude-prompt.md` or
  `.agent-loop/fix-prompt.md` naming the follow-up scope, and
  Claude reads that shipped artifact in the next cycle. The
  desktop panel NEVER dispatches Claude directly from this
  surface.

If the target artifact is orchestrator-owned per the shipped
Phase 10AB map (`.agent-loop/loop-state.json`, `.agent-loop/
orchestrator.log`, `.agent-loop/git-diff.patch`, `.agent-loop/
*.log` evidence artifacts), the desktop panel MUST refuse the
request fail-closed. The orchestrator remains the sole writer
of those artifacts.

## Refusal Behavior

The future Phase 10AG runtime MUST refuse fail-closed on every
one of the following conditions, surfacing an explicit refusal
line naming the shipped rule that was violated. No conditional
"maybe" refusals, no silent no-ops:

- intent outside the closed
  `PHASE_10AF_DESKTOP_CODEX_CONVERSATION_INTENTS` vocabulary
- operator-composed request naming a target file that is
  orchestrator-owned per the shipped Phase 10AB map (any
  attempt to route through the desktop surface into loop-state
  or orchestrator.log is refused)
- operator-composed request naming a target file that is
  Claude-owned per the shipped Phase 10AB map when the intent
  is `request_codex_targeted_repo_change` (Codex is not allowed
  to mutate Claude-owned implementation source; Claude follow-
  up MUST route through a fresh `claude-prompt.md` /
  `fix-prompt.md`)
- attempt to dispatch a Codex request when the shipped
  Phase 10AC overlap-safe detection aggregate is in
  `refused_pending_recovery` (the shipped concurrency gate
  fires first)
- attempt to dispatch a Codex request when the shipped Phase 5C
  strict-mode gate is unsatisfied (the shipped strict-mode
  pause fires first)
- attempt to auto-fill an operator identity (`attached_by`,
  `bootstrapped_by`, `accepted_by`, `codex_conversation_
  operator`) from OS state, environment variables, browser
  session, or any packaging-time identity source (the shipped
  no-auto-fill boundary is preserved verbatim)
- attempt to send a request while a prior Codex invocation is
  still in flight (the shipped local-adapter contract requires
  serial invocation; a per-session in-flight flag MUST refuse
  a second dispatch until the first artifact write has
  landed).
- attempt to persist the operator-in-progress draft to disk
  under a canonical-artifact name (the advisory-only rule is
  a hard invariant)
- attempt to hide a Codex refusal reason from the operator (the
  refusal MUST be surfaced verbatim from the canonical
  artifact where Codex wrote it; the desktop panel is a
  mirror, not a filter)

Every refusal MUST include the intent id it refused (from the
closed vocabulary), the shipped rule that was violated (with a
docs anchor citation matching the Phase 10AE auditability
convention), and the closed refusal category the future runtime
MUST expose (e.g.
`refused_intent_outside_closed_vocabulary`,
`refused_orchestrator_owned_target`,
`refused_claude_owned_target`,
`refused_overlap_unsafe`,
`refused_strict_mode_gate`,
`refused_auto_fill_operator_identity`,
`refused_in_flight_codex_invocation`,
`refused_advisory_persistence`).

## Approval Gates

The desktop Codex conversation surface MUST preserve every
shipped approval gate verbatim:

- Phase 5A/5C/5D approval-mode gating: a request MUST NOT
  dispatch when the shipped `review` gate is unsatisfied. In
  `strict` mode the gate MUST fire an explicit pause with the
  operator's explicit resume required.
- Phase 4C activator + `APPROVED_FOR_ACTIVATION` human
  approval: a `request_codex_claude_prompt_authorship` for a
  new phase MUST route through the shipped Phase 4C activator
  path rather than short-circuiting.
- Phase 9G human acceptance gate: a request that would trigger
  a `record-final-acceptance` MUST route through the shipped
  Phase 9G path with the explicit `--accepted-by <NAME>`
  operator identity supplied per-invocation (no auto-fill).
- Phase 10U MCP action guardrail per-tool approval policy: if
  a Codex request would trigger an MCP mutation (a
  `deferred_mutating` MCP tool category per the shipped
  Phase 10O contract), the shipped Phase 10U per-tool approval
  policy MUST fire first.
- Phase 5F post-review prompt bootstrap: a Codex-authored
  `claude-prompt.md` MUST route through the shipped Phase 5F
  post-review prompt bootstrap surface so the shipped Claude
  reader picks it up on the next cycle boundary.

Any request that bypasses an approval gate is REFUSED
fail-closed with the closed refusal category
`refused_approval_gate_bypass`.

## Audit Expectations

Every Codex invocation triggered from the desktop conversation
surface MUST audit through the shipped surfaces:

- `.agent-loop/orchestrator.log` receives an audit line per the
  shipped Phase 3A orchestrator contract naming the intent id,
  the target artifact, the operator identity (explicit,
  operator-supplied), the closed refusal category if refused,
  and the epoch-second timestamp.
- `.agent-loop/codex-review.md` (for `request_codex_review` and
  `request_codex_issue_classification` intents) is written by
  Codex through the shipped review path. The desktop panel
  displays the file as an advisory mirror.
- `.agent-loop/claude-prompt.md` / `.agent-loop/fix-prompt.md`
  (for the corresponding intents) is written by Codex through
  the shipped Phase 4C / Phase 5F path.
- `ROADMAP.md` / `TASK.md` / `.agent-loop/phase-plan.md` /
  `.agent-loop/current-phase.md` / `.agent-loop/current-
  task.md` (for `request_codex_roadmap_update`) is written by
  Codex through the shipped planning path.

The desktop panel MUST NOT introduce a separate audit surface
(a "conversation history" file, a per-session log, a UI-only
event stream). The shipped `.agent-loop/orchestrator.log` +
canonical artifacts are the sole audit sources of truth.

## Source-Of-Truth Preservation (No Hidden UI Store)

The Phase 10AF contract preserves the shipped source-of-truth
model verbatim. Specifically the future Phase 10AG runtime
MUST NOT introduce ANY of the following:

- a UI-only "conversation history" JSON file, SQLite database,
  MessagePack blob, or any other persistent store
- a session state file that shadows `.agent-loop/loop-state.
  json` for the desktop panel's own state
- a "draft" file that mirrors an in-progress operator message
  to disk
- a "pending Codex responses" queue file that buffers responses
  before they land in a canonical artifact
- a browser-session identity token cache, an MCP-side session
  cookie, or any cross-session identity persistence
- a "recents" list of previous requests / responses (the
  operator uses `git log`, the shipped `phase-plan.md`, or the
  OS's native editor to review history)
- an autofill / suggestion engine that derives operator
  identity from OS state (`$USER`, `whoami`, browser session,
  packaging-time identity)
- a background watcher / polling thread beyond the shipped
  Phase 10L / 10M polling cadence rules

The desktop panel's per-session in-memory state (the current
draft, the current in-flight-flag, the current advisory
classification) is CLEARED on window close and NEVER persisted.
On next session the operator sees an empty panel and MUST
compose fresh.

## Ownership Boundary Preservation

The Phase 10AF surface preserves every shipped ownership
boundary verbatim. Specifically:

- Codex remains the SOLE writer of planning artifacts
  (`ROADMAP.md`, `TASK.md`, `.agent-loop/phase-plan.md`,
  `.agent-loop/current-phase.md`, `.agent-loop/current-task.
  md`), `codex-review.md`, `fix-prompt.md`, and
  `claude-prompt.md` per the shipped Phase 3A / 4A / 10AB
  contracts. The desktop panel NEVER writes these directly.
- Claude remains the SOLE writer of `claude-summary.md` and
  the shipped Claude-owned implementation surface (source,
  tests, non-planning docs). A Codex-side request to modify
  Claude-owned source MUST refuse fail-closed with
  `refused_claude_owned_target` and instead author a
  `.agent-loop/claude-prompt.md` or `.agent-loop/fix-prompt.
  md` naming the change so Claude picks it up on the next
  cycle.
- The orchestrator remains the SOLE writer of `loop-state.
  json`, `orchestrator.log`, and the shipped evidence
  artifacts. Any desktop-side request routed toward these is
  refused fail-closed with `refused_orchestrator_owned_
  target`.
- Human-owned decisions (final acceptance,
  `APPROVED_FOR_ACTIVATION` token, `APPROVED_FOR_HUMAN_
  REVIEW` verdict) remain human-authored. The desktop panel
  NEVER auto-generates any of them.

## Dependencies On Phase 10AG (Runtime Implementation)

Phase 10AG will implement the runtime that satisfies this
contract. The Phase 10AG runtime is expected to add:

- a closed intent-vocabulary constant matching the six intents
  named above
- a pure request-composition validator (Tk-free, unit-
  testable) that refuses fail-closed on any of the enumerated
  refusal categories
- a thin adapter wrapper that delegates verbatim to the shipped
  `AGENT_LOOP_CODEX_CMD` per the local-adapter contract so
  every Phase 10C / 10D / 10E refusal path fires unchanged
- a Tk panel that renders the closed intent vocabulary, the
  current draft, the in-flight-flag, and the canonical-mirror
  response, all following the Phase 10L polling / attribution-
  tag conventions
- an in-flight-flag that refuses a second Codex dispatch while
  a prior invocation has not yet landed in a canonical
  artifact
- a per-invocation operator-identity Entry that requires
  explicit typing (no auto-fill from OS state) per the shipped
  no-auto-fill identity boundary

Phase 10AG will NOT add: a background chat driver, an
autonomous conversation loop, a UI-only state store, a network
transport, or an MCP-side "codex chat" endpoint. This is a
hard boundary; a Phase 10AG PR that includes any of those is
`NEEDS_FIXES`.

## Out Of Scope For Phase 10AF

The Phase 10AF slice is contract-definition only. The following
are explicitly out of scope:

- any Tk panel implementation, widget layout, or `_launch_
  desktop_app_window(...)` addition
- any new library-callable control (the shipped Phase 10I
  three-control cap is preserved verbatim)
- any new canonical artifact (the shipped canonical set is
  preserved verbatim; no `codex-conversation-history.md` or
  similar file)
- any change to the shipped Phase 2A / 3A / 4A / 5A / 6M /
  10L / 10M / 10O / 10AB / 10AC / 10AD contracts
- any Git automation
- any framework-side integration (crewai / langgraph /
  langchain remain evaluation-only per the shipped Phase 10AE
  contract)
- any change to the shipped `EXTERNAL_TARGET_APPROVAL_MODES`
  closed enum, the shipped `PRIMARY_DESKTOP_BOOTSTRAP_FIELD_
  NAMES` closed enum, or the shipped Phase 10AB
  `_DESKTOP_CONCURRENCY_OWNERSHIP_MAP` closed map
