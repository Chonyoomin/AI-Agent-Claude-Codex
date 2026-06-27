"""Phase 10M - Desktop App Read-Only Runtime Initial Slice tests.

Exercises:
  - module-level constants (signal version, cadence floors,
    precedence note, controller-root markers)
  - `validate_desktop_controller_root(...)` soft-failure shape
  - `_desktop_safe_call_view(...)` HaltError / exception soft-wrap
  - `_desktop_clamp_cadence(...)` floor enforcement
  - `assemble_desktop_app_view(...)` shape + sub-view delegation
  - `render_desktop_app_text(...)` attribution
  - the `launch-desktop-app` CLI handler in headless mode
  - non-mutation invariants required by the Phase 10L contract
    (no orchestrator.log write, no loop-state mutation, no
    `_halt` invocation, no new library-callable controls beyond
    the Phase 10I three)
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
    td: Path, status: str = "awaiting_claude_implementation",
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
                "Phase 10M - Desktop App Read-Only Runtime Initial "
                "Slice"
            ),
            "task": "phase-10m-test",
            "status": status,
            "cycle_count": 1,
            "max_cycles": 3,
            "last_verdict": None,
            "last_verdict_phase": None,
            "contract_version": CONTRACT_VERSION,
            "claude_version": "claude-opus-4-7",
            "codex_version": None,
            "orchestrator_version": "phase-3d-v0",
            "approval_mode": "review",
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
            agent_loop.DESKTOP_APP_VIEW_SIGNAL_VERSION,
            "phase-10m-v1",
        )

    def test_cadence_floors_match_phase_10l_contract(self) -> None:
        self.assertEqual(
            agent_loop._DESKTOP_APP_MIN_IDLE_CADENCE_SECONDS, 2,
        )
        self.assertEqual(
            agent_loop._DESKTOP_APP_MIN_OPERATOR_CADENCE_SECONDS, 1,
        )

    def test_controller_root_markers_match_contract(self) -> None:
        self.assertEqual(
            agent_loop._DESKTOP_APP_CONTROLLER_ROOT_MARKERS,
            ("AGENTS.md", "CLAUDE.md", "TASK.md", ".agent-loop"),
        )

    def test_precedence_note_pins_phase_10l_contract(self) -> None:
        note = agent_loop.DESKTOP_APP_PRECEDENCE_NOTE
        for fragment in (
            "Canonical artifacts on disk always win",
            "Phase 10H",
            "Phase 10I",
            "Phase 10K",
            "library-callable control surface",
        ):
            self.assertIn(fragment, note)


# ---------------------------------------------------------------------------
# Controller-root validation
# ---------------------------------------------------------------------------
class ValidateControllerRootTests(unittest.TestCase):

    def test_valid_controller_root(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            result = agent_loop.validate_desktop_controller_root(
                controller,
            )
            self.assertTrue(result["valid"])
            self.assertEqual(result["missing_markers"], ())
            self.assertTrue(
                result["root_path"].endswith("/c"),
                f"got root_path={result['root_path']!r}",
            )

    def test_missing_agents_md(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            (controller / "AGENTS.md").unlink()
            result = agent_loop.validate_desktop_controller_root(
                controller,
            )
            self.assertFalse(result["valid"])
            self.assertIn("AGENTS.md", result["missing_markers"])

    def test_missing_all_markers(self) -> None:
        with TemporaryDirectory() as td:
            controller = Path(td) / "c"
            controller.mkdir()
            result = agent_loop.validate_desktop_controller_root(
                controller,
            )
            self.assertFalse(result["valid"])
            for marker in (
                "AGENTS.md", "CLAUDE.md", "TASK.md", ".agent-loop",
            ):
                self.assertIn(marker, result["missing_markers"])

    def test_validation_does_not_raise_on_nonexistent_path(
        self,
    ) -> None:
        # Soft-failure: a non-existent path returns valid=False
        # rather than raising. The desktop shell renders the error
        # state per the Phase 10L refusal vocabulary.
        with TemporaryDirectory() as td:
            missing = Path(td) / "does-not-exist"
            result = agent_loop.validate_desktop_controller_root(
                missing,
            )
            self.assertFalse(result["valid"])


# ---------------------------------------------------------------------------
# _desktop_safe_call_view
# ---------------------------------------------------------------------------
class DesktopSafeCallViewTests(unittest.TestCase):

    def test_normal_call_returns_view_dict(self) -> None:
        def _fn(_root):
            return {"view_signal_version": "fake", "data": 1}
        result = agent_loop._desktop_safe_call_view(_fn, Path("."))
        self.assertEqual(result["view_signal_version"], "fake")

    def test_halt_error_converted_to_soft_error(self) -> None:
        def _fn(_root):
            raise agent_loop.HaltError(
                "halted_input_missing", "test halt",
            )
        result = agent_loop._desktop_safe_call_view(_fn, Path("."))
        self.assertEqual(result["view"], None)
        self.assertIn("test halt", result["error"])

    def test_generic_exception_converted_to_soft_error(self) -> None:
        def _fn(_root):
            raise ValueError("boom")
        result = agent_loop._desktop_safe_call_view(_fn, Path("."))
        self.assertEqual(result["view"], None)
        self.assertIn("ValueError: boom", result["error"])


# ---------------------------------------------------------------------------
# _desktop_clamp_cadence
# ---------------------------------------------------------------------------
class DesktopClampCadenceTests(unittest.TestCase):

    def test_none_returns_idle_floor(self) -> None:
        self.assertEqual(
            agent_loop._desktop_clamp_cadence(None), 2.0,
        )

    def test_none_operator_driven_returns_operator_floor(
        self,
    ) -> None:
        self.assertEqual(
            agent_loop._desktop_clamp_cadence(
                None, operator_driven=True,
            ),
            1.0,
        )

    def test_value_below_idle_floor_clamped_up(self) -> None:
        self.assertEqual(
            agent_loop._desktop_clamp_cadence(0.1), 2.0,
        )

    def test_value_below_operator_floor_clamped_up(self) -> None:
        self.assertEqual(
            agent_loop._desktop_clamp_cadence(
                0.1, operator_driven=True,
            ),
            1.0,
        )

    def test_value_above_floor_preserved(self) -> None:
        self.assertEqual(
            agent_loop._desktop_clamp_cadence(5.0), 5.0,
        )

    def test_non_numeric_returns_floor(self) -> None:
        # Soft-failure: a bad cadence falls back to the floor
        # rather than raising. The desktop shell must not crash on
        # operator-supplied non-numeric input.
        self.assertEqual(
            agent_loop._desktop_clamp_cadence("not a number"), 2.0,
        )


# ---------------------------------------------------------------------------
# assemble_desktop_app_view
# ---------------------------------------------------------------------------
class AssembleDesktopAppViewTests(unittest.TestCase):

    def test_view_shape(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.assemble_desktop_app_view(controller)
            self.assertEqual(
                view["view_signal_version"], "phase-10m-v1",
            )
            self.assertEqual(
                view["controller_path_canonical"],
                controller.resolve().as_posix(),
            )
            self.assertIn("status_view", view)
            self.assertIn("controls_view", view)
            self.assertIn("dashboard_view", view)
            self.assertIn(
                "Canonical artifacts on disk always win",
                view["precedence_note"],
            )

    def test_sub_views_delegate_to_shipped_library_functions(
        self,
    ) -> None:
        # The Phase 10L Bridge contract requires the desktop shell
        # to invoke the shipped view library functions verbatim and
        # MUST NOT inject additional fields. Patch each shipped fn
        # to return a sentinel; assert the assembled view returns
        # exactly those sentinels.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            status_sentinel = {
                "view_signal_version": "phase-10h-v1",
                "_sentinel": "status",
            }
            controls_sentinel = {
                "view_signal_version": "phase-10i-v1",
                "_sentinel": "controls",
            }
            dashboard_sentinel = {
                "view_signal_version": "phase-10k-v1",
                "_sentinel": "dashboard",
                "surfaces": {},
                "controller_path_canonical": "",
                "precedence_note": "",
            }
            with mock.patch.object(
                agent_loop, "build_external_ui_status_view",
                return_value=status_sentinel,
            ), mock.patch.object(
                agent_loop, "build_external_ui_control_view",
                return_value=controls_sentinel,
            ), mock.patch.object(
                agent_loop, "build_artifact_dashboard_view",
                return_value=dashboard_sentinel,
            ):
                view = agent_loop.assemble_desktop_app_view(
                    controller,
                )
            self.assertIs(view["status_view"], status_sentinel)
            self.assertIs(view["controls_view"], controls_sentinel)
            self.assertIs(view["dashboard_view"], dashboard_sentinel)

    def test_halt_error_in_one_sub_view_does_not_break_others(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            def _raise_halt(_root):
                raise agent_loop.HaltError(
                    "halted_input_missing", "status halt",
                )
            with mock.patch.object(
                agent_loop, "build_external_ui_status_view",
                side_effect=_raise_halt,
            ):
                view = agent_loop.assemble_desktop_app_view(
                    controller,
                )
            # status_view surfaced as soft error
            self.assertIsNone(view["status_view"]["view"])
            self.assertIn(
                "status halt", view["status_view"]["error"],
            )
            # controls_view and dashboard_view succeeded
            self.assertIn(
                "view_signal_version", view["controls_view"],
            )
            self.assertIn(
                "view_signal_version", view["dashboard_view"],
            )


# ---------------------------------------------------------------------------
# render_desktop_app_text
# ---------------------------------------------------------------------------
class RenderDesktopAppTextTests(unittest.TestCase):

    def test_render_includes_signal_version_and_all_three_labels(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.assemble_desktop_app_view(controller)
            lines = agent_loop.render_desktop_app_text(view)
            output = "\n".join(lines)
            self.assertIn(
                "signal_version='phase-10m-v1'", output,
            )
            for label in (
                "Status (Phase 10H)",
                "Controls (Phase 10I)",
                "Dashboard (Phase 10K)",
            ):
                self.assertIn(label, output)
            self.assertIn("precedence_note:", output)

    def test_render_includes_canonical_and_advisory_attribution(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.assemble_desktop_app_view(controller)
            lines = agent_loop.render_desktop_app_text(view)
            output = "\n".join(lines)
            self.assertIn("[canonical mirror]", output)
            self.assertIn("[advisory]", output)

    def test_render_handles_sub_view_error_envelope(self) -> None:
        view = {
            "view_signal_version": "phase-10m-v1",
            "controller_path_canonical": "/tmp/c",
            "status_view": {
                "error": "test status error", "view": None,
            },
            "controls_view": {
                "view_signal_version": "phase-10i-v1",
                "controls": [],
            },
            "dashboard_view": {
                "view_signal_version": "phase-10k-v1",
                "controller_path_canonical": "/tmp/c",
                "surfaces": {},
                "precedence_note": "x",
            },
            "setup_view": {
                "error": "test setup error", "view": None,
            },
            "precedence_note": "x",
        }
        lines = agent_loop.render_desktop_app_text(view)
        output = "\n".join(lines)
        self.assertIn("[error] 'test status error'", output)
        self.assertIn("[error] 'test setup error'", output)


# ---------------------------------------------------------------------------
# Phase 10P integration into the Phase 10M desktop app view
# (the Phase 10P fix cycle requires assemble_desktop_app_view to
# expose the onboarding surface alongside the Phase 10H / 10I /
# 10K sub-views, not as a separate CLI-only reporter)
# ---------------------------------------------------------------------------
class DesktopAppViewIncludesSetupViewTests(unittest.TestCase):

    def test_assemble_includes_setup_view_key(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.assemble_desktop_app_view(controller)
            self.assertIn("setup_view", view)
            setup = view["setup_view"]
            self.assertIsInstance(setup, dict)
            self.assertEqual(
                setup["view_signal_version"],
                agent_loop.DESKTOP_SETUP_SIGNAL_VERSION,
            )

    def test_assemble_delegates_to_build_desktop_setup_view(
        self,
    ) -> None:
        sentinel = {
            "view_signal_version": "phase-10p-v1",
            "_sentinel": "setup",
            "controller_path_canonical": "/tmp/c",
            "controller_root": {"status": "ok", "summary": ""},
            "target": {"status": "missing", "summary": ""},
            "adapter_env": {
                "status": "missing",
                "summary": "",
                "adapters": [],
            },
            "runtime_config": {
                "status": "default",
                "summary": "",
                "selected_runtime": None,
                "default_runtime": "local",
            },
            "wrapper_templates": {
                "status": "ok",
                "summary": "",
                "templates": [],
            },
            "local_tools": {
                "status": "ok",
                "summary": "",
                "required_tools": [],
                "python": {
                    "name": "python", "version": "x",
                    "executable": "x",
                },
            },
            "precedence_note": "x",
        }
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            with mock.patch.object(
                agent_loop, "build_desktop_setup_view",
                return_value=sentinel,
            ):
                view = agent_loop.assemble_desktop_app_view(
                    controller,
                )
            self.assertIs(view["setup_view"], sentinel)

    def test_setup_view_halt_does_not_break_other_sub_views(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")

            def _raise_halt(_root, *args, **kwargs):
                raise agent_loop.HaltError(
                    "halted_input_missing", "setup halt",
                )

            with mock.patch.object(
                agent_loop, "build_desktop_setup_view",
                side_effect=_raise_halt,
            ):
                view = agent_loop.assemble_desktop_app_view(
                    controller,
                )
            self.assertIsNone(view["setup_view"]["view"])
            self.assertIn("setup halt", view["setup_view"]["error"])
            for key in ("status_view", "controls_view",
                        "dashboard_view"):
                self.assertIn(
                    "view_signal_version", view[key],
                )

    def test_render_includes_setup_phase_10p_label(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.assemble_desktop_app_view(controller)
            lines = agent_loop.render_desktop_app_text(view)
            output = "\n".join(lines)
            self.assertIn("Setup (Phase 10P)", output)
            self.assertIn(
                "[desktop-setup] view "
                "(signal_version='phase-10p-v1')",
                output,
            )

    def test_render_includes_setup_section_attribution(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.assemble_desktop_app_view(controller)
            lines = agent_loop.render_desktop_app_text(view)
            output = "\n".join(lines)
            for fragment in (
                "controller_root status=",
                "adapter_env status=",
                "runtime_config status=",
                "local_tools status=",
            ):
                self.assertIn(fragment, output)


# ---------------------------------------------------------------------------
# CLI handler (headless mode)
# ---------------------------------------------------------------------------
class CmdLaunchDesktopAppHeadlessTests(unittest.TestCase):

    def _run(
        self,
        controller: Path,
        *,
        headless: bool = True,
        once: bool = False,
        controller_root: bool = True,
    ) -> tuple:
        args = argparse.Namespace(
            cmd="launch-desktop-app",
            controller_root=(
                str(controller) if controller_root else None
            ),
            headless=headless,
            once=once,
            cadence_seconds=None,
            operator_driven=False,
        )
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = agent_loop.cmd_launch_desktop_app(args)
        return rc, out.getvalue(), err.getvalue()

    def test_handler_wired(self) -> None:
        self.assertIn("launch-desktop-app", agent_loop.HANDLERS)
        self.assertIs(
            agent_loop.HANDLERS["launch-desktop-app"],
            agent_loop.cmd_launch_desktop_app,
        )

    def test_argparse_grammar(self) -> None:
        parser = agent_loop.build_parser()
        args = parser.parse_args([
            "launch-desktop-app",
            "--controller-root", "/tmp/c",
            "--headless",
            "--cadence-seconds", "5",
        ])
        self.assertEqual(args.cmd, "launch-desktop-app")
        self.assertEqual(args.controller_root, "/tmp/c")
        self.assertTrue(args.headless)
        self.assertEqual(args.cadence_seconds, 5.0)

    def test_argparse_once_alias(self) -> None:
        parser = agent_loop.build_parser()
        args = parser.parse_args([
            "launch-desktop-app", "--once",
        ])
        self.assertTrue(args.once)

    def test_headless_exits_zero_with_rendered_view(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            rc, out, err = self._run(controller, headless=True)
            self.assertEqual(rc, 0)
            self.assertEqual(err, "")
            self.assertIn("signal_version='phase-10m-v1'", out)
            self.assertIn("Status (Phase 10H)", out)
            self.assertIn("Controls (Phase 10I)", out)
            self.assertIn("Dashboard (Phase 10K)", out)

    def test_once_alias_works_like_headless(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            rc, out, err = self._run(
                controller, headless=False, once=True,
            )
            self.assertEqual(rc, 0)
            self.assertIn("signal_version='phase-10m-v1'", out)

    def test_missing_controller_root_markers_refuses(self) -> None:
        with TemporaryDirectory() as td:
            controller = Path(td) / "c"
            controller.mkdir()
            rc, out, err = self._run(controller, headless=True)
            self.assertEqual(rc, 2)
            self.assertEqual(out, "")
            self.assertIn("[desktop-app] REFUSED:", err)
            self.assertIn("AGENTS.md", err)
            self.assertIn("CLAUDE.md", err)
            self.assertIn("TASK.md", err)

    def test_omitted_controller_root_refuses_explicitly(
        self,
    ) -> None:
        # Phase 10L "Controller-Root Selection Flow" REQUIRES
        # explicit operator selection of the controller root. The
        # desktop shell MUST NOT silently pick a default root from
        # the auto-discovered repo root, the OS-level current
        # working directory, an environment variable, or a
        # packaging-time configured path. Pin the explicit-refusal
        # behavior here so a future regression (e.g. reintroducing
        # `find_repo_root()` fallback) is caught immediately.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            # `controller_root=False` -> the Namespace's
            # controller_root field is None, matching the case
            # where the operator omits `--controller-root`.
            rc, out, err = self._run(
                controller, headless=True, controller_root=False,
            )
            self.assertEqual(rc, 2)
            self.assertEqual(out, "")
            self.assertIn("[desktop-app] REFUSED:", err)
            self.assertIn("--controller-root is required", err)
            # The refusal message MUST surface the contract
            # rationale so an operator reading the stderr line
            # understands why the shell refused (not just that it
            # refused).
            for fragment in (
                "Phase 10L",
                "Controller-Root Selection Flow",
                "MUST NOT silently pick a default root",
            ):
                self.assertIn(fragment, err)

    def test_omitted_controller_root_does_not_call_find_repo_root(
        self,
    ) -> None:
        # Regression guard: patch `find_repo_root` to a recorder.
        # The CLI handler MUST refuse before any auto-discovery
        # fallback could fire.
        with TemporaryDirectory() as td:
            _make_controller(Path(td) / "c")
            calls = []

            def _record(*args, **kwargs):
                calls.append((args, kwargs))
                return Path(td) / "c"

            args = argparse.Namespace(
                cmd="launch-desktop-app",
                controller_root=None,
                headless=True, once=False,
                cadence_seconds=None, operator_driven=False,
            )
            out, err = io.StringIO(), io.StringIO()
            with mock.patch.object(
                agent_loop, "find_repo_root", _record,
            ):
                with redirect_stdout(out), redirect_stderr(err):
                    rc = agent_loop.cmd_launch_desktop_app(args)
            self.assertEqual(rc, 2)
            self.assertEqual(
                calls, [],
                "cmd_launch_desktop_app called find_repo_root() "
                "when --controller-root was omitted; Phase 10L "
                "Controller-Root Selection Flow forbids any "
                "auto-discovered fallback",
            )


# ---------------------------------------------------------------------------
# Non-mutation invariants (Phase 10L contract)
# ---------------------------------------------------------------------------
class NonMutationInvariantsTests(unittest.TestCase):

    def test_assemble_does_not_mutate_loop_state(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            state_path = (
                controller / ".agent-loop" / "loop-state.json"
            )
            before = state_path.read_text(encoding="utf-8")
            agent_loop.assemble_desktop_app_view(controller)
            after = state_path.read_text(encoding="utf-8")
            self.assertEqual(before, after)

    def test_assemble_does_not_write_orchestrator_log(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            log_path = (
                controller / ".agent-loop" / "orchestrator.log"
            )
            self.assertFalse(log_path.exists())
            agent_loop.assemble_desktop_app_view(controller)
            self.assertFalse(
                log_path.exists(),
                "assemble_desktop_app_view must NOT create "
                "`.agent-loop/orchestrator.log` (Phase 10L "
                "contract)",
            )

    def test_assemble_does_not_invoke_halt(self) -> None:
        # The Phase 10L contract explicitly forbids the desktop
        # shell from invoking `_halt(...)`. Patch `_halt` to a
        # sentinel that records calls; the assemble path must not
        # touch it.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            calls = []

            def _record(*args, **kwargs):
                calls.append((args, kwargs))
                return -1

            with mock.patch.object(agent_loop, "_halt", _record):
                agent_loop.assemble_desktop_app_view(controller)
            self.assertEqual(
                calls, [],
                "assemble_desktop_app_view called _halt(...); "
                "Phase 10L contract forbids invoking _halt from "
                "the desktop shell path",
            )

    def test_cli_headless_does_not_mutate_controller_state(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            state_path = (
                controller / ".agent-loop" / "loop-state.json"
            )
            log_path = (
                controller / ".agent-loop" / "orchestrator.log"
            )
            before_state = state_path.read_text(encoding="utf-8")
            log_exists_before = log_path.exists()
            args = argparse.Namespace(
                cmd="launch-desktop-app",
                controller_root=str(controller),
                headless=True, once=False,
                cadence_seconds=None, operator_driven=False,
            )
            with redirect_stdout(io.StringIO()):
                agent_loop.cmd_launch_desktop_app(args)
            self.assertEqual(
                before_state,
                state_path.read_text(encoding="utf-8"),
            )
            self.assertEqual(
                log_exists_before, log_path.exists(),
            )

    def test_does_not_introduce_new_library_callable_control(
        self,
    ) -> None:
        # The Phase 10L contract caps the library-callable control
        # surface at the Phase 10I three. The Phase 10M slice MUST
        # NOT add a new entry to `_EXTERNAL_UI_CONTROL_REGISTRY`.
        # Anchor the cap at exactly the three known ids.
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
            "Phase 10M MUST NOT widen the Phase 10I "
            "library-callable control surface beyond the three "
            "shipped controls",
        )


if __name__ == "__main__":
    unittest.main()
