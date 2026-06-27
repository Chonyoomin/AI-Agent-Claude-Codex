"""Phase 10P - Desktop App Operator Setup And CLI Onboarding tests.

Exercises:
  - module-level constants (signal version, precedence note,
    required-local-tool tuple, env-adapter spec tuple)
  - per-section assemblers (controller-root, target,
    adapter-env, runtime-config, wrapper-templates, local-tools)
  - `build_desktop_setup_view(...)` shape + soft-failure
    semantics on a HaltError-raising delegate
  - `render_desktop_setup_text(...)` attribution
  - `cmd_view_desktop_setup(...)` CLI handler wiring, the
    Phase-10L-mandated `--controller-root` REQUIRED refusal, and
    the missing-controller-root-markers refusal
  - non-mutation invariants required by the Phase 10L contract
    (no orchestrator.log write, no loop-state mutation, no
    `_halt` invocation, no subprocess spawn, no widening of the
    Phase 10I three-control library-callable cap, no mutation of
    `runtime-config.json` / `external-target.json` / the shell
    environment / the wrapper templates)
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


def _make_controller(td: Path) -> Path:
    td.mkdir(parents=True, exist_ok=True)
    (td / "AGENTS.md").write_text("test\n", encoding="utf-8")
    (td / "CLAUDE.md").write_text("test\n", encoding="utf-8")
    (td / "TASK.md").write_text("# TASK.md\n", encoding="utf-8")
    (td / ".agent-loop").mkdir()
    (td / ".agent-loop" / "loop-state.json").write_text(
        json.dumps({
            "phase": "Phase 10 - Future Product Features",
            "sub_phase": (
                "Phase 10P - Desktop App Operator Setup And CLI "
                "Onboarding"
            ),
            "task": "phase-10p-test",
            "status": "awaiting_claude_implementation",
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


def _add_wrapper_templates(controller: Path) -> None:
    scripts = controller / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    (scripts / "claude-wrapper.sh.template").write_text(
        "#!/bin/sh\n", encoding="utf-8",
    )
    (scripts / "codex-wrapper.sh.template").write_text(
        "#!/bin/sh\n", encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
class ConstantsTests(unittest.TestCase):

    def test_signal_version(self) -> None:
        self.assertEqual(
            agent_loop.DESKTOP_SETUP_SIGNAL_VERSION,
            "phase-10p-v1",
        )

    def test_precedence_note_mentions_read_only_and_no_mutation(
        self,
    ) -> None:
        note = agent_loop.DESKTOP_SETUP_PRECEDENCE_NOTE
        self.assertIn("read-only", note)
        self.assertIn("NEVER mutates", note)
        self.assertIn("Phase 10I", note)
        self.assertIn("subprocess", note)
        self.assertIn("network socket", note)

    def test_required_local_tools_includes_git(self) -> None:
        tools = agent_loop._DESKTOP_SETUP_REQUIRED_LOCAL_TOOLS
        self.assertIn("git", tools)

    def test_env_adapter_specs_cover_claude_and_codex(self) -> None:
        adapters = agent_loop._DESKTOP_SETUP_ENV_ADAPTERS
        names = {spec["adapter"] for spec in adapters}
        self.assertEqual(names, {"claude", "codex"})
        for spec in adapters:
            self.assertIn(spec["command_env_var"], {
                agent_loop.ENV_CLAUDE_CMD,
                agent_loop.ENV_CODEX_CMD,
            })
            self.assertIn(spec["model_env_var"], {
                agent_loop.ENV_CLAUDE_MODEL,
                agent_loop.ENV_CODEX_MODEL,
            })
            self.assertTrue(
                spec["wrapper_template_rel"].startswith(
                    "scripts/",
                ),
            )
            self.assertTrue(
                spec["wrapper_template_rel"].endswith(
                    ".sh.template",
                ),
            )


# ---------------------------------------------------------------------------
# Section assemblers
# ---------------------------------------------------------------------------
class ControllerRootSectionTests(unittest.TestCase):

    def test_valid_controller_returns_ok(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            section = (
                agent_loop._desktop_setup_controller_root_section(
                    controller,
                )
            )
            self.assertEqual(section["status"], "ok")
            self.assertEqual(section["missing_markers"], [])
            self.assertIn(
                "controller root markers present",
                section["summary"],
            )

    def test_missing_markers_returns_refused(self) -> None:
        with TemporaryDirectory() as td:
            section = (
                agent_loop._desktop_setup_controller_root_section(
                    Path(td),
                )
            )
            self.assertEqual(section["status"], "refused")
            self.assertIn(
                "AGENTS.md", section["missing_markers"],
            )
            self.assertIn(
                "Phase 10L", section["summary"],
            )


class TargetSectionTests(unittest.TestCase):

    def test_no_attach_record_returns_missing(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            section = agent_loop._desktop_setup_target_section(
                controller,
            )
            self.assertEqual(section["status"], "missing")
            self.assertFalse(section["attached"])
            self.assertFalse(section["schema_valid"])
            self.assertEqual(section["schema_violations"], [])

    def test_halt_error_from_inspector_returns_refused(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            halt = agent_loop.HaltError(
                "halted_input_missing",
                "attach record unreadable",
            )
            with mock.patch.object(
                agent_loop, "inspect_external_target_attach",
                side_effect=halt,
            ):
                section = (
                    agent_loop._desktop_setup_target_section(
                        controller,
                    )
                )
            self.assertEqual(section["status"], "refused")
            self.assertIn(
                "attach record unreadable", section["summary"],
            )
            self.assertEqual(
                section["schema_violations"],
                ["attach record unreadable"],
            )


class AdapterEnvSectionTests(unittest.TestCase):

    def test_both_env_vars_set_returns_ok(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            section = (
                agent_loop._desktop_setup_adapter_env_section(
                    controller,
                    {
                        agent_loop.ENV_CLAUDE_CMD: (
                            "/usr/local/bin/claude-wrapper"
                        ),
                        agent_loop.ENV_CODEX_CMD: (
                            "/usr/local/bin/codex-wrapper"
                        ),
                    },
                )
            )
            self.assertEqual(section["status"], "ok")
            for entry in section["adapters"]:
                self.assertEqual(entry["status"], "ok")
                self.assertTrue(entry["command_set"])

    def test_missing_env_vars_returns_missing(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            section = (
                agent_loop._desktop_setup_adapter_env_section(
                    controller, {},
                )
            )
            self.assertEqual(section["status"], "missing")
            for entry in section["adapters"]:
                self.assertEqual(entry["status"], "missing")
                self.assertFalse(entry["command_set"])
                self.assertFalse(entry["model_set"])

    def test_one_set_one_unset_returns_missing(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            section = (
                agent_loop._desktop_setup_adapter_env_section(
                    controller,
                    {
                        agent_loop.ENV_CLAUDE_CMD: (
                            "/usr/bin/claude"
                        ),
                    },
                )
            )
            self.assertEqual(section["status"], "missing")
            statuses = {
                entry["adapter"]: entry["status"]
                for entry in section["adapters"]
            }
            self.assertEqual(statuses["claude"], "ok")
            self.assertEqual(statuses["codex"], "missing")

    def test_wrapper_template_presence_is_reflected(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            _add_wrapper_templates(controller)
            section = (
                agent_loop._desktop_setup_adapter_env_section(
                    controller, {},
                )
            )
            for entry in section["adapters"]:
                self.assertTrue(entry["wrapper_template_present"])


class RuntimeConfigSectionTests(unittest.TestCase):

    def test_absent_runtime_config_returns_default(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            section = (
                agent_loop._desktop_setup_runtime_config_section(
                    controller,
                )
            )
            self.assertEqual(section["status"], "default")
            self.assertIsNone(section["selected_runtime"])
            self.assertEqual(
                section["default_runtime"],
                agent_loop.RUNTIME_ADAPTER_DEFAULT,
            )

    def test_present_runtime_config_returns_ok(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            agent_loop.write_runtime_config(
                controller,
                agent_loop.RUNTIME_ADAPTER_LANGGRAPH,
            )
            section = (
                agent_loop._desktop_setup_runtime_config_section(
                    controller,
                )
            )
            self.assertEqual(section["status"], "ok")
            self.assertEqual(
                section["selected_runtime"],
                agent_loop.RUNTIME_ADAPTER_LANGGRAPH,
            )

    def test_malformed_runtime_config_returns_refused(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            (
                controller / ".agent-loop" / "runtime-config.json"
            ).write_text("not json", encoding="utf-8")
            section = (
                agent_loop._desktop_setup_runtime_config_section(
                    controller,
                )
            )
            self.assertEqual(section["status"], "refused")
            self.assertIn(
                "runtime-config refused fail-closed",
                section["summary"],
            )


class WrapperTemplateSectionTests(unittest.TestCase):

    def test_absent_templates_return_missing(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            section = (
                agent_loop
                ._desktop_setup_wrapper_template_section(
                    controller,
                )
            )
            self.assertEqual(section["status"], "missing")
            self.assertFalse(
                any(t["present"] for t in section["templates"]),
            )

    def test_present_templates_return_ok(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            _add_wrapper_templates(controller)
            section = (
                agent_loop
                ._desktop_setup_wrapper_template_section(
                    controller,
                )
            )
            self.assertEqual(section["status"], "ok")
            for t in section["templates"]:
                self.assertTrue(t["present"])


class LocalToolSectionTests(unittest.TestCase):

    def test_present_tools_return_ok(self) -> None:
        with mock.patch.object(
            agent_loop.shutil, "which",
            side_effect=lambda name: f"/usr/bin/{name}",
        ):
            section = agent_loop._desktop_setup_local_tool_section()
        self.assertEqual(section["status"], "ok")
        for tool in section["required_tools"]:
            self.assertTrue(tool["present"])

    def test_missing_tools_return_missing(self) -> None:
        with mock.patch.object(
            agent_loop.shutil, "which", return_value=None,
        ):
            section = agent_loop._desktop_setup_local_tool_section()
        self.assertEqual(section["status"], "missing")
        for tool in section["required_tools"]:
            self.assertFalse(tool["present"])
            self.assertIsNone(tool["resolved_path"])

    def test_python_info_carries_version_and_executable(
        self,
    ) -> None:
        with mock.patch.object(
            agent_loop.shutil, "which", return_value="/usr/bin/git",
        ):
            section = agent_loop._desktop_setup_local_tool_section()
        python_info = section["python"]
        self.assertEqual(python_info["name"], "python")
        self.assertEqual(
            python_info["version"], sys.version.split()[0],
        )
        self.assertEqual(
            python_info["executable"], sys.executable,
        )


# ---------------------------------------------------------------------------
# build_desktop_setup_view
# ---------------------------------------------------------------------------
class BuildDesktopSetupViewTests(unittest.TestCase):

    def test_view_carries_canonical_keys(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.build_desktop_setup_view(
                controller, environ={},
            )
            self.assertEqual(
                view["view_signal_version"],
                agent_loop.DESKTOP_SETUP_SIGNAL_VERSION,
            )
            self.assertEqual(
                view["precedence_note"],
                agent_loop.DESKTOP_SETUP_PRECEDENCE_NOTE,
            )
            for key in (
                "controller_root",
                "target",
                "adapter_env",
                "runtime_config",
                "wrapper_templates",
                "local_tools",
                "controller_path_canonical",
            ):
                self.assertIn(key, view)

    def test_explicit_environ_does_not_mutate_caller(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            environ = {
                agent_loop.ENV_CLAUDE_CMD: "/usr/bin/claude",
            }
            before = dict(environ)
            agent_loop.build_desktop_setup_view(
                controller, environ=environ,
            )
            self.assertEqual(environ, before)

    def test_environ_defaults_to_os_environ(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            sentinel = (
                "/sentinel/path/that/should/not/exist/agent-loop"
            )
            with mock.patch.dict(
                "os.environ",
                {agent_loop.ENV_CLAUDE_CMD: sentinel},
                clear=False,
            ):
                view = agent_loop.build_desktop_setup_view(
                    controller,
                )
            adapter_for_claude = next(
                a for a in view["adapter_env"]["adapters"]
                if a["adapter"] == "claude"
            )
            self.assertTrue(adapter_for_claude["command_set"])


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------
class RenderDesktopSetupTextTests(unittest.TestCase):

    def _view(self) -> dict:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            return agent_loop.build_desktop_setup_view(
                controller, environ={},
            )

    def test_header_carries_signal_version(self) -> None:
        view = self._view()
        lines = agent_loop.render_desktop_setup_text(view)
        self.assertTrue(any(
            line.startswith("[desktop-setup] view")
            and "phase-10p-v1" in line
            for line in lines
        ))

    def test_every_section_is_rendered_with_tag(self) -> None:
        view = self._view()
        lines = agent_loop.render_desktop_setup_text(view)
        text = "\n".join(lines)
        for fragment in (
            "controller_root status=",
            "target status=",
            "adapter_env status=",
            "runtime_config status=",
            "wrapper_templates status=",
            "local_tools status=",
        ):
            self.assertIn(fragment, text)

    def test_advisory_tag_marks_derived_state(self) -> None:
        view = self._view()
        lines = agent_loop.render_desktop_setup_text(view)
        self.assertTrue(any(
            "[advisory]" in line for line in lines
        ))

    def test_precedence_note_is_last_line(self) -> None:
        view = self._view()
        lines = agent_loop.render_desktop_setup_text(view)
        self.assertTrue(
            lines[-1].startswith("precedence_note:"),
        )


# ---------------------------------------------------------------------------
# CLI handler
# ---------------------------------------------------------------------------
class CmdViewDesktopSetupTests(unittest.TestCase):

    def test_omitted_controller_root_refuses(self) -> None:
        args = argparse.Namespace(
            cmd="view-desktop-setup", controller_root=None,
        )
        err = io.StringIO()
        with redirect_stderr(err):
            rc = agent_loop.cmd_view_desktop_setup(args)
        self.assertEqual(rc, 2)
        self.assertIn("REFUSED", err.getvalue())
        self.assertIn("--controller-root", err.getvalue())

    def test_empty_controller_root_refuses(self) -> None:
        args = argparse.Namespace(
            cmd="view-desktop-setup", controller_root="",
        )
        err = io.StringIO()
        with redirect_stderr(err):
            rc = agent_loop.cmd_view_desktop_setup(args)
        self.assertEqual(rc, 2)
        self.assertIn("REFUSED", err.getvalue())

    def test_invalid_controller_root_refuses_with_markers(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            args = argparse.Namespace(
                cmd="view-desktop-setup",
                controller_root=str(Path(td)),
            )
            err = io.StringIO()
            with redirect_stderr(err):
                rc = agent_loop.cmd_view_desktop_setup(args)
            self.assertEqual(rc, 2)
            stderr = err.getvalue()
            self.assertIn("REFUSED", stderr)
            self.assertIn("AGENTS.md", stderr)

    def test_valid_controller_root_exits_zero_and_prints_view(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            args = argparse.Namespace(
                cmd="view-desktop-setup",
                controller_root=str(controller),
            )
            out = io.StringIO()
            with redirect_stdout(out):
                rc = agent_loop.cmd_view_desktop_setup(args)
            self.assertEqual(rc, 0)
            self.assertIn(
                "[desktop-setup] view", out.getvalue(),
            )

    def test_handler_registered_in_handlers_map(self) -> None:
        self.assertIn(
            "view-desktop-setup", agent_loop.HANDLERS,
        )
        self.assertIs(
            agent_loop.HANDLERS["view-desktop-setup"],
            agent_loop.cmd_view_desktop_setup,
        )

    def test_parser_accepts_view_desktop_setup(self) -> None:
        parser = agent_loop.build_parser()
        args = parser.parse_args([
            "view-desktop-setup",
            "--controller-root", "/tmp/nope",
        ])
        self.assertEqual(args.cmd, "view-desktop-setup")
        self.assertEqual(args.controller_root, "/tmp/nope")


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
            agent_loop.build_desktop_setup_view(
                controller, environ={},
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
            agent_loop.build_desktop_setup_view(
                controller, environ={},
            )
            self.assertFalse(
                log_path.exists(),
                "build_desktop_setup_view must NOT create "
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
                agent_loop.build_desktop_setup_view(
                    controller, environ={},
                )
            self.assertEqual(
                calls, [],
                "build_desktop_setup_view called _halt(...); "
                "Phase 10L contract forbids invoking _halt from "
                "the desktop setup path",
            )

    def test_build_does_not_create_runtime_config(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            rc_path = (
                controller / ".agent-loop" / "runtime-config.json"
            )
            self.assertFalse(rc_path.exists())
            agent_loop.build_desktop_setup_view(
                controller, environ={},
            )
            self.assertFalse(
                rc_path.exists(),
                "build_desktop_setup_view must NOT create "
                "`.agent-loop/runtime-config.json` (the only "
                "mutating path is set-runtime-config)",
            )

    def test_build_does_not_mutate_os_environ(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            import os
            before = dict(os.environ)
            agent_loop.build_desktop_setup_view(controller)
            after = dict(os.environ)
            self.assertEqual(before, after)

    def test_cli_does_not_spawn_subprocess(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            args = argparse.Namespace(
                cmd="view-desktop-setup",
                controller_root=str(controller),
            )
            spawn_calls = []

            def _record(*args, **kwargs):
                spawn_calls.append((args, kwargs))
                raise RuntimeError(
                    "Phase 10L contract violation: setup view "
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
                    rc = agent_loop.cmd_view_desktop_setup(args)
            finally:
                for p in patches:
                    p.stop()
            self.assertEqual(rc, 0)
            self.assertEqual(
                spawn_calls, [],
                "cmd_view_desktop_setup spawned a subprocess; "
                "Phase 10L contract forbids silent CLI dispatch",
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
            "Phase 10P MUST NOT widen the Phase 10I library-"
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
                agent_loop.build_desktop_setup_view(
                    controller, environ={},
                )
            self.assertEqual(
                calls, [],
                "build_desktop_setup_view opened a network "
                "socket; Phase 10P explicitly forbids network IO",
            )


if __name__ == "__main__":
    unittest.main()
