"""Phase 10AD - Codex-Owned Concurrent Work Initial Slice tests.

Exercises:
  - module-level constants (signal version, precedence note, halt-
    status, closed enumerations, closed registry)
  - operator-input normalizer
  - closed action registry + descriptor validator (re-uses the
    Phase 10AB `CONCURRENCY_OWNERSHIP_ROLES` closed vocabulary
    verbatim)
  - pure eligibility evaluator (Phase 10AC-refused / owner-role /
    would-invalidate / unknown / eligible branches)
  - `build_desktop_codex_concurrent_work_view(...)` shape + soft-
    fail on missing loop-state + reuse of the shipped Phase 10AC
    aggregate
  - renderer per-line attribution
  - `build_desktop_codex_concurrent_work_controls(...)` widget
    shape (COPY-PASTE only; every button clickable per the Phase
    10Z / 10AA / 10AB / 10AC fix-cycle affordance pattern)
  - `cmd_view_desktop_codex_concurrent_work(...)` CLI + Phase 7C
  - integration into `assemble_desktop_app_view(...)` +
    `render_desktop_app_text(...)`
  - shipped runtime eligibility helper
    (`evaluate_codex_concurrent_work_eligibility(...)`) refusal +
    success branches
  - non-mutation invariants (no socket, no subprocess, no
    orchestrator.log append, no loop-state mutation, no
    `_halt(...)`, no Phase 10I library-callable cap widening, no
    persisted concurrent-work cache, no actual concurrent Codex/
    Claude worker launched)
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
    (td / "TASK.md").write_text("# TASK.md\n", encoding="utf-8")
    (td / "README.md").write_text("readme\n", encoding="utf-8")
    (td / ".agent-loop").mkdir()
    (td / ".agent-loop" / "loop-state.json").write_text(
        json.dumps({
            "phase": "Phase 10 - Future Product Features",
            "sub_phase": (
                "Phase 10AD - Codex-Owned Concurrent Work "
                "Initial Slice"
            ),
            "task": "phase-10ad-test",
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


def _write_bytes(path: Path, body: bytes, mtime: float) -> None:
    """Write bytes and force the on-disk mtime to a deterministic
    value so the aggregate-state assertions are stable across the
    shipped test suite (Windows universal-newline translation is
    also bypassed by writing bytes directly).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    os.utime(path, (mtime, mtime))


def _mock_overlap_aggregate(state):
    """Return a mock `build_desktop_overlap_detection_view(...)`
    return value with the given aggregate `overall_signal_state`.
    """
    return {
        "overall": {
            "overall_signal_state": state,
            "overall_severity": {
                "refused_pending_recovery": "refusal",
                "signal_detected": "warning",
                "unknown": "unknown",
                "no_signal": "info",
            }[state],
            "refusal_signal_ids": [],
            "warning_signal_ids": [],
            "unknown_signal_ids": [],
            "reason": "synthetic",
            "triggered_count": 0,
        },
        "signals": [],
    }


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
class ConstantsTests(unittest.TestCase):

    def test_signal_version(self) -> None:
        self.assertEqual(
            agent_loop.DESKTOP_CODEX_CONCURRENT_WORK_SIGNAL_VERSION,
            "phase-10ad-v1",
        )

    def test_halt_status(self) -> None:
        self.assertEqual(
            agent_loop.HALTED_CODEX_CONCURRENT_WORK_UNSAFE,
            "halted_codex_concurrent_work_unsafe",
        )

    def test_action_types_closed_enum(self) -> None:
        self.assertEqual(
            agent_loop.CODEX_CONCURRENT_ACTION_TYPES,
            (
                "prd_intake_read",
                "plan_proposal_write",
                "artifact_dashboard_read",
                "memory_vault_read",
                "active_context_write",
            ),
        )

    def test_effect_classes_closed_enum(self) -> None:
        self.assertEqual(
            agent_loop.CODEX_CONCURRENT_EFFECT_CLASSES,
            (
                "read_only_advisory",
                "codex_owned_write",
                "codex_owned_write_invalidates_claude",
            ),
        )

    def test_eligibility_states_closed_enum(self) -> None:
        self.assertEqual(
            agent_loop.CODEX_CONCURRENT_ELIGIBILITY_STATES,
            (
                "eligible_bounded_execution",
                "refused_overlap_unsafe",
                "refused_owner_role_violation",
                "refused_would_invalidate_claude_context",
                "refused_until_policy_update",
            ),
        )

    def test_precedence_note_pins_contract(self) -> None:
        note = (
            agent_loop.DESKTOP_CODEX_CONCURRENT_WORK_PRECEDENCE_NOTE
        )
        for needle in (
            "Phase 10AD",
            "Phase 10AB",
            "Phase 10AC",
            "_DESKTOP_CONCURRENCY_OWNERSHIP_MAP",
            "phase_10ad_runtime_available",
            "evaluate_codex_concurrent_work_eligibility",
            "HALTED_CODEX_CONCURRENT_WORK_UNSAFE",
            "hard-coded `True`",
            "Phase 10I three-control library-callable cap is "
            "preserved exactly",
            "NEVER launches",
            "NEVER opens a network socket",
        ):
            self.assertIn(needle, note, needle)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
class RegistryTests(unittest.TestCase):

    def test_registry_ships_five_actions(self) -> None:
        self.assertEqual(
            len(
                agent_loop._DESKTOP_CODEX_CONCURRENT_WORK_REGISTRY
            ),
            5,
        )

    def test_every_registry_entry_passes_validator(self) -> None:
        for spec in (
            agent_loop._DESKTOP_CODEX_CONCURRENT_WORK_REGISTRY
        ):
            agent_loop._desktop_codex_concurrent_work_validate_descriptor(
                spec,
            )

    def test_registry_covers_every_action_type(self) -> None:
        # Registry MUST cover every closed action_type at least
        # once so the surface exercises every branch of the
        # eligibility evaluator through real registry entries.
        seen = {
            spec["action_type"]
            for spec in (
                agent_loop._DESKTOP_CODEX_CONCURRENT_WORK_REGISTRY
            )
        }
        self.assertEqual(
            seen, set(agent_loop.CODEX_CONCURRENT_ACTION_TYPES),
        )

    def test_every_registry_target_in_phase_10ab_ownership_map(
        self,
    ) -> None:
        lookup = (
            agent_loop._desktop_codex_concurrent_work_ownership_lookup()
        )
        for spec in (
            agent_loop._DESKTOP_CODEX_CONCURRENT_WORK_REGISTRY
        ):
            target = spec["target_artifact_canonical_rel"]
            self.assertIn(
                target, lookup,
                (
                    f"Phase 10AD entry {spec['id']!r} targets "
                    f"{target!r} which is not in the shipped "
                    f"Phase 10AB _DESKTOP_CONCURRENCY_OWNERSHIP_MAP"
                ),
            )

    def test_registry_owner_roles_are_phase_10ab_members(
        self,
    ) -> None:
        for spec in (
            agent_loop._DESKTOP_CODEX_CONCURRENT_WORK_REGISTRY
        ):
            self.assertIn(
                spec["expected_target_owner_role"],
                agent_loop.CONCURRENCY_OWNERSHIP_ROLES,
                spec["id"],
            )

    def test_at_least_one_would_invalidate_entry(self) -> None:
        # The registry MUST anchor the
        # `refused_would_invalidate_claude_context` branch by
        # shipping at least one action with
        # `would_invalidate_claude_context=True`.
        invalidating = [
            spec
            for spec in (
                agent_loop._DESKTOP_CODEX_CONCURRENT_WORK_REGISTRY
            )
            if spec["would_invalidate_claude_context"]
        ]
        self.assertTrue(invalidating)


# ---------------------------------------------------------------------------
# Descriptor validator
# ---------------------------------------------------------------------------
class ValidatorTests(unittest.TestCase):

    def _valid(self):
        return {
            "id": "x",
            "display_name": "X",
            "action_type": "prd_intake_read",
            "effect_class": "read_only_advisory",
            "target_artifact_canonical_rel": "TASK.md",
            "expected_target_owner_role": "codex_owned",
            "would_invalidate_claude_context": False,
            "description": "d",
            "safety_copy": "s",
            "deferred_runtime_marker": "m",
            "refusal_reason_template": "t",
        }

    def test_valid_passes(self) -> None:
        agent_loop._desktop_codex_concurrent_work_validate_descriptor(
            self._valid(),
        )

    def test_non_dict_refuses(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_codex_concurrent_work_validate_descriptor(
                ["not", "a", "dict"],
            )

    def test_missing_string_field_refuses(self) -> None:
        spec = self._valid()
        del spec["action_type"]
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_codex_concurrent_work_validate_descriptor(
                spec,
            )

    def test_empty_string_field_refuses(self) -> None:
        spec = self._valid()
        spec["display_name"] = ""
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_codex_concurrent_work_validate_descriptor(
                spec,
            )

    def test_missing_would_invalidate_refuses(self) -> None:
        spec = self._valid()
        del spec["would_invalidate_claude_context"]
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_codex_concurrent_work_validate_descriptor(
                spec,
            )

    def test_non_bool_would_invalidate_refuses(self) -> None:
        spec = self._valid()
        spec["would_invalidate_claude_context"] = "yes"
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_codex_concurrent_work_validate_descriptor(
                spec,
            )

    def test_unknown_action_type_refuses(self) -> None:
        spec = self._valid()
        spec["action_type"] = "not_a_real_action_type"
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_codex_concurrent_work_validate_descriptor(
                spec,
            )

    def test_unknown_effect_class_refuses(self) -> None:
        spec = self._valid()
        spec["effect_class"] = "not_a_real_effect_class"
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_codex_concurrent_work_validate_descriptor(
                spec,
            )

    def test_unknown_owner_role_refuses(self) -> None:
        spec = self._valid()
        spec["expected_target_owner_role"] = "not_a_real_role"
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_codex_concurrent_work_validate_descriptor(
                spec,
            )

    def test_backslash_target_path_refuses(self) -> None:
        spec = self._valid()
        spec["target_artifact_canonical_rel"] = (
            ".agent-loop\\bad.md"
        )
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_codex_concurrent_work_validate_descriptor(
                spec,
            )

    def test_absolute_target_path_refuses(self) -> None:
        spec = self._valid()
        spec["target_artifact_canonical_rel"] = "/bad/path.md"
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_codex_concurrent_work_validate_descriptor(
                spec,
            )

    def test_drive_prefix_target_path_refuses(self) -> None:
        spec = self._valid()
        spec["target_artifact_canonical_rel"] = "C:/bad/path.md"
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_codex_concurrent_work_validate_descriptor(
                spec,
            )

    def test_parent_traversal_target_path_refuses(self) -> None:
        spec = self._valid()
        spec["target_artifact_canonical_rel"] = (
            "../evil/path.md"
        )
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_codex_concurrent_work_validate_descriptor(
                spec,
            )


# ---------------------------------------------------------------------------
# Operator-input normalizer
# ---------------------------------------------------------------------------
class OperatorInputsNormalizerTests(unittest.TestCase):

    def test_none_returns_empty(self) -> None:
        got = (
            agent_loop._desktop_codex_concurrent_work_normalize_operator_inputs(
                None,
            )
        )
        self.assertEqual(got["identity"], "")
        self.assertEqual(got["acknowledged_action_ids"], frozenset())

    def test_non_dict_refuses(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_codex_concurrent_work_normalize_operator_inputs(
                ["not", "a", "dict"],
            )

    def test_non_str_identity_refuses(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_codex_concurrent_work_normalize_operator_inputs(
                {"identity": 42},
            )

    def test_non_iterable_acknowledged_refuses(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_codex_concurrent_work_normalize_operator_inputs(
                {"acknowledged_action_ids": 42},
            )

    def test_non_str_acknowledged_member_refuses(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_codex_concurrent_work_normalize_operator_inputs(
                {"acknowledged_action_ids": ["ok", 42]},
            )

    def test_valid_normalized(self) -> None:
        got = (
            agent_loop._desktop_codex_concurrent_work_normalize_operator_inputs(
                {
                    "identity": "alice",
                    "acknowledged_action_ids": ("a", "b"),
                },
            )
        )
        self.assertEqual(got["identity"], "alice")
        self.assertEqual(
            got["acknowledged_action_ids"], frozenset({"a", "b"}),
        )


# ---------------------------------------------------------------------------
# Eligibility evaluator
# ---------------------------------------------------------------------------
class EligibilityEvaluatorTests(unittest.TestCase):

    def _lookup(self):
        return (
            agent_loop._desktop_codex_concurrent_work_ownership_lookup()
        )

    def _spec(self, **overrides):
        base = {
            "id": "x",
            "display_name": "X",
            "action_type": "prd_intake_read",
            "effect_class": "read_only_advisory",
            "target_artifact_canonical_rel": "TASK.md",
            "expected_target_owner_role": "codex_owned",
            "would_invalidate_claude_context": False,
            "description": "d",
            "safety_copy": "s",
            "deferred_runtime_marker": "m",
            "refusal_reason_template": "t",
        }
        base.update(overrides)
        return base

    def test_refused_overlap_short_circuits(self) -> None:
        got = (
            agent_loop._desktop_codex_concurrent_work_evaluate_eligibility(
                self._spec(),
                self._lookup(),
                "refused_pending_recovery",
            )
        )
        self.assertEqual(
            got["eligibility_state"], "refused_overlap_unsafe",
        )
        self.assertIn(
            "refused_pending_recovery",
            got["eligibility_reason"],
        )

    def test_unknown_overlap_refuses_when_otherwise_eligible(
        self,
    ) -> None:
        got = (
            agent_loop._desktop_codex_concurrent_work_evaluate_eligibility(
                self._spec(),
                self._lookup(),
                "unknown",
            )
        )
        self.assertEqual(
            got["eligibility_state"], "refused_overlap_unsafe",
        )
        self.assertIn(
            "unknown", got["eligibility_reason"],
        )

    def test_target_not_in_ownership_map_refuses(self) -> None:
        got = (
            agent_loop._desktop_codex_concurrent_work_evaluate_eligibility(
                self._spec(
                    target_artifact_canonical_rel=(
                        ".agent-loop/not-in-map.md"
                    ),
                ),
                self._lookup(),
                "no_signal",
            )
        )
        self.assertEqual(
            got["eligibility_state"],
            "refused_owner_role_violation",
        )
        self.assertIsNone(
            got["actual_target_owner_role"],
        )

    def test_owner_role_mismatch_refuses(self) -> None:
        # TASK.md is `codex_owned` in the Phase 10AB map;
        # advertise it as `claude_owned` and the evaluator MUST
        # refuse.
        got = (
            agent_loop._desktop_codex_concurrent_work_evaluate_eligibility(
                self._spec(
                    expected_target_owner_role="claude_owned",
                ),
                self._lookup(),
                "no_signal",
            )
        )
        self.assertEqual(
            got["eligibility_state"],
            "refused_owner_role_violation",
        )
        self.assertEqual(
            got["actual_target_owner_role"], "codex_owned",
        )

    def test_would_invalidate_claude_refuses(self) -> None:
        got = (
            agent_loop._desktop_codex_concurrent_work_evaluate_eligibility(
                self._spec(
                    would_invalidate_claude_context=True,
                ),
                self._lookup(),
                "no_signal",
            )
        )
        self.assertEqual(
            got["eligibility_state"],
            "refused_would_invalidate_claude_context",
        )

    def test_eligible_bounded_execution(self) -> None:
        got = (
            agent_loop._desktop_codex_concurrent_work_evaluate_eligibility(
                self._spec(),
                self._lookup(),
                "no_signal",
            )
        )
        self.assertEqual(
            got["eligibility_state"],
            "eligible_bounded_execution",
        )
        self.assertEqual(
            got["actual_target_owner_role"], "codex_owned",
        )

    def test_signal_detected_still_eligible(self) -> None:
        # A `warning`-severity aggregate does not by itself
        # refuse the Phase 10AD gate; only `refused_pending_
        # recovery` / `unknown` refuse the whole surface.
        got = (
            agent_loop._desktop_codex_concurrent_work_evaluate_eligibility(
                self._spec(),
                self._lookup(),
                "signal_detected",
            )
        )
        self.assertEqual(
            got["eligibility_state"],
            "eligible_bounded_execution",
        )

    def test_overlap_precedence_over_owner_role_violation(
        self,
    ) -> None:
        # If Phase 10AC is refused AND owner-role would violate,
        # the overlap-refusal short-circuits first (safer state).
        got = (
            agent_loop._desktop_codex_concurrent_work_evaluate_eligibility(
                self._spec(
                    target_artifact_canonical_rel=(
                        ".agent-loop/not-in-map.md"
                    ),
                ),
                self._lookup(),
                "refused_pending_recovery",
            )
        )
        self.assertEqual(
            got["eligibility_state"], "refused_overlap_unsafe",
        )


# ---------------------------------------------------------------------------
# build_desktop_codex_concurrent_work_view
# ---------------------------------------------------------------------------
class BuildViewTests(unittest.TestCase):

    def test_view_shape_fields(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_codex_concurrent_work_view(
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
            "phase_10ad_runtime_available",
            "operator_inputs",
            "action_types",
            "effect_classes",
            "eligibility_states",
            "ownership_roles",
            "overlap_overall_state",
            "actions",
            "eligible_action_ids",
            "refused_action_ids",
            "precedence_note",
        ):
            self.assertIn(key, view, key)
        self.assertEqual(
            view["view_signal_version"], "phase-10ad-v1",
        )
        # Phase 10AD ships the shipped bounded eligibility
        # runtime helper so the flag advertises `True`.
        self.assertTrue(view["phase_10ad_runtime_available"])

    def test_all_actions_refused_when_overlap_unsafe(self) -> None:
        # With no canonical artifacts staged, the Phase 10AC
        # aggregate is `unknown` (fresh controller has no
        # summary), which refuses every Phase 10AD entry EXCEPT
        # the always-refused `codex_current_task_write` entry
        # whose `would_invalidate_claude_context=True` branch
        # fires first (per the closed evaluation order:
        # overlap-refusal short-circuit -> owner-role check ->
        # would-invalidate check -> unknown-overlap fallback ->
        # eligible).
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_codex_concurrent_work_view(
                    controller,
                )
            )
        self.assertEqual(view["eligible_action_ids"], [])
        by_id = {a["id"]: a for a in view["actions"]}
        self.assertEqual(
            by_id["codex_current_task_write"]["eligibility_state"],
            "refused_would_invalidate_claude_context",
        )
        for other_id in (
            "codex_prd_intake_read",
            "codex_plan_proposal_write",
            "codex_artifact_dashboard_read",
            "codex_memory_vault_read",
        ):
            self.assertEqual(
                by_id[other_id]["eligibility_state"],
                "refused_overlap_unsafe",
                other_id,
            )

    def test_eligible_when_overlap_clear(self) -> None:
        # When the Phase 10AC aggregate is `no_signal`, entries
        # whose target ownership matches and whose
        # would_invalidate_claude_context is False become
        # eligible; the `codex_current_task_write` entry stays
        # refused via the would-invalidate branch.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            with mock.patch.object(
                agent_loop,
                "build_desktop_overlap_detection_view",
                return_value=_mock_overlap_aggregate("no_signal"),
            ):
                view = (
                    agent_loop.build_desktop_codex_concurrent_work_view(
                        controller,
                    )
                )
        by_id = {a["id"]: a for a in view["actions"]}
        self.assertEqual(
            by_id["codex_prd_intake_read"]["eligibility_state"],
            "eligible_bounded_execution",
        )
        self.assertEqual(
            by_id["codex_plan_proposal_write"][
                "eligibility_state"
            ],
            "eligible_bounded_execution",
        )
        self.assertEqual(
            by_id["codex_artifact_dashboard_read"][
                "eligibility_state"
            ],
            "eligible_bounded_execution",
        )
        self.assertEqual(
            by_id["codex_memory_vault_read"][
                "eligibility_state"
            ],
            "eligible_bounded_execution",
        )
        self.assertEqual(
            by_id["codex_current_task_write"][
                "eligibility_state"
            ],
            "refused_would_invalidate_claude_context",
        )
        self.assertIn(
            "codex_current_task_write",
            view["refused_action_ids"],
        )

    def test_view_soft_fails_on_missing_loop_state(self) -> None:
        # The view builder MUST NOT raise if loop-state.json is
        # missing (soft-fail per the Phase 10L rule).
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            (controller / ".agent-loop" / "loop-state.json").unlink()
            view = (
                agent_loop.build_desktop_codex_concurrent_work_view(
                    controller,
                )
            )
        self.assertIsNone(view["current_loop_state_status"])

    def test_operator_inputs_threaded(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_codex_concurrent_work_view(
                    controller,
                    operator_inputs={
                        "identity": "alice",
                        "acknowledged_action_ids": (
                            "codex_prd_intake_read",
                        ),
                    },
                )
            )
        self.assertEqual(
            view["operator_inputs"]["identity"], "alice",
        )
        self.assertEqual(
            view["operator_inputs"]["acknowledged_action_ids"],
            ["codex_prd_intake_read"],
        )
        acked = [
            a
            for a in view["actions"]
            if a["id"] == "codex_prd_intake_read"
        ][0]
        self.assertTrue(acked["operator_acknowledged"])


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------
class RendererTests(unittest.TestCase):

    def test_render_includes_attribution_tags(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_codex_concurrent_work_view(
                    controller,
                )
            )
        output = "\n".join(
            agent_loop.render_desktop_codex_concurrent_work_text(
                view,
            ),
        )
        for tag in (
            "phase-10ad-v1",
            "[canonical mirror]",
            "[advisory]",
            "[codex-concurrent]",
            "[codex-owner]",
            "[codex-effect]",
            "[codex-eligibility]",
            "[codex-overlap]",
            "[deferred-runtime]",
            "[refused]",
        ):
            self.assertIn(tag, output, tag)

    def test_render_advertises_runtime_gate(self) -> None:
        # The rendered text MUST describe the shipped bounded
        # eligibility runtime helper and MUST NOT tell the
        # operator that eligibility enforcement is deferred.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_codex_concurrent_work_view(
                    controller,
                )
            )
        output = "\n".join(
            agent_loop.render_desktop_codex_concurrent_work_text(
                view,
            ),
        )
        for needle in (
            "phase_10ad_runtime_available",
            "evaluate_codex_concurrent_work_eligibility",
        ):
            self.assertIn(needle, output, needle)


# ---------------------------------------------------------------------------
# Controls builder
# ---------------------------------------------------------------------------
class ControlsBuilderTests(unittest.TestCase):

    def test_controls_one_per_action(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_codex_concurrent_work_view(
                    controller,
                )
            )
            controls = (
                agent_loop.build_desktop_codex_concurrent_work_controls(
                    view,
                )
            )
        self.assertEqual(
            len(controls), len(view["actions"]),
        )

    def test_every_control_dispatch_mode_is_copy_paste(
        self,
    ) -> None:
        # Phase 10I cap: NO new library-callable controls.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_codex_concurrent_work_view(
                    controller,
                )
            )
            controls = (
                agent_loop.build_desktop_codex_concurrent_work_controls(
                    view,
                )
            )
        for control in controls:
            self.assertEqual(
                control["dispatch_mode"], "copy_paste",
                control["id"],
            )

    def test_every_control_enabled_true(self) -> None:
        # Phase 10Z / 10AA / 10AB / 10AC affordance pattern: the
        # button surfaces `enabled=True` (copy path) while
        # `runtime_enabled` reflects eligibility.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_codex_concurrent_work_view(
                    controller,
                )
            )
            controls = (
                agent_loop.build_desktop_codex_concurrent_work_controls(
                    view,
                )
            )
        for control in controls:
            self.assertTrue(control["enabled"], control["id"])

    def test_runtime_enabled_matches_eligibility(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            with mock.patch.object(
                agent_loop,
                "build_desktop_overlap_detection_view",
                return_value=_mock_overlap_aggregate("no_signal"),
            ):
                view = (
                    agent_loop.build_desktop_codex_concurrent_work_view(
                        controller,
                    )
                )
                controls = (
                    agent_loop.build_desktop_codex_concurrent_work_controls(
                        view,
                    )
                )
        by_id = {c["id"]: c for c in controls}
        self.assertTrue(
            by_id["codex_prd_intake_read"]["runtime_enabled"],
        )
        # `codex_current_task_write` is always refused via the
        # would-invalidate branch, so `runtime_enabled` is False.
        self.assertFalse(
            by_id["codex_current_task_write"]["runtime_enabled"],
        )


# ---------------------------------------------------------------------------
# cmd_view_desktop_codex_concurrent_work
# ---------------------------------------------------------------------------
class CmdViewDesktopCodexConcurrentWorkTests(unittest.TestCase):

    def test_missing_controller_root_returns_exit_2(self) -> None:
        args = argparse.Namespace(controller_root=None)
        buf = io.StringIO()
        with redirect_stderr(buf):
            rc = agent_loop.cmd_view_desktop_codex_concurrent_work(
                args,
            )
        self.assertEqual(rc, 2)
        self.assertIn(
            "[desktop-codex-concurrent-work] REFUSED",
            buf.getvalue(),
        )

    def test_missing_markers_returns_exit_2(self) -> None:
        with TemporaryDirectory() as td:
            controller = Path(td) / "c"
            controller.mkdir()
            args = argparse.Namespace(
                controller_root=str(controller),
                operator_identity=None,
                acknowledge_action=None,
            )
            buf = io.StringIO()
            with redirect_stderr(buf):
                rc = (
                    agent_loop.cmd_view_desktop_codex_concurrent_work(
                        args,
                    )
                )
        self.assertEqual(rc, 2)
        self.assertIn(
            "[desktop-codex-concurrent-work] REFUSED",
            buf.getvalue(),
        )

    def test_success_returns_exit_0(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            args = argparse.Namespace(
                controller_root=str(controller),
                operator_identity=None,
                acknowledge_action=None,
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = (
                    agent_loop.cmd_view_desktop_codex_concurrent_work(
                        args,
                    )
                )
        self.assertEqual(rc, 0)
        self.assertIn("phase-10ad-v1", buf.getvalue())


# ---------------------------------------------------------------------------
# evaluate_codex_concurrent_work_eligibility (shipped runtime helper)
# ---------------------------------------------------------------------------
class EvaluateEligibilityRuntimeTests(unittest.TestCase):

    def test_unknown_action_id_raises_halt_error(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            with self.assertRaises(agent_loop.HaltError) as cm:
                agent_loop.evaluate_codex_concurrent_work_eligibility(
                    controller, "not_a_real_action_id",
                )
        self.assertEqual(
            cm.exception.status,
            agent_loop.HALTED_CODEX_CONCURRENT_WORK_UNSAFE,
        )
        self.assertIn(
            "not_a_real_action_id", cm.exception.reason,
        )

    def test_refused_action_raises_halt_error(self) -> None:
        # A fresh controller has an `unknown` Phase 10AC
        # aggregate; every entry is refused; the runtime helper
        # MUST raise.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            with self.assertRaises(agent_loop.HaltError) as cm:
                agent_loop.evaluate_codex_concurrent_work_eligibility(
                    controller, "codex_prd_intake_read",
                )
        self.assertEqual(
            cm.exception.status,
            agent_loop.HALTED_CODEX_CONCURRENT_WORK_UNSAFE,
        )
        self.assertIn(
            "refused_overlap_unsafe", cm.exception.reason,
        )

    def test_eligible_action_returns_envelope(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            with mock.patch.object(
                agent_loop,
                "build_desktop_overlap_detection_view",
                return_value=_mock_overlap_aggregate("no_signal"),
            ):
                got = (
                    agent_loop.evaluate_codex_concurrent_work_eligibility(
                        controller, "codex_prd_intake_read",
                    )
                )
        self.assertEqual(
            got["eligibility_state"],
            "eligible_bounded_execution",
        )
        self.assertEqual(got["id"], "codex_prd_intake_read")

    def test_would_invalidate_action_always_refused(self) -> None:
        # Even with the overlap gate clear, the always-refused
        # `codex_current_task_write` entry MUST raise via the
        # `refused_would_invalidate_claude_context` branch.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            with mock.patch.object(
                agent_loop,
                "build_desktop_overlap_detection_view",
                return_value=_mock_overlap_aggregate("no_signal"),
            ), self.assertRaises(agent_loop.HaltError) as cm:
                agent_loop.evaluate_codex_concurrent_work_eligibility(
                    controller, "codex_current_task_write",
                )
        self.assertEqual(
            cm.exception.status,
            agent_loop.HALTED_CODEX_CONCURRENT_WORK_UNSAFE,
        )
        self.assertIn(
            "refused_would_invalidate_claude_context",
            cm.exception.reason,
        )


# ---------------------------------------------------------------------------
# Desktop app integration
# ---------------------------------------------------------------------------
class DesktopAppIntegrationTests(unittest.TestCase):

    def test_assemble_includes_codex_concurrent_work_sub_view(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.assemble_desktop_app_view(controller)
        self.assertIn("codex_concurrent_work_view", view)
        sv = view["codex_concurrent_work_view"]
        self.assertIsInstance(sv, dict)
        self.assertEqual(sv["view_signal_version"], "phase-10ad-v1")

    def test_render_includes_phase_10ad_label(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.assemble_desktop_app_view(controller)
            lines = agent_loop.render_desktop_app_text(view)
        output = "\n".join(lines)
        self.assertIn(
            "=== Codex-Owned Concurrent Work (Phase 10AD) ===",
            output,
        )
        self.assertIn("phase-10ad-v1", output)


# ---------------------------------------------------------------------------
# Non-mutation invariants
# ---------------------------------------------------------------------------
class NonMutationInvariantsTests(unittest.TestCase):

    def test_view_does_not_open_socket(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            with mock.patch.object(socket, "socket") as p:
                agent_loop.build_desktop_codex_concurrent_work_view(
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
                agent_loop.build_desktop_codex_concurrent_work_view(
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
                agent_loop.build_desktop_codex_concurrent_work_view(
                    controller,
                )
        h.assert_not_called()

    def test_view_does_not_mutate_loop_state(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            ls = controller / ".agent-loop" / "loop-state.json"
            before = ls.read_bytes()
            agent_loop.build_desktop_codex_concurrent_work_view(
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
            agent_loop.build_desktop_codex_concurrent_work_view(
                controller,
            )
        self.assertFalse(log_path.exists())

    def test_view_does_not_persist_concurrent_work_cache(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            before_root = sorted(
                p.name for p in controller.iterdir()
            )
            before_dot = sorted(
                p.name
                for p in (controller / ".agent-loop").iterdir()
            )
            agent_loop.build_desktop_codex_concurrent_work_view(
                controller,
            )
            after_root = sorted(
                p.name for p in controller.iterdir()
            )
            after_dot = sorted(
                p.name
                for p in (controller / ".agent-loop").iterdir()
            )
        self.assertEqual(before_root, after_root)
        self.assertEqual(before_dot, after_dot)

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
                agent_loop.build_desktop_codex_concurrent_work_view(
                    controller,
                )
            finally:
                for p in patches:
                    p.stop()
        for m in mocks:
            m.assert_not_called()

    def test_runtime_helper_does_not_launch_concurrent_worker(
        self,
    ) -> None:
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
                try:
                    agent_loop.evaluate_codex_concurrent_work_eligibility(
                        controller, "codex_prd_intake_read",
                    )
                except agent_loop.HaltError:
                    pass
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
                agent_loop.build_desktop_codex_concurrent_work_view(
                    controller,
                )
            )
            controls = (
                agent_loop.build_desktop_codex_concurrent_work_controls(
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
