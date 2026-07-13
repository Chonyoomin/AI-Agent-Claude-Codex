"""Phase 10AE - Framework Evaluation Beyond The Native Loop tests.

Exercises:
  - module-level constants (signal version, precedence note, halt-
    status, closed enumerations, closed registry)
  - operator-input normalizer
  - closed criterion registry + descriptor validator (framework-id
    coverage, verdict enum, native-loop-status enum)
  - `build_desktop_framework_evaluation_view(...)` shape + soft-fail
    on missing loop-state
  - renderer per-line attribution
  - `build_desktop_framework_evaluation_controls(...)` widget shape
    (COPY-PASTE only; every button clickable per the Phase 10Z /
    10AA / 10AB / 10AC / 10AD fix-cycle affordance pattern)
  - `cmd_view_desktop_framework_evaluation(...)` CLI + Phase 7C
  - integration into `assemble_desktop_app_view(...)` +
    `render_desktop_app_text(...)`
  - shipped `evaluate_framework_runtime_availability(...)` refusal
    branches (unknown framework_id, non-native framework requested)
  - non-mutation invariants (no socket, no subprocess, no
    orchestrator.log append, no loop-state mutation, no
    `_halt(...)`, no crewai / langgraph / langchain import at
    surface build time, no Phase 10I library-callable cap widening)
"""
from __future__ import annotations

import argparse
import io
import json
import socket
import sys
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock


HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import agent_loop  # noqa: E402


CONTRACT_VERSION = "phase-3a-v2"


def _make_controller(
    td: Path,
    status: str = "awaiting_claude_implementation",
    approval_mode: str = "review",
) -> Path:
    td.mkdir(parents=True, exist_ok=True)
    (td / "AGENTS.md").write_text("agents\n", encoding="utf-8")
    (td / "CLAUDE.md").write_text("claude\n", encoding="utf-8")
    (td / "TASK.md").write_text("# TASK.md\n", encoding="utf-8")
    (td / "README.md").write_text("readme\n", encoding="utf-8")
    (td / ".agent-loop").mkdir()
    (td / ".agent-loop" / "loop-state.json").write_text(
        json.dumps({
            "phase": "Phase 10 - Future Product Features",
            "sub_phase": (
                "Phase 10AE - Framework Evaluation Beyond The "
                "Native Loop"
            ),
            "task": "phase-10ae-test",
            "status": status,
            "cycle_count": 0,
            "max_cycles": 3,
            "last_verdict": None,
            "last_verdict_phase": None,
            "contract_version": CONTRACT_VERSION,
            "claude_version": "claude-opus-4-7",
            "codex_version": None,
            "orchestrator_version": "phase-3d-v0",
            "approval_mode": approval_mode,
            "awaiting_human_for": None,
        }),
        encoding="utf-8",
    )
    return td


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
class ConstantsTests(unittest.TestCase):

    def test_signal_version(self) -> None:
        self.assertEqual(
            agent_loop.DESKTOP_FRAMEWORK_EVALUATION_SIGNAL_VERSION,
            "phase-10ae-v1",
        )

    def test_halt_status(self) -> None:
        self.assertEqual(
            agent_loop.HALTED_FRAMEWORK_EVALUATION_UNSAFE,
            "halted_framework_evaluation_unsafe",
        )

    def test_framework_ids_closed_enum(self) -> None:
        self.assertEqual(
            agent_loop.FRAMEWORK_EVALUATION_FRAMEWORK_IDS,
            ("native_loop", "crewai", "langgraph", "langchain"),
        )

    def test_criterion_categories_closed_enum(self) -> None:
        self.assertEqual(
            agent_loop.FRAMEWORK_EVALUATION_CRITERION_CATEGORIES,
            (
                "shipped_boundary_preservation",
                "native_loop_strength",
                "framework_leverage_opportunity",
            ),
        )

    def test_verdicts_closed_enum(self) -> None:
        self.assertEqual(
            agent_loop.FRAMEWORK_EVALUATION_VERDICTS,
            (
                "preserves_shipped_boundary",
                "could_help_bounded",
                "would_conflict_with_shipped_boundary",
                "native_loop_only",
                "not_applicable",
            ),
        )

    def test_native_loop_statuses_closed_enum(self) -> None:
        self.assertEqual(
            agent_loop.FRAMEWORK_EVALUATION_NATIVE_LOOP_STATUSES,
            (
                "shipped_boundary_preserved",
                "native_loop_only",
                "framework_leverage_opportunity_bounded",
            ),
        )

    def test_precedence_note_pins_contract(self) -> None:
        note = (
            agent_loop.DESKTOP_FRAMEWORK_EVALUATION_PRECEDENCE_NOTE
        )
        for needle in (
            "Phase 10AE",
            "native Codex/Claude loop",
            "crewai",
            "langgraph",
            "langchain",
            "phase_10ae_runtime_available",
            "EVALUATION-ONLY",
            "HALTED_FRAMEWORK_EVALUATION_UNSAFE",
            "Phase 10I three-control library-callable cap",
            "NEVER imports crewai",
            "NEVER opens a network socket",
            "hard-coded `False`",
        ):
            self.assertIn(needle, note, needle)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
class RegistryTests(unittest.TestCase):

    def test_registry_ships_at_least_six_criteria(self) -> None:
        self.assertGreaterEqual(
            len(
                agent_loop._DESKTOP_FRAMEWORK_EVALUATION_REGISTRY
            ),
            6,
        )

    def test_every_registry_entry_passes_validator(self) -> None:
        for spec in (
            agent_loop._DESKTOP_FRAMEWORK_EVALUATION_REGISTRY
        ):
            agent_loop._desktop_framework_evaluation_validate_descriptor(
                spec,
            )

    def test_registry_covers_every_criterion_category(self) -> None:
        seen = {
            spec["criterion_category"]
            for spec in (
                agent_loop._DESKTOP_FRAMEWORK_EVALUATION_REGISTRY
            )
        }
        self.assertEqual(
            seen,
            set(
                agent_loop.FRAMEWORK_EVALUATION_CRITERION_CATEGORIES,
            ),
        )

    def test_every_criterion_covers_every_framework_id(self) -> None:
        # The validator enforces this end-to-end but pin it as a
        # dedicated regression so a future refactor cannot silently
        # drop a framework_id from a criterion.
        for spec in (
            agent_loop._DESKTOP_FRAMEWORK_EVALUATION_REGISTRY
        ):
            seen_ids = {
                e["framework_id"]
                for e in spec["framework_verdicts"]
            }
            self.assertEqual(
                seen_ids,
                set(
                    agent_loop.FRAMEWORK_EVALUATION_FRAMEWORK_IDS,
                ),
                spec["id"],
            )

    def test_every_native_loop_verdict_is_preserved(self) -> None:
        # Every criterion MUST advertise the native loop verdict as
        # `preserves_shipped_boundary` because the shipped surface's
        # entire point is to preserve the shipped boundary while
        # comparing frameworks.
        for spec in (
            agent_loop._DESKTOP_FRAMEWORK_EVALUATION_REGISTRY
        ):
            native = [
                e for e in spec["framework_verdicts"]
                if e["framework_id"] == "native_loop"
            ][0]
            self.assertEqual(
                native["verdict"],
                "preserves_shipped_boundary",
                spec["id"],
            )


# ---------------------------------------------------------------------------
# Descriptor validator
# ---------------------------------------------------------------------------
class ValidatorTests(unittest.TestCase):

    def _valid(self):
        return {
            "id": "x",
            "display_name": "X",
            "criterion_category": "shipped_boundary_preservation",
            "native_loop_status": "shipped_boundary_preserved",
            "docs_anchor": "docs/architecture.md",
            "description": "d",
            "safety_copy": "s",
            "framework_verdicts": (
                {
                    "framework_id": "native_loop",
                    "verdict": "preserves_shipped_boundary",
                    "reason": "r",
                    "evidence_anchors": (
                        "scripts/agent_loop.py::x",
                    ),
                },
                {
                    "framework_id": "crewai",
                    "verdict": "not_applicable",
                    "reason": "r",
                    "evidence_anchors": (
                        "docs/architecture.md",
                    ),
                },
                {
                    "framework_id": "langgraph",
                    "verdict": "not_applicable",
                    "reason": "r",
                    "evidence_anchors": (
                        "docs/architecture.md",
                    ),
                },
                {
                    "framework_id": "langchain",
                    "verdict": "not_applicable",
                    "reason": "r",
                    "evidence_anchors": (
                        "docs/architecture.md",
                    ),
                },
            ),
            "deferred_runtime_marker": "m",
            "refusal_reason_template": "t",
        }

    def test_valid_passes(self) -> None:
        agent_loop._desktop_framework_evaluation_validate_descriptor(
            self._valid(),
        )

    def test_non_dict_refuses(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_framework_evaluation_validate_descriptor(
                "not a dict",
            )

    def test_missing_string_field_refuses(self) -> None:
        spec = self._valid()
        del spec["display_name"]
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_framework_evaluation_validate_descriptor(
                spec,
            )

    def test_empty_string_field_refuses(self) -> None:
        spec = self._valid()
        spec["description"] = ""
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_framework_evaluation_validate_descriptor(
                spec,
            )

    def test_unknown_criterion_category_refuses(self) -> None:
        spec = self._valid()
        spec["criterion_category"] = "bogus"
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_framework_evaluation_validate_descriptor(
                spec,
            )

    def test_unknown_native_loop_status_refuses(self) -> None:
        spec = self._valid()
        spec["native_loop_status"] = "bogus"
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_framework_evaluation_validate_descriptor(
                spec,
            )

    def test_non_tuple_framework_verdicts_refuses(self) -> None:
        spec = self._valid()
        spec["framework_verdicts"] = list(
            spec["framework_verdicts"],
        )
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_framework_evaluation_validate_descriptor(
                spec,
            )

    def test_unknown_framework_id_refuses(self) -> None:
        spec = self._valid()
        spec["framework_verdicts"] = (
            {
                "framework_id": "native_loop",
                "verdict": "preserves_shipped_boundary",
                "reason": "r",
            },
            {
                "framework_id": "not_a_real_framework",
                "verdict": "not_applicable",
                "reason": "r",
            },
            {
                "framework_id": "langgraph",
                "verdict": "not_applicable",
                "reason": "r",
            },
            {
                "framework_id": "langchain",
                "verdict": "not_applicable",
                "reason": "r",
            },
        )
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_framework_evaluation_validate_descriptor(
                spec,
            )

    def test_missing_framework_id_refuses(self) -> None:
        spec = self._valid()
        spec["framework_verdicts"] = tuple(
            e for e in spec["framework_verdicts"]
            if e["framework_id"] != "langchain"
        )
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_framework_evaluation_validate_descriptor(
                spec,
            )

    def test_duplicate_framework_id_refuses(self) -> None:
        spec = self._valid()
        spec["framework_verdicts"] = spec["framework_verdicts"] + (
            {
                "framework_id": "native_loop",
                "verdict": "preserves_shipped_boundary",
                "reason": "duplicate",
            },
        )
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_framework_evaluation_validate_descriptor(
                spec,
            )

    def test_unknown_verdict_refuses(self) -> None:
        spec = self._valid()
        spec["framework_verdicts"] = (
            {
                "framework_id": "native_loop",
                "verdict": "bogus",
                "reason": "r",
            },
            {
                "framework_id": "crewai",
                "verdict": "not_applicable",
                "reason": "r",
            },
            {
                "framework_id": "langgraph",
                "verdict": "not_applicable",
                "reason": "r",
            },
            {
                "framework_id": "langchain",
                "verdict": "not_applicable",
                "reason": "r",
            },
        )
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_framework_evaluation_validate_descriptor(
                spec,
            )

    def test_missing_reason_refuses(self) -> None:
        spec = self._valid()
        spec["framework_verdicts"] = (
            {
                "framework_id": "native_loop",
                "verdict": "preserves_shipped_boundary",
                "reason": "",
                "evidence_anchors": (
                    "scripts/agent_loop.py::x",
                ),
            },
            {
                "framework_id": "crewai",
                "verdict": "not_applicable",
                "reason": "r",
                "evidence_anchors": (
                    "docs/architecture.md",
                ),
            },
            {
                "framework_id": "langgraph",
                "verdict": "not_applicable",
                "reason": "r",
                "evidence_anchors": (
                    "docs/architecture.md",
                ),
            },
            {
                "framework_id": "langchain",
                "verdict": "not_applicable",
                "reason": "r",
                "evidence_anchors": (
                    "docs/architecture.md",
                ),
            },
        )
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_framework_evaluation_validate_descriptor(
                spec,
            )

    # ------------------------------------------------------------------
    # Phase 10AE refinement: auditability anchors
    # ------------------------------------------------------------------
    def test_missing_docs_anchor_refuses(self) -> None:
        # Phase 10AE refinement: every criterion MUST carry a
        # non-empty docs_anchor so a reviewer can navigate from a
        # surfaced criterion to a canonical / advisory shipped
        # artifact. A missing docs_anchor is refused fail-closed.
        spec = self._valid()
        del spec["docs_anchor"]
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop._desktop_framework_evaluation_validate_descriptor(
                spec,
            )
        self.assertIn("docs_anchor", cm.exception.reason)

    def test_empty_docs_anchor_refuses(self) -> None:
        for bad in ("", "   ", "\t"):
            spec = self._valid()
            spec["docs_anchor"] = bad
            with self.assertRaises(agent_loop.HaltError) as cm:
                agent_loop._desktop_framework_evaluation_validate_descriptor(
                    spec,
                )
            self.assertIn("docs_anchor", cm.exception.reason)

    def test_non_string_docs_anchor_refuses(self) -> None:
        spec = self._valid()
        spec["docs_anchor"] = 42
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_framework_evaluation_validate_descriptor(
                spec,
            )

    def test_missing_evidence_anchors_refuses(self) -> None:
        # Phase 10AE refinement: every framework_verdict MUST
        # carry a non-empty evidence_anchors tuple citing the
        # repo-relative artifact(s) backing the verdict.
        spec = self._valid()
        # Rebuild verdicts without evidence_anchors on the first entry.
        head = dict(spec["framework_verdicts"][0])
        del head["evidence_anchors"]
        spec["framework_verdicts"] = (
            head,
        ) + spec["framework_verdicts"][1:]
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop._desktop_framework_evaluation_validate_descriptor(
                spec,
            )
        self.assertIn("evidence_anchors", cm.exception.reason)

    def test_empty_evidence_anchors_tuple_refuses(self) -> None:
        spec = self._valid()
        head = dict(spec["framework_verdicts"][0])
        head["evidence_anchors"] = ()
        spec["framework_verdicts"] = (
            head,
        ) + spec["framework_verdicts"][1:]
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop._desktop_framework_evaluation_validate_descriptor(
                spec,
            )
        self.assertIn("evidence_anchors", cm.exception.reason)

    def test_non_tuple_evidence_anchors_refuses(self) -> None:
        # A list would silently coerce; the shipped invariant
        # demands a tuple to match the closed-vocabulary shape used
        # elsewhere in the descriptor (`framework_verdicts` is also
        # a tuple).
        spec = self._valid()
        head = dict(spec["framework_verdicts"][0])
        head["evidence_anchors"] = [
            "scripts/agent_loop.py::x",
        ]
        spec["framework_verdicts"] = (
            head,
        ) + spec["framework_verdicts"][1:]
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop._desktop_framework_evaluation_validate_descriptor(
                spec,
            )
        self.assertIn("evidence_anchors", cm.exception.reason)

    def test_empty_evidence_anchor_entry_refuses(self) -> None:
        for bad in ("", "   ", 42):
            spec = self._valid()
            head = dict(spec["framework_verdicts"][0])
            head["evidence_anchors"] = (bad,)
            spec["framework_verdicts"] = (
                head,
            ) + spec["framework_verdicts"][1:]
            with self.assertRaises(agent_loop.HaltError) as cm:
                agent_loop._desktop_framework_evaluation_validate_descriptor(
                    spec,
                )
            self.assertIn("evidence_anchors", cm.exception.reason)

    def test_every_shipped_registry_entry_names_anchors(self) -> None:
        # Regression pin: every shipped registry entry MUST carry a
        # non-empty docs_anchor and each of its four framework_
        # verdicts MUST carry a non-empty evidence_anchors tuple.
        # A future edit that forgets an anchor on any new criterion
        # would violate the Phase 10AE auditability rule.
        for spec in agent_loop._DESKTOP_FRAMEWORK_EVALUATION_REGISTRY:
            self.assertIsInstance(spec["docs_anchor"], str)
            self.assertTrue(
                spec["docs_anchor"].strip(),
                spec["id"],
            )
            for entry in spec["framework_verdicts"]:
                anchors = entry["evidence_anchors"]
                self.assertIsInstance(anchors, tuple, spec["id"])
                self.assertGreaterEqual(
                    len(anchors), 1, (spec["id"], entry["framework_id"]),
                )
                for a in anchors:
                    self.assertIsInstance(a, str, spec["id"])
                    self.assertTrue(
                        a.strip(),
                        (spec["id"], entry["framework_id"]),
                    )


# ---------------------------------------------------------------------------
# Operator-input normalizer
# ---------------------------------------------------------------------------
class OperatorInputsNormalizerTests(unittest.TestCase):

    def test_none_returns_empty(self) -> None:
        got = (
            agent_loop._desktop_framework_evaluation_normalize_operator_inputs(
                None,
            )
        )
        self.assertEqual(got["identity"], "")
        self.assertEqual(
            got["acknowledged_criterion_ids"], frozenset(),
        )

    def test_non_dict_refuses(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_framework_evaluation_normalize_operator_inputs(
                "not a dict",
            )

    def test_non_str_identity_refuses(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_framework_evaluation_normalize_operator_inputs(
                {"identity": 42},
            )

    def test_non_iterable_acknowledged_refuses(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_framework_evaluation_normalize_operator_inputs(
                {"acknowledged_criterion_ids": 42},
            )

    def test_non_str_ack_member_refuses(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_framework_evaluation_normalize_operator_inputs(
                {"acknowledged_criterion_ids": (42,)},
            )

    def test_happy_path(self) -> None:
        got = (
            agent_loop._desktop_framework_evaluation_normalize_operator_inputs(
                {
                    "identity": "alice",
                    "acknowledged_criterion_ids": (
                        "codex_claude_ownership_boundary_"
                        "preservation",
                    ),
                },
            )
        )
        self.assertEqual(got["identity"], "alice")
        self.assertEqual(
            got["acknowledged_criterion_ids"],
            frozenset({
                "codex_claude_ownership_boundary_preservation",
            }),
        )


# ---------------------------------------------------------------------------
# build_desktop_framework_evaluation_view
# ---------------------------------------------------------------------------
class BuildViewTests(unittest.TestCase):

    def test_view_shape_fields(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_framework_evaluation_view(
                    controller,
                )
            )
        for key in (
            "view_signal_version",
            "controller_path_canonical",
            "current_loop_state_status",
            "controller_loop_state_approval_mode",
            "current_loop_state_phase",
            "current_loop_state_sub_phase",
            "current_loop_state_cycle_count",
            "phase_10ae_runtime_available",
            "operator_inputs",
            "framework_ids",
            "criterion_categories",
            "verdicts",
            "native_loop_statuses",
            "criteria",
            "verdict_summary_counts",
            "precedence_note",
        ):
            self.assertIn(key, view, key)
        self.assertEqual(
            view["view_signal_version"], "phase-10ae-v1",
        )
        # No framework runtime is shipped in this slice.
        self.assertFalse(view["phase_10ae_runtime_available"])

    def test_view_soft_fails_on_missing_loop_state(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            (controller / ".agent-loop" / "loop-state.json").unlink()
            view = (
                agent_loop.build_desktop_framework_evaluation_view(
                    controller,
                )
            )
        self.assertIsNone(view["current_loop_state_status"])

    def test_operator_inputs_threaded(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_framework_evaluation_view(
                    controller,
                    operator_inputs={
                        "identity": "alice",
                        "acknowledged_criterion_ids": (
                            "codex_claude_ownership_boundary_"
                            "preservation",
                        ),
                    },
                )
            )
        self.assertEqual(
            view["operator_inputs"]["identity"], "alice",
        )
        self.assertEqual(
            view["operator_inputs"][
                "acknowledged_criterion_ids"
            ],
            [
                "codex_claude_ownership_boundary_preservation",
            ],
        )
        acked = [
            c for c in view["criteria"]
            if c["id"]
            == "codex_claude_ownership_boundary_preservation"
        ][0]
        self.assertTrue(acked["operator_acknowledged"])

    def test_verdict_summary_counts_present(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_framework_evaluation_view(
                    controller,
                )
            )
        counts = view["verdict_summary_counts"]
        # every framework_id is a key
        self.assertEqual(
            set(counts.keys()),
            set(agent_loop.FRAMEWORK_EVALUATION_FRAMEWORK_IDS),
        )
        # native_loop MUST have every criterion counted as
        # `preserves_shipped_boundary`.
        expected_count = len(view["criteria"])
        self.assertEqual(
            counts["native_loop"]["preserves_shipped_boundary"],
            expected_count,
        )

    def test_view_criteria_include_docs_anchor(self) -> None:
        # Phase 10AE refinement: the assembled view MUST surface a
        # non-empty docs_anchor per criterion so the operator-
        # visible renderer + CLI reporter can navigate from the
        # verdict to the canonical shipping artifact that pins the
        # boundary.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_framework_evaluation_view(
                    controller,
                )
            )
        for criterion in view["criteria"]:
            self.assertIn("docs_anchor", criterion, criterion["id"])
            self.assertIsInstance(
                criterion["docs_anchor"], str, criterion["id"],
            )
            self.assertTrue(
                criterion["docs_anchor"].strip(), criterion["id"],
            )

    def test_view_verdicts_include_evidence_anchors(self) -> None:
        # Phase 10AE refinement: every per-framework verdict in the
        # assembled view MUST surface a non-empty evidence_anchors
        # list so a reviewer can navigate from the verdict to the
        # shipped artifact(s) backing it.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_framework_evaluation_view(
                    controller,
                )
            )
        for criterion in view["criteria"]:
            for entry in criterion["framework_verdicts"]:
                self.assertIn(
                    "evidence_anchors", entry,
                    (criterion["id"], entry["framework_id"]),
                )
                # View surfaces the anchors as a list (JSON-
                # friendly) rather than the descriptor's tuple.
                self.assertIsInstance(
                    entry["evidence_anchors"], list,
                    (criterion["id"], entry["framework_id"]),
                )
                self.assertGreaterEqual(
                    len(entry["evidence_anchors"]), 1,
                    (criterion["id"], entry["framework_id"]),
                )


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------
class RendererTests(unittest.TestCase):

    def test_render_includes_attribution_tags(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_framework_evaluation_view(
                    controller,
                )
            )
        output = "\n".join(
            agent_loop.render_desktop_framework_evaluation_text(
                view,
            ),
        )
        for tag in (
            "phase-10ae-v1",
            "[canonical mirror]",
            "[advisory]",
            "[framework-evaluation]",
            "[framework-criterion]",
            "[framework-verdict]",
            "[framework-summary]",
            "[deferred-runtime]",
            "[refused]",
            # Phase 10AE refinement: auditability anchor tags.
            "[framework-anchor]",
            "[framework-evidence]",
        ):
            self.assertIn(tag, output, tag)

    def test_render_surfaces_shipped_anchor_citations(self) -> None:
        # Phase 10AE refinement: the rendered text MUST include the
        # concrete anchor citations from the shipped registry so
        # the operator sees the actual navigation targets, not
        # just the tag.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_framework_evaluation_view(
                    controller,
                )
            )
        output = "\n".join(
            agent_loop.render_desktop_framework_evaluation_text(
                view,
            ),
        )
        # Sample concrete anchors from the shipped registry.
        for anchor in (
            "docs/controlled-concurrency-contract.md",
            "docs/approval-modes.md",
            "docs/desktop-app-contract.md",
            "docs/mcp-integration-contract.md",
            "AGENTS.md",
            "scripts/agent_loop.py::_DESKTOP_CONCURRENCY_OWNERSHIP_MAP",
            "scripts/agent_loop.py::_fire_strict_gate",
            "scripts/agent_loop.py::load_loop_state",
            "scripts/agent_loop.py::enforce_overlap_safe_runtime_gate",
        ):
            self.assertIn(anchor, output, anchor)

    def test_render_never_advertises_shipped_framework_runtime(
        self,
    ) -> None:
        # The rendered text MUST advertise the framework-evaluation
        # runtime as UNAVAILABLE per the shipped
        # `phase_10ae_runtime_available=False` flag.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_framework_evaluation_view(
                    controller,
                )
            )
        output = "\n".join(
            agent_loop.render_desktop_framework_evaluation_text(
                view,
            ),
        )
        self.assertIn(
            "phase_10ae_runtime_available", output,
        )
        # `EVALUATION-ONLY` copy MUST appear so the reviewer sees
        # explicitly that no framework runtime is dispatched.
        self.assertIn("EVALUATION view only", output)


# ---------------------------------------------------------------------------
# Controls builder
# ---------------------------------------------------------------------------
class ControlsBuilderTests(unittest.TestCase):

    def test_controls_one_per_criterion(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_framework_evaluation_view(
                    controller,
                )
            )
            controls = (
                agent_loop.build_desktop_framework_evaluation_controls(
                    view,
                )
            )
        self.assertEqual(
            len(controls), len(view["criteria"]),
        )

    def test_every_control_dispatch_mode_is_copy_paste(
        self,
    ) -> None:
        # Phase 10I cap: NO new library-callable controls.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_framework_evaluation_view(
                    controller,
                )
            )
            controls = (
                agent_loop.build_desktop_framework_evaluation_controls(
                    view,
                )
            )
        for control in controls:
            self.assertEqual(
                control["dispatch_mode"], "copy_paste",
                control["id"],
            )

    def test_every_control_enabled_true_runtime_false(self) -> None:
        # Phase 10Z / 10AA / 10AB / 10AC / 10AD affordance pattern:
        # `enabled=True` (copy affordance available) while
        # `runtime_enabled=False` (no shipped framework runtime).
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_framework_evaluation_view(
                    controller,
                )
            )
            controls = (
                agent_loop.build_desktop_framework_evaluation_controls(
                    view,
                )
            )
        for control in controls:
            self.assertTrue(control["enabled"], control["id"])
            self.assertFalse(
                control["runtime_enabled"], control["id"],
            )


# ---------------------------------------------------------------------------
# cmd_view_desktop_framework_evaluation
# ---------------------------------------------------------------------------
class CmdViewDesktopFrameworkEvaluationTests(unittest.TestCase):

    def test_missing_controller_root_returns_exit_2(self) -> None:
        args = argparse.Namespace(controller_root=None)
        buf = io.StringIO()
        with redirect_stderr(buf):
            rc = agent_loop.cmd_view_desktop_framework_evaluation(
                args,
            )
        self.assertEqual(rc, 2)
        self.assertIn(
            "[desktop-framework-evaluation] REFUSED",
            buf.getvalue(),
        )

    def test_missing_markers_returns_exit_2(self) -> None:
        with TemporaryDirectory() as td:
            controller = Path(td) / "c"
            controller.mkdir()
            args = argparse.Namespace(
                controller_root=str(controller),
                operator_identity=None,
                acknowledge_criterion=None,
            )
            buf = io.StringIO()
            with redirect_stderr(buf):
                rc = (
                    agent_loop.cmd_view_desktop_framework_evaluation(
                        args,
                    )
                )
        self.assertEqual(rc, 2)
        self.assertIn(
            "[desktop-framework-evaluation] REFUSED",
            buf.getvalue(),
        )

    def test_success_returns_exit_0(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            args = argparse.Namespace(
                controller_root=str(controller),
                operator_identity=None,
                acknowledge_criterion=None,
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = (
                    agent_loop.cmd_view_desktop_framework_evaluation(
                        args,
                    )
                )
        self.assertEqual(rc, 0)
        self.assertIn("phase-10ae-v1", buf.getvalue())


# ---------------------------------------------------------------------------
# evaluate_framework_runtime_availability (shipped runtime helper)
# ---------------------------------------------------------------------------
class EvaluateFrameworkRuntimeAvailabilityTests(unittest.TestCase):

    def test_unknown_framework_id_raises_halt_error(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            with self.assertRaises(agent_loop.HaltError) as cm:
                agent_loop.evaluate_framework_runtime_availability(
                    controller, "not_a_real_framework",
                )
        self.assertEqual(
            cm.exception.status,
            agent_loop.HALTED_FRAMEWORK_EVALUATION_UNSAFE,
        )
        self.assertIn(
            "not_a_real_framework", cm.exception.reason,
        )

    def test_crewai_request_refuses(self) -> None:
        # No framework runtime is shipped in this slice; a request
        # for the crewai runtime MUST refuse fail-closed.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            with self.assertRaises(agent_loop.HaltError) as cm:
                agent_loop.evaluate_framework_runtime_availability(
                    controller, "crewai",
                )
        self.assertEqual(
            cm.exception.status,
            agent_loop.HALTED_FRAMEWORK_EVALUATION_UNSAFE,
        )

    def test_langgraph_request_refuses(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            with self.assertRaises(agent_loop.HaltError):
                agent_loop.evaluate_framework_runtime_availability(
                    controller, "langgraph",
                )

    def test_langchain_request_refuses(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            with self.assertRaises(agent_loop.HaltError):
                agent_loop.evaluate_framework_runtime_availability(
                    controller, "langchain",
                )

    def test_native_loop_request_returns_availability(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            got = (
                agent_loop.evaluate_framework_runtime_availability(
                    controller, "native_loop",
                )
            )
        self.assertEqual(got["framework_id"], "native_loop")
        self.assertTrue(got["runtime_available"])
        # native_loop MUST have every criterion counted as
        # `preserves_shipped_boundary` per the shipped registry.
        self.assertGreaterEqual(
            got["verdict_summary_counts"][
                "preserves_shipped_boundary"
            ],
            6,
        )


# ---------------------------------------------------------------------------
# Desktop app integration
# ---------------------------------------------------------------------------
class DesktopAppIntegrationTests(unittest.TestCase):

    def test_assemble_includes_framework_evaluation_sub_view(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.assemble_desktop_app_view(controller)
        self.assertIn("framework_evaluation_view", view)
        sv = view["framework_evaluation_view"]
        self.assertIsInstance(sv, dict)
        self.assertEqual(
            sv["view_signal_version"], "phase-10ae-v1",
        )

    def test_render_includes_phase_10ae_label(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.assemble_desktop_app_view(controller)
            lines = agent_loop.render_desktop_app_text(view)
        output = "\n".join(lines)
        self.assertIn(
            "=== Framework Evaluation (Phase 10AE) ===",
            output,
        )
        self.assertIn("phase-10ae-v1", output)


# ---------------------------------------------------------------------------
# Non-mutation invariants
# ---------------------------------------------------------------------------
class NonMutationInvariantsTests(unittest.TestCase):

    def test_view_does_not_open_socket(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            with mock.patch.object(socket, "socket") as p:
                agent_loop.build_desktop_framework_evaluation_view(
                    controller,
                )
        p.assert_not_called()

    def test_view_does_not_spawn_subprocess(self) -> None:
        import subprocess
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            patches = [
                mock.patch.object(subprocess, "run"),
                mock.patch.object(subprocess, "Popen"),
                mock.patch.object(subprocess, "call"),
                mock.patch.object(subprocess, "check_call"),
                mock.patch.object(subprocess, "check_output"),
                mock.patch("os.system"),
            ]
            mocks = [p.start() for p in patches]
            try:
                agent_loop.build_desktop_framework_evaluation_view(
                    controller,
                )
            finally:
                for p in patches:
                    p.stop()
        for m in mocks:
            m.assert_not_called()

    def test_view_does_not_invoke_halt(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            with mock.patch.object(agent_loop, "_halt") as h:
                agent_loop.build_desktop_framework_evaluation_view(
                    controller,
                )
        h.assert_not_called()

    def test_view_does_not_mutate_loop_state(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            ls = controller / ".agent-loop" / "loop-state.json"
            before = ls.read_bytes()
            agent_loop.build_desktop_framework_evaluation_view(
                controller,
            )
            after = ls.read_bytes()
        self.assertEqual(before, after)

    def test_view_does_not_append_orchestrator_log(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            log_path = (
                controller / ".agent-loop" / "orchestrator.log"
            )
            agent_loop.build_desktop_framework_evaluation_view(
                controller,
            )
            self.assertFalse(log_path.exists())

    def test_view_does_not_import_crewai_langgraph_langchain(
        self,
    ) -> None:
        # Snapshot the sys.modules keyset before / after the view
        # build; the shipped surface MUST NOT lazy-import crewai /
        # langgraph / langchain at build time (a fresh sub-process
        # or an environment without those packages must not fail).
        before = set(sys.modules.keys())
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            agent_loop.build_desktop_framework_evaluation_view(
                controller,
            )
        after = set(sys.modules.keys())
        added = after - before
        for name in added:
            self.assertFalse(
                name == "crewai"
                or name.startswith("crewai.")
                or name == "langgraph"
                or name.startswith("langgraph.")
                or name == "langchain"
                or name.startswith("langchain."),
                name,
            )

    def test_view_never_launches_concurrent_worker(self) -> None:
        import threading
        import multiprocessing
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            patches = [
                mock.patch.object(threading, "Thread"),
                mock.patch.object(multiprocessing, "Process"),
                mock.patch.object(multiprocessing, "Pool"),
            ]
            mocks = [p.start() for p in patches]
            try:
                agent_loop.build_desktop_framework_evaluation_view(
                    controller,
                )
            finally:
                for p in patches:
                    p.stop()
        for m in mocks:
            m.assert_not_called()

    def test_phase_10i_library_callable_cap_not_widened(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_framework_evaluation_view(
                    controller,
                )
            )
            controls = (
                agent_loop.build_desktop_framework_evaluation_controls(
                    view,
                )
            )
        for control in controls:
            self.assertEqual(
                control["dispatch_mode"], "copy_paste",
                control["id"],
            )
        library_callable = [
            c for c in agent_loop._EXTERNAL_UI_CONTROL_REGISTRY
            if c.get("dispatch_mode") == "library_call"
        ]
        self.assertEqual(
            {c["id"] for c in library_callable},
            {
                "view-external-status",
                "view-external-controls",
                "inspect-external-target",
            },
        )


if __name__ == "__main__":
    unittest.main()
