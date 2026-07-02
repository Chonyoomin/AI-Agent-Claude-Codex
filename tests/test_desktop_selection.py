"""Phase 10Z - Model, Policy Pack, And Template Selection UX tests.

Exercises:
  - module-level constants (signal version, precedence note,
    closed enumerations)
  - operator-input normalizer
  - closed selection registry + descriptor validator
  - approval-state / enablement-state helpers
  - `build_desktop_selection_view(...)` shape + soft-fail on
    missing loop-state + fail-closed default (every preset
    surfaces as `refused_until_policy_update`)
  - renderer per-line attribution
  - `build_desktop_selection_controls(...)` widget shape
    (COPY-PASTE only; every button disabled by contract)
  - `cmd_view_desktop_selection(...)` CLI handler + Phase 7C
    exit-0 pattern
  - integration into `assemble_desktop_app_view(...)` +
    `render_desktop_app_text(...)`
  - non-mutation invariants (no socket, no subprocess, no
    orchestrator.log append, no loop-state mutation, no
    `_halt(...)`, no Phase 10I library-callable cap widening,
    no persisted selection cache)
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
                "Phase 10Z - Model, Policy Pack, And Template "
                "Selection UX"
            ),
            "task": "phase-10z-test",
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
            agent_loop.DESKTOP_SELECTION_SIGNAL_VERSION,
            "phase-10z-v1",
        )

    def test_precedence_note_pins_phase_10z_contract(self) -> None:
        note = agent_loop.DESKTOP_SELECTION_PRECEDENCE_NOTE
        for needle in (
            "Phase 10Z",
            "SELECTION-CONTRACT SLICE",
            "Phase 10I",
            "refused_until_policy_update",
            "NEVER mutates any canonical artifact",
            "NEVER spawns a subprocess",
            "NEVER opens a network socket",
            "NEVER writes a selection cache",
            "NEVER refreshes a preset from a hosted service",
        ):
            self.assertIn(needle, note, needle)

    def test_preset_categories_closed_enum(self) -> None:
        self.assertEqual(
            agent_loop.SELECTION_PRESET_CATEGORIES,
            ("model", "policy_pack", "project_template"),
        )

    def test_enablement_states_closed_enum(self) -> None:
        self.assertEqual(
            agent_loop.SELECTION_ENABLEMENT_STATES,
            (
                "disabled_by_default",
                "enabled_pending_runtime",
                "refused_until_policy_update",
            ),
        )

    def test_approval_requirements_closed_enum(self) -> None:
        self.assertEqual(
            agent_loop.SELECTION_APPROVAL_REQUIREMENTS,
            (
                "operator_acknowledged_preset_scope",
                "operator_supplied_identity",
                "approval_mode_supports_selection",
                "phase_10z_runtime_available",
                "policy_rule_permits_selection",
            ),
        )

    def test_refusal_reasons_closed_enum(self) -> None:
        self.assertEqual(
            agent_loop.SELECTION_REFUSAL_REASONS,
            (
                "approval_mode_strict",
                "operator_identity_missing",
                "operator_acknowledgement_missing",
                "policy_rule_refuses_selection",
                "runtime_not_available",
            ),
        )

    def test_permitted_approval_modes(self) -> None:
        self.assertEqual(
            agent_loop.SELECTION_PERMITTED_APPROVAL_MODES,
            frozenset({"review", "autonomous"}),
        )


# ---------------------------------------------------------------------------
# Registry + descriptor validator
# ---------------------------------------------------------------------------
class RegistryTests(unittest.TestCase):

    def test_registry_ships_three_presets(self) -> None:
        self.assertEqual(
            len(agent_loop._DESKTOP_SELECTION_REGISTRY), 3,
        )

    def test_registry_covers_every_closed_category(self) -> None:
        categories = {
            spec["preset_category"]
            for spec in agent_loop._DESKTOP_SELECTION_REGISTRY
        }
        self.assertEqual(
            categories,
            set(agent_loop.SELECTION_PRESET_CATEGORIES),
        )

    def test_every_registry_entry_passes_validator(self) -> None:
        for spec in agent_loop._DESKTOP_SELECTION_REGISTRY:
            agent_loop._desktop_selection_validate_descriptor(spec)


class ValidatorTests(unittest.TestCase):

    def _valid(self):
        return {
            "id": "x",
            "display_name": "X",
            "preset_category": "model",
            "preset_summary": "s",
            "safety_copy": "c",
            "approval_requirements": (
                "operator_acknowledged_preset_scope",
            ),
            "deferred_runtime_marker": "m",
            "refusal_reason_template": "t",
        }

    def test_missing_field_refuses(self) -> None:
        spec = self._valid()
        del spec["preset_category"]
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_selection_validate_descriptor(spec)

    def test_unknown_category_refuses(self) -> None:
        spec = self._valid()
        spec["preset_category"] = "not_a_category"
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_selection_validate_descriptor(spec)

    def test_unknown_approval_requirement_refuses(self) -> None:
        spec = self._valid()
        spec["approval_requirements"] = ("not_a_requirement",)
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_selection_validate_descriptor(spec)

    def test_non_tuple_approval_requirements_refuses(self) -> None:
        spec = self._valid()
        spec["approval_requirements"] = [
            "operator_acknowledged_preset_scope",
        ]
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_selection_validate_descriptor(spec)


# ---------------------------------------------------------------------------
# Operator-input normalizer
# ---------------------------------------------------------------------------
class OperatorInputsNormalizerTests(unittest.TestCase):

    def test_none_returns_empty_defaults(self) -> None:
        got = (
            agent_loop._desktop_selection_normalize_operator_inputs(
                None,
            )
        )
        self.assertEqual(got["identity"], "")
        self.assertEqual(got["acknowledged_preset_ids"], frozenset())
        self.assertEqual(
            got["policy_permitted_preset_ids"], frozenset(),
        )

    def test_non_dict_refuses(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_selection_normalize_operator_inputs(
                ["not", "a", "dict"],
            )

    def test_iterable_ids_normalized(self) -> None:
        got = (
            agent_loop._desktop_selection_normalize_operator_inputs(
                {
                    "identity": " me ",
                    "acknowledged_preset_ids": [
                        "shipped_default_model",
                    ],
                    "policy_permitted_preset_ids": (
                        "shipped_default_model",
                    ),
                },
            )
        )
        self.assertEqual(got["identity"], "me")
        self.assertIn(
            "shipped_default_model",
            got["acknowledged_preset_ids"],
        )
        self.assertIn(
            "shipped_default_model",
            got["policy_permitted_preset_ids"],
        )


# ---------------------------------------------------------------------------
# Approval / enablement helpers
# ---------------------------------------------------------------------------
class ApprovalStateTests(unittest.TestCase):

    def test_all_unsatisfied_default(self) -> None:
        state = (
            agent_loop._desktop_selection_compute_approval_state(
                approval_mode=None,
                phase_10z_runtime_available=False,
                operator_acknowledged_preset_scope=False,
                operator_supplied_identity=False,
                policy_rule_permits_selection=False,
            )
        )
        for req in agent_loop.SELECTION_APPROVAL_REQUIREMENTS:
            self.assertFalse(state[req]["satisfied"], req)

    def test_strict_mode_refuses_selection(self) -> None:
        state = (
            agent_loop._desktop_selection_compute_approval_state(
                approval_mode="strict",
                phase_10z_runtime_available=True,
                operator_acknowledged_preset_scope=True,
                operator_supplied_identity=True,
                policy_rule_permits_selection=True,
            )
        )
        self.assertFalse(
            state["approval_mode_supports_selection"]["satisfied"],
        )

    def test_review_and_autonomous_modes_are_permitted(self) -> None:
        for mode in ("review", "autonomous"):
            state = (
                agent_loop._desktop_selection_compute_approval_state(
                    approval_mode=mode,
                    phase_10z_runtime_available=False,
                    operator_acknowledged_preset_scope=False,
                    operator_supplied_identity=False,
                    policy_rule_permits_selection=False,
                )
            )
            self.assertTrue(
                state["approval_mode_supports_selection"][
                    "satisfied"
                ],
                mode,
            )


class EnablementStateTests(unittest.TestCase):

    def _approval_all_true(self):
        return (
            agent_loop._desktop_selection_compute_approval_state(
                approval_mode="review",
                phase_10z_runtime_available=True,
                operator_acknowledged_preset_scope=True,
                operator_supplied_identity=True,
                policy_rule_permits_selection=True,
            )
        )

    def test_runtime_unavailable_forces_refused(self) -> None:
        state = self._approval_all_true()
        enablement, reason = (
            agent_loop._desktop_selection_compute_enablement_state(
                state, phase_10z_runtime_available=False,
            )
        )
        self.assertEqual(enablement, "refused_until_policy_update")

    def test_runtime_available_and_all_met_promotes(self) -> None:
        state = self._approval_all_true()
        enablement, _ = (
            agent_loop._desktop_selection_compute_enablement_state(
                state, phase_10z_runtime_available=True,
            )
        )
        self.assertEqual(enablement, "enabled_pending_runtime")

    def test_runtime_available_missing_requirement_disabled(
        self,
    ) -> None:
        state = (
            agent_loop._desktop_selection_compute_approval_state(
                approval_mode="review",
                phase_10z_runtime_available=True,
                operator_acknowledged_preset_scope=False,
                operator_supplied_identity=True,
                policy_rule_permits_selection=True,
            )
        )
        enablement, _ = (
            agent_loop._desktop_selection_compute_enablement_state(
                state, phase_10z_runtime_available=True,
            )
        )
        self.assertEqual(enablement, "disabled_by_default")


# ---------------------------------------------------------------------------
# build_desktop_selection_view
# ---------------------------------------------------------------------------
class BuildSelectionViewTests(unittest.TestCase):

    def test_view_shape_fields(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.build_desktop_selection_view(
                controller,
            )
        for key in (
            "view_signal_version",
            "controller_path_canonical",
            "current_loop_state_status",
            "controller_loop_state_approval_mode",
            "phase_10z_runtime_available",
            "operator_inputs",
            "preset_categories",
            "enablement_states",
            "approval_requirements",
            "refusal_reasons",
            "presets",
            "precedence_note",
        ):
            self.assertIn(key, view, key)
        self.assertEqual(
            view["view_signal_version"], "phase-10z-v1",
        )
        self.assertFalse(view["phase_10z_runtime_available"])

    def test_every_preset_refused_by_default(self) -> None:
        # Fail-closed default: since runtime is not available,
        # every preset surfaces as `refused_until_policy_update`
        # regardless of operator input.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.build_desktop_selection_view(
                controller,
                operator_inputs={
                    "identity": "me",
                    "acknowledged_preset_ids": [
                        "shipped_default_model",
                        "shipped_default_policy_pack",
                        "shipped_default_project_template",
                    ],
                    "policy_permitted_preset_ids": [
                        "shipped_default_model",
                        "shipped_default_policy_pack",
                        "shipped_default_project_template",
                    ],
                },
            )
        for preset in view["presets"]:
            self.assertEqual(
                preset["enablement_state"],
                "refused_until_policy_update",
                preset["id"],
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
            view = agent_loop.build_desktop_selection_view(
                controller,
            )
        self.assertIsNone(view["current_loop_state_status"])
        self.assertIsNone(
            view["controller_loop_state_approval_mode"],
        )

    def test_operator_inputs_mirrored_in_view(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.build_desktop_selection_view(
                controller,
                operator_inputs={
                    "identity": "me",
                    "acknowledged_preset_ids": [
                        "shipped_default_model",
                    ],
                    "policy_permitted_preset_ids": [
                        "shipped_default_model",
                    ],
                },
            )
        self.assertEqual(view["operator_inputs"]["identity"], "me")
        self.assertIn(
            "shipped_default_model",
            view["operator_inputs"]["acknowledged_preset_ids"],
        )


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------
class RendererTests(unittest.TestCase):

    def test_render_includes_attribution_tags(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.build_desktop_selection_view(
                controller,
            )
        output = "\n".join(
            agent_loop.render_desktop_selection_text(view),
        )
        for tag in (
            "phase-10z-v1",
            "[canonical mirror]",
            "[advisory]",
            "[selection]",
            "[preset-category]",
            "[preset-enablement]",
            "[deferred-runtime]",
            "[refused]",
        ):
            self.assertIn(tag, output, tag)


# ---------------------------------------------------------------------------
# build_desktop_selection_controls
# ---------------------------------------------------------------------------
class SelectionControlsBuilderTests(unittest.TestCase):

    def test_controls_one_per_preset(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.build_desktop_selection_view(
                controller,
            )
            controls = (
                agent_loop.build_desktop_selection_controls(view)
            )
        self.assertEqual(
            len(controls), len(view["presets"]),
        )
        for control in controls:
            self.assertEqual(
                control["dispatch_mode"], "copy_paste",
            )
            self.assertEqual(control["category"], "selection_ux")
            # Fail-closed default: EVERY button disabled in this
            # slice regardless of operator input.
            self.assertFalse(control["enabled"], control["id"])

    def test_clipboard_payload_is_operator_visible_template(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.build_desktop_selection_view(
                controller,
            )
            controls = (
                agent_loop.build_desktop_selection_controls(view)
            )
        for control in controls:
            payload = control["clipboard_payload"]
            self.assertIn("preset_id:", payload)
            self.assertIn(
                "requested_action: enable_pending_runtime",
                payload,
            )
            self.assertIn(
                "operator_identity: <NAME>",
                payload,
            )
            # No actual CLI invocation - the payload is a copy-
            # paste request template, not a shipped subcommand.
            self.assertNotIn(
                "python scripts/agent_loop.py", payload,
            )


# ---------------------------------------------------------------------------
# CLI handler
# ---------------------------------------------------------------------------
class CmdViewDesktopSelectionTests(unittest.TestCase):

    def _args(self, **kwargs):
        defaults = {
            "controller_root": None,
            "operator_identity": None,
            "acknowledge_preset": None,
            "policy_permit_preset": None,
        }
        defaults.update(kwargs)
        return argparse.Namespace(**defaults)

    def test_refuses_missing_controller_root(self) -> None:
        buf_err = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(buf_err):
            rc = agent_loop.cmd_view_desktop_selection(
                self._args(),
            )
        self.assertEqual(rc, 2)
        self.assertIn(
            "[desktop-selection] REFUSED", buf_err.getvalue(),
        )

    def test_refuses_invalid_controller_root(self) -> None:
        with TemporaryDirectory() as td:
            # Missing required markers -- the Phase 10L guard
            # refuses.
            buf_err = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(
                buf_err,
            ):
                rc = agent_loop.cmd_view_desktop_selection(
                    self._args(controller_root=str(td)),
                )
        self.assertEqual(rc, 2)
        self.assertIn("REFUSED", buf_err.getvalue())

    def test_phase_7c_exits_zero_on_valid_root(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            buf_out = io.StringIO()
            with redirect_stdout(buf_out):
                rc = agent_loop.cmd_view_desktop_selection(
                    self._args(controller_root=str(controller)),
                )
        self.assertEqual(rc, 0)
        self.assertIn(
            "[desktop-selection]", buf_out.getvalue(),
        )

    def test_handler_registered(self) -> None:
        self.assertIn(
            "view-desktop-selection", agent_loop.HANDLERS,
        )

    def test_parser_accepts_subcommand_and_flags(self) -> None:
        parser = agent_loop.build_parser()
        args = parser.parse_args([
            "view-desktop-selection",
            "--controller-root", ".",
            "--operator-identity", "me",
            "--acknowledge-preset", "shipped_default_model",
            "--policy-permit-preset", "shipped_default_model",
        ])
        self.assertEqual(args.cmd, "view-desktop-selection")
        self.assertEqual(args.operator_identity, "me")
        self.assertEqual(
            args.acknowledge_preset,
            ["shipped_default_model"],
        )
        self.assertEqual(
            args.policy_permit_preset,
            ["shipped_default_model"],
        )


# ---------------------------------------------------------------------------
# Integration into the Phase 10M desktop app view
# ---------------------------------------------------------------------------
class DesktopAppIntegrationTests(unittest.TestCase):

    def test_assemble_includes_selection_view_key(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.assemble_desktop_app_view(controller)
        self.assertIn("selection_view", view)
        sv = view["selection_view"]
        self.assertIsInstance(sv, dict)
        self.assertEqual(sv["view_signal_version"], "phase-10z-v1")

    def test_render_includes_phase_10z_label(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.assemble_desktop_app_view(controller)
            lines = agent_loop.render_desktop_app_text(view)
        output = "\n".join(lines)
        self.assertIn("=== Selection UX (Phase 10Z) ===", output)
        self.assertIn("phase-10z-v1", output)


# ---------------------------------------------------------------------------
# Non-mutation invariants
# ---------------------------------------------------------------------------
class NonMutationInvariantsTests(unittest.TestCase):

    def test_view_does_not_open_socket(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            with mock.patch.object(socket, "socket") as p:
                agent_loop.build_desktop_selection_view(controller)
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
                agent_loop.build_desktop_selection_view(controller)
            finally:
                for p in patches:
                    p.stop()
        for m in mocks:
            m.assert_not_called()

    def test_view_does_not_invoke_halt(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            with mock.patch.object(agent_loop, "_halt") as h:
                agent_loop.build_desktop_selection_view(controller)
        h.assert_not_called()

    def test_view_does_not_mutate_loop_state(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            ls = controller / ".agent-loop" / "loop-state.json"
            before = ls.read_bytes()
            agent_loop.build_desktop_selection_view(controller)
            after = ls.read_bytes()
        self.assertEqual(before, after)

    def test_view_does_not_append_orchestrator_log(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            log_path = (
                controller / ".agent-loop" / "orchestrator.log"
            )
            agent_loop.build_desktop_selection_view(controller)
        self.assertFalse(log_path.exists())

    def test_view_does_not_persist_selection_cache(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            before_root = sorted(
                p.name for p in controller.iterdir()
            )
            before_dot = sorted(
                p.name
                for p in (controller / ".agent-loop").iterdir()
            )
            agent_loop.build_desktop_selection_view(controller)
            after_root = sorted(
                p.name for p in controller.iterdir()
            )
            after_dot = sorted(
                p.name
                for p in (controller / ".agent-loop").iterdir()
            )
        self.assertEqual(before_root, after_root)
        self.assertEqual(before_dot, after_dot)

    def test_phase_10i_library_callable_cap_not_widened(
        self,
    ) -> None:
        # The Phase 10Z selection UX MUST NOT introduce any new
        # library-callable control. Every descriptor is
        # `dispatch_mode='copy_paste'`.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.build_desktop_selection_view(
                controller,
            )
            controls = (
                agent_loop.build_desktop_selection_controls(view)
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
