"""Phase 9D - Autonomous Internal Review/Fix Loop tests.

Exercises `run_internal_review_fix_cycle(...)` and the
`run-internal-review-fix-cycle` CLI subcommand without going through
the live Claude / Codex CLIs. Adapter seams are patched via
`unittest.mock.patch.object` and `invoke_*=False` escape hatches, so
the tests prove the orchestration logic (Phase 9C handoff consumption,
Codex review parsing, owner routing, fix-prompt regeneration, next
Phase 9C dispatch, cycle-threshold gate, descriptor write, audit-log
lines) without requiring real CLIs or bash.

The tests deliberately stub `scripts/run_checks.sh` and the six
evidence files only when the test path runs `capture_evidence=True`;
the default test path uses `--skip-evidence` to keep the slice
narrowly focused on the review/fix glue.
"""
from __future__ import annotations

import argparse
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock


HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import agent_loop  # noqa: E402 - sys.path is set above
from agent_loop import HaltError  # noqa: E402


CONTRACT_VERSION = "phase-3a-v2"

ACTIVE_PHASE = "Phase 9 - Fully Autonomous PRD-To-Product Mode"
ACTIVE_SUB_PHASE = "Phase 9D - Autonomous Internal Review/Fix Loop"

VALID_CLAUDE_SUMMARY = (
    "# Claude Implementation Summary\n"
    "\n"
    "## Phase\n"
    f"{ACTIVE_SUB_PHASE}\n"
    "\n"
    "## Task\n"
    "Implement Phase 9D slice.\n"
    "\n"
    "## Files changed\n"
    "- scripts/agent_loop.py\n"
    "\n"
    "## What was implemented\n"
    "- autonomous review/fix glue\n"
    "\n"
    "## What was not implemented\n"
    "- Phase 9E activation\n"
    "\n"
    "## Tests added or changed\n"
    "- tests/test_internal_review_fix_loop.py\n"
    "\n"
    "## Validation run\n"
    "- pytest tests/\n"
    "\n"
    "## Assumptions\n"
    "- Phase 9C handoff descriptor on disk\n"
    "\n"
    "## Risk areas\n"
    "- bounded by max_inner_cycles\n"
)

VALID_FIX_PROMPT = (
    "# Claude Code Fix Task\n"
    "\n"
    "## Objective\n"
    "Fix prompt body.\n"
    "\n"
    "## Context\n"
    "Test context.\n"
    "\n"
    "## Required fixes\n"
    "Test fixes.\n"
    "\n"
    "## Constraints\n"
    "Test constraints.\n"
    "\n"
    "## Required output\n"
    "Test output.\n"
)

VALID_CLAUDE_PROMPT = (
    "# Claude Code Task\n"
    "\n"
    "## Phase\n"
    f"{ACTIVE_SUB_PHASE}\n"
    "\n"
    "## Objective\n"
    "Test prompt.\n"
)


def _review_md(
    verdict: str,
    *,
    issues: tuple = (),
) -> str:
    issues_body = "None" if not issues else "\n\n".join(issues)
    return (
        "# Codex Review\n"
        "\n"
        "## Verdict\n"
        f"{verdict}\n"
        "\n"
        "## Review summary\n"
        "Test review.\n"
        "\n"
        "## Claude summary accuracy\n"
        "Accurate.\n"
        "\n"
        "## Scope control\n"
        "In scope.\n"
        "\n"
        "## Validation result\n"
        "Passed.\n"
        "\n"
        "## Issues found\n"
        f"{issues_body}\n"
    )


def _claude_owned_issue_block(title: str = "Issue 1: thing") -> str:
    return (
        f"### {title}\n"
        "Severity: medium\n"
        "Category: correctness\n"
        "File(s): scripts/agent_loop.py\n"
        "Owner: Claude\n"
        "Problem:\n"
        "test problem\n"
        "Evidence:\n"
        "test evidence\n"
        "Required fix:\n"
        "do the thing"
    )


def _make_repo(td: Path) -> Path:
    (td / "AGENTS.md").write_text("test\n", encoding="utf-8")
    (td / "CLAUDE.md").write_text("test\n", encoding="utf-8")
    (td / "TASK.md").write_text("test\n", encoding="utf-8")
    (td / ".agent-loop").mkdir()
    return td


def _plant_loop_state(
    repo_root: Path,
    *,
    cycle_count: int = 0,
    max_cycles: int = 3,
    status: str = "awaiting_claude_implementation",
) -> Path:
    state_path = repo_root / ".agent-loop" / "loop-state.json"
    state_path.write_text(json.dumps({
        "phase": ACTIVE_PHASE,
        "sub_phase": ACTIVE_SUB_PHASE,
        "task": "review-fix-test",
        "status": status,
        "cycle_count": cycle_count,
        "max_cycles": max_cycles,
        "last_verdict": None,
        "last_verdict_phase": None,
        "contract_version": CONTRACT_VERSION,
        "claude_version": "claude-opus-4-7",
        "codex_version": None,
        "orchestrator_version": "phase-3d-v0",
        "approval_mode": "review",
        "awaiting_human_for": None,
    }), encoding="utf-8")
    return state_path


def _plant_canonical_artifacts(repo_root: Path) -> None:
    al = repo_root / ".agent-loop"
    (al / "claude-prompt.md").write_text(
        VALID_CLAUDE_PROMPT, encoding="utf-8",
    )
    (al / "fix-prompt.md").write_text(
        VALID_FIX_PROMPT, encoding="utf-8",
    )
    (al / "claude-summary.md").write_text(
        VALID_CLAUDE_SUMMARY, encoding="utf-8",
    )


def _plant_phase_9c_handoff(repo_root: Path) -> Path:
    handoff = repo_root / ".agent-loop" / "prompt-handoff.json"
    handoff.write_text(json.dumps({
        "handoff_signal_version": "phase-9c-v1",
        "dispatched_at": "2026-06-16T00:00:00Z",
        "mode": "implementation",
        "source_prompt_path": ".agent-loop/claude-prompt.md",
        "source_prompt_byte_size": 100,
        "phase": ACTIVE_PHASE,
        "sub_phase": ACTIVE_SUB_PHASE,
        "task": "review-fix-test",
        "cycle_count": 0,
        "approval_mode": "review",
        "last_verdict": None,
        "advisory_only": True,
        "adapter_invoked": True,
        "adapter_invocation": {
            "exit_code": 0,
            "model_id": "claude-opus-4-7",
            "duration_seconds": 1.0,
            "summary_path": ".agent-loop/claude-summary.md",
        },
    }), encoding="utf-8")
    return handoff


def _plant_review(repo_root: Path, verdict: str, *, issues: tuple = ()) -> Path:
    review = repo_root / ".agent-loop" / "codex-review.md"
    review.write_text(_review_md(verdict, issues=issues), encoding="utf-8")
    return review


class ReviewFixConstantsTests(unittest.TestCase):

    def test_signal_version_is_phase_9d_v1(self) -> None:
        self.assertEqual(
            agent_loop.INTERNAL_REVIEW_FIX_LOOP_SIGNAL_VERSION,
            "phase-9d-v1",
        )

    def test_output_rel_is_under_agent_loop(self) -> None:
        self.assertEqual(
            agent_loop.INTERNAL_REVIEW_FIX_LOOP_OUTPUT_REL,
            ".agent-loop/review-fix-loop.json",
        )

    def test_default_and_max_inner_cycles(self) -> None:
        self.assertEqual(
            agent_loop.INTERNAL_REVIEW_FIX_LOOP_DEFAULT_MAX_INNER_CYCLES,
            1,
        )
        self.assertEqual(
            agent_loop.INTERNAL_REVIEW_FIX_LOOP_MAX_MAX_INNER_CYCLES,
            5,
        )

    def test_handler_is_wired(self) -> None:
        self.assertIn(
            "run-internal-review-fix-cycle", agent_loop.HANDLERS,
        )
        self.assertIs(
            agent_loop.HANDLERS["run-internal-review-fix-cycle"],
            agent_loop.cmd_run_internal_review_fix_cycle,
        )

    def test_protected_output_set_includes_sibling_slices(self) -> None:
        # Phase 9D must not be writable to the Phase 9B intake or
        # Phase 9C handoff outputs.
        protected = agent_loop.INTERNAL_REVIEW_FIX_LOOP_PROTECTED_OUTPUT_PATHS
        self.assertIn(".agent-loop/prd-intake.json", protected)
        self.assertIn(".agent-loop/prompt-handoff.json", protected)

    def test_protected_output_set_excludes_self_default(self) -> None:
        self.assertNotIn(
            ".agent-loop/review-fix-loop.json",
            agent_loop.INTERNAL_REVIEW_FIX_LOOP_PROTECTED_OUTPUT_PATHS,
        )

    def test_sibling_protected_sets_protect_phase_9d_output(self) -> None:
        # Symmetric protection: Phase 9B / 9C cannot overwrite the
        # Phase 9D advisory descriptor either.
        self.assertIn(
            ".agent-loop/review-fix-loop.json",
            agent_loop.PRD_INTAKE_PROTECTED_OUTPUT_PATHS,
        )
        self.assertIn(
            ".agent-loop/review-fix-loop.json",
            agent_loop.PROMPT_HANDOFF_PROTECTED_OUTPUT_PATHS,
        )


class ReviewFixApprovedBranchTests(unittest.TestCase):

    def test_approved_writes_descriptor_and_terminal_status(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            state_path = _plant_loop_state(repo)
            _plant_canonical_artifacts(repo)
            _plant_phase_9c_handoff(repo)
            _plant_review(repo, "APPROVED_FOR_HUMAN_REVIEW")
            written = agent_loop.run_internal_review_fix_cycle(
                repo,
                capture_evidence=False,
                invoke_codex_adapter=False,
                invoke_claude_adapter=False,
            )
            payload = json.loads(written.read_text(encoding="utf-8"))
            self.assertEqual(payload["signal_version"], "phase-9d-v1")
            self.assertEqual(
                payload["terminal_verdict"], "APPROVED_FOR_HUMAN_REVIEW",
            )
            self.assertEqual(
                payload["terminal_status"],
                "phase_complete_awaiting_human_approval",
            )
            self.assertEqual(len(payload["iterations"]), 1)
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(
                state["status"], "phase_complete_awaiting_human_approval",
            )
            self.assertEqual(
                state["last_verdict"], "APPROVED_FOR_HUMAN_REVIEW",
            )


class ReviewFixFailedBranchTests(unittest.TestCase):

    def test_failed_requires_human_halts_with_status(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            _plant_canonical_artifacts(repo)
            _plant_phase_9c_handoff(repo)
            _plant_review(repo, "FAILED_REQUIRES_HUMAN")
            with self.assertRaises(HaltError) as ctx:
                agent_loop.run_internal_review_fix_cycle(
                    repo,
                    capture_evidence=False,
                    invoke_codex_adapter=False,
                    invoke_claude_adapter=False,
                )
            self.assertEqual(
                ctx.exception.status, "halted_failed_requires_human",
            )


class ReviewFixNeedsFixesBranchTests(unittest.TestCase):

    def test_needs_fixes_with_claude_owned_dispatches_next(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            state_path = _plant_loop_state(repo, cycle_count=0, max_cycles=3)
            _plant_canonical_artifacts(repo)
            _plant_phase_9c_handoff(repo)
            _plant_review(
                repo, "NEEDS_FIXES",
                issues=(_claude_owned_issue_block(),),
            )
            written = agent_loop.run_internal_review_fix_cycle(
                repo,
                capture_evidence=False,
                invoke_codex_adapter=False,
                invoke_claude_adapter=False,
            )
            payload = json.loads(written.read_text(encoding="utf-8"))
            self.assertEqual(payload["terminal_verdict"], "NEEDS_FIXES")
            it0 = payload["iterations"][0]
            self.assertTrue(it0["fix_prompt_refreshed"])
            self.assertEqual(
                it0["next_handoff_path"],
                ".agent-loop/prompt-handoff.json",
            )
            self.assertEqual(it0["issues"][0]["owner"], "Claude")
            # Phase 3A: cycle_count incremented at start of fix dispatch.
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(state["cycle_count"], 1)
            self.assertEqual(state["last_verdict"], "NEEDS_FIXES")
            # The slice rewrote fix-prompt.md from the Claude-owned issue.
            fix_prompt = (repo / ".agent-loop" / "fix-prompt.md").read_text(
                encoding="utf-8",
            )
            self.assertIn("Claude-owned", fix_prompt)
            self.assertIn("do the thing", fix_prompt)

    def test_needs_fixes_threshold_halts_before_dispatch(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo, cycle_count=3, max_cycles=3)
            _plant_canonical_artifacts(repo)
            _plant_phase_9c_handoff(repo)
            _plant_review(
                repo, "NEEDS_FIXES",
                issues=(_claude_owned_issue_block(),),
            )
            with self.assertRaises(HaltError) as ctx:
                agent_loop.run_internal_review_fix_cycle(
                    repo,
                    capture_evidence=False,
                    invoke_codex_adapter=False,
                    invoke_claude_adapter=False,
                )
            self.assertEqual(
                ctx.exception.status, "halted_max_cycles_reached",
            )

    def test_needs_fixes_with_zero_claude_owned_refuses(self) -> None:
        # NEEDS_FIXES with no Claude-owned issues after Codex auto-fixes
        # is refused by the shipped `_prepare_needs_fixes_follow_up`.
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            _plant_canonical_artifacts(repo)
            _plant_phase_9c_handoff(repo)
            # No issues at all -> review still has Issues found body == "None",
            # which is parse-OK but Phase 3A NEEDS_FIXES with empty Claude-side
            # is refused by _prepare_needs_fixes_follow_up.
            _plant_review(repo, "NEEDS_FIXES")
            with self.assertRaises(HaltError) as ctx:
                agent_loop.run_internal_review_fix_cycle(
                    repo,
                    capture_evidence=False,
                    invoke_codex_adapter=False,
                    invoke_claude_adapter=False,
                )
            self.assertEqual(ctx.exception.status, "halted_input_missing")


class ReviewFixRefusalTests(unittest.TestCase):

    def test_missing_phase_9c_handoff_refuses(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            _plant_canonical_artifacts(repo)
            # No prompt-handoff.json planted.
            _plant_review(repo, "APPROVED_FOR_HUMAN_REVIEW")
            with self.assertRaises(HaltError) as ctx:
                agent_loop.run_internal_review_fix_cycle(
                    repo,
                    capture_evidence=False,
                    invoke_codex_adapter=False,
                    invoke_claude_adapter=False,
                )
            self.assertEqual(ctx.exception.status, "halted_input_missing")
            self.assertIn("9C handoff", str(ctx.exception))

    def test_missing_claude_summary_refuses(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            _plant_phase_9c_handoff(repo)
            # No claude-summary.md
            with self.assertRaises(HaltError) as ctx:
                agent_loop.run_internal_review_fix_cycle(
                    repo,
                    capture_evidence=False,
                    invoke_codex_adapter=False,
                    invoke_claude_adapter=False,
                )
            self.assertEqual(
                ctx.exception.status, "halted_summary_malformed",
            )

    def test_phase_mismatch_summary_refuses(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            _plant_canonical_artifacts(repo)
            _plant_phase_9c_handoff(repo)
            # Overwrite the summary with a wrong-phase body.
            (repo / ".agent-loop" / "claude-summary.md").write_text(
                VALID_CLAUDE_SUMMARY.replace(
                    ACTIVE_SUB_PHASE, "Phase 1 - Wrong",
                ),
                encoding="utf-8",
            )
            _plant_review(repo, "APPROVED_FOR_HUMAN_REVIEW")
            with self.assertRaises(HaltError) as ctx:
                agent_loop.run_internal_review_fix_cycle(
                    repo,
                    capture_evidence=False,
                    invoke_codex_adapter=False,
                    invoke_claude_adapter=False,
                )
            self.assertEqual(
                ctx.exception.status, "halted_summary_malformed",
            )

    def test_max_inner_cycles_out_of_bounds(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            _plant_canonical_artifacts(repo)
            _plant_phase_9c_handoff(repo)
            for bad in (0, -1, 99, "two", 2.5, True):
                with self.subTest(value=bad):
                    with self.assertRaises(HaltError) as ctx:
                        agent_loop.run_internal_review_fix_cycle(
                            repo,
                            max_inner_cycles=bad,
                            capture_evidence=False,
                            invoke_codex_adapter=False,
                            invoke_claude_adapter=False,
                        )
                    self.assertEqual(
                        ctx.exception.status, "halted_input_missing",
                    )

    def test_missing_loop_state_refuses(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            # No loop-state.json
            with self.assertRaises(HaltError) as ctx:
                agent_loop.run_internal_review_fix_cycle(
                    repo,
                    capture_evidence=False,
                    invoke_codex_adapter=False,
                    invoke_claude_adapter=False,
                )
            self.assertEqual(ctx.exception.status, "halted_input_missing")


class ReviewFixOutputBoundaryTests(unittest.TestCase):

    def _common_setup(self, td: Path) -> Path:
        repo = _make_repo(td)
        _plant_loop_state(repo)
        _plant_canonical_artifacts(repo)
        _plant_phase_9c_handoff(repo)
        _plant_review(repo, "APPROVED_FOR_HUMAN_REVIEW")
        return repo

    def test_refuses_output_outside_agent_loop(self) -> None:
        with TemporaryDirectory() as td:
            repo = self._common_setup(Path(td))
            with self.assertRaises(HaltError) as ctx:
                agent_loop.run_internal_review_fix_cycle(
                    repo,
                    output_path=repo / "outside.json",
                    capture_evidence=False,
                    invoke_codex_adapter=False,
                    invoke_claude_adapter=False,
                )
            self.assertEqual(ctx.exception.status, "halted_input_missing")

    def test_refuses_output_under_memory_subtree(self) -> None:
        with TemporaryDirectory() as td:
            repo = self._common_setup(Path(td))
            with self.assertRaises(HaltError) as ctx:
                agent_loop.run_internal_review_fix_cycle(
                    repo,
                    output_path=(
                        repo / ".agent-loop" / "memory" / "x.json"
                    ),
                    capture_evidence=False,
                    invoke_codex_adapter=False,
                    invoke_claude_adapter=False,
                )
            self.assertEqual(ctx.exception.status, "halted_input_missing")

    def test_refuses_output_overwriting_handoff_descriptor(self) -> None:
        with TemporaryDirectory() as td:
            repo = self._common_setup(Path(td))
            with self.assertRaises(HaltError) as ctx:
                agent_loop.run_internal_review_fix_cycle(
                    repo,
                    output_path=(
                        repo / ".agent-loop" / "prompt-handoff.json"
                    ),
                    capture_evidence=False,
                    invoke_codex_adapter=False,
                    invoke_claude_adapter=False,
                )
            self.assertEqual(ctx.exception.status, "halted_input_missing")

    def test_refuses_output_overwriting_intake_descriptor(self) -> None:
        with TemporaryDirectory() as td:
            repo = self._common_setup(Path(td))
            with self.assertRaises(HaltError) as ctx:
                agent_loop.run_internal_review_fix_cycle(
                    repo,
                    output_path=(
                        repo / ".agent-loop" / "prd-intake.json"
                    ),
                    capture_evidence=False,
                    invoke_codex_adapter=False,
                    invoke_claude_adapter=False,
                )
            self.assertEqual(ctx.exception.status, "halted_input_missing")

    def test_safe_override_succeeds(self) -> None:
        with TemporaryDirectory() as td:
            repo = self._common_setup(Path(td))
            written = agent_loop.run_internal_review_fix_cycle(
                repo,
                output_path=(
                    repo / ".agent-loop" / "custom-review-fix.json"
                ),
                capture_evidence=False,
                invoke_codex_adapter=False,
                invoke_claude_adapter=False,
            )
            self.assertTrue(written.is_file())
            self.assertEqual(written.name, "custom-review-fix.json")


class ReviewFixAdapterSeamTests(unittest.TestCase):
    """When `invoke_codex_adapter=True`, the slice MUST reach
    `make_codex_adapter()`. When `invoke_claude_adapter=True` on a
    NEEDS_FIXES dispatch, the slice MUST reach `make_claude_adapter()`
    via the shipped Phase 9C `dispatch_prompt_handoff`. The tests
    monkey-patch both factories with spies and prove the real
    autonomous path reaches both adapter seams.
    """

    def _spy_codex_adapter(self, review_text: str):
        result = agent_loop.ExecutionResult(
            exit_code=0, model_id="codex-test", duration_seconds=0.1,
        )
        calls: list[Path] = []
        repo_ref: dict = {"path": None}

        class Spy:
            def wait_for_review(self_, review_path: Path):
                calls.append(review_path)
                review_path.write_text(review_text, encoding="utf-8")
                return result
        Spy.calls = calls
        return Spy()

    def _spy_claude_adapter(self):
        result = agent_loop.ExecutionResult(
            exit_code=0,
            model_id="claude-test",
            duration_seconds=0.1,
        )
        calls: list[tuple[Path, Path]] = []

        class Spy:
            def invoke(self_, prompt_path: Path, summary_path: Path):
                calls.append((prompt_path, summary_path))
                return result
        Spy.calls = calls
        return Spy()

    def test_default_path_invokes_codex_adapter(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            _plant_canonical_artifacts(repo)
            _plant_phase_9c_handoff(repo)
            codex_spy = self._spy_codex_adapter(
                _review_md("APPROVED_FOR_HUMAN_REVIEW"),
            )
            with mock.patch.object(
                agent_loop, "make_codex_adapter",
                return_value=codex_spy,
            ):
                written = agent_loop.run_internal_review_fix_cycle(
                    repo,
                    capture_evidence=False,
                    invoke_codex_adapter=True,
                    invoke_claude_adapter=False,
                )
            self.assertEqual(len(codex_spy.calls), 1)
            payload = json.loads(written.read_text(encoding="utf-8"))
            self.assertEqual(
                payload["iterations"][0]["codex_invocation"]["model_id"],
                "codex-test",
            )

    def test_needs_fixes_dispatches_via_claude_adapter(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo, cycle_count=0, max_cycles=3)
            _plant_canonical_artifacts(repo)
            _plant_phase_9c_handoff(repo)
            codex_spy = self._spy_codex_adapter(
                _review_md(
                    "NEEDS_FIXES",
                    issues=(_claude_owned_issue_block(),),
                ),
            )
            claude_spy = self._spy_claude_adapter()
            with mock.patch.object(
                agent_loop, "make_codex_adapter",
                return_value=codex_spy,
            ), mock.patch.object(
                agent_loop, "make_claude_adapter",
                return_value=claude_spy,
            ):
                agent_loop.run_internal_review_fix_cycle(
                    repo,
                    capture_evidence=False,
                    invoke_codex_adapter=True,
                    invoke_claude_adapter=True,
                )
            self.assertEqual(len(claude_spy.calls), 1)
            self.assertEqual(
                claude_spy.calls[0][0].name, "fix-prompt.md",
            )

    def test_two_inner_cycles_run_two_codex_invocations(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo, cycle_count=0, max_cycles=5)
            _plant_canonical_artifacts(repo)
            _plant_phase_9c_handoff(repo)
            # First call returns NEEDS_FIXES; second call returns APPROVED.
            class Cycler:
                def __init__(self_):
                    self_.calls = 0
                def wait_for_review(self_, review_path: Path):
                    self_.calls += 1
                    if self_.calls == 1:
                        review_path.write_text(
                            _review_md(
                                "NEEDS_FIXES",
                                issues=(_claude_owned_issue_block(),),
                            ),
                            encoding="utf-8",
                        )
                    else:
                        review_path.write_text(
                            _review_md("APPROVED_FOR_HUMAN_REVIEW"),
                            encoding="utf-8",
                        )
                    return agent_loop.ExecutionResult(
                        exit_code=0,
                        model_id="codex-test",
                        duration_seconds=0.0,
                    )
            cycler = Cycler()
            claude_spy = self._spy_claude_adapter()
            with mock.patch.object(
                agent_loop, "make_codex_adapter",
                return_value=cycler,
            ), mock.patch.object(
                agent_loop, "make_claude_adapter",
                return_value=claude_spy,
            ):
                written = agent_loop.run_internal_review_fix_cycle(
                    repo,
                    max_inner_cycles=2,
                    capture_evidence=False,
                    invoke_codex_adapter=True,
                    invoke_claude_adapter=True,
                )
            self.assertEqual(cycler.calls, 2)
            payload = json.loads(written.read_text(encoding="utf-8"))
            self.assertEqual(
                payload["terminal_verdict"], "APPROVED_FOR_HUMAN_REVIEW",
            )
            self.assertEqual(len(payload["iterations"]), 2)


class ReviewFixAuditLogTests(unittest.TestCase):

    def test_audit_log_records_start_iteration_and_finish(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            _plant_canonical_artifacts(repo)
            _plant_phase_9c_handoff(repo)
            _plant_review(repo, "APPROVED_FOR_HUMAN_REVIEW")
            log = repo / ".agent-loop" / "orchestrator.log"
            agent_loop.run_internal_review_fix_cycle(
                repo,
                capture_evidence=False,
                invoke_codex_adapter=False,
                invoke_claude_adapter=False,
                log_path=log,
            )
            audit = log.read_text(encoding="utf-8")
            self.assertIn("review/fix loop: started", audit)
            self.assertIn(
                "review/fix loop: iteration=0 verdict="
                "APPROVED_FOR_HUMAN_REVIEW",
                audit,
            )
            self.assertIn(
                "review/fix loop: approved",
                audit,
            )
            self.assertIn("review/fix loop: finished", audit)


class ReviewFixCliTests(unittest.TestCase):

    def setUp(self) -> None:
        self.td = TemporaryDirectory()
        self.repo = Path(self.td.name)
        _make_repo(self.repo)
        _plant_loop_state(self.repo)
        _plant_canonical_artifacts(self.repo)
        _plant_phase_9c_handoff(self.repo)
        _plant_review(self.repo, "APPROVED_FOR_HUMAN_REVIEW")
        import os
        self._prev_cwd = os.getcwd()
        os.chdir(self.repo)

    def tearDown(self) -> None:
        import os
        os.chdir(self._prev_cwd)
        self.td.cleanup()

    def test_cli_default_dry_run_writes_descriptor(self) -> None:
        rc = agent_loop.main([
            "run-internal-review-fix-cycle",
            "--skip-evidence", "--no-invoke-codex", "--no-invoke-claude",
        ])
        self.assertEqual(rc, 0)
        out = self.repo / ".agent-loop" / "review-fix-loop.json"
        self.assertTrue(out.is_file())
        payload = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(
            payload["terminal_verdict"], "APPROVED_FOR_HUMAN_REVIEW",
        )

    def test_cli_refuses_bad_output_via_halt(self) -> None:
        rc = agent_loop.main([
            "run-internal-review-fix-cycle",
            "--output", ".agent-loop/prompt-handoff.json",
            "--skip-evidence", "--no-invoke-codex", "--no-invoke-claude",
        ])
        self.assertEqual(rc, 2)

    def test_cli_refuses_absolute_output(self) -> None:
        rc = agent_loop.main([
            "run-internal-review-fix-cycle",
            "--output", str(
                (self.repo / ".agent-loop" / "x.json").resolve(),
            ),
            "--skip-evidence", "--no-invoke-codex", "--no-invoke-claude",
        ])
        self.assertEqual(rc, 2)

    def test_cli_max_inner_cycles_bounds_via_argparse(self) -> None:
        # Out-of-bound int is caught by the library validator.
        rc = agent_loop.main([
            "run-internal-review-fix-cycle",
            "--max-inner-cycles", "99",
            "--skip-evidence", "--no-invoke-codex", "--no-invoke-claude",
        ])
        self.assertEqual(rc, 2)


class ReviewFixHelpTextTests(unittest.TestCase):

    def _help_text(self) -> str:
        parser = agent_loop.build_parser()
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                for choice_action in action._choices_actions:
                    if (
                        choice_action.dest
                        == "run-internal-review-fix-cycle"
                    ):
                        return choice_action.help or ""
        self.fail(
            "run-internal-review-fix-cycle subparser help not found",
        )
        return ""

    def test_help_describes_phase_9d_role(self) -> None:
        text = self._help_text()
        self.assertIn("Phase 9D", text)
        self.assertIn("review/fix", text)

    def test_help_documents_dry_run_escape_hatches(self) -> None:
        text = self._help_text()
        self.assertIn("--skip-evidence", text)
        self.assertIn("--no-invoke-codex", text)
        self.assertIn("--no-invoke-claude", text)

    def test_help_documents_descriptor_path(self) -> None:
        text = self._help_text()
        self.assertIn(".agent-loop/review-fix-loop.json", text)


if __name__ == "__main__":
    unittest.main()
