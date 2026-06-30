"""Phase 10T - MCP Read-Only Assistance In Desktop App tests.

Exercises:
  - module-level constants (signal version, precedence note,
    permission-class / capability-category / enablement-state /
    approval-requirement closed enumerations)
  - the closed `_DESKTOP_MCP_ASSISTANCE_REGISTRY` shape
  - the `_desktop_mcp_assistance_validate_descriptor(...)`
    validator (positive + every closed-enumeration negative)
  - per-requirement approval-state computation
  - the closed three-state enablement state machine including the
    `deferred_mutating_class` short-circuit refusal
  - `build_desktop_mcp_assistance_view(...)` shape + HaltError
    soft-failure on the loop-state delegate
  - `render_desktop_mcp_assistance_text(...)` per-line attribution
  - `build_desktop_mcp_assistance_controls(...)` widget descriptor
    shape (enabled mirrors enablement_state =
    enabled_pending_runtime; `deferred_mutating_class` servers are
    always disabled)
  - `cmd_view_desktop_mcp_assistance(...)` CLI handler wiring, the
    Phase-10L-mandated `--controller-root` REQUIRED refusal, the
    missing-marker refusal, the Phase 7C always-exit-0 rule,
    handler-registered, parser-accepts-subcommand
  - integration into `assemble_desktop_app_view(...)` and
    `render_desktop_app_text(...)` (the new `MCP Assistance
    (Phase 10T)` sub-view)
  - non-mutation invariants (no orchestrator.log write, no
    loop-state mutation, no `_halt(...)` invocation, no subprocess
    spawn for all six entry points, no network socket open, no
    Phase 10I cap widening, no canonical artifact write)
"""
from __future__ import annotations

import argparse
import io
import json
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
    (td / "AGENTS.md").write_text("test\n", encoding="utf-8")
    (td / "CLAUDE.md").write_text("test\n", encoding="utf-8")
    (td / "TASK.md").write_text(
        "# TASK.md\n## Human Objective\n\ntest task\n",
        encoding="utf-8",
    )
    (td / ".agent-loop").mkdir()
    (td / ".agent-loop" / "loop-state.json").write_text(
        json.dumps({
            "phase": "Phase 10 - Future Product Features",
            "sub_phase": (
                "Phase 10T - MCP Read-Only Assistance In "
                "Desktop App"
            ),
            "task": "phase-10t-test",
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
    return td


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
class ConstantsTests(unittest.TestCase):

    def test_signal_version(self) -> None:
        self.assertEqual(
            agent_loop.DESKTOP_MCP_ASSISTANCE_SIGNAL_VERSION,
            "phase-10t-v1",
        )

    def test_precedence_note_mentions_required_invariants(
        self,
    ) -> None:
        note = (
            agent_loop.DESKTOP_MCP_ASSISTANCE_PRECEDENCE_NOTE
        )
        for fragment in (
            "Phase 10O", "Phase 10S", "Phase 10I",
            "deferred_mutating_class", "Phase 10U",
            "ROADMAP.md", "NEVER spawns a subprocess",
            "NEVER opens a network socket",
            "NEVER widens the Phase 10I",
        ):
            self.assertIn(fragment, note, f"missing: {fragment!r}")

    def test_permission_classes_match_phase_10s(self) -> None:
        self.assertEqual(
            agent_loop.MCP_SERVER_PERMISSION_CLASSES,
            (
                "read_only_advisory_class",
                "browser_inspection_class",
                "deferred_mutating_class",
            ),
        )

    def test_capability_categories_match_phase_10o(self) -> None:
        self.assertEqual(
            agent_loop.MCP_SERVER_CAPABILITY_CATEGORIES,
            (
                "read_only_advisory",
                "browser_app_inspection",
                "deferred_mutating",
            ),
        )

    def test_enablement_states_closed(self) -> None:
        self.assertEqual(
            agent_loop.MCP_SERVER_ENABLEMENT_STATES,
            (
                "disabled_by_default",
                "enabled_pending_runtime",
                "refused_deferred_runtime",
            ),
        )

    def test_approval_requirements_closed(self) -> None:
        self.assertEqual(
            agent_loop.MCP_SERVER_APPROVAL_REQUIREMENTS,
            (
                "operator_acknowledged_safety_copy",
                "operator_supplied_identity",
                "approval_mode_supports_enablement",
                "phase_10t_runtime_available",
                "policy_rule_permits_enablement",
            ),
        )

    def test_strict_mode_not_in_enablement_permitted_modes(
        self,
    ) -> None:
        self.assertNotIn(
            "strict",
            agent_loop.MCP_ENABLEMENT_PERMITTED_APPROVAL_MODES,
        )
        self.assertIn(
            "review",
            agent_loop.MCP_ENABLEMENT_PERMITTED_APPROVAL_MODES,
        )
        self.assertIn(
            "autonomous",
            agent_loop.MCP_ENABLEMENT_PERMITTED_APPROVAL_MODES,
        )


# ---------------------------------------------------------------------------
# Registry shape
# ---------------------------------------------------------------------------
class RegistryShapeTests(unittest.TestCase):

    def test_registry_carries_each_permission_class(self) -> None:
        classes = {
            s["permission_class"]
            for s in agent_loop._DESKTOP_MCP_ASSISTANCE_REGISTRY
        }
        self.assertEqual(
            classes,
            set(agent_loop.MCP_SERVER_PERMISSION_CLASSES),
            "the registry must surface at least one server per "
            "permission class so the renderer / refusal-path "
            "tests can exercise every closed branch",
        )

    def test_every_registry_entry_passes_descriptor_validator(
        self,
    ) -> None:
        for spec in (
            agent_loop._DESKTOP_MCP_ASSISTANCE_REGISTRY
        ):
            try:
                agent_loop._desktop_mcp_assistance_validate_descriptor(
                    spec,
                )
            except agent_loop.HaltError as halt:
                self.fail(
                    f"registry entry id={spec.get('id')!r} fails "
                    f"validator: {halt.reason}"
                )

    def test_every_registry_entry_carries_required_fields(
        self,
    ) -> None:
        required_string = (
            "id", "display_name", "source_url",
            "permission_class", "deferred_runtime_marker",
            "refusal_reason_template",
        )
        required_list = (
            "capability_categories", "safety_copy",
            "approval_requirements", "enablement_steps",
        )
        for spec in (
            agent_loop._DESKTOP_MCP_ASSISTANCE_REGISTRY
        ):
            for f in required_string:
                self.assertIsInstance(
                    spec.get(f), str,
                    f"{spec.get('id')!r} field {f!r} not str",
                )
                self.assertTrue(spec[f])
            for f in required_list:
                self.assertIsInstance(
                    spec.get(f), (list, tuple),
                    f"{spec.get('id')!r} field {f!r} not list",
                )
                self.assertTrue(spec[f])

    def test_every_step_carries_typed_content(self) -> None:
        for spec in (
            agent_loop._DESKTOP_MCP_ASSISTANCE_REGISTRY
        ):
            for step in spec["enablement_steps"]:
                self.assertIn(
                    step["type"],
                    agent_loop.DESKTOP_RUN_PROFILE_STEP_TYPES,
                )
                self.assertIsInstance(step["content"], str)
                self.assertTrue(step["content"])

    def test_registry_ids_are_unique(self) -> None:
        ids = [
            s["id"]
            for s in agent_loop._DESKTOP_MCP_ASSISTANCE_REGISTRY
        ]
        self.assertEqual(len(ids), len(set(ids)))


# ---------------------------------------------------------------------------
# Descriptor validator
# ---------------------------------------------------------------------------
class DescriptorValidatorTests(unittest.TestCase):

    def _valid(self) -> dict:
        return {
            "id": "x", "display_name": "X",
            "source_url": "https://example.invalid/x",
            "permission_class": "read_only_advisory_class",
            "capability_categories": ("read_only_advisory",),
            "safety_copy": ("a.",),
            "approval_requirements": (
                "operator_acknowledged_safety_copy",
            ),
            "enablement_steps": (
                {"type": "manual_edit", "content": "do x"},
            ),
            "deferred_runtime_marker": "deferred to Phase 10U+",
            "refusal_reason_template": "refused",
        }

    def test_valid_passes(self) -> None:
        agent_loop._desktop_mcp_assistance_validate_descriptor(
            self._valid(),
        )

    def test_non_dict_refused(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_mcp_assistance_validate_descriptor(
                "not-a-dict",
            )

    def test_missing_required_string_field_refused(self) -> None:
        spec = self._valid()
        del spec["id"]
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop._desktop_mcp_assistance_validate_descriptor(
                spec,
            )
        self.assertIn("'id'", cm.exception.reason)

    def test_empty_required_list_field_refused(self) -> None:
        spec = self._valid()
        spec["capability_categories"] = ()
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop._desktop_mcp_assistance_validate_descriptor(
                spec,
            )
        self.assertIn("capability_categories", cm.exception.reason)

    def test_unknown_permission_class_refused(self) -> None:
        spec = self._valid()
        spec["permission_class"] = "nope_class"
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop._desktop_mcp_assistance_validate_descriptor(
                spec,
            )
        self.assertIn("permission_class", cm.exception.reason)
        self.assertIn("'nope_class'", cm.exception.reason)

    def test_unknown_capability_category_refused(self) -> None:
        spec = self._valid()
        spec["capability_categories"] = ("not_a_cat",)
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop._desktop_mcp_assistance_validate_descriptor(
                spec,
            )
        self.assertIn("capability_categories", cm.exception.reason)
        self.assertIn("'not_a_cat'", cm.exception.reason)

    def test_unknown_approval_requirement_refused(self) -> None:
        spec = self._valid()
        spec["approval_requirements"] = ("not_a_req",)
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop._desktop_mcp_assistance_validate_descriptor(
                spec,
            )
        self.assertIn("approval_requirements", cm.exception.reason)
        self.assertIn("'not_a_req'", cm.exception.reason)

    def test_unknown_step_type_refused(self) -> None:
        spec = self._valid()
        spec["enablement_steps"] = (
            {"type": "shell_exec", "content": "x"},
        )
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop._desktop_mcp_assistance_validate_descriptor(
                spec,
            )
        self.assertIn("step type", cm.exception.reason)


# ---------------------------------------------------------------------------
# Approval / enablement state computation
# ---------------------------------------------------------------------------
class EnablementStateTests(unittest.TestCase):

    def _ros(self) -> dict:
        return next(
            s for s in (
                agent_loop._DESKTOP_MCP_ASSISTANCE_REGISTRY
            ) if s["permission_class"]
            == "read_only_advisory_class"
        )

    def _bi(self) -> dict:
        return next(
            s for s in (
                agent_loop._DESKTOP_MCP_ASSISTANCE_REGISTRY
            ) if s["permission_class"]
            == "browser_inspection_class"
        )

    def _dm(self) -> dict:
        return next(
            s for s in (
                agent_loop._DESKTOP_MCP_ASSISTANCE_REGISTRY
            ) if s["permission_class"]
            == "deferred_mutating_class"
        )

    def _all_ok_approval(self) -> dict:
        return (
            agent_loop._desktop_mcp_assistance_compute_approval_state(
                self._ros(),
                approval_mode="review",
                phase_10t_runtime_available=True,
                operator_acknowledged_safety_copy=True,
                operator_supplied_identity=True,
                policy_rule_permits_enablement=True,
            )
        )

    def test_deferred_mutating_always_refuses(self) -> None:
        approval = (
            agent_loop._desktop_mcp_assistance_compute_approval_state(
                self._dm(),
                approval_mode="review",
                phase_10t_runtime_available=True,
                operator_acknowledged_safety_copy=True,
                operator_supplied_identity=True,
                policy_rule_permits_enablement=True,
            )
        )
        state, reason = (
            agent_loop._desktop_mcp_assistance_compute_enablement_state(
                self._dm(), approval_state=approval,
            )
        )
        self.assertEqual(state, "refused_deferred_runtime")
        self.assertIn("deferred_mutating_class", reason)

    def test_read_only_with_all_requirements_satisfied(
        self,
    ) -> None:
        state, _ = (
            agent_loop._desktop_mcp_assistance_compute_enablement_state(
                self._ros(),
                approval_state=self._all_ok_approval(),
            )
        )
        self.assertEqual(state, "enabled_pending_runtime")

    def test_read_only_with_unsatisfied_requirement_disabled(
        self,
    ) -> None:
        approval = (
            agent_loop._desktop_mcp_assistance_compute_approval_state(
                self._ros(),
                approval_mode="review",
                phase_10t_runtime_available=True,
                operator_acknowledged_safety_copy=False,
                operator_supplied_identity=True,
                policy_rule_permits_enablement=True,
            )
        )
        state, reason = (
            agent_loop._desktop_mcp_assistance_compute_enablement_state(
                self._ros(), approval_state=approval,
            )
        )
        self.assertEqual(state, "disabled_by_default")
        self.assertIn(
            "operator_acknowledged_safety_copy", reason,
        )

    def test_strict_mode_disables_read_only(self) -> None:
        approval = (
            agent_loop._desktop_mcp_assistance_compute_approval_state(
                self._ros(),
                approval_mode="strict",
                phase_10t_runtime_available=True,
                operator_acknowledged_safety_copy=True,
                operator_supplied_identity=True,
                policy_rule_permits_enablement=True,
            )
        )
        self.assertFalse(
            approval[
                "approval_mode_supports_enablement"
            ]["satisfied"],
        )
        state, reason = (
            agent_loop._desktop_mcp_assistance_compute_enablement_state(
                self._ros(), approval_state=approval,
            )
        )
        self.assertEqual(state, "disabled_by_default")
        self.assertIn(
            "approval_mode_supports_enablement", reason,
        )

    def test_runtime_unavailable_disables(self) -> None:
        approval = (
            agent_loop._desktop_mcp_assistance_compute_approval_state(
                self._bi(),
                approval_mode="review",
                phase_10t_runtime_available=False,
                operator_acknowledged_safety_copy=True,
                operator_supplied_identity=True,
                policy_rule_permits_enablement=True,
            )
        )
        state, _ = (
            agent_loop._desktop_mcp_assistance_compute_enablement_state(
                self._bi(), approval_state=approval,
            )
        )
        self.assertEqual(state, "disabled_by_default")

    def test_policy_rule_refusal_disables(self) -> None:
        approval = (
            agent_loop._desktop_mcp_assistance_compute_approval_state(
                self._bi(),
                approval_mode="review",
                phase_10t_runtime_available=True,
                operator_acknowledged_safety_copy=True,
                operator_supplied_identity=True,
                policy_rule_permits_enablement=False,
            )
        )
        state, reason = (
            agent_loop._desktop_mcp_assistance_compute_enablement_state(
                self._bi(), approval_state=approval,
            )
        )
        self.assertEqual(state, "disabled_by_default")
        self.assertIn(
            "policy_rule_permits_enablement", reason,
        )


# ---------------------------------------------------------------------------
# build_desktop_mcp_assistance_view
# ---------------------------------------------------------------------------
class BuildMcpAssistanceViewTests(unittest.TestCase):

    def test_view_shape(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_mcp_assistance_view(
                    controller,
                )
            )
            self.assertEqual(
                view["view_signal_version"], "phase-10t-v1",
            )
            for key in (
                "controller_path_canonical",
                "current_loop_state_status",
                "controller_loop_state_approval_mode",
                "phase_10t_runtime_available",
                "phase_10u_runtime_available",
                "permission_classes",
                "capability_categories",
                "enablement_states",
                "approval_requirements",
                "servers", "precedence_note",
            ):
                self.assertIn(key, view)
            self.assertTrue(view["phase_10t_runtime_available"])
            self.assertFalse(view["phase_10u_runtime_available"])

    def test_view_carries_one_descriptor_per_registry_entry(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_mcp_assistance_view(
                    controller,
                )
            )
            self.assertEqual(
                len(view["servers"]),
                len(agent_loop._DESKTOP_MCP_ASSISTANCE_REGISTRY),
            )

    def test_deferred_mutating_descriptor_refused_in_view(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_mcp_assistance_view(
                    controller,
                )
            )
            deferred = [
                s for s in view["servers"]
                if s["permission_class"]
                == "deferred_mutating_class"
            ]
            self.assertTrue(deferred)
            for s in deferred:
                self.assertEqual(
                    s["enablement_state"],
                    "refused_deferred_runtime",
                )

    def test_read_only_descriptors_disabled_until_operator_inputs(
        self,
    ) -> None:
        # Phase 10T fix cycle: with no per-session operator
        # inputs supplied the read-only servers stay
        # `disabled_by_default` because the operator-supplied-
        # identity / safety-copy-acknowledgement requirements
        # are unsatisfied. This anchors the fail-CLOSED default;
        # the `..._with_full_operator_inputs` test below proves
        # the surface ACTUALLY exposes a selectable path once
        # the operator supplies the required per-session inputs.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_mcp_assistance_view(
                    controller,
                )
            )
            ros = [
                s for s in view["servers"]
                if s["permission_class"]
                == "read_only_advisory_class"
            ]
            for s in ros:
                self.assertEqual(
                    s["enablement_state"],
                    "disabled_by_default",
                )

    def test_read_only_path_selectable_with_full_operator_inputs(
        self,
    ) -> None:
        # Phase 10T fix cycle (the headline bug fix): the
        # shipped bounded Phase 10T surface MUST expose a
        # selectable read-only MCP assistance path once the
        # operator explicitly supplies their identity AND
        # acknowledges the per-server safety copy this session.
        # Without this coverage the previous slice could ship
        # with every read-only button permanently disabled.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_mcp_assistance_view(
                    controller,
                    operator_inputs={
                        "identity": "tester",
                        "acknowledged_server_ids": frozenset({
                            "local_repo_docs",
                            "local_browser_inspector",
                        }),
                    },
                )
            )
            ros = [
                s for s in view["servers"]
                if s["permission_class"]
                == "read_only_advisory_class"
            ]
            self.assertTrue(ros)
            for s in ros:
                self.assertEqual(
                    s["enablement_state"],
                    "enabled_pending_runtime",
                    (
                        f"server {s['id']!r} should flip to "
                        f"enabled_pending_runtime when identity "
                        f"and acknowledgement are supplied"
                    ),
                )
            bi = [
                s for s in view["servers"]
                if s["permission_class"]
                == "browser_inspection_class"
            ]
            self.assertTrue(bi)
            for s in bi:
                self.assertEqual(
                    s["enablement_state"],
                    "enabled_pending_runtime",
                )

    def test_deferred_mutating_remains_refused_with_full_inputs(
        self,
    ) -> None:
        # Phase 10S Deferred Mutation-Capable Tool Boundary
        # MUST hold even when every operator-side requirement
        # is satisfied; the deferred-mutating short-circuit is
        # not bypassable via operator inputs.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_mcp_assistance_view(
                    controller,
                    operator_inputs={
                        "identity": "tester",
                        "acknowledged_server_ids": frozenset({
                            "local_repo_docs",
                            "local_browser_inspector",
                            "github_pr_comment_poster",
                        }),
                    },
                )
            )
            deferred = [
                s for s in view["servers"]
                if s["permission_class"]
                == "deferred_mutating_class"
            ]
            self.assertTrue(deferred)
            for s in deferred:
                self.assertEqual(
                    s["enablement_state"],
                    "refused_deferred_runtime",
                    (
                        f"server {s['id']!r} must remain refused "
                        f"even when every operator input is "
                        f"supplied; the Phase 10S deferred-"
                        f"mutating boundary is NOT bypassable "
                        f"via operator inputs"
                    ),
                )

    def test_acknowledgement_alone_without_identity_stays_disabled(
        self,
    ) -> None:
        # Partial inputs MUST not flip the server to enabled
        # (every Phase 10S approval requirement must hold).
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_mcp_assistance_view(
                    controller,
                    operator_inputs={
                        "identity": "",
                        "acknowledged_server_ids": frozenset({
                            "local_repo_docs",
                        }),
                    },
                )
            )
            s = next(
                s for s in view["servers"]
                if s["id"] == "local_repo_docs"
            )
            self.assertEqual(
                s["enablement_state"],
                "disabled_by_default",
            )

    def test_per_server_acknowledgement_is_isolated(
        self,
    ) -> None:
        # Acknowledging one server MUST NOT cascade to other
        # servers; the per-server safety-copy ack is bound to
        # the specific server id.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_mcp_assistance_view(
                    controller,
                    operator_inputs={
                        "identity": "tester",
                        "acknowledged_server_ids": frozenset({
                            "local_repo_docs",
                        }),
                    },
                )
            )
            acked = next(
                s for s in view["servers"]
                if s["id"] == "local_repo_docs"
            )
            other = next(
                s for s in view["servers"]
                if s["id"] == "local_browser_inspector"
            )
            self.assertEqual(
                acked["enablement_state"],
                "enabled_pending_runtime",
            )
            self.assertEqual(
                other["enablement_state"],
                "disabled_by_default",
            )

    def test_policy_refusal_disables_targeted_server_only(
        self,
    ) -> None:
        # Operator-side additive policy refusal MUST refuse the
        # targeted server even when every other requirement is
        # satisfied, and MUST NOT cascade to non-targeted
        # servers.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_mcp_assistance_view(
                    controller,
                    operator_inputs={
                        "identity": "tester",
                        "acknowledged_server_ids": frozenset({
                            "local_repo_docs",
                            "local_browser_inspector",
                        }),
                        "policy_refused_server_ids": frozenset({
                            "local_repo_docs",
                        }),
                    },
                )
            )
            refused = next(
                s for s in view["servers"]
                if s["id"] == "local_repo_docs"
            )
            other = next(
                s for s in view["servers"]
                if s["id"] == "local_browser_inspector"
            )
            self.assertEqual(
                refused["enablement_state"],
                "disabled_by_default",
            )
            self.assertEqual(
                other["enablement_state"],
                "enabled_pending_runtime",
            )

    def test_operator_inputs_mirror_in_view(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_mcp_assistance_view(
                    controller,
                    operator_inputs={
                        "identity": "  tester  ",
                        "acknowledged_server_ids": (
                            "local_repo_docs",
                        ),
                        "policy_refused_server_ids": [],
                    },
                )
            )
            self.assertIn("operator_inputs", view)
            mirror = view["operator_inputs"]
            self.assertEqual(mirror["identity"], "tester")
            self.assertEqual(
                mirror["acknowledged_server_ids"],
                ["local_repo_docs"],
            )
            self.assertEqual(
                mirror["policy_refused_server_ids"], [],
            )

    def test_operator_inputs_normalizer_refuses_non_dict(
        self,
    ) -> None:
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_mcp_assistance_normalize_operator_inputs(
                "not-a-dict",
            )

    def test_operator_inputs_normalizer_refuses_bad_identity(
        self,
    ) -> None:
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_mcp_assistance_normalize_operator_inputs(
                {"identity": 42},
            )

    def test_loop_state_halt_soft_fails(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            with mock.patch.object(
                agent_loop, "load_loop_state",
                side_effect=agent_loop.HaltError(
                    "halted_input_missing", "synthetic halt",
                ),
            ):
                view = (
                    agent_loop
                    .build_desktop_mcp_assistance_view(controller)
                )
            self.assertIsNone(view["current_loop_state_status"])
            self.assertIsNone(
                view["controller_loop_state_approval_mode"],
            )
            # The selection UX must still render every descriptor
            # (just with the approval_mode requirement reported as
            # unsatisfied because the mode is unknown).
            self.assertEqual(
                len(view["servers"]),
                len(agent_loop._DESKTOP_MCP_ASSISTANCE_REGISTRY),
            )

    def test_strict_mode_disables_every_non_deferred_server(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(
                Path(td) / "c", approval_mode="strict",
            )
            view = (
                agent_loop.build_desktop_mcp_assistance_view(
                    controller,
                )
            )
            for s in view["servers"]:
                if (
                    s["permission_class"]
                    == "deferred_mutating_class"
                ):
                    self.assertEqual(
                        s["enablement_state"],
                        "refused_deferred_runtime",
                    )
                else:
                    self.assertEqual(
                        s["enablement_state"],
                        "disabled_by_default",
                    )

    def test_invalid_registry_entry_refuses_fail_closed(
        self,
    ) -> None:
        # If a registry entry ever drifts to a wrong shape the
        # validator MUST raise; the view builder calls the
        # validator on every descriptor.
        bad = ({"id": "x"},)  # missing every other required field
        with mock.patch.object(
            agent_loop,
            "_DESKTOP_MCP_ASSISTANCE_REGISTRY",
            bad,
        ):
            with TemporaryDirectory() as td:
                controller = _make_controller(Path(td) / "c")
                with self.assertRaises(agent_loop.HaltError):
                    agent_loop.build_desktop_mcp_assistance_view(
                        controller,
                    )


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------
class RenderMcpAssistanceTextTests(unittest.TestCase):

    def _view(self) -> dict:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            return (
                agent_loop.build_desktop_mcp_assistance_view(
                    controller,
                )
            )

    def test_header_signal_version(self) -> None:
        lines = (
            agent_loop.render_desktop_mcp_assistance_text(
                self._view(),
            )
        )
        self.assertTrue(any(
            "[desktop-mcp-assistance] view" in line
            and "phase-10t-v1" in line
            for line in lines
        ))

    def test_renders_per_line_tags(self) -> None:
        text = "\n".join(
            agent_loop.render_desktop_mcp_assistance_text(
                self._view(),
            )
        )
        for fragment in (
            "[canonical mirror] current_loop_state_status",
            "[advisory] permission_classes",
            "[advisory] capability_categories",
            "[advisory] enablement_states",
            "[advisory] approval_requirements",
            "[mcp-approval] operator_inputs.identity",
            "[mcp-approval] operator_inputs."
            "acknowledged_server_ids",
            "[mcp-approval] operator_inputs."
            "policy_refused_server_ids",
            "[mcp-server] id=",
            "[mcp-capability] [capability: read-only-advisory]",
            "[mcp-safety] 1.",
            "[mcp-enablement] enablement_reason:",
            "[deferred-runtime] deferred_runtime_marker:",
        ):
            self.assertIn(fragment, text)

    def test_renders_refused_tag_for_deferred_mutating(
        self,
    ) -> None:
        text = "\n".join(
            agent_loop.render_desktop_mcp_assistance_text(
                self._view(),
            )
        )
        self.assertIn("[refused]", text)
        self.assertIn("'refused_deferred_runtime'", text)

    def test_precedence_note_is_last_line(self) -> None:
        lines = (
            agent_loop.render_desktop_mcp_assistance_text(
                self._view(),
            )
        )
        self.assertTrue(
            lines[-1].startswith("precedence_note:"),
        )

    def test_renders_typed_steps_with_tags(self) -> None:
        text = "\n".join(
            agent_loop.render_desktop_mcp_assistance_text(
                self._view(),
            )
        )
        self.assertIn("[manual-edit]", text)


# ---------------------------------------------------------------------------
# Controls (Tk widget descriptors)
# ---------------------------------------------------------------------------
class BuildMcpAssistanceControlsTests(unittest.TestCase):

    def _view(self) -> dict:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            return (
                agent_loop.build_desktop_mcp_assistance_view(
                    controller,
                )
            )

    def test_controls_match_server_count(self) -> None:
        view = self._view()
        controls = (
            agent_loop.build_desktop_mcp_assistance_controls(view)
        )
        self.assertEqual(len(controls), len(view["servers"]))

    def test_each_control_carries_required_fields(self) -> None:
        required = {
            "id", "label", "enabled", "permission_class",
            "enablement_state", "enablement_reason",
            "clipboard_payload", "deferred_runtime_marker",
            "refusal_reason_template", "dispatch_mode",
            "category",
        }
        for c in (
            agent_loop.build_desktop_mcp_assistance_controls(
                self._view(),
            )
        ):
            missing = required - set(c.keys())
            self.assertEqual(missing, set(), f"control: {c}")

    def test_deferred_mutating_controls_always_disabled(
        self,
    ) -> None:
        for c in (
            agent_loop.build_desktop_mcp_assistance_controls(
                self._view(),
            )
        ):
            if (
                c["permission_class"]
                == "deferred_mutating_class"
            ):
                self.assertFalse(c["enabled"])
                self.assertEqual(
                    c["enablement_state"],
                    "refused_deferred_runtime",
                )

    def test_clipboard_payload_per_line_tagged(self) -> None:
        for c in (
            agent_loop.build_desktop_mcp_assistance_controls(
                self._view(),
            )
        ):
            for line in c["clipboard_payload"].splitlines():
                self.assertTrue(
                    line.startswith("[cli]")
                    or line.startswith("[manual-edit]"),
                    f"payload line {line!r} missing step tag",
                )

    def test_empty_input_returns_empty_controls(self) -> None:
        self.assertEqual(
            agent_loop.build_desktop_mcp_assistance_controls(
                {"servers": []},
            ),
            [],
        )
        self.assertEqual(
            agent_loop.build_desktop_mcp_assistance_controls({}),
            [],
        )

    def test_controls_enable_read_only_with_operator_inputs(
        self,
    ) -> None:
        # Phase 10T fix cycle: prove the shipped Tk button row
        # actually exposes a clickable read-only enablement
        # affordance once operator inputs are supplied; without
        # this coverage the prior slice could ship with every
        # read-only button permanently disabled.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_mcp_assistance_view(
                    controller,
                    operator_inputs={
                        "identity": "tester",
                        "acknowledged_server_ids": frozenset({
                            "local_repo_docs",
                            "local_browser_inspector",
                        }),
                    },
                )
            )
            controls = (
                agent_loop
                .build_desktop_mcp_assistance_controls(view)
            )
            by_id = {c["id"]: c for c in controls}
            self.assertTrue(by_id["local_repo_docs"]["enabled"])
            self.assertTrue(
                by_id["local_browser_inspector"]["enabled"],
            )
            self.assertFalse(
                by_id["github_pr_comment_poster"]["enabled"],
                "deferred-mutating MUST stay disabled even when "
                "operator inputs are supplied",
            )


# ---------------------------------------------------------------------------
# CLI handler
# ---------------------------------------------------------------------------
class CmdViewDesktopMcpAssistanceTests(unittest.TestCase):

    def test_omitted_controller_root_refuses(self) -> None:
        args = argparse.Namespace(
            cmd="view-desktop-mcp-assistance",
            controller_root=None,
        )
        err = io.StringIO()
        with redirect_stderr(err):
            rc = (
                agent_loop
                .cmd_view_desktop_mcp_assistance(args)
            )
        self.assertEqual(rc, 2)
        self.assertIn("REFUSED", err.getvalue())
        self.assertIn("--controller-root", err.getvalue())

    def test_invalid_controller_root_refuses_with_markers(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            args = argparse.Namespace(
                cmd="view-desktop-mcp-assistance",
                controller_root=str(Path(td)),
            )
            err = io.StringIO()
            with redirect_stderr(err):
                rc = (
                    agent_loop
                    .cmd_view_desktop_mcp_assistance(args)
                )
            self.assertEqual(rc, 2)
            self.assertIn("REFUSED", err.getvalue())
            self.assertIn("AGENTS.md", err.getvalue())

    def test_valid_controller_root_exits_zero_and_prints_view(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            args = argparse.Namespace(
                cmd="view-desktop-mcp-assistance",
                controller_root=str(controller),
            )
            out = io.StringIO()
            with redirect_stdout(out):
                rc = (
                    agent_loop
                    .cmd_view_desktop_mcp_assistance(args)
                )
            self.assertEqual(rc, 0)
            self.assertIn(
                "[desktop-mcp-assistance] view",
                out.getvalue(),
            )

    def test_handler_registered(self) -> None:
        self.assertIn(
            "view-desktop-mcp-assistance",
            agent_loop.HANDLERS,
        )
        self.assertIs(
            agent_loop.HANDLERS[
                "view-desktop-mcp-assistance"
            ],
            agent_loop.cmd_view_desktop_mcp_assistance,
        )

    def test_parser_accepts_subcommand(self) -> None:
        parser = agent_loop.build_parser()
        args = parser.parse_args([
            "view-desktop-mcp-assistance",
            "--controller-root", "/tmp/nope",
        ])
        self.assertEqual(
            args.cmd, "view-desktop-mcp-assistance",
        )
        self.assertEqual(args.controller_root, "/tmp/nope")

    def test_parser_accepts_operator_input_flags(self) -> None:
        # Phase 10T fix cycle: the CLI MUST accept per-session
        # operator-input flags so the operator can flip read-
        # only servers from `disabled_by_default` to
        # `enabled_pending_runtime` without persisting state.
        parser = agent_loop.build_parser()
        args = parser.parse_args([
            "view-desktop-mcp-assistance",
            "--controller-root", "/tmp/nope",
            "--operator-identity", "yoomin",
            "--acknowledge-server", "local_repo_docs",
            "--acknowledge-server", "local_browser_inspector",
            "--policy-refuse-server",
            "local_browser_inspector",
        ])
        self.assertEqual(args.operator_identity, "yoomin")
        self.assertEqual(
            args.acknowledge_server,
            ["local_repo_docs", "local_browser_inspector"],
        )
        self.assertEqual(
            args.policy_refuse_server,
            ["local_browser_inspector"],
        )

    def test_cli_flags_flip_read_only_server_to_enabled(
        self,
    ) -> None:
        # End-to-end: parser + handler must thread the flags
        # through so the rendered view shows the read-only
        # server as `enabled_pending_runtime` while the
        # deferred-mutating server stays refused.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            parser = agent_loop.build_parser()
            args = parser.parse_args([
                "view-desktop-mcp-assistance",
                "--controller-root", str(controller),
                "--operator-identity", "yoomin",
                "--acknowledge-server", "local_repo_docs",
            ])
            out = io.StringIO()
            with redirect_stdout(out):
                rc = (
                    agent_loop
                    .cmd_view_desktop_mcp_assistance(args)
                )
            self.assertEqual(rc, 0)
            text = out.getvalue()
            self.assertIn(
                "id='local_repo_docs' display_name='Local Repo "
                "Docs (read-only advisory)' "
                "permission_class='read_only_advisory_class' "
                "enablement_state='enabled_pending_runtime'",
                text,
            )
            self.assertIn(
                "id='github_pr_comment_poster' "
                "display_name='GitHub PR Comment Poster "
                "(deferred mutation-capable)' "
                "permission_class='deferred_mutating_class' "
                "enablement_state='refused_deferred_runtime'",
                text,
            )


# ---------------------------------------------------------------------------
# Integration into the Phase 10M desktop app view
# ---------------------------------------------------------------------------
class DesktopAppViewIncludesMcpAssistanceTests(
    unittest.TestCase,
):

    def test_assemble_includes_mcp_assistance_view_key(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.assemble_desktop_app_view(
                controller,
            )
            self.assertIn("mcp_assistance_view", view)
            mv = view["mcp_assistance_view"]
            self.assertIsInstance(mv, dict)
            self.assertEqual(
                mv["view_signal_version"],
                agent_loop.DESKTOP_MCP_ASSISTANCE_SIGNAL_VERSION,
            )

    def test_assemble_delegates_to_build_mcp_assistance_view(
        self,
    ) -> None:
        sentinel = {
            "view_signal_version": "phase-10t-v1",
            "_sentinel": "mcp_assistance",
            "controller_path_canonical": "/tmp/c",
            "current_loop_state_status": None,
            "controller_loop_state_approval_mode": None,
            "phase_10t_runtime_available": True,
            "phase_10u_runtime_available": False,
            "permission_classes": [],
            "capability_categories": [],
            "enablement_states": [],
            "approval_requirements": [],
            "servers": [],
            "precedence_note": "x",
        }
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            with mock.patch.object(
                agent_loop,
                "build_desktop_mcp_assistance_view",
                return_value=sentinel,
            ):
                view = agent_loop.assemble_desktop_app_view(
                    controller,
                )
            self.assertIs(view["mcp_assistance_view"], sentinel)

    def test_render_includes_mcp_assistance_phase_10t_label(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.assemble_desktop_app_view(
                controller,
            )
            lines = agent_loop.render_desktop_app_text(view)
            output = "\n".join(lines)
            self.assertIn("MCP Assistance (Phase 10T)", output)
            self.assertIn(
                "[desktop-mcp-assistance] view "
                "(signal_version='phase-10t-v1')",
                output,
            )

    def test_halt_does_not_break_other_sub_views(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")

            def _raise_halt(_root, *args, **kwargs):
                raise agent_loop.HaltError(
                    "halted_input_missing", "mcp halt",
                )

            with mock.patch.object(
                agent_loop,
                "build_desktop_mcp_assistance_view",
                side_effect=_raise_halt,
            ):
                view = agent_loop.assemble_desktop_app_view(
                    controller,
                )
            self.assertIsNone(
                view["mcp_assistance_view"]["view"],
            )
            self.assertIn(
                "mcp halt",
                view["mcp_assistance_view"]["error"],
            )
            for key in (
                "status_view", "controls_view",
                "dashboard_view", "setup_view",
                "run_profiles_view", "project_start_view",
            ):
                self.assertIn(
                    "view_signal_version", view[key],
                )


# ---------------------------------------------------------------------------
# Non-mutation invariants
# ---------------------------------------------------------------------------
class NonMutationInvariantsTests(unittest.TestCase):

    def test_build_does_not_mutate_loop_state(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            state_path = (
                controller / ".agent-loop" / "loop-state.json"
            )
            before = state_path.read_text(encoding="utf-8")
            agent_loop.build_desktop_mcp_assistance_view(
                controller,
            )
            after = state_path.read_text(encoding="utf-8")
            self.assertEqual(before, after)

    def test_build_does_not_write_orchestrator_log(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            log_path = (
                controller / ".agent-loop" / "orchestrator.log"
            )
            self.assertFalse(log_path.exists())
            agent_loop.build_desktop_mcp_assistance_view(
                controller,
            )
            self.assertFalse(log_path.exists())

    def test_build_does_not_invoke_halt(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            calls = []

            def _record(*args, **kwargs):
                calls.append((args, kwargs))
                return -1

            with mock.patch.object(agent_loop, "_halt", _record):
                agent_loop.build_desktop_mcp_assistance_view(
                    controller,
                )
            self.assertEqual(calls, [])

    def test_build_does_not_create_canonical_artifact(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            for rel in (
                agent_loop.EXTERNAL_TARGET_ATTACH_RECORD_REL,
                ".agent-loop/claude-prompt.md",
                ".agent-loop/current-task.md",
                ".agent-loop/current-phase.md",
                ".agent-loop/runtime-config.json",
                ".agent-loop/proposed-phase.md",
                ".agent-loop/prd-intake.json",
            ):
                self.assertFalse(
                    (controller / rel).exists(),
                    f"{rel} exists pre-build; test leak",
                )
            before_task = (
                controller / "TASK.md"
            ).read_text(encoding="utf-8")
            agent_loop.build_desktop_mcp_assistance_view(
                controller,
            )
            for rel in (
                agent_loop.EXTERNAL_TARGET_ATTACH_RECORD_REL,
                ".agent-loop/claude-prompt.md",
                ".agent-loop/current-task.md",
                ".agent-loop/current-phase.md",
                ".agent-loop/runtime-config.json",
                ".agent-loop/proposed-phase.md",
                ".agent-loop/prd-intake.json",
            ):
                self.assertFalse(
                    (controller / rel).exists(),
                    f"{rel} created by Phase 10T",
                )
            after_task = (
                controller / "TASK.md"
            ).read_text(encoding="utf-8")
            self.assertEqual(before_task, after_task)

    def test_cli_does_not_spawn_subprocess(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            args = argparse.Namespace(
                cmd="view-desktop-mcp-assistance",
                controller_root=str(controller),
            )
            spawn_calls = []

            def _record(*args, **kwargs):
                spawn_calls.append((args, kwargs))
                raise RuntimeError(
                    "Phase 10L contract violation: MCP "
                    "assistance surface must NOT spawn a "
                    "subprocess"
                )

            patches = [
                mock.patch(
                    "subprocess.Popen", side_effect=_record,
                ),
                mock.patch(
                    "subprocess.run", side_effect=_record,
                ),
                mock.patch(
                    "subprocess.call", side_effect=_record,
                ),
                mock.patch(
                    "subprocess.check_call",
                    side_effect=_record,
                ),
                mock.patch(
                    "subprocess.check_output",
                    side_effect=_record,
                ),
                mock.patch("os.system", side_effect=_record),
            ]
            for p in patches:
                p.start()
            try:
                with redirect_stdout(io.StringIO()):
                    rc = (
                        agent_loop
                        .cmd_view_desktop_mcp_assistance(args)
                    )
            finally:
                for p in patches:
                    p.stop()
            self.assertEqual(rc, 0)
            self.assertEqual(spawn_calls, [])

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
            "Phase 10T MUST NOT widen the Phase 10I library-"
            "callable control surface beyond the three shipped "
            "controls",
        )

    def test_build_does_not_open_a_network_socket(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            import socket
            calls = []
            real_socket = socket.socket

            def _record(*args, **kwargs):
                calls.append((args, kwargs))
                return real_socket(*args, **kwargs)

            with mock.patch.object(
                socket, "socket", side_effect=_record,
            ):
                agent_loop.build_desktop_mcp_assistance_view(
                    controller,
                )
            self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
