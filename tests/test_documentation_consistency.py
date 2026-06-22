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
ALL_OPERATOR_DOC_PATHS = (
    PHASE_8A_DOC_PATHS
    + PHASE_8B_DOC_PATHS
    + PHASE_9A_DOC_PATHS
    + PHASE_10A_DOC_PATHS
    + PHASE_10B_DOC_PATHS
    + PHASE_10C_DOC_PATHS
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
    - Phase 10C = External Target Bootstrap Contract
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
            ("Phase 10C", "External Target Bootstrap Contract"),
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
                f"10C title is 'External Target Bootstrap Contract' "
                f"and the external UI / dashboard surface is now "
                f"Phase 10G",
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

    def test_contract_marks_runtime_as_not_yet_implemented(self) -> None:
        self.assertIn(
            "is NOT yet implemented", self.collapsed,
            "bootstrap contract does not mark the bootstrap runtime "
            "as not-yet-implemented",
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


if __name__ == "__main__":
    unittest.main()
