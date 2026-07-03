"""Phase 10AB - Controlled Concurrent Operation Contract tests.

Exercises:
  - module-level constants (signal version, precedence note,
    closed enumerations)
  - operator-input normalizer
  - closed rule registry + descriptor validator (contract-only)
  - closed ownership-map + ownership-entry validator (POSIX path
    boundedness, closed role vocabulary)
  - pure per-artifact staleness probe (`Path.stat()`; NEVER
    reads artifact BODY content)
  - approval-state / enablement-state helpers
  - `build_desktop_concurrency_view(...)` shape + soft-fail on
    missing loop-state + fail-closed default (every rule
    surfaces as `refused_until_policy_update`)
  - renderer per-line attribution
  - `build_desktop_concurrency_controls(...)` widget shape
    (COPY-PASTE only; every button clickable for clipboard-
    copy per the Phase 10Z fix-cycle affordance; `runtime_
    enabled=False` mirrors the deferred contract slice)
  - `cmd_view_desktop_concurrency(...)` CLI + Phase 7C exit-0
  - integration into `assemble_desktop_app_view(...)` +
    `render_desktop_app_text(...)`
  - non-mutation invariants (no socket, no subprocess, no
    orchestrator.log append, no loop-state mutation, no
    `_halt(...)`, no Phase 10I library-callable cap widening,
    no persisted concurrency cache, no actual concurrent
    Codex/Claude runtime launched, NEVER reads artifact BODY
    content)
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
                "Phase 10AB - Controlled Concurrent Operation "
                "Contract"
            ),
            "task": "phase-10ab-test",
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
            agent_loop.DESKTOP_CONCURRENCY_SIGNAL_VERSION,
            "phase-10ab-v1",
        )

    def test_precedence_note_pins_phase_10ab_contract(self) -> None:
        note = agent_loop.DESKTOP_CONCURRENCY_PRECEDENCE_NOTE
        for needle in (
            "Phase 10AB",
            "Phase 3A orchestrator contract",
            "Phase 4 planner / activator separation",
            "Phase 10I",
            "refused_until_policy_update",
            "NEVER launches or coordinates any actual "
            "concurrent Codex/Claude runtime",
            "NEVER schedules a background watcher",
            "NEVER reads canonical artifact BODY content",
            "NEVER mutates any canonical artifact",
        ):
            self.assertIn(needle, note, needle)

    def test_overlap_states_closed_enum(self) -> None:
        self.assertEqual(
            agent_loop.CONCURRENCY_OVERLAP_STATES,
            (
                "no_overlap",
                "overlap_safe_read_only",
                "overlap_invalidating",
                "unknown",
            ),
        )

    def test_ownership_roles_closed_enum(self) -> None:
        self.assertEqual(
            agent_loop.CONCURRENCY_OWNERSHIP_ROLES,
            (
                "claude_owned",
                "codex_owned",
                "orchestrator_owned",
                "human_owned",
                "shared_read_only",
            ),
        )

    def test_staleness_states_closed_enum(self) -> None:
        self.assertEqual(
            agent_loop.CONCURRENCY_STALENESS_STATES,
            (
                "fresh",
                "stale_phase",
                "stale_cycle",
                "missing",
                "unknown",
            ),
        )

    def test_invalidation_triggers_closed_enum(self) -> None:
        self.assertEqual(
            agent_loop.CONCURRENCY_INVALIDATION_TRIGGERS,
            (
                "codex_review_verdict_changed",
                "claude_prompt_replaced",
                "fix_prompt_replaced",
                "loop_state_advanced",
                "phase_activation_advanced",
                "cycle_count_advanced",
            ),
        )

    def test_recovery_actions_closed_enum(self) -> None:
        self.assertEqual(
            agent_loop.CONCURRENCY_RECOVERY_ACTIONS,
            (
                "re_read_active_prompt",
                "re_read_codex_review",
                "refresh_loop_state",
                "manual_operator_intervention",
                "refused_until_policy_update",
            ),
        )

    def test_refusal_reasons_closed_enum(self) -> None:
        self.assertEqual(
            agent_loop.CONCURRENCY_REFUSAL_REASONS,
            (
                "overlap_not_permitted",
                "stale_artifact_detected",
                "invalidation_trigger_active",
                "runtime_not_available",
                "approval_mode_strict",
            ),
        )

    def test_enablement_states_closed_enum(self) -> None:
        self.assertEqual(
            agent_loop.CONCURRENCY_ENABLEMENT_STATES,
            (
                "disabled_by_default",
                "enabled_pending_runtime",
                "refused_until_policy_update",
            ),
        )

    def test_approval_requirements_closed_enum(self) -> None:
        self.assertEqual(
            agent_loop.CONCURRENCY_APPROVAL_REQUIREMENTS,
            (
                "operator_acknowledged_contract",
                "operator_supplied_identity",
                "approval_mode_supports_concurrency",
                "phase_10ab_runtime_available",
                "no_invalidation_trigger_active",
            ),
        )

    def test_permitted_approval_modes(self) -> None:
        self.assertEqual(
            agent_loop.CONCURRENCY_PERMITTED_APPROVAL_MODES,
            frozenset({"review", "autonomous"}),
        )


# ---------------------------------------------------------------------------
# Registry + descriptor validator
# ---------------------------------------------------------------------------
class RegistryTests(unittest.TestCase):

    def test_registry_ships_six_rules(self) -> None:
        self.assertEqual(
            len(agent_loop._DESKTOP_CONCURRENCY_RULE_REGISTRY), 6,
        )

    def test_registry_covers_every_overlap_state_except_unknown(
        self,
    ) -> None:
        overlaps = {
            spec["overlap_state"]
            for spec in agent_loop._DESKTOP_CONCURRENCY_RULE_REGISTRY
        }
        # `unknown` is the fail-closed default; it does not
        # appear as a shipped rule.
        self.assertEqual(
            overlaps,
            {
                "no_overlap",
                "overlap_safe_read_only",
                "overlap_invalidating",
            },
        )

    def test_registry_exercises_every_recovery_action_except_refused(
        self,
    ) -> None:
        actions = {
            spec["recovery_action"]
            for spec in agent_loop._DESKTOP_CONCURRENCY_RULE_REGISTRY
        }
        self.assertIn("re_read_codex_review", actions)
        self.assertIn("re_read_active_prompt", actions)
        self.assertIn("refresh_loop_state", actions)
        self.assertIn("manual_operator_intervention", actions)

    def test_every_registry_entry_passes_validator(self) -> None:
        for spec in agent_loop._DESKTOP_CONCURRENCY_RULE_REGISTRY:
            agent_loop._desktop_concurrency_validate_rule_descriptor(
                spec,
            )


class ValidatorTests(unittest.TestCase):

    def _valid(self):
        return {
            "id": "x",
            "display_name": "X",
            "overlap_state": "overlap_invalidating",
            "owner_role_writer": "codex_owned",
            "owner_role_reader": "claude_owned",
            "invalidation_trigger": (
                "codex_review_verdict_changed"
            ),
            "recovery_action": "re_read_codex_review",
            "description": "d",
            "safety_copy": "s",
            "approval_requirements": (
                "operator_acknowledged_contract",
            ),
            "deferred_runtime_marker": "m",
            "refusal_reason_template": "t",
        }

    def test_non_dict_refuses(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_concurrency_validate_rule_descriptor(
                ["not", "a", "dict"],
            )

    def test_missing_string_field_refuses(self) -> None:
        spec = self._valid()
        del spec["overlap_state"]
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_concurrency_validate_rule_descriptor(
                spec,
            )

    def test_unknown_overlap_state_refuses(self) -> None:
        spec = self._valid()
        spec["overlap_state"] = "not_an_overlap"
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_concurrency_validate_rule_descriptor(
                spec,
            )

    def test_unknown_writer_role_refuses(self) -> None:
        spec = self._valid()
        spec["owner_role_writer"] = "unknown_role"
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_concurrency_validate_rule_descriptor(
                spec,
            )

    def test_unknown_reader_role_refuses(self) -> None:
        spec = self._valid()
        spec["owner_role_reader"] = "unknown_role"
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_concurrency_validate_rule_descriptor(
                spec,
            )

    def test_unknown_invalidation_trigger_refuses(self) -> None:
        spec = self._valid()
        spec["invalidation_trigger"] = "not_a_trigger"
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_concurrency_validate_rule_descriptor(
                spec,
            )

    def test_unknown_recovery_action_refuses(self) -> None:
        spec = self._valid()
        spec["recovery_action"] = "not_a_recovery"
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_concurrency_validate_rule_descriptor(
                spec,
            )

    def test_unknown_approval_requirement_refuses(self) -> None:
        spec = self._valid()
        spec["approval_requirements"] = ("not_a_requirement",)
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_concurrency_validate_rule_descriptor(
                spec,
            )

    def test_non_tuple_approval_requirements_refuses(self) -> None:
        spec = self._valid()
        spec["approval_requirements"] = [
            "operator_acknowledged_contract",
        ]
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_concurrency_validate_rule_descriptor(
                spec,
            )


# ---------------------------------------------------------------------------
# Ownership-map validator
# ---------------------------------------------------------------------------
class OwnershipMapTests(unittest.TestCase):

    def test_ownership_map_is_non_empty(self) -> None:
        self.assertGreater(
            len(agent_loop._DESKTOP_CONCURRENCY_OWNERSHIP_MAP),
            0,
        )

    def test_ownership_map_covers_every_role(self) -> None:
        roles = {
            role for _, role in (
                agent_loop._DESKTOP_CONCURRENCY_OWNERSHIP_MAP
            )
        }
        self.assertEqual(
            roles, set(agent_loop.CONCURRENCY_OWNERSHIP_ROLES),
        )

    def test_every_ownership_entry_passes_validator(self) -> None:
        for entry in (
            agent_loop._DESKTOP_CONCURRENCY_OWNERSHIP_MAP
        ):
            agent_loop._desktop_concurrency_validate_ownership_entry(
                entry,
            )

    def test_backslash_path_refuses(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_concurrency_validate_ownership_entry(
                (".agent-loop\\loop-state.json", "orchestrator_owned"),
            )

    def test_absolute_path_refuses(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_concurrency_validate_ownership_entry(
                ("/etc/passwd", "orchestrator_owned"),
            )

    def test_drive_prefix_refuses(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_concurrency_validate_ownership_entry(
                ("C:/x", "orchestrator_owned"),
            )

    def test_parent_traversal_refuses(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_concurrency_validate_ownership_entry(
                ("a/../b", "orchestrator_owned"),
            )

    def test_unknown_role_refuses(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_concurrency_validate_ownership_entry(
                ("TASK.md", "not_a_role"),
            )

    def test_wrong_shape_refuses(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_concurrency_validate_ownership_entry(
                ["TASK.md", "codex_owned"],
            )


# ---------------------------------------------------------------------------
# Operator-input normalizer
# ---------------------------------------------------------------------------
class OperatorInputsNormalizerTests(unittest.TestCase):

    def test_none_returns_empty_defaults(self) -> None:
        got = (
            agent_loop._desktop_concurrency_normalize_operator_inputs(
                None,
            )
        )
        self.assertEqual(got["identity"], "")
        self.assertEqual(
            got["acknowledged_rule_ids"], frozenset(),
        )

    def test_non_dict_refuses(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_concurrency_normalize_operator_inputs(
                ["not", "a", "dict"],
            )

    def test_iterable_ids_normalized(self) -> None:
        got = (
            agent_loop._desktop_concurrency_normalize_operator_inputs(
                {
                    "identity": " me ",
                    "acknowledged_rule_ids": [
                        "codex_review_verdict_supersedes_in_"
                        "flight_claude_work",
                    ],
                },
            )
        )
        self.assertEqual(got["identity"], "me")
        self.assertIn(
            "codex_review_verdict_supersedes_in_flight_"
            "claude_work",
            got["acknowledged_rule_ids"],
        )

    def test_wrong_identity_type_refuses(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_concurrency_normalize_operator_inputs(
                {"identity": 42},
            )

    def test_wrong_ack_type_refuses(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_concurrency_normalize_operator_inputs(
                {
                    "identity": "me",
                    "acknowledged_rule_ids": "not-iterable",
                },
            )


# ---------------------------------------------------------------------------
# Staleness probe
# ---------------------------------------------------------------------------
class StalenessProbeTests(unittest.TestCase):

    def test_missing_artifact_reports_missing(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            probe = (
                agent_loop._desktop_concurrency_probe_artifact_staleness(
                    controller,
                    ".agent-loop/codex-review.md",
                    active_ts=None,
                )
            )
        self.assertFalse(probe["exists"])
        self.assertEqual(probe["staleness_state"], "missing")
        self.assertIsNone(probe["last_modified_utc"])
        self.assertIsNone(probe["size_bytes"])

    def test_present_artifact_without_active_ts_reports_unknown(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            (controller / ".agent-loop"
             / "codex-review.md").write_bytes(b"x")
            probe = (
                agent_loop._desktop_concurrency_probe_artifact_staleness(
                    controller,
                    ".agent-loop/codex-review.md",
                    active_ts=None,
                )
            )
        self.assertTrue(probe["exists"])
        self.assertEqual(probe["staleness_state"], "unknown")

    def test_fresh_artifact_reports_fresh(self) -> None:
        import time
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            (controller / ".agent-loop"
             / "codex-review.md").write_bytes(b"x")
            probe = (
                agent_loop._desktop_concurrency_probe_artifact_staleness(
                    controller,
                    ".agent-loop/codex-review.md",
                    active_ts=time.time(),
                )
            )
        self.assertEqual(probe["staleness_state"], "fresh")

    def test_stale_cycle_boundary(self) -> None:
        import time
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            (controller / ".agent-loop"
             / "codex-review.md").write_bytes(b"x")
            # active_ts is far enough in the future to push the
            # artifact past the 1-hour cycle-scale grace window
            # but not past the 7-day phase-scale window.
            probe = (
                agent_loop._desktop_concurrency_probe_artifact_staleness(
                    controller,
                    ".agent-loop/codex-review.md",
                    active_ts=time.time() + 2 * 3600,
                )
            )
        self.assertEqual(probe["staleness_state"], "stale_cycle")

    def test_stale_phase_boundary(self) -> None:
        import time
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            (controller / ".agent-loop"
             / "codex-review.md").write_bytes(b"x")
            # active_ts is far enough in the future to push the
            # artifact past the 7-day phase-scale window.
            probe = (
                agent_loop._desktop_concurrency_probe_artifact_staleness(
                    controller,
                    ".agent-loop/codex-review.md",
                    active_ts=time.time() + 10 * 24 * 3600,
                )
            )
        self.assertEqual(probe["staleness_state"], "stale_phase")

    def test_probe_never_reads_artifact_body(self) -> None:
        sentinel = (
            "PHASE_10AB_STALENESS_PROBE_SENTINEL_DO_NOT_LEAK"
        )
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            (controller / ".agent-loop"
             / "codex-review.md").write_bytes(
                sentinel.encode("utf-8"),
            )
            probe = (
                agent_loop._desktop_concurrency_probe_artifact_staleness(
                    controller,
                    ".agent-loop/codex-review.md",
                    active_ts=None,
                )
            )
        self.assertNotIn(
            sentinel, json.dumps(probe, default=str),
        )


# ---------------------------------------------------------------------------
# Approval / enablement helpers
# ---------------------------------------------------------------------------
class ApprovalStateTests(unittest.TestCase):

    def _spec(self):
        return dict(
            agent_loop._DESKTOP_CONCURRENCY_RULE_REGISTRY[0],
        )

    def test_all_unsatisfied_default(self) -> None:
        state = (
            agent_loop._desktop_concurrency_compute_approval_state(
                self._spec(),
                approval_mode=None,
                phase_10ab_runtime_available=False,
                operator_acknowledged_contract=False,
                operator_supplied_identity=False,
                no_invalidation_trigger_active=False,
            )
        )
        for req in agent_loop.CONCURRENCY_APPROVAL_REQUIREMENTS:
            self.assertFalse(state[req]["satisfied"], req)

    def test_strict_mode_refuses_concurrency(self) -> None:
        state = (
            agent_loop._desktop_concurrency_compute_approval_state(
                self._spec(),
                approval_mode="strict",
                phase_10ab_runtime_available=True,
                operator_acknowledged_contract=True,
                operator_supplied_identity=True,
                no_invalidation_trigger_active=True,
            )
        )
        self.assertFalse(
            state["approval_mode_supports_concurrency"][
                "satisfied"
            ],
        )

    def test_review_and_autonomous_modes_are_permitted(self) -> None:
        for mode in ("review", "autonomous"):
            state = (
                agent_loop._desktop_concurrency_compute_approval_state(
                    self._spec(),
                    approval_mode=mode,
                    phase_10ab_runtime_available=False,
                    operator_acknowledged_contract=False,
                    operator_supplied_identity=False,
                    no_invalidation_trigger_active=False,
                )
            )
            self.assertTrue(
                state["approval_mode_supports_concurrency"][
                    "satisfied"
                ],
                mode,
            )


class EnablementStateTests(unittest.TestCase):

    def _spec(self):
        return dict(
            agent_loop._DESKTOP_CONCURRENCY_RULE_REGISTRY[0],
        )

    def _approval_all_true(self, spec):
        return (
            agent_loop._desktop_concurrency_compute_approval_state(
                spec,
                approval_mode="review",
                phase_10ab_runtime_available=True,
                operator_acknowledged_contract=True,
                operator_supplied_identity=True,
                no_invalidation_trigger_active=True,
            )
        )

    def test_runtime_unavailable_forces_refused(self) -> None:
        spec = self._spec()
        state = (
            agent_loop._desktop_concurrency_compute_approval_state(
                spec,
                approval_mode="review",
                phase_10ab_runtime_available=False,
                operator_acknowledged_contract=True,
                operator_supplied_identity=True,
                no_invalidation_trigger_active=True,
            )
        )
        enablement, _ = (
            agent_loop._desktop_concurrency_compute_enablement_state(
                spec, approval_state=state,
            )
        )
        self.assertEqual(enablement, "refused_until_policy_update")

    def test_invalidation_trigger_active_forces_refused(
        self,
    ) -> None:
        spec = self._spec()
        state = (
            agent_loop._desktop_concurrency_compute_approval_state(
                spec,
                approval_mode="review",
                phase_10ab_runtime_available=True,
                operator_acknowledged_contract=True,
                operator_supplied_identity=True,
                no_invalidation_trigger_active=False,
            )
        )
        enablement, _ = (
            agent_loop._desktop_concurrency_compute_enablement_state(
                spec, approval_state=state,
            )
        )
        self.assertEqual(enablement, "refused_until_policy_update")

    def test_runtime_available_all_met_promotes(self) -> None:
        spec = self._spec()
        state = self._approval_all_true(spec)
        enablement, _ = (
            agent_loop._desktop_concurrency_compute_enablement_state(
                spec, approval_state=state,
            )
        )
        self.assertEqual(enablement, "enabled_pending_runtime")

    def test_operator_requirement_missing_disabled_by_default(
        self,
    ) -> None:
        spec = self._spec()
        state = (
            agent_loop._desktop_concurrency_compute_approval_state(
                spec,
                approval_mode="review",
                phase_10ab_runtime_available=True,
                operator_acknowledged_contract=False,
                operator_supplied_identity=True,
                no_invalidation_trigger_active=True,
            )
        )
        enablement, _ = (
            agent_loop._desktop_concurrency_compute_enablement_state(
                spec, approval_state=state,
            )
        )
        self.assertEqual(enablement, "disabled_by_default")


# ---------------------------------------------------------------------------
# build_desktop_concurrency_view
# ---------------------------------------------------------------------------
class BuildConcurrencyViewTests(unittest.TestCase):

    def test_view_shape_fields(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.build_desktop_concurrency_view(
                controller,
            )
        for key in (
            "view_signal_version",
            "controller_path_canonical",
            "current_loop_state_status",
            "controller_loop_state_approval_mode",
            "current_loop_state_phase",
            "current_loop_state_sub_phase",
            "current_loop_state_cycle_count",
            "phase_10ab_runtime_available",
            "operator_inputs",
            "overlap_states",
            "ownership_roles",
            "staleness_states",
            "invalidation_triggers",
            "recovery_actions",
            "refusal_reasons",
            "enablement_states",
            "approval_requirements",
            "rules",
            "ownership_map",
            "precedence_note",
        ):
            self.assertIn(key, view, key)
        self.assertEqual(
            view["view_signal_version"], "phase-10ab-v1",
        )
        self.assertFalse(view["phase_10ab_runtime_available"])

    def test_every_rule_refused_by_default(self) -> None:
        # Fail-closed default: since runtime is not available,
        # every rule surfaces as `refused_until_policy_update`
        # regardless of operator input.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.build_desktop_concurrency_view(
                controller,
                operator_inputs={
                    "identity": "me",
                    "acknowledged_rule_ids": [
                        s["id"] for s in (
                            agent_loop._DESKTOP_CONCURRENCY_RULE_REGISTRY
                        )
                    ],
                },
            )
        for rule in view["rules"]:
            self.assertEqual(
                rule["enablement_state"],
                "refused_until_policy_update",
                rule["id"],
            )

    def test_view_soft_fails_on_missing_loop_state(self) -> None:
        with TemporaryDirectory() as td:
            controller = Path(td) / "c"
            controller.mkdir()
            for name in ("AGENTS.md", "CLAUDE.md", "TASK.md",
                         "README.md"):
                (controller / name).write_text(
                    "x", encoding="utf-8",
                )
            (controller / ".agent-loop").mkdir()
            view = agent_loop.build_desktop_concurrency_view(
                controller,
            )
        self.assertIsNone(view["current_loop_state_status"])
        self.assertIsNone(
            view["controller_loop_state_approval_mode"],
        )
        self.assertIsNone(view["current_loop_state_phase"])
        self.assertIsNone(view["current_loop_state_sub_phase"])
        self.assertIsNone(view["current_loop_state_cycle_count"])

    def test_view_surfaces_ownership_map(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.build_desktop_concurrency_view(
                controller,
            )
        # Every shipped ownership entry maps to exactly one
        # per-artifact descriptor with a closed role.
        self.assertEqual(
            len(view["ownership_map"]),
            len(agent_loop._DESKTOP_CONCURRENCY_OWNERSHIP_MAP),
        )
        for entry in view["ownership_map"]:
            self.assertIn(
                entry["owner_role"],
                agent_loop.CONCURRENCY_OWNERSHIP_ROLES,
                entry["path_canonical_rel"],
            )
            self.assertIn(
                entry["staleness_state"],
                agent_loop.CONCURRENCY_STALENESS_STATES,
                entry["path_canonical_rel"],
            )


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------
class RendererTests(unittest.TestCase):

    def test_render_includes_attribution_tags(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.build_desktop_concurrency_view(
                controller,
            )
        output = "\n".join(
            agent_loop.render_desktop_concurrency_text(view),
        )
        for tag in (
            "phase-10ab-v1",
            "[canonical mirror]",
            "[advisory]",
            "[concurrency-overlap]",
            "[concurrency-owner]",
            "[concurrency-invalidation]",
            "[concurrency-recovery]",
            "[concurrency-approval]",
            "[concurrency-enablement]",
            "[deferred-runtime]",
            "[ownership-map]",
            "[refused]",
        ):
            self.assertIn(tag, output, tag)


# ---------------------------------------------------------------------------
# build_desktop_concurrency_controls
# ---------------------------------------------------------------------------
class ConcurrencyControlsBuilderTests(unittest.TestCase):

    def test_controls_one_per_rule(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.build_desktop_concurrency_view(
                controller,
            )
            controls = (
                agent_loop.build_desktop_concurrency_controls(
                    view,
                )
            )
        self.assertEqual(
            len(controls), len(view["rules"]),
        )
        for control in controls:
            self.assertEqual(
                control["dispatch_mode"], "copy_paste",
            )
            self.assertEqual(
                control["category"],
                "concurrency_contract_ux",
            )
            self.assertTrue(control["enabled"], control["id"])
            self.assertFalse(
                control["runtime_enabled"], control["id"],
            )

    def test_clipboard_payload_is_acknowledgement_template(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.build_desktop_concurrency_view(
                controller,
            )
            controls = (
                agent_loop.build_desktop_concurrency_controls(
                    view,
                )
            )
        for control in controls:
            payload = control["clipboard_payload"]
            self.assertIn("rule_id:", payload)
            self.assertIn("overlap_state:", payload)
            self.assertIn(
                "requested_action: acknowledge_contract",
                payload,
            )
            self.assertIn(
                "operator_identity: <NAME>", payload,
            )
            # No shipped CLI invocation.
            self.assertNotIn(
                "python scripts/agent_loop.py", payload,
            )

    def test_control_label_discloses_enablement_state(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.build_desktop_concurrency_view(
                controller,
            )
            controls = (
                agent_loop.build_desktop_concurrency_controls(
                    view,
                )
            )
        for control in controls:
            self.assertIn(
                f"[{control['enablement_state']}]",
                control["label"],
                control["id"],
            )
            self.assertIn(
                "Copy concurrency-contract acknowledgement "
                "template:",
                control["label"],
                control["id"],
            )

    def test_click_only_copies_template_never_runs_runtime(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.build_desktop_concurrency_view(
                controller,
            )
            controls = (
                agent_loop.build_desktop_concurrency_controls(
                    view,
                )
            )
        forbidden = {
            "runtime_command",
            "on_click",
            "subprocess",
            "library_call",
            "callable",
            "handler",
        }
        for control in controls:
            for field in forbidden:
                self.assertNotIn(field, control, control["id"])
            self.assertIsInstance(
                control["clipboard_payload"], str,
            )


# ---------------------------------------------------------------------------
# CLI handler
# ---------------------------------------------------------------------------
class CmdViewDesktopConcurrencyTests(unittest.TestCase):

    def _args(self, **kwargs):
        defaults = {
            "controller_root": None,
            "operator_identity": None,
            "acknowledge_rule": None,
        }
        defaults.update(kwargs)
        return argparse.Namespace(**defaults)

    def test_refuses_missing_controller_root(self) -> None:
        buf_err = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(
            buf_err,
        ):
            rc = agent_loop.cmd_view_desktop_concurrency(
                self._args(),
            )
        self.assertEqual(rc, 2)
        self.assertIn(
            "[desktop-concurrency] REFUSED",
            buf_err.getvalue(),
        )

    def test_refuses_invalid_controller_root(self) -> None:
        with TemporaryDirectory() as td:
            buf_err = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(
                buf_err,
            ):
                rc = agent_loop.cmd_view_desktop_concurrency(
                    self._args(controller_root=str(td)),
                )
        self.assertEqual(rc, 2)
        self.assertIn("REFUSED", buf_err.getvalue())

    def test_phase_7c_exits_zero_on_valid_root(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            buf_out = io.StringIO()
            with redirect_stdout(buf_out):
                rc = agent_loop.cmd_view_desktop_concurrency(
                    self._args(controller_root=str(controller)),
                )
        self.assertEqual(rc, 0)
        self.assertIn(
            "[desktop-concurrency]", buf_out.getvalue(),
        )

    def test_handler_registered(self) -> None:
        self.assertIn(
            "view-desktop-concurrency", agent_loop.HANDLERS,
        )

    def test_parser_accepts_subcommand_and_flags(self) -> None:
        parser = agent_loop.build_parser()
        args = parser.parse_args([
            "view-desktop-concurrency",
            "--controller-root", ".",
            "--operator-identity", "me",
            "--acknowledge-rule",
            "codex_review_verdict_supersedes_in_flight_"
            "claude_work",
        ])
        self.assertEqual(args.cmd, "view-desktop-concurrency")
        self.assertEqual(args.operator_identity, "me")
        self.assertEqual(
            args.acknowledge_rule,
            [
                "codex_review_verdict_supersedes_in_flight_"
                "claude_work",
            ],
        )


# ---------------------------------------------------------------------------
# Integration into the Phase 10M desktop app view
# ---------------------------------------------------------------------------
class DesktopAppIntegrationTests(unittest.TestCase):

    def test_assemble_includes_concurrency_view_key(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.assemble_desktop_app_view(controller)
        self.assertIn("concurrency_view", view)
        sv = view["concurrency_view"]
        self.assertIsInstance(sv, dict)
        self.assertEqual(sv["view_signal_version"], "phase-10ab-v1")

    def test_render_includes_phase_10ab_label(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.assemble_desktop_app_view(controller)
            lines = agent_loop.render_desktop_app_text(view)
        output = "\n".join(lines)
        self.assertIn(
            "=== Controlled Concurrent Operation (Phase 10AB) ===",
            output,
        )
        self.assertIn("phase-10ab-v1", output)


# ---------------------------------------------------------------------------
# Non-mutation invariants
# ---------------------------------------------------------------------------
class NonMutationInvariantsTests(unittest.TestCase):

    def test_view_does_not_open_socket(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            with mock.patch.object(socket, "socket") as p:
                agent_loop.build_desktop_concurrency_view(
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
                agent_loop.build_desktop_concurrency_view(
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
                agent_loop.build_desktop_concurrency_view(
                    controller,
                )
        h.assert_not_called()

    def test_view_does_not_mutate_loop_state(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            ls = controller / ".agent-loop" / "loop-state.json"
            before = ls.read_bytes()
            agent_loop.build_desktop_concurrency_view(controller)
            after = ls.read_bytes()
        self.assertEqual(before, after)

    def test_view_does_not_append_orchestrator_log(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            log_path = (
                controller / ".agent-loop" / "orchestrator.log"
            )
            agent_loop.build_desktop_concurrency_view(controller)
        self.assertFalse(log_path.exists())

    def test_view_does_not_persist_concurrency_cache(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            before_root = sorted(
                p.name for p in controller.iterdir()
            )
            before_dot = sorted(
                p.name
                for p in (controller / ".agent-loop").iterdir()
            )
            agent_loop.build_desktop_concurrency_view(controller)
            after_root = sorted(
                p.name for p in controller.iterdir()
            )
            after_dot = sorted(
                p.name
                for p in (controller / ".agent-loop").iterdir()
            )
        self.assertEqual(before_root, after_root)
        self.assertEqual(before_dot, after_dot)

    def test_view_never_reads_artifact_body(self) -> None:
        # Write a unique sentinel into every ownership-map
        # artifact and assert it does NOT appear in the
        # assembled view dict OR the rendered text. This is the
        # headline "never reads canonical artifact BODY content"
        # invariant end-to-end.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            sentinels = []
            for i, (path_rel, _role) in enumerate(
                agent_loop._DESKTOP_CONCURRENCY_OWNERSHIP_MAP
            ):
                sentinel = (
                    f"PHASE_10AB_ARTIFACT_BODY_SENTINEL_"
                    f"{i}_DO_NOT_LEAK"
                )
                path = controller / path_rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(sentinel.encode("utf-8"))
                sentinels.append(sentinel)
            view = agent_loop.build_desktop_concurrency_view(
                controller,
            )
            rendered = "\n".join(
                agent_loop.render_desktop_concurrency_text(view),
            )
        serialized_view = json.dumps(view, default=str)
        for sentinel in sentinels:
            self.assertNotIn(
                sentinel, serialized_view, sentinel,
            )
            self.assertNotIn(sentinel, rendered, sentinel)

    def test_view_never_launches_actual_concurrent_runtime(
        self,
    ) -> None:
        # The Phase 10AB slice ships the CONTRACT only. It MUST
        # NOT launch any actual concurrent Codex/Claude runtime
        # via threading, multiprocessing, or asyncio. Patch the
        # entry points and assert zero calls during a full
        # view build.
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
                agent_loop.build_desktop_concurrency_view(
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
            view = agent_loop.build_desktop_concurrency_view(
                controller,
            )
            controls = (
                agent_loop.build_desktop_concurrency_controls(
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
