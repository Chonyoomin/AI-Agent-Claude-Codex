"""Phase 10V - RAG Source Selection Contract And Desktop UX tests.

Exercises:
  - module-level constants (signal version, precedence note,
    closed source-type / provenance / advisory-labeling /
    freshness / enablement / approval-requirement enumerations,
    permitted approval-mode set, freshness threshold)
  - the closed `_DESKTOP_RAG_SOURCE_SELECTION_REGISTRY` shape
  - the `_desktop_rag_source_selection_validate_descriptor(...)`
    validator (positive + every closed-enumeration negative)
  - the pure file-stat freshness probe (fresh / stale / missing /
    unknown branches)
  - per-requirement approval-state computation
  - the closed three-state enablement state machine including
    the Phase 10V fail-closed default
    (`refused_until_policy_update`) that survives even with
    every operator input satisfied
  - the `refused_until_policy_update` advisory_label_rule
    short-circuit
  - `build_desktop_rag_source_selection_view(...)` shape +
    HaltError soft-failure on the loop-state delegate
  - `render_desktop_rag_source_selection_text(...)` per-line
    attribution
  - `build_desktop_rag_source_selection_controls(...)` widget
    descriptor shape (every control disabled in this slice
    because `phase_10v_runtime_available` is hard-coded False)
  - `cmd_view_desktop_rag_source_selection(...)` CLI handler
    wiring (Phase-10L-mandated `--controller-root` REQUIRED
    refusal, missing-marker refusal, Phase 7C always-exit-0
    rule, handler-registered, parser-accepts-subcommand,
    operator-input flag wiring)
  - integration into `assemble_desktop_app_view(...)` and
    `render_desktop_app_text(...)` (the new `RAG Source
    Selection (Phase 10V)` sub-view)
  - non-mutation invariants (no orchestrator.log write, no
    loop-state mutation, no `_halt(...)` invocation, no
    subprocess spawn, no network socket open, no Phase 10I cap
    widening, no canonical artifact write, no source CONTENT
    read)
"""
from __future__ import annotations

import argparse
import io
import json
import os
import socket
import sys
import time
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
    (td / "TASK.md").write_text(
        "# TASK.md\n## Human Objective\n\ntest task\n",
        encoding="utf-8",
    )
    (td / "README.md").write_text("readme\n", encoding="utf-8")
    (td / ".agent-loop").mkdir()
    (td / ".agent-loop" / "loop-state.json").write_text(
        json.dumps({
            "phase": "Phase 10 - Future Product Features",
            "sub_phase": (
                "Phase 10V - RAG Source Selection Contract "
                "And Desktop UX"
            ),
            "task": "phase-10v-test",
            "status": status,
            "cycle_count": 1,
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
    (td / ".agent-loop" / "codex-review.md").write_text(
        "test review\n", encoding="utf-8",
    )
    (td / ".agent-loop" / "git-diff.patch").write_text(
        "diff\n", encoding="utf-8",
    )
    return td


def _full_inputs() -> dict:
    """Return per-session operator inputs that satisfy every
    operator-side approval requirement for every registry source.
    """
    source_ids = [
        spec["id"]
        for spec in (
            agent_loop._DESKTOP_RAG_SOURCE_SELECTION_REGISTRY
        )
    ]
    return {
        "identity": "yoomin",
        "acknowledged_source_ids": frozenset(source_ids),
    }


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
class ConstantsTests(unittest.TestCase):

    def test_signal_version(self) -> None:
        self.assertEqual(
            agent_loop.DESKTOP_RAG_SOURCE_SELECTION_SIGNAL_VERSION,
            "phase-10v-v1",
        )

    def test_precedence_note_pins_phase_10v_contract(self) -> None:
        note = (
            agent_loop.DESKTOP_RAG_SOURCE_SELECTION_PRECEDENCE_NOTE
        )
        for needle in (
            "Phase 10V",
            "Phase 10O",
            "Phase 10S",
            "Phase 10T",
            "Phase 10U",
            "Phase 10I",
            "refused_until_policy_update",
            "phase_10v_runtime_available",
            "NEVER spawns a subprocess",
            "NEVER opens a network socket",
            "NEVER reads source CONTENT",
            "NEVER builds an embeddings index",
            "NEVER mutates any canonical artifact",
            "NEVER widens the Phase 10I cap",
        ):
            self.assertIn(needle, note)

    def test_source_types_closed_enumeration(self) -> None:
        self.assertEqual(
            agent_loop.RAG_SOURCE_TYPES,
            (
                "repo_local_docs",
                "repo_local_prds",
                "repo_local_notes",
                "repo_local_standards",
                "repo_local_evidence",
            ),
        )

    def test_provenance_categories_closed_enumeration(
        self,
    ) -> None:
        self.assertEqual(
            agent_loop.RAG_PROVENANCE_CATEGORIES,
            (
                "checked_in_documentation",
                "checked_in_planning_artifact",
                "checked_in_standard",
                "operator_supplied_notes",
                "transient_evidence",
            ),
        )

    def test_freshness_states_closed_enumeration(self) -> None:
        self.assertEqual(
            agent_loop.RAG_FRESHNESS_STATES,
            ("fresh", "stale", "missing", "unknown"),
        )

    def test_advisory_labeling_rules_closed_enumeration(
        self,
    ) -> None:
        self.assertEqual(
            agent_loop.RAG_ADVISORY_LABELING_RULES,
            (
                "advisory_only_no_canonical_substitution",
                "advisory_with_provenance_required",
                "refused_until_policy_update",
            ),
        )

    def test_enablement_states_closed_enumeration(self) -> None:
        self.assertEqual(
            agent_loop.RAG_SOURCE_ENABLEMENT_STATES,
            (
                "disabled_by_default",
                "enabled_pending_runtime",
                "refused_until_policy_update",
            ),
        )

    def test_approval_requirements_closed_enumeration(
        self,
    ) -> None:
        self.assertEqual(
            agent_loop.RAG_SOURCE_APPROVAL_REQUIREMENTS,
            (
                "operator_acknowledged_advisory_labeling",
                "operator_supplied_identity",
                "approval_mode_supports_selection",
                "phase_10v_runtime_available",
                "source_path_present_in_repo",
            ),
        )

    def test_permitted_approval_modes(self) -> None:
        self.assertEqual(
            agent_loop.RAG_SOURCE_PERMITTED_APPROVAL_MODES,
            frozenset({"review", "autonomous"}),
        )

    def test_freshness_threshold_constant(self) -> None:
        self.assertEqual(
            agent_loop.RAG_SOURCE_FRESHNESS_STALE_THRESHOLD_SECONDS,
            30 * 24 * 3600,
        )


# ---------------------------------------------------------------------------
# Registry shape
# ---------------------------------------------------------------------------
class RegistryShapeTests(unittest.TestCase):

    def test_registry_is_non_empty_tuple(self) -> None:
        registry = (
            agent_loop._DESKTOP_RAG_SOURCE_SELECTION_REGISTRY
        )
        self.assertIsInstance(registry, tuple)
        self.assertGreater(len(registry), 0)

    def test_every_registry_entry_validates(self) -> None:
        for spec in (
            agent_loop._DESKTOP_RAG_SOURCE_SELECTION_REGISTRY
        ):
            agent_loop._desktop_rag_source_selection_validate_descriptor(
                spec,
            )

    def test_every_registry_id_unique(self) -> None:
        ids = [
            spec["id"]
            for spec in (
                agent_loop._DESKTOP_RAG_SOURCE_SELECTION_REGISTRY
            )
        ]
        self.assertEqual(len(ids), len(set(ids)))

    def test_registry_covers_every_source_type(self) -> None:
        seen = {
            spec["source_type"]
            for spec in (
                agent_loop._DESKTOP_RAG_SOURCE_SELECTION_REGISTRY
            )
        }
        self.assertEqual(
            seen,
            set(agent_loop.RAG_SOURCE_TYPES),
        )


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------
class ValidatorTests(unittest.TestCase):

    def _valid_spec(self) -> dict:
        return dict(
            agent_loop._DESKTOP_RAG_SOURCE_SELECTION_REGISTRY[0]
        )

    def test_accepts_valid_spec(self) -> None:
        agent_loop._desktop_rag_source_selection_validate_descriptor(
            self._valid_spec(),
        )

    def test_refuses_non_dict(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_rag_source_selection_validate_descriptor(
                ["nope"],
            )

    def test_refuses_missing_string_field(self) -> None:
        spec = self._valid_spec()
        del spec["display_name"]
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_rag_source_selection_validate_descriptor(
                spec,
            )

    def test_refuses_empty_string_field(self) -> None:
        spec = self._valid_spec()
        spec["description"] = ""
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_rag_source_selection_validate_descriptor(
                spec,
            )

    def test_refuses_missing_list_field(self) -> None:
        spec = self._valid_spec()
        del spec["selection_steps"]
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_rag_source_selection_validate_descriptor(
                spec,
            )

    def test_refuses_unknown_source_type(self) -> None:
        spec = self._valid_spec()
        spec["source_type"] = "remote_grafana_dashboard"
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop._desktop_rag_source_selection_validate_descriptor(
                spec,
            )
        self.assertIn("source_type", str(cm.exception))

    def test_refuses_unknown_provenance(self) -> None:
        spec = self._valid_spec()
        spec["provenance"] = "third_party_blog"
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop._desktop_rag_source_selection_validate_descriptor(
                spec,
            )
        self.assertIn("provenance", str(cm.exception))

    def test_refuses_unknown_advisory_label_rule(self) -> None:
        spec = self._valid_spec()
        spec["advisory_label_rule"] = "canonical_replacement"
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop._desktop_rag_source_selection_validate_descriptor(
                spec,
            )
        self.assertIn(
            "advisory_label_rule", str(cm.exception),
        )

    def test_refuses_unknown_approval_requirement(self) -> None:
        spec = self._valid_spec()
        spec["approval_requirements"] = (
            "unknown_requirement",
        )
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop._desktop_rag_source_selection_validate_descriptor(
                spec,
            )
        self.assertIn(
            "approval_requirements", str(cm.exception),
        )

    def test_refuses_unknown_step_type(self) -> None:
        spec = self._valid_spec()
        spec["selection_steps"] = (
            {"type": "shell_exec", "content": "rm -rf /"},
        )
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop._desktop_rag_source_selection_validate_descriptor(
                spec,
            )
        self.assertIn("selection_step type", str(cm.exception))


# ---------------------------------------------------------------------------
# Freshness probe
# ---------------------------------------------------------------------------
class FreshnessProbeTests(unittest.TestCase):

    def test_missing_source_marks_missing(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            spec = {
                "path_canonical_rel": (
                    "does_not_exist.md"
                ),
            }
            probe = (
                agent_loop._desktop_rag_source_selection_probe_freshness(
                    controller, spec,
                )
            )
        self.assertFalse(probe["exists"])
        self.assertEqual(probe["freshness_state"], "missing")
        self.assertIsNone(probe["last_modified_utc"])
        self.assertIsNone(probe["size_bytes"])

    def test_recent_source_marks_fresh(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            spec = {"path_canonical_rel": "README.md"}
            probe = (
                agent_loop._desktop_rag_source_selection_probe_freshness(
                    controller, spec,
                )
            )
        self.assertTrue(probe["exists"])
        self.assertEqual(probe["freshness_state"], "fresh")
        self.assertIsNotNone(probe["last_modified_utc"])
        self.assertIsNotNone(probe["size_bytes"])

    def test_old_source_marks_stale(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            target = controller / "README.md"
            # Force a fake mtime older than the threshold.
            ancient_ts = (
                time.time()
                - agent_loop.RAG_SOURCE_FRESHNESS_STALE_THRESHOLD_SECONDS
                - 3600
            )
            os.utime(target, (ancient_ts, ancient_ts))
            spec = {"path_canonical_rel": "README.md"}
            probe = (
                agent_loop._desktop_rag_source_selection_probe_freshness(
                    controller, spec,
                )
            )
        self.assertTrue(probe["exists"])
        self.assertEqual(probe["freshness_state"], "stale")

    def test_future_mtime_marks_unknown(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            target = controller / "README.md"
            # Future mtime (clock skew). `now_ts - mtime_ts` < 0.
            future_ts = time.time() + 3600
            os.utime(target, (future_ts, future_ts))
            spec = {"path_canonical_rel": "README.md"}
            probe = (
                agent_loop._desktop_rag_source_selection_probe_freshness(
                    controller, spec,
                )
            )
        self.assertTrue(probe["exists"])
        self.assertEqual(probe["freshness_state"], "unknown")


# ---------------------------------------------------------------------------
# Approval-state computation
# ---------------------------------------------------------------------------
class ApprovalStateTests(unittest.TestCase):

    def _spec(self) -> dict:
        return dict(
            agent_loop._DESKTOP_RAG_SOURCE_SELECTION_REGISTRY[0]
        )

    def test_all_unsatisfied_default(self) -> None:
        state = (
            agent_loop._desktop_rag_source_selection_compute_approval_state(
                self._spec(),
                approval_mode=None,
                phase_10v_runtime_available=False,
                operator_acknowledged_advisory_labeling=False,
                operator_supplied_identity=False,
                source_path_present_in_repo=False,
            )
        )
        for req in agent_loop.RAG_SOURCE_APPROVAL_REQUIREMENTS:
            self.assertFalse(state[req]["satisfied"], req)

    def test_strict_mode_refuses_selection(self) -> None:
        state = (
            agent_loop._desktop_rag_source_selection_compute_approval_state(
                self._spec(),
                approval_mode="strict",
                phase_10v_runtime_available=True,
                operator_acknowledged_advisory_labeling=True,
                operator_supplied_identity=True,
                source_path_present_in_repo=True,
            )
        )
        self.assertFalse(
            state["approval_mode_supports_selection"][
                "satisfied"
            ],
        )

    def test_review_mode_supports_selection(self) -> None:
        state = (
            agent_loop._desktop_rag_source_selection_compute_approval_state(
                self._spec(),
                approval_mode="review",
                phase_10v_runtime_available=False,
                operator_acknowledged_advisory_labeling=False,
                operator_supplied_identity=False,
                source_path_present_in_repo=False,
            )
        )
        self.assertTrue(
            state["approval_mode_supports_selection"][
                "satisfied"
            ],
        )

    def test_autonomous_mode_supports_selection(self) -> None:
        state = (
            agent_loop._desktop_rag_source_selection_compute_approval_state(
                self._spec(),
                approval_mode="autonomous",
                phase_10v_runtime_available=False,
                operator_acknowledged_advisory_labeling=False,
                operator_supplied_identity=False,
                source_path_present_in_repo=False,
            )
        )
        self.assertTrue(
            state["approval_mode_supports_selection"][
                "satisfied"
            ],
        )


# ---------------------------------------------------------------------------
# Enablement-state machine
# ---------------------------------------------------------------------------
class EnablementStateMachineTests(unittest.TestCase):

    def _spec(self) -> dict:
        return dict(
            agent_loop._DESKTOP_RAG_SOURCE_SELECTION_REGISTRY[0]
        )

    def test_refused_when_runtime_not_available(self) -> None:
        spec = self._spec()
        state = {
            req: {"satisfied": True}
            for req in spec["approval_requirements"]
        }
        state["phase_10v_runtime_available"] = {
            "satisfied": False,
        }
        value, reason = (
            agent_loop._desktop_rag_source_selection_compute_enablement_state(
                spec, approval_state=state,
            )
        )
        self.assertEqual(value, "refused_until_policy_update")
        self.assertIn(
            "phase_10v_runtime_available", reason,
        )

    def test_refused_when_source_path_missing(self) -> None:
        spec = self._spec()
        state = {
            req: {"satisfied": True}
            for req in spec["approval_requirements"]
        }
        state["source_path_present_in_repo"] = {
            "satisfied": False,
        }
        value, reason = (
            agent_loop._desktop_rag_source_selection_compute_enablement_state(
                spec, approval_state=state,
            )
        )
        self.assertEqual(value, "refused_until_policy_update")
        self.assertIn(
            "source_path_present_in_repo", reason,
        )

    def test_refused_when_advisory_label_rule_refused(
        self,
    ) -> None:
        spec = self._spec()
        spec["advisory_label_rule"] = (
            "refused_until_policy_update"
        )
        # Even if every other requirement is satisfied, the
        # labeling-rule short-circuit refuses fail-closed.
        state = {
            req: {"satisfied": True}
            for req in spec["approval_requirements"]
        }
        value, reason = (
            agent_loop._desktop_rag_source_selection_compute_enablement_state(
                spec, approval_state=state,
            )
        )
        self.assertEqual(value, "refused_until_policy_update")
        self.assertIn(
            "labeling-rule", reason,
        )

    def test_disabled_when_operator_side_unsatisfied(self) -> None:
        spec = self._spec()
        state = {
            req: {"satisfied": True}
            for req in spec["approval_requirements"]
        }
        state["operator_acknowledged_advisory_labeling"] = {
            "satisfied": False,
        }
        value, reason = (
            agent_loop._desktop_rag_source_selection_compute_enablement_state(
                spec, approval_state=state,
            )
        )
        self.assertEqual(value, "disabled_by_default")
        self.assertIn(
            "operator_acknowledged_advisory_labeling", reason,
        )

    def test_enabled_when_every_requirement_satisfied(
        self,
    ) -> None:
        spec = self._spec()
        state = {
            req: {"satisfied": True}
            for req in spec["approval_requirements"]
        }
        value, reason = (
            agent_loop._desktop_rag_source_selection_compute_enablement_state(
                spec, approval_state=state,
            )
        )
        self.assertEqual(value, "enabled_pending_runtime")
        self.assertIn("future Phase 10 runtime slice", reason)


# ---------------------------------------------------------------------------
# Operator-input normalizer
# ---------------------------------------------------------------------------
class OperatorInputsNormalizerTests(unittest.TestCase):

    def test_none_returns_empty_defaults(self) -> None:
        result = (
            agent_loop._desktop_rag_source_selection_normalize_operator_inputs(
                None,
            )
        )
        self.assertEqual(result["identity"], "")
        self.assertEqual(
            result["acknowledged_source_ids"], frozenset(),
        )

    def test_strips_identity_whitespace(self) -> None:
        result = (
            agent_loop._desktop_rag_source_selection_normalize_operator_inputs(
                {"identity": "  me  "},
            )
        )
        self.assertEqual(result["identity"], "me")

    def test_coerces_list_to_frozenset(self) -> None:
        result = (
            agent_loop._desktop_rag_source_selection_normalize_operator_inputs(
                {
                    "acknowledged_source_ids": [
                        "repo_local_docs_readme",
                    ],
                },
            )
        )
        self.assertIsInstance(
            result["acknowledged_source_ids"], frozenset,
        )

    def test_refuses_non_dict(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_rag_source_selection_normalize_operator_inputs(
                ["nope"],
            )

    def test_refuses_non_string_identity(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_rag_source_selection_normalize_operator_inputs(
                {"identity": 42},
            )

    def test_refuses_non_iterable_ack_set(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_rag_source_selection_normalize_operator_inputs(
                {"acknowledged_source_ids": 42},
            )


# ---------------------------------------------------------------------------
# build_desktop_rag_source_selection_view
# ---------------------------------------------------------------------------
class BuildViewTests(unittest.TestCase):

    def test_view_shape_fields(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_rag_source_selection_view(
                    controller,
                )
            )
        for key in (
            "view_signal_version",
            "controller_path_canonical",
            "current_loop_state_status",
            "controller_loop_state_approval_mode",
            "phase_10v_runtime_available",
            "freshness_stale_threshold_seconds",
            "operator_inputs",
            "source_types",
            "provenance_categories",
            "advisory_labeling_rules",
            "freshness_states",
            "enablement_states",
            "approval_requirements",
            "sources",
            "precedence_note",
        ):
            self.assertIn(key, view, key)
        self.assertEqual(
            view["view_signal_version"], "phase-10v-v1",
        )
        self.assertFalse(view["phase_10v_runtime_available"])

    def test_view_reflects_loop_state_status_and_mode(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(
                Path(td) / "c",
                status="awaiting_codex_review",
                approval_mode="autonomous",
            )
            view = (
                agent_loop.build_desktop_rag_source_selection_view(
                    controller,
                )
            )
        self.assertEqual(
            view["current_loop_state_status"],
            "awaiting_codex_review",
        )
        self.assertEqual(
            view["controller_loop_state_approval_mode"],
            "autonomous",
        )

    def test_view_soft_fails_on_missing_loop_state(self) -> None:
        with TemporaryDirectory() as td:
            controller = Path(td) / "c"
            controller.mkdir()
            (controller / "AGENTS.md").write_text(
                "x", encoding="utf-8",
            )
            (controller / "CLAUDE.md").write_text(
                "x", encoding="utf-8",
            )
            (controller / "TASK.md").write_text(
                "x", encoding="utf-8",
            )
            (controller / "README.md").write_text(
                "x", encoding="utf-8",
            )
            (controller / ".agent-loop").mkdir()
            view = (
                agent_loop.build_desktop_rag_source_selection_view(
                    controller,
                )
            )
        self.assertIsNone(view["current_loop_state_status"])
        self.assertIsNone(
            view["controller_loop_state_approval_mode"],
        )

    def test_every_source_refused_by_default(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_rag_source_selection_view(
                    controller,
                )
            )
        for source in view["sources"]:
            self.assertEqual(
                source["enablement_state"],
                "refused_until_policy_update",
                source["id"],
            )

    def test_fail_closed_default_survives_full_operator_inputs(
        self,
    ) -> None:
        # The headline Phase 10V guardrail: even with every
        # operator-side requirement satisfied the contract-only
        # slice keeps every source `refused_until_policy_update`
        # because `phase_10v_runtime_available` is hard-coded
        # False. A future runtime slice flipping the flag must
        # be what unlocks selection; the operator inputs alone
        # MUST NOT bypass the boundary.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_rag_source_selection_view(
                    controller,
                    operator_inputs=_full_inputs(),
                )
            )
        for source in view["sources"]:
            self.assertEqual(
                source["enablement_state"],
                "refused_until_policy_update",
                source["id"],
            )

    def test_operator_inputs_mirror_in_view(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_rag_source_selection_view(
                    controller,
                    operator_inputs={
                        "identity": "me",
                        "acknowledged_source_ids": [
                            "repo_local_docs_readme",
                        ],
                    },
                )
            )
        op = view["operator_inputs"]
        self.assertEqual(op["identity"], "me")
        self.assertEqual(
            op["acknowledged_source_ids"],
            ["repo_local_docs_readme"],
        )

    def test_per_poll_freshness_re_derived(self) -> None:
        # Each view-builder call MUST re-derive freshness from
        # disk; nothing is cached across calls.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            v1 = (
                agent_loop.build_desktop_rag_source_selection_view(
                    controller,
                )
            )
            readme = controller / "README.md"
            ancient_ts = (
                time.time()
                - agent_loop.RAG_SOURCE_FRESHNESS_STALE_THRESHOLD_SECONDS
                - 3600
            )
            os.utime(readme, (ancient_ts, ancient_ts))
            v2 = (
                agent_loop.build_desktop_rag_source_selection_view(
                    controller,
                )
            )
        readme_source_v1 = next(
            s for s in v1["sources"]
            if s["id"] == "repo_local_docs_readme"
        )
        readme_source_v2 = next(
            s for s in v2["sources"]
            if s["id"] == "repo_local_docs_readme"
        )
        self.assertEqual(
            readme_source_v1["freshness_state"], "fresh",
        )
        self.assertEqual(
            readme_source_v2["freshness_state"], "stale",
        )

    def test_missing_source_path_marks_runtime_side_refused(
        self,
    ) -> None:
        # Delete a registry source path on disk; the resulting
        # view MUST keep the source `refused_until_policy_update`
        # via the runtime-side `source_path_present_in_repo`
        # requirement.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            (controller / "README.md").unlink()
            view = (
                agent_loop.build_desktop_rag_source_selection_view(
                    controller,
                    operator_inputs=_full_inputs(),
                )
            )
        readme = next(
            s for s in view["sources"]
            if s["id"] == "repo_local_docs_readme"
        )
        self.assertEqual(
            readme["enablement_state"],
            "refused_until_policy_update",
        )
        self.assertEqual(
            readme["freshness_state"], "missing",
        )
        self.assertFalse(
            readme["source_path_present_in_repo"],
        )


# ---------------------------------------------------------------------------
# render_desktop_rag_source_selection_text
# ---------------------------------------------------------------------------
class RenderTextTests(unittest.TestCase):

    def _view(self) -> dict:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            return (
                agent_loop.build_desktop_rag_source_selection_view(
                    controller,
                )
            )

    def test_renders_signal_version_header(self) -> None:
        lines = (
            agent_loop.render_desktop_rag_source_selection_text(
                self._view(),
            )
        )
        self.assertTrue(
            any("phase-10v-v1" in line for line in lines),
        )

    def test_renders_every_source_with_attribution_tags(
        self,
    ) -> None:
        view = self._view()
        lines = (
            agent_loop.render_desktop_rag_source_selection_text(
                view,
            )
        )
        output = "\n".join(lines)
        for tag in (
            "[refused]",
            "[rag-provenance]",
            "[rag-advisory]",
            "[rag-freshness]",
            "[rag-approval]",
            "[rag-enablement]",
            "[deferred-runtime]",
            "[canonical mirror]",
            "[advisory]",
        ):
            self.assertIn(tag, output, tag)
        for source in view["sources"]:
            self.assertIn(source["id"], output)

    def test_renders_operator_inputs_mirror_lines(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_rag_source_selection_view(
                    controller,
                    operator_inputs={
                        "identity": "me",
                        "acknowledged_source_ids": [
                            "repo_local_docs_readme",
                        ],
                    },
                )
            )
        output = "\n".join(
            agent_loop.render_desktop_rag_source_selection_text(
                view,
            )
        )
        self.assertIn(
            "operator_inputs.identity", output,
        )
        self.assertIn(
            "operator_inputs.acknowledged_source_ids", output,
        )


# ---------------------------------------------------------------------------
# build_desktop_rag_source_selection_controls
# ---------------------------------------------------------------------------
class BuildControlsTests(unittest.TestCase):

    def test_controls_one_per_source(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_rag_source_selection_view(
                    controller,
                )
            )
        controls = (
            agent_loop.build_desktop_rag_source_selection_controls(
                view,
            )
        )
        self.assertEqual(len(controls), len(view["sources"]))
        for control in controls:
            self.assertIn("id", control)
            self.assertIn("label", control)
            self.assertIn("enabled", control)
            self.assertEqual(
                control["dispatch_mode"], "copy_paste",
            )
            self.assertEqual(
                control["category"], "rag_source_selection_ux",
            )

    def test_every_control_disabled_in_this_slice(self) -> None:
        # Phase 10V ships the contract only; every control MUST
        # render as disabled regardless of operator input.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_rag_source_selection_view(
                    controller,
                    operator_inputs=_full_inputs(),
                )
            )
        controls = (
            agent_loop.build_desktop_rag_source_selection_controls(
                view,
            )
        )
        for control in controls:
            self.assertFalse(control["enabled"], control["id"])


# ---------------------------------------------------------------------------
# CLI handler
# ---------------------------------------------------------------------------
class CmdHandlerTests(unittest.TestCase):

    def _make_args(self, **kwargs) -> argparse.Namespace:
        defaults = {
            "controller_root": None,
            "operator_identity": None,
            "acknowledge_source": None,
        }
        defaults.update(kwargs)
        return argparse.Namespace(**defaults)

    def test_refuses_missing_controller_root(self) -> None:
        args = self._make_args(controller_root=None)
        buf_out = io.StringIO()
        buf_err = io.StringIO()
        with redirect_stdout(buf_out), redirect_stderr(buf_err):
            rc = (
                agent_loop.cmd_view_desktop_rag_source_selection(
                    args,
                )
            )
        self.assertEqual(rc, 2)
        self.assertIn("REFUSED", buf_err.getvalue())

    def test_refuses_missing_markers(self) -> None:
        with TemporaryDirectory() as td:
            controller = Path(td) / "no_markers"
            controller.mkdir()
            args = self._make_args(controller_root=str(controller))
            buf_out = io.StringIO()
            buf_err = io.StringIO()
            with redirect_stdout(buf_out), redirect_stderr(
                buf_err,
            ):
                rc = (
                    agent_loop.cmd_view_desktop_rag_source_selection(
                        args,
                    )
                )
        self.assertEqual(rc, 2)
        self.assertIn(
            "missing required markers", buf_err.getvalue(),
        )

    def test_phase_7c_reporter_pattern_exits_zero(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            args = self._make_args(controller_root=str(controller))
            buf_out = io.StringIO()
            with redirect_stdout(buf_out):
                rc = (
                    agent_loop.cmd_view_desktop_rag_source_selection(
                        args,
                    )
                )
        self.assertEqual(rc, 0)
        self.assertIn(
            "[desktop-rag-source-selection]", buf_out.getvalue(),
        )

    def test_operator_input_flags_thread_through(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            args = self._make_args(
                controller_root=str(controller),
                operator_identity="me",
                acknowledge_source=["repo_local_docs_readme"],
            )
            buf_out = io.StringIO()
            with redirect_stdout(buf_out):
                rc = (
                    agent_loop.cmd_view_desktop_rag_source_selection(
                        args,
                    )
                )
        self.assertEqual(rc, 0)
        output = buf_out.getvalue()
        self.assertIn("'me'", output)
        self.assertIn(
            "['repo_local_docs_readme']", output,
        )
        # Even with the operator inputs supplied, the source
        # stays refused (Phase 10V fail-closed default).
        self.assertIn(
            "refused_until_policy_update", output,
        )

    def test_handler_registered(self) -> None:
        self.assertIn(
            "view-desktop-rag-source-selection",
            agent_loop.HANDLERS,
        )
        self.assertIs(
            agent_loop.HANDLERS[
                "view-desktop-rag-source-selection"
            ],
            agent_loop.cmd_view_desktop_rag_source_selection,
        )

    def test_parser_accepts_subcommand(self) -> None:
        parser = agent_loop.build_parser()
        args = parser.parse_args([
            "view-desktop-rag-source-selection",
            "--controller-root", ".",
            "--operator-identity", "me",
            "--acknowledge-source", "repo_local_docs_readme",
        ])
        self.assertEqual(
            args.cmd, "view-desktop-rag-source-selection",
        )
        self.assertEqual(args.operator_identity, "me")
        self.assertEqual(
            args.acknowledge_source,
            ["repo_local_docs_readme"],
        )


# ---------------------------------------------------------------------------
# Integration: assemble_desktop_app_view + render_desktop_app_text
# ---------------------------------------------------------------------------
class DesktopAppIntegrationTests(unittest.TestCase):

    def test_assemble_includes_rag_source_selection_view_key(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.assemble_desktop_app_view(controller)
        self.assertIn("rag_source_selection_view", view)
        sub = view["rag_source_selection_view"]
        self.assertIsInstance(sub, dict)
        self.assertEqual(
            sub["view_signal_version"], "phase-10v-v1",
        )

    def test_assemble_delegates_to_build_view(self) -> None:
        sentinel = {
            "view_signal_version": "phase-10v-v1",
            "controller_path_canonical": "/tmp/sentinel",
            "current_loop_state_status": None,
            "controller_loop_state_approval_mode": None,
            "phase_10v_runtime_available": False,
            "freshness_stale_threshold_seconds": 100,
            "operator_inputs": {
                "identity": "",
                "acknowledged_source_ids": [],
            },
            "source_types": [],
            "provenance_categories": [],
            "advisory_labeling_rules": [],
            "freshness_states": [],
            "enablement_states": [],
            "approval_requirements": [],
            "sources": [],
            "precedence_note": "sentinel-precedence",
        }
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            with mock.patch.object(
                agent_loop,
                "build_desktop_rag_source_selection_view",
                return_value=sentinel,
            ) as mocked:
                view = agent_loop.assemble_desktop_app_view(
                    controller,
                )
        mocked.assert_called_once_with(controller)
        self.assertIs(
            view["rag_source_selection_view"], sentinel,
        )

    def test_render_includes_phase_10v_label(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.assemble_desktop_app_view(controller)
            lines = agent_loop.render_desktop_app_text(view)
        output = "\n".join(lines)
        self.assertIn(
            "=== RAG Source Selection (Phase 10V) ===", output,
        )
        self.assertIn("phase-10v-v1", output)


# ---------------------------------------------------------------------------
# Non-mutation invariants
# ---------------------------------------------------------------------------
class NonMutationInvariantsTests(unittest.TestCase):

    def test_render_does_not_open_socket(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            args = argparse.Namespace(
                controller_root=str(controller),
                operator_identity=None,
                acknowledge_source=None,
            )
            with mock.patch.object(
                socket, "socket",
            ) as patched_socket:
                buf_out = io.StringIO()
                with redirect_stdout(buf_out):
                    rc = (
                        agent_loop.cmd_view_desktop_rag_source_selection(
                            args,
                        )
                    )
        self.assertEqual(rc, 0)
        patched_socket.assert_not_called()

    def test_render_does_not_spawn_subprocess(self) -> None:
        import subprocess
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            args = argparse.Namespace(
                controller_root=str(controller),
                operator_identity=None,
                acknowledge_source=None,
            )
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
                buf_out = io.StringIO()
                with redirect_stdout(buf_out):
                    rc = (
                        agent_loop.cmd_view_desktop_rag_source_selection(
                            args,
                        )
                    )
            finally:
                for p in patches:
                    p.stop()
        self.assertEqual(rc, 0)
        for m in mocks:
            m.assert_not_called()

    def test_render_does_not_invoke_halt(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            with mock.patch.object(agent_loop, "_halt") as halt:
                view = (
                    agent_loop.build_desktop_rag_source_selection_view(
                        controller,
                    )
                )
        self.assertEqual(
            view["view_signal_version"], "phase-10v-v1",
        )
        halt.assert_not_called()

    def test_render_does_not_mutate_loop_state(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            ls_path = (
                controller / ".agent-loop" / "loop-state.json"
            )
            before = ls_path.read_bytes()
            agent_loop.build_desktop_rag_source_selection_view(
                controller,
            )
            after = ls_path.read_bytes()
        self.assertEqual(before, after)

    def test_render_does_not_append_to_orchestrator_log(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            log_path = (
                controller / ".agent-loop" / "orchestrator.log"
            )
            agent_loop.build_desktop_rag_source_selection_view(
                controller,
            )
        self.assertFalse(log_path.exists())

    def test_render_does_not_read_source_content(self) -> None:
        # The Phase 10V view-builder MUST NOT read source
        # CONTENT, only `Path.stat()`. Behavioral check: write
        # a unique sentinel string into every registered
        # source path on disk, build the view, render it, and
        # assert that the sentinel does NOT appear anywhere in
        # the rendered output. If the view-builder were
        # secretly reading source content the sentinel would
        # leak into either the view dict or the rendered text.
        sentinel = (
            "PHASE10V_SENTINEL_SOURCE_CONTENT_MUST_NOT_LEAK"
        )
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            for spec in (
                agent_loop._DESKTOP_RAG_SOURCE_SELECTION_REGISTRY
            ):
                p = controller / spec["path_canonical_rel"]
                if p.exists():
                    p.write_text(sentinel, encoding="utf-8")
            view = (
                agent_loop.build_desktop_rag_source_selection_view(
                    controller,
                    operator_inputs=_full_inputs(),
                )
            )
            rendered = "\n".join(
                agent_loop.render_desktop_rag_source_selection_text(
                    view,
                )
            )
        view_repr = repr(view)
        self.assertNotIn(sentinel, view_repr)
        self.assertNotIn(sentinel, rendered)

    def test_does_not_widen_phase_10i_library_callable_cap(
        self,
    ) -> None:
        library_call_ids = {
            spec["id"]
            for spec in agent_loop._EXTERNAL_UI_CONTROL_REGISTRY
            if spec["dispatch_mode"] == "library_call"
        }
        self.assertEqual(
            library_call_ids,
            {
                "view-external-status",
                "view-external-controls",
                "inspect-external-target",
            },
            "Phase 10V MUST NOT widen the Phase 10I library-"
            "callable control surface beyond the three shipped "
            "controls",
        )


if __name__ == "__main__":
    unittest.main()
