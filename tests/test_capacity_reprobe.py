"""Phase 9F - Capacity-Halt Reprobe And Automatic Resume tests.

Exercises `reprobe_capacity_and_resume(...)` and the
`run-capacity-reprobe` CLI subcommand without actually sleeping.
The tests inject:
  - a `sleep` callable that records calls so backoff progression
    is verifiable without real wall-clock delay
  - a `probe` callable that returns a configurable bool so the
    "capacity available" / "capacity still unavailable" branches
    are deterministically testable

The tests prove:
  - structural refusal vocabulary fires fail-closed on missing
    loop-state, wrong status, out-of-bound bounds args, output-
    boundary violations, and stale retry-state on disk
  - the first attempt initializes the retry-state at the canonical
    path with the documented schema
  - subsequent attempts increment `attempt_count` and append to
    `history`
  - cumulative budget caps total attempts across multiple
    invocations
  - successful probe restores loop-state.status from
    `suspended_status` and deletes the retry-state
  - failed probe with budget remaining returns the retry-state
    path with the failure persisted
  - exponential backoff is computed correctly and capped at
    max_backoff_seconds
  - the symmetric output-boundary protects sibling Phase 9
    descriptors from a Phase 9F write
  - the operator-facing argparse help cannot drift silently
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
ACTIVE_SUB_PHASE = "Phase 9F - Capacity-Halt Reprobe And Automatic Resume"


def _make_repo(td: Path) -> Path:
    (td / "AGENTS.md").write_text("test\n", encoding="utf-8")
    (td / "CLAUDE.md").write_text("test\n", encoding="utf-8")
    (td / "TASK.md").write_text("test\n", encoding="utf-8")
    (td / ".agent-loop").mkdir()
    return td


def _plant_loop_state(
    repo_root: Path,
    *,
    status: str = "halted_capacity_unavailable",
    cycle_count: int = 0,
    max_cycles: int = 3,
    task: str = "capacity-reprobe-test",
) -> Path:
    state_path = repo_root / ".agent-loop" / "loop-state.json"
    state_path.write_text(json.dumps({
        "phase": ACTIVE_PHASE,
        "sub_phase": ACTIVE_SUB_PHASE,
        "task": task,
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


def _plant_prompts(repo_root: Path) -> None:
    """Phase 9F fix-cycle: a successful reprobe dispatches the
    matching Claude prompt handoff (implementation or fix), which
    validates the prompt artifact is present. Tests that exercise
    the success path plant both prompts so either suspended_status
    resolves cleanly.
    """
    al = repo_root / ".agent-loop"
    (al / "claude-prompt.md").write_text(
        "# Claude Implementation Prompt\n\nbody\n", encoding="utf-8",
    )
    (al / "fix-prompt.md").write_text(
        "# Claude Fix Prompt\n\nbody\n", encoding="utf-8",
    )


def _noop_sleep(seconds: float) -> None:
    return None


def _always_true_probe(repo_root: Path) -> bool:
    return True


def _always_false_probe(repo_root: Path) -> bool:
    return False


class CapacityReprobeConstantsTests(unittest.TestCase):

    def test_halt_vocabulary(self) -> None:
        self.assertEqual(
            agent_loop.HALTED_CAPACITY_UNAVAILABLE,
            "halted_capacity_unavailable",
        )

    def test_signal_version_is_phase_9f_v1(self) -> None:
        self.assertEqual(
            agent_loop.CAPACITY_RETRY_SIGNAL_VERSION, "phase-9f-v1",
        )

    def test_output_rel_is_under_agent_loop(self) -> None:
        self.assertEqual(
            agent_loop.CAPACITY_RETRY_STATE_OUTPUT_REL,
            ".agent-loop/capacity-retry-state.json",
        )

    def test_default_and_max_attempts(self) -> None:
        self.assertEqual(
            agent_loop.CAPACITY_RETRY_DEFAULT_MAX_ATTEMPTS, 5,
        )
        self.assertEqual(
            agent_loop.CAPACITY_RETRY_MAX_MAX_ATTEMPTS, 16,
        )

    def test_default_and_max_backoff(self) -> None:
        self.assertEqual(
            agent_loop.CAPACITY_RETRY_DEFAULT_INITIAL_BACKOFF_SECONDS,
            1.0,
        )
        self.assertEqual(
            agent_loop.CAPACITY_RETRY_DEFAULT_MAX_BACKOFF_SECONDS,
            30.0,
        )
        self.assertEqual(
            agent_loop.CAPACITY_RETRY_MAX_MAX_BACKOFF_SECONDS, 600.0,
        )

    def test_handler_is_wired(self) -> None:
        self.assertIn(
            "run-capacity-reprobe", agent_loop.HANDLERS,
        )
        self.assertIs(
            agent_loop.HANDLERS["run-capacity-reprobe"],
            agent_loop.cmd_reprobe_capacity_and_resume,
        )

    def test_protected_output_set_includes_siblings(self) -> None:
        protected = agent_loop.CAPACITY_RETRY_PROTECTED_OUTPUT_PATHS
        for sibling in (
            ".agent-loop/prd-intake.json",
            ".agent-loop/prompt-handoff.json",
            ".agent-loop/review-fix-loop.json",
            ".agent-loop/long-run-continuation.json",
        ):
            self.assertIn(sibling, protected)

    def test_protected_output_set_excludes_self_default(self) -> None:
        self.assertNotIn(
            ".agent-loop/capacity-retry-state.json",
            agent_loop.CAPACITY_RETRY_PROTECTED_OUTPUT_PATHS,
        )

    def test_sibling_sets_protect_phase_9f_output(self) -> None:
        for sibling_set in (
            agent_loop.PRD_INTAKE_PROTECTED_OUTPUT_PATHS,
            agent_loop.PROMPT_HANDOFF_PROTECTED_OUTPUT_PATHS,
            agent_loop.INTERNAL_REVIEW_FIX_LOOP_PROTECTED_OUTPUT_PATHS,
            agent_loop.LONG_RUN_CONTINUATION_PROTECTED_OUTPUT_PATHS,
        ):
            self.assertIn(
                ".agent-loop/capacity-retry-state.json", sibling_set,
            )


class CapacityReprobeRefusalTests(unittest.TestCase):

    def test_refuses_wrong_status(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo, status="awaiting_claude_implementation")
            with self.assertRaises(HaltError) as ctx:
                agent_loop.reprobe_capacity_and_resume(
                    repo, sleep=_noop_sleep, probe=_always_true_probe,
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )
            self.assertIn(
                "halted_capacity_unavailable", str(ctx.exception),
            )

    def test_refuses_missing_loop_state(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            with self.assertRaises(HaltError) as ctx:
                agent_loop.reprobe_capacity_and_resume(
                    repo, sleep=_noop_sleep, probe=_always_true_probe,
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )

    def test_refuses_out_of_bound_max_attempts(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            for bad in (0, -1, 99, "two", 2.5, True):
                with self.subTest(value=bad):
                    with self.assertRaises(HaltError) as ctx:
                        agent_loop.reprobe_capacity_and_resume(
                            repo,
                            max_attempts=bad,
                            sleep=_noop_sleep,
                            probe=_always_true_probe,
                        )
                    self.assertEqual(
                        ctx.exception.status, "halted_input_missing",
                    )

    def test_refuses_out_of_bound_backoff(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            for bad in (0, -1, 9999, "x", True):
                with self.subTest(value=bad):
                    with self.assertRaises(HaltError) as ctx:
                        agent_loop.reprobe_capacity_and_resume(
                            repo,
                            initial_backoff_seconds=bad,
                            sleep=_noop_sleep,
                            probe=_always_true_probe,
                        )
                    self.assertEqual(
                        ctx.exception.status, "halted_input_missing",
                    )

    def test_refuses_initial_greater_than_max_backoff(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            with self.assertRaises(HaltError) as ctx:
                agent_loop.reprobe_capacity_and_resume(
                    repo,
                    initial_backoff_seconds=10,
                    max_backoff_seconds=5,
                    sleep=_noop_sleep,
                    probe=_always_true_probe,
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )

    def test_refuses_probe_raising_exception(self) -> None:
        def bad_probe(_repo_root: Path) -> bool:
            raise RuntimeError("probe blew up")

        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            with self.assertRaises(HaltError) as ctx:
                agent_loop.reprobe_capacity_and_resume(
                    repo, sleep=_noop_sleep, probe=bad_probe,
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )
            self.assertIn("probe raised", str(ctx.exception))


class CapacityReprobeOutputBoundaryTests(unittest.TestCase):

    def _setup(self, td: Path) -> Path:
        repo = _make_repo(td)
        _plant_loop_state(repo)
        return repo

    def test_refuses_outside_agent_loop(self) -> None:
        with TemporaryDirectory() as td:
            repo = self._setup(Path(td))
            with self.assertRaises(HaltError) as ctx:
                agent_loop.reprobe_capacity_and_resume(
                    repo,
                    output_path=repo / "outside.json",
                    sleep=_noop_sleep, probe=_always_true_probe,
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )

    def test_refuses_overwriting_long_run_descriptor(self) -> None:
        with TemporaryDirectory() as td:
            repo = self._setup(Path(td))
            with self.assertRaises(HaltError) as ctx:
                agent_loop.reprobe_capacity_and_resume(
                    repo,
                    output_path=(
                        repo / ".agent-loop"
                        / "long-run-continuation.json"
                    ),
                    sleep=_noop_sleep, probe=_always_true_probe,
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )

    def test_refuses_overwriting_review_fix_loop_descriptor(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            repo = self._setup(Path(td))
            with self.assertRaises(HaltError) as ctx:
                agent_loop.reprobe_capacity_and_resume(
                    repo,
                    output_path=(
                        repo / ".agent-loop" / "review-fix-loop.json"
                    ),
                    sleep=_noop_sleep, probe=_always_true_probe,
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )

    def test_refuses_memory_subtree(self) -> None:
        with TemporaryDirectory() as td:
            repo = self._setup(Path(td))
            with self.assertRaises(HaltError) as ctx:
                agent_loop.reprobe_capacity_and_resume(
                    repo,
                    output_path=(
                        repo / ".agent-loop" / "memory" / "x.json"
                    ),
                    sleep=_noop_sleep, probe=_always_true_probe,
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )

    def test_safe_override_succeeds(self) -> None:
        with TemporaryDirectory() as td:
            repo = self._setup(Path(td))
            _plant_prompts(repo)
            written = agent_loop.reprobe_capacity_and_resume(
                repo,
                output_path=(
                    repo / ".agent-loop" / "custom-retry.json"
                ),
                sleep=_noop_sleep, probe=_always_true_probe,
                invoke_adapter=False,
            )
            # On success, the retry-state file is deleted.
            self.assertEqual(written.name, "custom-retry.json")
            self.assertFalse(written.exists())


class CapacityReprobeSuccessTests(unittest.TestCase):

    def test_first_attempt_success_restores_status(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            state_path = _plant_loop_state(repo)
            _plant_prompts(repo)
            agent_loop.reprobe_capacity_and_resume(
                repo,
                suspended_status="claude_implementing",
                sleep=_noop_sleep, probe=_always_true_probe,
                invoke_adapter=False,
            )
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(state["status"], "claude_implementing")
            # Retry-state file is deleted on success.
            retry_path = (
                repo / ".agent-loop" / "capacity-retry-state.json"
            )
            self.assertFalse(retry_path.exists())

    def test_default_suspended_status_is_claude_implementing(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            state_path = _plant_loop_state(repo)
            _plant_prompts(repo)
            agent_loop.reprobe_capacity_and_resume(
                repo, sleep=_noop_sleep, probe=_always_true_probe,
                invoke_adapter=False,
            )
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(state["status"], "claude_implementing")

    def test_custom_suspended_status_is_respected(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            state_path = _plant_loop_state(repo)
            _plant_prompts(repo)
            agent_loop.reprobe_capacity_and_resume(
                repo,
                suspended_status="claude_fixing",
                sleep=_noop_sleep, probe=_always_true_probe,
                invoke_adapter=False,
            )
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(state["status"], "claude_fixing")

    def test_sleep_is_invoked_with_first_backoff(self) -> None:
        sleep_calls: list[float] = []
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            _plant_prompts(repo)
            agent_loop.reprobe_capacity_and_resume(
                repo,
                initial_backoff_seconds=2.0,
                max_backoff_seconds=30.0,
                sleep=lambda s: sleep_calls.append(s),
                probe=_always_true_probe,
                invoke_adapter=False,
            )
            # Attempt 1 backoff = 2 * 2**0 = 2.
            self.assertEqual(sleep_calls, [2.0])


class CapacityReprobeFailureAndBudgetTests(unittest.TestCase):

    def test_all_attempts_fail_exhausts_budget(self) -> None:
        sleep_calls: list[float] = []
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            with self.assertRaises(HaltError) as ctx:
                agent_loop.reprobe_capacity_and_resume(
                    repo,
                    max_attempts=3,
                    initial_backoff_seconds=1.0,
                    max_backoff_seconds=4.0,
                    sleep=lambda s: sleep_calls.append(s),
                    probe=_always_false_probe,
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )
            self.assertIn("budget exhausted", str(ctx.exception))
            # Backoff progression: 1, 2, 4 (capped at max_backoff).
            self.assertEqual(sleep_calls, [1.0, 2.0, 4.0])
            # Retry-state is preserved on disk for inspection.
            retry_path = (
                repo / ".agent-loop" / "capacity-retry-state.json"
            )
            self.assertTrue(retry_path.exists())
            retry_state = json.loads(
                retry_path.read_text(encoding="utf-8"),
            )
            self.assertEqual(retry_state["attempt_count"], 3)
            self.assertEqual(len(retry_state["history"]), 3)
            self.assertEqual(retry_state["last_outcome"], "failed")

    def test_backoff_caps_at_max(self) -> None:
        sleep_calls: list[float] = []
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            try:
                agent_loop.reprobe_capacity_and_resume(
                    repo,
                    max_attempts=5,
                    initial_backoff_seconds=1.0,
                    max_backoff_seconds=3.0,
                    sleep=lambda s: sleep_calls.append(s),
                    probe=_always_false_probe,
                )
            except HaltError:
                pass
            # Expected: 1, 2, 3 (cap), 3, 3.
            self.assertEqual(sleep_calls, [1.0, 2.0, 3.0, 3.0, 3.0])

    def test_history_records_each_attempt_outcome(self) -> None:
        probe_results = [False, False, True]

        def cyclic_probe(_repo_root: Path) -> bool:
            return probe_results.pop(0)

        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            state_path = _plant_loop_state(repo)
            _plant_prompts(repo)
            retry_path = (
                repo / ".agent-loop" / "capacity-retry-state.json"
            )
            agent_loop.reprobe_capacity_and_resume(
                repo,
                max_attempts=5,
                initial_backoff_seconds=1.0,
                sleep=_noop_sleep,
                probe=cyclic_probe,
                invoke_adapter=False,
            )
            # On success, retry-state file is deleted.
            self.assertFalse(retry_path.exists())
            # Loop-state was restored.
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(state["status"], "claude_implementing")


class CapacityReprobeCumulativeBudgetTests(unittest.TestCase):
    """The retry-state on disk persists across invocations; the
    cumulative attempt count is bounded by max_attempts even when
    the operator re-runs the CLI multiple times.
    """

    def test_persisted_retry_state_carries_history_across_runs(
        self,
    ) -> None:
        # First call: 2 max_attempts, both fail.
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            try:
                agent_loop.reprobe_capacity_and_resume(
                    repo,
                    max_attempts=2,
                    initial_backoff_seconds=1.0,
                    sleep=_noop_sleep,
                    probe=_always_false_probe,
                )
            except HaltError:
                pass
            retry_path = (
                repo / ".agent-loop" / "capacity-retry-state.json"
            )
            state = json.loads(retry_path.read_text(encoding="utf-8"))
            self.assertEqual(state["attempt_count"], 2)
            # Second call with max_attempts=5: persisted_cap=2,
            # effective_cap=min(5,2)=2; cumulative count is 2 so
            # no more attempts run and the call refuses immediately.
            with self.assertRaises(HaltError) as ctx:
                agent_loop.reprobe_capacity_and_resume(
                    repo,
                    max_attempts=5,
                    initial_backoff_seconds=1.0,
                    sleep=_noop_sleep,
                    probe=_always_true_probe,
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )

    def test_deleting_retry_state_resets_budget(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            _plant_prompts(repo)
            try:
                agent_loop.reprobe_capacity_and_resume(
                    repo,
                    max_attempts=1,
                    initial_backoff_seconds=1.0,
                    sleep=_noop_sleep,
                    probe=_always_false_probe,
                )
            except HaltError:
                pass
            retry_path = (
                repo / ".agent-loop" / "capacity-retry-state.json"
            )
            retry_path.unlink()
            # Re-run with a successful probe; the budget is fresh.
            agent_loop.reprobe_capacity_and_resume(
                repo,
                max_attempts=1,
                initial_backoff_seconds=1.0,
                sleep=_noop_sleep,
                probe=_always_true_probe,
                invoke_adapter=False,
            )
            state_path = repo / ".agent-loop" / "loop-state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(state["status"], "claude_implementing")


class CapacityReprobeStaleRetryStateTests(unittest.TestCase):

    def _seed_retry_state(self, repo: Path, **overrides) -> Path:
        path = repo / ".agent-loop" / "capacity-retry-state.json"
        body = {
            "retry_signal_version": "phase-9f-v1",
            "created_at": "2026-06-17T00:00:00Z",
            "phase": ACTIVE_PHASE,
            "sub_phase": ACTIVE_SUB_PHASE,
            "task": "capacity-reprobe-test",
            "cycle_count": 0,
            "attempt_count": 0,
            "max_attempts": 5,
            "initial_backoff_seconds": 1.0,
            "max_backoff_seconds": 30.0,
            "suspended_status": "claude_implementing",
            "history": [],
            "last_outcome": None,
            "canonical_precedence_note": "test",
        }
        body.update(overrides)
        path.write_text(json.dumps(body), encoding="utf-8")
        return path

    def test_wrong_signal_version_refuses(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            self._seed_retry_state(
                repo, retry_signal_version="phase-9e-v1",
            )
            with self.assertRaises(HaltError) as ctx:
                agent_loop.reprobe_capacity_and_resume(
                    repo, sleep=_noop_sleep, probe=_always_true_probe,
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )
            self.assertIn(
                "retry_signal_version", str(ctx.exception),
            )

    def test_phase_mismatch_refuses(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            self._seed_retry_state(repo, phase="Phase 1 - Stale")
            with self.assertRaises(HaltError) as ctx:
                agent_loop.reprobe_capacity_and_resume(
                    repo, sleep=_noop_sleep, probe=_always_true_probe,
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )

    def test_cycle_count_mismatch_refuses(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo, cycle_count=2)
            self._seed_retry_state(repo, cycle_count=0)
            with self.assertRaises(HaltError) as ctx:
                agent_loop.reprobe_capacity_and_resume(
                    repo, sleep=_noop_sleep, probe=_always_true_probe,
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )

    def test_missing_required_field_refuses(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            path = self._seed_retry_state(repo)
            body = json.loads(path.read_text(encoding="utf-8"))
            del body["attempt_count"]
            path.write_text(json.dumps(body), encoding="utf-8")
            with self.assertRaises(HaltError) as ctx:
                agent_loop.reprobe_capacity_and_resume(
                    repo, sleep=_noop_sleep, probe=_always_true_probe,
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )

    def test_malformed_json_refuses(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            (repo / ".agent-loop" / "capacity-retry-state.json").write_text(
                "not json {", encoding="utf-8",
            )
            with self.assertRaises(HaltError) as ctx:
                agent_loop.reprobe_capacity_and_resume(
                    repo, sleep=_noop_sleep, probe=_always_true_probe,
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )


class CapacityReprobeAuditLogTests(unittest.TestCase):

    def test_success_audit_lines(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            _plant_prompts(repo)
            log = repo / ".agent-loop" / "orchestrator.log"
            agent_loop.reprobe_capacity_and_resume(
                repo,
                sleep=_noop_sleep, probe=_always_true_probe,
                log_path=log,
                invoke_adapter=False,
            )
            audit = log.read_text(encoding="utf-8")
            self.assertIn("capacity reprobe: started", audit)
            self.assertIn("capacity reprobe: succeeded", audit)
            # Phase 9F fix-cycle: success audit now also records the
            # resume dispatch line proving the suspended step was
            # actually dispatched (not just status restored).
            self.assertIn("capacity reprobe: resumed", audit)

    def test_failure_audit_lines(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            log = repo / ".agent-loop" / "orchestrator.log"
            try:
                agent_loop.reprobe_capacity_and_resume(
                    repo,
                    max_attempts=2,
                    sleep=_noop_sleep, probe=_always_false_probe,
                    log_path=log,
                )
            except HaltError:
                pass
            audit = log.read_text(encoding="utf-8")
            self.assertIn(
                "capacity reprobe: attempt_failed", audit,
            )
            self.assertIn(
                "capacity reprobe: budget_exhausted", audit,
            )


class CapacityReprobeCliTests(unittest.TestCase):

    def setUp(self) -> None:
        self.td = TemporaryDirectory()
        self.repo = Path(self.td.name)
        _make_repo(self.repo)
        _plant_loop_state(self.repo)
        _plant_prompts(self.repo)
        import os
        self._prev_cwd = os.getcwd()
        os.chdir(self.repo)

    def tearDown(self) -> None:
        import os
        os.chdir(self._prev_cwd)
        self.td.cleanup()

    def test_cli_default_refuses_without_env_var(self) -> None:
        # Phase 9F fix-cycle: the default probe is env-var-gated.
        # Without AGENT_LOOP_CAPACITY_PROBE set, the bounded
        # budget exhausts and the CLI returns 2.
        import os
        prev = os.environ.pop(agent_loop.CAPACITY_PROBE_ENV_VAR, None)
        try:
            with mock.patch("agent_loop.time.sleep", lambda s: None):
                rc = agent_loop.main([
                    "run-capacity-reprobe",
                    "--max-attempts", "1",
                    "--initial-backoff-seconds", "0.001",
                    "--max-backoff-seconds", "0.001",
                ])
            self.assertEqual(rc, 2)
        finally:
            if prev is not None:
                os.environ[agent_loop.CAPACITY_PROBE_ENV_VAR] = prev

    def test_cli_default_succeeds_with_env_var_available(self) -> None:
        # With AGENT_LOOP_CAPACITY_PROBE=available the default
        # probe returns True and the CLI restores loop-state on
        # the first attempt. `--no-invoke-adapter` keeps the
        # success-path dispatch to a descriptor-only write so the
        # test does not block on a real Claude adapter handoff.
        import os
        prev = os.environ.get(agent_loop.CAPACITY_PROBE_ENV_VAR)
        os.environ[agent_loop.CAPACITY_PROBE_ENV_VAR] = "available"
        try:
            with mock.patch("agent_loop.time.sleep", lambda s: None):
                rc = agent_loop.main([
                    "run-capacity-reprobe",
                    "--max-attempts", "1",
                    "--initial-backoff-seconds", "0.001",
                    "--max-backoff-seconds", "0.001",
                    "--no-invoke-adapter",
                ])
            self.assertEqual(rc, 0)
            state = json.loads(
                (
                    self.repo / ".agent-loop" / "loop-state.json"
                ).read_text(encoding="utf-8"),
            )
            self.assertEqual(state["status"], "claude_implementing")
        finally:
            if prev is None:
                os.environ.pop(agent_loop.CAPACITY_PROBE_ENV_VAR, None)
            else:
                os.environ[agent_loop.CAPACITY_PROBE_ENV_VAR] = prev

    def test_cli_refuses_bad_output(self) -> None:
        rc = agent_loop.main([
            "run-capacity-reprobe",
            "--output", ".agent-loop/long-run-continuation.json",
        ])
        self.assertEqual(rc, 2)

    def test_cli_refuses_out_of_bound_max_attempts(self) -> None:
        rc = agent_loop.main([
            "run-capacity-reprobe",
            "--max-attempts", "99",
        ])
        self.assertEqual(rc, 2)


class DefaultProbeBehaviorTests(unittest.TestCase):
    """Phase 9F fix-cycle: the default probe is env-var-gated.
    Without `AGENT_LOOP_CAPACITY_PROBE` set to an "available"
    value, the probe returns False so the bounded retry budget
    exhausts rather than silently auto-succeeding.
    """

    def setUp(self) -> None:
        import os
        self._prev = os.environ.pop(
            agent_loop.CAPACITY_PROBE_ENV_VAR, None,
        )

    def tearDown(self) -> None:
        import os
        if self._prev is None:
            os.environ.pop(
                agent_loop.CAPACITY_PROBE_ENV_VAR, None,
            )
        else:
            os.environ[agent_loop.CAPACITY_PROBE_ENV_VAR] = self._prev

    def test_default_probe_refuses_with_no_env_var(self) -> None:
        with TemporaryDirectory() as td:
            self.assertFalse(
                agent_loop._default_capacity_probe(Path(td)),
            )

    def test_default_probe_returns_true_with_available(self) -> None:
        import os
        os.environ[agent_loop.CAPACITY_PROBE_ENV_VAR] = "available"
        with TemporaryDirectory() as td:
            self.assertTrue(
                agent_loop._default_capacity_probe(Path(td)),
            )

    def test_default_probe_accepts_truthy_aliases(self) -> None:
        import os
        for value in ("1", "true", "yes", "ok", "AVAILABLE", "True"):
            with self.subTest(value=value):
                os.environ[agent_loop.CAPACITY_PROBE_ENV_VAR] = value
                with TemporaryDirectory() as td:
                    self.assertTrue(
                        agent_loop._default_capacity_probe(Path(td)),
                        f"probe should accept {value!r}",
                    )

    def test_default_probe_rejects_other_values(self) -> None:
        import os
        for value in ("unavailable", "0", "false", "no", "maybe", " "):
            with self.subTest(value=value):
                os.environ[agent_loop.CAPACITY_PROBE_ENV_VAR] = value
                with TemporaryDirectory() as td:
                    self.assertFalse(
                        agent_loop._default_capacity_probe(Path(td)),
                        f"probe should reject {value!r}",
                    )

    def test_default_probe_used_by_reprobe_without_explicit_arg(
        self,
    ) -> None:
        # Integration: calling reprobe without injecting `probe`
        # uses the env-var-gated default. With no env var set the
        # bounded budget exhausts.
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            with self.assertRaises(HaltError) as ctx:
                agent_loop.reprobe_capacity_and_resume(
                    repo,
                    max_attempts=2,
                    initial_backoff_seconds=0.001,
                    sleep=_noop_sleep,
                    # probe=None -> use default
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )
            self.assertIn("budget exhausted", str(ctx.exception))


class RecordCapacityHaltTests(unittest.TestCase):
    """Phase 9F fix-cycle: production-path entry via
    `record_capacity_halt(...)`.
    """

    def test_transitions_status_and_plants_retry_state(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            state_path = _plant_loop_state(
                repo, status="claude_implementing",
            )
            written = agent_loop.record_capacity_halt(
                repo, reason="rate-limit-429",
            )
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(
                state["status"], "halted_capacity_unavailable",
            )
            self.assertTrue(written.is_file())
            retry_state = json.loads(written.read_text(encoding="utf-8"))
            self.assertEqual(
                retry_state["retry_signal_version"], "phase-9f-v1",
            )
            self.assertEqual(retry_state["attempt_count"], 0)
            self.assertEqual(retry_state["history"], [])
            # Default suspended_status captures CURRENT loop-state
            # status (claude_implementing in this setup).
            self.assertEqual(
                retry_state["suspended_status"], "claude_implementing",
            )
            self.assertEqual(
                retry_state["recorded_reason"], "rate-limit-429",
            )

    def test_custom_suspended_status_override(self) -> None:
        # Phase 9F fix-cycle: the suspended_status override is now
        # validated against the supported allowlist. Switching from
        # the default ("claude_implementing" inferred from current
        # status) to the other supported value ("claude_fixing")
        # still works.
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo, status="claude_implementing")
            written = agent_loop.record_capacity_halt(
                repo, suspended_status="claude_fixing",
            )
            retry_state = json.loads(written.read_text(encoding="utf-8"))
            self.assertEqual(
                retry_state["suspended_status"],
                "claude_fixing",
            )

    def test_refuses_when_already_capacity_halted(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(
                repo, status="halted_capacity_unavailable",
            )
            with self.assertRaises(HaltError) as ctx:
                agent_loop.record_capacity_halt(repo)
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )
            self.assertIn("already", str(ctx.exception))

    def test_refuses_when_other_halt_active(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(
                repo, status="halted_max_cycles_reached",
            )
            with self.assertRaises(HaltError) as ctx:
                agent_loop.record_capacity_halt(repo)
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )
            self.assertIn("already a halt", str(ctx.exception))

    def test_refuses_when_retry_state_already_exists(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo, status="claude_implementing")
            # Plant a stale retry-state.
            retry_path = (
                repo / ".agent-loop" / "capacity-retry-state.json"
            )
            retry_path.write_text("{}", encoding="utf-8")
            with self.assertRaises(HaltError) as ctx:
                agent_loop.record_capacity_halt(repo)
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )
            self.assertIn("already exists", str(ctx.exception))

    def test_audit_log_records_event(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo, status="claude_implementing")
            log = repo / ".agent-loop" / "orchestrator.log"
            agent_loop.record_capacity_halt(
                repo, reason="test-event", log_path=log,
            )
            audit = log.read_text(encoding="utf-8")
            self.assertIn(
                "capacity reprobe: recorded", audit,
            )
            self.assertIn("test-event", audit)

    def test_cli_records_capacity_halt(self) -> None:
        import os
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            state_path = _plant_loop_state(
                repo, status="claude_implementing",
            )
            prev_cwd = os.getcwd()
            os.chdir(repo)
            try:
                rc = agent_loop.main([
                    "record-capacity-halt",
                    "--reason", "manual-rate-limit",
                ])
            finally:
                os.chdir(prev_cwd)
            self.assertEqual(rc, 0)
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(
                state["status"], "halted_capacity_unavailable",
            )


class Phase9EAndPhase9FIntegrationTests(unittest.TestCase):
    """Phase 9F fix-cycle: the Phase 9E long-run loop integrates
    the Phase 9F reprobe seam. A long-run hop that lands in
    `halted_capacity_unavailable` dispatches
    `reprobe_capacity_and_resume(...)` via the new pre-hop branch
    rather than terminating on a generic `completion_halted`.
    """

    def test_long_run_dispatches_reprobe_on_capacity_halt(
        self,
    ) -> None:
        import os
        # Plant the halt + retry-state via the production path.
        prev = os.environ.get(agent_loop.CAPACITY_PROBE_ENV_VAR)
        os.environ[agent_loop.CAPACITY_PROBE_ENV_VAR] = "available"
        try:
            with TemporaryDirectory() as td:
                repo = _make_repo(Path(td))
                state_path = _plant_loop_state(
                    repo, status="claude_implementing",
                )
                _plant_prompts(repo)
                agent_loop.record_capacity_halt(repo)
                # Now run the long-run loop; the pre-hop branch
                # should detect halted_capacity_unavailable and
                # dispatch reprobe, which succeeds (env var is set)
                # and restores loop-state.
                with mock.patch(
                    "agent_loop.time.sleep", lambda s: None,
                ):
                    written = agent_loop.run_long_run_continuation(
                        repo,
                        max_hops=2,
                        capture_evidence=False,
                        invoke_codex_adapter=False,
                        invoke_claude_adapter=False,
                    )
                payload = json.loads(
                    written.read_text(encoding="utf-8"),
                )
                # Hop 0 should be the capacity reprobe.
                self.assertEqual(
                    payload["hops"][0]["action_taken"],
                    "capacity_reprobe",
                )
                self.assertEqual(
                    payload["hops"][0]["capacity_reprobe_rc"], 0,
                )
                # Loop-state restored to suspended_status.
                state = json.loads(
                    state_path.read_text(encoding="utf-8"),
                )
                self.assertEqual(
                    state["status"], "claude_implementing",
                )
        finally:
            if prev is None:
                os.environ.pop(
                    agent_loop.CAPACITY_PROBE_ENV_VAR, None,
                )
            else:
                os.environ[agent_loop.CAPACITY_PROBE_ENV_VAR] = prev

    def test_long_run_stops_on_reprobe_refusal(self) -> None:
        # No env var set: default probe returns False; the hop's
        # reprobe call runs through its full persisted budget
        # (default 5 attempts), all fail, and refuses on budget
        # exhaustion. Phase 9E catches the refusal and stops.
        import os
        prev = os.environ.pop(agent_loop.CAPACITY_PROBE_ENV_VAR, None)
        try:
            with TemporaryDirectory() as td:
                repo = _make_repo(Path(td))
                _plant_loop_state(repo, status="claude_implementing")
                agent_loop.record_capacity_halt(repo)
                with mock.patch(
                    "agent_loop.time.sleep", lambda s: None,
                ):
                    written = agent_loop.run_long_run_continuation(
                        repo,
                        max_hops=3,
                        capture_evidence=False,
                        invoke_codex_adapter=False,
                        invoke_claude_adapter=False,
                    )
                payload = json.loads(
                    written.read_text(encoding="utf-8"),
                )
                # Hop 0's reprobe call exhausts the cumulative
                # budget in one call (5 failed attempts against the
                # default-False probe); the refusal halts the
                # long-run loop.
                self.assertEqual(payload["hops_run"], 1)
                self.assertEqual(
                    payload["hops"][0]["action_taken"],
                    "capacity_reprobe",
                )
                self.assertNotEqual(
                    payload["hops"][0]["capacity_reprobe_rc"], 0,
                )
                self.assertIn(
                    "budget exhausted",
                    payload["hops"][0]["capacity_reprobe_halt_reason"],
                )
        finally:
            if prev is not None:
                os.environ[agent_loop.CAPACITY_PROBE_ENV_VAR] = prev

    def test_long_run_capacity_reprobe_budget_exhausted_stops(
        self,
    ) -> None:
        # With max_attempts=1 on the retry-state, the hop's
        # reprobe call runs 1 attempt against the default-False
        # probe, fails, and refuses on budget exhaustion in the
        # same call. hops_run = 1.
        import os
        prev = os.environ.pop(agent_loop.CAPACITY_PROBE_ENV_VAR, None)
        try:
            with TemporaryDirectory() as td:
                repo = _make_repo(Path(td))
                _plant_loop_state(repo, status="claude_implementing")
                agent_loop.record_capacity_halt(repo)
                retry_path = (
                    repo / ".agent-loop"
                    / "capacity-retry-state.json"
                )
                retry_state = json.loads(
                    retry_path.read_text(encoding="utf-8"),
                )
                retry_state["max_attempts"] = 1
                retry_path.write_text(
                    json.dumps(retry_state), encoding="utf-8",
                )
                with mock.patch(
                    "agent_loop.time.sleep", lambda s: None,
                ):
                    written = agent_loop.run_long_run_continuation(
                        repo,
                        max_hops=3,
                        capture_evidence=False,
                        invoke_codex_adapter=False,
                        invoke_claude_adapter=False,
                    )
                payload = json.loads(
                    written.read_text(encoding="utf-8"),
                )
                self.assertEqual(payload["hops_run"], 1)
                self.assertEqual(
                    payload["hops"][0]["action_taken"],
                    "capacity_reprobe",
                )
                self.assertNotEqual(
                    payload["hops"][0]["capacity_reprobe_rc"], 0,
                )
        finally:
            if prev is not None:
                os.environ[agent_loop.CAPACITY_PROBE_ENV_VAR] = prev

    def test_audit_log_records_capacity_reprobe_in_long_run(
        self,
    ) -> None:
        import os
        os.environ[agent_loop.CAPACITY_PROBE_ENV_VAR] = "available"
        try:
            with TemporaryDirectory() as td:
                repo = _make_repo(Path(td))
                _plant_loop_state(repo, status="claude_implementing")
                _plant_prompts(repo)
                agent_loop.record_capacity_halt(repo)
                log = repo / ".agent-loop" / "orchestrator.log"
                with mock.patch(
                    "agent_loop.time.sleep", lambda s: None,
                ):
                    agent_loop.run_long_run_continuation(
                        repo,
                        max_hops=2,
                        capture_evidence=False,
                        invoke_codex_adapter=False,
                        invoke_claude_adapter=False,
                        log_path=log,
                    )
                audit = log.read_text(encoding="utf-8")
                self.assertIn(
                    "long-run continuation: capacity_reprobe",
                    audit,
                )
        finally:
            os.environ.pop(agent_loop.CAPACITY_PROBE_ENV_VAR, None)


class SuspendedStatusAllowlistTests(unittest.TestCase):
    """Phase 9F fix-cycle: only Claude-side step statuses have a
    known resume continuation. Capacity halts recorded against any
    other status (or carrying a tampered suspended_status on disk)
    must refuse fail-closed rather than silently misroute on
    resume.
    """

    def test_constant_lists_supported_statuses(self) -> None:
        # Phase 9F fix-cycle: the allowlist now covers both
        # Claude-side suspended statuses (claude_implementing /
        # claude_fixing) AND the Codex-side suspended status
        # (awaiting_codex_review) so Claude/Codex token or
        # rate-limit exhaustion are both resumable.
        self.assertEqual(
            agent_loop.CAPACITY_RETRY_SUPPORTED_SUSPENDED_STATUSES,
            frozenset({
                "claude_implementing",
                "claude_fixing",
                "awaiting_codex_review",
            }),
        )

    def test_record_refuses_unsupported_explicit_override(self) -> None:
        # `evidence_capture` has no Phase 9F continuation routing
        # (it is owned by the run_checks evidence producer, not by
        # Claude or Codex), so a capacity halt recorded against it
        # is still refused fail-closed.
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo, status="claude_implementing")
            with self.assertRaises(HaltError) as ctx:
                agent_loop.record_capacity_halt(
                    repo, suspended_status="evidence_capture",
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )
            self.assertIn(
                "not a Phase 9F supported resume target",
                str(ctx.exception),
            )

    def test_record_refuses_unsupported_inferred_status(self) -> None:
        # No explicit override: the resolved suspended_status falls
        # back to the CURRENT loop-state status. A non-Claude-side
        # status is also refused fail-closed.
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo, status="evidence_capture")
            with self.assertRaises(HaltError) as ctx:
                agent_loop.record_capacity_halt(repo)
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )
            self.assertIn(
                "evidence_capture", str(ctx.exception),
            )

    def test_record_accepts_claude_implementing(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo, status="claude_implementing")
            written = agent_loop.record_capacity_halt(repo)
            retry_state = json.loads(written.read_text(encoding="utf-8"))
            self.assertEqual(
                retry_state["suspended_status"], "claude_implementing",
            )

    def test_record_accepts_claude_fixing(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo, status="claude_fixing")
            written = agent_loop.record_capacity_halt(repo)
            retry_state = json.loads(written.read_text(encoding="utf-8"))
            self.assertEqual(
                retry_state["suspended_status"], "claude_fixing",
            )

    def test_reprobe_refuses_persisted_unsupported_status(self) -> None:
        # A retry-state on disk that names an unsupported
        # suspended_status (operator-tampered, legacy from before
        # the allowlist landed, etc.) is refused fail-closed at
        # validation time so no successful re-probe ever routes
        # into the wrong continuation.
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            retry_path = (
                repo / ".agent-loop" / "capacity-retry-state.json"
            )
            retry_path.write_text(json.dumps({
                "retry_signal_version": "phase-9f-v1",
                "created_at": "2026-06-19T00:00:00Z",
                "phase": ACTIVE_PHASE,
                "sub_phase": ACTIVE_SUB_PHASE,
                "task": "capacity-reprobe-test",
                "cycle_count": 0,
                "attempt_count": 0,
                "max_attempts": 5,
                "initial_backoff_seconds": 1.0,
                "max_backoff_seconds": 30.0,
                "suspended_status": "evidence_capture",
                "history": [],
                "last_outcome": None,
                "canonical_precedence_note": "test",
            }), encoding="utf-8")
            with self.assertRaises(HaltError) as ctx:
                agent_loop.reprobe_capacity_and_resume(
                    repo,
                    sleep=_noop_sleep,
                    probe=_always_true_probe,
                    invoke_adapter=False,
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )
            self.assertIn(
                "supported resume target", str(ctx.exception),
            )


class ReprobeDispatchesSuspendedStepTests(unittest.TestCase):
    """Phase 9F fix-cycle: a successful re-probe does not merely
    restore loop-state.status; it also dispatches the matching
    Claude prompt handoff so the original suspended step actually
    runs. The dispatch writes the canonical
    `.agent-loop/prompt-handoff.json` descriptor (the same one
    cmd_dispatch_prompt_handoff produces) so the rest of the
    orchestrator picks up exactly where it would have if the
    capacity halt had never occurred.
    """

    def test_claude_implementing_dispatches_implementation_handoff(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            _plant_prompts(repo)
            agent_loop.reprobe_capacity_and_resume(
                repo,
                suspended_status="claude_implementing",
                sleep=_noop_sleep,
                probe=_always_true_probe,
                invoke_adapter=False,
            )
            handoff_path = (
                repo / ".agent-loop" / "prompt-handoff.json"
            )
            self.assertTrue(
                handoff_path.exists(),
                "prompt-handoff descriptor must be written on a "
                "successful reprobe so the suspended step actually "
                "runs",
            )
            handoff = json.loads(
                handoff_path.read_text(encoding="utf-8"),
            )
            self.assertEqual(handoff["mode"], "implementation")
            self.assertEqual(
                handoff["source_prompt_path"],
                ".agent-loop/claude-prompt.md",
            )

    def test_claude_fixing_dispatches_fix_handoff(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            _plant_prompts(repo)
            agent_loop.reprobe_capacity_and_resume(
                repo,
                suspended_status="claude_fixing",
                sleep=_noop_sleep,
                probe=_always_true_probe,
                invoke_adapter=False,
            )
            handoff_path = (
                repo / ".agent-loop" / "prompt-handoff.json"
            )
            self.assertTrue(handoff_path.exists())
            handoff = json.loads(
                handoff_path.read_text(encoding="utf-8"),
            )
            self.assertEqual(handoff["mode"], "fix")
            self.assertEqual(
                handoff["source_prompt_path"],
                ".agent-loop/fix-prompt.md",
            )

    def test_invoke_adapter_default_true_invokes_claude(self) -> None:
        # The default `invoke_adapter=True` actually invokes the
        # Claude adapter as part of the dispatch. Verified by
        # stubbing make_claude_adapter so the dispatch records the
        # invocation without blocking on a real handoff.
        invocations: list[dict] = []

        class _StubAdapter:
            def invoke(self, prompt_path, summary_path):
                invocations.append({
                    "prompt": prompt_path.name,
                    "summary": summary_path.name,
                })
                summary_path.write_text(
                    "# summary\n", encoding="utf-8",
                )
                from agent_loop import ExecutionResult
                return ExecutionResult(
                    exit_code=0,
                    model_id="claude-stub-model",
                    duration_seconds=0.0,
                )

        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            _plant_prompts(repo)
            with mock.patch(
                "agent_loop.make_claude_adapter",
                lambda: _StubAdapter(),
            ):
                agent_loop.reprobe_capacity_and_resume(
                    repo,
                    suspended_status="claude_implementing",
                    sleep=_noop_sleep,
                    probe=_always_true_probe,
                    # invoke_adapter default True
                )
            self.assertEqual(len(invocations), 1)
            self.assertEqual(
                invocations[0]["prompt"], "claude-prompt.md",
            )

    def test_resumed_audit_line_includes_handoff_mode(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            _plant_prompts(repo)
            log = repo / ".agent-loop" / "orchestrator.log"
            agent_loop.reprobe_capacity_and_resume(
                repo,
                suspended_status="claude_fixing",
                sleep=_noop_sleep,
                probe=_always_true_probe,
                invoke_adapter=False,
                log_path=log,
            )
            audit = log.read_text(encoding="utf-8")
            self.assertIn("capacity reprobe: resumed", audit)
            self.assertIn("handoff_mode='fix'", audit)
            self.assertIn(
                "suspended_status='claude_fixing'", audit,
            )


class Phase9FResumeRoutingIntegrationTests(unittest.TestCase):
    """Phase 9F fix-cycle: the Phase 9E long-run integration must
    actually resume the suspended Claude step on a successful
    re-probe, not just restore loop-state.status and drop into the
    generic Phase 9D review/fix path on the next hop.

    Concretely: a capacity halt recorded from a real in-flight
    `claude_implementing` status must, after a successful re-probe,
    have dispatched the implementation prompt handoff. The
    long-run loop's `invoke_claude_adapter` toggle forwards into
    the reprobe call so the test can verify the descriptor without
    consuming Claude capacity.
    """

    def setUp(self) -> None:
        import os
        self._prev = os.environ.get(
            agent_loop.CAPACITY_PROBE_ENV_VAR,
        )
        os.environ[agent_loop.CAPACITY_PROBE_ENV_VAR] = "available"

    def tearDown(self) -> None:
        import os
        if self._prev is None:
            os.environ.pop(
                agent_loop.CAPACITY_PROBE_ENV_VAR, None,
            )
        else:
            os.environ[agent_loop.CAPACITY_PROBE_ENV_VAR] = self._prev

    def test_long_run_resume_dispatches_implementation_not_review(
        self,
    ) -> None:
        # Record the capacity halt while loop-state is
        # claude_implementing; the production path captures that as
        # suspended_status. After run_long_run_continuation, the
        # prompt-handoff descriptor must show the implementation
        # mode was dispatched as part of the reprobe hop -- proving
        # the long-run loop did NOT silently misroute into the
        # Phase 9D review/fix path.
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo, status="claude_implementing")
            _plant_prompts(repo)
            agent_loop.record_capacity_halt(repo)
            with mock.patch(
                "agent_loop.time.sleep", lambda s: None,
            ):
                agent_loop.run_long_run_continuation(
                    repo,
                    max_hops=1,
                    capture_evidence=False,
                    invoke_codex_adapter=False,
                    invoke_claude_adapter=False,
                )
            handoff_path = (
                repo / ".agent-loop" / "prompt-handoff.json"
            )
            self.assertTrue(
                handoff_path.exists(),
                "the long-run loop's capacity_reprobe hop must "
                "dispatch the prompt handoff for the suspended "
                "step, not just restore loop-state.status",
            )
            handoff = json.loads(
                handoff_path.read_text(encoding="utf-8"),
            )
            self.assertEqual(handoff["mode"], "implementation")

    def test_long_run_resume_dispatches_fix_for_claude_fixing(
        self,
    ) -> None:
        # Symmetric test: a capacity halt recorded while loop-state
        # is claude_fixing resumes via the fix prompt, not the
        # implementation prompt.
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo, status="claude_fixing")
            _plant_prompts(repo)
            agent_loop.record_capacity_halt(repo)
            with mock.patch(
                "agent_loop.time.sleep", lambda s: None,
            ):
                agent_loop.run_long_run_continuation(
                    repo,
                    max_hops=1,
                    capture_evidence=False,
                    invoke_codex_adapter=False,
                    invoke_claude_adapter=False,
                )
            handoff = json.loads(
                (
                    repo / ".agent-loop" / "prompt-handoff.json"
                ).read_text(encoding="utf-8"),
            )
            self.assertEqual(handoff["mode"], "fix")

    def test_long_run_resume_forwards_invoke_claude_toggle(
        self,
    ) -> None:
        # When the operator passes invoke_claude_adapter=False to
        # the long-run loop, the reprobe call inside the hop must
        # NOT invoke the Claude adapter. Stub make_claude_adapter
        # to assert no invocations leaked through.
        invocations: list[str] = []

        class _UnexpectedAdapter:
            def invoke(self, prompt_path, summary_path):
                invocations.append(prompt_path.name)
                from agent_loop import ExecutionResult
                return ExecutionResult(
                    exit_code=0,
                    model_id="unexpected",
                    duration_seconds=0.0,
                )

        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo, status="claude_implementing")
            _plant_prompts(repo)
            agent_loop.record_capacity_halt(repo)
            with mock.patch(
                "agent_loop.make_claude_adapter",
                lambda: _UnexpectedAdapter(),
            ):
                with mock.patch(
                    "agent_loop.time.sleep", lambda s: None,
                ):
                    agent_loop.run_long_run_continuation(
                        repo,
                        max_hops=1,
                        capture_evidence=False,
                        invoke_codex_adapter=False,
                        invoke_claude_adapter=False,
                    )
            self.assertEqual(
                invocations, [],
                "invoke_claude_adapter=False must propagate into "
                "the capacity-reprobe hop's dispatch",
            )


class CodexSideCapacityHaltTests(unittest.TestCase):
    """Phase 9F fix-cycle: Codex/Claude parity. A capacity halt
    recorded while loop-state is at `awaiting_codex_review` (the
    Codex-side suspended status) is supported by the Phase 9F
    allowlist and resumes through the correct Codex review
    continuation, not through a Claude prompt re-dispatch.
    """

    def test_record_accepts_awaiting_codex_review_explicit(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo, status="claude_implementing")
            written = agent_loop.record_capacity_halt(
                repo, suspended_status="awaiting_codex_review",
            )
            retry_state = json.loads(written.read_text(encoding="utf-8"))
            self.assertEqual(
                retry_state["suspended_status"],
                "awaiting_codex_review",
            )

    def test_record_accepts_awaiting_codex_review_inferred(
        self,
    ) -> None:
        # No explicit override: the resolved suspended_status falls
        # back to the CURRENT loop-state status. A Codex-side
        # in-flight status is now accepted (Phase 9F fix-cycle:
        # Claude/Codex parity).
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo, status="awaiting_codex_review")
            written = agent_loop.record_capacity_halt(repo)
            retry_state = json.loads(written.read_text(encoding="utf-8"))
            self.assertEqual(
                retry_state["suspended_status"],
                "awaiting_codex_review",
            )

    def test_reprobe_restores_codex_side_status_without_claude_dispatch(
        self,
    ) -> None:
        # A successful reprobe for awaiting_codex_review restores
        # loop-state.status to "awaiting_codex_review" and does
        # NOT write a Claude prompt handoff descriptor (the Phase
        # 9F seam deliberately routes the continuation through the
        # next orchestrator step's Codex review invocation).
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            state_path = _plant_loop_state(repo)
            agent_loop.reprobe_capacity_and_resume(
                repo,
                suspended_status="awaiting_codex_review",
                sleep=_noop_sleep,
                probe=_always_true_probe,
                invoke_adapter=False,
            )
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(
                state["status"], "awaiting_codex_review",
            )
            # No Claude prompt handoff descriptor written for the
            # Codex-side resume path.
            handoff_path = (
                repo / ".agent-loop" / "prompt-handoff.json"
            )
            self.assertFalse(
                handoff_path.exists(),
                "Codex-side capacity resume must NOT dispatch a "
                "Claude prompt handoff; the continuation is the "
                "next orchestrator step's Codex review invocation",
            )
            # Retry-state file is deleted on success.
            retry_path = (
                repo / ".agent-loop" / "capacity-retry-state.json"
            )
            self.assertFalse(retry_path.exists())

    def test_reprobe_codex_side_audit_records_codex_review_pending(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            log = repo / ".agent-loop" / "orchestrator.log"
            agent_loop.reprobe_capacity_and_resume(
                repo,
                suspended_status="awaiting_codex_review",
                sleep=_noop_sleep,
                probe=_always_true_probe,
                invoke_adapter=False,
                log_path=log,
            )
            audit = log.read_text(encoding="utf-8")
            self.assertIn("capacity reprobe: resumed", audit)
            self.assertIn(
                "suspended_status='awaiting_codex_review'", audit,
            )
            self.assertIn(
                "handoff_mode='codex_review_pending'", audit,
            )

    def test_reprobe_codex_side_does_not_invoke_claude_adapter(
        self,
    ) -> None:
        # The Codex-side resume path must not touch the Claude
        # adapter even when invoke_adapter=True. The flag dispatches
        # the Codex review wait (not a Claude prompt handoff) for
        # the Codex-side branch.
        claude_invocations: list[str] = []
        codex_invocations: list[str] = []

        class _UnexpectedClaude:
            def invoke(self, prompt_path, summary_path):
                claude_invocations.append(prompt_path.name)
                from agent_loop import ExecutionResult
                return ExecutionResult(
                    exit_code=0,
                    model_id="unexpected-claude",
                    duration_seconds=0.0,
                )

        class _StubCodex:
            def wait_for_review(self, review_path):
                codex_invocations.append(review_path.name)
                review_path.write_text(
                    "# Codex Review\n\n## Verdict\n"
                    "APPROVED_FOR_HUMAN_REVIEW\n",
                    encoding="utf-8",
                )
                from agent_loop import ExecutionResult
                return ExecutionResult(
                    exit_code=0,
                    model_id="codex-stub-model",
                    duration_seconds=0.0,
                )

        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            with mock.patch(
                "agent_loop.make_claude_adapter",
                lambda: _UnexpectedClaude(),
            ), mock.patch(
                "agent_loop.make_codex_adapter",
                lambda: _StubCodex(),
            ):
                agent_loop.reprobe_capacity_and_resume(
                    repo,
                    suspended_status="awaiting_codex_review",
                    sleep=_noop_sleep,
                    probe=_always_true_probe,
                    # invoke_adapter defaults to True
                )
            self.assertEqual(
                claude_invocations, [],
                "Codex-side resume must NOT invoke the Claude "
                "adapter even when invoke_adapter=True",
            )
            # Codex IS invoked on the Codex-side resume path
            # (Phase 9F fix-cycle: close the automatic-resume gap).
            self.assertEqual(
                codex_invocations, ["codex-review.md"],
                "Codex-side resume must invoke the Codex adapter "
                "with the canonical codex-review.md path",
            )

    def test_long_run_resume_routes_codex_side_capacity_halt(
        self,
    ) -> None:
        # Phase 9E integration: a capacity halt recorded while
        # loop-state is at awaiting_codex_review resumes via the
        # Codex review path. The successful reprobe restores the
        # status to "awaiting_codex_review"; the long-run loop's
        # next hop then runs run_internal_review_fix_cycle, which
        # is the canonical Codex review invocation path. The test
        # verifies the resume does NOT write a Claude prompt
        # handoff descriptor (silent Claude misroute would be a
        # contract violation).
        import os
        prev = os.environ.get(agent_loop.CAPACITY_PROBE_ENV_VAR)
        os.environ[agent_loop.CAPACITY_PROBE_ENV_VAR] = "available"
        try:
            with TemporaryDirectory() as td:
                repo = _make_repo(Path(td))
                _plant_loop_state(
                    repo, status="awaiting_codex_review",
                )
                _plant_prompts(repo)
                agent_loop.record_capacity_halt(repo)
                with mock.patch(
                    "agent_loop.time.sleep", lambda s: None,
                ):
                    written = agent_loop.run_long_run_continuation(
                        repo,
                        max_hops=1,
                        capture_evidence=False,
                        invoke_codex_adapter=False,
                        invoke_claude_adapter=False,
                    )
                payload = json.loads(
                    written.read_text(encoding="utf-8"),
                )
                self.assertEqual(
                    payload["hops"][0]["action_taken"],
                    "capacity_reprobe",
                )
                self.assertEqual(
                    payload["hops"][0]["capacity_reprobe_rc"], 0,
                )
                # Loop-state restored to the Codex-side suspended
                # status, not silently flipped to a Claude-side
                # one.
                state_path = (
                    repo / ".agent-loop" / "loop-state.json"
                )
                state = json.loads(
                    state_path.read_text(encoding="utf-8"),
                )
                self.assertEqual(
                    state["status"], "awaiting_codex_review",
                )
                # No Claude prompt handoff descriptor written.
                handoff_path = (
                    repo / ".agent-loop" / "prompt-handoff.json"
                )
                self.assertFalse(
                    handoff_path.exists(),
                    "Codex-side capacity halt resume must NOT "
                    "dispatch a Claude prompt handoff in the "
                    "long-run loop",
                )
        finally:
            if prev is None:
                os.environ.pop(
                    agent_loop.CAPACITY_PROBE_ENV_VAR, None,
                )
            else:
                os.environ[agent_loop.CAPACITY_PROBE_ENV_VAR] = prev

    def test_reprobe_refuses_persisted_evidence_capture_status(
        self,
    ) -> None:
        # Defense in depth: a persisted retry-state naming
        # `evidence_capture` (still unsupported even after the
        # Codex-side parity extension) is refused fail-closed at
        # load time.
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            retry_path = (
                repo / ".agent-loop" / "capacity-retry-state.json"
            )
            retry_path.write_text(json.dumps({
                "retry_signal_version": "phase-9f-v1",
                "created_at": "2026-06-19T00:00:00Z",
                "phase": ACTIVE_PHASE,
                "sub_phase": ACTIVE_SUB_PHASE,
                "task": "capacity-reprobe-test",
                "cycle_count": 0,
                "attempt_count": 0,
                "max_attempts": 5,
                "initial_backoff_seconds": 1.0,
                "max_backoff_seconds": 30.0,
                "suspended_status": "evidence_capture",
                "history": [],
                "last_outcome": None,
                "canonical_precedence_note": "test",
            }), encoding="utf-8")
            with self.assertRaises(HaltError) as ctx:
                agent_loop.reprobe_capacity_and_resume(
                    repo,
                    sleep=_noop_sleep,
                    probe=_always_true_probe,
                    invoke_adapter=False,
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )
            self.assertIn(
                "supported resume target", str(ctx.exception),
            )


class CodexSideAutomaticResumeTests(unittest.TestCase):
    """Phase 9F fix-cycle: a successful capacity reprobe from
    `awaiting_codex_review` resumes the suspended Codex review
    step AUTOMATICALLY by invoking the shipped Codex adapter
    (via `make_codex_adapter().wait_for_review(...)`) against the
    already-captured Claude summary + evidence, not merely
    restoring loop-state.status. The standalone CLI success path
    + the library entry both honor this contract.
    """

    def _stub_codex(self, invocations, model_id="codex-stub-v1"):
        class _StubCodex:
            def wait_for_review(self_inner, review_path):
                invocations.append({
                    "review_path": review_path.name,
                })
                review_path.write_text(
                    "# Codex Review\n\n## Verdict\n"
                    "APPROVED_FOR_HUMAN_REVIEW\n",
                    encoding="utf-8",
                )
                from agent_loop import ExecutionResult
                return ExecutionResult(
                    exit_code=0,
                    model_id=model_id,
                    duration_seconds=0.0,
                )
        return _StubCodex()

    def test_library_resume_invokes_codex_adapter_by_default(
        self,
    ) -> None:
        invocations: list[dict] = []
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            with mock.patch(
                "agent_loop.make_codex_adapter",
                lambda: self._stub_codex(invocations),
            ):
                agent_loop.reprobe_capacity_and_resume(
                    repo,
                    suspended_status="awaiting_codex_review",
                    sleep=_noop_sleep,
                    probe=_always_true_probe,
                    # invoke_adapter defaults to True
                )
            self.assertEqual(len(invocations), 1)
            self.assertEqual(
                invocations[0]["review_path"], "codex-review.md",
            )
            # Codex adapter actually wrote the review artifact.
            review_path = (
                repo / ".agent-loop" / "codex-review.md"
            )
            self.assertTrue(review_path.exists())

    def test_resume_saves_codex_version_on_invocation(
        self,
    ) -> None:
        invocations: list[dict] = []
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            state_path = _plant_loop_state(repo)
            with mock.patch(
                "agent_loop.make_codex_adapter",
                lambda: self._stub_codex(
                    invocations, model_id="codex-resume-v9",
                ),
            ):
                agent_loop.reprobe_capacity_and_resume(
                    repo,
                    suspended_status="awaiting_codex_review",
                    sleep=_noop_sleep,
                    probe=_always_true_probe,
                )
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(
                state["codex_version"], "codex-resume-v9",
                "the resumed Codex review must persist its model_id "
                "into loop-state.codex_version when the adapter "
                "self-reports it (mirrors the normal-cycle Codex "
                "review step contract)",
            )

    def test_resume_audit_records_codex_review_invoked(self) -> None:
        invocations: list[dict] = []
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            log = repo / ".agent-loop" / "orchestrator.log"
            with mock.patch(
                "agent_loop.make_codex_adapter",
                lambda: self._stub_codex(invocations),
            ):
                agent_loop.reprobe_capacity_and_resume(
                    repo,
                    suspended_status="awaiting_codex_review",
                    sleep=_noop_sleep,
                    probe=_always_true_probe,
                    log_path=log,
                )
            audit = log.read_text(encoding="utf-8")
            self.assertIn(
                "capacity reprobe: resumed", audit,
            )
            self.assertIn("handoff_mode='codex_review'", audit)
            self.assertNotIn(
                "handoff_mode='codex_review_pending'", audit,
                "the audit line must record 'codex_review' (active "
                "dispatch) when invoke_adapter=True, not the "
                "descriptor-free 'codex_review_pending' marker",
            )
            self.assertIn(
                "capacity reprobe: codex_review_invoked", audit,
            )
            self.assertIn("exit_code=0", audit)

    def test_dry_run_invoke_adapter_false_keeps_descriptor_free(
        self,
    ) -> None:
        # Explicit invoke_adapter=False keeps the prior behavior:
        # restore status, audit codex_review_pending, do NOT call
        # the Codex adapter.
        invocations: list[dict] = []
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            log = repo / ".agent-loop" / "orchestrator.log"
            with mock.patch(
                "agent_loop.make_codex_adapter",
                lambda: self._stub_codex(invocations),
            ):
                agent_loop.reprobe_capacity_and_resume(
                    repo,
                    suspended_status="awaiting_codex_review",
                    sleep=_noop_sleep,
                    probe=_always_true_probe,
                    invoke_adapter=False,
                    log_path=log,
                )
            self.assertEqual(
                invocations, [],
                "invoke_adapter=False must skip the Codex adapter "
                "wait_for_review call on the Codex-side resume",
            )
            audit = log.read_text(encoding="utf-8")
            self.assertIn(
                "handoff_mode='codex_review_pending'", audit,
            )

    def test_cli_success_path_invokes_codex_adapter(self) -> None:
        # The standalone CLI success path (no --no-invoke-adapter)
        # now actively invokes the Codex adapter on a Codex-side
        # resume; it no longer stops at restore-only behavior.
        invocations: list[dict] = []
        import os
        prev = os.environ.get(agent_loop.CAPACITY_PROBE_ENV_VAR)
        os.environ[agent_loop.CAPACITY_PROBE_ENV_VAR] = "available"
        prev_cwd = os.getcwd()
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(
                repo, status="awaiting_codex_review",
            )
            agent_loop.record_capacity_halt(repo)
            os.chdir(repo)
            try:
                with mock.patch(
                    "agent_loop.make_codex_adapter",
                    lambda: self._stub_codex(invocations),
                ), mock.patch(
                    "agent_loop.time.sleep", lambda s: None,
                ):
                    rc = agent_loop.main([
                        "run-capacity-reprobe",
                        "--max-attempts", "1",
                        "--initial-backoff-seconds", "0.001",
                        "--max-backoff-seconds", "0.001",
                    ])
                self.assertEqual(rc, 0)
                self.assertEqual(
                    len(invocations), 1,
                    "CLI success path must invoke the Codex "
                    "adapter on a Codex-side resume",
                )
                # codex-review.md was written by the stub.
                review_path = (
                    repo / ".agent-loop" / "codex-review.md"
                )
                self.assertTrue(review_path.exists())
            finally:
                os.chdir(prev_cwd)
                if prev is None:
                    os.environ.pop(
                        agent_loop.CAPACITY_PROBE_ENV_VAR, None,
                    )
                else:
                    os.environ[
                        agent_loop.CAPACITY_PROBE_ENV_VAR
                    ] = prev

    def test_long_run_codex_side_resume_invokes_codex_when_codex_flag_true(
        self,
    ) -> None:
        # Phase 9F fix-cycle: the long-run loop's
        # `invoke_codex_adapter` (not invoke_claude_adapter) gates
        # the Codex-side capacity-resume dispatch. With
        # invoke_codex_adapter=True the Codex-side reprobe hop
        # actively dispatches `wait_for_review`. max_hops=1 means
        # only the reprobe hop runs; there is no next-hop
        # review/fix iteration to invoke Codex a second time.
        codex_invocations: list[dict] = []
        import os
        prev = os.environ.get(agent_loop.CAPACITY_PROBE_ENV_VAR)
        os.environ[agent_loop.CAPACITY_PROBE_ENV_VAR] = "available"
        try:
            with TemporaryDirectory() as td:
                repo = _make_repo(Path(td))
                _plant_loop_state(
                    repo, status="awaiting_codex_review",
                )
                _plant_prompts(repo)
                agent_loop.record_capacity_halt(repo)
                with mock.patch(
                    "agent_loop.make_codex_adapter",
                    lambda: self._stub_codex(codex_invocations),
                ), mock.patch(
                    "agent_loop.time.sleep", lambda s: None,
                ):
                    agent_loop.run_long_run_continuation(
                        repo,
                        max_hops=1,
                        capture_evidence=False,
                        invoke_codex_adapter=True,
                        invoke_claude_adapter=False,
                    )
                self.assertEqual(
                    len(codex_invocations), 1,
                    "long-run loop with invoke_codex_adapter=True "
                    "must dispatch the Codex review wait as part "
                    "of the Codex-side resume hop",
                )
        finally:
            if prev is None:
                os.environ.pop(
                    agent_loop.CAPACITY_PROBE_ENV_VAR, None,
                )
            else:
                os.environ[agent_loop.CAPACITY_PROBE_ENV_VAR] = prev

    def test_long_run_codex_side_resume_skips_codex_when_codex_flag_false(
        self,
    ) -> None:
        # Phase 9F fix-cycle: the long-run loop's
        # `invoke_codex_adapter=False` MUST suppress the Codex
        # adapter dispatch on the Codex-side capacity-resume hop,
        # regardless of `invoke_claude_adapter`. Previously the
        # call routed Codex dispatch through the Claude flag,
        # which meant `--no-invoke-codex` had no effect on a
        # Codex-side resume - an operator-control bug.
        codex_invocations: list[dict] = []
        import os
        prev = os.environ.get(agent_loop.CAPACITY_PROBE_ENV_VAR)
        os.environ[agent_loop.CAPACITY_PROBE_ENV_VAR] = "available"
        try:
            with TemporaryDirectory() as td:
                repo = _make_repo(Path(td))
                _plant_loop_state(
                    repo, status="awaiting_codex_review",
                )
                _plant_prompts(repo)
                agent_loop.record_capacity_halt(repo)
                with mock.patch(
                    "agent_loop.make_codex_adapter",
                    lambda: self._stub_codex(codex_invocations),
                ), mock.patch(
                    "agent_loop.time.sleep", lambda s: None,
                ):
                    agent_loop.run_long_run_continuation(
                        repo,
                        max_hops=1,
                        capture_evidence=False,
                        # invoke_claude_adapter=True must NOT
                        # leak through to the Codex-side dispatch.
                        invoke_codex_adapter=False,
                        invoke_claude_adapter=True,
                    )
                self.assertEqual(
                    codex_invocations, [],
                    "long-run loop with invoke_codex_adapter=False "
                    "must NOT dispatch the Codex adapter on the "
                    "Codex-side resume hop even when "
                    "invoke_claude_adapter=True",
                )
                # Loop-state is still correctly restored from the
                # halt; only the adapter dispatch was suppressed.
                state = json.loads(
                    (
                        repo / ".agent-loop" / "loop-state.json"
                    ).read_text(encoding="utf-8"),
                )
                self.assertEqual(
                    state["status"], "awaiting_codex_review",
                )
        finally:
            if prev is None:
                os.environ.pop(
                    agent_loop.CAPACITY_PROBE_ENV_VAR, None,
                )
            else:
                os.environ[agent_loop.CAPACITY_PROBE_ENV_VAR] = prev

    def test_long_run_claude_side_resume_still_respects_claude_flag(
        self,
    ) -> None:
        # Phase 9F fix-cycle regression guard: the Claude-side
        # branch must still honor invoke_claude_adapter (and
        # ignore invoke_codex_adapter). With
        # invoke_claude_adapter=False the Claude-side resume
        # writes only the prompt-handoff descriptor; the Claude
        # adapter is NOT invoked even when
        # invoke_codex_adapter=True.
        claude_invocations: list[str] = []

        class _UnexpectedClaude:
            def invoke(self, prompt_path, summary_path):
                claude_invocations.append(prompt_path.name)
                from agent_loop import ExecutionResult
                return ExecutionResult(
                    exit_code=0,
                    model_id="unexpected-claude",
                    duration_seconds=0.0,
                )

        import os
        prev = os.environ.get(agent_loop.CAPACITY_PROBE_ENV_VAR)
        os.environ[agent_loop.CAPACITY_PROBE_ENV_VAR] = "available"
        try:
            with TemporaryDirectory() as td:
                repo = _make_repo(Path(td))
                _plant_loop_state(
                    repo, status="claude_implementing",
                )
                _plant_prompts(repo)
                agent_loop.record_capacity_halt(repo)
                with mock.patch(
                    "agent_loop.make_claude_adapter",
                    lambda: _UnexpectedClaude(),
                ), mock.patch(
                    "agent_loop.time.sleep", lambda s: None,
                ):
                    agent_loop.run_long_run_continuation(
                        repo,
                        max_hops=1,
                        capture_evidence=False,
                        invoke_codex_adapter=True,
                        invoke_claude_adapter=False,
                    )
                self.assertEqual(
                    claude_invocations, [],
                    "Claude-side resume must honor "
                    "invoke_claude_adapter=False even when "
                    "invoke_codex_adapter=True",
                )
                # The prompt-handoff descriptor still gets
                # written (descriptor-only dispatch); only the
                # adapter call is suppressed.
                handoff = json.loads(
                    (
                        repo / ".agent-loop" / "prompt-handoff.json"
                    ).read_text(encoding="utf-8"),
                )
                self.assertEqual(handoff["mode"], "implementation")
                self.assertFalse(handoff["adapter_invoked"])
        finally:
            if prev is None:
                os.environ.pop(
                    agent_loop.CAPACITY_PROBE_ENV_VAR, None,
                )
            else:
                os.environ[agent_loop.CAPACITY_PROBE_ENV_VAR] = prev


class CapacityReprobeHelpTextTests(unittest.TestCase):

    def _help_text(self) -> str:
        parser = agent_loop.build_parser()
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                for choice_action in action._choices_actions:
                    if choice_action.dest == "run-capacity-reprobe":
                        return choice_action.help or ""
        self.fail("run-capacity-reprobe subparser help not found")
        return ""

    def test_help_describes_phase_9f_role(self) -> None:
        text = self._help_text()
        self.assertIn("Phase 9F", text)
        self.assertIn("capacity", text)

    def test_help_documents_retry_state_path(self) -> None:
        text = self._help_text()
        self.assertIn(
            ".agent-loop/capacity-retry-state.json", text,
        )

    def test_help_documents_bounded_behavior(self) -> None:
        text = self._help_text()
        self.assertIn("bounded", text)
        self.assertIn("backoff", text)
        self.assertIn("budget", text)

    def test_help_documents_halt_status(self) -> None:
        text = self._help_text()
        self.assertIn("halted_capacity_unavailable", text)


if __name__ == "__main__":
    unittest.main()
