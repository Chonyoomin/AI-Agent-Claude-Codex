"""Phase 9E - Long-Run Continuation And Completion Heuristics tests.

Exercises `evaluate_phase_completion(...)` and
`run_long_run_continuation(...)` plus the
`run-long-run-continuation` CLI subcommand without going through
the live Claude / Codex CLIs. Adapter seams are patched via
`unittest.mock.patch.object`; Phase 9D hops are driven through
the shipped `run_internal_review_fix_cycle(...)` with mocked
adapters.

The tests prove:
  - completion detection across approved / failed / halted / active
    states from canonical loop-state
  - default `max_hops` is bounded and >= 1
  - the loop stops at the FIRST terminal signal without invoking
    Phase 9D again
  - a Phase 9D halt inside a hop is CAPTURED into the advisory
    descriptor without propagating out of Phase 9E
  - structural refusal vocabulary fires fail-closed on the same
    paths the underlying Phase 9D validators refuse
  - the symmetric cross-slice output-boundary protects Phase 9B /
    9C / 9D descriptors from a Phase 9E write
  - the operator-facing argparse help cannot drift silently away
    from the runtime contract
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
ACTIVE_SUB_PHASE = "Phase 9E - Long-Run Continuation And Completion Heuristics"

VALID_CLAUDE_SUMMARY = (
    "# Claude Implementation Summary\n"
    "\n"
    "## Phase\n"
    f"{ACTIVE_SUB_PHASE}\n"
    "\n"
    "## Task\n"
    "Implement Phase 9E slice.\n"
    "\n"
    "## Files changed\n"
    "- scripts/agent_loop.py\n"
    "\n"
    "## What was implemented\n"
    "- long-run continuation\n"
    "\n"
    "## What was not implemented\n"
    "- Phase 9F\n"
    "\n"
    "## Tests added or changed\n"
    "- tests/test_long_run_continuation.py\n"
    "\n"
    "## Validation run\n"
    "- pytest tests/\n"
    "\n"
    "## Assumptions\n"
    "- Phase 9C handoff descriptor on disk\n"
    "\n"
    "## Risk areas\n"
    "- bounded by max_hops\n"
)

VALID_FIX_PROMPT = (
    "# Claude Code Fix Task\n"
    "\n"
    "## Objective\n"
    "Fix.\n"
    "\n"
    "## Context\n"
    "Ctx.\n"
    "\n"
    "## Required fixes\n"
    "Fix.\n"
    "\n"
    "## Constraints\n"
    "Tight.\n"
    "\n"
    "## Required output\n"
    "Update summary.\n"
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


def _review_md(verdict: str, *, issues: tuple = ()) -> str:
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
    last_verdict=None,
) -> Path:
    state_path = repo_root / ".agent-loop" / "loop-state.json"
    state_path.write_text(json.dumps({
        "phase": ACTIVE_PHASE,
        "sub_phase": ACTIVE_SUB_PHASE,
        "task": "long-run-test",
        "status": status,
        "cycle_count": cycle_count,
        "max_cycles": max_cycles,
        "last_verdict": last_verdict,
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


def _plant_phase_9c_handoff(
    repo_root: Path,
    *,
    cycle_count: int = 0,
) -> Path:
    handoff = repo_root / ".agent-loop" / "prompt-handoff.json"
    handoff.write_text(json.dumps({
        "handoff_signal_version": "phase-9c-v1",
        "dispatched_at": "2026-06-17T00:00:00Z",
        "mode": "implementation",
        "source_prompt_path": ".agent-loop/claude-prompt.md",
        "source_prompt_byte_size": 100,
        "phase": ACTIVE_PHASE,
        "sub_phase": ACTIVE_SUB_PHASE,
        "task": "long-run-test",
        "cycle_count": cycle_count,
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


class LongRunConstantsTests(unittest.TestCase):

    def test_signal_version_is_phase_9e_v1(self) -> None:
        self.assertEqual(
            agent_loop.LONG_RUN_CONTINUATION_SIGNAL_VERSION,
            "phase-9e-v1",
        )

    def test_output_rel_is_under_agent_loop(self) -> None:
        self.assertEqual(
            agent_loop.LONG_RUN_CONTINUATION_OUTPUT_REL,
            ".agent-loop/long-run-continuation.json",
        )

    def test_default_and_max_hops(self) -> None:
        self.assertGreaterEqual(
            agent_loop.LONG_RUN_CONTINUATION_DEFAULT_MAX_HOPS, 1,
        )
        self.assertEqual(
            agent_loop.LONG_RUN_CONTINUATION_DEFAULT_MAX_HOPS, 2,
        )
        self.assertEqual(
            agent_loop.LONG_RUN_CONTINUATION_MAX_MAX_HOPS, 8,
        )

    def test_handler_is_wired(self) -> None:
        self.assertIn(
            "run-long-run-continuation", agent_loop.HANDLERS,
        )
        self.assertIs(
            agent_loop.HANDLERS["run-long-run-continuation"],
            agent_loop.cmd_run_long_run_continuation,
        )

    def test_completion_signals_vocabulary(self) -> None:
        self.assertEqual(
            agent_loop.LONG_RUN_CONTINUATION_COMPLETION_SIGNALS,
            frozenset({
                "completion_approved",
                "completion_failed",
                "completion_halted",
            }),
        )

    def test_protected_output_set_includes_sibling_slices(self) -> None:
        protected = (
            agent_loop.LONG_RUN_CONTINUATION_PROTECTED_OUTPUT_PATHS
        )
        for sibling in (
            ".agent-loop/prd-intake.json",
            ".agent-loop/prompt-handoff.json",
            ".agent-loop/review-fix-loop.json",
        ):
            self.assertIn(sibling, protected)

    def test_protected_output_set_excludes_self_default(self) -> None:
        self.assertNotIn(
            ".agent-loop/long-run-continuation.json",
            agent_loop.LONG_RUN_CONTINUATION_PROTECTED_OUTPUT_PATHS,
        )

    def test_sibling_sets_protect_phase_9e_output(self) -> None:
        # Symmetric: Phase 9B / 9C / 9D protected sets all include
        # the Phase 9E descriptor path so no sibling slice can
        # overwrite it.
        for sibling_set in (
            agent_loop.PRD_INTAKE_PROTECTED_OUTPUT_PATHS,
            agent_loop.PROMPT_HANDOFF_PROTECTED_OUTPUT_PATHS,
            agent_loop.INTERNAL_REVIEW_FIX_LOOP_PROTECTED_OUTPUT_PATHS,
        ):
            self.assertIn(
                ".agent-loop/long-run-continuation.json", sibling_set,
            )


class EvaluatePhaseCompletionTests(unittest.TestCase):
    """`evaluate_phase_completion(...)` reads canonical loop-state
    and returns a structured completion determination.
    """

    def test_approved_terminal_state(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(
                repo,
                status="phase_complete_awaiting_human_approval",
                last_verdict="APPROVED_FOR_HUMAN_REVIEW",
            )
            result = agent_loop.evaluate_phase_completion(repo)
            self.assertEqual(
                result["completion_signal"], "completion_approved",
            )
            self.assertEqual(
                result["last_verdict"], "APPROVED_FOR_HUMAN_REVIEW",
            )

    def test_failed_terminal_state(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(
                repo,
                status="halted_failed_requires_human",
                last_verdict="FAILED_REQUIRES_HUMAN",
            )
            result = agent_loop.evaluate_phase_completion(repo)
            self.assertEqual(
                result["completion_signal"], "completion_failed",
            )

    def test_failed_verdict_without_halt_still_terminal(self) -> None:
        # If loop-state carries FAILED_REQUIRES_HUMAN as last_verdict
        # but the status hasn't been moved (e.g. a malformed prior
        # cycle), the failed signal still fires.
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(
                repo,
                status="awaiting_codex_review",
                last_verdict="FAILED_REQUIRES_HUMAN",
            )
            result = agent_loop.evaluate_phase_completion(repo)
            self.assertEqual(
                result["completion_signal"], "completion_failed",
            )

    def test_generic_halt_status_terminal(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(
                repo,
                status="halted_max_cycles_reached",
            )
            result = agent_loop.evaluate_phase_completion(repo)
            self.assertEqual(
                result["completion_signal"], "completion_halted",
            )
            self.assertEqual(
                result["terminal_status"], "halted_max_cycles_reached",
            )

    def test_active_state_not_terminal(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(
                repo, status="awaiting_claude_implementation",
            )
            result = agent_loop.evaluate_phase_completion(repo)
            self.assertIsNone(result["completion_signal"])
            self.assertIsNone(result["terminal_status"])

    def test_in_flight_states_not_terminal(self) -> None:
        for status in (
            "claude_implementing", "claude_fixing",
            "evidence_capture", "awaiting_codex_review",
        ):
            with self.subTest(status=status):
                with TemporaryDirectory() as td:
                    repo = _make_repo(Path(td))
                    _plant_loop_state(repo, status=status)
                    result = agent_loop.evaluate_phase_completion(repo)
                    self.assertIsNone(result["completion_signal"])

    def test_missing_loop_state_refuses(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            with self.assertRaises(HaltError) as ctx:
                agent_loop.evaluate_phase_completion(repo)
            self.assertEqual(ctx.exception.status, "halted_input_missing")


class LongRunBoundsAndRefusalTests(unittest.TestCase):

    def _common_setup(self, td: Path) -> Path:
        repo = _make_repo(td)
        _plant_loop_state(repo)
        _plant_canonical_artifacts(repo)
        _plant_phase_9c_handoff(repo)
        _plant_review(repo, "APPROVED_FOR_HUMAN_REVIEW")
        return repo

    def test_missing_loop_state_refuses(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            with self.assertRaises(HaltError) as ctx:
                agent_loop.run_long_run_continuation(
                    repo,
                    capture_evidence=False,
                    invoke_codex_adapter=False,
                    invoke_claude_adapter=False,
                )
            self.assertEqual(ctx.exception.status, "halted_input_missing")

    def test_max_hops_out_of_bounds(self) -> None:
        with TemporaryDirectory() as td:
            repo = self._common_setup(Path(td))
            for bad in (0, -1, 99, "two", 2.5, True):
                with self.subTest(value=bad):
                    with self.assertRaises(HaltError) as ctx:
                        agent_loop.run_long_run_continuation(
                            repo,
                            max_hops=bad,
                            capture_evidence=False,
                            invoke_codex_adapter=False,
                            invoke_claude_adapter=False,
                        )
                    self.assertEqual(
                        ctx.exception.status, "halted_input_missing",
                    )


class LongRunOutputBoundaryTests(unittest.TestCase):

    def _common_setup(self, td: Path) -> Path:
        repo = _make_repo(td)
        _plant_loop_state(repo)
        _plant_canonical_artifacts(repo)
        _plant_phase_9c_handoff(repo)
        _plant_review(repo, "APPROVED_FOR_HUMAN_REVIEW")
        return repo

    def test_refuses_outside_agent_loop(self) -> None:
        with TemporaryDirectory() as td:
            repo = self._common_setup(Path(td))
            with self.assertRaises(HaltError) as ctx:
                agent_loop.run_long_run_continuation(
                    repo,
                    output_path=repo / "outside.json",
                    capture_evidence=False,
                    invoke_codex_adapter=False,
                    invoke_claude_adapter=False,
                )
            self.assertEqual(ctx.exception.status, "halted_input_missing")

    def test_refuses_overwriting_review_fix_loop_descriptor(self) -> None:
        with TemporaryDirectory() as td:
            repo = self._common_setup(Path(td))
            with self.assertRaises(HaltError) as ctx:
                agent_loop.run_long_run_continuation(
                    repo,
                    output_path=(
                        repo / ".agent-loop" / "review-fix-loop.json"
                    ),
                    capture_evidence=False,
                    invoke_codex_adapter=False,
                    invoke_claude_adapter=False,
                )
            self.assertEqual(ctx.exception.status, "halted_input_missing")

    def test_refuses_overwriting_handoff_descriptor(self) -> None:
        with TemporaryDirectory() as td:
            repo = self._common_setup(Path(td))
            with self.assertRaises(HaltError) as ctx:
                agent_loop.run_long_run_continuation(
                    repo,
                    output_path=(
                        repo / ".agent-loop" / "prompt-handoff.json"
                    ),
                    capture_evidence=False,
                    invoke_codex_adapter=False,
                    invoke_claude_adapter=False,
                )
            self.assertEqual(ctx.exception.status, "halted_input_missing")

    def test_refuses_overwriting_intake_descriptor(self) -> None:
        with TemporaryDirectory() as td:
            repo = self._common_setup(Path(td))
            with self.assertRaises(HaltError) as ctx:
                agent_loop.run_long_run_continuation(
                    repo,
                    output_path=(
                        repo / ".agent-loop" / "prd-intake.json"
                    ),
                    capture_evidence=False,
                    invoke_codex_adapter=False,
                    invoke_claude_adapter=False,
                )
            self.assertEqual(ctx.exception.status, "halted_input_missing")

    def test_refuses_memory_subtree(self) -> None:
        with TemporaryDirectory() as td:
            repo = self._common_setup(Path(td))
            with self.assertRaises(HaltError) as ctx:
                agent_loop.run_long_run_continuation(
                    repo,
                    output_path=(
                        repo / ".agent-loop" / "memory" / "x.json"
                    ),
                    capture_evidence=False,
                    invoke_codex_adapter=False,
                    invoke_claude_adapter=False,
                )
            self.assertEqual(ctx.exception.status, "halted_input_missing")

    def test_safe_override_succeeds(self) -> None:
        with TemporaryDirectory() as td:
            repo = self._common_setup(Path(td))
            written = agent_loop.run_long_run_continuation(
                repo,
                output_path=(
                    repo / ".agent-loop" / "custom-long-run.json"
                ),
                capture_evidence=False,
                invoke_codex_adapter=False,
                invoke_claude_adapter=False,
            )
            self.assertTrue(written.is_file())
            self.assertEqual(written.name, "custom-long-run.json")


class LongRunCompletionDetectionTests(unittest.TestCase):
    """The loop stops at the first canonical completion signal -
    either at hop entry (already terminal) or after the Phase 9D
    hop transitions loop-state into a terminal state.
    """

    def test_pre_hop_terminal_state_does_no_phase_9d_work(self) -> None:
        # If loop-state is ALREADY at phase_complete_awaiting_human_approval
        # the loop should not even invoke Phase 9D once - it should
        # capture the no-op hop and stop.
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(
                repo,
                status="phase_complete_awaiting_human_approval",
                last_verdict="APPROVED_FOR_HUMAN_REVIEW",
            )
            # No canonical artifacts / handoff needed: Phase 9D is
            # never invoked.
            written = agent_loop.run_long_run_continuation(
                repo,
                capture_evidence=False,
                invoke_codex_adapter=False,
                invoke_claude_adapter=False,
            )
            payload = json.loads(written.read_text(encoding="utf-8"))
            self.assertEqual(payload["hops_run"], 1)
            self.assertEqual(payload["hops"][0]["action_taken"],
                             "noop_already_complete")
            self.assertEqual(
                payload["completion"]["completion_signal"],
                "completion_approved",
            )

    def test_approved_hop_stops_loop(self) -> None:
        # Hop 0: Phase 9D returns APPROVED. Loop stops at the
        # post-hop completion check; no hop 1 runs.
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo, cycle_count=0, max_cycles=3)
            _plant_canonical_artifacts(repo)
            _plant_phase_9c_handoff(repo)
            _plant_review(repo, "APPROVED_FOR_HUMAN_REVIEW")
            written = agent_loop.run_long_run_continuation(
                repo,
                max_hops=3,
                capture_evidence=False,
                invoke_codex_adapter=False,
                invoke_claude_adapter=False,
            )
            payload = json.loads(written.read_text(encoding="utf-8"))
            self.assertEqual(payload["hops_run"], 1)
            self.assertEqual(
                payload["completion"]["completion_signal"],
                "completion_approved",
            )

    def test_failed_hop_stops_loop_without_propagating(self) -> None:
        # Phase 9D on FAILED_REQUIRES_HUMAN raises HaltError. Phase
        # 9E catches it, records the halt_status, and stops without
        # propagating.
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo, cycle_count=0, max_cycles=3)
            _plant_canonical_artifacts(repo)
            _plant_phase_9c_handoff(repo)
            _plant_review(repo, "FAILED_REQUIRES_HUMAN")
            written = agent_loop.run_long_run_continuation(
                repo,
                max_hops=3,
                capture_evidence=False,
                invoke_codex_adapter=False,
                invoke_claude_adapter=False,
            )
            payload = json.loads(written.read_text(encoding="utf-8"))
            self.assertEqual(payload["hops_run"], 1)
            self.assertEqual(
                payload["hops"][0]["halt_status"],
                "halted_failed_requires_human",
            )
            # Post-hop evaluate_phase_completion sees the unchanged
            # loop-state (Phase 9D's HaltError did not update status),
            # so the completion signal at this point reflects whatever
            # loop-state actually shows. The slice's contract is to
            # CAPTURE the halt; the operator inspects the descriptor.
            self.assertIsNotNone(
                payload["hops"][0]["halt_status"],
            )

    def test_max_hops_exhausted_without_completion(self) -> None:
        # Cycler always returns NEEDS_FIXES. Phase 9D iterates once
        # per hop (max_inner_cycles=1) and dispatches a fix. After
        # max_hops, the loop stops without a completion signal.
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo, cycle_count=0, max_cycles=8)
            _plant_canonical_artifacts(repo)
            _plant_phase_9c_handoff(repo)

            class AlwaysNeedsFixes:
                def __init__(self_):
                    self_.calls = 0
                def wait_for_review(self_, review_path: Path):
                    self_.calls += 1
                    review_path.write_text(
                        _review_md(
                            "NEEDS_FIXES",
                            issues=(_claude_owned_issue_block(),),
                        ),
                        encoding="utf-8",
                    )
                    return agent_loop.ExecutionResult(
                        exit_code=0,
                        model_id="codex-test",
                        duration_seconds=0.0,
                    )

            class ClaudeSpy:
                def __init__(self_):
                    self_.calls = 0
                def invoke(self_, prompt_path: Path, summary_path: Path):
                    self_.calls += 1
                    return agent_loop.ExecutionResult(
                        exit_code=0,
                        model_id="claude-test",
                        duration_seconds=0.0,
                    )

            cycler = AlwaysNeedsFixes()
            claude = ClaudeSpy()
            with mock.patch.object(
                agent_loop, "make_codex_adapter",
                return_value=cycler,
            ), mock.patch.object(
                agent_loop, "make_claude_adapter",
                return_value=claude,
            ):
                written = agent_loop.run_long_run_continuation(
                    repo,
                    max_hops=2,
                    capture_evidence=False,
                    invoke_codex_adapter=True,
                    invoke_claude_adapter=True,
                )
            payload = json.loads(written.read_text(encoding="utf-8"))
            self.assertEqual(payload["hops_run"], 2)
            self.assertIsNone(
                payload["completion"]["completion_signal"],
                "with NEEDS_FIXES on every review, the loop must "
                "exhaust max_hops without a completion signal",
            )
            self.assertGreaterEqual(cycler.calls, 2)


class LongRunMultiHopAdapterSeamTests(unittest.TestCase):
    """When invoking real adapter seams, each Phase 9D hop should
    call them; on transition from NEEDS_FIXES to APPROVED across
    two hops, the loop stops after the second hop.
    """

    def test_needs_fixes_then_approved_across_two_hops(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo, cycle_count=0, max_cycles=8)
            _plant_canonical_artifacts(repo)
            _plant_phase_9c_handoff(repo)

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

            class ClaudeSpy:
                def __init__(self_):
                    self_.calls = 0
                def invoke(self_, prompt_path: Path, summary_path: Path):
                    self_.calls += 1
                    return agent_loop.ExecutionResult(
                        exit_code=0,
                        model_id="claude-test",
                        duration_seconds=0.0,
                    )

            cycler = Cycler()
            claude = ClaudeSpy()
            with mock.patch.object(
                agent_loop, "make_codex_adapter",
                return_value=cycler,
            ), mock.patch.object(
                agent_loop, "make_claude_adapter",
                return_value=claude,
            ):
                written = agent_loop.run_long_run_continuation(
                    repo,
                    max_hops=3,
                    capture_evidence=False,
                    invoke_codex_adapter=True,
                    invoke_claude_adapter=True,
                )
            payload = json.loads(written.read_text(encoding="utf-8"))
            self.assertEqual(
                payload["completion"]["completion_signal"],
                "completion_approved",
            )
            self.assertEqual(payload["hops_run"], 2)
            self.assertEqual(cycler.calls, 2)


class LongRunDescriptorTests(unittest.TestCase):

    def test_descriptor_carries_full_metadata(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(
                repo,
                status="phase_complete_awaiting_human_approval",
                last_verdict="APPROVED_FOR_HUMAN_REVIEW",
            )
            written = agent_loop.run_long_run_continuation(
                repo,
                capture_evidence=False,
                invoke_codex_adapter=False,
                invoke_claude_adapter=False,
            )
            payload = json.loads(written.read_text(encoding="utf-8"))
            self.assertEqual(payload["signal_version"], "phase-9e-v1")
            self.assertEqual(payload["phase"], ACTIVE_PHASE)
            self.assertEqual(payload["sub_phase"], ACTIVE_SUB_PHASE)
            self.assertTrue(payload["advisory_only"])
            self.assertIn(
                "canonical_precedence_note", payload,
            )
            self.assertIn(
                "Phase 9E", payload["canonical_precedence_note"],
            )

    def test_descriptor_records_iteration_max_hops(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            _plant_canonical_artifacts(repo)
            _plant_phase_9c_handoff(repo)
            _plant_review(repo, "APPROVED_FOR_HUMAN_REVIEW")
            written = agent_loop.run_long_run_continuation(
                repo,
                max_hops=5,
                capture_evidence=False,
                invoke_codex_adapter=False,
                invoke_claude_adapter=False,
            )
            payload = json.loads(written.read_text(encoding="utf-8"))
            self.assertEqual(payload["max_hops"], 5)


class LongRunAuditLogTests(unittest.TestCase):

    def test_audit_log_lines(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(
                repo,
                status="phase_complete_awaiting_human_approval",
                last_verdict="APPROVED_FOR_HUMAN_REVIEW",
            )
            log = repo / ".agent-loop" / "orchestrator.log"
            agent_loop.run_long_run_continuation(
                repo,
                capture_evidence=False,
                invoke_codex_adapter=False,
                invoke_claude_adapter=False,
                log_path=log,
            )
            audit = log.read_text(encoding="utf-8")
            self.assertIn("long-run continuation: started", audit)
            self.assertIn(
                "long-run continuation: completion_detected_at_entry",
                audit,
            )
            self.assertIn("long-run continuation: finished", audit)


class LongRunCliTests(unittest.TestCase):

    def setUp(self) -> None:
        self.td = TemporaryDirectory()
        self.repo = Path(self.td.name)
        _make_repo(self.repo)
        _plant_loop_state(
            self.repo,
            status="phase_complete_awaiting_human_approval",
            last_verdict="APPROVED_FOR_HUMAN_REVIEW",
        )
        import os
        self._prev_cwd = os.getcwd()
        os.chdir(self.repo)

    def tearDown(self) -> None:
        import os
        os.chdir(self._prev_cwd)
        self.td.cleanup()

    def test_cli_default_writes_descriptor(self) -> None:
        rc = agent_loop.main([
            "run-long-run-continuation",
            "--skip-evidence", "--no-invoke-codex",
            "--no-invoke-claude",
        ])
        self.assertEqual(rc, 0)
        out = self.repo / ".agent-loop" / "long-run-continuation.json"
        self.assertTrue(out.is_file())
        payload = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(
            payload["completion"]["completion_signal"],
            "completion_approved",
        )

    def test_cli_refuses_bad_output(self) -> None:
        rc = agent_loop.main([
            "run-long-run-continuation",
            "--output", ".agent-loop/review-fix-loop.json",
            "--skip-evidence", "--no-invoke-codex",
            "--no-invoke-claude",
        ])
        self.assertEqual(rc, 2)

    def test_cli_refuses_max_hops_out_of_bound(self) -> None:
        rc = agent_loop.main([
            "run-long-run-continuation",
            "--max-hops", "99",
            "--skip-evidence", "--no-invoke-codex",
            "--no-invoke-claude",
        ])
        self.assertEqual(rc, 2)


class LongRunHelpTextTests(unittest.TestCase):

    def _help_text(self) -> str:
        parser = agent_loop.build_parser()
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                for choice_action in action._choices_actions:
                    if (
                        choice_action.dest
                        == "run-long-run-continuation"
                    ):
                        return choice_action.help or ""
        self.fail("run-long-run-continuation subparser help not found")
        return ""

    def test_help_describes_phase_9e_role(self) -> None:
        text = self._help_text()
        self.assertIn("Phase 9E", text)
        self.assertIn("long-run continuation", text)

    def test_help_documents_dry_run_escape_hatches(self) -> None:
        text = self._help_text()
        self.assertIn("--skip-evidence", text)
        self.assertIn("--no-invoke-codex", text)
        self.assertIn("--no-invoke-claude", text)

    def test_help_documents_descriptor_path(self) -> None:
        text = self._help_text()
        self.assertIn(
            ".agent-loop/long-run-continuation.json", text,
        )


if __name__ == "__main__":
    unittest.main()
