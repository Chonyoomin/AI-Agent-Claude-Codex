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


# ---------------------------------------------------------------------------
# Desktop signatures
# ---------------------------------------------------------------------------
class DesktopSignatureTests(unittest.TestCase):

    def test_controls_signature_tracks_render_relevant_fields(self) -> None:
        controls = [{
            "label": "Run one cycle",
            "enabled": True,
            "clipboard_payload": "python scripts/agent_loop.py run",
            "ignored": "x",
        }]
        self.assertEqual(
            agent_loop._desktop_controls_signature(controls),
            ((
                "Run one cycle",
                True,
                "python scripts/agent_loop.py run",
            ),),
        )

    def test_ack_signature_supports_server_action_and_source_rows(
        self,
    ) -> None:
        self.assertEqual(
            agent_loop._desktop_ack_signature(
                [{"id": "docs", "display_name": "Local Repo Docs"}],
                kind="server",
            ),
            (("docs", "Local Repo Docs"),),
        )
        self.assertEqual(
            agent_loop._desktop_ack_signature(
                [{
                    "action_id": "open_docs",
                    "display_name": "Open docs",
                    "approval_policy": "per_action_explicit_approval",
                }],
                kind="action",
            ),
            ((
                "open_docs",
                "Open docs",
                "per_action_explicit_approval",
            ),),
        )
        self.assertEqual(
            agent_loop._desktop_ack_signature(
                [{"id": "prd", "display_name": "PRD upload"}],
                kind="source",
            ),
            (("prd", "PRD upload"),),
        )

    def test_ack_signature_rejects_unsupported_kind(self) -> None:
        with self.assertRaises(ValueError):
            agent_loop._desktop_ack_signature([], kind="unknown")

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
# _desktop_replace_text_preserving_view
# ---------------------------------------------------------------------------
class DesktopReplaceTextPreservingViewTests(unittest.TestCase):

    class _FakeTextWidget:
        def __init__(
            self,
            *,
            content: str = "",
            yview: tuple = (0.0, 1.0),
        ) -> None:
            self.content = content
            self._yview = yview
            self.delete_calls = 0
            self.insert_calls = 0
            self.moveto_calls: list[float] = []

        def get(self, _start: str, _end: str) -> str:
            return self.content

        def yview(self) -> tuple:
            return self._yview

        def delete(self, _start: str, _end: str) -> None:
            self.delete_calls += 1
            self.content = ""

        def insert(self, _start: str, value: str) -> None:
            self.insert_calls += 1
            self.content = value

        def yview_moveto(self, fraction: float) -> None:
            self.moveto_calls.append(fraction)
            self._yview = (fraction, fraction)

    def test_rewrites_content_and_restores_scroll_fraction(
        self,
    ) -> None:
        widget = self._FakeTextWidget(
            content="old\n",
            yview=(0.42, 0.88),
        )
        agent_loop._desktop_replace_text_preserving_view(
            widget,
            ["new line 1", "new line 2"],
        )
        self.assertEqual(
            widget.content,
            "new line 1\nnew line 2\n",
        )
        self.assertEqual(widget.delete_calls, 1)
        self.assertEqual(widget.insert_calls, 1)
        self.assertEqual(widget.moveto_calls, [0.42])

    def test_skips_rewrite_when_rendered_text_unchanged(
        self,
    ) -> None:
        widget = self._FakeTextWidget(
            content="same\nbody\n",
            yview=(0.25, 0.9),
        )
        agent_loop._desktop_replace_text_preserving_view(
            widget,
            ["same", "body"],
        )
        self.assertEqual(widget.delete_calls, 0)
        self.assertEqual(widget.insert_calls, 0)
        self.assertEqual(widget.moveto_calls, [0.25])


# ---------------------------------------------------------------------------
# _desktop_activity_popup_payload
# ---------------------------------------------------------------------------
class DesktopActivityPopupPayloadTests(unittest.TestCase):

    def test_claude_implementing_shows_combobulating(self) -> None:
        payload = agent_loop._desktop_activity_popup_payload(
            "claude_implementing",
        )
        self.assertEqual(payload["status"], "claude_implementing")
        self.assertIn("Combobulating", payload["title"])
        self.assertIn("Claude", payload["detail"])

    def test_claude_fixing_shows_recombobulating(self) -> None:
        payload = agent_loop._desktop_activity_popup_payload(
            "claude_fixing",
        )
        self.assertEqual(payload["status"], "claude_fixing")
        self.assertIn("Re-combobulating", payload["title"])

    def test_awaiting_codex_review_shows_codex_message(self) -> None:
        payload = agent_loop._desktop_activity_popup_payload(
            "awaiting_codex_review",
        )
        self.assertEqual(payload["status"], "awaiting_codex_review")
        self.assertIn("Codex", payload["detail"])

    def test_evidence_capture_shows_receipts_message(self) -> None:
        payload = agent_loop._desktop_activity_popup_payload(
            "evidence_capture",
        )
        self.assertEqual(payload["status"], "evidence_capture")
        self.assertIn("receipts", payload["title"])

    def test_idle_status_has_no_popup(self) -> None:
        self.assertIsNone(
            agent_loop._desktop_activity_popup_payload(
                "awaiting_claude_implementation",
            )
        )

    def test_non_string_status_has_no_popup(self) -> None:
        self.assertIsNone(
            agent_loop._desktop_activity_popup_payload(None)
        )


# ---------------------------------------------------------------------------
# _desktop_native_summary_payload
# ---------------------------------------------------------------------------
class DesktopNativeSummaryPayloadTests(unittest.TestCase):

    def test_extracts_compact_summary_from_view(self) -> None:
        view = {
            "controller_path_canonical": "/tmp/controller",
            "status_view": {
                "advisory_status_label": "in-flight (claude_implementing)",
                "controller": {
                    "loop_state": {
                        "mirror": {
                            "phase": "Phase 10 - Future Product Features",
                            "sub_phase": "Phase 10V - RAG Source Selection",
                            "task": "Implement the desktop app summary",
                            "cycle_count": 1,
                            "max_cycles": 3,
                        },
                    },
                },
            },
            "controls_view": {
                "current_loop_state_status": "claude_implementing",
            },
            "dashboard_view": {
                "surfaces": {
                    "review_summaries": {
                        "current_verdict": "NEEDS_FIXES",
                    },
                    "failure_analytics": {
                        "issue_count_in_latest_review": 2,
                    },
                },
            },
            "run_profiles_view": {
                "mirror": {
                    "approval_mode": "review",
                },
            },
            "project_start_view": {
                "target_attach": {
                    "summary": "attached to sample target",
                },
            },
            "setup_view": {
                "adapter_env": {
                    "summary": "manual handoff adapters active",
                },
            },
        }
        payload = agent_loop._desktop_native_summary_payload(view)
        self.assertEqual(payload["window_title"], "Agent Loop Desktop")
        self.assertEqual(
            payload["status_label"],
            "in-flight (claude_implementing)",
        )
        self.assertEqual(
            payload["phase"], "Phase 10 - Future Product Features",
        )
        self.assertEqual(
            payload["sub_phase"], "Phase 10V - RAG Source Selection",
        )
        self.assertEqual(
            payload["task"], "Implement the desktop app summary",
        )
        self.assertEqual(payload["approval_mode"], "review")
        self.assertEqual(payload["cycle_progress"], "1 / 3 cycles")
        self.assertEqual(payload["review_verdict"], "NEEDS_FIXES")
        self.assertEqual(payload["issue_count"], 2)
        self.assertEqual(
            payload["target_summary"], "attached to sample target",
        )
        self.assertEqual(
            payload["adapter_summary"],
            "manual handoff adapters active",
        )
        self.assertEqual(
            payload["current_loop_state_status"],
            "claude_implementing",
        )

    def test_missing_fields_soft_fall_back(self) -> None:
        payload = agent_loop._desktop_native_summary_payload({})
        self.assertEqual(payload["status_label"], "Status unavailable")
        self.assertEqual(payload["phase"], "Unknown phase")
        self.assertEqual(payload["sub_phase"], "Unknown sub-phase")
        self.assertEqual(payload["task"], "No active task loaded")
        self.assertEqual(payload["approval_mode"], "Unknown")
        self.assertEqual(payload["review_verdict"], "No review verdict yet")


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
            "run_profiles_view": {
                "error": "test run profiles error", "view": None,
            },
            "project_start_view": {
                "error": "test project start error",
                "view": None,
            },
            "mcp_assistance_view": {
                "error": "test mcp assistance error",
                "view": None,
            },
            "mcp_action_guardrails_view": {
                "error": "test mcp action guardrails error",
                "view": None,
            },
            "rag_source_selection_view": {
                "error": "test rag source selection error",
                "view": None,
            },
            "rag_retrieval_controls_view": {
                "error": "test rag retrieval controls error",
                "view": None,
            },
            "run_console_view": {
                "error": "test run console error",
                "view": None,
            },
            "resume_console_view": {
                "error": "test resume console error",
                "view": None,
            },
            "selection_view": {
                "error": "test selection error",
                "view": None,
            },
            "memory_vault_view": {
                "error": "test memory vault error",
                "view": None,
            },
            "concurrency_view": {
                "error": "test concurrency error",
                "view": None,
            },
            "overlap_detection_view": {
                "error": "test overlap detection error",
                "view": None,
            },
            "codex_concurrent_work_view": {
                "error": "test codex concurrent work error",
                "view": None,
            },
            "framework_evaluation_view": {
                "error": "test framework evaluation error",
                "view": None,
            },
            "precedence_note": "x",
        }
        lines = agent_loop.render_desktop_app_text(view)
        output = "\n".join(lines)
        self.assertIn("[error] 'test status error'", output)
        self.assertIn("[error] 'test setup error'", output)
        self.assertIn(
            "[error] 'test run profiles error'", output,
        )
        self.assertIn(
            "[error] 'test project start error'", output,
        )
        self.assertIn(
            "[error] 'test mcp assistance error'", output,
        )
        self.assertIn(
            "[error] 'test mcp action guardrails error'", output,
        )
        self.assertIn(
            "[error] 'test rag source selection error'", output,
        )
        self.assertIn(
            "[error] 'test rag retrieval controls error'",
            output,
        )
        self.assertIn(
            "[error] 'test run console error'", output,
        )
        self.assertIn(
            "[error] 'test resume console error'", output,
        )
        self.assertIn(
            "[error] 'test selection error'", output,
        )
        self.assertIn(
            "[error] 'test memory vault error'", output,
        )
        self.assertIn(
            "[error] 'test concurrency error'", output,
        )
        self.assertIn(
            "[error] 'test overlap detection error'", output,
        )
        self.assertIn(
            "[error] 'test codex concurrent work error'", output,
        )
        self.assertIn(
            "[error] 'test framework evaluation error'", output,
        )


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


# ---------------------------------------------------------------------------
# Simplified desktop UI (human-directed): three primary controls
# ---------------------------------------------------------------------------
class PrimaryDesktopControlsHelpersTests(unittest.TestCase):
    """Cover the pure module-level helpers backing the simplified
    Run/Stop + Code Review + approval-mode dropdown UI. Kept
    Tk-free so the helpers can be exercised on a headless CI
    without importing tkinter.
    """

    def test_approval_modes_closed_enum(self) -> None:
        # The dropdown MUST use exactly the three shipped Phase 5A
        # approval modes; no invented mode name.
        self.assertEqual(
            agent_loop.PRIMARY_DESKTOP_APPROVAL_MODES,
            (
                agent_loop.APPROVAL_MODE_REVIEW,
                agent_loop.APPROVAL_MODE_STRICT,
                agent_loop.APPROVAL_MODE_AUTONOMOUS,
            ),
        )

    def test_run_button_label_toggles(self) -> None:
        # The Run/Stop toggle is the whole point of the button; the
        # False -> "Run", True -> "Stop" contract must stay pinned.
        self.assertEqual(
            agent_loop._primary_desktop_run_button_label(False),
            "Run",
        )
        self.assertEqual(
            agent_loop._primary_desktop_run_button_label(True),
            "Stop",
        )

    def test_read_approval_mode_from_loop_state(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            # Default fixture sets approval_mode="review".
            self.assertEqual(
                agent_loop._primary_desktop_read_approval_mode(
                    controller,
                ),
                "review",
            )

    def test_read_approval_mode_soft_fails_to_review(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            (controller / ".agent-loop" / "loop-state.json").unlink()
            # Missing loop-state MUST soft-fail to the shipped
            # default rather than raise.
            self.assertEqual(
                agent_loop._primary_desktop_read_approval_mode(
                    controller,
                ),
                "review",
            )

    def test_write_approval_mode_persists(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            agent_loop._primary_desktop_write_approval_mode(
                controller, "strict",
            )
            data = json.loads(
                (controller / ".agent-loop" / "loop-state.json")
                .read_text(encoding="utf-8"),
            )
            self.assertEqual(data["approval_mode"], "strict")

    def test_write_approval_mode_refuses_unknown_value(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            state_path = (
                controller / ".agent-loop" / "loop-state.json"
            )
            before = state_path.read_bytes()
            with self.assertRaises(agent_loop.HaltError) as cm:
                agent_loop._primary_desktop_write_approval_mode(
                    controller, "not-a-real-mode",
                )
            after = state_path.read_bytes()
        self.assertIn(
            "not-a-real-mode", cm.exception.reason,
        )
        # The refusal MUST NOT have written a garbage value.
        self.assertEqual(before, after)

    def test_write_approval_mode_covers_every_shipped_mode(
        self,
    ) -> None:
        # Every closed-enum member must persist cleanly so the
        # dropdown can flip to any shipped mode without a refusal
        # on the happy path.
        for mode in agent_loop.PRIMARY_DESKTOP_APPROVAL_MODES:
            with TemporaryDirectory() as td:
                controller = _make_controller(Path(td) / "c")
                agent_loop._primary_desktop_write_approval_mode(
                    controller, mode,
                )
                data = json.loads(
                    (controller / ".agent-loop" / "loop-state.json")
                    .read_text(encoding="utf-8"),
                )
                self.assertEqual(data["approval_mode"], mode, mode)

    def test_build_run_command_shape(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            cmd = agent_loop._primary_desktop_build_run_command(
                controller,
            )
        self.assertEqual(cmd[0], sys.executable)
        # The `run` subcommand is the shipped Phase 5B primary
        # entry that runs a normal cycle.
        self.assertEqual(cmd[-1], "run")
        # The script path MUST resolve to agent_loop.py (per
        # inspection). Kept as a tolerant assertion so a future
        # rename can be caught by grep rather than a brittle
        # equality check.
        self.assertTrue(
            cmd[1].endswith("agent_loop.py")
            or cmd[1].endswith("agent_loop.pyc"),
            cmd[1],
        )

    def test_build_code_review_command_shape(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            cmd = (
                agent_loop._primary_desktop_build_code_review_command(
                    controller,
                )
            )
        self.assertEqual(cmd[0], sys.executable)
        # `resume` is the shipped subcommand that continues the
        # cycle past the Codex review gate.
        self.assertEqual(cmd[-1], "resume")


# ---------------------------------------------------------------------------
# Native folder-browse UX (human-directed)
# ---------------------------------------------------------------------------
class PrimaryDesktopFolderBrowseHelpersTests(unittest.TestCase):
    """Cover the module-level helpers backing the "Select Project
    Folder" primary button. Kept Tk-free so the helpers can be
    exercised on a headless CI without importing tkinter.
    """

    def test_normalize_selected_folder_none(self) -> None:
        self.assertIsNone(
            agent_loop._primary_desktop_normalize_selected_folder(
                None,
            ),
        )

    def test_normalize_selected_folder_empty_string(self) -> None:
        self.assertIsNone(
            agent_loop._primary_desktop_normalize_selected_folder(
                "",
            ),
        )

    def test_normalize_selected_folder_whitespace(self) -> None:
        self.assertIsNone(
            agent_loop._primary_desktop_normalize_selected_folder(
                "   ",
            ),
        )

    def test_normalize_selected_folder_empty_tuple(self) -> None:
        # macOS Tk's askdirectory returns an empty tuple on cancel;
        # both empty-tuple and empty-list MUST normalize to None so
        # the desktop shell never dispatches an attach on cancel.
        self.assertIsNone(
            agent_loop._primary_desktop_normalize_selected_folder(
                (),
            ),
        )
        self.assertIsNone(
            agent_loop._primary_desktop_normalize_selected_folder(
                [],
            ),
        )

    def test_normalize_selected_folder_stripped_path(self) -> None:
        self.assertEqual(
            agent_loop._primary_desktop_normalize_selected_folder(
                "  /tmp/project  ",
            ),
            "/tmp/project",
        )

    def test_normalize_selected_folder_non_string(self) -> None:
        # A wrong-typed dialog result MUST normalize to None rather
        # than crash the callback with an AttributeError.
        self.assertIsNone(
            agent_loop._primary_desktop_normalize_selected_folder(
                42,
            ),
        )

    def test_format_attached_target_label_none(self) -> None:
        self.assertEqual(
            (
                agent_loop
                ._primary_desktop_format_attached_target_label(None)
            ),
            "Attached project: (none)",
        )

    def test_format_attached_target_label_present(self) -> None:
        self.assertEqual(
            (
                agent_loop
                ._primary_desktop_format_attached_target_label(
                    "/tmp/project",
                )
            ),
            "Attached project: /tmp/project",
        )

    def test_read_attached_target_path_returns_none_when_unattached(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            # Fresh controller has no attach record on disk.
            self.assertIsNone(
                agent_loop._primary_desktop_read_attached_target_path(
                    controller,
                ),
            )

    def test_read_attached_target_path_after_attach(self) -> None:
        # An attach must surface the canonical target path in the
        # helper's read so the desktop Label can display it.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "controller")
            target = Path(td) / "target-project"
            target.mkdir()
            (target / "TASK.md").write_text("# t", encoding="utf-8")
            (target / ".agent-loop").mkdir()
            for name in (
                "current-task.md",
                "current-phase.md",
                "phase-plan.md",
            ):
                (target / ".agent-loop" / name).write_text(
                    "x", encoding="utf-8",
                )
            (target / ".agent-loop" / "loop-state.json").write_text(
                json.dumps({
                    "phase": "Phase 10 - Future Product Features",
                    "sub_phase": "Phase 10AE",
                    "task": "external-target-attach-test",
                    "status": "awaiting_claude_implementation",
                    "cycle_count": 0,
                    "max_cycles": 3,
                    "last_verdict": None,
                    "last_verdict_phase": None,
                    "contract_version": CONTRACT_VERSION,
                    "claude_version": None,
                    "codex_version": None,
                    "orchestrator_version": "phase-3d-v0",
                    "approval_mode": "review",
                    "awaiting_human_for": None,
                }),
                encoding="utf-8",
            )
            agent_loop.attach_external_target(
                controller,
                target_path=str(target),
                attached_by="test-operator",
                approval_mode="review",
            )
            got = (
                agent_loop
                ._primary_desktop_read_attached_target_path(
                    controller,
                )
            )
        self.assertIsNotNone(got)
        # The canonical resolved form MUST match the target we
        # attached (allowing platform-native separators).
        self.assertTrue(
            got.replace("\\", "/").endswith("target-project"),
            got,
        )

    def test_format_attach_cli_guidance_pins_shape(self) -> None:
        # Fix Phase B1 fix cycle: the full-target attach path
        # surfaces the shipped `attach-external-target` CLI as
        # copy-paste-ready guidance. The `--attached-by` slot MUST
        # remain a `<NAME>` placeholder so the desktop shell never
        # auto-fills a synthetic operator identity into the
        # controller-owned attach record.
        got = agent_loop._primary_desktop_format_attach_cli_guidance(
            target_path="/tmp/my-project",
            approval_mode="review",
        )
        self.assertIn("attach-external-target", got)
        self.assertIn("--target-path \"/tmp/my-project\"", got)
        self.assertIn("--attached-by <NAME>", got)
        self.assertIn("--approval-mode \"review\"", got)
        self.assertNotIn("desktop-ui-operator", got)
        self.assertNotIn("--bootstrap", got)

    def test_format_attach_cli_guidance_refuses_missing_target(
        self,
    ) -> None:
        for bad in (None, "", "   ", 42):
            with self.assertRaises(agent_loop.HaltError):
                agent_loop._primary_desktop_format_attach_cli_guidance(
                    target_path=bad,  # type: ignore[arg-type]
                    approval_mode="review",
                )

    def test_format_attach_cli_guidance_refuses_missing_mode(
        self,
    ) -> None:
        for bad in (None, "", "   ", 42):
            with self.assertRaises(agent_loop.HaltError):
                agent_loop._primary_desktop_format_attach_cli_guidance(
                    target_path="/tmp/my-project",
                    approval_mode=bad,  # type: ignore[arg-type]
                )

    def test_attach_cli_guidance_does_not_dispatch(self) -> None:
        # UX-only helper: building the CLI guidance MUST NOT call
        # the shipped `attach_external_target(...)` runtime. This
        # pins the Fix Phase B1 fix cycle boundary that the desktop
        # shell surfaces guidance instead of triggering canonical
        # mutation from the Tk callback.
        with mock.patch.object(
            agent_loop,
            "attach_external_target",
        ) as p:
            agent_loop._primary_desktop_format_attach_cli_guidance(
                target_path="/tmp/my-project",
                approval_mode="review",
            )
        p.assert_not_called()

    def test_format_attach_cli_guidance_refuses_quote_in_target(
        self,
    ) -> None:
        # Fix Phase B1 second fix cycle: an embedded double-quote
        # in a value would break the copy-paste-ready CLI regardless
        # of which shell the operator pastes into (POSIX / cmd /
        # PowerShell all treat `"` as a quote delimiter but differ
        # on how to escape an embedded `"`). Refuse fail-closed so
        # the desktop shell never surfaces a syntactically broken
        # command.
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop._primary_desktop_format_attach_cli_guidance(
                target_path="/tmp/bad\"name",
                approval_mode="review",
            )
        self.assertIn("target_path", cm.exception.reason)
        self.assertIn("double quote", cm.exception.reason)

    def test_format_attach_cli_guidance_refuses_quote_in_mode(
        self,
    ) -> None:
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop._primary_desktop_format_attach_cli_guidance(
                target_path="/tmp/my-project",
                approval_mode="re\"view",
            )
        self.assertIn("approval_mode", cm.exception.reason)
        self.assertIn("double quote", cm.exception.reason)


# ---------------------------------------------------------------------------
# Fix Phase B1 - Desktop Bootstrap UX Contract
# ---------------------------------------------------------------------------
class PrimaryDesktopBootstrapUxContractTests(unittest.TestCase):
    """Cover the module-level helpers that back the Fix Phase B1
    desktop bootstrap UX contract: closed mode enum, closed
    bootstrap-field enum, classification-to-mode mapping, form
    validator, folder-classification wrapper, and the bootstrap
    dispatch wrapper.
    """

    def test_folder_ux_modes_closed_enum(self) -> None:
        self.assertEqual(
            agent_loop.PRIMARY_DESKTOP_FOLDER_UX_MODES,
            (
                "attach_existing_project",
                "bootstrap_new_project",
                "refused_partial_target",
                "refused_malformed_target",
            ),
        )

    def test_bootstrap_field_names_closed_enum(self) -> None:
        # The desktop UI MUST prompt for exactly these five fields
        # in this order; no invented field, no auto-filled field.
        self.assertEqual(
            agent_loop.PRIMARY_DESKTOP_BOOTSTRAP_FIELD_NAMES,
            (
                "attached_by",
                "approval_mode",
                "bootstrapped_by",
                "human_objective",
                "project_intent",
            ),
        )

    def test_next_step_copy_pins_activation_boundary(self) -> None:
        copy = agent_loop.PRIMARY_DESKTOP_BOOTSTRAP_NEXT_STEP_COPY
        # The copy MUST name the shipped boundary explicitly so the
        # operator sees that bootstrap != activation.
        self.assertIn("awaiting_first_activation", copy)
        self.assertIn("Phase 4C activator", copy)
        self.assertIn("APPROVED_FOR_ACTIVATION", copy)

    def test_derive_folder_ux_mode_full_target(self) -> None:
        self.assertEqual(
            agent_loop._primary_desktop_derive_folder_ux_mode(
                "full_target",
            ),
            "attach_existing_project",
        )

    def test_derive_folder_ux_mode_empty_target(self) -> None:
        self.assertEqual(
            agent_loop._primary_desktop_derive_folder_ux_mode(
                "empty_target",
            ),
            "bootstrap_new_project",
        )

    def test_derive_folder_ux_mode_partial_target(self) -> None:
        self.assertEqual(
            agent_loop._primary_desktop_derive_folder_ux_mode(
                "partial_target",
            ),
            "refused_partial_target",
        )

    def test_derive_folder_ux_mode_malformed_target(self) -> None:
        self.assertEqual(
            agent_loop._primary_desktop_derive_folder_ux_mode(
                "malformed_target",
            ),
            "refused_malformed_target",
        )

    def test_derive_folder_ux_mode_unknown_refuses(self) -> None:
        # A vocabulary-drift refusal MUST fire fail-closed so the
        # desktop UI cannot silently pick a wrong mode.
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._primary_desktop_derive_folder_ux_mode(
                "invented_state",
            )

    def test_classify_folder_for_ux_missing_path(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._primary_desktop_classify_folder_for_ux(
                None,
            )

    def test_classify_folder_for_ux_empty_path(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._primary_desktop_classify_folder_for_ux(
                "  ",
            )

    def test_classify_folder_for_ux_non_directory(self) -> None:
        with TemporaryDirectory() as td:
            file_path = Path(td) / "not-a-directory"
            file_path.write_text("x", encoding="utf-8")
            with self.assertRaises(agent_loop.HaltError):
                agent_loop._primary_desktop_classify_folder_for_ux(
                    str(file_path),
                )

    def test_classify_folder_for_ux_empty_directory(self) -> None:
        with TemporaryDirectory() as td:
            empty = Path(td) / "empty-target"
            empty.mkdir()
            self.assertEqual(
                agent_loop._primary_desktop_classify_folder_for_ux(
                    str(empty),
                ),
                "empty_target",
            )

    def test_classify_folder_for_ux_full_directory(self) -> None:
        with TemporaryDirectory() as td:
            full = Path(td) / "full-target"
            full.mkdir()
            (full / "TASK.md").write_text(
                "# t", encoding="utf-8",
            )
            (full / ".agent-loop").mkdir()
            for name in (
                "current-task.md",
                "current-phase.md",
                "phase-plan.md",
            ):
                (full / ".agent-loop" / name).write_text(
                    "x", encoding="utf-8",
                )
            (full / ".agent-loop" / "loop-state.json").write_text(
                json.dumps({
                    "phase": "Phase 10 - Future Product Features",
                    "sub_phase": "Phase 10AE",
                    "task": "external-target-classification-test",
                    "status": "awaiting_claude_implementation",
                    "cycle_count": 0,
                    "max_cycles": 3,
                    "last_verdict": None,
                    "last_verdict_phase": None,
                    "contract_version": CONTRACT_VERSION,
                    "claude_version": None,
                    "codex_version": None,
                    "orchestrator_version": "phase-3d-v0",
                    "approval_mode": "review",
                    "awaiting_human_for": None,
                }),
                encoding="utf-8",
            )
            self.assertEqual(
                agent_loop._primary_desktop_classify_folder_for_ux(
                    str(full),
                ),
                "full_target",
            )

    def test_classify_folder_for_ux_partial_directory(self) -> None:
        with TemporaryDirectory() as td:
            partial = Path(td) / "partial-target"
            partial.mkdir()
            (partial / "TASK.md").write_text(
                "# t", encoding="utf-8",
            )
            # Missing every .agent-loop artifact -> partial_target.
            self.assertEqual(
                agent_loop._primary_desktop_classify_folder_for_ux(
                    str(partial),
                ),
                "partial_target",
            )

    def test_validate_bootstrap_form_all_fields_present(
        self,
    ) -> None:
        fields = {
            "attached_by": "alice",
            "approval_mode": "review",
            "bootstrapped_by": "alice",
            "human_objective": "Build a bounded thing.",
            "project_intent": "Ship a bounded slice.",
        }
        # Happy path: no exception.
        agent_loop._primary_desktop_validate_bootstrap_form(fields)

    def test_validate_bootstrap_form_missing_field_refuses(
        self,
    ) -> None:
        for missing in (
            "attached_by",
            "approval_mode",
            "bootstrapped_by",
            "human_objective",
            "project_intent",
        ):
            fields = {
                "attached_by": "alice",
                "approval_mode": "review",
                "bootstrapped_by": "alice",
                "human_objective": "obj",
                "project_intent": "intent",
            }
            del fields[missing]
            with self.assertRaises(agent_loop.HaltError) as cm:
                agent_loop._primary_desktop_validate_bootstrap_form(
                    fields,
                )
            self.assertIn(missing, cm.exception.reason, missing)

    def test_validate_bootstrap_form_empty_field_refuses(
        self,
    ) -> None:
        fields = {
            "attached_by": "alice",
            "approval_mode": "review",
            "bootstrapped_by": "alice",
            "human_objective": "   ",
            "project_intent": "intent",
        }
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._primary_desktop_validate_bootstrap_form(
                fields,
            )

    def test_validate_bootstrap_form_non_dict_refuses(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._primary_desktop_validate_bootstrap_form(
                "not a dict",
            )

    def test_format_bootstrap_cli_guidance_pins_shape(self) -> None:
        # Fix Phase B1 fix cycle: the bootstrap dialog surfaces the
        # shipped `attach-external-target --bootstrap ...` CLI as
        # copy-paste-ready guidance. Every field the operator typed
        # into the form MUST appear in the surfaced CLI so the
        # operator can paste it verbatim into their terminal.
        got = (
            agent_loop._primary_desktop_format_bootstrap_cli_guidance(
                target_path="/tmp/new-project",
                approval_mode="review",
                attached_by="alice",
                bootstrapped_by="alice",
                human_objective="Build a bounded thing.",
                project_intent="Ship a bounded slice.",
            )
        )
        self.assertIn("attach-external-target", got)
        self.assertIn("--target-path \"/tmp/new-project\"", got)
        self.assertIn("--attached-by \"alice\"", got)
        self.assertIn("--approval-mode \"review\"", got)
        self.assertIn("--bootstrap", got)
        self.assertIn("--bootstrapped-by \"alice\"", got)
        self.assertIn(
            "--human-objective \"Build a bounded thing.\"", got,
        )
        self.assertIn(
            "--project-intent \"Ship a bounded slice.\"", got,
        )
        self.assertNotIn("<NAME>", got)
        self.assertNotIn("<TEXT>", got)

    def test_format_bootstrap_cli_guidance_refuses_each_missing_field(
        self,
    ) -> None:
        # Each of the six required fields MUST refuse fail-closed
        # when missing / empty / whitespace-only so the surfaced CLI
        # is never rendered with an empty argument slot.
        base = {
            "target_path": "/tmp/new-project",
            "approval_mode": "review",
            "attached_by": "alice",
            "bootstrapped_by": "alice",
            "human_objective": "obj",
            "project_intent": "intent",
        }
        for missing in base:
            for bad in (None, "", "   "):
                fields = dict(base)
                fields[missing] = bad  # type: ignore[assignment]
                with self.assertRaises(agent_loop.HaltError) as cm:
                    (
                        agent_loop
                        ._primary_desktop_format_bootstrap_cli_guidance(
                            **fields,
                        )
                    )
                self.assertIn(
                    missing, cm.exception.reason, (missing, bad),
                )

    def test_bootstrap_cli_guidance_does_not_dispatch(self) -> None:
        # UX-only helper: building the bootstrap CLI guidance MUST
        # NOT call the shipped `attach_external_target(...)`
        # runtime. This pins the Fix Phase B1 fix cycle boundary
        # that the bootstrap dialog surfaces guidance instead of
        # triggering canonical mutation from the Tk callback.
        with mock.patch.object(
            agent_loop,
            "attach_external_target",
        ) as p:
            (
                agent_loop
                ._primary_desktop_format_bootstrap_cli_guidance(
                    target_path="/tmp/new-project",
                    approval_mode="review",
                    attached_by="alice",
                    bootstrapped_by="alice",
                    human_objective="obj",
                    project_intent="intent",
                )
            )
        p.assert_not_called()

    def test_format_bootstrap_cli_guidance_refuses_embedded_quote(
        self,
    ) -> None:
        # Fix Phase B1 second fix cycle: an embedded double-quote
        # in ANY field would break the copy-paste-ready CLI
        # regardless of which shell the operator pastes into.
        # Refuse fail-closed on every field, including the
        # free-text `human_objective` and `project_intent` where an
        # operator is most likely to type quotes for emphasis.
        base = {
            "target_path": "/tmp/new-project",
            "approval_mode": "review",
            "attached_by": "alice",
            "bootstrapped_by": "alice",
            "human_objective": "Build a bounded thing.",
            "project_intent": "Ship a bounded slice.",
        }
        for tainted in base:
            fields = dict(base)
            fields[tainted] = fields[tainted] + " with a \" mark"
            with self.assertRaises(agent_loop.HaltError) as cm:
                (
                    agent_loop
                    ._primary_desktop_format_bootstrap_cli_guidance(
                        **fields,
                    )
                )
            self.assertIn(tainted, cm.exception.reason, tainted)
            self.assertIn(
                "double quote", cm.exception.reason, tainted,
            )

    def test_removed_dispatch_helpers_are_gone(self) -> None:
        # Fix Phase B1 fix cycle: the previous dispatch wrappers and
        # the auto-fill identity constant are removed from the
        # module surface so no code path can accidentally re-wire
        # canonical mutation into the desktop Tk callback.
        self.assertFalse(
            hasattr(
                agent_loop, "PRIMARY_DESKTOP_ATTACHED_BY_DEFAULT",
            ),
        )
        self.assertFalse(
            hasattr(
                agent_loop,
                "_primary_desktop_attach_selected_folder",
            ),
        )
        self.assertFalse(
            hasattr(
                agent_loop,
                "_primary_desktop_bootstrap_selected_folder",
            ),
        )


# ---------------------------------------------------------------------------
# Fix Phase B2 - Desktop Bootstrap Form And Validation
# ---------------------------------------------------------------------------
class PrimaryDesktopBootstrapFormClassifierTests(unittest.TestCase):
    """Cover the Fix Phase B2 pure classifier
    `_primary_desktop_classify_bootstrap_form_refusal(...)` and its
    fail-closed wrapper `_primary_desktop_validate_bootstrap_form(
    ...)`. The classifier returns None on a passing form, else a
    dict with the offending field, closed refusal category, and
    human-readable reason. Kept Tk-free so the branches are
    exercised on a headless CI.
    """

    def _base_valid_fields(self) -> dict:
        return {
            "attached_by": "alice",
            "approval_mode": "review",
            "bootstrapped_by": "alice",
            "human_objective": "Build a bounded thing.",
            "project_intent": "Ship a bounded slice.",
        }

    def test_refusal_categories_closed_enum(self) -> None:
        self.assertEqual(
            agent_loop.PRIMARY_DESKTOP_BOOTSTRAP_REFUSAL_CATEGORIES,
            (
                "input_non_dict",
                "field_missing",
                "field_wrong_type",
                "field_empty",
                "field_embedded_double_quote",
                "approval_mode_not_in_shipped_enum",
                "bootstrapped_by_does_not_match_attached_by",
            ),
        )

    def test_classifier_returns_none_on_valid_form(self) -> None:
        self.assertIsNone(
            agent_loop._primary_desktop_classify_bootstrap_form_refusal(
                self._base_valid_fields(),
            ),
        )

    def test_classifier_returns_input_non_dict(self) -> None:
        got = (
            agent_loop
            ._primary_desktop_classify_bootstrap_form_refusal(
                "not a dict",
            )
        )
        self.assertIsNotNone(got)
        self.assertEqual(got["category"], "input_non_dict")
        # Not field-scoped: the offending-field slot is None so the
        # Tk callback does not try to focus a non-existent entry.
        self.assertIsNone(got["field"])
        self.assertIn("dict", got["reason"])

    def test_classifier_returns_field_missing(self) -> None:
        # Every field must trigger the missing branch when absent.
        for missing in (
            "attached_by",
            "approval_mode",
            "bootstrapped_by",
            "human_objective",
            "project_intent",
        ):
            fields = self._base_valid_fields()
            del fields[missing]
            got = (
                agent_loop
                ._primary_desktop_classify_bootstrap_form_refusal(
                    fields,
                )
            )
            self.assertIsNotNone(got, missing)
            self.assertEqual(got["category"], "field_missing", missing)
            self.assertEqual(got["field"], missing)
            self.assertIn(missing, got["reason"])

    def test_classifier_returns_field_wrong_type(self) -> None:
        fields = self._base_valid_fields()
        fields["human_objective"] = 42
        got = (
            agent_loop
            ._primary_desktop_classify_bootstrap_form_refusal(fields)
        )
        self.assertIsNotNone(got)
        self.assertEqual(got["category"], "field_wrong_type")
        self.assertEqual(got["field"], "human_objective")

    def test_classifier_returns_field_empty(self) -> None:
        for empty in ("", "   ", "\t\n"):
            fields = self._base_valid_fields()
            fields["project_intent"] = empty
            got = (
                agent_loop
                ._primary_desktop_classify_bootstrap_form_refusal(
                    fields,
                )
            )
            self.assertIsNotNone(got, empty)
            self.assertEqual(got["category"], "field_empty", empty)
            self.assertEqual(got["field"], "project_intent")

    def test_classifier_returns_field_embedded_quote(self) -> None:
        # Embedded double quote in any field surfaces early so the
        # operator sees the refusal at form-validation time instead
        # of at CLI-format time.
        for tainted in (
            "attached_by",
            "approval_mode",
            "bootstrapped_by",
            "human_objective",
            "project_intent",
        ):
            fields = self._base_valid_fields()
            fields[tainted] = fields[tainted] + " with \" mark"
            got = (
                agent_loop
                ._primary_desktop_classify_bootstrap_form_refusal(
                    fields,
                )
            )
            self.assertIsNotNone(got, tainted)
            self.assertEqual(
                got["category"],
                "field_embedded_double_quote",
                tainted,
            )
            self.assertEqual(got["field"], tainted)

    def test_classifier_returns_approval_mode_not_in_enum(
        self,
    ) -> None:
        fields = self._base_valid_fields()
        fields["approval_mode"] = "invented_mode"
        got = (
            agent_loop
            ._primary_desktop_classify_bootstrap_form_refusal(fields)
        )
        self.assertIsNotNone(got)
        self.assertEqual(
            got["category"], "approval_mode_not_in_shipped_enum",
        )
        self.assertEqual(got["field"], "approval_mode")
        self.assertIn("invented_mode", got["reason"])

    def test_classifier_accepts_every_shipped_approval_mode(
        self,
    ) -> None:
        # Every shipped closed-enum value MUST pass the desktop
        # form validator so the desktop UI stays in lockstep with
        # the shipped Phase 10B contract.
        for mode in agent_loop.EXTERNAL_TARGET_APPROVAL_MODES:
            fields = self._base_valid_fields()
            fields["approval_mode"] = mode
            got = (
                agent_loop
                ._primary_desktop_classify_bootstrap_form_refusal(
                    fields,
                )
            )
            self.assertIsNone(got, mode)

    def test_classifier_returns_identity_mismatch(self) -> None:
        fields = self._base_valid_fields()
        fields["bootstrapped_by"] = "eve"
        got = (
            agent_loop
            ._primary_desktop_classify_bootstrap_form_refusal(fields)
        )
        self.assertIsNotNone(got)
        self.assertEqual(
            got["category"],
            "bootstrapped_by_does_not_match_attached_by",
        )
        self.assertEqual(got["field"], "bootstrapped_by")
        self.assertIn("alice", got["reason"])
        self.assertIn("eve", got["reason"])

    def test_classifier_identity_match_is_whitespace_stripped(
        self,
    ) -> None:
        # bootstrapped_by "  alice  " should equal attached_by
        # "alice" after whitespace-stripping, matching the shipped
        # Phase 10C single-operator-identity invariant.
        fields = self._base_valid_fields()
        fields["attached_by"] = "alice"
        fields["bootstrapped_by"] = "  alice  "
        self.assertIsNone(
            agent_loop
            ._primary_desktop_classify_bootstrap_form_refusal(fields),
        )

    def test_check_precedence_missing_before_enum(self) -> None:
        # Precedence pin: missing beats the closed-enum check so a
        # form with a missing approval_mode surfaces the missing
        # refusal rather than the enum refusal.
        fields = self._base_valid_fields()
        del fields["approval_mode"]
        got = (
            agent_loop
            ._primary_desktop_classify_bootstrap_form_refusal(fields)
        )
        self.assertIsNotNone(got)
        self.assertEqual(got["category"], "field_missing")

    def test_check_precedence_empty_before_identity_mismatch(
        self,
    ) -> None:
        # Precedence pin: per-field empty check beats the identity-
        # mismatch check so an empty bootstrapped_by surfaces the
        # empty refusal, not the mismatch refusal.
        fields = self._base_valid_fields()
        fields["bootstrapped_by"] = "   "
        got = (
            agent_loop
            ._primary_desktop_classify_bootstrap_form_refusal(fields)
        )
        self.assertIsNotNone(got)
        self.assertEqual(got["category"], "field_empty")

    def test_check_precedence_quote_before_enum(self) -> None:
        # Precedence pin: embedded-quote check beats the closed-
        # enum check so a quoted approval_mode surfaces the quote
        # refusal, not the enum refusal.
        fields = self._base_valid_fields()
        fields["approval_mode"] = "re\"view"
        got = (
            agent_loop
            ._primary_desktop_classify_bootstrap_form_refusal(fields)
        )
        self.assertIsNotNone(got)
        self.assertEqual(
            got["category"], "field_embedded_double_quote",
        )

    def test_validator_raises_halt_error_when_classifier_returns(
        self,
    ) -> None:
        # The fail-closed wrapper MUST raise HaltError whenever the
        # classifier returns non-None, using the same reason string
        # so the Tk dialog status Label matches the raised error.
        fields = self._base_valid_fields()
        fields["approval_mode"] = "invented_mode"
        expected = (
            agent_loop
            ._primary_desktop_classify_bootstrap_form_refusal(fields)
        )
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop._primary_desktop_validate_bootstrap_form(
                fields,
            )
        self.assertEqual(cm.exception.reason, expected["reason"])

    def test_validator_returns_none_on_valid_form(self) -> None:
        # Happy path: no exception, no return value.
        self.assertIsNone(
            agent_loop._primary_desktop_validate_bootstrap_form(
                self._base_valid_fields(),
            ),
        )


# ---------------------------------------------------------------------------
# Fix Phase B3 - Desktop Bootstrap Dispatch And Post-Bootstrap Handoff
# ---------------------------------------------------------------------------
class PrimaryDesktopBootstrapDispatchHelperTests(unittest.TestCase):
    """Cover the Fix Phase B3 dispatch wrapper
    `_primary_desktop_dispatch_bootstrap_attach(...)`: delegates
    verbatim to the shipped `attach_external_target(...,
    bootstrap=True, ...)` runtime; does NOT auto-fill any
    identity/free-text field; propagates HaltError so the Tk
    callback can surface refusals while preserving typed context.
    """

    def test_dispatch_wrapper_delegates_verbatim(self) -> None:
        with mock.patch.object(
            agent_loop,
            "attach_external_target",
        ) as p:
            p.return_value = Path("/tmp/attach-record.json")
            got = (
                agent_loop
                ._primary_desktop_dispatch_bootstrap_attach(
                    Path("/tmp/controller"),
                    target_path="/tmp/new-project",
                    attached_by="alice",
                    approval_mode="review",
                    bootstrapped_by="alice",
                    human_objective="Build a bounded thing.",
                    project_intent="Ship a bounded slice.",
                    log_path=Path("/tmp/orch.log"),
                )
            )
        self.assertEqual(got, Path("/tmp/attach-record.json"))
        p.assert_called_once_with(
            Path("/tmp/controller"),
            target_path="/tmp/new-project",
            attached_by="alice",
            approval_mode="review",
            log_path=Path("/tmp/orch.log"),
            bootstrap=True,
            bootstrapped_by="alice",
            human_objective="Build a bounded thing.",
            project_intent="Ship a bounded slice.",
        )

    def test_dispatch_wrapper_propagates_halt_error(self) -> None:
        # Runtime HaltError MUST propagate so the Tk callback can
        # surface the reason in the dialog status Label without
        # silently swallowing it. Preserves typed operator context
        # for retry per the Fix Phase B3 prompt.
        with mock.patch.object(
            agent_loop,
            "attach_external_target",
            side_effect=agent_loop.HaltError(
                "halted_input_missing", "synthetic refusal",
            ),
        ):
            with self.assertRaises(agent_loop.HaltError) as cm:
                (
                    agent_loop
                    ._primary_desktop_dispatch_bootstrap_attach(
                        Path("/tmp/controller"),
                        target_path="/tmp/new-project",
                        attached_by="alice",
                        approval_mode="review",
                        bootstrapped_by="alice",
                        human_objective="obj",
                        project_intent="intent",
                    )
                )
        self.assertEqual(cm.exception.reason, "synthetic refusal")

    def test_dispatch_wrapper_defaults_log_path_to_none(
        self,
    ) -> None:
        # Callers that omit log_path get the shipped runtime's
        # default None behavior (no orchestrator.log audit
        # append). The Tk callback always passes a log_path so the
        # audit line is written; this test just pins the default.
        with mock.patch.object(
            agent_loop,
            "attach_external_target",
        ) as p:
            p.return_value = Path("/tmp/rec.json")
            (
                agent_loop
                ._primary_desktop_dispatch_bootstrap_attach(
                    Path("/tmp/controller"),
                    target_path="/tmp/new-project",
                    attached_by="alice",
                    approval_mode="review",
                    bootstrapped_by="alice",
                    human_objective="obj",
                    project_intent="intent",
                )
            )
        _, kwargs = p.call_args
        self.assertIsNone(kwargs["log_path"])
        # bootstrap=True MUST always be set; the wrapper's raison
        # d'etre is the bootstrap path.
        self.assertIs(kwargs["bootstrap"], True)


class PrimaryDesktopPostBootstrapSuccessMessageTests(
    unittest.TestCase,
):
    """Cover the Fix Phase B3 post-bootstrap next-step guidance
    formatter `_primary_desktop_format_post_bootstrap_success(...)`.
    The message MUST name three shipped anchors so the operator
    sees that bootstrap is distinct from first-phase activation.
    """

    def test_success_message_names_three_shipped_anchors(
        self,
    ) -> None:
        got = (
            agent_loop
            ._primary_desktop_format_post_bootstrap_success(
                target_path="/tmp/new-project",
                attach_record_name="attach-record.json",
            )
        )
        # Anchor 1: target loop-state landing spot.
        self.assertIn("awaiting_first_activation", got)
        # Anchor 2: named path forward.
        self.assertIn("Phase 4C activator", got)
        # Anchor 3: human approval gate.
        self.assertIn("APPROVED_FOR_ACTIVATION", got)
        # Bootstrap-not-activation explicit callout.
        self.assertIn(
            "Bootstrap is distinct from first-phase activation",
            got,
        )
        # Operator-facing surface names the resolved target path
        # and attach record so the operator can locate them
        # without leaving the desktop.
        self.assertIn("/tmp/new-project", got)
        self.assertIn("attach-record.json", got)

    def test_success_message_refuses_missing_target_path(
        self,
    ) -> None:
        for bad in (None, "", "   ", 42):
            with self.assertRaises(agent_loop.HaltError):
                (
                    agent_loop
                    ._primary_desktop_format_post_bootstrap_success(
                        target_path=bad,  # type: ignore[arg-type]
                        attach_record_name="attach-record.json",
                    )
                )

    def test_success_message_refuses_missing_record_name(
        self,
    ) -> None:
        for bad in (None, "", "   ", 42):
            with self.assertRaises(agent_loop.HaltError):
                (
                    agent_loop
                    ._primary_desktop_format_post_bootstrap_success(
                        target_path="/tmp/new-project",
                        attach_record_name=(
                            bad  # type: ignore[arg-type]
                        ),
                    )
                )

    def test_success_message_strips_whitespace(self) -> None:
        # Leading / trailing whitespace on the inputs MUST NOT
        # bleed into the surfaced message.
        got = (
            agent_loop
            ._primary_desktop_format_post_bootstrap_success(
                target_path="  /tmp/new-project  ",
                attach_record_name="  attach-record.json  ",
            )
        )
        self.assertIn("/tmp/new-project.", got)
        self.assertIn("attach-record.json.", got)


# ---------------------------------------------------------------------------
# Phase 10AG - Desktop Codex Conversation Surface Initial Slice
# ---------------------------------------------------------------------------
class DesktopCodexConversationConstantsTests(unittest.TestCase):
    """Cover the Phase 10AG closed vocabulary constants that
    mirror the shipped Phase 10AF contract verbatim.
    """

    def test_signal_version_pin(self) -> None:
        self.assertEqual(
            agent_loop.DESKTOP_CODEX_CONVERSATION_SIGNAL_VERSION,
            "phase-10ag-v1",
        )

    def test_intent_vocabulary_matches_contract(self) -> None:
        self.assertEqual(
            agent_loop.DESKTOP_CODEX_CONVERSATION_INTENT_IDS,
            (
                "request_codex_review",
                "request_codex_issue_classification",
                "request_codex_roadmap_update",
                "request_codex_targeted_repo_change",
                "request_codex_claude_prompt_authorship",
                "request_codex_fix_prompt_authorship",
            ),
        )

    def test_refusal_vocabulary_matches_contract(self) -> None:
        self.assertEqual(
            agent_loop.DESKTOP_CODEX_CONVERSATION_REFUSAL_CATEGORIES,
            (
                "refused_intent_outside_closed_vocabulary",
                "refused_orchestrator_owned_target",
                "refused_claude_owned_target",
                "refused_overlap_unsafe",
                "refused_strict_mode_gate",
                "refused_auto_fill_operator_identity",
                "refused_in_flight_codex_invocation",
                "refused_advisory_persistence",
            ),
        )

    def test_intent_target_map_covers_every_intent(self) -> None:
        target_map = (
            agent_loop.DESKTOP_CODEX_CONVERSATION_INTENT_TARGET_MAP
        )
        self.assertEqual(
            set(target_map.keys()),
            set(agent_loop.DESKTOP_CODEX_CONVERSATION_INTENT_IDS),
        )
        for path in target_map.values():
            self.assertIsInstance(path, str)
            self.assertTrue(path.startswith(".agent-loop/"))

    def test_attribution_tags(self) -> None:
        self.assertEqual(
            agent_loop.DESKTOP_CODEX_CONVERSATION_ATTRIBUTION_CANONICAL_MIRROR,
            "[canonical mirror]",
        )
        self.assertEqual(
            agent_loop.DESKTOP_CODEX_CONVERSATION_ATTRIBUTION_ADVISORY,
            "[codex-conversation-advisory]",
        )


class DesktopCodexConversationClassifierTests(unittest.TestCase):
    """Cover the pure classifier
    `_desktop_codex_conversation_classify_request(...)`. Refusals
    are ordered so a malformed request surfaces the earliest
    applicable refusal per the contract's precedence rule.
    """

    def _happy_kwargs(self) -> dict:
        return {
            "intent_id": "request_codex_review",
            "operator_identity": "alice",
            "message_body": "please review the current branch",
            "in_flight": False,
            "overlap_state": "no_signal",
            "strict_mode_gate_pending": False,
        }

    def test_classifier_returns_none_on_happy_request(
        self,
    ) -> None:
        self.assertIsNone(
            agent_loop._desktop_codex_conversation_classify_request(
                **self._happy_kwargs(),
            ),
        )

    def test_classifier_refuses_unknown_intent(self) -> None:
        kw = self._happy_kwargs()
        kw["intent_id"] = "invented_intent"
        got = agent_loop._desktop_codex_conversation_classify_request(
            **kw,
        )
        self.assertIsNotNone(got)
        self.assertEqual(
            got["refusal_category"],
            "refused_intent_outside_closed_vocabulary",
        )

    def test_classifier_refuses_missing_operator_identity(
        self,
    ) -> None:
        for bad in (None, "", "   "):
            kw = self._happy_kwargs()
            kw["operator_identity"] = bad
            got = (
                agent_loop
                ._desktop_codex_conversation_classify_request(**kw)
            )
            self.assertIsNotNone(got)
            self.assertEqual(
                got["refusal_category"],
                "refused_auto_fill_operator_identity",
                bad,
            )

    def test_classifier_refuses_missing_message_body(self) -> None:
        for bad in (None, "", "   ", "\n\t"):
            kw = self._happy_kwargs()
            kw["message_body"] = bad
            got = (
                agent_loop
                ._desktop_codex_conversation_classify_request(**kw)
            )
            self.assertIsNotNone(got)
            self.assertEqual(
                got["refusal_category"],
                "refused_advisory_persistence",
                bad,
            )

    def test_classifier_refuses_overlap_unsafe(self) -> None:
        kw = self._happy_kwargs()
        kw["overlap_state"] = "refused_pending_recovery"
        got = agent_loop._desktop_codex_conversation_classify_request(
            **kw,
        )
        self.assertIsNotNone(got)
        self.assertEqual(
            got["refusal_category"], "refused_overlap_unsafe",
        )

    def test_classifier_refuses_strict_mode_gate_pending(
        self,
    ) -> None:
        kw = self._happy_kwargs()
        kw["strict_mode_gate_pending"] = True
        got = agent_loop._desktop_codex_conversation_classify_request(
            **kw,
        )
        self.assertIsNotNone(got)
        self.assertEqual(
            got["refusal_category"], "refused_strict_mode_gate",
        )

    def test_classifier_refuses_in_flight(self) -> None:
        kw = self._happy_kwargs()
        kw["in_flight"] = True
        got = agent_loop._desktop_codex_conversation_classify_request(
            **kw,
        )
        self.assertIsNotNone(got)
        self.assertEqual(
            got["refusal_category"],
            "refused_in_flight_codex_invocation",
        )

    def test_classifier_precedence_intent_before_identity(
        self,
    ) -> None:
        # Unknown intent MUST be refused before missing identity;
        # the panel should not blame the operator for the wrong
        # intent selection.
        kw = self._happy_kwargs()
        kw["intent_id"] = "invented_intent"
        kw["operator_identity"] = ""
        got = agent_loop._desktop_codex_conversation_classify_request(
            **kw,
        )
        self.assertEqual(
            got["refusal_category"],
            "refused_intent_outside_closed_vocabulary",
        )

    def test_classifier_precedence_identity_before_body(
        self,
    ) -> None:
        kw = self._happy_kwargs()
        kw["operator_identity"] = ""
        kw["message_body"] = ""
        got = agent_loop._desktop_codex_conversation_classify_request(
            **kw,
        )
        self.assertEqual(
            got["refusal_category"],
            "refused_auto_fill_operator_identity",
        )


class DesktopCodexConversationFormatRequestTests(unittest.TestCase):
    """Cover the pure request formatter
    `_desktop_codex_conversation_format_request(...)`. Payload
    shape MUST include the six required fields; missing / empty
    fields refuse fail-closed via HaltError.
    """

    def test_format_request_shape(self) -> None:
        payload = (
            agent_loop._desktop_codex_conversation_format_request(
                intent_id="request_codex_review",
                operator_identity="alice",
                message_body="please review",
            )
        )
        self.assertEqual(
            payload["signal_version"], "phase-10ag-v1",
        )
        self.assertEqual(
            payload["intent_id"], "request_codex_review",
        )
        self.assertEqual(payload["operator_identity"], "alice")
        self.assertEqual(payload["message_body"], "please review")
        self.assertEqual(
            payload["target_artifact"],
            ".agent-loop/codex-review.md",
        )
        self.assertEqual(
            payload["attribution_tag"],
            "[codex-conversation-advisory]",
        )

    def test_format_request_strips_whitespace(self) -> None:
        payload = (
            agent_loop._desktop_codex_conversation_format_request(
                intent_id="request_codex_review",
                operator_identity="  alice  ",
                message_body="  please review\n",
            )
        )
        self.assertEqual(payload["operator_identity"], "alice")
        self.assertEqual(payload["message_body"], "please review")

    def test_format_request_refuses_unknown_intent(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_codex_conversation_format_request(
                intent_id="invented_intent",
                operator_identity="alice",
                message_body="body",
            )

    def test_format_request_refuses_missing_identity(self) -> None:
        for bad in (None, "", "   "):
            with self.assertRaises(agent_loop.HaltError):
                (
                    agent_loop
                    ._desktop_codex_conversation_format_request(
                        intent_id="request_codex_review",
                        operator_identity=bad,
                        message_body="body",
                    )
                )

    def test_format_request_refuses_missing_body(self) -> None:
        for bad in (None, "", "   "):
            with self.assertRaises(agent_loop.HaltError):
                (
                    agent_loop
                    ._desktop_codex_conversation_format_request(
                        intent_id="request_codex_review",
                        operator_identity="alice",
                        message_body=bad,
                    )
                )

    def test_target_artifact_matches_intent_map(self) -> None:
        # Every shipped intent's format_request payload MUST use
        # the closed per-intent target-artifact map.
        for intent in agent_loop.DESKTOP_CODEX_CONVERSATION_INTENT_IDS:
            payload = (
                agent_loop
                ._desktop_codex_conversation_format_request(
                    intent_id=intent,
                    operator_identity="alice",
                    message_body="body",
                )
            )
            self.assertEqual(
                payload["target_artifact"],
                agent_loop.DESKTOP_CODEX_CONVERSATION_INTENT_TARGET_MAP[
                    intent
                ],
                intent,
            )


class DesktopCodexConversationDispatchCommandTests(unittest.TestCase):
    """Cover the pure dispatch-command builder
    `_desktop_codex_conversation_build_dispatch_command(...)`.
    Only `request_codex_review` has a shipped dispatch path in
    this initial slice; every other closed-vocabulary intent is
    refused fail-closed with an explanatory HaltError.
    """

    def test_review_intent_returns_resume_command(self) -> None:
        cmd = (
            agent_loop
            ._desktop_codex_conversation_build_dispatch_command(
                intent_id="request_codex_review",
                controller_root=Path("."),
            )
        )
        self.assertEqual(cmd[0], sys.executable)
        self.assertTrue(
            cmd[1].endswith("agent_loop.py")
            or cmd[1].endswith("agent_loop.pyc"),
            cmd[1],
        )
        self.assertEqual(cmd[-1], "resume")

    def test_other_shipped_intents_refuse_dispatch(self) -> None:
        # Every closed intent OTHER than `request_codex_review`
        # MUST refuse fail-closed in this initial slice; the
        # panel accepts composition + validation but dispatch is
        # deferred to a later slice.
        deferred = tuple(
            i
            for i in agent_loop.DESKTOP_CODEX_CONVERSATION_INTENT_IDS
            if i != "request_codex_review"
        )
        for intent in deferred:
            with self.assertRaises(agent_loop.HaltError) as cm:
                (
                    agent_loop
                    ._desktop_codex_conversation_build_dispatch_command(
                        intent_id=intent,
                        controller_root=Path("."),
                    )
                )
            self.assertIn(intent, cm.exception.reason)

    def test_unknown_intent_refuses(self) -> None:
        with self.assertRaises(agent_loop.HaltError) as cm:
            (
                agent_loop
                ._desktop_codex_conversation_build_dispatch_command(
                    intent_id="invented_intent",
                    controller_root=Path("."),
                )
            )
        self.assertIn(
            "closed", cm.exception.reason,
        )


class DesktopCodexConversationResponseMirrorTests(unittest.TestCase):
    """Cover the pure response-mirror reader
    `_desktop_codex_conversation_read_canonical_response_mirror
    (...)`. NEVER writes; NEVER raises on missing / unreadable
    file (returns `present=False` + `error` field instead so the
    Tk panel can render an operator-facing hint).
    """

    def test_read_returns_present_true_when_file_exists(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = Path(td) / "controller"
            (controller / ".agent-loop").mkdir(parents=True)
            (controller / ".agent-loop" / "codex-review.md").write_text(
                "# Codex Review\n\nAPPROVED_FOR_HUMAN_REVIEW\n",
                encoding="utf-8",
            )
            mirror = (
                agent_loop
                ._desktop_codex_conversation_read_canonical_response_mirror(
                    controller, "request_codex_review",
                )
            )
        self.assertTrue(mirror["present"])
        self.assertIn(
            "APPROVED_FOR_HUMAN_REVIEW", mirror["mirror_text"],
        )
        self.assertEqual(
            mirror["attribution_tag"], "[canonical mirror]",
        )
        self.assertEqual(
            mirror["target_artifact"],
            ".agent-loop/codex-review.md",
        )
        self.assertIsNone(mirror["error"])

    def test_read_returns_present_false_when_missing(self) -> None:
        with TemporaryDirectory() as td:
            controller = Path(td) / "controller"
            controller.mkdir()
            mirror = (
                agent_loop
                ._desktop_codex_conversation_read_canonical_response_mirror(
                    controller, "request_codex_review",
                )
            )
        self.assertFalse(mirror["present"])
        self.assertEqual(mirror["mirror_text"], "")
        self.assertIn("not present", mirror["error"])

    def test_read_returns_error_on_unknown_intent(self) -> None:
        with TemporaryDirectory() as td:
            controller = Path(td) / "controller"
            controller.mkdir()
            mirror = (
                agent_loop
                ._desktop_codex_conversation_read_canonical_response_mirror(
                    controller, "invented_intent",
                )
            )
        self.assertFalse(mirror["present"])
        self.assertIn("closed", mirror["error"])

    def test_read_covers_every_intent(self) -> None:
        # Every shipped intent's read MUST succeed (either
        # present or explanatory-missing) without raising.
        with TemporaryDirectory() as td:
            controller = Path(td) / "controller"
            controller.mkdir()
            for intent in (
                agent_loop.DESKTOP_CODEX_CONVERSATION_INTENT_IDS
            ):
                mirror = (
                    agent_loop
                    ._desktop_codex_conversation_read_canonical_response_mirror(
                        controller, intent,
                    )
                )
                self.assertEqual(
                    mirror["attribution_tag"],
                    "[canonical mirror]",
                    intent,
                )
                self.assertFalse(mirror["present"], intent)


class DesktopCodexConversationAuditLineTests(unittest.TestCase):
    """Cover the pure audit-line formatter
    `_desktop_codex_conversation_format_audit_line(...)` which
    the Tk callback appends via the shipped audit-log writer.
    NEVER writes a parallel audit file per the Phase 10AF
    Source-Of-Truth Preservation rule.
    """

    def test_audit_line_shape_success(self) -> None:
        line = (
            agent_loop._desktop_codex_conversation_format_audit_line(
                intent_id="request_codex_review",
                operator_identity="alice",
                epoch_seconds=1700000000,
            )
        )
        self.assertIn("[desktop-codex-conversation]", line)
        self.assertIn("intent_id='request_codex_review'", line)
        self.assertIn("operator_identity='alice'", line)
        self.assertIn("refusal_category=None", line)
        self.assertIn("epoch_seconds=1700000000", line)

    def test_audit_line_shape_refusal(self) -> None:
        line = (
            agent_loop._desktop_codex_conversation_format_audit_line(
                intent_id="request_codex_review",
                operator_identity="alice",
                refusal_category=(
                    "refused_overlap_unsafe"
                ),
                epoch_seconds=1700000000,
            )
        )
        self.assertIn(
            "refusal_category='refused_overlap_unsafe'", line,
        )

    def test_audit_line_refuses_unknown_refusal_category(
        self,
    ) -> None:
        with self.assertRaises(agent_loop.HaltError):
            (
                agent_loop
                ._desktop_codex_conversation_format_audit_line(
                    intent_id="request_codex_review",
                    operator_identity="alice",
                    refusal_category="invented_category",
                    epoch_seconds=1700000000,
                )
            )

    def test_audit_line_refuses_missing_identity(self) -> None:
        for bad in (None, "", "   "):
            with self.assertRaises(agent_loop.HaltError):
                (
                    agent_loop
                    ._desktop_codex_conversation_format_audit_line(
                        intent_id="request_codex_review",
                        operator_identity=bad,
                        epoch_seconds=1700000000,
                    )
                )

    def test_audit_line_refuses_non_int_epoch(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            (
                agent_loop
                ._desktop_codex_conversation_format_audit_line(
                    intent_id="request_codex_review",
                    operator_identity="alice",
                    epoch_seconds="not an int",
                )
            )


class DesktopCodexConversationRuntimeGateInputsTests(
    unittest.TestCase,
):
    """Cover
    `_desktop_codex_conversation_derive_runtime_gate_inputs(...)`
    which the Tk callback uses in place of the previously-
    hardcoded `overlap_state='no_signal'` /
    `strict_mode_gate_pending=False` inputs. Regression pin: if
    this helper is bypassed or replaced with a synthetic stub,
    the shipped 10AG desktop Send path stops honoring the
    overlap-safe / strict-mode gates.
    """

    def test_missing_controller_soft_fails_to_neutral(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = Path(td) / "no_agent_loop_dir"
            controller.mkdir()
            result = (
                agent_loop
                ._desktop_codex_conversation_derive_runtime_gate_inputs(
                    controller,
                )
            )
        self.assertFalse(result["strict_mode_gate_pending"])
        self.assertIn(
            result["overlap_state"],
            (
                None, "no_signal", "signal_detected",
                "unknown", "refused_pending_recovery",
            ),
        )

    def test_non_strict_status_reports_gate_not_pending(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(
                Path(td), status="awaiting_claude_implementation",
            )
            result = (
                agent_loop
                ._desktop_codex_conversation_derive_runtime_gate_inputs(
                    controller,
                )
            )
        self.assertFalse(result["strict_mode_gate_pending"])

    def test_every_strict_gate_halt_marks_gate_pending(
        self,
    ) -> None:
        for status in agent_loop.STRICT_GATE_HALT_STATUSES:
            with TemporaryDirectory() as td:
                controller = _make_controller(
                    Path(td), status=status,
                )
                result = (
                    agent_loop
                    ._desktop_codex_conversation_derive_runtime_gate_inputs(
                        controller,
                    )
                )
            self.assertTrue(
                result["strict_mode_gate_pending"],
                msg=(
                    f"strict_mode_gate_pending must be True for "
                    f"loop-state status={status!r}"
                ),
            )

    def test_overlap_state_reflects_shipped_view(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td))
            expected = None
            try:
                view = (
                    agent_loop
                    .build_desktop_overlap_detection_view(
                        controller,
                    )
                )
            except agent_loop.HaltError:
                view = None
            if isinstance(view, dict):
                overall = view.get("overall") or {}
                cand = overall.get("overall_signal_state")
                if isinstance(cand, str):
                    expected = cand
            result = (
                agent_loop
                ._desktop_codex_conversation_derive_runtime_gate_inputs(
                    controller,
                )
            )
        self.assertEqual(result["overlap_state"], expected)

    def test_returns_only_the_expected_two_keys(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td))
            result = (
                agent_loop
                ._desktop_codex_conversation_derive_runtime_gate_inputs(
                    controller,
                )
            )
        self.assertEqual(
            set(result.keys()),
            {"overlap_state", "strict_mode_gate_pending"},
        )


class DesktopCodexConversationSendCallbackWiringTests(
    unittest.TestCase,
):
    """Source-inspection regression pin for the shipped Tk
    callback wiring inside `_launch_desktop_app_window(...)`.
    The callback body is a closure, so we inspect the enclosing
    function's source text and assert:
      - the derive-runtime-gate-inputs helper IS called
      - the audit-line formatter IS called
      - the shipped `_log_note` audit writer IS called
      - the previously-hardcoded gate literals are ABSENT
    A regression that hardcodes the gate inputs or drops the
    audit emit will fail this pin loudly.
    """

    def setUp(self) -> None:
        import inspect
        self._source = inspect.getsource(
            agent_loop._launch_desktop_app_window,
        )

    def test_calls_derive_runtime_gate_inputs_helper(
        self,
    ) -> None:
        self.assertIn(
            "_desktop_codex_conversation_derive_runtime_gate_inputs",
            self._source,
        )

    def test_calls_audit_line_formatter(self) -> None:
        self.assertIn(
            "_desktop_codex_conversation_format_audit_line",
            self._source,
        )

    def test_calls_shipped_log_note_writer(self) -> None:
        self.assertIn("_log_note(", self._source)

    def test_does_not_hardcode_overlap_state_no_signal(
        self,
    ) -> None:
        self.assertNotIn(
            'overlap_state="no_signal"', self._source,
        )
        self.assertNotIn(
            "overlap_state='no_signal'", self._source,
        )

    def test_does_not_hardcode_strict_mode_gate_pending_false(
        self,
    ) -> None:
        self.assertNotIn(
            "strict_mode_gate_pending=False", self._source,
        )

    def test_dispatches_orchestrator_log_as_audit_path(
        self,
    ) -> None:
        self.assertIn("orchestrator.log", self._source)


class Phase10AIVisualizationConstantsTests(unittest.TestCase):
    """Pin the shipped Phase 10AI closed vocabularies. Any
    widening or contraction of the closed sets is a contract
    break and MUST fail here loudly.
    """

    def test_signal_version(self) -> None:
        self.assertEqual(
            agent_loop.PHASE_10AI_VISUALIZATION_SIGNAL_VERSION,
            "phase-10ai-v1",
        )

    def test_ten_canonical_mirror_keys(self) -> None:
        self.assertEqual(
            agent_loop.PHASE_10AI_CANONICAL_MIRROR_KEYS,
            (
                "phase", "sub_phase", "task",
                "loop_state_status", "approval_mode",
                "cycle_count", "max_cycles",
                "awaiting_human_for", "last_verdict",
                "last_verdict_phase",
            ),
        )

    def test_five_advisory_derived_keys(self) -> None:
        self.assertEqual(
            agent_loop.PHASE_10AI_ADVISORY_DERIVED_KEYS,
            (
                "review_branch_active", "fix_branch_active",
                "human_gate_pending", "blocked_or_halted",
                "artifact_backed_progress",
            ),
        )

    def test_full_vocabulary_is_fifteen_and_concatenates(
        self,
    ) -> None:
        self.assertEqual(
            len(agent_loop.PHASE_10AI_VISUALIZATION_VOCABULARY),
            15,
        )
        self.assertEqual(
            agent_loop.PHASE_10AI_VISUALIZATION_VOCABULARY,
            (
                agent_loop.PHASE_10AI_CANONICAL_MIRROR_KEYS
                + agent_loop.PHASE_10AI_ADVISORY_DERIVED_KEYS
            ),
        )

    def test_two_source_categories(self) -> None:
        self.assertEqual(
            agent_loop.PHASE_10AI_SOURCE_CATEGORIES,
            ("canonical_mirror", "visualization_advisory"),
        )

    def test_five_status_categories(self) -> None:
        self.assertEqual(
            agent_loop.PHASE_10AI_STATUS_CATEGORIES,
            (
                "in_progress", "awaiting_review",
                "awaiting_human", "halted", "complete",
            ),
        )

    def test_nine_refusal_categories(self) -> None:
        self.assertEqual(
            len(agent_loop.PHASE_10AI_REFUSAL_CATEGORIES), 9,
        )
        for category in (
            "refused_value_outside_closed_vocabulary",
            "refused_source_category_outside_closed_vocabulary",
            "refused_gate_category_outside_closed_vocabulary",
            "refused_status_category_outside_closed_vocabulary",
            "refused_canonical_write_from_visualization",
            "refused_auto_progression_from_visualization",
            "refused_auto_fill_operator_identity",
            "refused_advisory_persistence",
            "refused_background_watcher_beyond_cadence",
        ):
            self.assertIn(
                category,
                agent_loop.PHASE_10AI_REFUSAL_CATEGORIES,
            )

    def test_key_source_category_map_covers_every_vocab_key(
        self,
    ) -> None:
        self.assertEqual(
            set(
                agent_loop.PHASE_10AI_KEY_SOURCE_CATEGORY_MAP
                .keys()
            ),
            set(
                agent_loop.PHASE_10AI_VISUALIZATION_VOCABULARY
            ),
        )
        for key, cat in (
            agent_loop.PHASE_10AI_KEY_SOURCE_CATEGORY_MAP.items()
        ):
            self.assertIn(
                cat, agent_loop.PHASE_10AI_SOURCE_CATEGORIES,
                key,
            )

    def test_key_source_artifacts_map_covers_every_vocab_key(
        self,
    ) -> None:
        self.assertEqual(
            set(
                agent_loop.PHASE_10AI_KEY_SOURCE_ARTIFACTS_MAP
                .keys()
            ),
            set(
                agent_loop.PHASE_10AI_VISUALIZATION_VOCABULARY
            ),
        )
        for key, paths in (
            agent_loop
            .PHASE_10AI_KEY_SOURCE_ARTIFACTS_MAP.items()
        ):
            self.assertGreater(len(paths), 0, key)

    def test_attribution_tags(self) -> None:
        self.assertEqual(
            agent_loop.PHASE_10AI_ATTRIBUTION_CANONICAL_MIRROR,
            "[canonical mirror]",
        )
        self.assertEqual(
            agent_loop.PHASE_10AI_ATTRIBUTION_ADVISORY,
            "[visualization-advisory]",
        )


class Phase10AIAdvisoryDerivationTests(unittest.TestCase):
    """Cover the pure Tk-free advisory-derivation helper. Every
    branch of every derived key is exercised through the pure
    function so we do not need a temp controller."""

    def _derive(
        self, *, loop_state, overlap_state=None,
        fix_prompt_mtime=None, claude_summary_mtime=None,
        artifact_backed_progress=None,
    ):
        if artifact_backed_progress is None:
            artifact_backed_progress = {}
        return (
            agent_loop
            ._desktop_orchestration_visualization_derive_advisory_state(
                loop_state=loop_state,
                overlap_state=overlap_state,
                fix_prompt_mtime=fix_prompt_mtime,
                claude_summary_mtime=claude_summary_mtime,
                artifact_backed_progress=artifact_backed_progress,
            )
        )

    def test_review_branch_active_from_normal_cycle_status(
        self,
    ) -> None:
        for status in agent_loop.PHASE_10AI_NORMAL_CYCLE_STATUSES:
            res = self._derive(loop_state={"status": status})
            self.assertTrue(
                res["review_branch_active"], status,
            )

    def test_review_branch_active_from_last_verdict(self) -> None:
        res = self._derive(
            loop_state={
                "status": "some_other",
                "last_verdict": "APPROVED_FOR_HUMAN_REVIEW",
            },
        )
        self.assertTrue(res["review_branch_active"])

    def test_review_branch_inactive_for_unrelated_status(
        self,
    ) -> None:
        res = self._derive(
            loop_state={"status": "awaiting_fix_prompt"},
        )
        self.assertFalse(res["review_branch_active"])

    def test_fix_branch_active_from_fix_cycle_status(self) -> None:
        for status in agent_loop.PHASE_10AI_FIX_CYCLE_STATUSES:
            res = self._derive(loop_state={"status": status})
            self.assertTrue(res["fix_branch_active"], status)

    def test_fix_branch_active_from_mtime_comparison(self) -> None:
        res = self._derive(
            loop_state={"status": "awaiting_claude_implementation"},
            fix_prompt_mtime=200.0,
            claude_summary_mtime=100.0,
        )
        self.assertTrue(res["fix_branch_active"])

    def test_fix_branch_inactive_when_summary_newer(self) -> None:
        res = self._derive(
            loop_state={"status": "awaiting_claude_implementation"},
            fix_prompt_mtime=100.0,
            claude_summary_mtime=200.0,
        )
        self.assertFalse(res["fix_branch_active"])

    def test_human_gate_pending_from_awaiting_human_for(
        self,
    ) -> None:
        res = self._derive(
            loop_state={
                "status": "awaiting_claude_implementation",
                "awaiting_human_for": "pre_claude_prompt",
            },
        )
        self.assertTrue(res["human_gate_pending"])

    def test_human_gate_pending_from_strict_gate_halt(self) -> None:
        for status in agent_loop.STRICT_GATE_HALT_STATUSES:
            res = self._derive(loop_state={"status": status})
            self.assertTrue(res["human_gate_pending"], status)

    def test_blocked_or_halted_from_halted_status(self) -> None:
        res = self._derive(
            loop_state={"status": "halted_overlap_unsafe_context"},
        )
        self.assertTrue(res["blocked_or_halted"])

    def test_blocked_or_halted_from_overlap_refused(self) -> None:
        res = self._derive(
            loop_state={"status": "awaiting_claude_implementation"},
            overlap_state="refused_pending_recovery",
        )
        self.assertTrue(res["blocked_or_halted"])

    def test_artifact_backed_progress_passes_through(self) -> None:
        payload = {"foo.md": {"present": True}}
        res = self._derive(
            loop_state={"status": "awaiting_claude_implementation"},
            artifact_backed_progress=payload,
        )
        self.assertIs(res["artifact_backed_progress"], payload)

    def test_non_dict_loop_state_soft_fails_neutral(self) -> None:
        res = self._derive(loop_state=None)
        self.assertFalse(res["review_branch_active"])
        self.assertFalse(res["fix_branch_active"])
        self.assertFalse(res["human_gate_pending"])
        self.assertFalse(res["blocked_or_halted"])


class Phase10AIStatusCategoryClassifierTests(unittest.TestCase):

    def _classify(self, *, loop_state, overlap_state=None):
        return (
            agent_loop
            ._desktop_orchestration_visualization_classify_status_category(
                loop_state=loop_state,
                overlap_state=overlap_state,
            )
        )

    def test_halted_status_returns_halted(self) -> None:
        self.assertEqual(
            self._classify(
                loop_state={"status": "halted_overlap_unsafe_context"},
            ),
            "halted",
        )

    def test_overlap_refused_returns_halted(self) -> None:
        self.assertEqual(
            self._classify(
                loop_state={
                    "status": "awaiting_claude_implementation",
                },
                overlap_state="refused_pending_recovery",
            ),
            "halted",
        )

    def test_phase_complete_returns_complete(self) -> None:
        self.assertEqual(
            self._classify(
                loop_state={
                    "status": (
                        "phase_complete_awaiting_human_approval"
                    ),
                },
            ),
            "complete",
        )

    def test_awaiting_human_for_returns_awaiting_human(
        self,
    ) -> None:
        self.assertEqual(
            self._classify(
                loop_state={
                    "status": "awaiting_claude_implementation",
                    "awaiting_human_for": "pre_claude_prompt",
                },
            ),
            "awaiting_human",
        )

    def test_strict_gate_halt_returns_awaiting_human(self) -> None:
        # The strict-gate halt statuses start with "halted_" which
        # matches the "halted" precedence branch first; verify
        # that precedence is intentional.
        for status in agent_loop.STRICT_GATE_HALT_STATUSES:
            self.assertEqual(
                self._classify(loop_state={"status": status}),
                "halted",
                status,
            )

    def test_awaiting_review_status_returns_awaiting_review(
        self,
    ) -> None:
        for status in (
            "awaiting_codex_review",
            "awaiting_codex_re_review",
        ):
            self.assertEqual(
                self._classify(loop_state={"status": status}),
                "awaiting_review",
                status,
            )

    def test_default_status_returns_in_progress(self) -> None:
        self.assertEqual(
            self._classify(
                loop_state={
                    "status": "awaiting_claude_implementation",
                },
            ),
            "in_progress",
        )

    def test_non_dict_loop_state_returns_in_progress(self) -> None:
        self.assertEqual(
            self._classify(loop_state=None), "in_progress",
        )


class Phase10AIAuditLineTests(unittest.TestCase):

    def test_line_shape_success(self) -> None:
        line = (
            agent_loop
            ._desktop_orchestration_visualization_format_audit_line(
                epoch_seconds=1700000000,
            )
        )
        self.assertIn(
            "[desktop-orchestration-visualization]", line,
        )
        self.assertIn(
            "signal_version='phase-10ai-v1'", line,
        )
        self.assertIn("refusal_category=None", line)
        self.assertIn("epoch_seconds=1700000000", line)

    def test_line_shape_refusal(self) -> None:
        line = (
            agent_loop
            ._desktop_orchestration_visualization_format_audit_line(
                epoch_seconds=1700000000,
                refusal_category=(
                    "refused_canonical_write_from_visualization"
                ),
            )
        )
        self.assertIn(
            "refusal_category="
            "'refused_canonical_write_from_visualization'",
            line,
        )

    def test_refuses_unknown_refusal_category(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            (
                agent_loop
                ._desktop_orchestration_visualization_format_audit_line(
                    epoch_seconds=1700000000,
                    refusal_category="invented",
                )
            )

    def test_refuses_non_int_epoch(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            (
                agent_loop
                ._desktop_orchestration_visualization_format_audit_line(
                    epoch_seconds="not int",
                )
            )


class Phase10AIViewBuilderTests(unittest.TestCase):

    def test_shape_covers_full_vocabulary(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td))
            view = (
                agent_loop
                .build_desktop_orchestration_visualization_view(
                    controller,
                )
            )
        self.assertEqual(
            view["signal_version"], "phase-10ai-v1",
        )
        self.assertEqual(
            view["vocabulary"],
            list(
                agent_loop.PHASE_10AI_VISUALIZATION_VOCABULARY
            ),
        )
        node_ids = [n["id"] for n in view["nodes"]]
        self.assertEqual(
            node_ids,
            list(
                agent_loop.PHASE_10AI_VISUALIZATION_VOCABULARY
            ),
        )
        for node in view["nodes"]:
            self.assertIn(
                node["source_category"],
                agent_loop.PHASE_10AI_SOURCE_CATEGORIES,
            )
            if (
                node["source_category"]
                == "canonical_mirror"
            ):
                self.assertEqual(
                    node["attribution_tag"],
                    "[canonical mirror]",
                )
            else:
                self.assertEqual(
                    node["attribution_tag"],
                    "[visualization-advisory]",
                )
        self.assertIn(
            view["status_category"],
            agent_loop.PHASE_10AI_STATUS_CATEGORIES,
        )

    def test_status_category_reflects_loop_state_status(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(
                Path(td),
                status="halted_overlap_unsafe_context",
            )
            view = (
                agent_loop
                .build_desktop_orchestration_visualization_view(
                    controller,
                )
            )
        self.assertEqual(view["status_category"], "halted")

    def test_canonical_mirror_values_match_loop_state(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(
                Path(td),
                status="awaiting_codex_review",
            )
            view = (
                agent_loop
                .build_desktop_orchestration_visualization_view(
                    controller,
                )
            )
        nodes_by_id = {n["id"]: n for n in view["nodes"]}
        self.assertEqual(
            nodes_by_id["loop_state_status"]["current_value"],
            "awaiting_codex_review",
        )
        self.assertEqual(
            nodes_by_id["approval_mode"]["current_value"],
            "review",
        )
        self.assertEqual(
            view["status_category"], "awaiting_review",
        )

    def test_artifact_backed_progress_is_a_dict(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td))
            view = (
                agent_loop
                .build_desktop_orchestration_visualization_view(
                    controller,
                )
            )
        nodes_by_id = {n["id"]: n for n in view["nodes"]}
        progress = nodes_by_id[
            "artifact_backed_progress"
        ]["current_value"]
        self.assertIsInstance(progress, dict)
        self.assertIn(
            ".agent-loop/claude-summary.md", progress,
        )


class Phase10AITextRendererTests(unittest.TestCase):

    def test_renderer_emits_header_plus_nodes_plus_edges(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td))
            view = (
                agent_loop
                .build_desktop_orchestration_visualization_view(
                    controller,
                )
            )
        lines = (
            agent_loop
            .render_desktop_orchestration_visualization_text(
                view,
            )
        )
        self.assertEqual(
            len(lines),
            1 + len(view["nodes"]) + len(view["edges"]),
        )
        self.assertIn(
            "[desktop-orchestration-visualization]", lines[0],
        )

    def test_every_body_line_carries_an_attribution_tag(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td))
            view = (
                agent_loop
                .build_desktop_orchestration_visualization_view(
                    controller,
                )
            )
        lines = (
            agent_loop
            .render_desktop_orchestration_visualization_text(
                view,
            )
        )
        # Node lines carry canonical / advisory tags; edge lines
        # carry the graph-edge tag. Every body line MUST match
        # exactly one of the three shipped attribution tags.
        for body_line in lines[1:]:
            self.assertTrue(
                "[canonical mirror]" in body_line
                or "[visualization-advisory]" in body_line
                or "[graph-edge]" in body_line,
                body_line,
            )


class Phase10AISendCallbackWiringTests(unittest.TestCase):
    """Source-inspection regression pin for the shipped Tk
    orchestration-visualization panel inside
    `_launch_desktop_app_window(...)`. Ensures the callback:
      - assembles the view via the shipped bounded builder
      - renders via the shipped bounded renderer
      - emits the per-tick audit line via the shipped
        `_log_note(...)` writer
      - is invoked from the main `_refresh(...)` poll callback
        (no separate background thread / timer)
    """

    def setUp(self) -> None:
        import inspect
        self._source = inspect.getsource(
            agent_loop._launch_desktop_app_window,
        )

    def test_calls_view_builder(self) -> None:
        self.assertIn(
            "build_desktop_orchestration_visualization_view",
            self._source,
        )

    def test_calls_audit_line_formatter(self) -> None:
        self.assertIn(
            (
                "_desktop_orchestration_visualization_"
                "format_audit_line"
            ),
            self._source,
        )

    def test_calls_shipped_log_note_writer(self) -> None:
        self.assertIn("_log_note(", self._source)

    def test_refresh_orchestration_visualization_hooked_into_poll(
        self,
    ) -> None:
        # The callback name must appear at least twice in the
        # source: once at definition, and at least once inside
        # the `_refresh()` main poll callback so the panel
        # refreshes on the shipped Phase 10L / 10M poll cadence
        # rather than via a separate background thread.
        count = self._source.count(
            "_refresh_orchestration_visualization()",
        )
        self.assertGreaterEqual(count, 2, count)

    def test_does_not_start_a_background_thread_or_timer(
        self,
    ) -> None:
        # A regression pin: the callback body MUST NOT introduce
        # a separate background thread / timer / watcher beyond
        # the shipped poll cadence.
        for forbidden in (
            "threading.Thread",
            "Timer(",
            "threading.Timer",
            "asyncio.",
        ):
            self.assertNotIn(forbidden, self._source, forbidden)


class Phase10AIGraphModelConstantsTests(unittest.TestCase):
    """Regression pin for the graph / icon materialisation added
    in the Phase 10AI fix cycle. Every closed set (gate
    categories, status icons, edge registry, node layout) MUST
    match the shipped Phase 10AH `Node / Edge / Status Model`
    section verbatim.
    """

    def test_seven_gate_categories(self) -> None:
        self.assertEqual(
            len(agent_loop.PHASE_10AI_GATE_CATEGORIES), 7,
        )
        for category in (
            "no_gate", "approval_gate", "evidence_gate",
            "overlap_safe_gate", "strict_mode_gate",
            "human_acceptance_gate", "token_exhaustion_gate",
        ):
            self.assertIn(
                category,
                agent_loop.PHASE_10AI_GATE_CATEGORIES,
            )

    def test_status_icon_map_covers_every_status_category(
        self,
    ) -> None:
        self.assertEqual(
            set(agent_loop.PHASE_10AI_STATUS_ICON_MAP.keys()),
            set(agent_loop.PHASE_10AI_STATUS_CATEGORIES),
        )
        for icon in (
            agent_loop.PHASE_10AI_STATUS_ICON_MAP.values()
        ):
            self.assertIsInstance(icon, str)
            self.assertGreater(len(icon), 0)

    def test_status_color_map_covers_every_status_category(
        self,
    ) -> None:
        self.assertEqual(
            set(
                agent_loop
                .PHASE_10AI_STATUS_CATEGORY_COLOR_MAP.keys()
            ),
            set(agent_loop.PHASE_10AI_STATUS_CATEGORIES),
        )
        for color in (
            agent_loop
            .PHASE_10AI_STATUS_CATEGORY_COLOR_MAP.values()
        ):
            self.assertTrue(color.startswith("#"), color)

    def test_node_layout_covers_every_vocab_key(self) -> None:
        self.assertEqual(
            set(agent_loop.PHASE_10AI_NODE_LAYOUT.keys()),
            set(
                agent_loop.PHASE_10AI_VISUALIZATION_VOCABULARY
            ),
        )
        for key, (x, y) in (
            agent_loop.PHASE_10AI_NODE_LAYOUT.items()
        ):
            self.assertIsInstance(x, int, key)
            self.assertIsInstance(y, int, key)
            self.assertGreaterEqual(x, 0, key)
            self.assertGreaterEqual(y, 0, key)
            self.assertLess(
                x + agent_loop.PHASE_10AI_NODE_BOX_WIDTH,
                agent_loop.PHASE_10AI_CANVAS_WIDTH + 1,
                key,
            )
            self.assertLess(
                y + agent_loop.PHASE_10AI_NODE_BOX_HEIGHT,
                agent_loop.PHASE_10AI_CANVAS_HEIGHT + 1,
                key,
            )

    def test_edge_registry_shape_is_closed_and_well_formed(
        self,
    ) -> None:
        vocab = set(
            agent_loop.PHASE_10AI_VISUALIZATION_VOCABULARY
        )
        gates = set(agent_loop.PHASE_10AI_GATE_CATEGORIES)
        edge_ids = set()
        for edge in agent_loop.PHASE_10AI_EDGE_REGISTRY:
            for field in (
                "id", "from_node", "to_node",
                "transition_id", "gate_category",
                "active_when",
            ):
                self.assertIn(field, edge, field)
            self.assertNotIn(
                edge["id"], edge_ids,
                f"duplicate edge id {edge['id']!r}",
            )
            edge_ids.add(edge["id"])
            self.assertIn(edge["from_node"], vocab)
            self.assertIn(edge["to_node"], vocab)
            self.assertIn(edge["gate_category"], gates)
            self.assertIn(
                edge["active_when"],
                (
                    "always", "review_branch_active",
                    "fix_branch_active", "human_gate_pending",
                    "blocked_or_halted",
                ),
                edge["active_when"],
            )

    def test_edge_registry_has_at_least_ten_edges(self) -> None:
        # Regression pin: a bounded orchestration graph MUST
        # have enough edges to actually connect the shipped
        # cycle. A collapse below this size is almost certainly
        # a refactor accident.
        self.assertGreaterEqual(
            len(agent_loop.PHASE_10AI_EDGE_REGISTRY), 10,
        )


class Phase10AIEdgeActiveDerivationTests(unittest.TestCase):

    def _derive(self, edge, advisory_state):
        return (
            agent_loop
            ._desktop_orchestration_visualization_derive_edge_active(
                edge=edge,
                advisory_state=advisory_state,
            )
        )

    def test_always_rule_returns_true(self) -> None:
        self.assertTrue(
            self._derive({"active_when": "always"}, {}),
        )

    def test_review_branch_active_reads_advisory(self) -> None:
        self.assertTrue(
            self._derive(
                {"active_when": "review_branch_active"},
                {"review_branch_active": True},
            ),
        )
        self.assertFalse(
            self._derive(
                {"active_when": "review_branch_active"},
                {"review_branch_active": False},
            ),
        )

    def test_fix_branch_active_reads_advisory(self) -> None:
        self.assertTrue(
            self._derive(
                {"active_when": "fix_branch_active"},
                {"fix_branch_active": True},
            ),
        )
        self.assertFalse(
            self._derive(
                {"active_when": "fix_branch_active"},
                {"fix_branch_active": False},
            ),
        )

    def test_human_gate_pending_reads_advisory(self) -> None:
        self.assertTrue(
            self._derive(
                {"active_when": "human_gate_pending"},
                {"human_gate_pending": True},
            ),
        )

    def test_blocked_or_halted_reads_advisory(self) -> None:
        self.assertTrue(
            self._derive(
                {"active_when": "blocked_or_halted"},
                {"blocked_or_halted": True},
            ),
        )

    def test_unknown_rule_refuses_fail_closed(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            self._derive({"active_when": "invented_rule"}, {})


class Phase10AIViewBuilderGraphShapeTests(unittest.TestCase):
    """Regression pin that the view builder actually materialises
    the node/edge/icon graph model (not just a flat text dump).
    Would fail if a future refactor drops the edges list, drops
    the per-node status_icon field, or drops the closed
    gate_categories block from the view header.
    """

    def _build(self, status="awaiting_claude_implementation"):
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td), status=status)
            return (
                agent_loop
                .build_desktop_orchestration_visualization_view(
                    controller,
                )
            )

    def test_view_includes_edges_list(self) -> None:
        view = self._build()
        self.assertIn("edges", view)
        self.assertEqual(
            len(view["edges"]),
            len(agent_loop.PHASE_10AI_EDGE_REGISTRY),
        )

    def test_view_includes_gate_categories(self) -> None:
        view = self._build()
        self.assertEqual(
            view["gate_categories"],
            list(agent_loop.PHASE_10AI_GATE_CATEGORIES),
        )

    def test_view_carries_top_level_status_icon_and_color(
        self,
    ) -> None:
        view = self._build()
        self.assertIn(
            view["status_icon"],
            agent_loop.PHASE_10AI_STATUS_ICON_MAP.values(),
        )
        self.assertTrue(view["status_color"].startswith("#"))

    def test_every_node_has_status_icon_color_and_layout(
        self,
    ) -> None:
        view = self._build()
        for node in view["nodes"]:
            self.assertIn("status_icon", node, node["id"])
            self.assertIn("status_color", node, node["id"])
            self.assertIn("layout_xy", node, node["id"])
            self.assertEqual(len(node["layout_xy"]), 2)

    def test_every_edge_has_full_shape(self) -> None:
        view = self._build()
        for edge in view["edges"]:
            for field in (
                "id", "from_node", "to_node",
                "transition_id", "gate_category",
                "edge_source_category", "active",
                "from_xy", "to_xy",
            ):
                self.assertIn(field, edge, field)
            self.assertEqual(
                edge["edge_source_category"],
                "canonical_mirror",
            )
            self.assertIsInstance(edge["active"], bool)

    def test_edges_active_flag_reflects_halted_state(
        self,
    ) -> None:
        view = self._build(status="halted_overlap_unsafe_context")
        edges_by_id = {e["id"]: e for e in view["edges"]}
        self.assertTrue(
            edges_by_id[
                "loop_state_status_to_blocked_or_halted"
            ]["active"],
        )

    def test_edges_active_flag_reflects_review_branch(
        self,
    ) -> None:
        view = self._build(status="awaiting_codex_review")
        edges_by_id = {e["id"]: e for e in view["edges"]}
        self.assertTrue(
            edges_by_id[
                "loop_state_status_to_review_branch"
            ]["active"],
        )
        self.assertFalse(
            edges_by_id[
                "loop_state_status_to_fix_branch"
            ]["active"],
        )

    def test_view_carries_canvas_dimensions(self) -> None:
        view = self._build()
        self.assertEqual(
            view["canvas_width"],
            agent_loop.PHASE_10AI_CANVAS_WIDTH,
        )
        self.assertEqual(
            view["canvas_height"],
            agent_loop.PHASE_10AI_CANVAS_HEIGHT,
        )
        self.assertEqual(
            view["node_box_width"],
            agent_loop.PHASE_10AI_NODE_BOX_WIDTH,
        )
        self.assertEqual(
            view["node_box_height"],
            agent_loop.PHASE_10AI_NODE_BOX_HEIGHT,
        )

    def test_loop_state_status_node_uses_active_status_icon(
        self,
    ) -> None:
        # The node identifying the current loop-state status
        # carries the active status_icon; other nodes carry the
        # neutral in_progress icon. That is how the graph shows
        # which node the shipped runtime is focused on.
        view = self._build(status="halted_overlap_unsafe_context")
        nodes_by_id = {n["id"]: n for n in view["nodes"]}
        self.assertEqual(
            nodes_by_id["loop_state_status"]["status_icon"],
            agent_loop.PHASE_10AI_STATUS_ICON_MAP["halted"],
        )
        self.assertEqual(
            nodes_by_id["phase"]["status_icon"],
            agent_loop.PHASE_10AI_STATUS_ICON_MAP["in_progress"],
        )


class Phase10AITextRendererGraphShapeTests(unittest.TestCase):
    """Regression pin that the text renderer emits at least one
    line per node PLUS one line per edge (not just node lines).
    Every edge line MUST carry the `[graph-edge]` attribution
    tag and its gate_category so a future review can
    grep-verify the shipped graph is materialised.
    """

    def _render(self):
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td))
            view = (
                agent_loop
                .build_desktop_orchestration_visualization_view(
                    controller,
                )
            )
        return view, (
            agent_loop
            .render_desktop_orchestration_visualization_text(
                view,
            )
        )

    def test_lines_count_equals_header_plus_nodes_plus_edges(
        self,
    ) -> None:
        view, lines = self._render()
        self.assertEqual(
            len(lines),
            1 + len(view["nodes"]) + len(view["edges"]),
        )

    def test_header_line_carries_status_icon(self) -> None:
        view, lines = self._render()
        self.assertIn(view["status_icon"], lines[0])

    def test_every_node_line_carries_a_status_icon(self) -> None:
        _view, lines = self._render()
        icons = list(
            agent_loop.PHASE_10AI_STATUS_ICON_MAP.values()
        )
        # Lines 1 through 15 are node lines.
        for body_line in lines[1:16]:
            self.assertTrue(
                any(icon in body_line for icon in icons),
                body_line,
            )

    def test_every_edge_line_carries_graph_edge_tag_and_gate(
        self,
    ) -> None:
        view, lines = self._render()
        gates = agent_loop.PHASE_10AI_GATE_CATEGORIES
        edge_lines = lines[1 + len(view["nodes"]):]
        self.assertEqual(len(edge_lines), len(view["edges"]))
        for edge_line in edge_lines:
            self.assertIn("[graph-edge]", edge_line)
            self.assertIn("->", edge_line)
            self.assertTrue(
                any(gate in edge_line for gate in gates),
                edge_line,
            )


class Phase10AITkCanvasGraphWiringTests(unittest.TestCase):
    """Source-inspection regression pin for the graph
    materialisation added in the Phase 10AI fix cycle. Would
    fail if a future refactor regressed the runtime back to a
    flat `tk.Text` value dump.
    """

    def setUp(self) -> None:
        import inspect
        self._source = inspect.getsource(
            agent_loop._launch_desktop_app_window,
        )

    def test_orchestration_panel_uses_tk_canvas(self) -> None:
        self.assertIn(
            "orchestration_visualization_canvas", self._source,
        )
        self.assertIn("tk.Canvas", self._source)

    def test_orchestration_panel_draws_node_rectangles(
        self,
    ) -> None:
        self.assertIn(
            ".create_rectangle(", self._source,
        )

    def test_orchestration_panel_draws_edge_lines_with_arrows(
        self,
    ) -> None:
        self.assertIn(".create_line(", self._source)
        self.assertIn("arrow=tk.LAST", self._source)

    def test_orchestration_panel_labels_nodes_with_icons(
        self,
    ) -> None:
        self.assertIn(".create_text(", self._source)
        self.assertIn("status_icon", self._source)

    def test_orchestration_panel_reads_view_edges_list(
        self,
    ) -> None:
        # A regression pin: the callback body must actually
        # iterate the shipped view["edges"] list to draw the
        # graph. Without this the runtime falls back to a
        # value-only dump.
        self.assertIn('view["edges"]', self._source)
        self.assertIn('view["nodes"]', self._source)

    def test_orchestration_panel_does_not_use_flat_tk_text_body(
        self,
    ) -> None:
        # The pre-fix implementation packed a single tk.Text
        # widget into the orchestration frame and inserted the
        # rendered lines into it. Regressing back to that shape
        # would mean the graph model is not visible in the
        # runtime. This pin blocks that specific regression.
        self.assertNotIn(
            "orchestration_visualization_body = tk.Text(",
            self._source,
        )
        self.assertNotIn(
            "orchestration_visualization_body.insert(",
            self._source,
        )


class FixPhaseC2ConstantsTests(unittest.TestCase):
    """Pin the shipped Fix Phase C2 closed vocabularies. Any
    widening or contraction is a contract break and MUST fail
    here loudly.
    """

    def test_signal_version(self) -> None:
        self.assertEqual(
            agent_loop.FIX_PHASE_C2_SIGNAL_VERSION,
            "fix-phase-c2-v1",
        )

    def test_four_classification_ids(self) -> None:
        self.assertEqual(
            agent_loop.FIX_PHASE_C2_CLASSIFICATION_IDS,
            (
                "existing_project", "empty_folder",
                "partial_target", "malformed_target",
            ),
        )

    def test_ux_mode_bridge_covers_every_shipped_ux_mode(
        self,
    ) -> None:
        # Every shipped Fix Phase B1 UX mode MUST bridge to
        # exactly one Fix Phase C1 classification id.
        self.assertEqual(
            set(
                agent_loop
                .FIX_PHASE_C2_UX_MODE_TO_CLASSIFICATION_MAP
                .keys()
            ),
            set(agent_loop.PRIMARY_DESKTOP_FOLDER_UX_MODES),
        )
        for classification in (
            agent_loop
            .FIX_PHASE_C2_UX_MODE_TO_CLASSIFICATION_MAP
            .values()
        ):
            self.assertIn(
                classification,
                agent_loop.FIX_PHASE_C2_CLASSIFICATION_IDS,
            )

    def test_display_map_covers_every_classification_id(
        self,
    ) -> None:
        self.assertEqual(
            set(
                agent_loop
                .FIX_PHASE_C2_CLASSIFICATION_DISPLAY_MAP
                .keys()
            ),
            set(
                agent_loop.FIX_PHASE_C2_CLASSIFICATION_IDS
            ),
        )
        required_fields = (
            "display_label", "plain_english_summary",
            "next_action_label", "next_action_help",
            "ready_to_run",
        )
        for cid, entry in (
            agent_loop
            .FIX_PHASE_C2_CLASSIFICATION_DISPLAY_MAP.items()
        ):
            for field in required_fields:
                self.assertIn(field, entry, f"{cid}.{field}")

    def test_only_existing_project_is_ready_to_run(self) -> None:
        # A regression pin per the shipped Fix Phase C1 contract:
        # only an existing (already-set-up) project is ready to
        # run; every other classification requires an explicit
        # setup / cleanup / repair gesture first.
        display_map = (
            agent_loop
            .FIX_PHASE_C2_CLASSIFICATION_DISPLAY_MAP
        )
        for cid, entry in display_map.items():
            if cid == "existing_project":
                self.assertTrue(entry["ready_to_run"], cid)
            else:
                self.assertFalse(entry["ready_to_run"], cid)

    def test_four_refusal_categories(self) -> None:
        # Fix Phase C2 fix cycle Issue 2: the closed vocabulary
        # gained a fourth entry (`cancelled_folder_picker`) so
        # the picker-cancel gesture is auditable per the Fix
        # Phase C1 contract.
        self.assertEqual(
            len(agent_loop.FIX_PHASE_C2_REFUSAL_CATEGORIES),
            4,
        )
        for category in (
            "refused_invalid_folder_path",
            "refused_unknown_shipped_ux_mode",
            "refused_missing_plain_english_display_entry",
            "cancelled_folder_picker",
        ):
            self.assertIn(
                category,
                agent_loop.FIX_PHASE_C2_REFUSAL_CATEGORIES,
            )

    def test_cancellation_category_constant_exposed(
        self,
    ) -> None:
        self.assertEqual(
            agent_loop.FIX_PHASE_C2_CANCELLATION_PICKER,
            "cancelled_folder_picker",
        )

    def test_empty_state_payload_shape(self) -> None:
        payload = agent_loop.FIX_PHASE_C2_EMPTY_STATE_PAYLOAD
        self.assertIsNone(payload["classification_id"])
        self.assertIsNone(payload["target_path"])
        self.assertFalse(payload["ready_to_run"])
        self.assertEqual(
            payload["attribution_tag"],
            "[project-classification]",
        )
        for field in (
            "display_label", "plain_english_summary",
            "next_action_label", "next_action_help",
        ):
            self.assertIsInstance(
                payload[field], str, field,
            )
            self.assertGreater(
                len(payload[field]), 0, field,
            )

    def test_attribution_tag(self) -> None:
        self.assertEqual(
            agent_loop.FIX_PHASE_C2_ATTRIBUTION,
            "[project-classification]",
        )


class FixPhaseC2ClassificationBridgeTests(unittest.TestCase):
    """Cover
    `_fix_phase_c2_derive_classification_from_ux_mode(...)`
    the pure Tk-free bridge from shipped Fix Phase B1 UX mode ->
    Fix Phase C1 plain-English classification id.
    """

    def test_bridges_every_shipped_ux_mode(self) -> None:
        expected = {
            "attach_existing_project": "existing_project",
            "bootstrap_new_project": "empty_folder",
            "refused_partial_target": "partial_target",
            "refused_malformed_target": "malformed_target",
        }
        for ux_mode, cid in expected.items():
            self.assertEqual(
                (
                    agent_loop
                    ._fix_phase_c2_derive_classification_from_ux_mode(
                        ux_mode,
                    )
                ),
                cid,
                ux_mode,
            )

    def test_refuses_unknown_ux_mode_fail_closed(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            (
                agent_loop
                ._fix_phase_c2_derive_classification_from_ux_mode(
                    "invented_ux_mode",
                )
            )


class FixPhaseC2NoFolderPayloadTests(unittest.TestCase):

    def test_returns_a_fresh_dict_copy(self) -> None:
        p1 = (
            agent_loop
            ._fix_phase_c2_format_no_folder_display_payload()
        )
        p2 = (
            agent_loop
            ._fix_phase_c2_format_no_folder_display_payload()
        )
        self.assertIsNot(p1, p2)
        p1["display_label"] = "MUTATED"
        # Mutating the returned copy MUST NOT leak into the
        # shipped constant (that would be a source-of-truth
        # leak).
        p3 = (
            agent_loop
            ._fix_phase_c2_format_no_folder_display_payload()
        )
        self.assertNotEqual(p3["display_label"], "MUTATED")

    def test_carries_empty_state_fields(self) -> None:
        payload = (
            agent_loop
            ._fix_phase_c2_format_no_folder_display_payload()
        )
        self.assertIsNone(payload["classification_id"])
        self.assertIsNone(payload["target_path"])
        self.assertFalse(payload["ready_to_run"])
        self.assertEqual(
            payload["attribution_tag"],
            "[project-classification]",
        )


class FixPhaseC2FolderDisplayPayloadTests(unittest.TestCase):
    """Cover the pure Tk-free payload formatter against real
    filesystem folder classifications. Uses TemporaryDirectory
    to stage each of the four shipped Fix Phase B1 target
    states.
    """

    def _write_full_target(self, td: Path) -> None:
        # Stage all five shipped canonical artifacts so the
        # shipped `classify_pre_bootstrap_target_state(...)`
        # returns `full_target`. `_make_controller` alone does
        # NOT satisfy that classification because Fix Phase C2
        # is about pre-attach state; the classifier looks at the
        # closed EXTERNAL_TARGET_CANONICAL_ARTIFACT_RELPATHS
        # tuple.
        _make_controller(td)
        for rel in (
            ".agent-loop/current-task.md",
            ".agent-loop/current-phase.md",
            ".agent-loop/phase-plan.md",
        ):
            path = td / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("test\n", encoding="utf-8")

    def test_existing_project_returns_ready_payload(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = Path(td)
            self._write_full_target(controller)
            payload = (
                agent_loop
                ._fix_phase_c2_format_folder_display_payload(
                    target_path=str(controller),
                )
            )
        self.assertEqual(
            payload["classification_id"], "existing_project",
        )
        self.assertTrue(payload["ready_to_run"])
        self.assertEqual(
            payload["display_label"], "Existing project",
        )
        self.assertEqual(
            payload["attribution_tag"],
            "[project-classification]",
        )

    def test_empty_folder_returns_bootstrap_payload(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            payload = (
                agent_loop
                ._fix_phase_c2_format_folder_display_payload(
                    target_path=td,
                )
            )
        self.assertEqual(
            payload["classification_id"], "empty_folder",
        )
        self.assertFalse(payload["ready_to_run"])
        self.assertEqual(
            payload["display_label"], "Empty folder",
        )
        self.assertIn(
            "set up a new project",
            payload["next_action_label"].lower(),
        )

    def test_partial_target_returns_cleanup_payload(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = Path(td)
            (controller / ".agent-loop").mkdir()
            # A partial target has some but not all of the
            # canonical set. Write just the loop-state.json to
            # trigger the shipped `partial_target` branch.
            (
                controller / ".agent-loop" / "loop-state.json"
            ).write_text("{}", encoding="utf-8")
            payload = (
                agent_loop
                ._fix_phase_c2_format_folder_display_payload(
                    target_path=str(controller),
                )
            )
        self.assertEqual(
            payload["classification_id"], "partial_target",
        )
        self.assertFalse(payload["ready_to_run"])
        # Regression pin: the plain-English label MUST NOT
        # leak the raw `partial_target` shipped-runtime term
        # into the default surface.
        self.assertNotIn(
            "partial_target", payload["display_label"],
        )

    def test_malformed_target_returns_repair_payload(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = Path(td)
            self._write_full_target(controller)
            # Corrupt loop-state.json so the shipped Phase 3A
            # schema validator refuses it.
            (
                controller / ".agent-loop" / "loop-state.json"
            ).write_text(
                "this is not valid json",
                encoding="utf-8",
            )
            payload = (
                agent_loop
                ._fix_phase_c2_format_folder_display_payload(
                    target_path=str(controller),
                )
            )
        self.assertEqual(
            payload["classification_id"], "malformed_target",
        )
        self.assertFalse(payload["ready_to_run"])
        self.assertNotIn(
            "malformed_target", payload["display_label"],
        )

    def test_none_path_refuses_fail_closed(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            (
                agent_loop
                ._fix_phase_c2_format_folder_display_payload(
                    target_path=None,
                )
            )

    def test_empty_path_refuses_fail_closed(self) -> None:
        for bad in ("", "   "):
            with self.assertRaises(agent_loop.HaltError):
                (
                    agent_loop
                    ._fix_phase_c2_format_folder_display_payload(
                        target_path=bad,
                    )
                )

    def test_nonexistent_path_refuses_fail_closed(self) -> None:
        with TemporaryDirectory() as td:
            missing = str(
                Path(td) / "does_not_exist_at_all_ever",
            )
            with self.assertRaises(agent_loop.HaltError):
                (
                    agent_loop
                    ._fix_phase_c2_format_folder_display_payload(
                        target_path=missing,
                    )
                )

    def test_payload_never_leaks_raw_cli_terms_in_display(
        self,
    ) -> None:
        # Regression pin per the shipped Fix Phase C1 contract's
        # `## Advanced Detail Hiding Rules`: the default surface
        # MUST NOT expose raw CLI subcommand names. Iterate every
        # display entry and pin that the display strings do not
        # leak raw runtime terms.
        forbidden_substrings = (
            "attach-external-target",
            "loop-state.json",
            "halted_",
            "awaiting_",
            "APPROVED_FOR_",
            "NEEDS_FIXES",
        )
        display_map = (
            agent_loop
            .FIX_PHASE_C2_CLASSIFICATION_DISPLAY_MAP
        )
        for cid, entry in display_map.items():
            for field in (
                "display_label", "plain_english_summary",
                "next_action_label", "next_action_help",
            ):
                text = entry[field]
                for token in forbidden_substrings:
                    self.assertNotIn(
                        token, text,
                        f"{cid}.{field}: raw runtime token "
                        f"{token!r} leaked into plain-English "
                        f"display",
                    )


class FixPhaseC2AuditLineTests(unittest.TestCase):

    def test_line_shape_success(self) -> None:
        line = (
            agent_loop
            ._fix_phase_c2_format_audit_line(
                classification_id="existing_project",
                epoch_seconds=1700000000,
            )
        )
        self.assertIn("[desktop-first-run-project]", line)
        self.assertIn(
            "signal_version='fix-phase-c2-v1'", line,
        )
        self.assertIn(
            "classification_id='existing_project'", line,
        )
        self.assertIn("refusal_category=None", line)
        self.assertIn("epoch_seconds=1700000000", line)

    def test_line_shape_refusal(self) -> None:
        line = (
            agent_loop
            ._fix_phase_c2_format_audit_line(
                classification_id=None,
                epoch_seconds=1700000000,
                refusal_category=(
                    "refused_invalid_folder_path"
                ),
            )
        )
        self.assertIn(
            "refusal_category='refused_invalid_folder_path'",
            line,
        )
        self.assertIn(
            "classification_id=None", line,
        )

    def test_refuses_unknown_refusal_category(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            (
                agent_loop
                ._fix_phase_c2_format_audit_line(
                    classification_id=None,
                    epoch_seconds=1700000000,
                    refusal_category="invented",
                )
            )

    def test_refuses_unknown_classification_id(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            (
                agent_loop
                ._fix_phase_c2_format_audit_line(
                    classification_id="invented_classification",
                    epoch_seconds=1700000000,
                )
            )

    def test_refuses_non_int_epoch(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            (
                agent_loop
                ._fix_phase_c2_format_audit_line(
                    classification_id="existing_project",
                    epoch_seconds="not int",
                )
            )

    def test_cancellation_category_accepted_by_formatter(
        self,
    ) -> None:
        # Regression pin for Fix Phase C2 fix cycle Issue 2:
        # the audit-line formatter MUST accept the closed
        # cancellation category so the picker-cancel gesture
        # can emit an audit line.
        line = (
            agent_loop
            ._fix_phase_c2_format_audit_line(
                classification_id=None,
                epoch_seconds=1700000000,
                refusal_category=(
                    agent_loop.FIX_PHASE_C2_CANCELLATION_PICKER
                ),
            )
        )
        self.assertIn(
            "refusal_category='cancelled_folder_picker'",
            line,
        )
        self.assertIn("classification_id=None", line)


class FixPhaseC2TkWiringTests(unittest.TestCase):
    """Source-inspection regression pin for the Fix Phase C2
    Project section wired into `_launch_desktop_app_window(...)`.
    Would fail loudly if a future refactor:
      - drops the Project section entirely
      - hides the section behind the Advanced toggle
      - reintroduces raw CLI vocabulary in the default surface
      - drops the audit-line emit
      - starts a background thread / timer / watcher
      - caches the selected folder path across sessions
    """

    def setUp(self) -> None:
        import inspect
        self._source = inspect.getsource(
            agent_loop._launch_desktop_app_window,
        )

    def test_project_section_labelframe_is_visible_by_default(
        self,
    ) -> None:
        # The Project section MUST be a top-level LabelFrame
        # packed directly under control_frame (not appended to
        # advanced_frames_holder). If a future refactor pushes
        # it behind Advanced, this pin fails.
        self.assertIn(
            'fix_phase_c2_project_frame = tk.LabelFrame(',
            self._source,
        )
        self.assertIn(
            'text="Project"', self._source,
        )
        # Regression pin: MUST NOT be appended to
        # advanced_frames_holder (that would hide it behind
        # the Advanced toggle).
        self.assertNotIn(
            "advanced_frames_holder.append("
            "fix_phase_c2_project_frame",
            self._source,
        )

    def test_project_section_calls_shipped_folder_picker(
        self,
    ) -> None:
        self.assertIn(
            '_filedialog.askdirectory(', self._source,
        )
        self.assertIn(
            '_primary_desktop_normalize_selected_folder(',
            self._source,
        )

    def test_project_section_calls_c2_payload_formatter(
        self,
    ) -> None:
        self.assertIn(
            "_fix_phase_c2_format_folder_display_payload(",
            self._source,
        )

    def test_project_section_calls_c2_audit_line_formatter(
        self,
    ) -> None:
        self.assertIn(
            "_fix_phase_c2_format_audit_line(", self._source,
        )

    def test_project_section_writes_audit_via_shipped_log_note(
        self,
    ) -> None:
        # Regression pin: the audit line MUST route through the
        # shipped `_log_note(...)` writer. A parallel audit file
        # would violate the Fix Phase C1 source-of-truth rule.
        self.assertIn("_log_note(", self._source)

    def test_project_section_does_not_persist_selected_folder(
        self,
    ) -> None:
        # Regression pin: the Fix Phase C1 contract forbids a
        # cross-session cache of the picked folder. Blocking
        # obvious persistence attempts:
        for forbidden in (
            "write_text(chosen",
            "with open(chosen",
            "json.dump(",  # would only be OK for non-picker paths
        ):
            # Bounded assertion: the picker callback MUST NOT
            # write the picked path anywhere. This exact
            # substring set is not exhaustive, but it catches
            # the obvious regression shapes.
            self.assertNotIn(
                f"{forbidden}",
                (
                    self._source.split(
                        "def _fix_phase_c2_choose_folder_click",
                        1,
                    )[1].split("def ", 1)[0]
                    if "_fix_phase_c2_choose_folder_click"
                    in self._source
                    else ""
                ),
                forbidden,
            )

    def test_project_section_does_not_start_background_thread(
        self,
    ) -> None:
        # The Fix Phase C1 contract forbids a background watcher
        # beyond the shipped Phase 10L / 10M poll cadence, and
        # the C2 section specifically refreshes only on the
        # operator's explicit Choose-Folder gesture. Blocking
        # any background thread / timer / asyncio pattern.
        project_body = self._source.split(
            "fix_phase_c2_project_frame = tk.LabelFrame(", 1,
        )[1].split(
            "# Advanced panels toggle.", 1,
        )[0]
        for forbidden in (
            "threading.Thread", "Timer(",
            "threading.Timer", "asyncio.",
            "root.after(",
        ):
            self.assertNotIn(
                forbidden, project_body, forbidden,
            )

    def test_picker_cancel_emits_cancellation_audit(
        self,
    ) -> None:
        # Regression pin for Fix Phase C2 fix cycle Issue 2: the
        # `chosen is None` branch of the picker callback MUST
        # emit the audit line via
        # `_fix_phase_c2_emit_audit(..., refusal_category=
        # FIX_PHASE_C2_CANCELLATION_PICKER)` rather than
        # returning silently.
        callback_body = self._source.split(
            "def _fix_phase_c2_choose_folder_click", 1,
        )[1].split("def ", 1)[0]
        cancel_branch = callback_body.split(
            "if chosen is None:", 1,
        )[1].split("try:", 1)[0]
        self.assertIn(
            "_fix_phase_c2_emit_audit(", cancel_branch,
        )
        self.assertIn(
            "FIX_PHASE_C2_CANCELLATION_PICKER", cancel_branch,
        )

    def test_picker_cancel_preserves_current_payload(
        self,
    ) -> None:
        # Regression pin for Fix Phase C2 fix cycle Issue 2:
        # the picker-cancel branch MUST NOT re-render the
        # payload, re-classify, or clear the current display.
        # Blocking known regression shapes.
        callback_body = self._source.split(
            "def _fix_phase_c2_choose_folder_click", 1,
        )[1].split("def ", 1)[0]
        cancel_branch = callback_body.split(
            "if chosen is None:", 1,
        )[1].split("try:", 1)[0]
        for forbidden in (
            "_fix_phase_c2_render_payload(",
            "_fix_phase_c2_format_folder_display_payload(",
            "_fix_phase_c2_format_no_folder_display_payload(",
        ):
            self.assertNotIn(
                forbidden, cancel_branch, forbidden,
            )


class FixPhaseC2LegacyFolderFrameTests(unittest.TestCase):
    """Regression pin for Fix Phase C2 fix cycle Issue 1: the
    legacy `Select Project Folder` button + `attached_target_
    label` MUST live behind the Advanced toggle so the C2
    Project section is the single default folder flow.
    """

    def setUp(self) -> None:
        import inspect
        self._source = inspect.getsource(
            agent_loop._launch_desktop_app_window,
        )

    def test_legacy_folder_frame_is_registered_behind_advanced(
        self,
    ) -> None:
        # The legacy widgets must be parented on
        # `legacy_folder_frame`, and that frame must be
        # registered in `advanced_frames_holder` so the toggle
        # hides it by default.
        self.assertIn(
            "legacy_folder_frame = tk.Frame(control_frame)",
            self._source,
        )
        self.assertIn(
            "advanced_frames_holder.append("
            "legacy_folder_frame)",
            self._source,
        )

    def test_legacy_select_button_is_parented_on_legacy_frame(
        self,
    ) -> None:
        # Locate the `select_project_button = tk.Button(...)`
        # site and confirm it is parented on
        # `legacy_folder_frame`, not on `primary_controls_frame`
        # (the pre-fix default surface).
        button_site = self._source.split(
            "select_project_button = tk.Button(", 1,
        )[1].split(")", 1)[0]
        self.assertIn(
            "legacy_folder_frame", button_site,
        )
        self.assertNotIn(
            "primary_controls_frame", button_site,
        )

    def test_legacy_attached_target_label_is_parented_on_legacy(
        self,
    ) -> None:
        label_site = self._source.split(
            "attached_target_label = tk.Label(", 1,
        )[1].split(")", 1)[0]
        self.assertIn(
            "legacy_folder_frame", label_site,
        )
        self.assertNotIn(
            "primary_controls_frame", label_site,
        )

    def test_legacy_folder_frame_not_packed_top_level_by_default(
        self,
    ) -> None:
        # Regression pin: the `legacy_folder_frame` MUST NOT be
        # packed directly under `control_frame` at construction
        # time; that would leave it visible by default and
        # defeat the Advanced-hiding.
        self.assertNotIn(
            "legacy_folder_frame.pack(", self._source,
        )


class FixPhaseC3ConstantsTests(unittest.TestCase):
    """Pin the shipped Fix Phase C3 closed vocabularies."""

    def test_signal_version(self) -> None:
        self.assertEqual(
            agent_loop.FIX_PHASE_C3_SIGNAL_VERSION,
            "fix-phase-c3-v1",
        )

    def test_four_state_ids(self) -> None:
        self.assertEqual(
            agent_loop.FIX_PHASE_C3_STATE_IDS,
            (
                "no_prd_selected",
                "prd_missing_after_project",
                "prd_invalid",
                "prd_ready",
            ),
        )

    def test_state_display_map_covers_every_state(self) -> None:
        self.assertEqual(
            set(
                agent_loop
                .FIX_PHASE_C3_STATE_DISPLAY_MAP.keys()
            ),
            set(agent_loop.FIX_PHASE_C3_STATE_IDS),
        )
        for sid, entry in (
            agent_loop
            .FIX_PHASE_C3_STATE_DISPLAY_MAP.items()
        ):
            for field in (
                "display_label", "plain_english_summary",
                "next_action_label", "next_action_help",
                "ready_to_run",
            ):
                self.assertIn(field, entry, f"{sid}.{field}")

    def test_only_prd_ready_is_ready_to_run(self) -> None:
        display_map = (
            agent_loop.FIX_PHASE_C3_STATE_DISPLAY_MAP
        )
        for sid, entry in display_map.items():
            if sid == "prd_ready":
                self.assertTrue(entry["ready_to_run"], sid)
            else:
                self.assertFalse(entry["ready_to_run"], sid)

    def test_three_refusal_categories(self) -> None:
        self.assertEqual(
            len(agent_loop.FIX_PHASE_C3_REFUSAL_CATEGORIES),
            3,
        )
        for category in (
            "refused_invalid_prd_path",
            "refused_invalid_prd_content",
            "cancelled_prd_picker",
        ):
            self.assertIn(
                category,
                agent_loop.FIX_PHASE_C3_REFUSAL_CATEGORIES,
            )

    def test_cancellation_category_constant_exposed(
        self,
    ) -> None:
        self.assertEqual(
            agent_loop.FIX_PHASE_C3_CANCELLATION_PICKER,
            "cancelled_prd_picker",
        )

    def test_attribution_tag(self) -> None:
        self.assertEqual(
            agent_loop.FIX_PHASE_C3_ATTRIBUTION,
            "[prd-intake]",
        )

    def test_empty_state_payload_shape(self) -> None:
        payload = agent_loop.FIX_PHASE_C3_EMPTY_STATE_PAYLOAD
        self.assertEqual(
            payload["state_id"], "no_prd_selected",
        )
        self.assertIsNone(payload["prd_path"])
        self.assertIsNone(payload["prd_title"])
        self.assertIsNone(payload["prd_summary_preview"])
        self.assertFalse(payload["ready_to_run"])
        self.assertEqual(
            payload["attribution_tag"], "[prd-intake]",
        )

    def test_summary_preview_max_chars_bounded(self) -> None:
        self.assertLessEqual(
            agent_loop.FIX_PHASE_C3_SUMMARY_PREVIEW_MAX_CHARS,
            400,
            "Preview MUST be bounded so the default surface "
            "does not dump the full PRD body",
        )
        self.assertGreater(
            agent_loop.FIX_PHASE_C3_SUMMARY_PREVIEW_MAX_CHARS,
            0,
        )


class FixPhaseC3StaticPayloadFormattersTests(unittest.TestCase):

    def test_no_prd_payload_returns_fresh_copy(self) -> None:
        p1 = (
            agent_loop
            ._fix_phase_c3_format_no_prd_display_payload()
        )
        p2 = (
            agent_loop
            ._fix_phase_c3_format_no_prd_display_payload()
        )
        self.assertIsNot(p1, p2)
        p1["display_label"] = "MUTATED"
        p3 = (
            agent_loop
            ._fix_phase_c3_format_no_prd_display_payload()
        )
        self.assertNotEqual(p3["display_label"], "MUTATED")

    def test_missing_after_project_payload_shape(self) -> None:
        payload = (
            agent_loop
            ._fix_phase_c3_format_missing_after_project_payload()
        )
        self.assertEqual(
            payload["state_id"], "prd_missing_after_project",
        )
        self.assertIsNone(payload["prd_path"])
        self.assertIsNone(payload["prd_title"])
        self.assertIsNone(payload["prd_summary_preview"])
        self.assertFalse(payload["ready_to_run"])
        self.assertEqual(
            payload["attribution_tag"], "[prd-intake]",
        )

    def test_invalid_payload_uses_bounded_category_copy(
        self,
    ) -> None:
        # Fix Phase C3 fix cycle Issue 2: payload MUST use the
        # shipped bounded plain-English copy from
        # `FIX_PHASE_C3_INVALID_REASON_COPY_MAP`, NOT a raw
        # Phase 9B `HaltError.reason`.
        payload = (
            agent_loop._fix_phase_c3_format_invalid_payload(
                prd_path="/nowhere/bad.json",
                reason_category=(
                    "refused_invalid_prd_content"
                ),
            )
        )
        self.assertEqual(
            payload["state_id"], "prd_invalid",
        )
        expected_copy = (
            agent_loop
            .FIX_PHASE_C3_INVALID_REASON_COPY_MAP[
                "refused_invalid_prd_content"
            ]
        )
        self.assertIn(
            expected_copy,
            payload["plain_english_summary"],
        )
        # The full absolute path is retained in the payload
        # dict (for audit / Advanced later) but the default
        # renderer converts it to filename-only.
        self.assertEqual(
            payload["prd_path"], "/nowhere/bad.json",
        )
        self.assertFalse(payload["ready_to_run"])

    def test_invalid_payload_never_leaks_raw_diagnostics(
        self,
    ) -> None:
        # Fix Phase C3 fix cycle Issue 2: the invalid-payload
        # plain-English summary MUST NOT expose parser tokens,
        # raw shipped halt-status names, or the caller-supplied
        # absolute path.
        payload = (
            agent_loop._fix_phase_c3_format_invalid_payload(
                prd_path="/some/absolute/path/bad.json",
                reason_category=(
                    "refused_invalid_prd_content"
                ),
            )
        )
        summary = payload["plain_english_summary"]
        for forbidden in (
            "/some/absolute/path/bad.json",
            "HaltError", "halted_",
            "prd_kind", "PRD_INTAKE_KIND",
            "_load_prd_intake_input",
            "_validate_prd_intake_common",
        ):
            self.assertNotIn(
                forbidden, summary, forbidden,
            )

    def test_invalid_payload_path_category_maps_to_path_copy(
        self,
    ) -> None:
        payload = (
            agent_loop._fix_phase_c3_format_invalid_payload(
                prd_path="/gone.json",
                reason_category="refused_invalid_prd_path",
            )
        )
        expected_copy = (
            agent_loop
            .FIX_PHASE_C3_INVALID_REASON_COPY_MAP[
                "refused_invalid_prd_path"
            ]
        )
        self.assertIn(
            expected_copy,
            payload["plain_english_summary"],
        )

    def test_invalid_payload_unknown_category_falls_back(
        self,
    ) -> None:
        # An unknown / None `reason_category` must still yield a
        # bounded plain-English summary; the formatter MUST NOT
        # blow up and MUST NOT surface raw diagnostics.
        for category in (None, "not_a_shipped_category"):
            payload = (
                agent_loop._fix_phase_c3_format_invalid_payload(
                    prd_path="/x.json",
                    reason_category=category,
                )
            )
            self.assertIn(
                agent_loop
                .FIX_PHASE_C3_INVALID_REASON_DEFAULT_COPY,
                payload["plain_english_summary"],
            )

    def test_preview_bounder_returns_short_string_unchanged(
        self,
    ) -> None:
        short = "A short summary."
        self.assertEqual(
            (
                agent_loop
                ._fix_phase_c3_bound_summary_preview(short)
            ),
            short,
        )

    def test_preview_bounder_truncates_long_strings_with_ellipsis(
        self,
    ) -> None:
        long_summary = "x" * 500
        bounded = (
            agent_loop
            ._fix_phase_c3_bound_summary_preview(long_summary)
        )
        self.assertLessEqual(
            len(bounded),
            agent_loop.FIX_PHASE_C3_SUMMARY_PREVIEW_MAX_CHARS,
        )
        self.assertTrue(bounded.endswith("..."))


class FixPhaseC3PrdDisplayPayloadTests(unittest.TestCase):
    """Cover the pure payload formatter against real
    TemporaryDirectory PRD files. Every branch routes through
    the shipped Phase 9B `_load_prd_intake_input(...)` +
    `_validate_prd_intake_common(...)` primitives.
    """

    def _write_prd(
        self, td: Path, *,
        prd_kind="product_brief",
        title="Test Project",
        summary="Test summary.",
    ) -> Path:
        prd_path = td / "prd.json"
        prd_path.write_text(
            json.dumps({
                "prd_kind": prd_kind,
                "title": title,
                "summary": summary,
            }),
            encoding="utf-8",
        )
        return prd_path

    def test_valid_prd_returns_ready_payload(self) -> None:
        with TemporaryDirectory() as td:
            prd_path = self._write_prd(Path(td))
            payload = (
                agent_loop
                ._fix_phase_c3_format_prd_display_payload(
                    prd_path=str(prd_path),
                )
            )
        self.assertEqual(payload["state_id"], "prd_ready")
        self.assertTrue(payload["ready_to_run"])
        self.assertEqual(
            payload["prd_title"], "Test Project",
        )
        self.assertEqual(
            payload["prd_summary_preview"], "Test summary.",
        )
        self.assertEqual(
            payload["attribution_tag"], "[prd-intake]",
        )

    def test_valid_prd_bounds_preview_when_summary_long(
        self,
    ) -> None:
        long_summary = "y" * 500
        with TemporaryDirectory() as td:
            prd_path = self._write_prd(
                Path(td), summary=long_summary,
            )
            payload = (
                agent_loop
                ._fix_phase_c3_format_prd_display_payload(
                    prd_path=str(prd_path),
                )
            )
        self.assertLessEqual(
            len(payload["prd_summary_preview"]),
            agent_loop.FIX_PHASE_C3_SUMMARY_PREVIEW_MAX_CHARS,
        )
        self.assertNotEqual(
            payload["prd_summary_preview"], long_summary,
        )

    def test_none_path_refuses_fail_closed(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            (
                agent_loop
                ._fix_phase_c3_format_prd_display_payload(
                    prd_path=None,
                )
            )

    def test_empty_path_refuses_fail_closed(self) -> None:
        for bad in ("", "   "):
            with self.assertRaises(agent_loop.HaltError):
                (
                    agent_loop
                    ._fix_phase_c3_format_prd_display_payload(
                        prd_path=bad,
                    )
                )

    def test_nonexistent_path_refuses_fail_closed(self) -> None:
        with TemporaryDirectory() as td:
            missing = str(Path(td) / "missing.json")
            with self.assertRaises(agent_loop.HaltError):
                (
                    agent_loop
                    ._fix_phase_c3_format_prd_display_payload(
                        prd_path=missing,
                    )
                )

    def test_non_json_file_refuses_fail_closed(self) -> None:
        with TemporaryDirectory() as td:
            bad = Path(td) / "not-json.json"
            bad.write_text(
                "this is not valid JSON",
                encoding="utf-8",
            )
            with self.assertRaises(agent_loop.HaltError):
                (
                    agent_loop
                    ._fix_phase_c3_format_prd_display_payload(
                        prd_path=str(bad),
                    )
                )

    def test_missing_prd_kind_refuses_fail_closed(self) -> None:
        with TemporaryDirectory() as td:
            bad = Path(td) / "no-kind.json"
            bad.write_text(
                json.dumps({
                    "title": "T", "summary": "S",
                }),
                encoding="utf-8",
            )
            with self.assertRaises(agent_loop.HaltError):
                (
                    agent_loop
                    ._fix_phase_c3_format_prd_display_payload(
                        prd_path=str(bad),
                    )
                )

    def test_missing_title_refuses_fail_closed(self) -> None:
        with TemporaryDirectory() as td:
            bad = Path(td) / "no-title.json"
            bad.write_text(
                json.dumps({
                    "prd_kind": "product_brief",
                    "summary": "S",
                }),
                encoding="utf-8",
            )
            with self.assertRaises(agent_loop.HaltError):
                (
                    agent_loop
                    ._fix_phase_c3_format_prd_display_payload(
                        prd_path=str(bad),
                    )
                )

    def test_directory_path_refuses_fail_closed(self) -> None:
        with TemporaryDirectory() as td:
            with self.assertRaises(agent_loop.HaltError):
                (
                    agent_loop
                    ._fix_phase_c3_format_prd_display_payload(
                        prd_path=td,
                    )
                )


class FixPhaseC3AuditLineTests(unittest.TestCase):

    def test_line_shape_success(self) -> None:
        line = (
            agent_loop
            ._fix_phase_c3_format_audit_line(
                state_id="prd_ready",
                epoch_seconds=1700000000,
            )
        )
        self.assertIn("[desktop-first-run-prd]", line)
        self.assertIn(
            "signal_version='fix-phase-c3-v1'", line,
        )
        self.assertIn("state_id='prd_ready'", line)
        self.assertIn("refusal_category=None", line)
        self.assertIn("epoch_seconds=1700000000", line)

    def test_line_shape_refusal_invalid_content(self) -> None:
        line = (
            agent_loop
            ._fix_phase_c3_format_audit_line(
                state_id="prd_invalid",
                epoch_seconds=1700000000,
                refusal_category=(
                    "refused_invalid_prd_content"
                ),
            )
        )
        self.assertIn(
            "refusal_category='refused_invalid_prd_content'",
            line,
        )

    def test_line_shape_cancellation(self) -> None:
        line = (
            agent_loop
            ._fix_phase_c3_format_audit_line(
                state_id=None,
                epoch_seconds=1700000000,
                refusal_category="cancelled_prd_picker",
            )
        )
        self.assertIn(
            "refusal_category='cancelled_prd_picker'", line,
        )
        self.assertIn("state_id=None", line)

    def test_refuses_unknown_refusal_category(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            (
                agent_loop
                ._fix_phase_c3_format_audit_line(
                    state_id=None,
                    epoch_seconds=1700000000,
                    refusal_category="invented",
                )
            )

    def test_refuses_unknown_state_id(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            (
                agent_loop
                ._fix_phase_c3_format_audit_line(
                    state_id="invented_state",
                    epoch_seconds=1700000000,
                )
            )

    def test_refuses_non_int_epoch(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            (
                agent_loop
                ._fix_phase_c3_format_audit_line(
                    state_id="prd_ready",
                    epoch_seconds="not int",
                )
            )


class FixPhaseC3TkWiringTests(unittest.TestCase):
    """Source-inspection regression pin for the Fix Phase C3
    PRD section wired into `_launch_desktop_app_window(...)`.
    Would fail loudly if a future refactor:
      - drops the PRD section entirely
      - hides the section behind the Advanced toggle
      - reintroduces raw CLI/parser vocabulary in the default
        surface
      - drops the audit-line emit on success, refusal, or
        cancellation
      - starts a background thread / timer / watcher
      - persists the picked PRD path across sessions
      - dumps the full PRD body into the default surface
    """

    def setUp(self) -> None:
        import inspect
        self._source = inspect.getsource(
            agent_loop._launch_desktop_app_window,
        )

    def test_prd_section_labelframe_is_visible_by_default(
        self,
    ) -> None:
        self.assertIn(
            "fix_phase_c3_prd_frame = tk.LabelFrame(",
            self._source,
        )
        self.assertIn('text="PRD"', self._source)
        # Regression pin: MUST NOT be appended to
        # advanced_frames_holder (that would hide it behind
        # the Advanced toggle and defeat the C1 ordered
        # section vocabulary).
        self.assertNotIn(
            "advanced_frames_holder.append("
            "fix_phase_c3_prd_frame",
            self._source,
        )

    def test_prd_section_calls_shipped_file_picker(self) -> None:
        self.assertIn(
            "_filedialog.askopenfilename(", self._source,
        )

    def test_prd_section_calls_c3_payload_formatter(
        self,
    ) -> None:
        self.assertIn(
            "_fix_phase_c3_format_prd_display_payload(",
            self._source,
        )

    def test_prd_section_calls_c3_audit_line_formatter(
        self,
    ) -> None:
        self.assertIn(
            "_fix_phase_c3_format_audit_line(", self._source,
        )

    def test_prd_section_writes_audit_via_shipped_log_note(
        self,
    ) -> None:
        self.assertIn("_log_note(", self._source)

    def test_picker_cancel_emits_cancellation_audit(
        self,
    ) -> None:
        # Regression pin: the `not chosen:` branch of the PRD
        # picker callback MUST emit the closed cancellation
        # audit line.
        callback_body = self._source.split(
            "def _fix_phase_c3_choose_prd_click", 1,
        )[1].split("def ", 1)[0]
        cancel_branch = callback_body.split(
            "if not chosen:", 1,
        )[1].split("try:", 1)[0]
        self.assertIn(
            "_fix_phase_c3_emit_audit(", cancel_branch,
        )
        self.assertIn(
            "FIX_PHASE_C3_CANCELLATION_PICKER", cancel_branch,
        )

    def test_picker_cancel_preserves_current_payload(
        self,
    ) -> None:
        # Regression pin: cancellation MUST NOT re-render the
        # payload, re-classify, or clear the current display.
        callback_body = self._source.split(
            "def _fix_phase_c3_choose_prd_click", 1,
        )[1].split("def ", 1)[0]
        cancel_branch = callback_body.split(
            "if not chosen:", 1,
        )[1].split("try:", 1)[0]
        for forbidden in (
            "_fix_phase_c3_render_payload(",
            "_fix_phase_c3_format_prd_display_payload(",
            "_fix_phase_c3_format_no_prd_display_payload(",
            "_fix_phase_c3_format_invalid_payload(",
        ):
            self.assertNotIn(
                forbidden, cancel_branch, forbidden,
            )

    def test_prd_section_does_not_start_background_thread(
        self,
    ) -> None:
        prd_body = self._source.split(
            "fix_phase_c3_prd_frame = tk.LabelFrame(", 1,
        )[1].split(
            "# Advanced panels toggle.", 1,
        )[0]
        for forbidden in (
            "threading.Thread", "Timer(",
            "threading.Timer", "asyncio.",
            "root.after(",
        ):
            self.assertNotIn(
                forbidden, prd_body, forbidden,
            )

    def test_prd_section_does_not_persist_chosen_prd_path(
        self,
    ) -> None:
        # Regression pin: the Fix Phase C1 contract forbids a
        # cross-session cache. The PRD callback MUST NOT write
        # the picked path or the loaded PRD content anywhere.
        callback_body = self._source.split(
            "def _fix_phase_c3_choose_prd_click", 1,
        )[1].split("def ", 1)[0]
        for forbidden in (
            "write_text(chosen",
            "with open(chosen",
        ):
            self.assertNotIn(
                forbidden, callback_body, forbidden,
            )

    def test_display_map_never_leaks_raw_runtime_tokens(
        self,
    ) -> None:
        # Regression pin per the shipped Fix Phase C1 contract's
        # `## Advanced Detail Hiding Rules`: the default surface
        # MUST NOT expose raw CLI subcommand names, canonical
        # paths, parser tokens, or refusal-token vocabulary.
        forbidden_substrings = (
            "attach-external-target", "loop-state.json",
            "halted_", "awaiting_",
            "APPROVED_FOR_", "NEEDS_FIXES",
            "_load_prd_intake_input",
            "_validate_prd_intake_common",
            "prd_kind", "PRD_INTAKE_KIND",
        )
        display_map = (
            agent_loop.FIX_PHASE_C3_STATE_DISPLAY_MAP
        )
        for sid, entry in display_map.items():
            for field in (
                "display_label", "plain_english_summary",
                "next_action_label", "next_action_help",
            ):
                text = entry[field]
                for token in forbidden_substrings:
                    self.assertNotIn(
                        token, text,
                        f"{sid}.{field}: raw runtime token "
                        f"{token!r} leaked into plain-English "
                        f"display",
                    )


class FixPhaseC3FixCycleIssue1TransitionTests(unittest.TestCase):
    """Regression pin for the Fix Phase C3 fix cycle Issue 1:
    a successful Fix Phase C2 folder-selection MUST transition
    the C3 PRD panel to `prd_missing_after_project` when the
    current PRD state is `no_prd_selected`, and MUST preserve a
    `prd_ready` state if the operator already picked a valid
    PRD earlier in the session. Source-inspection pin: the
    behavior lives inside a Tk-closure so pure execution here
    would require a full Tk root.
    """

    def setUp(self) -> None:
        import inspect
        self._source = inspect.getsource(
            agent_loop._launch_desktop_app_window,
        )
        # Slice out the shipped Fix Phase C2 callback body so
        # assertions target only the C2 success path (not the
        # C3 callback that also calls the missing-payload
        # formatter conditionally).
        c2_body = self._source.split(
            "def _fix_phase_c2_choose_folder_click", 1,
        )[1].split("def ", 1)[0]
        # The successful branch is everything AFTER the last
        # `_fix_phase_c2_render_payload(payload)` call in the
        # C2 callback body.
        self._c2_success_branch = c2_body.rsplit(
            "_fix_phase_c2_render_payload(payload)", 1,
        )[1]

    def test_state_holder_is_declared_and_initialized(
        self,
    ) -> None:
        self.assertIn(
            "fix_phase_c3_current_state_holder = [",
            self._source,
        )
        self.assertIn(
            "FIX_PHASE_C3_STATE_NO_PRD_SELECTED",
            self._source,
        )

    def test_c2_success_path_reads_c3_state_holder(
        self,
    ) -> None:
        self.assertIn(
            "fix_phase_c3_current_state_holder[0]",
            self._c2_success_branch,
        )
        self.assertIn(
            "FIX_PHASE_C3_STATE_NO_PRD_SELECTED",
            self._c2_success_branch,
        )

    def test_c2_success_path_calls_missing_after_project(
        self,
    ) -> None:
        self.assertIn(
            "_fix_phase_c3_format_missing_after_project_payload"
            "(",
            self._c2_success_branch,
        )

    def test_c2_success_path_renders_and_audits_c3_transition(
        self,
    ) -> None:
        self.assertIn(
            "_fix_phase_c3_render_payload(",
            self._c2_success_branch,
        )
        self.assertIn(
            "_fix_phase_c3_emit_audit(",
            self._c2_success_branch,
        )

    def test_c2_success_path_does_not_auto_start(
        self,
    ) -> None:
        # Fix Phase C1 no-auto-advance rule: the transition MUST
        # NOT auto-attach, bootstrap, start, or advance the
        # agent.
        for forbidden in (
            "attach_external_target(",
            "bootstrap=True",
            "start_agent(",
            "run(",
        ):
            self.assertNotIn(
                forbidden, self._c2_success_branch, forbidden,
            )

    def test_render_updates_state_holder(self) -> None:
        # The render callback MUST update the state holder so a
        # later C2 gesture sees the latest C3 state.
        render_body = self._source.split(
            "def _fix_phase_c3_render_payload", 1,
        )[1].split("def ", 1)[0]
        self.assertIn(
            "fix_phase_c3_current_state_holder[0] "
            "= payload[\"state_id\"]",
            render_body,
        )


class FixPhaseC3FixCycleIssue2DefaultSurfaceTests(
    unittest.TestCase,
):
    """Regression pin for the Fix Phase C3 fix cycle Issue 2:
    the default rendered PRD surface MUST NOT expose the
    resolved absolute path, raw parser tokens, or raw shipped
    Phase 9B validator reasons. Absolute paths and technical
    diagnostics remain reachable ONLY through the shipped audit
    evidence path (`.agent-loop/orchestrator.log`).
    """

    def setUp(self) -> None:
        import inspect
        self._source = inspect.getsource(
            agent_loop._launch_desktop_app_window,
        )
        self._render_body = self._source.split(
            "def _fix_phase_c3_render_payload", 1,
        )[1].split("def ", 1)[0]

    def test_render_uses_filename_only(self) -> None:
        # The default path Label MUST derive its text from
        # `Path(prd_path).name` (or an equivalent filename-only
        # selector), NOT from the resolved absolute path.
        self.assertIn("Path(prd_path).name", self._render_body)

    def test_render_does_not_display_raw_prd_file_prefix(
        self,
    ) -> None:
        # Regression pin: the shipped "PRD file: {prd_path}"
        # template that leaked the absolute path is gone.
        self.assertNotIn(
            'f"PRD file: {prd_path}"', self._render_body,
        )
        self.assertNotIn(
            "PRD file: {prd_path}", self._render_body,
        )

    def test_callback_passes_reason_category_not_raw_reason(
        self,
    ) -> None:
        # Regression pin: the PRD picker's HaltError branch
        # MUST pass `reason_category=` to the invalid-payload
        # formatter, NOT the raw `halt.reason`.
        callback_body = self._source.split(
            "def _fix_phase_c3_choose_prd_click", 1,
        )[1].split("def ", 1)[0]
        halt_branch = callback_body.split(
            "except HaltError", 1,
        )[1]
        self.assertIn(
            "reason_category=", halt_branch,
        )
        self.assertNotIn(
            "plain_english_reason=halt.reason", halt_branch,
        )
        self.assertNotIn(
            "plain_english_reason=halt", halt_branch,
        )

    def test_invalid_reason_copy_map_covers_both_refusal_categories(
        self,
    ) -> None:
        copy_map = (
            agent_loop.FIX_PHASE_C3_INVALID_REASON_COPY_MAP
        )
        for category in (
            "refused_invalid_prd_path",
            "refused_invalid_prd_content",
        ):
            self.assertIn(category, copy_map, category)
            self.assertIsInstance(copy_map[category], str)
            self.assertTrue(copy_map[category].strip(), category)

    def test_default_copy_never_leaks_raw_diagnostics(
        self,
    ) -> None:
        # The shipped bounded-copy map and default copy MUST NOT
        # contain parser tokens or path-shaped tokens.
        strings = list(
            agent_loop
            .FIX_PHASE_C3_INVALID_REASON_COPY_MAP.values()
        )
        strings.append(
            agent_loop
            .FIX_PHASE_C3_INVALID_REASON_DEFAULT_COPY
        )
        for text in strings:
            for forbidden in (
                "HaltError", "halted_",
                "prd_kind", "PRD_INTAKE_KIND",
                "_load_prd_intake_input",
                "_validate_prd_intake_common",
                ".json",
                "/",
                "\\",
            ):
                self.assertNotIn(
                    forbidden, text,
                    f"raw diagnostic token {forbidden!r} "
                    f"leaked into bounded copy: {text!r}",
                )


class FixPhaseC4ConstantsTests(unittest.TestCase):
    """Pin the shipped Fix Phase C4 closed vocabularies."""

    def test_signal_version(self) -> None:
        self.assertEqual(
            agent_loop.FIX_PHASE_C4_SIGNAL_VERSION,
            "fix-phase-c4-v1",
        )

    def test_three_choice_ids(self) -> None:
        self.assertEqual(
            agent_loop.FIX_PHASE_C4_CHOICE_IDS,
            (
                "guided",
                "review_each_phase",
                "more_autonomous",
            ),
        )

    def test_choice_display_map_covers_every_choice(
        self,
    ) -> None:
        self.assertEqual(
            set(
                agent_loop
                .FIX_PHASE_C4_CHOICE_DISPLAY_MAP.keys()
            ),
            set(agent_loop.FIX_PHASE_C4_CHOICE_IDS),
        )
        for cid, entry in (
            agent_loop
            .FIX_PHASE_C4_CHOICE_DISPLAY_MAP.items()
        ):
            for field in (
                "display_label", "plain_english_summary",
            ):
                self.assertIn(field, entry, f"{cid}.{field}")

    def test_three_state_ids(self) -> None:
        self.assertEqual(
            agent_loop.FIX_PHASE_C4_STATE_IDS,
            (
                "initial_no_selection",
                "mode_selected",
                "canonical_source_unavailable",
            ),
        )

    def test_state_display_map_covers_every_state(self) -> None:
        self.assertEqual(
            set(
                agent_loop
                .FIX_PHASE_C4_STATE_DISPLAY_MAP.keys()
            ),
            set(agent_loop.FIX_PHASE_C4_STATE_IDS),
        )
        for sid, entry in (
            agent_loop
            .FIX_PHASE_C4_STATE_DISPLAY_MAP.items()
        ):
            for field in (
                "display_label", "plain_english_summary",
                "next_action_label", "next_action_help",
                "ready_to_run",
            ):
                self.assertIn(field, entry, f"{sid}.{field}")

    def test_only_mode_selected_is_ready_to_run(self) -> None:
        display_map = (
            agent_loop.FIX_PHASE_C4_STATE_DISPLAY_MAP
        )
        for sid, entry in display_map.items():
            if sid == "mode_selected":
                self.assertTrue(entry["ready_to_run"], sid)
            else:
                self.assertFalse(entry["ready_to_run"], sid)

    def test_three_refusal_categories(self) -> None:
        self.assertEqual(
            len(agent_loop.FIX_PHASE_C4_REFUSAL_CATEGORIES),
            3,
        )
        for category in (
            "refused_invalid_choice",
            "refused_canonical_source_unreadable",
            "cancelled_mode_selection",
        ):
            self.assertIn(
                category,
                agent_loop.FIX_PHASE_C4_REFUSAL_CATEGORIES,
            )

    def test_attribution_tag(self) -> None:
        self.assertEqual(
            agent_loop.FIX_PHASE_C4_ATTRIBUTION,
            "[run-mode-intake]",
        )


class FixPhaseC4BridgeMappingTests(unittest.TestCase):
    """Pin the bounded bridge from C4 plain-English choices to
    shipped Phase 5A approval modes and shipped Phase 10Q
    affordance ids. The bridge exists SO the C4 selector never
    invents a new approval semantic and never persists a mode
    outside the shipped canonical loop-state.json path.
    """

    def test_choice_to_approval_mode_map_covers_every_choice(
        self,
    ) -> None:
        self.assertEqual(
            set(
                agent_loop
                .FIX_PHASE_C4_CHOICE_TO_APPROVAL_MODE_MAP
                .keys()
            ),
            set(agent_loop.FIX_PHASE_C4_CHOICE_IDS),
        )

    def test_choice_to_approval_mode_values_are_shipped_modes(
        self,
    ) -> None:
        # Every mapped approval-mode MUST be in the shipped
        # Phase 5A closed enumeration; the C4 selector NEVER
        # invents a new semantic.
        for value in (
            agent_loop
            .FIX_PHASE_C4_CHOICE_TO_APPROVAL_MODE_MAP.values()
        ):
            self.assertIn(
                value, agent_loop.ALLOWED_APPROVAL_MODES,
            )

    def test_choice_to_approval_mode_bridge_is_specific(
        self,
    ) -> None:
        # Pin exact plain-English -> shipped-mode mapping so a
        # future refactor cannot silently redirect "Guided" to
        # `autonomous` (or any other autonomy-widening move).
        self.assertEqual(
            agent_loop
            ._fix_phase_c4_map_choice_to_approval_mode(
                "guided",
            ),
            agent_loop.APPROVAL_MODE_STRICT,
        )
        self.assertEqual(
            agent_loop
            ._fix_phase_c4_map_choice_to_approval_mode(
                "review_each_phase",
            ),
            agent_loop.APPROVAL_MODE_REVIEW,
        )
        self.assertEqual(
            agent_loop
            ._fix_phase_c4_map_choice_to_approval_mode(
                "more_autonomous",
            ),
            agent_loop.APPROVAL_MODE_AUTONOMOUS,
        )

    def test_choice_to_affordance_id_bridge_is_specific(
        self,
    ) -> None:
        self.assertEqual(
            agent_loop
            ._fix_phase_c4_map_choice_to_affordance_id(
                "guided",
            ),
            "select_approval_mode_strict",
        )
        self.assertEqual(
            agent_loop
            ._fix_phase_c4_map_choice_to_affordance_id(
                "review_each_phase",
            ),
            "select_approval_mode_review",
        )
        self.assertEqual(
            agent_loop
            ._fix_phase_c4_map_choice_to_affordance_id(
                "more_autonomous",
            ),
            "select_approval_mode_autonomous",
        )

    def test_choice_to_affordance_ids_are_shipped(
        self,
    ) -> None:
        for affordance_id in (
            agent_loop
            .FIX_PHASE_C4_CHOICE_TO_AFFORDANCE_ID_MAP.values()
        ):
            self.assertIn(
                affordance_id,
                agent_loop.DESKTOP_RUN_PROFILE_AFFORDANCE_IDS,
            )

    def test_map_refuses_invented_choice_id(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._fix_phase_c4_map_choice_to_approval_mode(
                "invented",
            )
        with self.assertRaises(agent_loop.HaltError):
            (
                agent_loop
                ._fix_phase_c4_map_choice_to_affordance_id(
                    "invented",
                )
            )


class FixPhaseC4PayloadFormattersTests(unittest.TestCase):

    def test_initial_payload_shape_with_no_canonical_mode(
        self,
    ) -> None:
        payload = (
            agent_loop
            ._fix_phase_c4_format_initial_payload(
                current_canonical_mode=None,
            )
        )
        self.assertEqual(
            payload["state_id"], "initial_no_selection",
        )
        self.assertIsNone(payload["selected_choice_id"])
        self.assertEqual(
            payload["current_canonical_mode_display"],
            "Not set",
        )
        self.assertFalse(payload["ready_to_run"])
        self.assertEqual(
            payload["attribution_tag"], "[run-mode-intake]",
        )

    def test_initial_payload_shape_with_shipped_canonical_mode(
        self,
    ) -> None:
        # The canonical value flows through the shipped Phase
        # 5A -> C4 bridge and yields a plain-English label
        # (never the raw shipped mode name).
        payload = (
            agent_loop
            ._fix_phase_c4_format_initial_payload(
                current_canonical_mode=(
                    agent_loop.APPROVAL_MODE_STRICT
                ),
            )
        )
        self.assertEqual(
            payload["current_canonical_mode_display"],
            "Guided (recommended)",
        )
        # No raw shipped mode name leaks into the plain-English
        # rendering of the current canonical mode.
        for token in ("strict", "review", "autonomous"):
            self.assertNotIn(
                token,
                payload[
                    "current_canonical_mode_display"
                ].lower().split("(", 1)[0],
                token,
            )

    def test_selected_payload_shape(self) -> None:
        payload = (
            agent_loop
            ._fix_phase_c4_format_selected_payload(
                choice_id="review_each_phase",
                current_canonical_mode=(
                    agent_loop.APPROVAL_MODE_REVIEW
                ),
            )
        )
        self.assertEqual(
            payload["state_id"], "mode_selected",
        )
        self.assertEqual(
            payload["selected_choice_id"],
            "review_each_phase",
        )
        self.assertEqual(
            payload["selected_display_label"],
            "Review Each Phase",
        )
        self.assertTrue(payload["ready_to_run"])

    def test_selected_payload_refuses_invalid_choice(
        self,
    ) -> None:
        with self.assertRaises(agent_loop.HaltError):
            (
                agent_loop
                ._fix_phase_c4_format_selected_payload(
                    choice_id="invented",
                    current_canonical_mode=None,
                )
            )

    def test_canonical_source_unavailable_payload_shape(
        self,
    ) -> None:
        payload = (
            agent_loop
            ._fix_phase_c4_format_canonical_source_unavailable_payload()
        )
        self.assertEqual(
            payload["state_id"],
            "canonical_source_unavailable",
        )
        self.assertIsNone(payload["selected_choice_id"])
        self.assertEqual(
            payload["current_canonical_mode_display"],
            "Not available",
        )
        self.assertFalse(payload["ready_to_run"])

    def test_derive_plain_english_current_mode_refuses_unknown(
        self,
    ) -> None:
        with self.assertRaises(agent_loop.HaltError):
            (
                agent_loop
                ._fix_phase_c4_derive_plain_english_current_mode(
                    "not_a_shipped_mode",
                )
            )

    def test_display_map_never_leaks_raw_runtime_tokens(
        self,
    ) -> None:
        # Fix Phase C1 Advanced-detail hiding: the default
        # surface MUST NOT expose raw shipped CLI subcommand
        # names, raw canonical artifact paths, raw shipped
        # halt-status names, or raw shipped identifier tokens.
        # (The plain-English words "review" / "guided" /
        # "autonomous" appearing as natural English inside
        # sentences are permitted; the shipped mode NAMES like
        # `approval_mode: strict` are what the C1 rules forbid.)
        forbidden_substrings = (
            "loop-state.json", "proposed-phase.md",
            "attach-external-target",
            "halted_", "awaiting_",
            "APPROVED_FOR_", "NEEDS_FIXES",
            "approval_mode",
            "python scripts/agent_loop.py",
        )
        for cid, entry in (
            agent_loop
            .FIX_PHASE_C4_CHOICE_DISPLAY_MAP.items()
        ):
            for field in (
                "display_label", "plain_english_summary",
            ):
                text = entry[field]
                for token in forbidden_substrings:
                    self.assertNotIn(
                        token, text,
                        f"{cid}.{field}: raw runtime token "
                        f"{token!r} leaked",
                    )
        for sid, entry in (
            agent_loop
            .FIX_PHASE_C4_STATE_DISPLAY_MAP.items()
        ):
            for field in (
                "display_label", "plain_english_summary",
                "next_action_label", "next_action_help",
            ):
                text = entry[field]
                for token in forbidden_substrings:
                    self.assertNotIn(
                        token, text,
                        f"{sid}.{field}: raw runtime token "
                        f"{token!r} leaked",
                    )


class FixPhaseC4ClipboardPayloadDerivationTests(
    unittest.TestCase,
):
    """Pin the wiring from a C4 choice + a shipped Phase 10Q
    view to the shipped affordance's clipboard payload. The C4
    selector NEVER duplicates the shipped clipboard payload; it
    looks it up by affordance id from the shipped view.
    """

    def _real_view(self, td):
        (Path(td) / ".agent-loop").mkdir()
        return agent_loop.build_desktop_run_profiles_view(
            Path(td),
        )

    def test_derives_clipboard_payload_from_shipped_view(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            view = self._real_view(td)
        payload = (
            agent_loop
            ._fix_phase_c4_derive_clipboard_payload_from_view(
                choice_id="guided",
                run_profiles_view=view,
            )
        )
        self.assertIn("plan", payload)
        self.assertIn("activate", payload)
        # The clipboard payload for guided points to the
        # shipped strict affordance (per the C4 bridge).
        self.assertIn("strict", payload)

    def test_refuses_non_dict_view(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            (
                agent_loop
                ._fix_phase_c4_derive_clipboard_payload_from_view(
                    choice_id="guided",
                    run_profiles_view=None,
                )
            )

    def test_refuses_view_missing_affordances(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            (
                agent_loop
                ._fix_phase_c4_derive_clipboard_payload_from_view(
                    choice_id="guided",
                    run_profiles_view={"affordances": None},
                )
            )

    def test_refuses_view_missing_target_affordance(
        self,
    ) -> None:
        with self.assertRaises(agent_loop.HaltError):
            (
                agent_loop
                ._fix_phase_c4_derive_clipboard_payload_from_view(
                    choice_id="guided",
                    run_profiles_view={"affordances": []},
                )
            )

    def test_refuses_invalid_choice_id(self) -> None:
        with TemporaryDirectory() as td:
            view = self._real_view(td)
        with self.assertRaises(agent_loop.HaltError):
            (
                agent_loop
                ._fix_phase_c4_derive_clipboard_payload_from_view(
                    choice_id="invented",
                    run_profiles_view=view,
                )
            )


class FixPhaseC4AuditLineTests(unittest.TestCase):

    def test_line_shape_success(self) -> None:
        line = (
            agent_loop
            ._fix_phase_c4_format_audit_line(
                state_id="mode_selected",
                choice_id="guided",
                epoch_seconds=1700000000,
            )
        )
        self.assertIn("[run-mode-intake]", line)
        self.assertIn(
            "signal_version='fix-phase-c4-v1'", line,
        )
        self.assertIn("state_id='mode_selected'", line)
        self.assertIn("choice_id='guided'", line)
        self.assertIn("refusal_category=None", line)
        self.assertIn("epoch_seconds=1700000000", line)

    def test_line_shape_refusal_invalid_choice(self) -> None:
        line = (
            agent_loop
            ._fix_phase_c4_format_audit_line(
                state_id=None,
                choice_id=None,
                epoch_seconds=1700000000,
                refusal_category="refused_invalid_choice",
            )
        )
        self.assertIn(
            "refusal_category='refused_invalid_choice'", line,
        )

    def test_line_shape_canonical_source_unavailable(
        self,
    ) -> None:
        line = (
            agent_loop
            ._fix_phase_c4_format_audit_line(
                state_id="canonical_source_unavailable",
                choice_id="guided",
                epoch_seconds=1700000000,
                refusal_category=(
                    "refused_canonical_source_unreadable"
                ),
            )
        )
        self.assertIn(
            "state_id='canonical_source_unavailable'", line,
        )
        self.assertIn(
            "refusal_category='refused_canonical_source_"
            "unreadable'",
            line,
        )

    def test_line_shape_cancellation(self) -> None:
        line = (
            agent_loop
            ._fix_phase_c4_format_audit_line(
                state_id=None,
                choice_id=None,
                epoch_seconds=1700000000,
                refusal_category="cancelled_mode_selection",
            )
        )
        self.assertIn(
            "refusal_category='cancelled_mode_selection'",
            line,
        )

    def test_refuses_unknown_refusal_category(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            (
                agent_loop
                ._fix_phase_c4_format_audit_line(
                    state_id=None,
                    choice_id=None,
                    epoch_seconds=1700000000,
                    refusal_category="invented",
                )
            )

    def test_refuses_unknown_state_id(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            (
                agent_loop
                ._fix_phase_c4_format_audit_line(
                    state_id="invented_state",
                    choice_id="guided",
                    epoch_seconds=1700000000,
                )
            )

    def test_refuses_unknown_choice_id(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            (
                agent_loop
                ._fix_phase_c4_format_audit_line(
                    state_id="mode_selected",
                    choice_id="invented",
                    epoch_seconds=1700000000,
                )
            )

    def test_refuses_non_int_epoch(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            (
                agent_loop
                ._fix_phase_c4_format_audit_line(
                    state_id=None,
                    choice_id=None,
                    epoch_seconds="not int",
                )
            )


class FixPhaseC4TkWiringTests(unittest.TestCase):
    """Source-inspection regression pin for the Fix Phase C4
    Run Mode panel wired into `_launch_desktop_app_window(...)`.
    Would fail loudly if a future refactor:
      - drops the Run Mode section entirely
      - hides the section behind the Advanced toggle
      - reintroduces raw approval-mode names in the default
        surface
      - drops the audit-line emit on success or refusal
      - starts a background thread / timer / watcher
      - persists the selection to a UI-only settings file
      - directly writes the canonical loop-state.json
      - auto-attaches / bootstraps / starts / advances the agent
    """

    def setUp(self) -> None:
        import inspect
        self._source = inspect.getsource(
            agent_loop._launch_desktop_app_window,
        )
        self._c4_section = self._source.split(
            "# Fix Phase C4: bounded guided Run Mode section",
            1,
        )[1].split(
            "# Advanced panels toggle.", 1,
        )[0]

    def test_run_mode_labelframe_is_visible_by_default(
        self,
    ) -> None:
        self.assertIn(
            "fix_phase_c4_run_mode_frame = tk.LabelFrame(",
            self._c4_section,
        )
        self.assertIn('text="Run Mode"', self._c4_section)
        # Regression pin: MUST NOT be appended to
        # advanced_frames_holder.
        self.assertNotIn(
            "advanced_frames_holder.append("
            "fix_phase_c4_run_mode_frame",
            self._source,
        )

    def test_run_mode_calls_c4_payload_formatters(
        self,
    ) -> None:
        for formatter in (
            "_fix_phase_c4_format_initial_payload(",
            "_fix_phase_c4_format_selected_payload(",
            (
                "_fix_phase_c4_format_canonical_source_"
                "unavailable_payload("
            ),
        ):
            self.assertIn(formatter, self._c4_section, formatter)

    def test_run_mode_calls_c4_audit_line_formatter(
        self,
    ) -> None:
        self.assertIn(
            "_fix_phase_c4_format_audit_line(",
            self._c4_section,
        )

    def test_run_mode_reads_shipped_run_profiles_view(
        self,
    ) -> None:
        # Regression pin per the fix-prompt "make the selected
        # mode observable through the existing canonical
        # runtime configuration/state path" requirement: the
        # C4 section MUST route through the shipped Phase 10Q
        # view (which itself reads `.agent-loop/loop-state.
        # json`), NOT a UI-only settings file.
        self.assertIn(
            "build_desktop_run_profiles_view(",
            self._c4_section,
        )

    def test_run_mode_writes_audit_via_shipped_log_note(
        self,
    ) -> None:
        self.assertIn("_log_note(", self._c4_section)

    def test_run_mode_does_not_start_background_thread(
        self,
    ) -> None:
        for forbidden in (
            "threading.Thread", "Timer(",
            "threading.Timer", "asyncio.",
            "root.after(",
        ):
            self.assertNotIn(
                forbidden, self._c4_section, forbidden,
            )

    def test_run_mode_does_not_directly_write_canonical(
        self,
    ) -> None:
        # Regression pin: the C4 selector MUST NOT write
        # `.agent-loop/loop-state.json` or
        # `.agent-loop/proposed-phase.md` directly. The
        # operator applies the change through the shipped
        # affordance recipe.
        for forbidden in (
            "write_loop_state(",
            "write_text(loop_state",
            'open(".agent-loop/loop-state.json"',
            'open(".agent-loop/proposed-phase.md"',
            "attach_external_target(",
        ):
            self.assertNotIn(
                forbidden, self._c4_section, forbidden,
            )

    def test_run_mode_does_not_auto_start_or_advance(
        self,
    ) -> None:
        # Fix Phase C1 no-auto-advance rule: selecting a mode
        # MUST NOT auto-attach, bootstrap, start, or advance
        # the agent.
        for forbidden in (
            "bootstrap=True",
            "_run_normal_cycle_from_increment(",
            "subprocess.",
        ):
            self.assertNotIn(
                forbidden, self._c4_section, forbidden,
            )

    def test_run_mode_does_not_persist_selection_in_ui_only_file(
        self,
    ) -> None:
        # Regression pin: no UI-only settings file / preference
        # cache / recent-mode list per the prompt's explicit
        # forbid list.
        for forbidden in (
            "settings.json",
            "preferences.json",
            "run-mode-cache",
            "recent_modes",
        ):
            self.assertNotIn(
                forbidden, self._c4_section, forbidden,
            )


class FixPhaseC4RunModeSectionOrderTests(unittest.TestCase):
    """Regression pin for the shipped Fix Phase C1 ordered top-
    level section vocabulary (Project -> PRD -> Run Mode -> Run
    -> Progress). The Run Mode LabelFrame MUST be constructed
    AFTER the PRD LabelFrame and BEFORE the Advanced toggle.
    """

    def setUp(self) -> None:
        import inspect
        self._source = inspect.getsource(
            agent_loop._launch_desktop_app_window,
        )

    def test_project_prd_runmode_are_in_order(self) -> None:
        idx_project = self._source.find(
            "fix_phase_c2_project_frame = tk.LabelFrame(",
        )
        idx_prd = self._source.find(
            "fix_phase_c3_prd_frame = tk.LabelFrame(",
        )
        idx_run_mode = self._source.find(
            "fix_phase_c4_run_mode_frame = tk.LabelFrame(",
        )
        self.assertGreater(idx_project, -1, "Project frame")
        self.assertGreater(idx_prd, -1, "PRD frame")
        self.assertGreater(idx_run_mode, -1, "Run Mode frame")
        self.assertLess(idx_project, idx_prd)
        self.assertLess(idx_prd, idx_run_mode)

    def test_run_mode_frame_precedes_advanced_toggle(
        self,
    ) -> None:
        idx_run_mode = self._source.find(
            "fix_phase_c4_run_mode_frame = tk.LabelFrame(",
        )
        idx_advanced = self._source.find(
            "# Advanced panels toggle.",
        )
        self.assertGreater(idx_run_mode, -1)
        self.assertGreater(idx_advanced, -1)
        self.assertLess(idx_run_mode, idx_advanced)


if __name__ == "__main__":
    unittest.main()
