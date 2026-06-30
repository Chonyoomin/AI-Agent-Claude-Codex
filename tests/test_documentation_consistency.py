"""Focused tests for the Phase 8A architecture / usage documentation.

Scope of this suite (Phase 8A, narrow):
- The two new Phase 8A docs (`docs/architecture.md`, `docs/usage.md`)
  exist at the repo root, are ASCII-only, and are non-empty.
- Every `python scripts/agent_loop.py <subcommand>` invocation named
  in either doc resolves to a real `agent_loop.HANDLERS` entry; the
  docs never claim a subcommand the shipped CLI does not expose.
- The artifact-ownership section of `docs/architecture.md` names every
  orchestrator-owned artifact called out by `CLAUDE.md` (load-bearing
  ownership contract; a docs-only regression would silently mislead a
  new operator about which artifacts Claude may write).
- The architecture doc names the load-bearing concepts the shipped
  system actually implements (approval modes, halt families, runtime
  adapters, memory categories) so the doc cannot silently drift into
  describing only future-roadmap behavior.
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import agent_loop  # noqa: E402 - sys.path is set above


REPO_ROOT = HERE.parent
README_PATH = REPO_ROOT / "README.md"
ARCHITECTURE_PATH = REPO_ROOT / "docs" / "architecture.md"
USAGE_PATH = REPO_ROOT / "docs" / "usage.md"
PHASE_8A_DOC_PATHS = (ARCHITECTURE_PATH, USAGE_PATH)

# Phase 8B operator playbooks (added by the Safety, Approval, And
# Operational Playbooks slice).
SAFETY_RULES_PATH = REPO_ROOT / "docs" / "safety-rules.md"
APPROVAL_MODES_PATH = REPO_ROOT / "docs" / "approval-modes.md"
HALT_AND_RECOVERY_PATH = REPO_ROOT / "docs" / "halt-and-recovery.md"
PHASE_8B_DOC_PATHS = (
    SAFETY_RULES_PATH, APPROVAL_MODES_PATH, HALT_AND_RECOVERY_PATH,
)

# Phase 9A autonomy contract doc (Autonomous Mode Contract And Safety
# Policy slice; documentation-only contract for the future Phase 9
# fully autonomous PRD-to-product mode).
AUTONOMY_CONTRACT_PATH = REPO_ROOT / "docs" / "autonomy-contract.md"
PHASE_9A_DOC_PATHS = (AUTONOMY_CONTRACT_PATH,)

# Phase 10A external workspace controller contract doc (External
# Workspace Controller Contract slice; documentation-only contract for
# the future Phase 10 external-workspace runtime that lets the
# controller repository safely target a separate workspace or
# repository).
EXTERNAL_WORKSPACE_CONTRACT_PATH = (
    REPO_ROOT / "docs" / "external-workspace-contract.md"
)
PHASE_10A_DOC_PATHS = (EXTERNAL_WORKSPACE_CONTRACT_PATH,)

# Phase 10B external target attach record contract doc (External
# Target Attach Record Contract slice; documentation-only contract
# for the controller-owned attach-record schema future Phase 10D
# attach/detach runtime slices must persist).
ATTACH_RECORD_CONTRACT_PATH = (
    REPO_ROOT / "docs" / "external-target-attach-record-contract.md"
)
PHASE_10B_DOC_PATHS = (ATTACH_RECORD_CONTRACT_PATH,)

# Phase 10C external workspace bootstrap contract doc (External
# Workspace Bootstrap Contract slice; documentation-only contract
# for the target-side `.agent-loop` initialization surface future
# Phase 10D attach + Phase 10E bootstrap runtime slices must follow).
BOOTSTRAP_CONTRACT_PATH = (
    REPO_ROOT / "docs" / "external-workspace-bootstrap-contract.md"
)
PHASE_10C_DOC_PATHS = (BOOTSTRAP_CONTRACT_PATH,)

# Phase 10G external UI contract doc (Minimal External UI Contract
# slice; documentation-only contract for the future minimal external
# operator UI surface, pinning the read-only artifact set, the
# advisory-vs-canonical mirror rule, the CLI-only operation list, and
# the safety/approval boundaries the UI must preserve).
EXTERNAL_UI_CONTRACT_PATH = (
    REPO_ROOT / "docs" / "external-ui-contract.md"
)
PHASE_10G_DOC_PATHS = (EXTERNAL_UI_CONTRACT_PATH,)
# Phase 10J - Artifact Dashboard Contract documentation-only slice.
# Defines the contract a future external artifact dashboard runtime
# (Phase 10K) must satisfy, layered on top of the binding Phase 10G
# UI contract.
ARTIFACT_DASHBOARD_CONTRACT_PATH = (
    REPO_ROOT / "docs" / "artifact-dashboard-contract.md"
)
PHASE_10J_DOC_PATHS = (ARTIFACT_DASHBOARD_CONTRACT_PATH,)
# Phase 10L - Desktop App Shell Contract documentation-only slice.
# Defines the contract a future native desktop-app shell runtime
# (Phase 10M) must satisfy, layered on top of the binding Phase 10G
# UI contract and the Phase 10J dashboard contract.
DESKTOP_APP_CONTRACT_PATH = (
    REPO_ROOT / "docs" / "desktop-app-contract.md"
)
PHASE_10L_DOC_PATHS = (DESKTOP_APP_CONTRACT_PATH,)
# Phase 10O - MCP Integration Contract And Safe Tool Boundary
# documentation-only slice. Defines how a future MCP runtime
# (Phase 10T read-only assistance; Phase 10U+ mutation-capable
# actions) MAY consume MCP tools without bypassing the shipped
# evidence-review / approval-gate / ownership-boundary invariants.
MCP_INTEGRATION_CONTRACT_PATH = (
    REPO_ROOT / "docs" / "mcp-integration-contract.md"
)
PHASE_10O_DOC_PATHS = (MCP_INTEGRATION_CONTRACT_PATH,)
# Phase 10S - MCP Server Selection UX Contract documentation-only
# slice. Defines how the desktop app MUST present available MCP
# servers, permission classes, read-only vs deferred-mutating
# capability labels, per-server safety copy, and operator approval
# requirements before MCP enablement becomes user-facing. Layered
# on top of the Phase 10O integration contract.
MCP_SERVER_SELECTION_UX_CONTRACT_PATH = (
    REPO_ROOT / "docs" / "mcp-server-selection-ux-contract.md"
)
PHASE_10S_DOC_PATHS = (MCP_SERVER_SELECTION_UX_CONTRACT_PATH,)
ALL_OPERATOR_DOC_PATHS = (
    PHASE_8A_DOC_PATHS
    + PHASE_8B_DOC_PATHS
    + PHASE_9A_DOC_PATHS
    + PHASE_10A_DOC_PATHS
    + PHASE_10B_DOC_PATHS
    + PHASE_10C_DOC_PATHS
    + PHASE_10G_DOC_PATHS
    + PHASE_10J_DOC_PATHS
    + PHASE_10L_DOC_PATHS
    + PHASE_10O_DOC_PATHS
    + PHASE_10S_DOC_PATHS
)

# Regex for `python scripts/agent_loop.py <subcommand>` mentions in the
# docs, with the subcommand captured. Matches either inside backticks
# or in plain prose. The subcommand grammar matches the shipped CLI:
# lowercase ASCII letters and hyphens only.
AGENT_LOOP_INVOCATION_RE = re.compile(
    r"python scripts/agent_loop\.py ([a-z][a-z0-9-]*)"
)

# Orchestrator-owned artifacts the architecture doc must name to make
# the ownership boundary clear (mirror of the list in CLAUDE.md's
# "Orchestrator- or script-owned artifacts" section).
ORCHESTRATOR_OWNED_ARTIFACT_PATHS = (
    ".agent-loop/loop-state.json",
    ".agent-loop/orchestrator.log",
    ".agent-loop/git-diff.patch",
    ".agent-loop/git-status.log",
    ".agent-loop/test-output.log",
    ".agent-loop/lint-output.log",
    ".agent-loop/typecheck-output.log",
    ".agent-loop/build-output.log",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class DocsExistAndAreWellFormedTests(unittest.TestCase):

    def test_architecture_doc_exists_and_non_empty(self) -> None:
        self.assertTrue(
            ARCHITECTURE_PATH.is_file(),
            f"Expected Phase 8A architecture doc at "
            f"{ARCHITECTURE_PATH}",
        )
        self.assertGreater(ARCHITECTURE_PATH.stat().st_size, 0)

    def test_usage_doc_exists_and_non_empty(self) -> None:
        self.assertTrue(
            USAGE_PATH.is_file(),
            f"Expected Phase 8A usage doc at {USAGE_PATH}",
        )
        self.assertGreater(USAGE_PATH.stat().st_size, 0)

    def test_docs_are_ascii_only(self) -> None:
        for path in PHASE_8A_DOC_PATHS:
            text = _read(path)
            for i, line in enumerate(text.splitlines(), 1):
                for ch in line:
                    self.assertLessEqual(
                        ord(ch), 127,
                        f"non-ASCII character {ch!r} in {path.name} "
                        f"line {i}",
                    )


class DocsOnlyClaimShippedCliSurfacesTests(unittest.TestCase):

    def _named_subcommands(self, path: Path) -> set:
        text = _read(path)
        return set(AGENT_LOOP_INVOCATION_RE.findall(text))

    def test_architecture_doc_only_names_real_subcommands(self) -> None:
        named = self._named_subcommands(ARCHITECTURE_PATH)
        # Architecture doc may or may not name every subcommand by
        # invocation; the load-bearing assertion is "any subcommand it
        # DOES name must exist".
        unknown = named - set(agent_loop.HANDLERS)
        self.assertEqual(
            unknown, set(),
            f"docs/architecture.md references unknown subcommands: "
            f"{sorted(unknown)}",
        )

    def test_usage_doc_only_names_real_subcommands(self) -> None:
        named = self._named_subcommands(USAGE_PATH)
        unknown = named - set(agent_loop.HANDLERS)
        self.assertEqual(
            unknown, set(),
            f"docs/usage.md references unknown subcommands: "
            f"{sorted(unknown)}",
        )

    def test_usage_doc_covers_the_load_bearing_operator_subcommands(
        self,
    ) -> None:
        # The usage doc is the "where do I start" entry point; it must
        # name the load-bearing operator subcommands by invocation so a
        # clean-clone reader can act without cross-referencing the
        # CLI's --help output.
        named = self._named_subcommands(USAGE_PATH)
        required = {
            "status", "run", "resume", "auto-continue",
            "inspect-artifacts", "plan", "activate",
            "set-runtime-config",
        }
        missing = required - named
        self.assertEqual(
            missing, set(),
            f"docs/usage.md does not name these load-bearing "
            f"operator subcommands by invocation: {sorted(missing)}",
        )


class ArchitectureDocOwnershipBoundaryTests(unittest.TestCase):

    def setUp(self) -> None:
        self.text = _read(ARCHITECTURE_PATH)

    def test_names_every_orchestrator_owned_artifact(self) -> None:
        # The CLAUDE.md ownership list is the load-bearing contract; if
        # the architecture doc drops one of these, a new operator could
        # be misled about which artifacts Claude may write.
        for rel_path in ORCHESTRATOR_OWNED_ARTIFACT_PATHS:
            self.assertIn(
                rel_path, self.text,
                f"docs/architecture.md does not name orchestrator-"
                f"owned artifact {rel_path!r}",
            )

    def test_names_the_three_approval_modes(self) -> None:
        for mode in ("review", "strict", "autonomous"):
            self.assertIn(
                f"`{mode}`", self.text,
                f"docs/architecture.md does not name approval mode "
                f"{mode!r}",
            )

    def test_names_the_three_codex_verdicts(self) -> None:
        for verdict in (
            "APPROVED_FOR_HUMAN_REVIEW",
            "NEEDS_FIXES",
            "FAILED_REQUIRES_HUMAN",
        ):
            self.assertIn(
                verdict, self.text,
                f"docs/architecture.md does not name Codex verdict "
                f"{verdict!r}",
            )

    def test_names_the_load_bearing_runtime_adapter_ids(self) -> None:
        # The default 'local' adapter and the opt-in 'langgraph' mirror
        # are the only shipped runtime ids; both must be discoverable
        # from the architecture doc.
        for runtime in agent_loop.RUNTIME_ADAPTERS_SUPPORTED:
            self.assertIn(
                runtime, self.text,
                f"docs/architecture.md does not name shipped runtime "
                f"adapter {runtime!r}",
            )

    def test_names_the_load_bearing_memory_categories(self) -> None:
        for category in (
            "decision", "failure", "preference",
            "summary", "checkpoint",
        ):
            self.assertIn(
                category, self.text,
                f"docs/architecture.md does not name memory category "
                f"{category!r}",
            )

    def test_names_the_strict_mode_gate_vocabulary(self) -> None:
        # Strict-mode gates are part of the operator-visible halt
        # vocabulary; the architecture doc must name them so the
        # `status` recovery hints are interpretable.
        for halt in (
            "halted_awaiting_human_pre_claude_prompt",
            "halted_awaiting_human_pre_fix_prompt",
            "halted_awaiting_human_pre_codex_review_normal",
            "halted_awaiting_human_pre_codex_review_fix",
        ):
            self.assertIn(
                halt, self.text,
                f"docs/architecture.md does not name strict-mode "
                f"halt {halt!r}",
            )


class DocsDoNotPromiseFutureBehaviorTests(unittest.TestCase):
    """The Phase 8A prompt forbids documenting unshipped behavior.

    These assertions are defense-in-depth: a future docs edit that
    silently promotes a roadmap feature into present-tense product
    behavior would trip them. The list of forbidden present-tense
    promises tracks the unshipped Phase 9 / Phase 10 scope in
    `ROADMAP.md`.
    """

    def test_docs_do_not_claim_autonomous_prd_to_product_mode(
        self,
    ) -> None:
        # Phase 9 (Fully Autonomous PRD-To-Product Mode) is roadmap
        # only. The docs may MENTION it as roadmap context, but must
        # not present it as a current shipped behavior.
        for path in PHASE_8A_DOC_PATHS:
            text = _read(path)
            forbidden_present_tense = (
                # "ships fully autonomous PRD-to-product execution"
                "ships fully autonomous PRD",
                # "is a fully autonomous PRD-to-product system"
                "is a fully autonomous PRD",
            )
            for fragment in forbidden_present_tense:
                self.assertNotIn(
                    fragment, text,
                    f"{path.name} promises unshipped Phase 9 "
                    f"behavior via {fragment!r}",
                )

    def test_docs_do_not_claim_mcp_or_external_ui_support(self) -> None:
        # MCP support and external UI are roadmap-only per ROADMAP.md.
        for path in PHASE_8A_DOC_PATHS:
            text = _read(path)
            # The docs may reference these as future / roadmap items,
            # but must not present them as shipped capabilities. We
            # accept any mention adjacent to "roadmap", "future",
            # "deferred", or "not implemented"; reject a bare claim.
            for keyword in ("MCP", "external UI"):
                if keyword in text:
                    # If the keyword appears, it must appear in a
                    # context that disclaims current shipping.
                    self._assert_disclaim_context(path, text, keyword)

    def _assert_disclaim_context(
        self, path: Path, text: str, keyword: str,
    ) -> None:
        # Look at a window around the keyword and require at least one
        # disclaiming term. The window size is generous so a sentence-
        # adjacent disclaimer counts.
        disclaim_terms = (
            "roadmap", "future", "deferred", "not implemented",
            "not yet", "future-roadmap", "later phase",
        )
        idx = text.find(keyword)
        window = text[max(0, idx - 240): idx + 240]
        if not any(t in window for t in disclaim_terms):
            self.fail(
                f"{path.name} mentions {keyword!r} without a "
                f"disclaiming context (roadmap / future / deferred / "
                f"not implemented); a new operator could read this "
                f"as a current shipped capability"
            )


class DocsDescribeStrictModeAccuratelyTests(unittest.TestCase):
    """Phase 8A fix: the architecture doc previously said strict mode
    adds four human checkpoints; the shipped Phase 5C contract defines
    three gates (`pre_claude_prompt`, `pre_fix_prompt`,
    `pre_codex_review`) with two halt-status flavors for the
    `pre_codex_review` gate so resume can route correctly. These tests
    pin the corrected wording.
    """

    def setUp(self) -> None:
        self.text = _read(ARCHITECTURE_PATH)

    def test_strict_mode_section_does_not_claim_four_checkpoints(
        self,
    ) -> None:
        # The shipped Phase 5C contract defines three gates, not four.
        # Catching the literal regression phrase keeps the architecture
        # doc honest if someone re-flattens the two halt flavors into a
        # "four gates" claim.
        self.assertNotIn(
            "four human checkpoints", self.text,
            "docs/architecture.md claims strict mode adds four human "
            "checkpoints; the shipped Phase 5C contract defines three "
            "gates with two halt-status flavors on pre_codex_review",
        )
        self.assertNotIn(
            "four strict gates", self.text,
            "docs/architecture.md references 'four strict gates'; the "
            "shipped contract defines three gates (one of which has "
            "two halt-status flavors)",
        )

    def test_strict_mode_section_names_three_gates(self) -> None:
        self.assertIn(
            "three human checkpoints", self.text,
            "docs/architecture.md does not state the strict-mode gate "
            "count matches the shipped Phase 5C contract (three "
            "gates)",
        )
        # The three gate names must all appear.
        for gate in (
            "pre_claude_prompt",
            "pre_fix_prompt",
            "pre_codex_review",
        ):
            self.assertIn(
                f"`{gate}`", self.text,
                f"docs/architecture.md does not name strict-mode "
                f"gate {gate!r}",
            )

    def test_strict_mode_section_names_two_halt_flavors_for_pre_codex_review(
        self,
    ) -> None:
        # The pre_codex_review gate has two halt-status flavors so
        # resume can route to the normal vs fix continuation. This is
        # the load-bearing detail the original "four checkpoints"
        # claim was conflating.
        for halt in (
            "halted_awaiting_human_pre_codex_review_normal",
            "halted_awaiting_human_pre_codex_review_fix",
        ):
            self.assertIn(
                halt, self.text,
                f"docs/architecture.md does not name the "
                f"pre_codex_review halt-status flavor {halt!r}",
            )


class DocsDescribeCheckpointLayerAccuratelyTests(unittest.TestCase):
    """Phase 8A fix: the architecture doc previously said both
    token-exhaustion AND strict-mode gates write checkpoints under
    `.agent-loop/memory/checkpoint/`. Only token-exhaustion writes
    checkpoint artifacts; strict-mode halts resume by persisted halt
    status in `loop-state.json`. These tests pin the corrected wording.
    """

    def setUp(self) -> None:
        self.text = _read(ARCHITECTURE_PATH)

    def test_checkpoint_section_does_not_claim_strict_gates_write_checkpoints(
        self,
    ) -> None:
        # Catch the literal pre-fix phrasing AND a close paraphrase
        # ("strict-mode ... write[s] ... checkpoint[s]") so a future
        # rewording that re-introduces the bug also trips.
        forbidden_claims = (
            "Phase 5C strict-mode gates write\ncheckpoints",
            "Phase 5C strict-mode gates write checkpoints",
            "strict-mode gates write checkpoints",
        )
        for fragment in forbidden_claims:
            self.assertNotIn(
                fragment, self.text,
                f"docs/architecture.md claims strict-mode gates "
                f"write checkpoints via {fragment!r}; only "
                f"token-exhaustion writes checkpoint artifacts",
            )

    def test_checkpoint_section_states_strict_gates_use_persisted_status(
        self,
    ) -> None:
        # Positive assertion: the corrected wording must explain how
        # strict-mode halts actually resume (via persisted halt status
        # in loop-state, not via a strict-gate checkpoint write).
        self.assertIn(
            "do NOT write strict-gate checkpoint", self.text,
            "docs/architecture.md does not explicitly state that "
            "strict-mode gates do NOT write strict-gate checkpoint "
            "artifacts",
        )


class UsageDocHaltRecoveryWordingTests(unittest.TestCase):
    """Phase 8A fix: the usage doc previously claimed every halt
    persists a status that points at a specific recovery COMMAND, but
    `halted_failed_requires_human` and `halted_max_cycles_reached`
    require manual human/Codex intervention (the planner refuses to
    propose the next phase from those states). These tests pin the
    corrected wording.
    """

    def setUp(self) -> None:
        self.text = _read(USAGE_PATH)

    def test_safety_section_does_not_promise_a_recovery_command_for_every_halt(
        self,
    ) -> None:
        self.assertNotIn(
            "Every halt persists a status that points at a specific "
            "recovery\n  command",
            self.text,
            "docs/usage.md still promises a recovery command for "
            "every halt; halted_failed_requires_human and "
            "halted_max_cycles_reached require human/Codex "
            "intervention, not a CLI command",
        )
        self.assertNotIn(
            "Every halt persists a status that points at a specific "
            "recovery command",
            self.text,
        )

    def test_safety_section_names_the_human_required_terminal_halts(
        self,
    ) -> None:
        # The corrected wording must mention the two terminal halts
        # that require manual recovery, so an operator does not read
        # the safety section and expect a CLI command for them.
        for halt in (
            "halted_failed_requires_human",
            "halted_max_cycles_reached",
        ):
            self.assertIn(
                halt, self.text,
                f"docs/usage.md safety section does not name "
                f"human-required terminal halt {halt!r}",
            )

    def test_safety_section_notes_planner_refuses_from_terminal_halts(
        self,
    ) -> None:
        # The corrected wording must explain WHY there is no direct
        # CLI command for the human-required halts (the planner
        # refuses). Without that, an operator could think the doc is
        # incomplete.
        self.assertIn(
            "planner refuses", self.text,
            "docs/usage.md does not explain that the shipped planner "
            "refuses to propose the next phase from the human-"
            "required terminal halts",
        )


class Phase8BPlaybooksExistAndAreWellFormedTests(unittest.TestCase):
    """Phase 8B: the three operator playbooks (safety, approval modes,
    halt-and-recovery) ship as separate docs under `docs/`. These
    tests guard existence, non-emptiness, and ASCII purity for each.
    """

    def test_safety_rules_doc_exists_and_non_empty(self) -> None:
        self.assertTrue(
            SAFETY_RULES_PATH.is_file(),
            f"Expected Phase 8B safety doc at {SAFETY_RULES_PATH}",
        )
        self.assertGreater(SAFETY_RULES_PATH.stat().st_size, 0)

    def test_approval_modes_doc_exists_and_non_empty(self) -> None:
        self.assertTrue(
            APPROVAL_MODES_PATH.is_file(),
            f"Expected Phase 8B approval-modes doc at "
            f"{APPROVAL_MODES_PATH}",
        )
        self.assertGreater(APPROVAL_MODES_PATH.stat().st_size, 0)

    def test_halt_and_recovery_doc_exists_and_non_empty(self) -> None:
        self.assertTrue(
            HALT_AND_RECOVERY_PATH.is_file(),
            f"Expected Phase 8B halt/recovery doc at "
            f"{HALT_AND_RECOVERY_PATH}",
        )
        self.assertGreater(HALT_AND_RECOVERY_PATH.stat().st_size, 0)

    def test_phase_8b_docs_are_ascii_only(self) -> None:
        for path in PHASE_8B_DOC_PATHS:
            text = _read(path)
            for i, line in enumerate(text.splitlines(), 1):
                for ch in line:
                    self.assertLessEqual(
                        ord(ch), 127,
                        f"non-ASCII character {ch!r} in {path.name} "
                        f"line {i}",
                    )


class Phase8BPlaybooksOnlyClaimShippedCliSurfacesTests(unittest.TestCase):
    """Phase 8B: the same anti-drift guard from Phase 8A applies to
    each new playbook. Any `python scripts/agent_loop.py <subcommand>`
    mention must resolve to a real `agent_loop.HANDLERS` entry.
    """

    def test_safety_rules_only_names_real_subcommands(self) -> None:
        named = set(
            AGENT_LOOP_INVOCATION_RE.findall(_read(SAFETY_RULES_PATH))
        )
        unknown = named - set(agent_loop.HANDLERS)
        self.assertEqual(
            unknown, set(),
            f"docs/safety-rules.md references unknown subcommands: "
            f"{sorted(unknown)}",
        )

    def test_approval_modes_only_names_real_subcommands(self) -> None:
        named = set(
            AGENT_LOOP_INVOCATION_RE.findall(_read(APPROVAL_MODES_PATH))
        )
        unknown = named - set(agent_loop.HANDLERS)
        self.assertEqual(
            unknown, set(),
            f"docs/approval-modes.md references unknown subcommands: "
            f"{sorted(unknown)}",
        )

    def test_halt_and_recovery_only_names_real_subcommands(self) -> None:
        named = set(
            AGENT_LOOP_INVOCATION_RE.findall(
                _read(HALT_AND_RECOVERY_PATH)
            )
        )
        unknown = named - set(agent_loop.HANDLERS)
        self.assertEqual(
            unknown, set(),
            f"docs/halt-and-recovery.md references unknown "
            f"subcommands: {sorted(unknown)}",
        )


class SafetyRulesDocContentTests(unittest.TestCase):
    """The safety doc must name the load-bearing safety boundaries
    so an operator reading it from a clean clone can audit the
    constraints without cross-referencing CLAUDE.md or AGENTS.md.
    """

    def setUp(self) -> None:
        self.text = _read(SAFETY_RULES_PATH)

    def test_names_the_no_git_automation_boundary(self) -> None:
        # The specific shipped boundary the loop never crosses.
        for fragment in (
            "Git automation",
            "never invokes git",
        ):
            self.assertIn(
                fragment, self.text,
                f"docs/safety-rules.md does not name the no-git-"
                f"automation boundary via {fragment!r}",
            )

    def test_names_the_recovery_preserving_halt_pattern(self) -> None:
        self.assertIn(
            "Recovery-preserving halts", self.text,
            "docs/safety-rules.md does not describe the recovery-"
            "preserving halt pattern",
        )
        self.assertIn(
            "HaltError", self.text,
            "docs/safety-rules.md does not mention HaltError as the "
            "shipped refusal vocabulary",
        )

    def test_names_the_approved_for_activation_token(self) -> None:
        self.assertIn(
            "APPROVED_FOR_ACTIVATION", self.text,
            "docs/safety-rules.md does not name the human-authored "
            "APPROVED_FOR_ACTIVATION token (the Phase 4C activation "
            "gate)",
        )

    def test_names_the_artifact_ownership_partition(self) -> None:
        # The three ownership roles plus the orchestrator-owned
        # artifact list anchor the safety boundary.
        for role in ("Orchestrator-owned", "Codex-owned", "Claude-owned"):
            self.assertIn(
                role, self.text,
                f"docs/safety-rules.md does not name ownership role "
                f"{role!r}",
            )

    def test_names_evidence_state_vocabulary(self) -> None:
        # Phase 2A Evidence Collection Contract states.
        for state in agent_loop.EVIDENCE_STATES:
            self.assertIn(
                state, self.text,
                f"docs/safety-rules.md does not name Phase 2A "
                f"evidence state {state!r}",
            )


class ApprovalModesDocContentTests(unittest.TestCase):
    """The approval-modes doc must name every shipped approval mode
    by literal name, the three Phase 5C strict-mode gates, and the
    `claude-done.json` handoff artifact so an operator can drive any
    of the three modes from the doc alone.
    """

    def setUp(self) -> None:
        self.text = _read(APPROVAL_MODES_PATH)

    def test_names_every_shipped_approval_mode(self) -> None:
        for mode in (
            agent_loop.APPROVAL_MODE_REVIEW,
            agent_loop.APPROVAL_MODE_STRICT,
            agent_loop.APPROVAL_MODE_AUTONOMOUS,
        ):
            self.assertIn(
                f"`{mode}`", self.text,
                f"docs/approval-modes.md does not name approval mode "
                f"{mode!r}",
            )

    def test_names_the_three_strict_mode_gates(self) -> None:
        for gate in (
            "pre_claude_prompt",
            "pre_fix_prompt",
            "pre_codex_review",
        ):
            self.assertIn(
                gate, self.text,
                f"docs/approval-modes.md does not name strict-mode "
                f"gate {gate!r}",
            )

    def test_names_both_pre_codex_review_halt_flavors(self) -> None:
        for halt in (
            "halted_awaiting_human_pre_codex_review_normal",
            "halted_awaiting_human_pre_codex_review_fix",
        ):
            self.assertIn(
                halt, self.text,
                f"docs/approval-modes.md does not name the "
                f"pre_codex_review halt-status flavor {halt!r}",
            )

    def test_clarifies_strict_gates_do_not_write_checkpoint_artifacts(
        self,
    ) -> None:
        # The architecture doc's matching correction is mirrored here:
        # an operator reading the approval-modes doc should not infer
        # strict-mode halts write checkpoint artifacts. The check
        # collapses internal whitespace so line-wrapping does not
        # affect the assertion.
        collapsed = " ".join(self.text.split())
        self.assertIn(
            "do NOT write strict-gate checkpoint", collapsed,
            "docs/approval-modes.md does not explicitly state that "
            "strict-mode gates do NOT write strict-gate checkpoint "
            "artifacts",
        )

    def test_names_the_claude_done_handoff_artifact(self) -> None:
        self.assertIn(
            "claude-done.json", self.text,
            "docs/approval-modes.md does not name the Phase 5B "
            "claude-done.json handoff artifact",
        )

    def test_clarifies_autonomous_is_not_phase_9(self) -> None:
        # The shipped autonomous mode is the narrow strict-gate-
        # bypass slice; Phase 9 (Fully Autonomous PRD-To-Product
        # Mode) is roadmap only. The doc must keep that distinction
        # clear so operators do not over-trust autonomous.
        self.assertIn(
            "fully autonomous PRD-to-product", self.text,
            "docs/approval-modes.md does not explicitly disclaim "
            "that autonomous mode is NOT the Phase 9 fully autonomous "
            "PRD-to-product mode",
        )


class HaltAndRecoveryDocContentTests(unittest.TestCase):
    """The halt/recovery playbook is the operator-facing mirror of
    `STATUS_RECOVERY_HINTS`. Every status in that canonical map must
    appear in the doc as a dedicated section so an operator can find
    the recovery path for any persisted status they observe.
    """

    def setUp(self) -> None:
        self.text = _read(HALT_AND_RECOVERY_PATH)

    def test_names_every_status_in_recovery_hints_map(self) -> None:
        # The canonical map is the source of truth. If a status is in
        # STATUS_RECOVERY_HINTS but missing from this doc, an operator
        # who hits it gets the one-line `status` hint but no
        # operator-facing detail; this test fails closed so the doc
        # cannot silently lag the canonical map.
        for status in agent_loop.STATUS_RECOVERY_HINTS:
            self.assertIn(
                status, self.text,
                f"docs/halt-and-recovery.md does not have a section "
                f"for shipped status {status!r}",
            )

    def test_names_the_phase_complete_terminal_success_status(
        self,
    ) -> None:
        # The success terminal is not in STATUS_RECOVERY_HINTS (it is
        # not a recovery point), but the operator playbook must still
        # document it so the success path is discoverable.
        self.assertIn(
            "phase_complete_awaiting_human_approval", self.text,
            "docs/halt-and-recovery.md does not name the success "
            "terminal phase_complete_awaiting_human_approval",
        )

    def test_names_the_three_codex_verdicts(self) -> None:
        for verdict in (
            "APPROVED_FOR_HUMAN_REVIEW",
            "NEEDS_FIXES",
            "FAILED_REQUIRES_HUMAN",
        ):
            self.assertIn(
                verdict, self.text,
                f"docs/halt-and-recovery.md does not name Codex "
                f"verdict {verdict!r}",
            )

    def test_does_not_promise_cli_recovery_for_human_required_halts(
        self,
    ) -> None:
        # Mirror of the usage-doc fix: the human-required terminal
        # halts must not be described as having a direct CLI recovery
        # command.
        for halt in (
            "halted_failed_requires_human",
            "halted_max_cycles_reached",
        ):
            self.assertIn(
                halt, self.text,
                f"halt-and-recovery doc missing section for {halt!r}",
            )
        self.assertIn(
            "planner refuses", self.text,
            "docs/halt-and-recovery.md does not explain that the "
            "shipped planner refuses to propose the next phase from "
            "the human-required terminal halts",
        )


class Phase8BPlaybooksDoNotPromiseFutureBehaviorTests(unittest.TestCase):
    """Apply the Phase 8A no-future-claims guard to each Phase 8B
    playbook so a docs edit cannot quietly promote roadmap behavior
    into a present-tense product claim.
    """

    def test_phase_8b_docs_do_not_claim_autonomous_prd_to_product_mode(
        self,
    ) -> None:
        # Mirror of the Phase 8A assertion: PHASE 9 is roadmap only.
        forbidden_present_tense = (
            "ships fully autonomous PRD",
            "is a fully autonomous PRD",
        )
        for path in PHASE_8B_DOC_PATHS:
            text = _read(path)
            for fragment in forbidden_present_tense:
                self.assertNotIn(
                    fragment, text,
                    f"{path.name} promises unshipped Phase 9 "
                    f"behavior via {fragment!r}",
                )

    def test_phase_8b_docs_disclaim_mcp_and_external_ui(self) -> None:
        disclaim_terms = (
            "roadmap", "future", "deferred", "not implemented",
            "not yet", "later phase",
        )
        for path in PHASE_8B_DOC_PATHS:
            text = _read(path)
            for keyword in ("MCP", "external UI"):
                if keyword in text:
                    idx = text.find(keyword)
                    window = text[max(0, idx - 240): idx + 240]
                    if not any(t in window for t in disclaim_terms):
                        self.fail(
                            f"{path.name} mentions {keyword!r} "
                            f"without a disclaiming context"
                        )


class ReadmeDescribesStrictModeAccuratelyTests(unittest.TestCase):
    """Phase 8B fix: README previously claimed autonomous mode
    bypasses "four Phase 5C strict-mode human gates" and described
    `docs/halt-and-recovery.md` as covering "the four Phase 5C
    strict-mode gates". The shipped Phase 5C contract defines three
    gates (`pre_claude_prompt`, `pre_fix_prompt`, `pre_codex_review`),
    with `pre_codex_review` persisting in two halt-status flavors so
    resume can route correctly. These tests fail closed if either
    incorrect "four gates" wording is reintroduced in README.

    The forbidden-fragment list is narrow on purpose: it targets the
    specific wording Codex flagged ("four Phase 5C strict-mode human
    gates" / "four Phase 5C strict-mode gates") rather than every
    occurrence of "four ... strict". Other README passages that
    correctly enumerate the four halt-status STRINGS (e.g. "the four
    Phase 5C strict-mode halt vocabulary entries") describe a
    different fact - the halt-status count, not the gate count - and
    must not be caught by this guard.
    """

    def setUp(self) -> None:
        self.text = _read(README_PATH)

    def test_readme_does_not_claim_four_strict_mode_gates(self) -> None:
        for fragment in (
            "four Phase 5C strict-mode human gates",
            "four Phase 5C strict-mode gates",
            # Phase 8B fix-2: the test-description bullet for
            # tests/test_approval_modes.py still used the generic
            # "four strict gates" phrasing. Catch that variant too so
            # any README section (paragraph or bullet) that
            # reintroduces the gate / halt-status conflation fails
            # closed.
            "four strict gates",
        ):
            self.assertNotIn(
                fragment, self.text,
                f"README.md contains the inaccurate strict-mode "
                f"wording {fragment!r}; the shipped Phase 5C contract "
                f"defines three gates with two halt-status flavors on "
                f"pre_codex_review",
            )

    def test_readme_names_three_strict_mode_gates_in_phase_5d(self) -> None:
        # Positive assertion: after the corrected wording the Phase 5D
        # paragraph must name three gates rather than four.
        self.assertIn(
            "three Phase 5C strict-mode human gates", self.text,
            "README.md Phase 5D paragraph does not name the shipped "
            "three-gate count (with the pre_codex_review two-flavor "
            "note); the corrected wording from the Phase 8B fix is "
            "missing",
        )

    def test_readme_names_both_pre_codex_review_halt_flavors(
        self,
    ) -> None:
        # The corrected Phase 5D paragraph names both pre_codex_review
        # halt-status flavors so a reader sees the load-bearing
        # distinction (3 gates / 4 halt-status strings) explicitly.
        for halt in (
            "halted_awaiting_human_pre_codex_review_normal",
            "halted_awaiting_human_pre_codex_review_fix",
        ):
            self.assertIn(
                halt, self.text,
                f"README.md does not name the pre_codex_review halt-"
                f"status flavor {halt!r}; the corrected wording from "
                f"the Phase 8B fix is missing",
            )


class ReadmeOnlyNamesRealSubcommandsTests(unittest.TestCase):
    """Phase 8C: mirror the Phase 8A/8B CLI-surface guard onto README.
    Any `python scripts/agent_loop.py <subcommand>` mention in README
    must resolve to a real `agent_loop.HANDLERS` entry so the project
    front page cannot drift into claiming non-existent commands.
    """

    def test_readme_only_names_real_subcommands(self) -> None:
        named = set(AGENT_LOOP_INVOCATION_RE.findall(_read(README_PATH)))
        unknown = named - set(agent_loop.HANDLERS)
        self.assertEqual(
            unknown, set(),
            f"README.md references unknown subcommands: "
            f"{sorted(unknown)}",
        )


class ReadmeCleanCloneGettingStartedTests(unittest.TestCase):
    """Phase 8C: README must route a clean-clone reader at the shipped
    Phase 8A/8B operator docs and must not carry stale Phase-1 framing
    implying the orchestrator is not yet built. These tests pin the
    Phase 8C alignment so a later README edit cannot silently drop the
    operator-doc pointers or reintroduce the stale wording.
    """

    def setUp(self) -> None:
        self.text = _read(README_PATH)

    def test_readme_names_every_operator_doc(self) -> None:
        for rel_path in (
            "docs/usage.md",
            "docs/architecture.md",
            "docs/safety-rules.md",
            "docs/approval-modes.md",
            "docs/halt-and-recovery.md",
        ):
            self.assertIn(
                rel_path, self.text,
                f"README.md does not name operator doc {rel_path!r}; "
                f"a clean-clone reader has no pointer at the shipped "
                f"Phase 8A/8B documentation set",
            )

    def test_readme_does_not_carry_stale_phase_1_workflow_framing(
        self,
    ) -> None:
        # Phase 3A-3E all shipped; the original Phase-1 framing said the
        # orchestrator was not yet built. Catch the specific stale
        # phrases so a future edit that revives them fails closed. The
        # last fragment is the Phase 8C fix-cycle addition: the README
        # used to describe loop-state.json as "recorded by hand" as a
        # standalone fact, which contradicts the shipped orchestrator-
        # owned ownership model.
        for fragment in (
            "once the orchestrator (Phase 3) is built",
            "Until then, the same loop runs by hand",
            "While the orchestrator is not yet built",
            (
                "records the active phase, task, cycle count, max "
                "cycles, and last verdict by hand"
            ),
        ):
            self.assertNotIn(
                fragment, self.text,
                f"README.md still carries stale Phase-1 framing "
                f"{fragment!r}; Phase 3A-3E all shipped and the "
                f"orchestrator is the documented driver",
            )

    def test_readme_describes_loop_state_as_orchestrator_owned(
        self,
    ) -> None:
        # Phase 8C fix-cycle positive lock-in: the corrected wording
        # must explicitly call out loop-state.json as orchestrator-
        # owned in the shipped system so a reader sees the contract-
        # accurate ownership boundary directly in the README. Without
        # this, a future edit could drop both the stale phrase and the
        # corrected framing in one go and leave the file's ownership
        # ambiguous.
        collapsed = " ".join(self.text.split())
        self.assertIn(
            ".agent-loop/loop-state.json", collapsed,
            "README.md no longer names the loop-state.json artifact "
            "near the manual-fallback section",
        )
        self.assertIn(
            "orchestrator-owned runtime artifact", collapsed,
            "README.md does not describe loop-state.json as an "
            "orchestrator-owned runtime artifact; the Phase 8C fix-"
            "cycle corrected wording is missing",
        )
        # The corrected wording also names the shipped writers (the
        # activator at phase activation and scripts/agent_loop.py per
        # cycle) so the ownership claim is concrete. The README wraps
        # the script path in backticks; check the path and verb
        # substrings independently so the assertion does not depend
        # on the exact backtick layout.
        self.assertIn(
            "activator initializes it", collapsed,
            "README.md does not name the activator as the artifact "
            "initializer; the Phase 8C fix-cycle corrected wording "
            "is incomplete",
        )
        self.assertIn(
            "scripts/agent_loop.py", collapsed,
            "README.md does not name scripts/agent_loop.py near the "
            "loop-state.json ownership claim",
        )
        self.assertIn(
            "updates the per-cycle fields", collapsed,
            "README.md does not describe scripts/agent_loop.py as "
            "the per-cycle field updater; the Phase 8C fix-cycle "
            "corrected wording is incomplete",
        )

    def test_readme_marks_phase_8c_as_active(self) -> None:
        self.assertIn(
            "Phase 8C", self.text,
            "README.md does not name Phase 8C as a current focus",
        )
        self.assertIn(
            "Final README Alignment", self.text,
            "README.md does not name the Phase 8C sub-phase title",
        )


class ReadmeDoesNotPromiseFutureBehaviorTests(unittest.TestCase):
    """Phase 8C: apply the Phase 8A no-future-claims guard to README.
    README mentions Phase 9 / MCP / external UI as disclaiming framing
    today; this guard fails closed if a future edit collapses those
    roadmap items into a present-tense product claim.
    """

    def setUp(self) -> None:
        self.text = _read(README_PATH)

    def test_readme_does_not_claim_phase_9_as_shipped(self) -> None:
        for fragment in (
            "ships fully autonomous PRD",
            "is a fully autonomous PRD",
        ):
            self.assertNotIn(
                fragment, self.text,
                f"README.md promises unshipped Phase 9 behavior via "
                f"{fragment!r}",
            )

    def test_readme_disclaims_mcp_and_external_ui(self) -> None:
        # Mirror of the Phase 8A check: the first README occurrence of
        # each roadmap keyword must appear adjacent to a disclaiming
        # term so a new operator cannot read the front-of-README
        # mention as a current shipped capability. The README has many
        # legitimate later references (e.g. test-description prose that
        # itself documents the no-future-claims guard); checking the
        # first occurrence matches the Phase 8A precedent and avoids
        # false positives on self-referential meta-text.
        disclaim_terms = (
            "roadmap", "future", "deferred", "not implemented",
            "not yet", "later phase",
        )
        for keyword in ("MCP", "external UI"):
            idx = self.text.find(keyword)
            if idx < 0:
                continue
            window = self.text[max(0, idx - 240): idx + 240]
            if not any(t in window for t in disclaim_terms):
                self.fail(
                    f"README.md's first mention of {keyword!r} (offset "
                    f"{idx}) lacks a disclaiming context (roadmap / "
                    f"future / deferred / not implemented / later "
                    f"phase); a new operator could read it as a "
                    f"current shipped capability"
                )


class Phase9AAutonomyContractExistsAndIsWellFormedTests(unittest.TestCase):
    """Phase 9A: the autonomy contract doc must exist at the repo root,
    be ASCII-only, and be non-empty. Mirrors the Phase 8A/8B existence
    guards.
    """

    def test_autonomy_contract_doc_exists_and_non_empty(self) -> None:
        self.assertTrue(
            AUTONOMY_CONTRACT_PATH.is_file(),
            f"Expected Phase 9A autonomy contract doc at "
            f"{AUTONOMY_CONTRACT_PATH}",
        )
        self.assertGreater(AUTONOMY_CONTRACT_PATH.stat().st_size, 0)

    def test_autonomy_contract_doc_is_ascii_only(self) -> None:
        text = _read(AUTONOMY_CONTRACT_PATH)
        for i, line in enumerate(text.splitlines(), 1):
            for ch in line:
                self.assertLessEqual(
                    ord(ch), 127,
                    f"non-ASCII character {ch!r} in "
                    f"{AUTONOMY_CONTRACT_PATH.name} line {i}",
                )


class Phase9AAutonomyContractOnlyClaimsShippedCliSurfacesTests(
    unittest.TestCase,
):
    """Phase 9A: the same anti-drift CLI guard the Phase 8A/8B docs
    have. The autonomy contract is a forward-looking doc, but any
    subcommand it mentions still must resolve to a real shipped
    handler so the doc cannot drift into claiming non-existent CLI.
    """

    def test_autonomy_contract_only_names_real_subcommands(self) -> None:
        named = set(AGENT_LOOP_INVOCATION_RE.findall(
            _read(AUTONOMY_CONTRACT_PATH)
        ))
        unknown = named - set(agent_loop.HANDLERS)
        self.assertEqual(
            unknown, set(),
            f"docs/autonomy-contract.md references unknown "
            f"subcommands: {sorted(unknown)}",
        )


class Phase9AAutonomyContractDoesNotPromiseUnshippedRuntimeTests(
    unittest.TestCase,
):
    """The Phase 9A doc is a contract for a FUTURE mode. It must NOT
    claim the runtime is already implemented; a clean-clone reader
    must be able to tell from the doc itself that the mode is not yet
    shipped.
    """

    def setUp(self) -> None:
        self.text = _read(AUTONOMY_CONTRACT_PATH)

    def test_autonomy_contract_states_runtime_not_yet_implemented(
        self,
    ) -> None:
        # Defense in depth: the doc must explicitly say the runtime is
        # not yet built so a clean-clone reader cannot mistake the
        # contract for an as-shipped behavior reference. The literal
        # "NOT yet implemented" wording is pinned to make the drift
        # signal precise.
        self.assertIn(
            "NOT yet implemented", self.text,
            "docs/autonomy-contract.md does not state the runtime is "
            "not yet implemented; a reader could mistake the contract "
            "for shipped behavior",
        )

    def test_autonomy_contract_does_not_claim_shipped_phase_9_runtime(
        self,
    ) -> None:
        # Mirror of the Phase 8A/8C present-tense forbidden-fragment
        # guard.
        for fragment in (
            "ships fully autonomous PRD",
            "is a fully autonomous PRD",
        ):
            self.assertNotIn(
                fragment, self.text,
                f"docs/autonomy-contract.md promises unshipped Phase 9 "
                f"behavior via {fragment!r}",
            )


class Phase9AAutonomyContractDistinguishesFromShippedAutonomousModeTests(
    unittest.TestCase,
):
    """The shipped Phase 5D `autonomous` approval mode is a narrow
    intra-phase strict-gate bypass. The Phase 9 fully autonomous PRD-
    to-product mode is a different cross-phase mode. The contract MUST
    keep the distinction explicit so the two are not collapsed into
    one mode name.
    """

    def setUp(self) -> None:
        self.text = _read(AUTONOMY_CONTRACT_PATH)

    def test_autonomy_contract_names_phase_5d_as_shipped(self) -> None:
        self.assertIn(
            "Phase 5D", self.text,
            "docs/autonomy-contract.md does not name the shipped "
            "Phase 5D autonomous mode it must be distinguished from",
        )

    def test_autonomy_contract_names_phase_5c_strict_gate_set(
        self,
    ) -> None:
        # Naming the three Phase 5C gates makes the distinction
        # concrete: a reader sees exactly what the shipped narrow
        # `autonomous` mode bypasses.
        for gate in (
            "pre_claude_prompt",
            "pre_fix_prompt",
            "pre_codex_review",
        ):
            self.assertIn(
                gate, self.text,
                f"docs/autonomy-contract.md does not name the Phase "
                f"5C strict-mode gate {gate!r}",
            )

    def test_autonomy_contract_names_phase_9_subphases(self) -> None:
        # The contract must locate the future runtime work in the
        # right sub-phases so a reader knows which slices implement
        # which piece. ROADMAP.md defines Phase 9B-9G.
        for sub_phase in (
            "Phase 9B", "Phase 9D", "Phase 9F", "Phase 9G",
        ):
            self.assertIn(
                sub_phase, self.text,
                f"docs/autonomy-contract.md does not name "
                f"{sub_phase!r} as the locus for the corresponding "
                f"future runtime work",
            )


class Phase9AAutonomyContractPreservesShippedHardStopsTests(
    unittest.TestCase,
):
    """The contract MUST preserve the shipped hard stops (no Git
    automation, the human-authored `APPROVED_FOR_ACTIVATION` gate, the
    two human-required terminal halts, the final human acceptance
    gate). Operators read this section to verify the contract does
    not weaken the shipped safety boundaries.
    """

    def setUp(self) -> None:
        self.text = _read(AUTONOMY_CONTRACT_PATH)

    def test_autonomy_contract_preserves_no_git_automation(self) -> None:
        # The repo-wide no-Git-automation boundary must hold for the
        # future autonomous mode too.
        for fragment in (
            "never commits to Git",
            "never pushes",
        ):
            self.assertIn(
                fragment, self.text,
                f"docs/autonomy-contract.md does not preserve the "
                f"no-Git-automation boundary via {fragment!r}",
            )

    def test_autonomy_contract_preserves_approved_for_activation(
        self,
    ) -> None:
        self.assertIn(
            "APPROVED_FOR_ACTIVATION", self.text,
            "docs/autonomy-contract.md does not preserve the "
            "APPROVED_FOR_ACTIVATION gate semantics",
        )

    def test_autonomy_contract_names_terminal_halt_vocabulary(
        self,
    ) -> None:
        for halt in (
            "halted_failed_requires_human",
            "halted_max_cycles_reached",
        ):
            self.assertIn(
                halt, self.text,
                f"docs/autonomy-contract.md does not name preserved "
                f"terminal halt {halt!r}",
            )

    def test_autonomy_contract_names_final_human_acceptance(
        self,
    ) -> None:
        # The Phase 9G final acceptance gate is the load-bearing
        # human-approval boundary the autonomous mode never bypasses.
        self.assertIn(
            "final human acceptance", self.text,
            "docs/autonomy-contract.md does not preserve the final "
            "human acceptance / polish gate (Phase 9G)",
        )


class ReadmePointsAtAutonomyContractDocTests(unittest.TestCase):
    """Phase 9A: the README must route a reader at the new contract
    doc and mark Phase 9A as the current active sub-phase.
    """

    def setUp(self) -> None:
        self.text = _read(README_PATH)

    def test_readme_names_autonomy_contract_doc(self) -> None:
        # A clean-clone reader looking for the Phase 9A scope must be
        # routed at the new doc by repo-relative path.
        self.assertIn(
            "docs/autonomy-contract.md", self.text,
            "README.md does not name the new Phase 9A docs/autonomy-"
            "contract.md doc; a clean-clone reader has no pointer to "
            "the shipped contract",
        )

    def test_readme_marks_phase_9a_as_active(self) -> None:
        self.assertIn(
            "Phase 9A", self.text,
            "README.md does not name Phase 9A as a current focus",
        )
        self.assertIn(
            "Autonomous Mode Contract", self.text,
            "README.md does not name the Phase 9A sub-phase title",
        )

    def test_readme_does_not_still_mark_phase_8c_as_active(self) -> None:
        # Phase 8C is closed; the README must not still say it's "now
        # active" anywhere. The first fragment catches the original
        # "Phase 8C ... is now active" sentence the Phase 9A initial
        # slice already removed. The second fragment catches the
        # historical-summary stale wording that the Phase 9A fix cycle
        # uncovered ("the active Phase 8C ..."). The second substring
        # is precise enough not to false-positive on the legitimate
        # Phase 9A paragraph wording "previously-active Phase 8C"
        # because that surrounding text contains "the previously-
        # active Phase 8C" rather than "the active Phase 8C".
        for fragment in (
            "Phase 8C final README alignment and clean-clone polish "
            "is now active",
            "the active Phase 8C",
        ):
            self.assertNotIn(
                fragment, self.text,
                f"README.md still describes Phase 8C as active via "
                f"{fragment!r}; Phase 9A is the current active "
                f"sub-phase and every active-phase reference must "
                f"match the shipped 9A state",
            )


class ReadmeMarksPhase9bAsActiveTests(unittest.TestCase):
    """Phase 9B: the README must name Phase 9B as the current active
    sub-phase, describe the new shipped intake surface (the
    `intake-prd` CLI subcommand and the `.agent-loop/prd-intake.json`
    advisory artifact), and not promise the deferred Phase 9C-9G
    runtime work as shipped.
    """

    def setUp(self) -> None:
        self.text = _read(README_PATH)

    def test_readme_marks_phase_9b_as_active(self) -> None:
        self.assertIn(
            "Phase 9B", self.text,
            "README.md does not name Phase 9B as a current focus",
        )
        self.assertIn(
            "PRD Intake And Decomposition", self.text,
            "README.md does not name the Phase 9B sub-phase title",
        )

    def test_readme_names_the_shipped_intake_surface(self) -> None:
        # The new CLI subcommand and output artifact must be
        # discoverable from README so a clean-clone reader can
        # connect the Phase 9B paragraph to the shipped surface.
        for fragment in (
            "intake-prd",
            ".agent-loop/prd-intake.json",
        ):
            self.assertIn(
                fragment, self.text,
                f"README.md Phase 9B paragraph does not name shipped "
                f"surface {fragment!r}",
            )

    def test_readme_does_not_claim_phase_9c_through_9g_shipped(
        self,
    ) -> None:
        # Phase 9C-9G runtime work is explicitly deferred per the
        # Phase 9A contract. The README must not claim any of those
        # sub-phases is shipped or active.
        # The Phase 9B paragraph names Phase 9C-9G in a single
        # deferred clause that ends with "remain deferred"; the
        # window must be wide enough to cover the whole paragraph.
        # 500 chars on each side of the keyword is enough to span the
        # densest Phase 9 paragraph in the README without becoming
        # so wide it stops being a useful proximity signal.
        # Phase 9C, 9D, 9E, 9F, and 9G have all shipped in their
        # own implementation slices; the must-be-deferred set is
        # now empty for the Phase 9 surface (the Phase 9 runtime
        # is complete through Phase 9G). The loop is kept as a
        # structural guard so a future deferred sub-phase can be
        # re-added here without restructuring the test.
        for sub_phase in ():
            if sub_phase in self.text:
                idx = self.text.find(sub_phase)
                window = self.text[max(0, idx - 500): idx + 500]
                disclaim_terms = (
                    "deferred", "future", "roadmap", "not yet",
                    "remain deferred", "later phase",
                )
                if not any(t in window for t in disclaim_terms):
                    self.fail(
                        f"README.md mentions {sub_phase!r} (offset "
                        f"{idx}) without a deferred / future / "
                        f"roadmap context within 500 chars"
                    )

    def test_readme_prd_intake_paragraph_names_canonical_precedence(
        self,
    ) -> None:
        # The Phase 9B paragraph must reference the canonical-
        # precedence preservation explicitly so a reader sees that
        # the intake artifact does NOT replace the Phase 4 planner /
        # activator boundary.
        for fragment in (
            "Phase 4 planner",
            "Phase 4C activator",
        ):
            self.assertIn(
                fragment, self.text,
                f"README.md Phase 9B paragraph does not name the "
                f"preserved {fragment!r} boundary",
            )


class ReadmeMarksPhase9cAsActiveTests(unittest.TestCase):
    """Phase 9C: README must name Phase 9C as the current active
    sub-phase, describe the new shipped handoff surface (the
    `dispatch-prompt-handoff` CLI subcommand and the
    `.agent-loop/prompt-handoff.json` advisory descriptor), and not
    promise the deferred Phase 9D-9G runtime work as shipped.
    """

    def setUp(self) -> None:
        self.text = _read(README_PATH)

    def test_readme_marks_phase_9c_as_active(self) -> None:
        self.assertIn(
            "Phase 9C", self.text,
            "README.md does not name Phase 9C as a current focus",
        )
        self.assertIn(
            "Orchestrator-Driven Prompt Handoff", self.text,
            "README.md does not name the Phase 9C sub-phase title",
        )

    def test_readme_names_the_shipped_handoff_surface(self) -> None:
        for fragment in (
            "dispatch-prompt-handoff",
            ".agent-loop/prompt-handoff.json",
        ):
            self.assertIn(
                fragment, self.text,
                f"README.md Phase 9C paragraph does not name shipped "
                f"surface {fragment!r}",
            )

    def test_readme_preserves_handoff_canonical_boundary_language(
        self,
    ) -> None:
        # The Phase 9C paragraph must explicitly state the handoff
        # descriptor is a routing signal, not a replacement for the
        # canonical prompt artifacts or for `claude-done.json`. This
        # is the load-bearing safety distinction.
        for fragment in (
            "routing signal",
            "claude-done.json",
            "canonical prompt artifacts",
        ):
            self.assertIn(
                fragment, self.text,
                f"README.md Phase 9C paragraph does not name the "
                f"preserved {fragment!r} boundary",
            )


class ReadmeMarksPhase9dAsActiveTests(unittest.TestCase):
    """Phase 9D: README must name Phase 9D as the current active
    sub-phase, describe the new shipped autonomous-review/fix surface
    (the `run-internal-review-fix-cycle` CLI subcommand and the
    `.agent-loop/review-fix-loop.json` advisory descriptor), and not
    promise the deferred Phase 9E-9G runtime work as shipped.
    """

    def setUp(self) -> None:
        self.text = _read(README_PATH)

    def test_readme_marks_phase_9d_as_active(self) -> None:
        self.assertIn(
            "Phase 9D", self.text,
            "README.md does not name Phase 9D as a current focus",
        )
        self.assertIn(
            "Autonomous Internal Review/Fix Loop", self.text,
            "README.md does not name the Phase 9D sub-phase title",
        )

    def test_readme_names_the_shipped_review_fix_loop_surface(
        self,
    ) -> None:
        for fragment in (
            "run-internal-review-fix-cycle",
            ".agent-loop/review-fix-loop.json",
        ):
            self.assertIn(
                fragment, self.text,
                f"README.md Phase 9D paragraph does not name shipped "
                f"surface {fragment!r}",
            )

    def test_readme_preserves_review_fix_loop_canonical_boundary(
        self,
    ) -> None:
        # The Phase 9D paragraph must explicitly state that the
        # canonical review and fix-prompt artifacts remain the source
        # of truth and that the new descriptor is advisory.
        for fragment in (
            "canonical",
            "source of truth",
            "routing signal",
        ):
            self.assertIn(
                fragment, self.text,
                f"README.md Phase 9D paragraph does not name the "
                f"preserved {fragment!r} boundary",
            )

    def test_readme_documents_dry_run_escape_hatches(self) -> None:
        # Operators must be able to discover all three escape hatches
        # from README so they can preview the loop without invoking
        # real evidence / Codex / Claude work.
        for fragment in (
            "--skip-evidence",
            "--no-invoke-codex",
            "--no-invoke-claude",
        ):
            self.assertIn(
                fragment, self.text,
                f"README.md Phase 9D paragraph does not document "
                f"escape hatch {fragment!r}",
            )


class ReadmeMarksPhase9eAsActiveTests(unittest.TestCase):
    """Phase 9E: README must name Phase 9E as the current active
    sub-phase, describe the new shipped long-run-continuation
    surface (the `run-long-run-continuation` CLI subcommand and the
    `.agent-loop/long-run-continuation.json` advisory descriptor),
    and not promise the deferred Phase 9F-9G runtime work as
    shipped.
    """

    def setUp(self) -> None:
        self.text = _read(README_PATH)

    def test_readme_marks_phase_9e_as_active(self) -> None:
        self.assertIn(
            "Phase 9E", self.text,
            "README.md does not name Phase 9E as a current focus",
        )
        self.assertIn(
            "Long-Run Continuation And Completion Heuristics",
            self.text,
            "README.md does not name the Phase 9E sub-phase title",
        )

    def test_readme_names_the_shipped_long_run_surface(self) -> None:
        for fragment in (
            "run-long-run-continuation",
            ".agent-loop/long-run-continuation.json",
        ):
            self.assertIn(
                fragment, self.text,
                f"README.md Phase 9E paragraph does not name shipped "
                f"surface {fragment!r}",
            )

    def test_readme_preserves_long_run_canonical_boundary(self) -> None:
        # The Phase 9E paragraph must explicitly state that
        # completion detection is canonical-artifact-only and that
        # canonical loop-state / review / fix artifacts remain the
        # source of truth.
        for fragment in (
            "canonical",
            "source of truth",
            "advisory",
        ):
            self.assertIn(
                fragment, self.text,
                f"README.md Phase 9E paragraph does not name the "
                f"preserved {fragment!r} boundary",
            )

    def test_readme_documents_completion_signals(self) -> None:
        for fragment in (
            "completion_approved",
            "completion_failed",
            "completion_halted",
        ):
            self.assertIn(
                fragment, self.text,
                f"README.md Phase 9E paragraph does not document "
                f"completion signal {fragment!r}",
            )


class ReadmeMarksPhase9fAsActiveTests(unittest.TestCase):
    """Phase 9F: README must name Phase 9F as the current active
    sub-phase, describe the new shipped capacity-halt re-probe
    surface (the `run-capacity-reprobe` CLI subcommand, the
    `.agent-loop/capacity-retry-state.json` retry-state artifact,
    and the `halted_capacity_unavailable` halt vocabulary), and
    not promise the deferred Phase 9G runtime work as shipped.
    """

    def setUp(self) -> None:
        self.text = _read(README_PATH)

    def test_readme_marks_phase_9f_as_active(self) -> None:
        self.assertIn(
            "Phase 9F", self.text,
            "README.md does not name Phase 9F as a current focus",
        )
        self.assertIn(
            "Capacity-Halt Reprobe And Automatic Resume",
            self.text,
            "README.md does not name the Phase 9F sub-phase title",
        )

    def test_readme_names_the_shipped_capacity_surface(self) -> None:
        for fragment in (
            "run-capacity-reprobe",
            ".agent-loop/capacity-retry-state.json",
            "halted_capacity_unavailable",
        ):
            self.assertIn(
                fragment, self.text,
                f"README.md Phase 9F paragraph does not name "
                f"shipped surface {fragment!r}",
            )

    def test_readme_documents_bounded_retry_semantics(self) -> None:
        # The Phase 9F paragraph must document the bounded retry
        # contract so an operator can predict the behavior.
        for fragment in (
            "bounded",
            "backoff",
            "budget",
            "cumulative",
        ):
            self.assertIn(
                fragment, self.text,
                f"README.md Phase 9F paragraph does not document "
                f"bounded retry semantics fragment {fragment!r}",
            )

    def test_readme_preserves_capacity_retry_canonical_boundary(
        self,
    ) -> None:
        # The Phase 9F paragraph must explicitly state that the
        # canonical loop-state on disk is the source of truth and
        # that the retry-state artifact tracks the budget.
        for fragment in (
            "canonical",
            "source of truth",
            "advisory" if "advisory" in self.text else "retry-state",
        ):
            self.assertIn(
                fragment, self.text,
                f"README.md Phase 9F paragraph does not name "
                f"the preserved {fragment!r} boundary",
            )


class ReadmeMarksPhase9gAsActiveTests(unittest.TestCase):
    """Phase 9G: README must name Phase 9G as the current active
    sub-phase, describe the shipped final-human-acceptance surface
    (the `record-final-acceptance` and `evaluate-final-acceptance`
    CLI subcommands, the `.agent-loop/final-acceptance.json`
    canonical artifact, and the `awaiting_final_human_acceptance`
    / `final_acceptance_recorded` signal vocabulary), and
    preserve the documented Phase 4 planner / Phase 4C activator
    boundary so the gate does not silently activate the next
    phase.
    """

    def setUp(self) -> None:
        self.text = _read(README_PATH)

    def test_readme_marks_phase_9g_as_active(self) -> None:
        self.assertIn(
            "Phase 9G", self.text,
            "README.md does not name Phase 9G as a current focus",
        )
        self.assertIn(
            "Final Human Acceptance And Polish Gate", self.text,
            "README.md does not name the Phase 9G sub-phase title",
        )

    def test_readme_names_the_shipped_acceptance_surface(self) -> None:
        for fragment in (
            "record-final-acceptance",
            "evaluate-final-acceptance",
            ".agent-loop/final-acceptance.json",
            "awaiting_final_human_acceptance",
            "final_acceptance_recorded",
        ):
            self.assertIn(
                fragment, self.text,
                f"README.md Phase 9G paragraph does not name "
                f"shipped surface {fragment!r}",
            )

    def test_readme_preserves_planner_activator_boundary(
        self,
    ) -> None:
        # The Phase 9G paragraph must explicitly state that the
        # acceptance gate does NOT activate the next phase; the
        # shipped Phase 4C activator + APPROVED_FOR_ACTIVATION
        # human approval are still the only path.
        for fragment in (
            "Phase 4C activator",
            "APPROVED_FOR_ACTIVATION",
            "gate, not an activation",
        ):
            self.assertIn(
                fragment, self.text,
                f"README.md Phase 9G paragraph does not preserve "
                f"the {fragment!r} boundary",
            )

    def test_readme_documents_acceptance_refusal_modes(self) -> None:
        # The Phase 9G paragraph must name the load-bearing
        # refusal modes so an operator can predict the behavior.
        for fragment in (
            "phase_complete_awaiting_human_approval",
            "APPROVED_FOR_HUMAN_REVIEW",
            "refuses silent re-acceptance",
        ):
            self.assertIn(
                fragment, self.text,
                f"README.md Phase 9G paragraph does not document "
                f"refusal-mode fragment {fragment!r}",
            )


class ExternalWorkspaceContractDocExistsAndIsWellFormedTests(
    unittest.TestCase,
):
    """Phase 10A: the external-workspace controller contract doc must
    exist on disk, be non-empty, be ASCII-only, and carry the canonical
    section headers a Phase 10B implementer reads.
    """

    def setUp(self) -> None:
        self.path = EXTERNAL_WORKSPACE_CONTRACT_PATH
        self.text = _read(self.path)

    def test_doc_exists_and_non_empty(self) -> None:
        self.assertTrue(
            self.path.is_file(),
            f"Expected Phase 10A external-workspace contract doc at "
            f"{self.path}",
        )
        self.assertGreater(self.path.stat().st_size, 0)

    def test_doc_is_ascii_only(self) -> None:
        raw = self.path.read_bytes()
        try:
            raw.decode("ascii")
        except UnicodeDecodeError as exc:
            self.fail(
                f"docs/external-workspace-contract.md contains "
                f"non-ASCII bytes: {exc}"
            )

    def test_doc_has_required_top_level_sections(self) -> None:
        for header in (
            "# External Workspace Controller Contract",
            "## Status",
            "## Scope",
            "## Distinction From Shipped Self-Targeting Mode",
            "## Controller-Owned Artifacts",
            "## Target-Owned Artifacts",
            "## Path Resolution",
            "## Attach And Bootstrap",
            "## Refusal Behavior",
            "## Approval Gates",
            "## Source-Of-Truth Preservation",
            "## Safety Boundaries",
            "## Out Of Scope For Phase 10A",
        ):
            self.assertIn(
                header, self.text,
                f"docs/external-workspace-contract.md missing "
                f"required section header {header!r}",
            )


class ExternalWorkspaceContractDistinguishesShippedModeTests(
    unittest.TestCase,
):
    """The contract must explicitly distinguish the future Phase 10
    external-workspace mode from the shipped self-targeting mode so a
    reader cannot conflate them. This is the load-bearing scope
    distinction the Phase 9A autonomy contract uses too.
    """

    def setUp(self) -> None:
        self.text = _read(EXTERNAL_WORKSPACE_CONTRACT_PATH)
        # Collapse whitespace so substring checks survive line-wrap.
        self.collapsed = re.sub(r"\s+", " ", self.text)

    def test_contract_marks_runtime_as_not_yet_implemented(self) -> None:
        # Phase 10A is documentation-only; the doc must not silently
        # promise the runtime as shipped.
        self.assertIn(
            "is NOT yet implemented", self.collapsed,
            "docs/external-workspace-contract.md does not mark the "
            "external-workspace runtime as not-yet-implemented",
        )

    def test_contract_locates_future_runtime_in_phase_10b_or_later(
        self,
    ) -> None:
        # The contract must locate the future runtime in the right
        # Phase 10 sub-phases so a reader knows which slices implement
        # which piece.
        for sub_phase in (
            "Phase 10B",
            "Phase 10C",
        ):
            self.assertIn(
                sub_phase, self.collapsed,
                f"docs/external-workspace-contract.md does not name "
                f"{sub_phase!r} as the locus for the corresponding "
                f"future runtime work",
            )

    def test_contract_names_shipped_self_targeting_mode(self) -> None:
        # The contract must explicitly call out the shipped
        # self-targeting mode as a distinct, preserved mode rather
        # than silently replacing it.
        for fragment in (
            "shipped self-targeting mode",
            "find_repo_root",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"docs/external-workspace-contract.md does not "
                f"reference the shipped self-targeting mode via "
                f"{fragment!r}",
            )


class ExternalWorkspaceContractPreservesShippedHardStopsTests(
    unittest.TestCase,
):
    """The Phase 10A contract MUST preserve the shipped hard stops (no
    Git automation, the Phase 4C activator + APPROVED_FOR_ACTIVATION
    gate, the Phase 9G final human acceptance gate, the source-of-truth
    boundary). Operators read this section to verify the contract does
    not weaken the shipped safety boundaries before any runtime ships.
    """

    def setUp(self) -> None:
        self.text = _read(EXTERNAL_WORKSPACE_CONTRACT_PATH)
        # Collapse whitespace so substring checks survive line-wrap.
        self.collapsed = re.sub(r"\s+", " ", self.text)
        self.collapsed_lower = self.collapsed.lower()

    def test_contract_preserves_no_git_automation(self) -> None:
        # The repo-wide no-Git-automation boundary must apply in BOTH
        # roots (controller and target) under Phase 10.
        for fragment in (
            "commit, push, tag, branch, stash, reset, checkout",
            "BOTH roots",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"docs/external-workspace-contract.md does not "
                f"preserve the no-Git-automation boundary via "
                f"{fragment!r}",
            )

    def test_contract_preserves_approved_for_activation(self) -> None:
        self.assertIn(
            "APPROVED_FOR_ACTIVATION", self.collapsed,
            "docs/external-workspace-contract.md does not preserve "
            "the APPROVED_FOR_ACTIVATION human-approval gate",
        )
        self.assertIn(
            "Phase 4C activator", self.collapsed,
            "docs/external-workspace-contract.md does not name the "
            "Phase 4C activator as the preserved activation step",
        )

    def test_contract_preserves_final_human_acceptance_gate(self) -> None:
        # The Phase 9G gate must continue to apply per-target under
        # Phase 10; the external-workspace mode never auto-accepts.
        self.assertIn(
            "Phase 9G", self.collapsed,
            "docs/external-workspace-contract.md does not name the "
            "Phase 9G final acceptance gate as a preserved boundary",
        )
        self.assertIn(
            "final human acceptance", self.collapsed,
            "docs/external-workspace-contract.md does not preserve "
            "the final human acceptance / polish gate",
        )

    def test_contract_preserves_canonical_artifact_source_of_truth(
        self,
    ) -> None:
        # Advisory descriptors / future UI MUST stay advisory. The
        # contract must say so explicitly.
        for fragment in (
            "canonical artifacts on disk remain authoritative",
            "advisory",
        ):
            self.assertIn(
                fragment, self.collapsed_lower,
                f"docs/external-workspace-contract.md does not "
                f"preserve the canonical source-of-truth model via "
                f"{fragment!r}",
            )

    def test_contract_refuses_controller_target_collapse(self) -> None:
        # The two roots must be distinct; nesting and same-root are
        # explicit refusal cases.
        for fragment in (
            "same as the controller root",
            "nested inside the controller",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"docs/external-workspace-contract.md does not "
                f"refuse the controller/target collapse via "
                f"{fragment!r}",
            )


class ExternalWorkspaceContractUsesRealPhase9eDescriptorPathTests(
    unittest.TestCase,
):
    """Phase 10A fix: the contract surfaces must reference the REAL
    shipped Phase 9E descriptor path
    (`.agent-loop/long-run-continuation.json`,
    `LONG_RUN_CONTINUATION_OUTPUT_REL` in `scripts/agent_loop.py`), not
    a stale `.agent-loop/long-run-loop.json` name. The Phase 9E
    descriptor is the canonical long-run-continuation artifact written
    by `run_long_run_continuation(...)`; teaching a wrong path would
    mislead a future Phase 10B implementer about the target-owned
    artifact set.
    """

    def setUp(self) -> None:
        self.contract_text = _read(EXTERNAL_WORKSPACE_CONTRACT_PATH)
        self.readme_text = _read(README_PATH)

    def test_contract_uses_real_phase_9e_descriptor_path(self) -> None:
        self.assertIn(
            ".agent-loop/long-run-continuation.json",
            self.contract_text,
            "docs/external-workspace-contract.md does not name the "
            "real shipped Phase 9E descriptor path "
            ".agent-loop/long-run-continuation.json",
        )

    def test_contract_does_not_use_stale_phase_9e_descriptor_path(
        self,
    ) -> None:
        self.assertNotIn(
            "long-run-loop.json", self.contract_text,
            "docs/external-workspace-contract.md references the "
            "stale / non-existent Phase 9E descriptor name "
            "long-run-loop.json; the real shipped path is "
            ".agent-loop/long-run-continuation.json",
        )

    def test_readme_phase_10a_does_not_use_stale_phase_9e_name(
        self,
    ) -> None:
        # The bug rode along in the Phase 10A README paragraph too;
        # pin the corrected name there.
        self.assertNotIn(
            "long-run-loop", self.readme_text,
            "README.md references the stale / non-existent Phase 9E "
            "descriptor name long-run-loop; the real shipped path is "
            ".agent-loop/long-run-continuation.json",
        )


class ExternalWorkspaceContractUsesCurrentPhase10DependencyMapTests(
    unittest.TestCase,
):
    """Phase 10B fix: the Phase 10A baseline contract's future-phase
    dependency map MUST match the current resliced Phase 10 plan, not
    the pre-reslice mapping that named Phase 10B as "bootstrap and
    attach flow" and Phase 10C as "runtime control / UI". The current
    canonical slicing is:

    - Phase 10B = External Target Attach Record Contract
    - Phase 10C = External Workspace Bootstrap Contract
    - Phase 10D = External Workspace Attach/Detach Runtime Initial Slice
    - Phase 10E = External Target Bootstrap Runtime
    - Phase 10F = Target-Side Cycle Dispatch
    - Phase 10G = External UI / Dashboard / Run-Control

    The previous fix cycle missed this because no test guarded the
    Phase 10A doc's dependency map; this class is the guard.
    """

    def setUp(self) -> None:
        self.text = _read(EXTERNAL_WORKSPACE_CONTRACT_PATH)
        self.collapsed = re.sub(r"\s+", " ", self.text)

    def test_contract_pins_corrected_phase_10_dependency_map(
        self,
    ) -> None:
        # Each Phase 10x label must be paired with its current
        # canonical title at least once in the doc.
        for label, title in (
            ("Phase 10B", "External Target Attach Record Contract"),
            ("Phase 10C", "External Workspace Bootstrap Contract"),
            (
                "Phase 10D",
                "External Workspace Attach/Detach Runtime "
                "Initial Slice",
            ),
            ("Phase 10E", "External Target Bootstrap Runtime"),
            ("Phase 10F", "Target-Side Cycle Dispatch"),
            (
                "Phase 10G",
                "External UI / Dashboard / Run-Control",
            ),
        ):
            self.assertIn(
                label, self.collapsed,
                f"docs/external-workspace-contract.md does not name "
                f"sub-phase {label!r}",
            )
            self.assertIn(
                title, self.collapsed,
                f"docs/external-workspace-contract.md does not name "
                f"the canonical title {title!r} for {label!r}",
            )

    def test_contract_does_not_use_pre_reslice_phase_10b_mapping(
        self,
    ) -> None:
        # The pre-reslice mapping put bootstrap-and-attach at 10B;
        # the current canonical slicing puts the attach-record
        # contract at 10B and the bootstrap contract at 10C.
        for stale_fragment in (
            "Phase 10B: external workspace bootstrap and attach flow",
            "Phase 10B: External Workspace Bootstrap",
            "external workspace bootstrap and attach flow",
        ):
            self.assertNotIn(
                stale_fragment, self.collapsed,
                f"docs/external-workspace-contract.md still carries "
                f"the pre-reslice Phase 10B mapping via "
                f"{stale_fragment!r}; the current canonical Phase "
                f"10B title is 'External Target Attach Record "
                f"Contract'",
            )

    def test_contract_does_not_use_pre_reslice_phase_10c_mapping(
        self,
    ) -> None:
        # The pre-reslice mapping put runtime control / UI at 10C;
        # the current canonical slicing puts the bootstrap contract
        # at 10C and the external UI at 10G.
        for stale_fragment in (
            "Phase 10C: external workspace runtime control",
            "Phase 10C and later) is advisory",
            "Phase 10C and later",
        ):
            self.assertNotIn(
                stale_fragment, self.collapsed,
                f"docs/external-workspace-contract.md still carries "
                f"the pre-reslice Phase 10C mapping via "
                f"{stale_fragment!r}; the current canonical Phase "
                f"10C title is 'External Workspace Bootstrap "
                f"Contract' and the external UI / dashboard surface "
                f"is now Phase 10G",
            )

    def test_contract_routes_external_ui_to_phase_10g(self) -> None:
        # The advisory external-UI / dashboard / notification-stream
        # disclaimer in the Source-Of-Truth-Preservation section
        # must point at Phase 10G now, not Phase 10C.
        self.assertIn(
            "Phase 10G", self.collapsed,
            "docs/external-workspace-contract.md does not route the "
            "external UI / dashboard / notification-stream advisory "
            "at Phase 10G",
        )


class ReadmePointsAtExternalWorkspaceContractDocTests(
    unittest.TestCase,
):
    """Phase 10A: the README must route a reader at the new contract
    doc and mark Phase 10A as the current active sub-phase.
    """

    def setUp(self) -> None:
        self.text = _read(README_PATH)

    def test_readme_names_external_workspace_contract_doc(self) -> None:
        # A clean-clone reader looking for the Phase 10A scope must be
        # routed at the new contract doc by name.
        self.assertIn(
            "docs/external-workspace-contract.md", self.text,
            "README.md does not route readers at the Phase 10A "
            "external-workspace contract doc",
        )


class ReadmeMarksPhase10aAsActiveTests(unittest.TestCase):
    """Phase 10A: README must name Phase 10A as the current active
    sub-phase, describe the documentation-only contract surface (the
    new `docs/external-workspace-contract.md` contract doc and the
    controller-owned vs target-owned ownership boundary it pins), and
    preserve the documented Phase 4 planner / Phase 4C activator
    boundary plus the Phase 9G final human acceptance gate so the
    contract does not silently weaken either.
    """

    def setUp(self) -> None:
        self.text = _read(README_PATH)

    def test_readme_marks_phase_10a_as_active(self) -> None:
        self.assertIn(
            "Phase 10A", self.text,
            "README.md does not name Phase 10A as a current focus",
        )
        self.assertIn(
            "External Workspace Controller Contract", self.text,
            "README.md does not name the Phase 10A sub-phase title",
        )

    def test_readme_names_the_shipped_contract_surface(self) -> None:
        for fragment in (
            "docs/external-workspace-contract.md",
            ".agent-loop/external-target.json",
            "controller-owned",
            "target-owned",
        ):
            self.assertIn(
                fragment, self.text,
                f"README.md Phase 10A paragraph does not name "
                f"shipped contract surface {fragment!r}",
            )

    def test_readme_preserves_planner_activator_boundary(
        self,
    ) -> None:
        # The Phase 10A paragraph must explicitly state that any
        # target-side phase activation continues to require the
        # shipped Phase 4C activator + APPROVED_FOR_ACTIVATION token.
        for fragment in (
            "Phase 4C activator",
            "APPROVED_FOR_ACTIVATION",
        ):
            self.assertIn(
                fragment, self.text,
                f"README.md Phase 10A paragraph does not preserve "
                f"the {fragment!r} boundary",
            )

    def test_readme_preserves_phase_9g_final_acceptance_gate(
        self,
    ) -> None:
        # The Phase 10A paragraph must explicitly state that the
        # Phase 9G final acceptance gate continues to apply per-target.
        self.assertIn(
            "Phase 9G final human acceptance gate", self.text,
            "README.md Phase 10A paragraph does not preserve the "
            "Phase 9G final human acceptance gate per target",
        )

    def test_readme_marks_phase_10a_as_documentation_only(self) -> None:
        # Phase 10A must NOT silently promise runtime behavior; the
        # paragraph must explicitly mark itself as documentation /
        # contract only with the runtime deferred to Phase 10B+.
        for fragment in (
            "documentation / contract only",
            "Phase 10B",
        ):
            self.assertIn(
                fragment, self.text,
                f"README.md Phase 10A paragraph does not document "
                f"the documentation-only scope fragment "
                f"{fragment!r}",
            )


class AttachRecordContractDocExistsAndIsWellFormedTests(
    unittest.TestCase,
):
    """Phase 10B: the external target attach record contract doc must
    exist on disk, be non-empty, be ASCII-only, and carry the canonical
    section headers a Phase 10D implementer reads.
    """

    def setUp(self) -> None:
        self.path = ATTACH_RECORD_CONTRACT_PATH
        self.text = _read(self.path)

    def test_doc_exists_and_non_empty(self) -> None:
        self.assertTrue(
            self.path.is_file(),
            f"Expected Phase 10B attach-record contract doc at "
            f"{self.path}",
        )
        self.assertGreater(self.path.stat().st_size, 0)

    def test_doc_is_ascii_only(self) -> None:
        raw = self.path.read_bytes()
        try:
            raw.decode("ascii")
        except UnicodeDecodeError as exc:
            self.fail(
                f"docs/external-target-attach-record-contract.md "
                f"contains non-ASCII bytes: {exc}"
            )

    def test_doc_has_required_top_level_sections(self) -> None:
        for header in (
            "# External Target Attach Record Contract",
            "## Status",
            "## Scope",
            "## Distinction From Other Shipped Artifacts",
            "## Canonical Location",
            "## Required Fields",
            "## Canonical Versus Advisory Fields",
            "## Path Canonicalization",
            "## Audit Expectations",
            "## Refusal Behavior",
            "## Approval Gates",
            "## Source-Of-Truth Preservation",
            "## Safety Boundaries",
            "## Dependencies On Later Phase 10 Slices",
            "## Out Of Scope For Phase 10B",
        ):
            self.assertIn(
                header, self.text,
                f"docs/external-target-attach-record-contract.md "
                f"missing required section header {header!r}",
            )


class AttachRecordContractPinsSchemaTests(unittest.TestCase):
    """The Phase 10B attach-record contract MUST pin every
    schema-stable field by name so a future Phase 10D implementer can
    write the record from this contract without further design
    decisions.
    """

    def setUp(self) -> None:
        self.text = _read(ATTACH_RECORD_CONTRACT_PATH)
        self.collapsed = re.sub(r"\s+", " ", self.text)

    def test_contract_pins_signal_version_marker(self) -> None:
        self.assertIn(
            "attach_record_signal_version", self.collapsed,
            "attach-record contract does not name the "
            "attach_record_signal_version field",
        )
        self.assertIn(
            "phase-10b-v1", self.collapsed,
            "attach-record contract does not pin the "
            "phase-10b-v1 signal-version string",
        )

    def test_contract_pins_canonical_location(self) -> None:
        self.assertIn(
            ".agent-loop/external-target.json", self.collapsed,
            "attach-record contract does not pin the canonical "
            "location .agent-loop/external-target.json",
        )

    def test_contract_pins_every_required_top_level_field(self) -> None:
        # Each top-level required field of the schema MUST be named
        # explicitly so the schema is concrete enough for Phase 10D.
        for field in (
            "attach_record_signal_version",
            "attached_at",
            "attached_by",
            "target_path_canonical",
            "target_path_raw",
            "controller_path_canonical",
            "controller_identity",
            "mode_selection",
            "bootstrap_state",
            "stale_attach_detection",
            "audit",
            "canonical_precedence_note",
        ):
            self.assertIn(
                field, self.collapsed,
                f"attach-record contract does not name required "
                f"top-level field {field!r}",
            )

    def test_contract_pins_mode_selection_enumeration(self) -> None:
        # The mode_selection.approval_mode enumeration is a closed
        # set; every value MUST be named.
        for value in (
            '"review"',
            '"strict"',
            '"autonomous"',
            '"phase_9_autonomous_prd"',
        ):
            self.assertIn(
                value, self.collapsed,
                f"attach-record contract does not name "
                f"mode_selection.approval_mode value {value!r}",
            )

    def test_contract_pins_bootstrap_state_enumeration(self) -> None:
        # The bootstrap_state.status enumeration is a closed set.
        for value in (
            '"target_canonical_set_present"',
            '"target_canonical_set_bootstrapped"',
        ):
            self.assertIn(
                value, self.collapsed,
                f"attach-record contract does not name "
                f"bootstrap_state.status value {value!r}",
            )


class AttachRecordContractPreservesShippedHardStopsTests(
    unittest.TestCase,
):
    """The Phase 10B contract MUST preserve the shipped hard stops
    (no Git automation in either root, the Phase 4C activator +
    APPROVED_FOR_ACTIVATION gate, the Phase 9G final human acceptance
    gate, the source-of-truth boundary). The Phase 10A baseline
    already pins these; the attach record contract MUST NOT silently
    weaken any of them.
    """

    def setUp(self) -> None:
        self.text = _read(ATTACH_RECORD_CONTRACT_PATH)
        self.collapsed = re.sub(r"\s+", " ", self.text)

    def test_contract_marks_runtime_as_not_yet_implemented(self) -> None:
        # Phase 10B is documentation-only; the doc must not silently
        # promise the runtime as shipped.
        self.assertIn(
            "is NOT yet implemented", self.collapsed,
            "attach-record contract does not mark the attach/detach "
            "runtime as not-yet-implemented",
        )

    def test_contract_locates_future_runtime_in_phase_10c_or_later(
        self,
    ) -> None:
        for sub_phase in (
            "Phase 10C",
            "Phase 10D",
            "Phase 10E",
        ):
            self.assertIn(
                sub_phase, self.collapsed,
                f"attach-record contract does not name "
                f"{sub_phase!r} as the locus for the corresponding "
                f"future runtime work",
            )

    def test_contract_preserves_no_git_automation(self) -> None:
        # The repo-wide no-Git-automation boundary must apply in
        # BOTH roots (controller and target) under Phase 10B too.
        for fragment in (
            "commit, push, tag, branch, stash, reset, checkout",
            "BOTH roots",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"attach-record contract does not preserve the "
                f"no-Git-automation boundary via {fragment!r}",
            )

    def test_contract_preserves_approved_for_activation(self) -> None:
        self.assertIn(
            "APPROVED_FOR_ACTIVATION", self.collapsed,
            "attach-record contract does not preserve the "
            "APPROVED_FOR_ACTIVATION human-approval gate",
        )
        self.assertIn(
            "Phase 4C activator", self.collapsed,
            "attach-record contract does not name the Phase 4C "
            "activator as the preserved activation step",
        )

    def test_contract_preserves_final_human_acceptance_gate(
        self,
    ) -> None:
        self.assertIn(
            "Phase 9G", self.collapsed,
            "attach-record contract does not name the Phase 9G "
            "final acceptance gate as a preserved boundary",
        )

    def test_contract_preserves_canonical_artifact_source_of_truth(
        self,
    ) -> None:
        # The contract must say explicitly that canonical artifacts
        # win and that future UI / cache is advisory.
        for fragment in (
            "canonical artifacts on disk remain authoritative",
            "advisory",
        ):
            self.assertIn(
                fragment, self.collapsed.lower(),
                f"attach-record contract does not preserve the "
                f"source-of-truth model via {fragment!r}",
            )

    def test_contract_refuses_silent_autonomy_widening(self) -> None:
        # The runtime MUST NOT default approval_mode to autonomous /
        # phase_9_autonomous_prd without operator input. Pin both
        # half-fragments.
        self.assertIn(
            "silently widen", self.collapsed.lower(),
            "attach-record contract does not refuse silent autonomy "
            "widening at attach time",
        )

    def test_contract_refuses_silent_attached_by_autofill(self) -> None:
        # The runtime MUST NOT auto-fill attached_by from $USER /
        # whoami; the operator must claim identity explicitly.
        self.assertIn(
            "attached_by", self.collapsed,
            "attach-record contract does not name attached_by",
        )
        for fragment in ("$USER", "whoami"):
            self.assertIn(
                fragment, self.collapsed,
                f"attach-record contract does not explicitly refuse "
                f"auto-fill of attached_by from {fragment!r}",
            )


class ReadmePointsAtAttachRecordContractDocTests(unittest.TestCase):
    """Phase 10B: the README must route a reader at the new contract
    doc and mark Phase 10B as the current active sub-phase.
    """

    def setUp(self) -> None:
        self.text = _read(README_PATH)

    def test_readme_names_attach_record_contract_doc(self) -> None:
        self.assertIn(
            "docs/external-target-attach-record-contract.md",
            self.text,
            "README.md does not route readers at the Phase 10B "
            "attach-record contract doc",
        )


class ReadmeMarksPhase10bAsActiveTests(unittest.TestCase):
    """Phase 10B: README must name Phase 10B as the current active
    sub-phase, describe the documentation-only contract surface (the
    new `docs/external-target-attach-record-contract.md` contract
    doc, the canonical attach-record location, and the schema-stable
    fields), and preserve the documented Phase 4 planner / Phase 4C
    activator boundary plus the Phase 9G final human acceptance gate
    so the contract does not silently weaken either.
    """

    def setUp(self) -> None:
        self.text = _read(README_PATH)

    def test_readme_marks_phase_10b_as_active(self) -> None:
        self.assertIn(
            "Phase 10B", self.text,
            "README.md does not name Phase 10B as a current focus",
        )
        self.assertIn(
            "External Target Attach Record Contract", self.text,
            "README.md does not name the Phase 10B sub-phase title",
        )

    def test_readme_names_the_shipped_contract_surface(self) -> None:
        for fragment in (
            "docs/external-target-attach-record-contract.md",
            ".agent-loop/external-target.json",
            "attach_record_signal_version",
            "phase-10b-v1",
            "target_path_canonical",
            "controller_identity",
            "mode_selection",
            "bootstrap_state",
            "stale_attach_detection",
        ):
            self.assertIn(
                fragment, self.text,
                f"README.md Phase 10B paragraph does not name "
                f"shipped contract surface {fragment!r}",
            )

    def test_readme_preserves_planner_activator_boundary(self) -> None:
        for fragment in (
            "Phase 4C activator",
            "APPROVED_FOR_ACTIVATION",
        ):
            self.assertIn(
                fragment, self.text,
                f"README.md Phase 10B paragraph does not preserve "
                f"the {fragment!r} boundary",
            )

    def test_readme_preserves_phase_9g_final_acceptance_gate(
        self,
    ) -> None:
        self.assertIn(
            "Phase 9G final human acceptance gate", self.text,
            "README.md Phase 10B paragraph does not preserve the "
            "Phase 9G final human acceptance gate per target",
        )

    def test_readme_marks_phase_10b_as_documentation_only(self) -> None:
        for fragment in (
            "documentation / contract only",
            "Phase 10D",
        ):
            self.assertIn(
                fragment, self.text,
                f"README.md Phase 10B paragraph does not document "
                f"the documentation-only scope fragment "
                f"{fragment!r}",
            )


class BootstrapContractDocExistsAndIsWellFormedTests(
    unittest.TestCase,
):
    """Phase 10C: the external workspace bootstrap contract doc must
    exist on disk, be non-empty, be ASCII-only, and carry the canonical
    section headers a Phase 10E implementer reads.
    """

    def setUp(self) -> None:
        self.path = BOOTSTRAP_CONTRACT_PATH
        self.text = _read(self.path)

    def test_doc_exists_and_non_empty(self) -> None:
        self.assertTrue(
            self.path.is_file(),
            f"Expected Phase 10C bootstrap contract doc at "
            f"{self.path}",
        )
        self.assertGreater(self.path.stat().st_size, 0)

    def test_doc_is_ascii_only(self) -> None:
        raw = self.path.read_bytes()
        try:
            raw.decode("ascii")
        except UnicodeDecodeError as exc:
            self.fail(
                f"docs/external-workspace-bootstrap-contract.md "
                f"contains non-ASCII bytes: {exc}"
            )

    def test_doc_has_required_top_level_sections(self) -> None:
        for header in (
            "# External Workspace Bootstrap Contract",
            "## Status",
            "## Scope",
            "## Distinction From Other Shipped Artifacts",
            "## Canonical Artifact Set The Bootstrap May Write",
            "## Initial Contents Of Each Canonical Artifact",
            "## Pre-Bootstrap Target States",
            "## Operator Opt-In",
            "## Bootstrap-State Field Schema",
            "## Refusal Behavior",
            "## Approval Gates",
            "## Audit Expectations",
            "## Source-Of-Truth Preservation",
            "## Safety Boundaries",
            "## Dependencies On Later Phase 10 Slices",
            "## Out Of Scope For Phase 10C",
        ):
            self.assertIn(
                header, self.text,
                f"docs/external-workspace-bootstrap-contract.md "
                f"missing required section header {header!r}",
            )


class BootstrapContractPinsSchemaTests(unittest.TestCase):
    """The Phase 10C bootstrap contract MUST pin the canonical
    artifact set, pre-bootstrap state enumeration, and bootstrap-state
    extension fields by name so a future Phase 10E implementer can
    write the bootstrap runtime from this contract without further
    design decisions.
    """

    def setUp(self) -> None:
        self.text = _read(BOOTSTRAP_CONTRACT_PATH)
        self.collapsed = re.sub(r"\s+", " ", self.text)

    def test_contract_pins_signal_version_marker(self) -> None:
        self.assertIn(
            "bootstrap_signal_version", self.collapsed,
            "bootstrap contract does not name the "
            "bootstrap_signal_version field",
        )
        self.assertIn(
            "phase-10c-v1", self.collapsed,
            "bootstrap contract does not pin the phase-10c-v1 "
            "signal-version string",
        )

    def test_contract_pins_canonical_artifact_set(self) -> None:
        # The five target-side canonical artifacts bootstrap may
        # write (and only those five).
        for path in (
            "`TASK.md`",
            "`.agent-loop/current-task.md`",
            "`.agent-loop/current-phase.md`",
            "`.agent-loop/phase-plan.md`",
            "`.agent-loop/loop-state.json`",
        ):
            self.assertIn(
                path, self.collapsed,
                f"bootstrap contract does not name target-side "
                f"canonical artifact {path!r}",
            )

    def test_contract_pins_pre_bootstrap_state_enumeration(
        self,
    ) -> None:
        # The four pre-bootstrap target states; the enumeration is
        # closed.
        for value in (
            "empty_target",
            "partial_target",
            "full_target",
            "malformed_target",
        ):
            self.assertIn(
                value, self.collapsed,
                f"bootstrap contract does not name pre-bootstrap "
                f"target-state value {value!r}",
            )

    def test_contract_pins_bootstrap_state_extension_fields(
        self,
    ) -> None:
        # Six required extension fields for the Phase 10B attach
        # record's bootstrap_state sub-object when bootstrap was
        # performed.
        for field in (
            "bootstrap_signal_version",
            "pre_bootstrap_target_state",
            "artifacts_written",
            "initial_loop_state_status",
            "initial_human_objective_excerpt",
            "bootstrap_log_line",
        ):
            self.assertIn(
                field, self.collapsed,
                f"bootstrap contract does not name required "
                f"bootstrap-state extension field {field!r}",
            )

    def test_contract_pins_initial_loop_state_status(self) -> None:
        # The new awaiting_first_activation status the Phase 10E
        # bootstrap runtime introduces (no shipped status fits a
        # bootstrapped-but-not-activated target).
        self.assertIn(
            "awaiting_first_activation", self.collapsed,
            "bootstrap contract does not pin the new "
            "awaiting_first_activation loop-state.status value",
        )


class BootstrapContractPreservesShippedHardStopsTests(
    unittest.TestCase,
):
    """The Phase 10C contract MUST preserve the shipped hard stops
    (no Git automation, the Phase 4C activator + APPROVED_FOR_ACTIVATION
    gate, the Phase 9G final human acceptance gate, the
    source-of-truth boundary, the bootstrap-never-overwrites
    guarantee). The Phase 10A + 10B baselines already pin most of
    these; the bootstrap contract MUST NOT silently weaken any.
    """

    def setUp(self) -> None:
        self.text = _read(BOOTSTRAP_CONTRACT_PATH)
        self.collapsed = re.sub(r"\s+", " ", self.text)

    def test_contract_marks_runtime_as_implemented(self) -> None:
        # Phase 10E shipped the bootstrap runtime; the contract's
        # Status section must reflect that the runtime is implemented
        # so a future reader does not assume the bootstrap surface is
        # still documentation-only.
        self.assertNotIn(
            "is NOT yet implemented", self.collapsed,
            "bootstrap contract still claims the runtime is "
            "not-yet-implemented; Phase 10E shipped the runtime and "
            "the Status section must reflect that",
        )
        self.assertIn(
            "Phase 10E runtime slice implements", self.collapsed,
            "bootstrap contract does not announce that the Phase 10E "
            "runtime slice implements the bootstrap surface",
        )

    def test_contract_locates_future_runtime_in_phase_10d_or_later(
        self,
    ) -> None:
        for sub_phase in (
            "Phase 10D",
            "Phase 10E",
            "Phase 10F",
            "Phase 10G",
        ):
            self.assertIn(
                sub_phase, self.collapsed,
                f"bootstrap contract does not name {sub_phase!r} "
                f"as the locus for the corresponding future runtime "
                f"work",
            )

    def test_contract_preserves_no_git_automation(self) -> None:
        for fragment in (
            "commit, push, tag, branch, stash, reset, checkout",
            "BOTH roots",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"bootstrap contract does not preserve the "
                f"no-Git-automation boundary via {fragment!r}",
            )

    def test_contract_preserves_approved_for_activation(self) -> None:
        self.assertIn(
            "APPROVED_FOR_ACTIVATION", self.collapsed,
            "bootstrap contract does not preserve the "
            "APPROVED_FOR_ACTIVATION human-approval gate",
        )
        self.assertIn(
            "Phase 4C activator", self.collapsed,
            "bootstrap contract does not name the Phase 4C "
            "activator as the preserved activation step",
        )

    def test_contract_preserves_final_human_acceptance_gate(
        self,
    ) -> None:
        self.assertIn(
            "Phase 9G", self.collapsed,
            "bootstrap contract does not name the Phase 9G final "
            "acceptance gate as a preserved boundary",
        )

    def test_contract_preserves_canonical_artifact_source_of_truth(
        self,
    ) -> None:
        for fragment in (
            "canonical artifacts on disk remain authoritative",
            "advisory",
        ):
            self.assertIn(
                fragment, self.collapsed.lower(),
                f"bootstrap contract does not preserve the "
                f"source-of-truth model via {fragment!r}",
            )

    def test_contract_pins_bootstrap_never_overwrites(self) -> None:
        # The load-bearing guarantee: bootstrap MUST NOT overwrite
        # an existing canonical artifact even if it is malformed.
        for fragment in (
            "bootstrap never overwrites",
            "MUST NOT overwrite",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"bootstrap contract does not pin the "
                f"bootstrap-never-overwrites guarantee via "
                f"{fragment!r}",
            )

    def test_contract_refuses_silent_autonomy_widening(self) -> None:
        # bootstrap_by MUST NOT auto-fill from $USER / whoami.
        self.assertIn(
            "auto-fill", self.collapsed.lower(),
            "bootstrap contract does not refuse silent identity "
            "auto-fill",
        )
        for fragment in ("$USER", "whoami"):
            self.assertIn(
                fragment, self.collapsed,
                f"bootstrap contract does not explicitly refuse "
                f"auto-fill of bootstrapped_by from {fragment!r}",
            )


class ReadmePointsAtBootstrapContractDocTests(unittest.TestCase):
    """Phase 10C: the README must route a reader at the new contract
    doc and mark Phase 10C as the current active sub-phase.
    """

    def setUp(self) -> None:
        self.text = _read(README_PATH)

    def test_readme_names_bootstrap_contract_doc(self) -> None:
        self.assertIn(
            "docs/external-workspace-bootstrap-contract.md",
            self.text,
            "README.md does not route readers at the Phase 10C "
            "bootstrap contract doc",
        )


class ReadmeMarksPhase10cAsActiveTests(unittest.TestCase):
    """Phase 10C: README must name Phase 10C as the current active
    sub-phase, describe the documentation-only contract surface (the
    new doc, the five canonical artifacts bootstrap may write, the
    four-value pre-bootstrap state enumeration, the six bootstrap-
    state extension fields, the new awaiting_first_activation
    status), and preserve the documented Phase 4 planner / Phase 4C
    activator boundary plus the Phase 9G final human acceptance
    gate so the contract does not silently weaken either.
    """

    def setUp(self) -> None:
        self.text = _read(README_PATH)

    def test_readme_marks_phase_10c_as_active(self) -> None:
        self.assertIn(
            "Phase 10C", self.text,
            "README.md does not name Phase 10C as a current focus",
        )
        self.assertIn(
            "External Workspace Bootstrap Contract", self.text,
            "README.md does not name the Phase 10C sub-phase title",
        )

    def test_readme_names_the_shipped_contract_surface(self) -> None:
        for fragment in (
            "docs/external-workspace-bootstrap-contract.md",
            "bootstrap_signal_version",
            "phase-10c-v1",
            "empty_target",
            "partial_target",
            "full_target",
            "malformed_target",
            "pre_bootstrap_target_state",
            "artifacts_written",
            "initial_loop_state_status",
            "awaiting_first_activation",
            "bootstrap_log_line",
        ):
            self.assertIn(
                fragment, self.text,
                f"README.md Phase 10C paragraph does not name "
                f"shipped contract surface {fragment!r}",
            )

    def test_readme_preserves_planner_activator_boundary(self) -> None:
        for fragment in (
            "Phase 4C activator",
            "APPROVED_FOR_ACTIVATION",
        ):
            self.assertIn(
                fragment, self.text,
                f"README.md Phase 10C paragraph does not preserve "
                f"the {fragment!r} boundary",
            )

    def test_readme_preserves_phase_9g_final_acceptance_gate(
        self,
    ) -> None:
        self.assertIn(
            "Phase 9G final human acceptance gate", self.text,
            "README.md Phase 10C paragraph does not preserve the "
            "Phase 9G final human acceptance gate per target",
        )

    def test_readme_marks_phase_10c_as_documentation_only(self) -> None:
        for fragment in (
            "documentation / contract only",
            "Phase 10E",
        ):
            self.assertIn(
                fragment, self.text,
                f"README.md Phase 10C paragraph does not document "
                f"the documentation-only scope fragment "
                f"{fragment!r}",
            )


class Phase10cTitleAlignmentAcrossContractStackTests(
    unittest.TestCase,
):
    """Phase 10C fix: the layered Phase 10 contract stack MUST use the
    same canonical Phase 10C title everywhere. The active title is
    `External Workspace Bootstrap Contract`. An older draft used
    `External Target Bootstrap Contract`; the drift currently appears
    only in cross-references inside the Phase 10A baseline contract
    and the Phase 10B attach-record contract. This class is the guard
    that fails-closed if either doc drifts back to the stale title.

    The Phase 10C doc itself is covered by
    `BootstrapContractDocExistsAndIsWellFormedTests`; this class
    covers the cross-references in the sibling Phase 10A and 10B
    contract docs.
    """

    CORRECT_TITLE = "External Workspace Bootstrap Contract"
    STALE_TITLE = "External Target Bootstrap Contract"

    def setUp(self) -> None:
        self.workspace = _read(EXTERNAL_WORKSPACE_CONTRACT_PATH)
        self.attach = _read(ATTACH_RECORD_CONTRACT_PATH)
        self.workspace_collapsed = re.sub(
            r"\s+", " ", self.workspace,
        )
        self.attach_collapsed = re.sub(r"\s+", " ", self.attach)

    def test_workspace_contract_uses_correct_phase_10c_title(
        self,
    ) -> None:
        self.assertIn(
            self.CORRECT_TITLE, self.workspace_collapsed,
            f"docs/external-workspace-contract.md does not name the "
            f"canonical Phase 10C title {self.CORRECT_TITLE!r}",
        )

    def test_workspace_contract_does_not_use_stale_phase_10c_title(
        self,
    ) -> None:
        self.assertNotIn(
            self.STALE_TITLE, self.workspace_collapsed,
            f"docs/external-workspace-contract.md still names the "
            f"stale Phase 10C title {self.STALE_TITLE!r}; the "
            f"current canonical title is {self.CORRECT_TITLE!r}",
        )

    def test_attach_record_contract_uses_correct_phase_10c_title(
        self,
    ) -> None:
        self.assertIn(
            self.CORRECT_TITLE, self.attach_collapsed,
            f"docs/external-target-attach-record-contract.md does "
            f"not name the canonical Phase 10C title "
            f"{self.CORRECT_TITLE!r}",
        )

    def test_attach_record_contract_does_not_use_stale_phase_10c_title(
        self,
    ) -> None:
        self.assertNotIn(
            self.STALE_TITLE, self.attach_collapsed,
            f"docs/external-target-attach-record-contract.md still "
            f"names the stale Phase 10C title "
            f"{self.STALE_TITLE!r}; the current canonical title is "
            f"{self.CORRECT_TITLE!r}",
        )


class ReadmePhase10cBootstrapWriteBoundaryWordingTests(
    unittest.TestCase,
):
    """Phase 10C fix: the README's Phase 10C paragraph MUST describe
    bootstrap's write boundary accurately. The original wording said
    the five canonical artifacts may be written by bootstrap "and
    ONLY by bootstrap", which overstated the contract: the Phase 4C
    activator and the shipped Phase 3A orchestrator also rewrite
    those same target-side canonical artifacts on per-target activation
    and per-cycle updates. The corrected wording constrains
    bootstrap's own write boundary without claiming bootstrap is the
    only runtime that may ever touch those files.
    """

    def setUp(self) -> None:
        self.text = _read(README_PATH)

    def test_readme_does_not_overstate_bootstrap_write_ownership(
        self,
    ) -> None:
        # The "and ONLY by bootstrap" wording is the overstatement.
        self.assertNotIn(
            "and ONLY by bootstrap", self.text,
            "README.md Phase 10C paragraph still uses the "
            "overstated 'and ONLY by bootstrap' wording; Phase 10C "
            "only constrains bootstrap's own write boundary, not "
            "the long-term write ownership of the five canonical "
            "artifacts (the Phase 4C activator and the shipped "
            "Phase 3A orchestrator also rewrite those files)",
        )

    def test_readme_names_other_runtimes_that_rewrite_canonical_files(
        self,
    ) -> None:
        # The corrected wording should explicitly name at least one
        # of the other shipped runtimes that legitimately rewrites
        # these target-side canonical artifacts after bootstrap so a
        # reader sees the bootstrap write boundary is bootstrap-
        # scoped, not lifetime-scoped.
        for fragment in (
            "Phase 4C activator on per-target phase activation",
            "Phase 3A orchestrator",
        ):
            self.assertIn(
                fragment, self.text,
                f"README.md Phase 10C paragraph does not name "
                f"the shipped runtime {fragment!r} that "
                f"legitimately rewrites the same canonical files "
                f"after bootstrap; the corrected wording must "
                f"make clear bootstrap is not the only writer",
            )


# ---------------------------------------------------------------------------
# Phase 10G - Minimal External UI Contract: documentation tests
# ---------------------------------------------------------------------------
class ExternalUiContractDocExistsAndIsWellFormedTests(
    unittest.TestCase,
):
    """Phase 10G: the minimal external UI contract doc must exist on
    disk, be non-empty, be ASCII-only, and carry the canonical section
    headers a future Phase 10H implementer reads.
    """

    def setUp(self) -> None:
        self.path = EXTERNAL_UI_CONTRACT_PATH
        self.text = _read(self.path)

    def test_doc_exists_and_non_empty(self) -> None:
        self.assertTrue(
            self.path.is_file(),
            f"Expected Phase 10G external-UI contract doc at "
            f"{self.path}",
        )
        self.assertGreater(self.path.stat().st_size, 0)

    def test_doc_is_ascii_only(self) -> None:
        raw = self.path.read_bytes()
        try:
            raw.decode("ascii")
        except UnicodeDecodeError as exc:
            self.fail(
                f"docs/external-ui-contract.md contains non-ASCII "
                f"bytes: {exc}"
            )

    def test_doc_has_required_top_level_sections(self) -> None:
        for header in (
            "# Minimal External UI Contract",
            "## Status",
            "## Scope",
            "## Distinction From Shipped Artifacts And Surfaces",
            "## Canonical Artifacts The Minimal UI May Read",
            "## Advisory-Vs-Canonical Mirror Rule",
            "## Operations That Remain CLI-Only",
            "## UI Identity And Operator Attribution",
            "## Refusal Behavior",
            "## Source-Of-Truth Preservation",
            "## Safety Boundaries",
            "## Approval Gates",
            "## Audit Expectations",
            "## Dependencies On Later Phase 10 Slices",
            "## Out Of Scope For Phase 10G",
        ):
            self.assertIn(
                header, self.text,
                f"docs/external-ui-contract.md missing required "
                f"section header {header!r}",
            )


class ExternalUiContractPinsReadOnlyArtifactSetTests(
    unittest.TestCase,
):
    """Phase 10G: the UI contract MUST enumerate the canonical
    artifacts the future UI may read on both the controller and the
    target side, so a Phase 10H implementer can build the read set
    without further design decisions.
    """

    def setUp(self) -> None:
        self.text = _read(EXTERNAL_UI_CONTRACT_PATH)
        self.collapsed = re.sub(r"\s+", " ", self.text)

    def test_contract_names_controller_side_canonical_artifacts(
        self,
    ) -> None:
        for fragment in (
            ".agent-loop/external-target.json",
            ".agent-loop/loop-state.json",
            ".agent-loop/orchestrator.log",
            ".agent-loop/proposed-phase.md",
            ".agent-loop/current-task.md",
            ".agent-loop/current-phase.md",
            ".agent-loop/claude-prompt.md",
            ".agent-loop/claude-summary.md",
            ".agent-loop/codex-review.md",
            ".agent-loop/fix-prompt.md",
            ".agent-loop/final-acceptance.json",
            "TASK.md",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"external-ui contract does not name controller-side "
                f"canonical artifact {fragment!r} in its UI read set",
            )

    def test_contract_names_target_side_artifacts(self) -> None:
        # The UI may read target-side artifacts only when an attach
        # record is present and fresh; the doc must say so.
        self.assertIn(
            "attach record is present and fresh", self.collapsed,
            "external-ui contract does not gate target-side reads on "
            "attach-record-presence + freshness",
        )


class ExternalUiContractPinsAdvisoryMirrorRuleTests(
    unittest.TestCase,
):
    """The contract MUST distinguish canonical mirrors (verbatim
    renderings of on-disk artifact values, attributed to the source
    artifact, refreshed per poll) from advisory derived state
    (UI-computed values from canonical mirrors that MUST be marked as
    advisory). Without this distinction the UI could promote derived
    values to a source of truth.
    """

    def setUp(self) -> None:
        self.text = _read(EXTERNAL_UI_CONTRACT_PATH)
        self.collapsed = re.sub(r"\s+", " ", self.text)

    def test_contract_pins_canonical_mirror_vocabulary(self) -> None:
        for fragment in (
            "Canonical mirror",
            "Advisory derived state",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"external-ui contract does not pin the "
                f"{fragment!r} vocabulary",
            )

    def test_contract_prohibits_cross_snapshot_merging(self) -> None:
        # The UI MUST NOT show two values from different on-disk
        # snapshots in the same rendered record; without this rule
        # the UI could silently merge stale state.
        self.assertIn(
            "cross-merge", self.collapsed,
        )
        self.assertIn(
            "one consistent on-disk snapshot", self.collapsed,
            "external-ui contract does not prohibit cross-snapshot "
            "merging in a single rendered record",
        )

    def test_contract_prohibits_caching_past_poll_cycle(self) -> None:
        self.assertIn(
            "MUST NOT cache", self.collapsed,
        )
        self.assertIn(
            "single poll cycle", self.collapsed,
            "external-ui contract does not prohibit caching beyond a "
            "single poll cycle",
        )


class ExternalUiContractPinsCliOnlyOperationsTests(unittest.TestCase):
    """The Phase 10G contract MUST enumerate the shipped mutating
    operations the UI is not allowed to silently trigger. A future
    Phase 10H runtime that proxies a mutating CLI from a UI button
    would break this contract; the doc names the operations
    explicitly.
    """

    def setUp(self) -> None:
        self.text = _read(EXTERNAL_UI_CONTRACT_PATH)
        self.collapsed = re.sub(r"\s+", " ", self.text)

    def test_contract_names_cli_only_mutating_operations(self) -> None:
        for op in (
            "attach-external-target",
            "detach-external-target",
            "verify-external-target",
            "plan",
            "activate",
            "run",
            "resume",
            "auto-continue",
            "record-final-acceptance",
        ):
            self.assertIn(
                f"`{op}`", self.collapsed,
                f"external-ui contract does not name CLI-only "
                f"mutating operation {op!r}",
            )

    def test_contract_prohibits_ui_dispatch_of_mutating_cli(
        self,
    ) -> None:
        self.assertIn(
            "MUST NOT issue, dispatch, proxy, auto-trigger, "
            "queue, or schedule", self.collapsed,
            "external-ui contract does not explicitly prohibit the "
            "UI from dispatching mutating CLI operations",
        )

    def test_contract_permits_copy_to_clipboard_but_not_execute(
        self,
    ) -> None:
        for fragment in (
            "COPIES the equivalent CLI command",
            "MUST NOT execute the command on the operator's behalf",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"external-ui contract does not pin the "
                f"copy-paste-but-not-execute rule via {fragment!r}",
            )


class ExternalUiContractPreservesShippedHardStopsTests(
    unittest.TestCase,
):
    """The Phase 10G contract MUST preserve the shipped hard stops
    (no Git automation in either root, the Phase 4C activator + the
    APPROVED_FOR_ACTIVATION token, the Phase 9G final human
    acceptance gate, the no-auto-fill operator-identity invariants,
    the controller-vs-target ownership boundary, the source-of-truth
    boundary). The Phase 10A - 10F baselines pin most of these; the
    UI contract MUST NOT silently weaken any.
    """

    def setUp(self) -> None:
        self.text = _read(EXTERNAL_UI_CONTRACT_PATH)
        self.collapsed = re.sub(r"\s+", " ", self.text)

    def test_contract_preserves_no_git_automation(self) -> None:
        for fragment in (
            "commit, push, tag, branch, stash, reset, checkout",
            "BOTH roots",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"external-ui contract does not preserve the "
                f"no-Git-automation boundary via {fragment!r}",
            )

    def test_contract_preserves_approved_for_activation(self) -> None:
        self.assertIn(
            "APPROVED_FOR_ACTIVATION", self.collapsed,
            "external-ui contract does not preserve the "
            "APPROVED_FOR_ACTIVATION human-approval gate",
        )
        self.assertIn(
            "Phase 4C activator", self.collapsed,
            "external-ui contract does not name the Phase 4C "
            "activator as the preserved activation step",
        )

    def test_contract_preserves_phase_9g_acceptance_gate(self) -> None:
        self.assertIn(
            "Phase 9G", self.collapsed,
            "external-ui contract does not name the Phase 9G final "
            "acceptance gate as a preserved boundary",
        )
        self.assertIn(
            "record-final-acceptance", self.collapsed,
            "external-ui contract does not name the shipped "
            "record-final-acceptance CLI as the canonical acceptance "
            "writer",
        )

    def test_contract_refuses_silent_identity_autofill(self) -> None:
        # Operator-identity fields MUST NOT be auto-filled from
        # browser session, env vars, or any UI-side identity store.
        self.assertIn(
            "MUST NOT auto-fill", self.collapsed,
            "external-ui contract does not refuse silent identity "
            "auto-fill",
        )
        for fragment in (
            "browser session",
            "$USER",
            "whoami",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"external-ui contract does not explicitly refuse "
                f"identity auto-fill from {fragment!r}",
            )

    def test_contract_pins_canonical_artifact_source_of_truth(
        self,
    ) -> None:
        for fragment in (
            "canonical artifacts on disk remain authoritative",
            "must not introduce a ui-side database",
        ):
            self.assertIn(
                fragment, self.collapsed.lower(),
                f"external-ui contract does not preserve the "
                f"source-of-truth model via {fragment!r}",
            )

    def test_contract_preserves_controller_target_ownership(
        self,
    ) -> None:
        for fragment in (
            "controller-vs-target ownership boundary",
            "controller-owned",
            "target-side",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"external-ui contract does not preserve the "
                f"controller-vs-target ownership boundary via "
                f"{fragment!r}",
            )

    def test_contract_marks_phase_10h_runtime_as_shipped(
        self,
    ) -> None:
        # Phase 10H ships the first runtime surface that satisfies
        # this contract; the doc must announce that the bounded
        # read-only viewer is implemented and must NOT carry the
        # stale "No external UI runtime ships" claim. Later
        # external-UI slices (Phase 10I+) remain deferred and the
        # contract must say so.
        self.assertNotIn(
            "No external UI runtime", self.collapsed,
            "external-ui contract still carries the stale "
            "'No external UI runtime' claim after Phase 10H "
            "shipped the read-only viewer",
        )
        for fragment in (
            "Phase 10H",
            "SHIPPED",
            "build_external_ui_status_view",
            "view-external-status",
            "Phase 10I",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"external-ui contract does not surface Phase 10H "
                f"shipped marker {fragment!r}",
            )


class ExternalUiContractEnumeratesRefusalsTests(unittest.TestCase):
    """The Phase 10G contract MUST enumerate the cases in which the
    future UI is required to refuse fail-closed (render an error
    state rather than silently proceed). The enumeration lets a
    Phase 10H implementer build the error-state vocabulary without
    further design decisions.
    """

    def setUp(self) -> None:
        self.text = _read(EXTERNAL_UI_CONTRACT_PATH)
        self.collapsed = re.sub(r"\s+", " ", self.text)

    def test_contract_names_required_refusal_cases(self) -> None:
        for fragment in (
            "attach record is missing",
            "freshness probe reports drift",
            "filesystem permission denial",
            "signal-version marker",
            "APPROVED_FOR_ACTIVATION",
            "same-root / nesting refusal",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"external-ui contract does not enumerate the "
                f"refusal case named by {fragment!r}",
            )

    def test_contract_routes_refusals_to_shipped_cli_remediation(
        self,
    ) -> None:
        self.assertIn(
            "shipped CLI remediation step", self.collapsed,
            "external-ui contract does not route UI error states to "
            "shipped CLI remediation",
        )


class ReadmePointsAtExternalUiContractDocTests(unittest.TestCase):
    """Phase 10G: the README must route a reader at the new contract
    doc and mark Phase 10G as the current active sub-phase.
    """

    def setUp(self) -> None:
        self.text = _read(README_PATH)

    def test_readme_names_external_ui_contract_doc(self) -> None:
        self.assertIn(
            "docs/external-ui-contract.md", self.text,
            "README.md does not route readers at the Phase 10G "
            "external-UI contract doc",
        )


class ReadmeMarksPhase10gAsActiveTests(unittest.TestCase):
    """Phase 10G: README must name Phase 10G as the current active
    sub-phase, describe the documentation-only contract surface (the
    canonical artifact read set, the advisory-vs-canonical mirror
    rule, the CLI-only operations, the no-auto-fill operator-
    identity invariant), and preserve the documented Phase 4C
    activator boundary and the Phase 9G final human acceptance gate
    so the UI contract does not silently weaken either.
    """

    def setUp(self) -> None:
        self.text = _read(README_PATH)

    def test_readme_marks_phase_10g_as_active(self) -> None:
        self.assertIn(
            "Phase 10G", self.text,
            "README.md does not name Phase 10G as a current focus",
        )
        self.assertIn(
            "Minimal External UI Contract", self.text,
            "README.md does not name the Phase 10G sub-phase title",
        )

    def test_readme_names_shipped_contract_surface(self) -> None:
        for fragment in (
            "docs/external-ui-contract.md",
            "advisory-vs-canonical mirror rule",
            "CLI-only operation",
            "attach-external-target",
            "verify-external-target",
            "record-final-acceptance",
            "Phase 4C activator",
            "APPROVED_FOR_ACTIVATION",
        ):
            self.assertIn(
                fragment, self.text,
                f"README.md Phase 10G paragraph does not name "
                f"shipped contract surface {fragment!r}",
            )

    def test_readme_preserves_phase_9g_final_acceptance_gate(
        self,
    ) -> None:
        self.assertIn(
            "Phase 9G", self.text,
            "README.md Phase 10G paragraph does not name the Phase "
            "9G acceptance gate as a preserved boundary",
        )

    def test_readme_marks_phase_10g_as_documentation_only(self) -> None:
        for fragment in (
            "documentation form only",
            "Phase 10H",
        ):
            self.assertIn(
                fragment, self.text,
                f"README.md Phase 10G paragraph does not document "
                f"the documentation-only scope fragment "
                f"{fragment!r}",
            )

    def test_readme_routes_advanced_ui_to_phase_10h_or_later(
        self,
    ) -> None:
        # Future UI capabilities must be routed to Phase 10H/10I so a
        # reader does not assume they ship in 10G.
        for fragment in (
            "Phase 10H",
            "Phase 10I",
            "concurrent-attach awareness",
        ):
            self.assertIn(
                fragment, self.text,
                f"README.md Phase 10G paragraph does not route "
                f"future UI capability {fragment!r} to a later "
                f"sub-phase",
            )


# ---------------------------------------------------------------------------
# Phase 10J - Artifact Dashboard Contract: documentation tests
# ---------------------------------------------------------------------------
class ArtifactDashboardContractDocExistsAndIsWellFormedTests(
    unittest.TestCase,
):
    """Phase 10J: the artifact dashboard contract doc must exist on
    disk, be non-empty, be ASCII-only, and carry the canonical section
    headers a future Phase 10K implementer reads.
    """

    def setUp(self) -> None:
        self.path = ARTIFACT_DASHBOARD_CONTRACT_PATH
        self.text = _read(self.path)

    def test_doc_exists_and_non_empty(self) -> None:
        self.assertTrue(
            self.path.is_file(),
            f"Expected Phase 10J artifact-dashboard contract doc at "
            f"{self.path}",
        )
        self.assertGreater(self.path.stat().st_size, 0)

    def test_doc_is_ascii_only(self) -> None:
        raw = self.path.read_bytes()
        try:
            raw.decode("ascii")
        except UnicodeDecodeError as exc:
            self.fail(
                f"docs/artifact-dashboard-contract.md contains "
                f"non-ASCII bytes: {exc}"
            )

    def test_doc_has_required_top_level_sections(self) -> None:
        for header in (
            "# Artifact Dashboard Contract",
            "## Status",
            "## Scope",
            "## Distinction From Shipped Artifacts And Surfaces",
            "## Dashboard Surfaces",
            "## Advisory-Vs-Canonical Mirror Rule",
            "## Operations That Remain CLI-Only",
            "## Dashboard Identity And Operator Attribution",
            "## Refusal Behavior",
            "## Source-Of-Truth Preservation",
            "## Safety Boundaries",
            "## Approval Gates",
            "## Audit Expectations",
            "## Dependencies On Later Phase 10 Slices",
            "## Out Of Scope For Phase 10J",
        ):
            self.assertIn(
                header, self.text,
                f"docs/artifact-dashboard-contract.md missing "
                f"required section header {header!r}",
            )


class ArtifactDashboardContractEnumeratesSixSurfacesTests(
    unittest.TestCase,
):
    """Phase 10J: the contract MUST enumerate the six dashboard
    surfaces the prompt names so a Phase 10K implementer can build
    each one without further design decisions.
    """

    def setUp(self) -> None:
        self.text = _read(ARTIFACT_DASHBOARD_CONTRACT_PATH)

    def test_contract_names_each_required_surface_header(self) -> None:
        for header in (
            "### 1. Review Summaries",
            "### 2. Diff Views",
            "### 3. Progress History",
            "### 4. Approval Actions",
            "### 5. Token / Cost Reporting",
            "### 6. Failure Analytics",
        ):
            self.assertIn(
                header, self.text,
                f"artifact-dashboard contract missing required "
                f"surface header {header!r}",
            )


class ArtifactDashboardContractPinsSourceArtifactsTests(
    unittest.TestCase,
):
    """Each surface MUST name the canonical on-disk artifacts a
    Phase 10K runtime is permitted to read. Without this, an
    implementer would have to guess which files to mirror.
    """

    def setUp(self) -> None:
        self.text = _read(ARTIFACT_DASHBOARD_CONTRACT_PATH)
        self.collapsed = re.sub(r"\s+", " ", self.text)

    def test_review_summaries_source_artifacts(self) -> None:
        for fragment in (
            ".agent-loop/claude-summary.md",
            ".agent-loop/codex-review.md",
            ".agent-loop/fix-prompt.md",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"Review Summaries surface does not name source "
                f"artifact {fragment!r}",
            )

    def test_diff_views_source_artifacts(self) -> None:
        for fragment in (
            ".agent-loop/git-diff.patch",
            ".agent-loop/git-status.log",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"Diff Views surface does not name source artifact "
                f"{fragment!r}",
            )

    def test_progress_history_source_artifacts(self) -> None:
        for fragment in (
            ".agent-loop/loop-state.json",
            ".agent-loop/phase-plan.md",
            ".agent-loop/orchestrator.log",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"Progress History surface does not name source "
                f"artifact {fragment!r}",
            )

    def test_approval_actions_source_artifacts(self) -> None:
        for fragment in (
            ".agent-loop/proposed-phase.md",
            ".agent-loop/final-acceptance.json",
            "APPROVED_FOR_ACTIVATION",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"Approval Actions surface does not name source "
                f"artifact {fragment!r}",
            )

    def test_token_cost_source_artifacts(self) -> None:
        for fragment in (
            "capacity-retry-state",
            "token-exhaustion",
            "cycle_count",
            "max_cycles",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"Token/Cost Reporting surface does not name source "
                f"artifact {fragment!r}",
            )

    def test_failure_analytics_source_artifacts(self) -> None:
        for fragment in (
            ".agent-loop/codex-review.md",
            ".agent-loop/test-output.log",
            ".agent-loop/lint-output.log",
            ".agent-loop/typecheck-output.log",
            ".agent-loop/build-output.log",
            "repeated-failure",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"Failure Analytics surface does not name source "
                f"artifact {fragment!r}",
            )


class ArtifactDashboardContractPinsAdvisoryMirrorRuleTests(
    unittest.TestCase,
):
    """The contract MUST preserve the Phase 10G UI advisory-vs-
    canonical mirror rule and apply it to all six dashboard surfaces.
    """

    def setUp(self) -> None:
        self.text = _read(ARTIFACT_DASHBOARD_CONTRACT_PATH)
        self.collapsed = re.sub(r"\s+", " ", self.text)

    def test_contract_pins_canonical_mirror_vocabulary(self) -> None:
        for fragment in (
            "Canonical mirror",
            "Advisory derived state",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"artifact-dashboard contract does not pin the "
                f"{fragment!r} vocabulary",
            )

    def test_contract_prohibits_cross_snapshot_merging(self) -> None:
        self.assertIn(
            "cross-merge", self.collapsed,
        )
        self.assertIn(
            "one consistent on-disk snapshot", self.collapsed,
            "artifact-dashboard contract does not prohibit cross-"
            "snapshot merging in a single rendered record",
        )

    def test_contract_prohibits_caching_past_poll_cycle(self) -> None:
        for fragment in (
            "MUST NOT serve stale mirrors",
            "single poll cycle",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"artifact-dashboard contract does not prohibit "
                f"caching beyond a single poll cycle via "
                f"{fragment!r}",
            )


class ArtifactDashboardContractPreservesShippedHardStopsTests(
    unittest.TestCase,
):
    """The contract MUST preserve every shipped hard stop the Phase
    10G/10H/10I surfaces already pin: no Git automation in either
    root, the Phase 4C activator + `APPROVED_FOR_ACTIVATION` token,
    the Phase 9G acceptance gate, no auto-fill of operator identity,
    no canonical-artifact writes from the dashboard process, no
    dashboard-side databases / session stores / event queues /
    identity tokens / cost-budget enforcement.
    """

    def setUp(self) -> None:
        self.text = _read(ARTIFACT_DASHBOARD_CONTRACT_PATH)
        self.collapsed = re.sub(r"\s+", " ", self.text)

    def test_contract_preserves_no_git_automation(self) -> None:
        for fragment in (
            "commit, push, tag, branch, stash, reset, checkout",
            "BOTH roots",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"artifact-dashboard contract does not preserve "
                f"the no-Git-automation boundary via {fragment!r}",
            )

    def test_contract_preserves_approved_for_activation(self) -> None:
        for fragment in (
            "APPROVED_FOR_ACTIVATION",
            "Phase 4C activator",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"artifact-dashboard contract does not preserve "
                f"the activation gate via {fragment!r}",
            )

    def test_contract_preserves_phase_9g_acceptance_gate(self) -> None:
        for fragment in (
            "Phase 9G",
            "record-final-acceptance",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"artifact-dashboard contract does not preserve "
                f"the Phase 9G acceptance gate via {fragment!r}",
            )

    def test_contract_refuses_silent_identity_autofill(self) -> None:
        for fragment in (
            "MUST NOT auto-fill",
            "browser session",
            "$USER",
            "whoami",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"artifact-dashboard contract does not refuse "
                f"silent identity auto-fill via {fragment!r}",
            )

    def test_contract_forbids_dashboard_side_state_stores(
        self,
    ) -> None:
        for fragment in (
            "MUST NOT introduce a dashboard-side database",
            "MUST NOT introduce a dashboard-side notification queue",
            "MUST NOT introduce a dashboard-side identity",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"artifact-dashboard contract does not forbid "
                f"competing dashboard-side state via {fragment!r}",
            )

    def test_contract_forbids_dashboard_side_cost_enforcement(
        self,
    ) -> None:
        # Phase 10J explicitly carves out cost-budget enforcement
        # to the shipped Phase 6F / 9F runtime, not the dashboard.
        for fragment in (
            "enforce a \"cost budget\"",
            "no third-party analytics SDK",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"artifact-dashboard contract does not carve out "
                f"cost-budget enforcement via {fragment!r}",
            )

    def test_contract_marks_runtime_as_not_yet_implemented(
        self,
    ) -> None:
        # Phase 10J is documentation-only; the doc must NOT silently
        # promise the dashboard runtime as shipped.
        self.assertIn(
            "No artifact dashboard runtime", self.collapsed,
            "artifact-dashboard contract does not mark the "
            "dashboard runtime as not-yet-shipped",
        )
        for fragment in (
            "Phase 10K",
            "Phase 10L",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"artifact-dashboard contract does not locate the "
                f"future dashboard runtime in {fragment!r}",
            )


class ArtifactDashboardContractPinsCliOnlyOperationsTests(
    unittest.TestCase,
):
    """The contract MUST enumerate the shipped mutating CLI
    subcommands the dashboard is not allowed to silently trigger
    AND MUST cap the library-call delegation surface at the Phase
    10I-pinned three controls.
    """

    def setUp(self) -> None:
        self.text = _read(ARTIFACT_DASHBOARD_CONTRACT_PATH)
        self.collapsed = re.sub(r"\s+", " ", self.text)

    def test_contract_names_mutating_operations(self) -> None:
        for op in (
            "attach-external-target",
            "detach-external-target",
            "verify-external-target",
            "plan",
            "activate",
            "run",
            "resume",
            "auto-continue",
            "record-final-acceptance",
        ):
            self.assertIn(
                f"`{op}`", self.collapsed,
                f"artifact-dashboard contract does not name CLI-"
                f"only mutating operation {op!r}",
            )

    def test_contract_prohibits_dashboard_dispatch_of_mutating_cli(
        self,
    ) -> None:
        self.assertIn(
            "MUST NOT issue, dispatch, proxy, auto-trigger, "
            "queue, or schedule", self.collapsed,
            "artifact-dashboard contract does not explicitly "
            "prohibit dashboard dispatch of mutating CLI ops",
        )

    def test_contract_caps_library_callable_at_phase_10i_three(
        self,
    ) -> None:
        # The dashboard MUST NOT introduce additional library-
        # callable controls beyond the three the Phase 10I registry
        # already pins.
        for fragment in (
            "view-external-status",
            "view-external-controls",
            "inspect-external-target",
            "MUST NOT introduce additional library-callable "
            "controls",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"artifact-dashboard contract does not cap the "
                f"library-call delegation surface at the Phase 10I "
                f"three via {fragment!r}",
            )


class ReadmePointsAtArtifactDashboardContractDocTests(
    unittest.TestCase,
):
    """Phase 10J: the README must route a reader at the new contract
    doc and mark Phase 10J as the current active sub-phase.
    """

    def setUp(self) -> None:
        self.text = _read(README_PATH)

    def test_readme_names_artifact_dashboard_contract_doc(
        self,
    ) -> None:
        self.assertIn(
            "docs/artifact-dashboard-contract.md", self.text,
            "README.md does not route readers at the Phase 10J "
            "artifact-dashboard contract doc",
        )

    def test_readme_marks_phase_10j_as_active(self) -> None:
        self.assertIn(
            "Phase 10J", self.text,
            "README.md does not name Phase 10J as a current focus",
        )
        self.assertIn(
            "Artifact Dashboard Contract", self.text,
            "README.md does not name the Phase 10J sub-phase title",
        )

    def test_readme_marks_phase_10j_as_documentation_only(
        self,
    ) -> None:
        for fragment in (
            "documentation form only",
            "Phase 10K",
        ):
            self.assertIn(
                fragment, self.text,
                f"README.md Phase 10J paragraph does not document "
                f"the documentation-only scope fragment "
                f"{fragment!r}",
            )

    def test_readme_routes_advanced_dashboard_to_later_phases(
        self,
    ) -> None:
        # Future dashboard capabilities must be routed to Phase
        # 10K / 10L+ so a reader does not assume they ship in 10J.
        for fragment in (
            "Phase 10K",
            "Phase 10L",
        ):
            self.assertIn(
                fragment, self.text,
                f"README.md Phase 10J paragraph does not route "
                f"future dashboard capability to {fragment!r}",
            )


# ---------------------------------------------------------------------------
# Phase 10L - Desktop App Shell Contract documentation-only slice.
#
# These tests pin the canonical section headers, the contract's
# distinction from shipped surfaces, the desktop-process boundary,
# the controller-root selection flow, attach visibility, refresh /
# polling rules, artifact-opening behavior, the safe bridge to the
# shipped Python orchestrator / view surfaces, the CLI-only operation
# list, the refusal cases, and the safety / approval / audit
# boundaries the desktop runtime must preserve. The shipped Phase
# 10G - 10K surfaces remain authoritative; this contract layers on
# top of them.
# ---------------------------------------------------------------------------
class DesktopAppContractDocExistsAndIsWellFormedTests(
    unittest.TestCase,
):
    """Phase 10L: the desktop-app contract doc must exist on disk,
    be non-empty, be ASCII-only, and carry the canonical section
    headers a future Phase 10M implementer reads.
    """

    def setUp(self) -> None:
        self.path = DESKTOP_APP_CONTRACT_PATH
        self.text = _read(self.path)

    def test_doc_exists_and_non_empty(self) -> None:
        self.assertTrue(
            self.path.is_file(),
            f"Expected Phase 10L desktop-app contract doc at "
            f"{self.path}",
        )
        self.assertGreater(self.path.stat().st_size, 0)

    def test_doc_is_ascii_only(self) -> None:
        raw = self.path.read_bytes()
        try:
            raw.decode("ascii")
        except UnicodeDecodeError as exc:
            self.fail(
                f"docs/desktop-app-contract.md contains non-ASCII "
                f"bytes: {exc}"
            )

    def test_doc_has_required_top_level_sections(self) -> None:
        for header in (
            "# Desktop App Shell Contract",
            "## Status",
            "## Scope",
            "## Distinction From Shipped Artifacts And Surfaces",
            "## Desktop Process Boundary And Toolkit",
            "## Controller-Root Selection Flow",
            "## Attach Visibility",
            "## Refresh / Polling Rules",
            "## Artifact-Opening Behavior",
            "## Bridge To Shipped Python Orchestrator And View "
            "Surfaces",
            "## Advisory-Vs-Canonical Mirror Rule",
            "## Operations That Remain CLI-Only",
            "## Desktop Identity And Operator Attribution",
            "## Refusal Behavior",
            "## Source-Of-Truth Preservation",
            "## Safety Boundaries",
            "## Approval Gates",
            "## Audit Expectations",
            "## Dependencies On Later Phase 10 Slices",
            "## Out Of Scope For Phase 10L",
        ):
            self.assertIn(
                header, self.text,
                f"docs/desktop-app-contract.md missing required "
                f"section header {header!r}",
            )


class DesktopAppContractPinsProcessBoundaryTests(unittest.TestCase):
    """The contract MUST pin a local-only, read-mostly, native
    desktop process that does NOT introduce a remote server, hosted
    SaaS endpoint, or shared multi-user backend.
    """

    def setUp(self) -> None:
        self.text = _read(DESKTOP_APP_CONTRACT_PATH)
        self.collapsed = re.sub(r"\s+", " ", self.text)

    def test_contract_pins_local_only_process(self) -> None:
        for fragment in (
            "thin local-only native window process",
            "same machine as the controller repository",
            "MUST NOT introduce a remote server",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"desktop-app contract does not pin the local-only "
                f"process via {fragment!r}",
            )

    def test_contract_forbids_background_mutating_daemon(self) -> None:
        for fragment in (
            "MUST NOT bundle, fork, or auto-start a background "
            "daemon",
            "shipped CLI remains the only mutating writer",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"desktop-app contract does not forbid background "
                f"mutating daemons via {fragment!r}",
            )

    def test_contract_does_not_pin_specific_toolkit(self) -> None:
        # Phase 10M is free to pick any toolkit so long as it
        # satisfies the other invariants; the contract MUST NOT
        # pin Electron / Tauri / Qt / native at this layer.
        self.assertIn(
            "intentionally NOT pinned by this contract",
            self.collapsed,
        )

    def test_contract_pins_renderer_process_safety(self) -> None:
        # For toolkits with a separate renderer process the
        # renderer MUST NOT have direct filesystem write access
        # to any canonical artifact.
        for fragment in (
            "renderer process separate from the main process",
            "MUST NOT have direct filesystem write access",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"desktop-app contract does not pin renderer "
                f"safety via {fragment!r}",
            )


class DesktopAppContractPinsControllerRootSelectionTests(
    unittest.TestCase,
):
    """The contract MUST require explicit operator selection of the
    controller root before any canonical artifact is rendered.
    """

    def setUp(self) -> None:
        self.text = _read(DESKTOP_APP_CONTRACT_PATH)
        self.collapsed = re.sub(r"\s+", " ", self.text)

    def test_contract_requires_explicit_selection(self) -> None:
        for fragment in (
            "require explicit operator selection",
            "MUST NOT silently pick a default root",
            "native folder picker",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"desktop-app contract does not require explicit "
                f"controller-root selection via {fragment!r}",
            )

    def test_contract_validates_controller_repository(self) -> None:
        for fragment in (
            "AGENTS.md",
            "CLAUDE.md",
            "TASK.md",
            ".agent-loop/",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"desktop-app contract does not name "
                f"controller-root validation marker {fragment!r}",
            )

    def test_contract_treats_root_switch_as_clean_reset(self) -> None:
        for fragment in (
            "switch the controller root mid-session",
            "clean reset",
            "MUST NOT cross-merge artifacts from two different "
            "controller roots",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"desktop-app contract does not pin clean-reset "
                f"on root switch via {fragment!r}",
            )

    def test_contract_does_not_auto_create_controller_root(
        self,
    ) -> None:
        self.assertIn(
            "MUST NOT auto-create the controller root",
            self.collapsed,
        )


class DesktopAppContractPinsRefreshAndPollingTests(unittest.TestCase):
    """The contract MUST bound poll cadence, prohibit parallel
    event-stream / webhook surfaces, and require canonical-mirror
    refresh per poll cycle.
    """

    def setUp(self) -> None:
        self.text = _read(DESKTOP_APP_CONTRACT_PATH)
        self.collapsed = re.sub(r"\s+", " ", self.text)

    def test_contract_pins_bounded_poll_cadence(self) -> None:
        for fragment in (
            "at least 2 seconds between polls",
            "at least 1 second under operator-driven refresh",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"desktop-app contract does not pin bounded poll "
                f"cadence via {fragment!r}",
            )

    def test_contract_pins_per_poll_cache_invalidation(self) -> None:
        for fragment in (
            "MUST NOT serve stale mirrors",
            "cache invalidation per poll is required",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"desktop-app contract does not pin per-poll cache "
                f"invalidation via {fragment!r}",
            )

    def test_contract_forbids_parallel_event_stream(self) -> None:
        for fragment in (
            "MUST NOT introduce a long-poll",
            "WebSocket subscription",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"desktop-app contract does not forbid parallel "
                f"event-stream surfaces via {fragment!r}",
            )

    def test_contract_permits_filesystem_watch_as_optimization(
        self,
    ) -> None:
        # A FS watch is permitted as a polling optimization but
        # MUST NOT bypass the shipped view library functions.
        for fragment in (
            "file-system watch on `.agent-loop/`",
            "MUST NOT bypass the shipped view library functions",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"desktop-app contract does not pin FS-watch "
                f"safety via {fragment!r}",
            )


class DesktopAppContractPinsArtifactOpeningTests(unittest.TestCase):
    """The contract MUST pin artifact-opening behavior as read-only
    from the shell's perspective, using the operating system's
    default file-open mechanism.
    """

    def setUp(self) -> None:
        self.text = _read(DESKTOP_APP_CONTRACT_PATH)
        self.collapsed = re.sub(r"\s+", " ", self.text)

    def test_contract_pins_os_default_open_mechanism(self) -> None:
        for fragment in (
            "operating system's default file-open mechanism",
            "MUST NOT bundle its own editor",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"desktop-app contract does not pin OS-default "
                f"open via {fragment!r}",
            )

    def test_contract_forbids_git_side_effects(self) -> None:
        for fragment in (
            "MUST NOT auto-stage, auto-format, or auto-rewrite",
            "MUST NOT invoke `git add`",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"desktop-app contract does not forbid Git side "
                f"effects on artifact-open via {fragment!r}",
            )

    def test_contract_pins_codex_owned_artifact_readonly_open(
        self,
    ) -> None:
        # The Codex-owned planning artifacts must not be opened
        # for editing as a side effect of any dashboard render.
        for fragment in (
            "MUST NOT silently open a Codex-owned planning "
            "artifact",
            ".agent-loop/current-task.md",
            ".agent-loop/current-phase.md",
            ".agent-loop/phase-plan.md",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"desktop-app contract does not pin Codex-owned "
                f"read-only-open via {fragment!r}",
            )


class DesktopAppContractPinsBridgeTests(unittest.TestCase):
    """The contract MUST pin exactly two bridge modes to the shipped
    Python surfaces (library-call for reads, CLI-spawn for mutations)
    and MUST forbid re-implementing the shipped library functions or
    bypassing them via direct on-disk reads.
    """

    def setUp(self) -> None:
        self.text = _read(DESKTOP_APP_CONTRACT_PATH)
        self.collapsed = re.sub(r"\s+", " ", self.text)

    def test_contract_pins_library_call_bridge(self) -> None:
        for fragment in (
            "Library-call bridge",
            "build_external_ui_status_view",
            "build_external_ui_control_view",
            "build_artifact_dashboard_view",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"desktop-app contract does not pin the library-"
                f"call bridge via {fragment!r}",
            )

    def test_contract_pins_cli_spawn_bridge(self) -> None:
        for fragment in (
            "CLI-spawn bridge",
            "copy-paste affordance",
            "MUST NOT silently `Popen`",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"desktop-app contract does not pin the CLI-spawn "
                f"bridge via {fragment!r}",
            )

    def test_contract_forbids_reimplementing_view_functions(
        self,
    ) -> None:
        self.assertIn(
            "MUST NOT re-implement the shipped library functions",
            self.collapsed,
        )

    def test_contract_forbids_custom_ipc_protocol(self) -> None:
        for fragment in (
            "MUST NOT introduce a custom IPC protocol",
            "named pipe",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"desktop-app contract does not forbid custom "
                f"IPC via {fragment!r}",
            )


class DesktopAppContractPreservesShippedHardStopsTests(
    unittest.TestCase,
):
    """The contract MUST preserve every shipped hard stop the Phase
    10G/10H/10I/10J/10K surfaces already pin: no Git automation in
    either root, the Phase 4C activator + `APPROVED_FOR_ACTIVATION`
    token, the Phase 9G acceptance gate, no auto-fill of operator
    identity, no canonical-artifact writes from the desktop shell
    process, no desktop-side databases / session stores / event
    queues / identity tokens.
    """

    def setUp(self) -> None:
        self.text = _read(DESKTOP_APP_CONTRACT_PATH)
        self.collapsed = re.sub(r"\s+", " ", self.text)

    def test_contract_preserves_no_git_automation(self) -> None:
        for fragment in (
            "commit, push, tag, branch, stash, reset, checkout",
            "BOTH roots",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"desktop-app contract does not preserve the "
                f"no-Git-automation boundary via {fragment!r}",
            )

    def test_contract_preserves_approved_for_activation(self) -> None:
        for fragment in (
            "APPROVED_FOR_ACTIVATION",
            "Phase 4C activator",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"desktop-app contract does not preserve the "
                f"activation gate via {fragment!r}",
            )

    def test_contract_preserves_phase_9g_acceptance_gate(self) -> None:
        for fragment in (
            "Phase 9G",
            "record-final-acceptance",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"desktop-app contract does not preserve the "
                f"Phase 9G acceptance gate via {fragment!r}",
            )

    def test_contract_refuses_silent_identity_autofill(self) -> None:
        for fragment in (
            "MUST NOT auto-fill",
            "browser session",
            "$USER",
            "whoami",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"desktop-app contract does not refuse silent "
                f"identity auto-fill via {fragment!r}",
            )

    def test_contract_forbids_desktop_side_state_stores(self) -> None:
        for fragment in (
            "MUST NOT introduce a shell-side database",
            "MUST NOT introduce a shell-side notification queue",
            "MUST NOT introduce a shell-side identity",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"desktop-app contract does not forbid competing "
                f"desktop-side state via {fragment!r}",
            )

    def test_contract_preserves_phase_10i_library_call_cap(
        self,
    ) -> None:
        for fragment in (
            "MUST NOT introduce additional library-callable "
            "controls",
            "view-external-status",
            "view-external-controls",
            "inspect-external-target",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"desktop-app contract does not cap the "
                f"library-callable surface at the Phase 10I "
                f"three via {fragment!r}",
            )

    def test_contract_marks_runtime_as_not_yet_implemented(
        self,
    ) -> None:
        # Phase 10L is documentation-only; the doc must NOT
        # silently promise the desktop runtime as shipped.
        self.assertIn(
            "No desktop app runtime", self.collapsed,
            "desktop-app contract does not mark the desktop "
            "runtime as not-yet-shipped",
        )
        for fragment in (
            "Phase 10M",
            "Phase 10N",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"desktop-app contract does not locate the future "
                f"desktop runtime in {fragment!r}",
            )


class DesktopAppContractPinsCliOnlyOperationsTests(unittest.TestCase):
    """The contract MUST enumerate the shipped mutating CLI
    subcommands the desktop shell is not allowed to silently trigger.
    """

    def setUp(self) -> None:
        self.text = _read(DESKTOP_APP_CONTRACT_PATH)
        self.collapsed = re.sub(r"\s+", " ", self.text)

    def test_contract_names_mutating_operations(self) -> None:
        for op in (
            "attach-external-target",
            "detach-external-target",
            "verify-external-target",
            "plan",
            "activate",
            "run",
            "resume",
            "auto-continue",
            "record-final-acceptance",
        ):
            self.assertIn(
                op, self.collapsed,
                f"desktop-app contract does not enumerate "
                f"mutating CLI subcommand {op!r}",
            )

    def test_contract_names_readonly_reporter_operations(self) -> None:
        for op in (
            "inspect-external-target",
            "inspect-artifacts",
            "status",
            "evaluate-final-acceptance",
            "validate-artifacts",
            "check-state",
            "view-artifact-dashboard",
        ):
            self.assertIn(
                op, self.collapsed,
                f"desktop-app contract does not enumerate "
                f"read-only CLI reporter {op!r}",
            )


class DesktopAppContractInternalConsistencyWithPriorPhasesTests(
    unittest.TestCase,
):
    """The Phase 10L contract MUST stay internally consistent with
    the Phase 10G UI contract, the Phase 10J dashboard contract, and
    the shipped Phase 10K runtime: it MAY extend the boundaries but
    MUST NOT relax any of them.
    """

    def setUp(self) -> None:
        self.text = _read(DESKTOP_APP_CONTRACT_PATH)
        self.collapsed = re.sub(r"\s+", " ", self.text)

    def test_contract_references_external_ui_contract(self) -> None:
        for fragment in (
            "docs/external-ui-contract.md",
            "Phase 10G",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"desktop-app contract does not reference the "
                f"Phase 10G UI contract via {fragment!r}",
            )

    def test_contract_references_dashboard_contract(self) -> None:
        for fragment in (
            "docs/artifact-dashboard-contract.md",
            "Phase 10J",
            "Phase 10K",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"desktop-app contract does not reference the "
                f"Phase 10J/10K dashboard work via {fragment!r}",
            )

    def test_contract_references_phase_10h_view_surface(self) -> None:
        for fragment in (
            "view-external-status",
            "build_external_ui_status_view",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"desktop-app contract does not reference the "
                f"Phase 10H view surface via {fragment!r}",
            )

    def test_contract_references_phase_10i_control_surface(
        self,
    ) -> None:
        for fragment in (
            "view-external-controls",
            "invoke-external-control",
            "ExternalUiControlRefusal",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"desktop-app contract does not reference the "
                f"Phase 10I control surface via {fragment!r}",
            )

    def test_contract_references_phase_10k_dashboard_runtime(
        self,
    ) -> None:
        for fragment in (
            "view-artifact-dashboard",
            "build_artifact_dashboard_view",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"desktop-app contract does not reference the "
                f"Phase 10K dashboard runtime via {fragment!r}",
            )


class DesktopAppContractReadmeAlignmentTests(unittest.TestCase):
    """README.md MUST surface Phase 10L as active and route readers
    at `docs/desktop-app-contract.md`.
    """

    def setUp(self) -> None:
        readme = REPO_ROOT / "README.md"
        self.text = _read(readme)

    def test_readme_routes_at_desktop_app_contract(self) -> None:
        self.assertIn(
            "docs/desktop-app-contract.md", self.text,
            "README.md does not route readers at the Phase 10L "
            "desktop-app contract doc",
        )

    def test_readme_marks_phase_10l_as_active(self) -> None:
        self.assertIn(
            "Phase 10L", self.text,
            "README.md does not name Phase 10L as a current focus",
        )
        self.assertIn(
            "Desktop App Shell Contract", self.text,
            "README.md does not name the Phase 10L sub-phase title",
        )

    def test_readme_marks_phase_10l_as_documentation_only(
        self,
    ) -> None:
        for fragment in (
            "documentation form only",
            "Phase 10M",
        ):
            self.assertIn(
                fragment, self.text,
                f"README.md Phase 10L paragraph does not document "
                f"the documentation-only scope fragment "
                f"{fragment!r}",
            )

    def test_readme_routes_advanced_desktop_to_later_phases(
        self,
    ) -> None:
        # Future desktop capabilities must be routed to Phase
        # 10M / 10N+ so a reader does not assume they ship in 10L.
        for fragment in (
            "Phase 10M",
            "Phase 10N",
        ):
            self.assertIn(
                fragment, self.text,
                f"README.md Phase 10L paragraph does not route "
                f"future desktop capability to {fragment!r}",
            )


class DesktopAppContractRoadmapRoutingAlignmentTests(
    unittest.TestCase,
):
    """The Phase 10L contract and the README's Phase 10L
    description MUST point implementers at the correct next slices
    per the canonical `ROADMAP.md`:

    - Phase 10M = Desktop App Read-Only Runtime Initial Slice
    - Phase 10N = Desktop App Action Bridge Initial Slice
    - Phase 10AB / 10AC / 10AD = controlled-concurrency work
      (Controlled Concurrent Operation Contract, Overlap-Safe
      Detection Initial Slice, Codex-Owned Concurrent Work Initial
      Slice)

    A prior cycle described `Phase 10N` as the bucket for
    controlled-concurrency, multi-target desktop sessions, and
    packaging work. That is wrong and must not silently re-appear.
    """

    def setUp(self) -> None:
        self.contract_text = _read(DESKTOP_APP_CONTRACT_PATH)
        self.contract_collapsed = re.sub(
            r"\s+", " ", self.contract_text,
        )
        self.readme_text = _read(REPO_ROOT / "README.md")
        self.readme_collapsed = re.sub(r"\s+", " ", self.readme_text)
        self.roadmap_text = _read(REPO_ROOT / "ROADMAP.md")
        self.roadmap_collapsed = re.sub(
            r"\s+", " ", self.roadmap_text,
        )

    def test_roadmap_pins_canonical_phase_10m_name(self) -> None:
        # Anchor: the canonical roadmap line. If this test fails,
        # ROADMAP.md was renamed and every consumer below needs
        # updating in lockstep.
        self.assertIn(
            "Phase 10M - Desktop App Read-Only Runtime Initial "
            "Slice",
            self.roadmap_collapsed,
        )

    def test_roadmap_pins_canonical_phase_10n_name(self) -> None:
        self.assertIn(
            "Phase 10N - Desktop App Action Bridge Initial Slice",
            self.roadmap_collapsed,
        )

    def test_roadmap_pins_concurrency_at_10ab_10ac_10ad(self) -> None:
        for fragment in (
            "Phase 10AB - Controlled Concurrent Operation Contract",
            "Phase 10AC - Overlap-Safe Detection Initial Slice",
            "Phase 10AD - Codex-Owned Concurrent Work Initial "
            "Slice",
        ):
            self.assertIn(
                fragment, self.roadmap_collapsed,
                f"ROADMAP.md no longer pins controlled-concurrency "
                f"at {fragment!r}; downstream test pins must be "
                f"updated in lockstep",
            )

    def test_contract_names_phase_10m_as_read_only_runtime(
        self,
    ) -> None:
        self.assertIn(
            "Phase 10M (Desktop App Read-Only Runtime Initial "
            "Slice)",
            self.contract_collapsed,
            "desktop-app contract does not name Phase 10M with the "
            "canonical 'Desktop App Read-Only Runtime Initial "
            "Slice' title from ROADMAP.md",
        )

    def test_contract_names_phase_10n_as_action_bridge(self) -> None:
        self.assertIn(
            "Phase 10N (Desktop App Action Bridge Initial Slice)",
            self.contract_collapsed,
            "desktop-app contract does not name Phase 10N with the "
            "canonical 'Desktop App Action Bridge Initial Slice' "
            "title from ROADMAP.md",
        )

    def test_contract_routes_concurrency_to_10ab_10ac_10ad(
        self,
    ) -> None:
        # Controlled-concurrency work is at Phase 10AB / 10AC /
        # 10AD per the canonical ROADMAP.md, NOT at Phase 10N.
        # The contract uses both the explicit `Phase 10AB` form
        # and the compact `Phase 10AB / 10AC / 10AD` form; checking
        # for the short labels survives both.
        for fragment in (
            "10AB",
            "10AC",
            "10AD",
        ):
            self.assertIn(
                fragment, self.contract_collapsed,
                f"desktop-app contract does not route "
                f"controlled-concurrency work to "
                f"Phase {fragment!r}",
            )

    def test_contract_does_not_misroute_concurrency_to_10n(
        self,
    ) -> None:
        # Phase 10N is the Action Bridge slice; it MUST NOT be
        # described as the controlled-concurrency bucket.
        forbidden_phrases = (
            "Phase 10N controlled-concurrency",
            "Phase 10N+ controlled-concurrency",
            "Phase 10N: Controlled-Concurrency",
            "Phase 10N (Controlled-Concurrency",
            "Phase 10N and later (Controlled-Concurrency",
        )
        for phrase in forbidden_phrases:
            self.assertNotIn(
                phrase, self.contract_collapsed,
                f"desktop-app contract still misroutes "
                f"controlled-concurrency to Phase 10N via the "
                f"phrase {phrase!r}; per ROADMAP.md, "
                f"controlled-concurrency is at Phase 10AB / 10AC "
                f"/ 10AD and Phase 10N is the Action Bridge slice",
            )

    def test_readme_routes_concurrency_to_10ab_10ac_10ad(self) -> None:
        # The README's Phase 10L paragraph must route
        # controlled-concurrency to Phase 10AB / 10AC / 10AD, not
        # to Phase 10N. The README uses the compact form
        # `Phase 10AB / 10AC / 10AD`, so the short-form labels
        # `10AB` / `10AC` / `10AD` are what survive collapse.
        for fragment in (
            "10AB",
            "10AC",
            "10AD",
        ):
            self.assertIn(
                fragment, self.readme_collapsed,
                f"README.md does not route "
                f"controlled-concurrency work to "
                f"Phase {fragment!r}",
            )

    def test_readme_does_not_misroute_concurrency_to_10n(
        self,
    ) -> None:
        for phrase in (
            "Phase 10N controlled-concurrency",
            "Phase 10N+ controlled-concurrency",
            "Phase 10N: Controlled-Concurrency",
            "Phase 10N (Controlled-Concurrency",
            "Phase 10N and later (Controlled-Concurrency",
        ):
            self.assertNotIn(
                phrase, self.readme_collapsed,
                f"README.md still misroutes "
                f"controlled-concurrency to Phase 10N via the "
                f"phrase {phrase!r}; per ROADMAP.md, "
                f"controlled-concurrency is at Phase 10AB / 10AC "
                f"/ 10AD and Phase 10N is the Action Bridge slice",
            )


# ---------------------------------------------------------------------------
# Phase 10O - MCP Integration Contract And Safe Tool Boundary
# documentation-only slice.
#
# These tests pin the canonical section headers, the contract's
# distinction from shipped surfaces, the three closed tool categories
# (read_only_advisory, browser_app_inspection, deferred_mutating),
# the read-only-vs-deferred-mutating boundary, the per-tool descriptor
# fields, the browser/app inspection hook safety boundary, the policy-
# rule hook additive-only boundary, the CLI-only operation list, the
# refusal cases, the evidence-review preservation, and the safety /
# approval / audit boundaries the future MCP runtime must preserve.
# The shipped Phase 10G - 10N surfaces remain authoritative; this
# contract layers on top of them.
# ---------------------------------------------------------------------------
class McpIntegrationContractDocExistsAndIsWellFormedTests(
    unittest.TestCase,
):
    """Phase 10O: the MCP integration contract doc must exist on
    disk, be non-empty, be ASCII-only, and carry the canonical
    section headers a future Phase 10T implementer reads.
    """

    def setUp(self) -> None:
        self.path = MCP_INTEGRATION_CONTRACT_PATH
        self.text = _read(self.path)

    def test_doc_exists_and_non_empty(self) -> None:
        self.assertTrue(
            self.path.is_file(),
            f"Expected Phase 10O MCP integration contract doc at "
            f"{self.path}",
        )
        self.assertGreater(self.path.stat().st_size, 0)

    def test_doc_is_ascii_only(self) -> None:
        raw = self.path.read_bytes()
        try:
            raw.decode("ascii")
        except UnicodeDecodeError as exc:
            self.fail(
                f"docs/mcp-integration-contract.md contains "
                f"non-ASCII bytes: {exc}"
            )

    def test_doc_has_required_top_level_sections(self) -> None:
        for header in (
            "# MCP Integration Contract And Safe Tool Boundary",
            "## Status",
            "## Scope",
            "## Distinction From Shipped Artifacts And Surfaces",
            "## MCP Tool Categories",
            "## MCP Tool Ownership And Routing",
            "## Read-Only Tool Boundary",
            "## Deferred Mutation-Capable Tool Boundary",
            "## Browser/App Inspection Hook Boundary",
            "## Policy Rule Hook Boundary",
            "## Advisory-Vs-Canonical Mirror Rule",
            "## Operations That Remain CLI-Only",
            "## MCP Identity And Operator Attribution",
            "## Refusal Behavior",
            "## Source-Of-Truth Preservation",
            "## Safety Boundaries",
            "## Approval Gates",
            "## Audit Expectations",
            "## Evidence-Review Preservation",
            "## Dependencies On Later Phase 10 Slices",
            "## Out Of Scope For Phase 10O",
        ):
            self.assertIn(
                header, self.text,
                f"docs/mcp-integration-contract.md missing "
                f"required section header {header!r}",
            )


class McpIntegrationContractPinsThreeToolCategoriesTests(
    unittest.TestCase,
):
    """The contract MUST enumerate exactly three closed tool
    categories so a Phase 10T implementer can classify every MCP
    tool without further design decisions.
    """

    def setUp(self) -> None:
        self.text = _read(MCP_INTEGRATION_CONTRACT_PATH)
        self.collapsed = re.sub(r"\s+", " ", self.text)

    def test_contract_names_three_required_category_headers(
        self,
    ) -> None:
        for header in (
            "### 1. Read-Only Advisory Context",
            "### 2. Browser/App Inspection (Read-Only)",
            "### 3. Deferred Mutation-Capable Tools",
        ):
            self.assertIn(
                header, self.text,
                f"mcp-integration contract missing required "
                f"category header {header!r}",
            )

    def test_contract_pins_canonical_category_id_strings(
        self,
    ) -> None:
        # The per-tool descriptor's `category` field MUST carry one
        # of three closed string values; the contract surfaces them
        # in code-fence backticks so a Phase 10T implementer can
        # grep for the canonical identifiers.
        for category_id in (
            "read_only_advisory",
            "browser_app_inspection",
            "deferred_mutating",
        ):
            self.assertIn(
                category_id, self.collapsed,
                f"mcp-integration contract does not pin canonical "
                f"category id {category_id!r}",
            )

    def test_contract_defers_mutation_capable_to_phase_10u_plus(
        self,
    ) -> None:
        # Phase 10O explicitly defers every mutation-capable tool to
        # Phase 10U+; the Phase 10T initial slice MUST refuse them.
        for fragment in (
            "Phase 10U",
            "MUST refuse fail-closed unconditionally",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"mcp-integration contract does not defer "
                f"mutation-capable tools via {fragment!r}",
            )


class McpIntegrationContractPinsPerToolDescriptorTests(
    unittest.TestCase,
):
    """Every MCP tool MUST be described by a closed-field
    descriptor matching the Phase 10I control-registry pattern. The
    contract pins the minimum required field set.
    """

    def setUp(self) -> None:
        self.text = _read(MCP_INTEGRATION_CONTRACT_PATH)
        self.collapsed = re.sub(r"\s+", " ", self.text)

    def test_contract_names_required_descriptor_fields(self) -> None:
        for field in (
            "id",
            "category",
            "dispatch_mode",
            "delegated_phase_10i_control_id",
            "mutation_eligible",
            "audit_note",
            "refusal_reason_template",
        ):
            self.assertIn(
                field, self.collapsed,
                f"mcp-integration contract does not name required "
                f"per-tool descriptor field {field!r}",
            )

    def test_contract_pins_mutation_eligible_false_in_phase_10t(
        self,
    ) -> None:
        # The Phase 10T initial slice MUST refuse any tool with
        # `mutation_eligible=True`; the contract pins this with
        # ALWAYS `false` language.
        self.assertIn(
            "ALWAYS `false` in the Phase 10T initial slice",
            self.collapsed,
        )


class McpIntegrationContractPreservesShippedHardStopsTests(
    unittest.TestCase,
):
    """The contract MUST preserve every shipped hard stop the
    Phase 10A - 10N surfaces already pin: no Git automation in
    either root, the Phase 4C activator + `APPROVED_FOR_ACTIVATION`
    token, the Phase 9G acceptance gate, no auto-fill of operator
    identity, no canonical-artifact writes from the MCP runtime
    process, no MCP-side databases / session stores / event queues
    / identity tokens, the Phase 10I three-control library-callable
    cap, and the evidence-review preservation.
    """

    def setUp(self) -> None:
        self.text = _read(MCP_INTEGRATION_CONTRACT_PATH)
        self.collapsed = re.sub(r"\s+", " ", self.text)

    def test_contract_preserves_no_git_automation(self) -> None:
        for fragment in (
            "commit, push, tag, branch, stash, reset, checkout",
            "BOTH roots",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"mcp-integration contract does not preserve the "
                f"no-Git-automation boundary via {fragment!r}",
            )

    def test_contract_preserves_approved_for_activation(self) -> None:
        for fragment in (
            "APPROVED_FOR_ACTIVATION",
            "Phase 4C activator",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"mcp-integration contract does not preserve the "
                f"activation gate via {fragment!r}",
            )

    def test_contract_preserves_phase_9g_acceptance_gate(self) -> None:
        for fragment in (
            "Phase 9G",
            "record-final-acceptance",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"mcp-integration contract does not preserve the "
                f"Phase 9G acceptance gate via {fragment!r}",
            )

    def test_contract_refuses_silent_identity_autofill(self) -> None:
        for fragment in (
            "MUST NOT auto-fill",
            "$USER",
            "whoami",
            "browser session",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"mcp-integration contract does not refuse silent "
                f"identity auto-fill via {fragment!r}",
            )

    def test_contract_forbids_mcp_side_state_stores(self) -> None:
        for fragment in (
            "MUST NOT introduce an MCP-side database",
            "MUST NOT introduce an MCP-side notification queue",
            "MUST NOT introduce an MCP-side identity",
            "MUST NOT introduce an MCP-side memory store",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"mcp-integration contract does not forbid "
                f"competing MCP-side state via {fragment!r}",
            )

    def test_contract_preserves_phase_10i_library_call_cap(
        self,
    ) -> None:
        for fragment in (
            "MUST NOT introduce additional library-callable "
            "controls",
            "view-external-status",
            "view-external-controls",
            "inspect-external-target",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"mcp-integration contract does not cap the "
                f"library-callable surface at the Phase 10I three "
                f"via {fragment!r}",
            )

    def test_contract_marks_runtime_as_not_yet_implemented(
        self,
    ) -> None:
        # Phase 10O is documentation-only; the doc must NOT
        # silently promise the MCP runtime as shipped.
        self.assertIn(
            "ZERO MCP integration paths", self.collapsed,
            "mcp-integration contract does not mark MCP runtime "
            "as not-yet-shipped",
        )
        for fragment in (
            "Phase 10T",
            "Phase 10U",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"mcp-integration contract does not locate the "
                f"future MCP runtime in {fragment!r}",
            )


class McpIntegrationContractPinsBrowserInspectionBoundaryTests(
    unittest.TestCase,
):
    """The browser/app inspection hook MUST satisfy specific
    safety boundaries: explicit per-session operator authorization,
    no credential/cookie/session-token capture, no synthetic input
    injection, no OS-level event-stream subscription, no
    cross-session persistence.
    """

    def setUp(self) -> None:
        self.text = _read(MCP_INTEGRATION_CONTRACT_PATH)
        self.collapsed = re.sub(r"\s+", " ", self.text)

    def test_contract_requires_explicit_session_authorization(
        self,
    ) -> None:
        for fragment in (
            "explicitly authorize each inspection session",
            "MUST NOT auto-enable inspection",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"mcp-integration contract does not require "
                f"explicit inspection authorization via "
                f"{fragment!r}",
            )

    def test_contract_forbids_credential_capture(self) -> None:
        for fragment in (
            "no cookies",
            "no browser session tokens",
            "no OS-level credentials",
            "no SSH keys",
            "no API keys",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"mcp-integration contract does not forbid "
                f"credential capture via {fragment!r}",
            )

    def test_contract_forbids_synthetic_input_injection(self) -> None:
        for fragment in (
            "MUST NOT inject any value back",
            "no synthetic mouse events",
            "no synthetic keystrokes",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"mcp-integration contract does not forbid "
                f"synthetic input injection via {fragment!r}",
            )

    def test_contract_forbids_cross_session_persistence(self) -> None:
        self.assertIn(
            "MUST NOT persist inspection captures across",
            self.collapsed,
        )


class McpIntegrationContractPinsPolicyHookAdditiveBoundaryTests(
    unittest.TestCase,
):
    """The policy-rule hook MUST be additive only - a policy rule
    MAY refuse a tool the base contract would allow, but MUST NOT
    approve a tool the base contract refuses.
    """

    def setUp(self) -> None:
        self.text = _read(MCP_INTEGRATION_CONTRACT_PATH)
        self.collapsed = re.sub(r"\s+", " ", self.text)

    def test_contract_pins_additive_only_policy_boundary(
        self,
    ) -> None:
        for fragment in (
            "policy rules are ADDITIVE only",
            "MUST NOT approve a tool the base contract refuses",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"mcp-integration contract does not pin additive-"
                f"only policy boundary via {fragment!r}",
            )

    def test_contract_forbids_policy_widening_of_categories(
        self,
    ) -> None:
        for fragment in (
            "MUST NOT widen the read-only / deferred-mutation "
            "boundary",
            "cannot promote a `deferred_mutating` tool to a "
            "permitted category",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"mcp-integration contract does not forbid policy-"
                f"driven category widening via {fragment!r}",
            )


class McpIntegrationContractPinsEvidenceReviewPreservationTests(
    unittest.TestCase,
):
    """MCP-fetched values MUST NOT substitute for the shipped
    Phase 2A evidence files, the shipped git diff/status capture,
    Claude's summary, or Codex's review.
    """

    def setUp(self) -> None:
        self.text = _read(MCP_INTEGRATION_CONTRACT_PATH)
        self.collapsed = re.sub(r"\s+", " ", self.text)

    def test_contract_forbids_substituting_shipped_evidence(
        self,
    ) -> None:
        for fragment in (
            ".agent-loop/test-output.log",
            ".agent-loop/lint-output.log",
            ".agent-loop/typecheck-output.log",
            ".agent-loop/build-output.log",
            ".agent-loop/git-diff.patch",
            ".agent-loop/git-status.log",
            ".agent-loop/claude-summary.md",
            ".agent-loop/codex-review.md",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"mcp-integration contract does not name canonical "
                f"evidence artifact {fragment!r}",
            )

    def test_contract_requires_mcp_advisory_provenance_tag(
        self,
    ) -> None:
        for fragment in (
            "[mcp-advisory]",
            "tagged `[mcp-advisory]`",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"mcp-integration contract does not require the "
                f"`[mcp-advisory]` provenance tag via {fragment!r}",
            )


class McpIntegrationContractPinsCliOnlyOperationsTests(
    unittest.TestCase,
):
    """The contract MUST enumerate the shipped mutating CLI
    subcommands the MCP runtime is not allowed to silently trigger.
    """

    def setUp(self) -> None:
        self.text = _read(MCP_INTEGRATION_CONTRACT_PATH)
        self.collapsed = re.sub(r"\s+", " ", self.text)

    def test_contract_names_mutating_operations(self) -> None:
        for op in (
            "attach-external-target",
            "detach-external-target",
            "verify-external-target",
            "plan",
            "activate",
            "run",
            "resume",
            "auto-continue",
            "record-final-acceptance",
        ):
            self.assertIn(
                op, self.collapsed,
                f"mcp-integration contract does not enumerate "
                f"mutating CLI subcommand {op!r}",
            )

    def test_contract_names_readonly_reporter_operations(
        self,
    ) -> None:
        for op in (
            "inspect-external-target",
            "inspect-artifacts",
            "status",
            "evaluate-final-acceptance",
            "validate-artifacts",
            "check-state",
            "view-artifact-dashboard",
            "view-desktop-actions",
        ):
            self.assertIn(
                op, self.collapsed,
                f"mcp-integration contract does not enumerate "
                f"read-only CLI reporter {op!r}",
            )


class McpIntegrationContractInternalConsistencyWithPriorPhasesTests(
    unittest.TestCase,
):
    """The Phase 10O contract MUST stay internally consistent with
    every prior contract / surface it layers on top of (Phase 10G
    UI contract, Phase 10J dashboard contract, Phase 10L desktop-
    app contract, and the shipped Phase 10H / 10I / 10K / 10M /
    10N runtime surfaces).
    """

    def setUp(self) -> None:
        self.text = _read(MCP_INTEGRATION_CONTRACT_PATH)
        self.collapsed = re.sub(r"\s+", " ", self.text)

    def test_contract_references_external_ui_contract(self) -> None:
        for fragment in (
            "docs/external-ui-contract.md",
            "Phase 10G",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"mcp-integration contract does not reference the "
                f"Phase 10G UI contract via {fragment!r}",
            )

    def test_contract_references_dashboard_contract(self) -> None:
        for fragment in (
            "Phase 10J",
            "Phase 10K",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"mcp-integration contract does not reference the "
                f"Phase 10J/10K dashboard work via {fragment!r}",
            )

    def test_contract_references_desktop_app_contract(self) -> None:
        # The contract uses compact range phrasing
        # (`Phase 10L - 10N`, `Phase 10M - 10N`) so the short
        # labels `10L` / `10M` / `10N` are what survive collapse;
        # plus the explicit `docs/desktop-app-contract.md` link
        # pins the source artifact.
        for fragment in (
            "docs/desktop-app-contract.md",
            "10L",
            "10M",
            "10N",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"mcp-integration contract does not reference the "
                f"Phase 10L/M/N desktop work via {fragment!r}",
            )

    def test_contract_references_phase_2a_evidence(self) -> None:
        for fragment in (
            "Phase 2A Evidence Collection Contract",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"mcp-integration contract does not reference the "
                f"Phase 2A evidence-collection contract via "
                f"{fragment!r}",
            )

    def test_contract_references_phase_6_memory_tree(self) -> None:
        for fragment in (
            ".agent-loop/memory/",
            "Phase 6",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"mcp-integration contract does not reference the "
                f"Phase 6 memory tree via {fragment!r}",
            )


class McpIntegrationContractReadmeAlignmentTests(unittest.TestCase):
    """README.md MUST surface Phase 10O as active and route readers
    at `docs/mcp-integration-contract.md`.
    """

    def setUp(self) -> None:
        readme = REPO_ROOT / "README.md"
        self.text = _read(readme)

    def test_readme_routes_at_mcp_integration_contract(self) -> None:
        self.assertIn(
            "docs/mcp-integration-contract.md", self.text,
            "README.md does not route readers at the Phase 10O "
            "MCP integration contract doc",
        )

    def test_readme_marks_phase_10o_as_active(self) -> None:
        self.assertIn(
            "Phase 10O", self.text,
            "README.md does not name Phase 10O as a current focus",
        )
        self.assertIn(
            "MCP Integration Contract", self.text,
            "README.md does not name the Phase 10O sub-phase title",
        )

    def test_readme_marks_phase_10o_as_documentation_only(
        self,
    ) -> None:
        for fragment in (
            "documentation form only",
            "Phase 10T",
        ):
            self.assertIn(
                fragment, self.text,
                f"README.md Phase 10O paragraph does not document "
                f"the documentation-only scope fragment "
                f"{fragment!r}",
            )

    def test_readme_routes_advanced_mcp_to_later_phases(
        self,
    ) -> None:
        # Future MCP runtime capabilities must be routed to Phase
        # 10T / 10U+ so a reader does not assume they ship in 10O.
        for fragment in (
            "Phase 10T",
            "Phase 10U",
        ):
            self.assertIn(
                fragment, self.text,
                f"README.md Phase 10O paragraph does not route "
                f"future MCP capability to {fragment!r}",
            )


class McpIntegrationContractRoadmapRoutingAlignmentTests(
    unittest.TestCase,
):
    """The Phase 10O MCP integration contract and the README's
    Phase 10O description MUST point implementers at the correct
    successor MCP runtime slices per the canonical `ROADMAP.md`:

    - Phase 10T = MCP Read-Only Assistance In Desktop App (the
      first MCP runtime slice; category 1 and category 2 only)
    - Phase 10U = MCP Action Guardrails And Per-Tool Approval
      Policies (first mutation-capable MCP work)

    A prior cycle described `Phase 10P` / `Phase 10Q` as the
    successor MCP runtime buckets. That is wrong per the current
    ROADMAP.md (Phase 10P is Desktop App Operator Setup, Phase 10Q
    is Desktop App Run Profiles) and must not silently re-appear.
    """

    def setUp(self) -> None:
        self.contract_text = _read(MCP_INTEGRATION_CONTRACT_PATH)
        self.contract_collapsed = re.sub(
            r"\s+", " ", self.contract_text,
        )
        self.readme_text = _read(REPO_ROOT / "README.md")
        self.readme_collapsed = re.sub(r"\s+", " ", self.readme_text)
        self.roadmap_text = _read(REPO_ROOT / "ROADMAP.md")
        self.roadmap_collapsed = re.sub(
            r"\s+", " ", self.roadmap_text,
        )

    def test_roadmap_pins_canonical_phase_10t_name(self) -> None:
        # Anchor: the canonical roadmap line. If this test fails,
        # ROADMAP.md was renamed and every consumer below needs
        # updating in lockstep.
        self.assertIn(
            "Phase 10T - MCP Read-Only Assistance In Desktop App",
            self.roadmap_collapsed,
        )

    def test_roadmap_pins_canonical_phase_10u_name(self) -> None:
        self.assertIn(
            "Phase 10U - MCP Action Guardrails And Per-Tool "
            "Approval Policies",
            self.roadmap_collapsed,
        )

    def test_roadmap_does_not_route_mcp_runtime_to_10p_or_10q(
        self,
    ) -> None:
        # Phase 10P / 10Q are reserved for desktop-app operator
        # setup and run-profile work respectively per ROADMAP.md.
        # They MUST NOT carry an "MCP" runtime title.
        for stale in (
            "Phase 10P - MCP",
            "Phase 10Q - MCP",
        ):
            self.assertNotIn(
                stale, self.roadmap_collapsed,
                f"ROADMAP.md still routes MCP runtime work to "
                f"{stale!r}; the canonical MCP runtime slices are "
                f"Phase 10T and Phase 10U+",
            )

    def test_contract_names_phase_10t_as_first_mcp_runtime(
        self,
    ) -> None:
        # The contract MUST name Phase 10T using the canonical
        # ROADMAP.md title so a future implementer can grep across
        # both files for the same identifier.
        self.assertIn(
            "Phase 10T", self.contract_collapsed,
            "mcp-integration contract does not name Phase 10T as "
            "the first MCP runtime slice",
        )
        self.assertIn(
            "MCP Read-Only Assistance In Desktop App",
            self.contract_collapsed,
            "mcp-integration contract does not carry the canonical "
            "Phase 10T title 'MCP Read-Only Assistance In Desktop "
            "App' from ROADMAP.md",
        )

    def test_contract_names_phase_10u_as_mutation_capable_slice(
        self,
    ) -> None:
        self.assertIn(
            "Phase 10U", self.contract_collapsed,
            "mcp-integration contract does not name Phase 10U as "
            "the first mutation-capable MCP runtime slice",
        )

    def test_contract_does_not_misroute_mcp_runtime_to_10p_or_10q(
        self,
    ) -> None:
        # Stale phrasing that previously mislabeled the successor
        # MCP runtime slices. None of these forms may re-appear in
        # the contract once the canonical routing is Phase 10T /
        # 10U+. The check is intentionally narrow to MCP-runtime
        # phrasings (Phase 10P / Phase 10Q on their own remain
        # legal text elsewhere because they are the canonical
        # desktop-app phase names).
        forbidden_phrases = (
            "Phase 10P initial slice",
            "Phase 10P read-only",
            "Phase 10P runtime",
            "Phase 10P MCP",
            "Phase 10P (MCP",
            "Phase 10Q+",
            "Phase 10Q mutation",
            "Phase 10Q MCP",
            "Phase 10Q (MCP",
        )
        for phrase in forbidden_phrases:
            self.assertNotIn(
                phrase, self.contract_collapsed,
                f"mcp-integration contract still routes MCP "
                f"runtime work via the stale phrase {phrase!r}; "
                f"per ROADMAP.md the canonical successor slices "
                f"are Phase 10T (read-only) and Phase 10U+ "
                f"(mutation-capable)",
            )

    def test_readme_names_phase_10t_for_mcp_routing(self) -> None:
        # The README's Phase 10O paragraph MUST route the reader
        # at Phase 10T for the first MCP runtime slice.
        self.assertIn(
            "Phase 10T", self.readme_collapsed,
            "README.md does not route MCP runtime readers at "
            "Phase 10T",
        )

    def test_readme_names_phase_10u_for_mcp_mutation_routing(
        self,
    ) -> None:
        self.assertIn(
            "Phase 10U", self.readme_collapsed,
            "README.md does not route MCP mutation-capable "
            "readers at Phase 10U+",
        )

    def test_readme_does_not_misroute_mcp_runtime_to_10p_or_10q(
        self,
    ) -> None:
        # Same narrow MCP-runtime phrasing guard as the contract.
        # Bare "Phase 10P" / "Phase 10Q" remain legal because the
        # README may surface them later as the desktop-app
        # operator-setup / run-profile slices.
        forbidden_phrases = (
            "Phase 10P initial slice",
            "Phase 10P read-only",
            "Phase 10P MCP",
            "Phase 10P (MCP",
            "later Phase 10P/10Q",
            "later Phase 10P / 10Q",
            "Phase 10Q+",
            "Phase 10Q mutation",
            "Phase 10Q MCP",
            "Phase 10Q (MCP",
        )
        for phrase in forbidden_phrases:
            self.assertNotIn(
                phrase, self.readme_collapsed,
                f"README.md still routes MCP runtime work via "
                f"the stale phrase {phrase!r}; per ROADMAP.md the "
                f"canonical successor slices are Phase 10T "
                f"(read-only) and Phase 10U+ (mutation-capable)",
            )

    def test_contract_and_readme_agree_on_phase_10t_title(
        self,
    ) -> None:
        # Both the contract and the README must use the canonical
        # "MCP Read-Only Assistance In Desktop App" title for
        # Phase 10T so a reader following either path lands on the
        # same identifier in ROADMAP.md.
        canonical = "MCP Read-Only Assistance In Desktop App"
        self.assertIn(
            canonical, self.contract_collapsed,
            "mcp-integration contract does not carry the "
            "canonical Phase 10T title",
        )
        self.assertIn(
            canonical, self.readme_collapsed,
            "README.md does not carry the canonical Phase 10T "
            "title",
        )


class McpServerSelectionUxContractDocExistsAndIsWellFormedTests(
    unittest.TestCase,
):
    """Phase 10S: the MCP server selection UX contract doc must
    exist on disk, be non-empty, ASCII-only, and carry the
    canonical section headers a future MCP server selection
    runtime implementer reads.
    """

    def setUp(self) -> None:
        self.path = MCP_SERVER_SELECTION_UX_CONTRACT_PATH
        self.text = _read(self.path)

    def test_doc_exists_and_non_empty(self) -> None:
        self.assertTrue(
            self.path.is_file(),
            f"Expected Phase 10S MCP server selection UX contract "
            f"doc at {self.path}",
        )
        self.assertGreater(self.path.stat().st_size, 0)

    def test_doc_is_ascii_only(self) -> None:
        raw = self.path.read_bytes()
        try:
            raw.decode("ascii")
        except UnicodeDecodeError as exc:
            self.fail(
                f"docs/mcp-server-selection-ux-contract.md contains "
                f"non-ASCII bytes: {exc}"
            )

    def test_doc_has_required_top_level_sections(self) -> None:
        for header in (
            "# MCP Server Selection UX Contract",
            "## Status",
            "## Scope",
            "## Relationship To Phase 10O MCP Integration Contract",
            "## Distinction From Shipped Artifacts And Surfaces",
            "## Server Entry Descriptor Shape",
            "## Permission Classes",
            "## Capability Category Labels",
            "## Per-Server Safety Copy",
            "## Approval Requirements",
            "## Enablement State Machine",
            "## Selection-UX Rendering Rules",
            "## Operations That Remain CLI-Only",
            "## Identity And Operator Attribution",
            "## Refusal Behavior",
            "## Source-Of-Truth Preservation",
            "## Safety Boundaries",
            "## Approval Gates",
            "## Audit Expectations",
            "## Evidence-Review Preservation",
            "## Dependencies On Later Phase 10 Slices",
            "## Out Of Scope For Phase 10S",
        ):
            self.assertIn(
                header, self.text,
                f"docs/mcp-server-selection-ux-contract.md missing "
                f"required section header {header!r}",
            )


class McpServerSelectionUxContractMarksDocumentationOnlyTests(
    unittest.TestCase,
):
    """The contract MUST be unambiguous that no MCP runtime ships
    in this slice. It defines the UX boundary; runtime work is
    deferred to Phase 10T / 10U+.
    """

    def setUp(self) -> None:
        self.text = _read(MCP_SERVER_SELECTION_UX_CONTRACT_PATH)
        self.collapsed = re.sub(r"\s+", " ", self.text)

    def test_contract_marks_documentation_only_status(self) -> None:
        for fragment in (
            "No MCP server runtime",
            "MCP server selection runtime",
            "ships in this slice",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"mcp-server-selection-ux contract does not mark "
                f"runtime work as not-yet-shipped via fragment "
                f"{fragment!r}",
            )

    def test_contract_defers_runtime_to_phase_10t_and_10u(
        self,
    ) -> None:
        for fragment in (
            "Phase 10T",
            "Phase 10U",
            "deferred to later Phase 10",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"mcp-server-selection-ux contract does not defer "
                f"MCP runtime to {fragment!r}",
            )

    def test_contract_states_no_runtime_today(self) -> None:
        # The "ZERO MCP integration paths" / "ZERO MCP server
        # selection surfaces" wording is the load-bearing claim
        # that the repository today does not ship any MCP runtime
        # surface. Without it a reader might assume the selection
        # UX is already implemented.
        for fragment in (
            "ZERO MCP integration paths",
            "ZERO MCP server selection surfaces",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"mcp-server-selection-ux contract does not state "
                f"that no MCP runtime ships today via fragment "
                f"{fragment!r}",
            )


class McpServerSelectionUxContractPinsThreePermissionClassesTests(
    unittest.TestCase,
):
    """The contract MUST pin a closed three-permission-class
    enumeration (`read_only_advisory_class`,
    `browser_inspection_class`, `deferred_mutating_class`) so a
    future runtime cannot silently introduce a fourth class.
    """

    def setUp(self) -> None:
        self.text = _read(MCP_SERVER_SELECTION_UX_CONTRACT_PATH)
        self.collapsed = re.sub(r"\s+", " ", self.text)

    def test_contract_names_all_three_permission_classes(
        self,
    ) -> None:
        for cls in (
            "read_only_advisory_class",
            "browser_inspection_class",
            "deferred_mutating_class",
        ):
            self.assertIn(
                cls, self.collapsed,
                f"mcp-server-selection-ux contract does not name "
                f"required permission class {cls!r}",
            )

    def test_contract_marks_class_enumeration_as_closed(
        self,
    ) -> None:
        for fragment in (
            "closed permission-class enumeration",
            "exactly one of the following three closed permission",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"mcp-server-selection-ux contract does not mark "
                f"the permission-class set as closed via fragment "
                f"{fragment!r}",
            )

    def test_contract_routes_deferred_mutating_class_to_phase_10u(
        self,
    ) -> None:
        # A reader hitting the deferred-mutating-class section
        # MUST be routed at Phase 10U+ for the eventual enablement.
        self.assertIn(
            "Phase 10U", self.collapsed,
            "mcp-server-selection-ux contract does not route "
            "deferred_mutating_class enablement to Phase 10U+",
        )


class McpServerSelectionUxContractPinsServerEntryDescriptorTests(
    unittest.TestCase,
):
    """The contract MUST pin a closed per-server descriptor shape
    so a future runtime cannot silently widen the rendered fields.
    """

    def setUp(self) -> None:
        self.text = _read(MCP_SERVER_SELECTION_UX_CONTRACT_PATH)
        self.collapsed = re.sub(r"\s+", " ", self.text)

    def test_contract_names_all_required_descriptor_fields(
        self,
    ) -> None:
        for field in (
            "`id`",
            "`display_name`",
            "`source_url`",
            "`permission_class`",
            "`capability_categories`",
            "`safety_copy`",
            "`approval_requirements`",
            "`enablement_state`",
            "`deferred_runtime_marker`",
            "`refusal_reason_template`",
        ):
            self.assertIn(
                field, self.text,
                f"mcp-server-selection-ux contract does not name "
                f"required descriptor field {field!r}",
            )

    def test_contract_pins_descriptor_validation_refusal(
        self,
    ) -> None:
        for fragment in (
            "refuse fail-closed on any server descriptor that is "
            "missing one of the required fields",
            "unknown `permission_class`",
            "unknown `capability_categories`",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"mcp-server-selection-ux contract does not pin "
                f"descriptor-validation refusal via fragment "
                f"{fragment!r}",
            )


class McpServerSelectionUxContractPinsApprovalRequirementsTests(
    unittest.TestCase,
):
    """The contract MUST pin a closed approval-requirement list so
    a future runtime cannot silently bypass any gate.
    """

    def setUp(self) -> None:
        self.text = _read(MCP_SERVER_SELECTION_UX_CONTRACT_PATH)
        self.collapsed = re.sub(r"\s+", " ", self.text)

    def test_contract_names_all_required_approval_requirements(
        self,
    ) -> None:
        for req in (
            "operator_acknowledged_safety_copy",
            "operator_supplied_identity",
            "approval_mode_supports_enablement",
            "phase_10t_runtime_available",
            "policy_rule_permits_enablement",
        ):
            self.assertIn(
                req, self.collapsed,
                f"mcp-server-selection-ux contract does not name "
                f"required approval-requirement {req!r}",
            )

    def test_contract_refuses_strict_mode_enablement(self) -> None:
        # The `approval_mode_supports_enablement` requirement must
        # be explicit that strict mode is refused fail-closed.
        for fragment in (
            "refuse fail-closed in",
            "strict",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"mcp-server-selection-ux contract does not pin "
                f"strict-mode refusal via fragment {fragment!r}",
            )

    def test_contract_refuses_no_runtime_enablement(self) -> None:
        # The selection UX cannot render a working enablement
        # affordance against a non-shipped runtime; the contract
        # MUST anchor this explicitly so a future runtime cannot
        # silently relax it.
        for fragment in (
            "non-shipped runtime",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"mcp-server-selection-ux contract does not pin "
                f"refusal against non-shipped runtime via fragment "
                f"{fragment!r}",
            )


class McpServerSelectionUxContractPreservesShippedHardStopsTests(
    unittest.TestCase,
):
    """Every shipped hard-stop the Phase 10G / 10J / 10L / 10O
    contracts pin MUST also apply to the selection UX verbatim.
    """

    def setUp(self) -> None:
        self.text = _read(MCP_SERVER_SELECTION_UX_CONTRACT_PATH)
        self.collapsed = re.sub(r"\s+", " ", self.text)

    def test_contract_preserves_no_git_automation(self) -> None:
        for fragment in (
            "no-Git-automation boundary",
            "no Git automation",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"mcp-server-selection-ux contract does not "
                f"preserve the no-Git-automation boundary via "
                f"fragment {fragment!r}",
            )

    def test_contract_preserves_canonical_artifact_write_ban(
        self,
    ) -> None:
        for fragment in (
            "write any canonical artifact",
            "TASK.md",
            ".agent-loop/loop-state.json",
            ".agent-loop/orchestrator.log",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"mcp-server-selection-ux contract does not "
                f"preserve the no-canonical-artifact-write boundary "
                f"via fragment {fragment!r}",
            )

    def test_contract_preserves_no_auto_fill_identity(self) -> None:
        for fragment in (
            "MUST NOT auto-fill any operator identity field",
            "$USER",
            "whoami",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"mcp-server-selection-ux contract does not "
                f"preserve the no-auto-fill identity rule via "
                f"fragment {fragment!r}",
            )

    def test_contract_preserves_phase_10i_three_control_cap(
        self,
    ) -> None:
        for fragment in (
            "Phase 10I library-callable",
            "three controls",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"mcp-server-selection-ux contract does not "
                f"preserve the Phase 10I three-control cap via "
                f"fragment {fragment!r}",
            )

    def test_contract_preserves_approval_gates(self) -> None:
        for fragment in (
            "Phase 4C activator",
            "APPROVED_FOR_ACTIVATION",
            "Phase 9G",
            "record-final-acceptance",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"mcp-server-selection-ux contract does not "
                f"preserve approval gates via fragment "
                f"{fragment!r}",
            )

    def test_contract_forbids_side_state_stores(self) -> None:
        for fragment in (
            "MUST NOT introduce an MCP-side database",
            "MUST NOT introduce a per-operator MCP-server "
            "enablement preference store",
            "MUST NOT introduce an MCP-side identity token",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"mcp-server-selection-ux contract does not forbid "
                f"side state stores via fragment {fragment!r}",
            )


class McpServerSelectionUxContractPinsCliOnlyOperationsTests(
    unittest.TestCase,
):
    """The contract MUST preserve the shipped CLI-only enumeration
    verbatim so the selection UX cannot silently dispatch a
    mutating CLI subcommand.
    """

    def setUp(self) -> None:
        self.text = _read(MCP_SERVER_SELECTION_UX_CONTRACT_PATH)

    def test_contract_lists_required_mutating_clis(self) -> None:
        for sub in (
            "attach-external-target",
            "detach-external-target",
            "verify-external-target",
            "plan",
            "activate",
            "run",
            "resume",
            "auto-continue",
            "record-final-acceptance",
            "record-token-exhaustion",
            "record-capacity-halt",
            "intake-prd",
            "set-runtime-config",
            "bootstrap-prompt",
        ):
            self.assertIn(
                sub, self.text,
                f"mcp-server-selection-ux contract does not "
                f"enumerate mutating CLI {sub!r}",
            )

    def test_contract_lists_required_read_only_advisory_clis(
        self,
    ) -> None:
        for sub in (
            "view-desktop-setup",
            "view-desktop-run-profiles",
            "view-desktop-project-start",
        ):
            self.assertIn(
                sub, self.text,
                f"mcp-server-selection-ux contract does not "
                f"surface read-only advisory CLI {sub!r} (must be "
                f"in the Phase 10S CLI-only enumeration to anchor "
                f"the surface against later 10P/10Q/10R additions)",
            )


class McpServerSelectionUxContractInternalConsistencyTests(
    unittest.TestCase,
):
    """The Phase 10S contract MUST reference and align with the
    Phase 10O integration contract; the two are companions and
    the Phase 10S permission classes are layered on top of the
    Phase 10O tool categories.
    """

    def setUp(self) -> None:
        self.text = _read(MCP_SERVER_SELECTION_UX_CONTRACT_PATH)
        self.collapsed = re.sub(r"\s+", " ", self.text)
        self.integration_text = _read(MCP_INTEGRATION_CONTRACT_PATH)
        self.integration_collapsed = re.sub(
            r"\s+", " ", self.integration_text,
        )

    def test_contract_routes_at_phase_10o_integration_doc(
        self,
    ) -> None:
        self.assertIn(
            "docs/mcp-integration-contract.md", self.text,
            "mcp-server-selection-ux contract does not route the "
            "reader at the Phase 10O integration contract doc",
        )
        self.assertIn(
            "Phase 10O", self.collapsed,
            "mcp-server-selection-ux contract does not name "
            "Phase 10O",
        )

    def test_contract_aligns_class_to_category_layering(
        self,
    ) -> None:
        for fragment in (
            "Phase 10S permission-class enumeration is layered on "
            "top of the Phase 10O tool-category enumeration",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"mcp-server-selection-ux contract does not align "
                f"its permission classes with the Phase 10O tool "
                f"categories via fragment {fragment!r}",
            )

    def test_integration_contract_does_not_yet_widen_to_selection_ux(
        self,
    ) -> None:
        # The Phase 10O contract is the runtime / safety contract;
        # it MUST NOT itself absorb the selection UX rendering
        # rules (those belong in Phase 10S). This guard catches a
        # scope-creep edit that would silently re-route the
        # selection-UX rules into the runtime doc.
        for fragment in (
            "Server Entry Descriptor Shape",
            "Per-Server Safety Copy",
            "Enablement State Machine",
            "Selection-UX Rendering Rules",
        ):
            self.assertNotIn(
                fragment, self.integration_text,
                f"docs/mcp-integration-contract.md now carries "
                f"selection-UX-specific heading {fragment!r}; that "
                f"belongs in docs/mcp-server-selection-ux-contract"
                f".md, not in the Phase 10O integration contract",
            )


class McpServerSelectionUxContractReadmeAlignmentTests(
    unittest.TestCase,
):
    """README.md MUST surface Phase 10S as active and route readers
    at `docs/mcp-server-selection-ux-contract.md`.
    """

    def setUp(self) -> None:
        readme = REPO_ROOT / "README.md"
        self.text = _read(readme)
        self.collapsed = re.sub(r"\s+", " ", self.text)

    def test_readme_routes_at_phase_10s_contract(self) -> None:
        self.assertIn(
            "docs/mcp-server-selection-ux-contract.md", self.text,
            "README.md does not route readers at the Phase 10S MCP "
            "server selection UX contract doc",
        )

    def test_readme_marks_phase_10s_as_active(self) -> None:
        self.assertIn(
            "Phase 10S", self.text,
            "README.md does not name Phase 10S as a current focus",
        )
        self.assertIn(
            "MCP Server Selection UX Contract", self.text,
            "README.md does not name the Phase 10S sub-phase title",
        )

    def test_readme_marks_phase_10s_as_documentation_only(
        self,
    ) -> None:
        for fragment in (
            "documentation form only",
            "Phase 10T",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"README.md Phase 10S paragraph does not document "
                f"the documentation-only scope fragment "
                f"{fragment!r}",
            )

    def test_readme_routes_advanced_mcp_to_later_phases(
        self,
    ) -> None:
        # Future MCP runtime capabilities must be routed to Phase
        # 10T / 10U+ so a reader does not assume they ship in 10S.
        for fragment in (
            "Phase 10T",
            "Phase 10U",
        ):
            self.assertIn(
                fragment, self.collapsed,
                f"README.md does not route future MCP capability "
                f"to {fragment!r}",
            )


class ReadmeActivePhaseClaimsAreInternallyConsistentTests(
    unittest.TestCase,
):
    """Phase 10S fix cycle: the README MUST NOT claim two different
    active phases at once. The status line above and any
    per-phase paragraph below MUST agree on which Phase 10 sub-phase
    is currently the active one.

    The bug this guards against: a per-phase paragraph leaves
    `, active)` in its opening header even after the slice has
    actually shipped and the status line has moved on to the next
    phase. The existing
    `McpServerSelectionUxContractReadmeAlignmentTests.test_readme_
    marks_phase_10s_as_active` only confirmed that `Phase 10S`
    appears somewhere; it did NOT fail when an older paragraph
    still advertised its own phase as active.
    """

    CANONICAL_ACTIVE_PHASE = "Phase 10U"
    # Matches the README per-phase paragraph header form
    # `Phase 10X (Slice Name, active|complete) ...` at the start of
    # a line. The phase id grammar matches the shipped sub-phase
    # naming used in the README (`Phase 10A` through `Phase 10Z`,
    # plus older numeric-only ids like `Phase 1` / `Phase 9G` and
    # `Fix Phase A`). We restrict to the canonical "X (slice name,
    # status)" header form so prose mentions of phase ids inside
    # paragraph bodies do not get falsely matched.
    _PHASE_HEADER_RE = re.compile(
        r"^(?P<phase>(?:Fix )?Phase [0-9]+[A-Z]?) "
        r"\([^)]*?, (?P<status>active|complete)\)",
        re.MULTILINE,
    )

    def setUp(self) -> None:
        self.text = _read(REPO_ROOT / "README.md")

    def _claimed_active(self) -> list:
        return [
            m.group("phase")
            for m in self._PHASE_HEADER_RE.finditer(self.text)
            if m.group("status") == "active"
        ]

    def test_exactly_one_phase_paragraph_claims_active(
        self,
    ) -> None:
        active = self._claimed_active()
        self.assertEqual(
            len(active), 1,
            f"README.md claims {len(active)} different phases are "
            f"active simultaneously ({active!r}); exactly one "
            f"per-phase paragraph header may carry `, active)` at "
            f"a time. The remaining claims are stale and must flip "
            f"to `, complete)`. The canonical active phase per the "
            f"status line is {self.CANONICAL_ACTIVE_PHASE!r}",
        )

    def test_active_phase_paragraph_matches_canonical_phase_10s(
        self,
    ) -> None:
        active = self._claimed_active()
        self.assertEqual(
            active, [self.CANONICAL_ACTIVE_PHASE],
            f"README.md claims active phase(s) {active!r}; per the "
            f"current `.agent-loop/current-phase.md` and the "
            f"README status line the canonical active phase is "
            f"{self.CANONICAL_ACTIVE_PHASE!r}. Any other per-phase "
            f"paragraph still marked `, active)` is stale and must "
            f"flip to `, complete)`",
        )

    def test_no_completed_phase_paragraph_still_claims_active(
        self,
    ) -> None:
        # The README status line enumerates a long list of "complete"
        # phases; any per-phase paragraph for one of those phases
        # MUST NOT contradict the status line by claiming itself
        # active. The most common drift mode: a fix cycle flips the
        # status-line summary but forgets to flip the per-phase
        # paragraph header.
        completed_sentinels = (
            "Phase 10T",
            "Phase 10S",
            "Phase 10R",
            "Phase 10Q",
            "Phase 10P",
            "Phase 10O",
            "Phase 10N",
            "Phase 10M",
            "Phase 10L",
            "Phase 10K",
            "Phase 10J",
            "Phase 10I",
            "Phase 10H",
            "Phase 10G",
            "Phase 10F",
            "Phase 10E",
            "Phase 10D",
            "Phase 10C",
            "Phase 10B",
            "Phase 10A",
        )
        active = self._claimed_active()
        stale = [p for p in active if p in completed_sentinels]
        self.assertEqual(
            stale, [],
            f"README.md per-phase paragraphs still claim "
            f"{stale!r} as `, active)` even though the status line "
            f"enumerates each of these phases as complete. Flip "
            f"the stale paragraph header(s) to `, complete)`",
        )


class McpServerSelectionUxContractDoesNotClaimRuntimeShipsTests(
    unittest.TestCase,
):
    """Anchor test: README and ROADMAP MUST NOT silently claim
    that the Phase 10S slice ships MCP runtime, MCP server
    selection runtime, or MCP enablement runtime.
    """

    def setUp(self) -> None:
        self.readme_text = _read(REPO_ROOT / "README.md")
        self.readme_collapsed = re.sub(
            r"\s+", " ", self.readme_text,
        )
        self.roadmap_text = _read(REPO_ROOT / "ROADMAP.md")
        self.roadmap_collapsed = re.sub(
            r"\s+", " ", self.roadmap_text,
        )

    def test_readme_does_not_claim_phase_10s_ships_runtime(
        self,
    ) -> None:
        # A "Phase 10S ... runtime" / "Phase 10S ... initial
        # slice" phrasing implies actual MCP runtime ships in 10S,
        # which violates the documentation-only scope.
        forbidden = (
            "Phase 10S initial slice runtime",
            "Phase 10S MCP runtime",
            "Phase 10S MCP server selection runtime",
            "Phase 10S MCP integration runtime",
            "Phase 10S read-only MCP runtime",
            "Phase 10S MCP enablement runtime",
        )
        for phrase in forbidden:
            self.assertNotIn(
                phrase, self.readme_collapsed,
                f"README.md silently claims Phase 10S ships "
                f"runtime via {phrase!r}; Phase 10S is documentation"
                f" only - runtime is deferred to Phase 10T / 10U+",
            )

    def test_roadmap_pins_phase_10s_as_selection_ux_contract(
        self,
    ) -> None:
        # The canonical roadmap line for the slice.
        self.assertIn(
            "Phase 10S",
            self.roadmap_collapsed,
            "ROADMAP.md does not name Phase 10S",
        )
        self.assertIn(
            "MCP Server Selection UX Contract",
            self.roadmap_collapsed,
            "ROADMAP.md does not pin the canonical Phase 10S title",
        )


if __name__ == "__main__":
    unittest.main()
