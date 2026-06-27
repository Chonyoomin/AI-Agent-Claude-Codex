"""Phase 10Q - Desktop App Run Profiles And Approval Controls
tests.

Exercises:
  - module-level constants (signal version, precedence note,
    dimension id tuple, affordance id tuple)
  - the closed `_DESKTOP_RUN_PROFILE_AFFORDANCES` registry shape
  - per-affordance eligibility computation against loop-state.status
  - canonical-mirror assembly (`_desktop_run_profile_mirror`)
  - `build_desktop_run_profiles_view(...)` shape + HaltError
    soft-failure semantics on missing / malformed loop-state and
    runtime-config
  - `render_desktop_run_profiles_text(...)` attribution
  - `cmd_view_desktop_run_profiles(...)` CLI handler wiring, the
    Phase-10L-mandated `--controller-root` REQUIRED refusal, the
    missing-controller-root-markers refusal, and the Phase 7C
    always-exit-0-on-report-content rule
  - integration of the Phase 10Q view into the shipped Phase 10M
    `assemble_desktop_app_view(...)` / `render_desktop_app_text(...)`
  - non-mutation invariants required by the Phase 10L contract
    (no orchestrator.log write, no loop-state mutation, no `_halt`
    invocation, no subprocess spawn, no runtime-config rewrite,
    no Phase 10I library-callable cap widening, no network socket)
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
    max_cycles: int = 3,
    cycle_count: int = 1,
) -> Path:
    td.mkdir(parents=True, exist_ok=True)
    (td / "AGENTS.md").write_text("test\n", encoding="utf-8")
    (td / "CLAUDE.md").write_text("test\n", encoding="utf-8")
    (td / "TASK.md").write_text("# TASK.md\n", encoding="utf-8")
    (td / ".agent-loop").mkdir()
    (td / ".agent-loop" / "loop-state.json").write_text(
        json.dumps({
            "phase": "Phase 10 - Future Product Features",
            "sub_phase": (
                "Phase 10Q - Desktop App Run Profiles And "
                "Approval Controls"
            ),
            "task": "phase-10q-test",
            "status": status,
            "cycle_count": cycle_count,
            "max_cycles": max_cycles,
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
            agent_loop.DESKTOP_RUN_PROFILES_SIGNAL_VERSION,
            "phase-10q-v1",
        )

    def test_precedence_note_mentions_required_invariants(
        self,
    ) -> None:
        note = agent_loop.DESKTOP_RUN_PROFILES_PRECEDENCE_NOTE
        self.assertIn("Canonical artifacts on disk always win", note)
        self.assertIn("NEVER silently mutates", note)
        self.assertIn("approval_mode", note)
        self.assertIn("Phase 10I", note)
        self.assertIn("subprocess", note)
        self.assertIn("network socket", note)

    def test_dimension_ids_cover_required_run_profile_axes(
        self,
    ) -> None:
        ids = set(agent_loop.DESKTOP_RUN_PROFILE_DIMENSION_IDS)
        for required in (
            "approval_mode",
            "max_cycles",
            "cycle_count",
            "status",
            "runtime_adapter",
        ):
            self.assertIn(required, ids)

    def test_affordance_ids_cover_three_modes_and_two_policies(
        self,
    ) -> None:
        ids = set(agent_loop.DESKTOP_RUN_PROFILE_AFFORDANCE_IDS)
        for required in (
            "select_approval_mode_review",
            "select_approval_mode_strict",
            "select_approval_mode_autonomous",
            "set_attach_approval_mode",
            "select_run_policy_bounded",
            "select_run_policy_prd_to_completion",
        ):
            self.assertIn(required, ids)


# ---------------------------------------------------------------------------
# Affordance registry shape
# ---------------------------------------------------------------------------
class AffordanceRegistryShapeTests(unittest.TestCase):

    def test_registry_matches_id_tuple(self) -> None:
        registered_ids = tuple(
            spec["id"]
            for spec in agent_loop._DESKTOP_RUN_PROFILE_AFFORDANCES
        )
        self.assertEqual(
            registered_ids,
            agent_loop.DESKTOP_RUN_PROFILE_AFFORDANCE_IDS,
        )

    def test_every_spec_carries_required_fields(self) -> None:
        required = {
            "id", "label", "dimension", "target_value", "command",
            "dispatch_mode", "category", "eligibility_states",
            "audit_note",
        }
        for spec in agent_loop._DESKTOP_RUN_PROFILE_AFFORDANCES:
            missing = required - set(spec.keys())
            self.assertEqual(
                missing, set(),
                f"affordance {spec.get('id')!r} missing fields "
                f"{missing!r}",
            )

    def test_every_affordance_is_mutating_copy_paste(self) -> None:
        # Phase 10Q ships ZERO library-callable controls. Every
        # affordance MUST be a copy-paste-only mutating command so
        # the desktop run-profiles surface cannot silently dispatch.
        for spec in agent_loop._DESKTOP_RUN_PROFILE_AFFORDANCES:
            self.assertEqual(
                spec["dispatch_mode"], "copy_paste",
                f"{spec['id']!r} dispatch_mode is not copy_paste",
            )
            self.assertEqual(
                spec["category"], "mutating",
                f"{spec['id']!r} category is not mutating",
            )

    def test_approval_mode_affordances_route_through_plan(
        self,
    ) -> None:
        for spec in agent_loop._DESKTOP_RUN_PROFILE_AFFORDANCES:
            if spec["id"].startswith("select_approval_mode_"):
                self.assertIn("plan", spec["command"])
                self.assertIn("activate", spec["command"])

    def test_attach_affordance_uses_real_attach_external_target_grammar(
        self,
    ) -> None:
        # The attach affordance MUST match the shipped
        # `attach-external-target` parser grammar exactly (the same
        # Phase 10N fix-cycle regression: target-path /
        # attached-by / approval-mode are all REQUIRED). A
        # placeholder-substituted parse against the real
        # `build_parser()` must succeed.
        spec = next(
            s for s in agent_loop._DESKTOP_RUN_PROFILE_AFFORDANCES
            if s["id"] == "set_attach_approval_mode"
        )
        cmd = (
            spec["command"]
            .replace("<PATH>", "/tmp/target")
            .replace("<NAME>", "tester")
            .replace("<MODE>", "review")
        )
        parts = cmd.split()
        # drop the `python scripts/agent_loop.py` prefix
        argv = parts[2:]
        parser = agent_loop.build_parser()
        ns = parser.parse_args(argv)
        self.assertEqual(ns.cmd, "attach-external-target")
        self.assertEqual(ns.target_path, "/tmp/target")
        self.assertEqual(ns.attached_by, "tester")
        self.assertEqual(ns.approval_mode, "review")

    def test_run_policy_eligibility_states_match_shipped_statuses(
        self,
    ) -> None:
        bounded = next(
            s for s in agent_loop._DESKTOP_RUN_PROFILE_AFFORDANCES
            if s["id"] == "select_run_policy_bounded"
        )
        prd = next(
            s for s in agent_loop._DESKTOP_RUN_PROFILE_AFFORDANCES
            if s["id"] == "select_run_policy_prd_to_completion"
        )
        self.assertIn(
            "awaiting_claude_implementation",
            bounded["eligibility_states"],
        )
        self.assertIn(
            agent_loop.HALTED_TOKEN_EXHAUSTION,
            prd["eligibility_states"],
        )


# ---------------------------------------------------------------------------
# Eligibility computation
# ---------------------------------------------------------------------------
class EligibilityTests(unittest.TestCase):

    def test_unbounded_affordance_is_always_eligible(self) -> None:
        spec = next(
            s for s in agent_loop._DESKTOP_RUN_PROFILE_AFFORDANCES
            if s["id"] == "select_approval_mode_review"
        )
        eligible, reason = (
            agent_loop._desktop_run_profile_eligibility(
                spec, None,
            )
        )
        self.assertTrue(eligible)
        self.assertIn("operator-decision", reason)

    def test_bounded_run_eligible_at_awaiting_claude(self) -> None:
        spec = next(
            s for s in agent_loop._DESKTOP_RUN_PROFILE_AFFORDANCES
            if s["id"] == "select_run_policy_bounded"
        )
        eligible, reason = (
            agent_loop._desktop_run_profile_eligibility(
                spec, "awaiting_claude_implementation",
            )
        )
        self.assertTrue(eligible)
        self.assertIn(
            "awaiting_claude_implementation", reason,
        )

    def test_bounded_run_ineligible_at_other_status(self) -> None:
        spec = next(
            s for s in agent_loop._DESKTOP_RUN_PROFILE_AFFORDANCES
            if s["id"] == "select_run_policy_bounded"
        )
        eligible, reason = (
            agent_loop._desktop_run_profile_eligibility(
                spec, "phase_complete_awaiting_human_approval",
            )
        )
        self.assertFalse(eligible)
        self.assertIn("not in", reason)

    def test_bounded_run_ineligible_when_status_is_none(self) -> None:
        spec = next(
            s for s in agent_loop._DESKTOP_RUN_PROFILE_AFFORDANCES
            if s["id"] == "select_run_policy_bounded"
        )
        eligible, reason = (
            agent_loop._desktop_run_profile_eligibility(
                spec, None,
            )
        )
        self.assertFalse(eligible)
        self.assertIn("unavailable", reason)

    def test_prd_to_completion_eligible_at_token_exhaustion(
        self,
    ) -> None:
        spec = next(
            s for s in agent_loop._DESKTOP_RUN_PROFILE_AFFORDANCES
            if s["id"] == "select_run_policy_prd_to_completion"
        )
        eligible, _ = (
            agent_loop._desktop_run_profile_eligibility(
                spec, agent_loop.HALTED_TOKEN_EXHAUSTION,
            )
        )
        self.assertTrue(eligible)


# ---------------------------------------------------------------------------
# Mirror dict
# ---------------------------------------------------------------------------
class RunProfileMirrorTests(unittest.TestCase):

    def test_none_loop_state_returns_none_fields(self) -> None:
        mirror = agent_loop._desktop_run_profile_mirror(
            None, agent_loop.RUNTIME_ADAPTER_DEFAULT,
        )
        for canonical_key in (
            "approval_mode", "max_cycles", "cycle_count",
            "phase", "sub_phase", "task", "status",
        ):
            self.assertIsNone(mirror[canonical_key])
        self.assertEqual(
            mirror["runtime_adapter"],
            agent_loop.RUNTIME_ADAPTER_DEFAULT,
        )
        self.assertEqual(
            mirror["approval_mode_allowed_values"],
            sorted(agent_loop.ALLOWED_APPROVAL_MODES),
        )

    def test_populated_loop_state_propagates(self) -> None:
        ls = {
            "approval_mode": "strict",
            "max_cycles": 5,
            "cycle_count": 2,
            "phase": "Phase X",
            "sub_phase": "Phase X - Y",
            "task": "t",
            "status": "awaiting_claude_implementation",
        }
        mirror = agent_loop._desktop_run_profile_mirror(
            ls, agent_loop.RUNTIME_ADAPTER_LANGGRAPH,
        )
        self.assertEqual(mirror["approval_mode"], "strict")
        self.assertEqual(mirror["max_cycles"], 5)
        self.assertEqual(mirror["cycle_count"], 2)
        self.assertEqual(
            mirror["runtime_adapter"],
            agent_loop.RUNTIME_ADAPTER_LANGGRAPH,
        )


# ---------------------------------------------------------------------------
# build_desktop_run_profiles_view
# ---------------------------------------------------------------------------
class BuildRunProfilesViewTests(unittest.TestCase):

    def test_view_shape(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.build_desktop_run_profiles_view(
                controller,
            )
            self.assertEqual(
                view["view_signal_version"], "phase-10q-v1",
            )
            self.assertEqual(
                view["controller_path_canonical"],
                controller.resolve().as_posix(),
            )
            self.assertEqual(
                view["current_loop_state_status"],
                "awaiting_claude_implementation",
            )
            self.assertEqual(
                len(view["affordances"]),
                len(
                    agent_loop
                    .DESKTOP_RUN_PROFILE_AFFORDANCE_IDS
                ),
            )

    def test_mirror_reflects_canonical_loop_state(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(
                Path(td) / "c",
                approval_mode="autonomous",
                max_cycles=7,
                cycle_count=4,
            )
            view = agent_loop.build_desktop_run_profiles_view(
                controller,
            )
            self.assertEqual(
                view["mirror"]["approval_mode"], "autonomous",
            )
            self.assertEqual(view["mirror"]["max_cycles"], 7)
            self.assertEqual(view["mirror"]["cycle_count"], 4)

    def test_persisted_runtime_config_appears_in_mirror(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            agent_loop.write_runtime_config(
                controller,
                agent_loop.RUNTIME_ADAPTER_LANGGRAPH,
            )
            view = agent_loop.build_desktop_run_profiles_view(
                controller,
            )
            self.assertEqual(
                view["mirror"]["runtime_adapter"],
                agent_loop.RUNTIME_ADAPTER_LANGGRAPH,
            )

    def test_halt_in_loop_state_loader_soft_fails(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            with mock.patch.object(
                agent_loop, "load_loop_state",
                side_effect=agent_loop.HaltError(
                    "halted_input_missing", "loop-state halt",
                ),
            ):
                view = agent_loop.build_desktop_run_profiles_view(
                    controller,
                )
            self.assertIsNone(view["current_loop_state_status"])
            self.assertIsNone(view["mirror"]["approval_mode"])

    def test_halt_in_runtime_config_reader_falls_back_to_default(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            with mock.patch.object(
                agent_loop, "read_runtime_config",
                side_effect=agent_loop.HaltError(
                    "halted_input_missing", "runtime halt",
                ),
            ):
                view = agent_loop.build_desktop_run_profiles_view(
                    controller,
                )
            self.assertEqual(
                view["mirror"]["runtime_adapter"],
                agent_loop.RUNTIME_ADAPTER_DEFAULT,
            )

    def test_bounded_run_eligibility_propagates_from_status(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(
                Path(td) / "c",
                status="awaiting_claude_implementation",
            )
            view = agent_loop.build_desktop_run_profiles_view(
                controller,
            )
            bounded = next(
                a for a in view["affordances"]
                if a["id"] == "select_run_policy_bounded"
            )
            self.assertTrue(bounded["currently_eligible"])


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------
class RenderRunProfilesTextTests(unittest.TestCase):

    def _view(self) -> dict:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            return (
                agent_loop.build_desktop_run_profiles_view(
                    controller,
                )
            )

    def test_header_signal_version(self) -> None:
        lines = (
            agent_loop.render_desktop_run_profiles_text(
                self._view(),
            )
        )
        self.assertTrue(any(
            "[desktop-run-profiles] view" in line
            and "phase-10q-v1" in line
            for line in lines
        ))

    def test_canonical_mirror_attribution_appears(self) -> None:
        text = "\n".join(
            agent_loop.render_desktop_run_profiles_text(
                self._view(),
            )
        )
        for fragment in (
            "[canonical mirror] approval_mode",
            "[canonical mirror] max_cycles",
            "[canonical mirror] cycle_count",
            "[canonical mirror] phase / sub_phase / task",
            "[canonical mirror] current_loop_state_status",
            "[advisory] runtime_adapter",
        ):
            self.assertIn(fragment, text)

    def test_affordance_and_ineligible_tags(self) -> None:
        # Default state machine: bounded run is eligible
        # (awaiting_claude_implementation); prd_to_completion is
        # ineligible (not at HALTED_TOKEN_EXHAUSTION).
        text = "\n".join(
            agent_loop.render_desktop_run_profiles_text(
                self._view(),
            )
        )
        self.assertIn("[affordance]", text)
        self.assertIn("[ineligible]", text)

    def test_precedence_note_is_last_line(self) -> None:
        lines = (
            agent_loop.render_desktop_run_profiles_text(
                self._view(),
            )
        )
        self.assertTrue(
            lines[-1].startswith("precedence_note:"),
        )


# ---------------------------------------------------------------------------
# CLI handler
# ---------------------------------------------------------------------------
class CmdViewDesktopRunProfilesTests(unittest.TestCase):

    def test_omitted_controller_root_refuses(self) -> None:
        args = argparse.Namespace(
            cmd="view-desktop-run-profiles",
            controller_root=None,
        )
        err = io.StringIO()
        with redirect_stderr(err):
            rc = agent_loop.cmd_view_desktop_run_profiles(args)
        self.assertEqual(rc, 2)
        self.assertIn("REFUSED", err.getvalue())
        self.assertIn("--controller-root", err.getvalue())

    def test_invalid_controller_root_refuses_with_markers(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            args = argparse.Namespace(
                cmd="view-desktop-run-profiles",
                controller_root=str(Path(td)),
            )
            err = io.StringIO()
            with redirect_stderr(err):
                rc = agent_loop.cmd_view_desktop_run_profiles(args)
            self.assertEqual(rc, 2)
            self.assertIn("REFUSED", err.getvalue())
            self.assertIn("AGENTS.md", err.getvalue())

    def test_valid_controller_root_exits_zero_and_prints_view(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            args = argparse.Namespace(
                cmd="view-desktop-run-profiles",
                controller_root=str(controller),
            )
            out = io.StringIO()
            with redirect_stdout(out):
                rc = agent_loop.cmd_view_desktop_run_profiles(args)
            self.assertEqual(rc, 0)
            self.assertIn(
                "[desktop-run-profiles] view", out.getvalue(),
            )

    def test_handler_registered(self) -> None:
        self.assertIn(
            "view-desktop-run-profiles", agent_loop.HANDLERS,
        )
        self.assertIs(
            agent_loop.HANDLERS["view-desktop-run-profiles"],
            agent_loop.cmd_view_desktop_run_profiles,
        )

    def test_parser_accepts_subcommand(self) -> None:
        parser = agent_loop.build_parser()
        args = parser.parse_args([
            "view-desktop-run-profiles",
            "--controller-root", "/tmp/nope",
        ])
        self.assertEqual(args.cmd, "view-desktop-run-profiles")
        self.assertEqual(args.controller_root, "/tmp/nope")


# ---------------------------------------------------------------------------
# Integration into the Phase 10M desktop app view
# ---------------------------------------------------------------------------
class DesktopAppViewIncludesRunProfilesTests(unittest.TestCase):

    def test_assemble_includes_run_profiles_view_key(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.assemble_desktop_app_view(controller)
            self.assertIn("run_profiles_view", view)
            run_profiles = view["run_profiles_view"]
            self.assertIsInstance(run_profiles, dict)
            self.assertEqual(
                run_profiles["view_signal_version"],
                agent_loop.DESKTOP_RUN_PROFILES_SIGNAL_VERSION,
            )

    def test_assemble_delegates_to_build_run_profiles_view(
        self,
    ) -> None:
        sentinel = {
            "view_signal_version": "phase-10q-v1",
            "_sentinel": "run_profiles",
            "controller_path_canonical": "/tmp/c",
            "current_loop_state_status": None,
            "mirror": {
                "approval_mode": None,
                "approval_mode_allowed_values": [],
                "max_cycles": None, "cycle_count": None,
                "phase": None, "sub_phase": None, "task": None,
                "status": None,
                "runtime_adapter": "local",
                "runtime_adapter_default": "local",
                "runtime_adapter_supported": ["local"],
            },
            "affordances": [],
            "precedence_note": "x",
        }
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            with mock.patch.object(
                agent_loop, "build_desktop_run_profiles_view",
                return_value=sentinel,
            ):
                view = agent_loop.assemble_desktop_app_view(
                    controller,
                )
            self.assertIs(view["run_profiles_view"], sentinel)

    def test_run_profiles_halt_does_not_break_other_sub_views(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")

            def _raise_halt(_root, *args, **kwargs):
                raise agent_loop.HaltError(
                    "halted_input_missing", "run profiles halt",
                )

            with mock.patch.object(
                agent_loop, "build_desktop_run_profiles_view",
                side_effect=_raise_halt,
            ):
                view = agent_loop.assemble_desktop_app_view(
                    controller,
                )
            self.assertIsNone(view["run_profiles_view"]["view"])
            self.assertIn(
                "run profiles halt",
                view["run_profiles_view"]["error"],
            )
            for key in (
                "status_view", "controls_view",
                "dashboard_view", "setup_view",
            ):
                self.assertIn(
                    "view_signal_version", view[key],
                )

    def test_render_includes_run_profiles_label_and_header(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.assemble_desktop_app_view(controller)
            lines = agent_loop.render_desktop_app_text(view)
            output = "\n".join(lines)
            self.assertIn("Run Profiles (Phase 10Q)", output)
            self.assertIn(
                "[desktop-run-profiles] view "
                "(signal_version='phase-10q-v1')",
                output,
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
            agent_loop.build_desktop_run_profiles_view(controller)
            after = state_path.read_text(encoding="utf-8")
            self.assertEqual(before, after)

    def test_build_does_not_write_orchestrator_log(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            log_path = (
                controller / ".agent-loop" / "orchestrator.log"
            )
            self.assertFalse(log_path.exists())
            agent_loop.build_desktop_run_profiles_view(controller)
            self.assertFalse(
                log_path.exists(),
                "build_desktop_run_profiles_view must NOT create "
                "`.agent-loop/orchestrator.log` (Phase 10L "
                "contract)",
            )

    def test_build_does_not_invoke_halt(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            calls = []

            def _record(*args, **kwargs):
                calls.append((args, kwargs))
                return -1

            with mock.patch.object(agent_loop, "_halt", _record):
                agent_loop.build_desktop_run_profiles_view(
                    controller,
                )
            self.assertEqual(
                calls, [],
                "build_desktop_run_profiles_view called "
                "_halt(...); Phase 10L contract forbids invoking "
                "_halt from the desktop run-profiles path",
            )

    def test_build_does_not_create_runtime_config(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            rc_path = (
                controller / ".agent-loop" / "runtime-config.json"
            )
            self.assertFalse(rc_path.exists())
            agent_loop.build_desktop_run_profiles_view(controller)
            self.assertFalse(
                rc_path.exists(),
                "build_desktop_run_profiles_view must NOT create "
                "`.agent-loop/runtime-config.json` (only "
                "set-runtime-config writes that artifact)",
            )

    def test_build_does_not_create_external_target_record(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            target_path = (
                controller
                / agent_loop.EXTERNAL_TARGET_ATTACH_RECORD_REL
            )
            self.assertFalse(target_path.exists())
            agent_loop.build_desktop_run_profiles_view(controller)
            self.assertFalse(
                target_path.exists(),
                "build_desktop_run_profiles_view must NOT create "
                "an attach record (only attach-external-target "
                "writes that artifact)",
            )

    def test_cli_does_not_spawn_subprocess(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            args = argparse.Namespace(
                cmd="view-desktop-run-profiles",
                controller_root=str(controller),
            )
            spawn_calls = []

            def _record(*args, **kwargs):
                spawn_calls.append((args, kwargs))
                raise RuntimeError(
                    "Phase 10L contract violation: run-profiles "
                    "must NOT spawn a subprocess"
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
                    "subprocess.check_call", side_effect=_record,
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
                        .cmd_view_desktop_run_profiles(args)
                    )
            finally:
                for p in patches:
                    p.stop()
            self.assertEqual(rc, 0)
            self.assertEqual(
                spawn_calls, [],
                "cmd_view_desktop_run_profiles spawned a "
                "subprocess; Phase 10L contract forbids silent "
                "CLI dispatch",
            )

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
            "Phase 10Q MUST NOT widen the Phase 10I library-"
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
                agent_loop.build_desktop_run_profiles_view(
                    controller,
                )
            self.assertEqual(
                calls, [],
                "build_desktop_run_profiles_view opened a "
                "network socket; Phase 10Q forbids network IO",
            )


if __name__ == "__main__":
    unittest.main()
