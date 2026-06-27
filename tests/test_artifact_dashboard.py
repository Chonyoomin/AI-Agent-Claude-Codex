"""Phase 10K - Artifact Dashboard Initial Slice tests.

Exercises:
  - module-level constants (signal version, precedence note, surface
    id enumeration)
  - the six per-surface builders
    (`_build_review_summaries_surface`, `_build_diff_views_surface`,
    `_build_progress_history_surface`,
    `_build_approval_actions_surface`, `_build_token_cost_surface`,
    `_build_failure_analytics_surface`)
  - `build_artifact_dashboard_view(controller_root) -> dict`
  - the renderer + the `view-artifact-dashboard` CLI handler
  - non-mutation invariants required by the Phase 10J contract
    (no orchestrator.log write, no loop-state.json mutation, no
    canonical-artifact mutation, no `_halt` invocation, no new
    library-callable controls beyond the Phase 10I three)
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import unittest
from contextlib import redirect_stdout
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
                "Phase 10K - Artifact Dashboard Initial Slice"
            ),
            "task": "phase-10k-test",
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


def _write_review_artifacts(td: Path) -> None:
    al = td / ".agent-loop"
    (al / "claude-summary.md").write_text(
        "# Claude Implementation Summary\n## Phase\nfoo\n",
        encoding="utf-8",
    )
    (al / "codex-review.md").write_text(
        "# Codex Review\n## Verdict\nNEEDS_FIXES\n"
        "## Issues found\n### Issue 1\nfoo\n### Issue 2\nbar\n",
        encoding="utf-8",
    )
    (al / "fix-prompt.md").write_text(
        "# Fix Prompt\nfoo\n", encoding="utf-8",
    )


def _write_diff_artifacts(td: Path) -> None:
    al = td / ".agent-loop"
    (al / "git-diff.patch").write_text(
        "diff --git a/x b/x\n"
        "--- a/x\n+++ b/x\n@@ -1 +1,2 @@\n"
        "+added line\n-removed line\n",
        encoding="utf-8",
    )
    (al / "git-status.log").write_text(
        " M scripts/agent_loop.py\n", encoding="utf-8",
    )


def _write_progress_artifacts(td: Path) -> None:
    al = td / ".agent-loop"
    (al / "phase-plan.md").write_text(
        "# Phase Plan\n## Phase 10J\nfoo\n## Phase 10K\nbar\n",
        encoding="utf-8",
    )
    (al / "orchestrator.log").write_text(
        "[orchestrator] line 1\n[orchestrator] line 2\n"
        "[orchestrator] line 3\n",
        encoding="utf-8",
    )


def _write_approval_artifacts(
    td: Path, with_token: bool = False,
) -> None:
    al = td / ".agent-loop"
    body = (
        "# Proposed Phase\n## Label\nphase-10k-proposal\n"
        "## Approval\n"
    )
    if with_token:
        body += "APPROVED_FOR_ACTIVATION\n"
    (al / "proposed-phase.md").write_text(body, encoding="utf-8")


def _write_failure_artifacts(td: Path) -> None:
    al = td / ".agent-loop"
    (al / "test-output.log").write_text(
        "test failed: foo\n", encoding="utf-8",
    )
    (al / "lint-output.log").write_text(
        "lint clean\n", encoding="utf-8",
    )
    (al / "typecheck-output.log").write_text(
        "", encoding="utf-8",
    )
    (al / "build-output.log").write_text(
        "build clean\n", encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
class ConstantsTests(unittest.TestCase):

    def test_signal_version(self) -> None:
        self.assertEqual(
            agent_loop.EXTERNAL_DASHBOARD_VIEW_SIGNAL_VERSION,
            "phase-10k-v1",
        )

    def test_precedence_note_pins_phase_10j_contract(self) -> None:
        note = agent_loop.EXTERNAL_DASHBOARD_PRECEDENCE_NOTE
        for fragment in (
            "Canonical artifacts on disk always win",
            "advisory derived state",
            "Phase 10I",
            "library-callable controls",
        ):
            self.assertIn(fragment, note)

    def test_surface_ids_match_contract_six(self) -> None:
        self.assertEqual(
            agent_loop.EXTERNAL_DASHBOARD_SURFACE_IDS,
            (
                "review_summaries",
                "diff_views",
                "progress_history",
                "approval_actions",
                "token_cost",
                "failure_analytics",
            ),
        )


# ---------------------------------------------------------------------------
# Per-surface builders
# ---------------------------------------------------------------------------
class ReviewSummariesSurfaceTests(unittest.TestCase):

    def test_surface_with_all_artifacts_present(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            _write_review_artifacts(controller)
            surface = agent_loop._build_review_summaries_surface(
                controller,
            )
            self.assertEqual(surface["surface_id"], "review_summaries")
            mirrors = surface["canonical_mirrors"]
            self.assertTrue(mirrors["claude_summary"]["present"])
            self.assertTrue(mirrors["codex_review"]["present"])
            self.assertTrue(mirrors["fix_prompt"]["present"])
            # Verdict extracted advisorily from on-disk codex-review.
            self.assertEqual(
                surface["advisory"]["current_verdict"],
                "NEEDS_FIXES",
            )

    def test_surface_with_missing_artifacts(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            surface = agent_loop._build_review_summaries_surface(
                controller,
            )
            mirrors = surface["canonical_mirrors"]
            self.assertFalse(mirrors["claude_summary"]["present"])
            self.assertFalse(mirrors["codex_review"]["present"])
            self.assertIsNone(
                surface["advisory"]["current_verdict"],
            )


class DiffViewsSurfaceTests(unittest.TestCase):

    def test_surface_counts_added_and_removed_lines(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            _write_diff_artifacts(controller)
            surface = agent_loop._build_diff_views_surface(
                controller,
            )
            self.assertEqual(surface["surface_id"], "diff_views")
            self.assertTrue(
                surface["canonical_mirrors"]["git_diff_patch"][
                    "present"
                ],
            )
            self.assertEqual(
                surface["advisory"]["added_line_count"], 1,
            )
            self.assertEqual(
                surface["advisory"]["removed_line_count"], 1,
            )

    def test_missing_diff_files_surface_advisorily(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            surface = agent_loop._build_diff_views_surface(
                controller,
            )
            self.assertFalse(
                surface["canonical_mirrors"]["git_diff_patch"][
                    "present"
                ],
            )
            self.assertEqual(
                surface["advisory"]["added_line_count"], 0,
            )


class ProgressHistorySurfaceTests(unittest.TestCase):

    def test_surface_mirrors_loop_state_and_phase_plan(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            _write_progress_artifacts(controller)
            surface = agent_loop._build_progress_history_surface(
                controller,
            )
            ls = surface["canonical_mirrors"]["loop_state"]
            self.assertTrue(ls["present"])
            self.assertEqual(
                ls["mirror"]["sub_phase"],
                "Phase 10K - Artifact Dashboard Initial Slice",
            )
            headers = (
                surface["advisory"]
                ["phase_plan_section_headers_tail"]
            )
            self.assertIn("## Phase 10J", headers)
            self.assertIn("## Phase 10K", headers)
            self.assertEqual(
                surface["advisory"]["cycle_progress_hint"],
                "1 of 3 used",
            )

    def test_surface_handles_missing_loop_state(self) -> None:
        with TemporaryDirectory() as td:
            controller = Path(td) / "c"
            controller.mkdir()
            (controller / ".agent-loop").mkdir()
            surface = agent_loop._build_progress_history_surface(
                controller,
            )
            ls = surface["canonical_mirrors"]["loop_state"]
            self.assertFalse(ls["present"])
            self.assertIsNone(ls["mirror"])
            self.assertIsNone(
                surface["advisory"]["cycle_progress_hint"],
            )


class ApprovalActionsSurfaceTests(unittest.TestCase):

    def test_surface_detects_approved_token(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            _write_approval_artifacts(controller, with_token=True)
            surface = agent_loop._build_approval_actions_surface(
                controller,
            )
            self.assertTrue(
                surface["advisory"][
                    "approved_for_activation_token_present"
                ],
            )

    def test_surface_without_token(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            _write_approval_artifacts(controller, with_token=False)
            surface = agent_loop._build_approval_actions_surface(
                controller,
            )
            self.assertFalse(
                surface["advisory"][
                    "approved_for_activation_token_present"
                ],
            )

    def test_approval_affordances_are_copy_paste_only(self) -> None:
        # The Phase 10J contract requires the three approval-relevant
        # CLI affordances to be surfaced as copy-paste-only (not as
        # library-call delegations) so the dashboard cannot widen the
        # library-call surface beyond the Phase 10I three.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            surface = agent_loop._build_approval_actions_surface(
                controller,
            )
            affordances = surface["advisory"]["approval_affordances"]
            ids = {a["id"] for a in affordances}
            self.assertEqual(
                ids,
                {"plan", "activate", "record-final-acceptance"},
            )
            for affordance in affordances:
                self.assertEqual(
                    affordance["dispatch_mode"], "copy_paste",
                    f"approval affordance {affordance['id']!r} "
                    f"must be copy_paste; got "
                    f"{affordance['dispatch_mode']!r}",
                )
                self.assertEqual(
                    affordance["category"], "mutating",
                )

    def test_approval_affordance_set_does_not_widen_library_calls(
        self,
    ) -> None:
        # Cross-check: no approval affordance id collides with the
        # Phase 10I library-callable control ids.
        library_call_ids = {
            spec["id"]
            for spec in agent_loop._EXTERNAL_UI_CONTROL_REGISTRY
            if spec["dispatch_mode"] == "library_call"
        }
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            surface = agent_loop._build_approval_actions_surface(
                controller,
            )
            affordance_ids = {
                a["id"]
                for a in surface["advisory"]["approval_affordances"]
            }
            self.assertEqual(
                affordance_ids & library_call_ids, set(),
                "approval affordances must NOT collide with the "
                "Phase 10I library-callable control ids; the "
                "dashboard MUST NOT widen the library-call surface",
            )


class TokenCostSurfaceTests(unittest.TestCase):

    def test_surface_renders_cycle_progress(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            surface = agent_loop._build_token_cost_surface(
                controller,
            )
            self.assertEqual(
                surface["advisory"]["cycle_progress_hint"],
                "1 of 3 used",
            )
            self.assertFalse(
                surface["advisory"]["approaching_cycle_cap"],
            )

    def test_surface_flags_approaching_cap(self) -> None:
        # cycle_count >= max_cycles - 1 is the advisory "approaching"
        # signal. With cycle_count=2 and max_cycles=3, the hint
        # should fire.
        with TemporaryDirectory() as td:
            controller = Path(td) / "c"
            controller.mkdir()
            (controller / ".agent-loop").mkdir()
            (controller / ".agent-loop" / "loop-state.json").write_text(
                json.dumps({
                    "phase": "Phase 10 - Future Product Features",
                    "sub_phase": "Phase 10K",
                    "task": "foo",
                    "status": "awaiting_claude_implementation",
                    "cycle_count": 2, "max_cycles": 3,
                    "last_verdict": None, "last_verdict_phase": None,
                    "contract_version": CONTRACT_VERSION,
                    "claude_version": "claude-opus-4-7",
                    "codex_version": None,
                    "orchestrator_version": "phase-3d-v0",
                    "approval_mode": "review",
                    "awaiting_human_for": None,
                }),
                encoding="utf-8",
            )
            surface = agent_loop._build_token_cost_surface(
                controller,
            )
            self.assertTrue(
                surface["advisory"]["approaching_cycle_cap"],
            )

    def test_capacity_retry_state_missing_is_advisory(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            surface = agent_loop._build_token_cost_surface(
                controller,
            )
            retry = (
                surface["canonical_mirrors"]["capacity_retry_state"]
            )
            self.assertFalse(retry["present"])


class FailureAnalyticsSurfaceTests(unittest.TestCase):

    def test_surface_counts_review_issues(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            _write_review_artifacts(controller)
            surface = agent_loop._build_failure_analytics_surface(
                controller,
            )
            self.assertEqual(
                surface["advisory"]["issue_count_in_latest_review"],
                2,
            )

    def test_surface_tags_evidence_files_with_content(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            _write_failure_artifacts(controller)
            surface = agent_loop._build_failure_analytics_surface(
                controller,
            )
            categories = (
                surface["advisory"]["evidence_files_with_content"]
            )
            # typecheck-output.log is empty, so it does NOT appear.
            self.assertNotIn("typecheck_output", categories)
            self.assertIn("test_output", categories)
            self.assertIn("lint_output", categories)
            self.assertIn("build_output", categories)


# ---------------------------------------------------------------------------
# build_artifact_dashboard_view
# ---------------------------------------------------------------------------
class ViewBuildTests(unittest.TestCase):

    def test_view_shape(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.build_artifact_dashboard_view(
                controller,
            )
            self.assertEqual(
                view["view_signal_version"], "phase-10k-v1",
            )
            self.assertEqual(
                view["controller_path_canonical"],
                controller.resolve().as_posix(),
            )
            for surface_id in (
                agent_loop.EXTERNAL_DASHBOARD_SURFACE_IDS
            ):
                self.assertIn(surface_id, view["surfaces"])
            self.assertIn(
                "Canonical artifacts on disk always win",
                view["precedence_note"],
            )

    def test_view_surface_count_matches_contract_six(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.build_artifact_dashboard_view(
                controller,
            )
            self.assertEqual(len(view["surfaces"]), 6)

    def test_view_handles_missing_loop_state(self) -> None:
        with TemporaryDirectory() as td:
            controller = Path(td) / "c"
            controller.mkdir()
            view = agent_loop.build_artifact_dashboard_view(
                controller,
            )
            self.assertEqual(
                view["view_signal_version"], "phase-10k-v1",
            )
            # No raise, no halt persistence; all 6 surfaces present.
            self.assertEqual(len(view["surfaces"]), 6)


# ---------------------------------------------------------------------------
# Non-mutation invariants (Phase 10J contract)
# ---------------------------------------------------------------------------
class NonMutationInvariantsTests(unittest.TestCase):

    def test_view_build_does_not_mutate_loop_state(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            state_path = (
                controller / ".agent-loop" / "loop-state.json"
            )
            before = state_path.read_text(encoding="utf-8")
            agent_loop.build_artifact_dashboard_view(controller)
            after = state_path.read_text(encoding="utf-8")
            self.assertEqual(before, after)

    def test_view_build_does_not_write_orchestrator_log(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            log_path = (
                controller / ".agent-loop" / "orchestrator.log"
            )
            self.assertFalse(log_path.exists())
            agent_loop.build_artifact_dashboard_view(controller)
            self.assertFalse(
                log_path.exists(),
                "build_artifact_dashboard_view must NOT create "
                "`.agent-loop/orchestrator.log` (Phase 10J UI "
                "contract)",
            )

    def test_view_build_does_not_mutate_existing_orchestrator_log(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            log_path = (
                controller / ".agent-loop" / "orchestrator.log"
            )
            log_path.write_text(
                "[orchestrator] existing line\n", encoding="utf-8",
            )
            before = log_path.read_text(encoding="utf-8")
            agent_loop.build_artifact_dashboard_view(controller)
            after = log_path.read_text(encoding="utf-8")
            self.assertEqual(before, after)

    def test_view_build_does_not_mutate_review_artifacts(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            _write_review_artifacts(controller)
            al = controller / ".agent-loop"
            originals = {
                "claude_summary": (
                    al / "claude-summary.md"
                ).read_text(encoding="utf-8"),
                "codex_review": (
                    al / "codex-review.md"
                ).read_text(encoding="utf-8"),
                "fix_prompt": (
                    al / "fix-prompt.md"
                ).read_text(encoding="utf-8"),
            }
            agent_loop.build_artifact_dashboard_view(controller)
            self.assertEqual(
                (al / "claude-summary.md").read_text(
                    encoding="utf-8",
                ),
                originals["claude_summary"],
            )
            self.assertEqual(
                (al / "codex-review.md").read_text(
                    encoding="utf-8",
                ),
                originals["codex_review"],
            )

    def test_view_does_not_introduce_new_library_callable_controls(
        self,
    ) -> None:
        # The Phase 10J contract caps the library-call surface at
        # the Phase 10I three. The dashboard MUST NOT add new entries
        # to `_EXTERNAL_UI_CONTROL_REGISTRY` or expose any new
        # library-callable control via the view model.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.build_artifact_dashboard_view(
                controller,
            )
            # Walk every advisory.approval_affordance and assert
            # none claim `dispatch_mode='library_call'`.
            approval = view["surfaces"]["approval_actions"]
            for affordance in (
                approval["advisory"]["approval_affordances"]
            ):
                self.assertNotEqual(
                    affordance["dispatch_mode"], "library_call",
                    f"dashboard approval affordance "
                    f"{affordance['id']!r} declares "
                    f"dispatch_mode='library_call'; this widens "
                    f"the library-call surface beyond the Phase "
                    f"10I three and violates the Phase 10J cap",
                )

    def test_view_does_not_invoke_halt(self) -> None:
        # The Phase 10J contract explicitly forbids the dashboard
        # from invoking `_halt(...)`. Patch `_halt` to a sentinel
        # that records calls; the dashboard build must not touch it.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            calls = []

            def _record(*args, **kwargs):
                calls.append((args, kwargs))
                return -1

            with mock.patch.object(agent_loop, "_halt", _record):
                agent_loop.build_artifact_dashboard_view(controller)
            self.assertEqual(
                calls, [],
                "build_artifact_dashboard_view called _halt(...); "
                "Phase 10J contract forbids invoking _halt from "
                "the dashboard path",
            )


# ---------------------------------------------------------------------------
# CLI handler
# ---------------------------------------------------------------------------
class CmdViewArtifactDashboardTests(unittest.TestCase):

    def _run(self, controller: Path) -> tuple:
        args = argparse.Namespace(cmd="view-artifact-dashboard")
        buf = io.StringIO()
        with mock.patch.object(
            agent_loop, "find_repo_root", return_value=controller,
        ):
            with redirect_stdout(buf):
                rc = agent_loop.cmd_view_artifact_dashboard(args)
        return rc, buf.getvalue()

    def test_handler_wired(self) -> None:
        self.assertIn(
            "view-artifact-dashboard", agent_loop.HANDLERS,
        )
        self.assertIs(
            agent_loop.HANDLERS["view-artifact-dashboard"],
            agent_loop.cmd_view_artifact_dashboard,
        )

    def test_argparse_grammar(self) -> None:
        parser = agent_loop.build_parser()
        args = parser.parse_args(["view-artifact-dashboard"])
        self.assertEqual(args.cmd, "view-artifact-dashboard")

    def test_exits_zero_with_rendered_surfaces(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            _write_review_artifacts(controller)
            _write_diff_artifacts(controller)
            _write_progress_artifacts(controller)
            _write_approval_artifacts(controller, with_token=True)
            _write_failure_artifacts(controller)
            rc, output = self._run(controller)
            self.assertEqual(rc, 0)
            self.assertIn(
                "signal_version='phase-10k-v1'", output,
            )
            for surface_id in (
                agent_loop.EXTERNAL_DASHBOARD_SURFACE_IDS
            ):
                self.assertIn(
                    f"surface: {surface_id}", output,
                    f"rendered output missing surface "
                    f"{surface_id!r}",
                )
            self.assertIn("[canonical mirror]", output)
            self.assertIn("[advisory]", output)
            self.assertIn("precedence_note:", output)

    def test_cli_does_not_mutate_controller_state(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            state_path = (
                controller / ".agent-loop" / "loop-state.json"
            )
            log_path = (
                controller / ".agent-loop" / "orchestrator.log"
            )
            before = state_path.read_text(encoding="utf-8")
            log_exists_before = log_path.exists()
            self._run(controller)
            self.assertEqual(
                before, state_path.read_text(encoding="utf-8"),
            )
            self.assertEqual(
                log_path.exists(), log_exists_before,
            )


# ---------------------------------------------------------------------------
# Contract-mandated source-artifact coverage (Phase 10K fix cycle):
#
# The Phase 10J contract names additional canonical source artifacts for
# three surfaces that the initial Phase 10K slice did not yet mirror.
# These tests pin the coverage so a future change cannot silently drop
# the contract-mandated mirrors.
# ---------------------------------------------------------------------------


def _write_raw_memory_entry(
    controller: Path, *, category: str, filename: str,
    phase: str, sub_phase: str, cycle_count: int, body: dict,
) -> Path:
    cat_dir = (
        controller / ".agent-loop" / "memory" / category
    )
    cat_dir.mkdir(parents=True, exist_ok=True)
    envelope = {
        "signal_version": "phase-6b-v1",
        "category": category,
        "phase": phase,
        "sub_phase": sub_phase,
        "cycle_count": cycle_count,
        "source_artifact_path": ".agent-loop/codex-review.md",
        "created_at": "2026-06-26T00:00:00Z",
        "supersedes": None,
        "body": json.dumps(body),
    }
    path = cat_dir / filename
    path.write_text(json.dumps(envelope, indent=2), encoding="utf-8")
    return path


class ProgressHistoryDistillationCoverageTests(unittest.TestCase):
    """Phase 10J contract: Progress History MUST mirror the per-phase
    Phase 6I distillation entries under `.agent-loop/memory/` when
    present.
    """

    def test_surface_mirrors_distillation_summary_entries(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            _write_raw_memory_entry(
                controller,
                category=agent_loop.MEMORY_CATEGORY_SUMMARY,
                filename="20260626T000000Z-aaaaaaaa.json",
                phase="Phase 10", sub_phase="Phase 10K",
                cycle_count=1,
                body={
                    agent_loop.DISTILLATION_BODY_MARKER_FIELD: (
                        agent_loop.DISTILLATION_SIGNAL_VERSION
                    ),
                    "summary": "distilled phase boundary",
                },
            )
            surface = (
                agent_loop._build_progress_history_surface(controller)
            )
            mirror = surface["canonical_mirrors"][
                "distillation_summary_entries"
            ]
            self.assertTrue(mirror["present"])
            self.assertEqual(mirror["entry_count"], 1)
            self.assertEqual(
                mirror["entries"][0]["filename"],
                "20260626T000000Z-aaaaaaaa.json",
            )

    def test_surface_mirrors_distillation_in_all_three_categories(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            for cat, fname in (
                (agent_loop.MEMORY_CATEGORY_SUMMARY,
                 "20260626T000000Z-aaaaaaaa.json"),
                (agent_loop.MEMORY_CATEGORY_DECISION,
                 "20260626T000000Z-bbbbbbbb.json"),
                (agent_loop.MEMORY_CATEGORY_FAILURE,
                 "20260626T000000Z-cccccccc.json"),
            ):
                _write_raw_memory_entry(
                    controller, category=cat, filename=fname,
                    phase="Phase 10", sub_phase="Phase 10K",
                    cycle_count=1,
                    body={
                        agent_loop.DISTILLATION_BODY_MARKER_FIELD: (
                            agent_loop.DISTILLATION_SIGNAL_VERSION
                        ),
                    },
                )
            surface = (
                agent_loop._build_progress_history_surface(controller)
            )
            mirrors = surface["canonical_mirrors"]
            self.assertEqual(
                mirrors["distillation_summary_entries"][
                    "entry_count"
                ], 1,
            )
            self.assertEqual(
                mirrors["distillation_decision_entries"][
                    "entry_count"
                ], 1,
            )
            self.assertEqual(
                mirrors["distillation_failure_entries"][
                    "entry_count"
                ], 1,
            )
            self.assertEqual(
                surface["advisory"]["distillation_entry_total"], 3,
            )

    def test_surface_skips_non_distillation_memory_entries(
        self,
    ) -> None:
        # A failure-category entry that is NOT a Phase 6I distillation
        # entry (e.g. a Phase 6L synthesis entry) MUST NOT appear in
        # the distillation_failure_entries mirror.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            _write_raw_memory_entry(
                controller,
                category=agent_loop.MEMORY_CATEGORY_FAILURE,
                filename="20260626T000000Z-dddddddd.json",
                phase="Phase 10", sub_phase="Phase 10K",
                cycle_count=2,
                body={
                    agent_loop.REPEATED_FAILURE_BODY_MARKER_FIELD: (
                        agent_loop.REPEATED_FAILURE_SIGNAL_VERSION
                    ),
                },
            )
            surface = (
                agent_loop._build_progress_history_surface(controller)
            )
            self.assertEqual(
                surface["canonical_mirrors"][
                    "distillation_failure_entries"
                ]["entry_count"], 0,
            )

    def test_surface_handles_missing_memory_dir(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            surface = (
                agent_loop._build_progress_history_surface(controller)
            )
            for key in (
                "distillation_summary_entries",
                "distillation_decision_entries",
                "distillation_failure_entries",
            ):
                mirror = surface["canonical_mirrors"][key]
                self.assertFalse(mirror["present"])
                self.assertEqual(mirror["entry_count"], 0)
            self.assertEqual(
                surface["advisory"]["distillation_entry_total"], 0,
            )


class TokenCostExhaustionCoverageTests(unittest.TestCase):
    """Phase 10J contract: Token / Cost Reporting MUST mirror the
    Phase 6F token-exhaustion checkpoint files AND the Phase 6G/6H
    continuation context.
    """

    def test_surface_mirrors_token_exhaustion_checkpoint(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            _write_raw_memory_entry(
                controller,
                category=agent_loop.MEMORY_CATEGORY_CHECKPOINT,
                filename="20260626T000000Z-eeeeeeee.json",
                phase="Phase 10", sub_phase="Phase 10K",
                cycle_count=1,
                body={
                    "checkpoint_signal_version": (
                        agent_loop.CHECKPOINT_SIGNAL_VERSION
                    ),
                    "task": "t",
                    "status": (
                        agent_loop.HALTED_TOKEN_EXHAUSTION
                    ),
                    "approval_mode": "review",
                    "awaiting_human_for": None,
                    "active_prompt_path": (
                        ".agent-loop/claude-prompt.md"
                    ),
                    "suspension_reason": (
                        agent_loop.TOKEN_EXHAUSTION_SUSPENSION_REASON
                    ),
                    "continuation_budget": 2,
                },
            )
            surface = agent_loop._build_token_cost_surface(controller)
            mirror = surface["canonical_mirrors"][
                "token_exhaustion_checkpoints"
            ]
            self.assertTrue(mirror["present"])
            self.assertEqual(mirror["entry_count"], 1)
            self.assertEqual(
                surface["advisory"][
                    "token_exhaustion_checkpoint_count"
                ], 1,
            )

    def test_surface_skips_non_token_exhaustion_checkpoints(
        self,
    ) -> None:
        # A checkpoint with a non-token-exhaustion suspension reason
        # (e.g. strict-mode halt) MUST NOT appear in the
        # token-exhaustion enumeration.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            _write_raw_memory_entry(
                controller,
                category=agent_loop.MEMORY_CATEGORY_CHECKPOINT,
                filename="20260626T000000Z-ffffffff.json",
                phase="Phase 10", sub_phase="Phase 10K",
                cycle_count=1,
                body={
                    "checkpoint_signal_version": (
                        agent_loop.CHECKPOINT_SIGNAL_VERSION
                    ),
                    "task": "t",
                    "status": (
                        "halted_awaiting_human_pre_codex_review_normal"
                    ),
                    "approval_mode": "strict",
                    "awaiting_human_for": "pre_codex_review",
                    "active_prompt_path": (
                        ".agent-loop/claude-prompt.md"
                    ),
                    "suspension_reason": (
                        "halted_awaiting_human_pre_codex_review_normal"
                    ),
                    "continuation_budget": 0,
                },
            )
            surface = agent_loop._build_token_cost_surface(controller)
            self.assertEqual(
                surface["canonical_mirrors"][
                    "token_exhaustion_checkpoints"
                ]["entry_count"], 0,
            )

    def test_surface_mirrors_continuation_context_file(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            (
                controller / agent_loop.CONTINUATION_CONTEXT_OUTPUT_REL
            ).write_text("{\"k\": 1}", encoding="utf-8")
            surface = agent_loop._build_token_cost_surface(controller)
            mirror = surface["canonical_mirrors"][
                "continuation_context"
            ]
            self.assertTrue(mirror["present"])
            self.assertGreater(mirror["byte_size"], 0)

    def test_surface_continuation_context_missing_is_advisory(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            surface = agent_loop._build_token_cost_surface(controller)
            mirror = surface["canonical_mirrors"][
                "continuation_context"
            ]
            self.assertFalse(mirror["present"])


class FailureAnalyticsExtendedCoverageTests(unittest.TestCase):
    """Phase 10J contract: Failure Analytics MUST mirror the Phase 6L
    repeated-failure synthesis entries AND the `last_verdict` /
    `status` fields from `loop-state.json` as canonical inputs.
    """

    def test_surface_mirrors_repeated_failure_synthesis(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            _write_raw_memory_entry(
                controller,
                category=agent_loop.MEMORY_CATEGORY_FAILURE,
                filename="20260626T000000Z-66666666.json",
                phase="Phase 10", sub_phase="Phase 10K",
                cycle_count=3,
                body={
                    agent_loop.REPEATED_FAILURE_BODY_MARKER_FIELD: (
                        agent_loop.REPEATED_FAILURE_SIGNAL_VERSION
                    ),
                    "source_memory_entries": [
                        "memory/failure/a.json",
                        "memory/failure/b.json",
                    ],
                },
            )
            surface = (
                agent_loop._build_failure_analytics_surface(controller)
            )
            mirror = surface["canonical_mirrors"][
                "repeated_failure_synthesis_entries"
            ]
            self.assertTrue(mirror["present"])
            self.assertEqual(mirror["entry_count"], 1)
            self.assertEqual(
                surface["advisory"][
                    "repeated_failure_synthesis_count"
                ], 1,
            )

    def test_surface_skips_non_synthesis_failure_entries(self) -> None:
        # A Phase 6I distillation `failure` entry must NOT count
        # toward the Phase 6L synthesis enumeration.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            _write_raw_memory_entry(
                controller,
                category=agent_loop.MEMORY_CATEGORY_FAILURE,
                filename="20260626T000000Z-77777777.json",
                phase="Phase 10", sub_phase="Phase 10K",
                cycle_count=1,
                body={
                    agent_loop.DISTILLATION_BODY_MARKER_FIELD: (
                        agent_loop.DISTILLATION_SIGNAL_VERSION
                    ),
                },
            )
            surface = (
                agent_loop._build_failure_analytics_surface(controller)
            )
            self.assertEqual(
                surface["canonical_mirrors"][
                    "repeated_failure_synthesis_entries"
                ]["entry_count"], 0,
            )

    def test_surface_mirrors_loop_state_failure_context(self) -> None:
        with TemporaryDirectory() as td:
            controller = Path(td) / "c"
            controller.mkdir()
            (controller / ".agent-loop").mkdir()
            (
                controller / ".agent-loop" / "loop-state.json"
            ).write_text(
                json.dumps({
                    "phase": "Phase 10",
                    "sub_phase": "Phase 10K",
                    "task": "t",
                    "status": "halted_awaiting_human_review",
                    "cycle_count": 2, "max_cycles": 3,
                    "last_verdict": "NEEDS_FIXES",
                    "last_verdict_phase": "Phase 10K",
                    "contract_version": CONTRACT_VERSION,
                    "claude_version": "claude-opus-4-7",
                    "codex_version": None,
                    "orchestrator_version": "phase-3d-v0",
                    "approval_mode": "review",
                    "awaiting_human_for": None,
                }),
                encoding="utf-8",
            )
            surface = (
                agent_loop._build_failure_analytics_surface(controller)
            )
            ls = surface["canonical_mirrors"][
                "loop_state_failure_context"
            ]
            self.assertTrue(ls["present"])
            self.assertEqual(
                ls["mirror"]["last_verdict"], "NEEDS_FIXES",
            )
            self.assertEqual(
                ls["mirror"]["status"], "halted_awaiting_human_review",
            )
            self.assertEqual(
                surface["advisory"]["loop_state_last_verdict"],
                "NEEDS_FIXES",
            )
            self.assertEqual(
                surface["advisory"]["loop_state_status"],
                "halted_awaiting_human_review",
            )

    def test_surface_handles_missing_loop_state(self) -> None:
        with TemporaryDirectory() as td:
            controller = Path(td) / "c"
            controller.mkdir()
            (controller / ".agent-loop").mkdir()
            surface = (
                agent_loop._build_failure_analytics_surface(controller)
            )
            ls = surface["canonical_mirrors"][
                "loop_state_failure_context"
            ]
            self.assertFalse(ls["present"])
            self.assertIsNone(
                surface["advisory"]["loop_state_last_verdict"],
            )
            self.assertIsNone(
                surface["advisory"]["loop_state_status"],
            )


class DashboardScanMemoryHelperTests(unittest.TestCase):
    """The shared `_dashboard_scan_memory_category` helper backs the
    three new mirrors. These tests pin its read-only soft-failure
    semantics so a future change cannot accidentally raise from the
    dashboard build path.
    """

    def test_missing_directory_returns_present_false(self) -> None:
        with TemporaryDirectory() as td:
            controller = Path(td) / "c"
            controller.mkdir()
            result = agent_loop._dashboard_scan_memory_category(
                controller, category="summary",
                body_predicate=lambda body: True,
            )
            self.assertFalse(result["present"])
            self.assertEqual(result["entry_count"], 0)
            self.assertEqual(result["entries"], ())
            self.assertIsNone(result["error"])

    def test_malformed_json_entries_are_skipped(self) -> None:
        with TemporaryDirectory() as td:
            controller = Path(td) / "c"
            cat_dir = (
                controller / ".agent-loop" / "memory" / "summary"
            )
            cat_dir.mkdir(parents=True)
            (cat_dir / "broken.json").write_text(
                "not json", encoding="utf-8",
            )
            result = agent_loop._dashboard_scan_memory_category(
                controller, category="summary",
                body_predicate=lambda body: True,
            )
            self.assertTrue(result["present"])
            self.assertEqual(result["entry_count"], 0)

    def test_predicate_filters_entries(self) -> None:
        with TemporaryDirectory() as td:
            controller = Path(td) / "c"
            _write_raw_memory_entry(
                controller, category="summary",
                filename="20260626T000000Z-99999999.json",
                phase="P", sub_phase="S", cycle_count=1,
                body={"keep": True},
            )
            _write_raw_memory_entry(
                controller, category="summary",
                filename="20260626T000000Z-88888888.json",
                phase="P", sub_phase="S", cycle_count=1,
                body={"keep": False},
            )
            result = agent_loop._dashboard_scan_memory_category(
                controller, category="summary",
                body_predicate=lambda body: body.get("keep") is True,
            )
            self.assertEqual(result["entry_count"], 1)
            self.assertEqual(
                result["entries"][0]["filename"],
                "20260626T000000Z-99999999.json",
            )

    def test_results_are_capped_at_max_entries(self) -> None:
        with TemporaryDirectory() as td:
            controller = Path(td) / "c"
            for i in range(8):
                _write_raw_memory_entry(
                    controller, category="summary",
                    filename=(
                        f"20260626T00000{i}Z-aaaaaaaa.json"
                    ),
                    phase="P", sub_phase="S", cycle_count=i,
                    body={"k": True},
                )
            result = agent_loop._dashboard_scan_memory_category(
                controller, category="summary",
                body_predicate=lambda body: True,
                max_entries=3,
            )
            self.assertEqual(result["entry_count"], 8)
            self.assertEqual(len(result["entries"]), 3)


class DashboardRendererMemoryMirrorTests(unittest.TestCase):
    """The renderer MUST attribute each memory-entries mirror to its
    on-disk source directory and tag it as `[canonical mirror]`.
    """

    def test_rendered_output_includes_distillation_attribution(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            _write_raw_memory_entry(
                controller,
                category=agent_loop.MEMORY_CATEGORY_SUMMARY,
                filename="20260626T000000Z-aaaaaaaa.json",
                phase="Phase 10", sub_phase="Phase 10K",
                cycle_count=1,
                body={
                    agent_loop.DISTILLATION_BODY_MARKER_FIELD: (
                        agent_loop.DISTILLATION_SIGNAL_VERSION
                    ),
                },
            )
            view = agent_loop.build_artifact_dashboard_view(controller)
            lines = agent_loop._dashboard_render_view_lines(view)
            output = "\n".join(lines)
            self.assertIn(
                "[canonical mirror] distillation_summary_entries "
                "(.agent-loop/memory/summary/):",
                output,
            )
            self.assertIn(
                "entry: filename='20260626T000000Z-aaaaaaaa.json'",
                output,
            )


if __name__ == "__main__":
    unittest.main()
