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
ARCHITECTURE_PATH = REPO_ROOT / "docs" / "architecture.md"
USAGE_PATH = REPO_ROOT / "docs" / "usage.md"
PHASE_8A_DOC_PATHS = (ARCHITECTURE_PATH, USAGE_PATH)

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


if __name__ == "__main__":
    unittest.main()
