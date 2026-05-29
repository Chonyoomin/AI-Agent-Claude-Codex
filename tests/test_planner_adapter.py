"""Focused tests for the Phase 4E planner-adapter seam in
`scripts/agent_loop.py`.

Scope:
- `make_planner_adapter()` is the dispatch seam. By default it returns the
  in-process `LocalPlannerAdapter`, whose `run` is a thin pass-through to
  `run_planner` (today's behavior is preserved).
- The `plan` CLI path (`cmd_plan`) routes planner execution through the
  adapter seam rather than calling `run_planner` directly.
- The post-approval refresh (`_invoke_post_approval_planner`) routes through
  the same seam and still contains adapter exceptions (returns the
  containment sentinel, logs a `note:` line, never re-raises `Exception`).
- The seam does not widen writes: a successful `plan` through the default
  adapter writes only `.agent-loop/proposed-phase.md` and
  `.agent-loop/planner.log`; it performs no activation-owned writes and does
  not touch `.agent-loop/loop-state.json`.

The synthetic repository reuses `test_planner._Repo`, whose default state is
a planner-success setup (fresh evidence and a dispatchable active sub-phase).
"""

from __future__ import annotations

import argparse
import json
import sys
import unittest
import unittest.mock as mock
from pathlib import Path
from tempfile import TemporaryDirectory


HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(HERE))

import agent_loop  # noqa: E402 - sys.path is set above
import test_planner  # noqa: E402 - reuse the planner-success _Repo builder


# Activation-owned files the planner path (and its adapter seam) must never
# write. loop-state.json is checked separately: the `plan` path must not touch
# it at all.
_ACTIVATION_OWNED_MARKDOWN = (
    "TASK.md",
    ".agent-loop/current-task.md",
    ".agent-loop/current-phase.md",
    ".agent-loop/phase-plan.md",
)


class _RecordingAdapter:
    """Stand-in planner adapter that records calls instead of running the
    real planner. Used to prove the call sites dispatch through the seam."""

    name = "recording"

    def __init__(self, rc: int = 0, exc: BaseException | None = None) -> None:
        self.calls: list[Path] = []
        self._rc = rc
        self._exc = exc

    def run(self, repo_root: Path) -> int:
        self.calls.append(repo_root)
        if self._exc is not None:
            raise self._exc
        return self._rc


class _AdapterTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = test_planner._Repo(Path(self._tmp.name))
        self.log_path = self.repo.root / ".agent-loop" / "orchestrator.log"

    def _orchestrator_log(self) -> str:
        return self.log_path.read_text(encoding="utf-8") if self.log_path.is_file() else ""


class AdapterFactoryTests(_AdapterTestCase):

    def test_default_factory_returns_local_adapter(self) -> None:
        adapter = agent_loop.make_planner_adapter()
        self.assertIsInstance(adapter, agent_loop.LocalPlannerAdapter)
        self.assertEqual(adapter.name, "local")
        self.assertTrue(hasattr(adapter, "run"))


class LocalAdapterBehaviorTests(_AdapterTestCase):

    def test_local_adapter_delegates_to_run_planner(self) -> None:
        sentinel = 7
        with mock.patch.object(
            agent_loop, "run_planner", return_value=sentinel
        ) as patched:
            rc = agent_loop.LocalPlannerAdapter().run(self.repo.root)
        self.assertEqual(rc, sentinel, "adapter must pass run_planner's code through")
        patched.assert_called_once_with(self.repo.root)

    def test_local_adapter_preserves_success_behavior(self) -> None:
        rc = agent_loop.LocalPlannerAdapter().run(self.repo.root)
        self.assertEqual(rc, 0)
        self.assertTrue(
            (self.repo.root / agent_loop.PROPOSAL_PATH_REL).exists(),
            "default adapter must preserve the planner's proposal-write behavior",
        )


class PlanCommandSeamTests(_AdapterTestCase):

    def test_cmd_plan_routes_through_adapter_seam(self) -> None:
        recorder = _RecordingAdapter(rc=0)
        with mock.patch.object(
            agent_loop, "find_repo_root", return_value=self.repo.root
        ), mock.patch.object(
            agent_loop, "make_planner_adapter", return_value=recorder
        ):
            rc = agent_loop.cmd_plan(argparse.Namespace())
        self.assertEqual(rc, 0)
        self.assertEqual(
            recorder.calls, [self.repo.root],
            "cmd_plan must dispatch planner execution through the adapter seam",
        )

    def test_cmd_plan_default_adapter_preserves_behavior(self) -> None:
        with mock.patch.object(
            agent_loop, "find_repo_root", return_value=self.repo.root
        ):
            rc = agent_loop.cmd_plan(argparse.Namespace())
        self.assertEqual(rc, 0)
        self.assertTrue((self.repo.root / agent_loop.PROPOSAL_PATH_REL).exists())


class PostApprovalSeamTests(_AdapterTestCase):

    def test_post_approval_routes_through_adapter_seam(self) -> None:
        recorder = _RecordingAdapter(rc=0)
        with mock.patch.object(
            agent_loop, "make_planner_adapter", return_value=recorder
        ):
            rc = agent_loop._invoke_post_approval_planner(self.repo.root, self.log_path)
        self.assertEqual(rc, 0)
        self.assertEqual(recorder.calls, [self.repo.root])
        self.assertIn("post-approval planner invoked", self._orchestrator_log())
        self.assertIn("planner_exit_code=0", self._orchestrator_log())

    def test_post_approval_contains_adapter_exception(self) -> None:
        recorder = _RecordingAdapter(exc=RuntimeError("adapter blew up"))
        with mock.patch.object(
            agent_loop, "make_planner_adapter", return_value=recorder
        ):
            rc = agent_loop._invoke_post_approval_planner(self.repo.root, self.log_path)
        self.assertEqual(rc, agent_loop.POST_APPROVAL_PLANNER_EXCEPTION_CODE)
        log = self._orchestrator_log()
        self.assertIn("post-approval planner raised an unexpected exception", log)
        self.assertIn("RuntimeError", log)
        self.assertIn("adapter blew up", log)


class NoWideningWriteTests(_AdapterTestCase):

    def _snapshot_markdown(self) -> dict:
        snap: dict = {}
        for rel in _ACTIVATION_OWNED_MARKDOWN:
            p = self.repo.root / rel
            snap[rel] = p.read_bytes() if p.is_file() else None
        return snap

    def test_default_adapter_plan_does_not_widen_writes(self) -> None:
        state_path = self.repo.root / ".agent-loop" / "loop-state.json"
        before_md = self._snapshot_markdown()
        before_state = state_path.read_bytes()

        with mock.patch.object(
            agent_loop, "find_repo_root", return_value=self.repo.root
        ):
            rc = agent_loop.cmd_plan(argparse.Namespace())
        self.assertEqual(rc, 0)

        # The planner wrote within its boundary only.
        self.assertTrue((self.repo.root / agent_loop.PROPOSAL_PATH_REL).exists())
        self.assertTrue((self.repo.root / agent_loop.PLANNER_LOG_PATH_REL).exists())

        # No activation-owned markdown was created or mutated.
        after_md = self._snapshot_markdown()
        for rel in _ACTIVATION_OWNED_MARKDOWN:
            self.assertEqual(
                before_md[rel], after_md[rel],
                f"adapter seam must not widen writes to activation-owned file {rel}",
            )

        # The `plan` path does not touch loop-state.json at all.
        self.assertEqual(
            before_state, state_path.read_bytes(),
            "the adapterized plan path must not write loop-state.json",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
