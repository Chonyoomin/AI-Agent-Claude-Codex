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


if __name__ == "__main__":
    unittest.main()
