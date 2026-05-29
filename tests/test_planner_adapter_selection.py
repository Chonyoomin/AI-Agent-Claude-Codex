"""Focused tests for the Phase 4F planner-adapter SELECTION behavior in
`scripts/agent_loop.py`.

Phase 4E introduced the seam (`make_planner_adapter()` + `LocalPlannerAdapter`);
Phase 4F makes the seam selectable behind the `AGENT_LOOP_PLANNER_CMD` env var:

- no / blank / whitespace-only configuration -> the default in-process
  `LocalPlannerAdapter` (the fallback), behavior unchanged
- a non-blank command -> exactly one alternate, the out-of-process
  `SubprocessPlannerAdapter`, which delegates to the configured command and
  passes its exit code through (0 success / 2 refusal convention)
- selecting an adapter never widens the planner write boundary
  (`.agent-loop/proposed-phase.md` and `.agent-loop/planner.log` only) and
  never performs an activation-owned write

The synthetic repository reuses `test_planner._Repo` (a planner-success setup).
The alternate-adapter tests invoke a real subprocess driving the current
Python interpreter against a tiny helper script written into the temp repo, so
they stay cross-platform and do not depend on any shell builtin behavior.
"""

from __future__ import annotations

import argparse
import os
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


_ACTIVATION_OWNED_MARKDOWN = (
    "TASK.md",
    ".agent-loop/current-task.md",
    ".agent-loop/current-phase.md",
    ".agent-loop/phase-plan.md",
)


def _clear_planner_env() -> dict:
    """Return an os.environ copy with AGENT_LOOP_PLANNER_CMD removed."""
    env = dict(os.environ)
    env.pop(agent_loop.ENV_PLANNER_CMD, None)
    return env


class _SelectionTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = test_planner._Repo(Path(self._tmp.name))
        self.state_path = self.repo.root / ".agent-loop" / "loop-state.json"

    def _write_helper(self, name: str, body: str) -> str:
        """Write a helper planner script into the repo and return a shell
        command (quoted) that runs it with the current interpreter."""
        script = self.repo.root / name
        script.write_text(body, encoding="utf-8")
        return f'"{sys.executable}" "{script}"'


class SelectionTests(_SelectionTestCase):

    def test_no_config_falls_back_to_local(self) -> None:
        with mock.patch.dict(os.environ, _clear_planner_env(), clear=True):
            adapter = agent_loop.make_planner_adapter()
        self.assertIsInstance(adapter, agent_loop.LocalPlannerAdapter)

    def test_blank_config_falls_back_to_local(self) -> None:
        env = _clear_planner_env()
        env[agent_loop.ENV_PLANNER_CMD] = ""
        with mock.patch.dict(os.environ, env, clear=True):
            adapter = agent_loop.make_planner_adapter()
        self.assertIsInstance(adapter, agent_loop.LocalPlannerAdapter)

    def test_whitespace_config_falls_back_to_local(self) -> None:
        env = _clear_planner_env()
        env[agent_loop.ENV_PLANNER_CMD] = "   \t  "
        with mock.patch.dict(os.environ, env, clear=True):
            adapter = agent_loop.make_planner_adapter()
        self.assertIsInstance(
            adapter, agent_loop.LocalPlannerAdapter,
            "an invalid (whitespace-only) command must fall back to local",
        )

    def test_nonblank_config_selects_subprocess_adapter(self) -> None:
        env = _clear_planner_env()
        env[agent_loop.ENV_PLANNER_CMD] = "my-planner --flag"
        with mock.patch.dict(os.environ, env, clear=True):
            adapter = agent_loop.make_planner_adapter()
        self.assertIsInstance(adapter, agent_loop.SubprocessPlannerAdapter)
        self.assertEqual(adapter.command, "my-planner --flag")
        self.assertEqual(adapter.name, "subprocess")


class LocalFallbackBehaviorTests(_SelectionTestCase):

    def test_local_fallback_preserves_success_behavior(self) -> None:
        # With no alternate configured, cmd_plan must behave exactly as the
        # in-process planner: a success writes proposed-phase.md.
        env = _clear_planner_env()
        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(
            agent_loop, "find_repo_root", return_value=self.repo.root
        ):
            rc = agent_loop.cmd_plan(argparse.Namespace())
        self.assertEqual(rc, 0)
        self.assertTrue((self.repo.root / agent_loop.PROPOSAL_PATH_REL).exists())


class SubprocessAdapterTests(_SelectionTestCase):

    def test_subprocess_adapter_passes_success_code_through(self) -> None:
        # Helper writes a proposal artifact (within the planner boundary)
        # and exits 0; the adapter must return 0.
        cmd = self._write_helper(
            "_fake_planner_ok.py",
            "import pathlib\n"
            "pathlib.Path('.agent-loop/proposed-phase.md')"
            ".write_text('alternate-adapter proposal\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n",
        )
        rc = agent_loop.SubprocessPlannerAdapter(cmd).run(self.repo.root)
        self.assertEqual(rc, 0)
        self.assertTrue(
            (self.repo.root / agent_loop.PROPOSAL_PATH_REL).exists(),
            "the alternate adapter ran the command with repo root as cwd",
        )

    def test_subprocess_adapter_passes_refusal_code_through(self) -> None:
        cmd = self._write_helper(
            "_fake_planner_refuse.py", "raise SystemExit(2)\n",
        )
        rc = agent_loop.SubprocessPlannerAdapter(cmd).run(self.repo.root)
        self.assertEqual(rc, 2, "a refusal exit code must pass through unchanged")

    def test_subprocess_adapter_maps_missing_shell_to_127(self) -> None:
        # If the platform shell itself cannot be launched, subprocess raises
        # FileNotFoundError; the adapter must map that to 127 rather than
        # propagating the exception.
        with mock.patch.object(
            agent_loop.subprocess, "run", side_effect=FileNotFoundError()
        ):
            rc = agent_loop.SubprocessPlannerAdapter("anything").run(self.repo.root)
        self.assertEqual(rc, 127)


class NoWideningSelectionTests(_SelectionTestCase):

    def _snapshot_markdown(self) -> dict:
        snap: dict = {}
        for rel in _ACTIVATION_OWNED_MARKDOWN:
            p = self.repo.root / rel
            snap[rel] = p.read_bytes() if p.is_file() else None
        return snap

    def test_alternate_adapter_plan_does_not_widen_writes(self) -> None:
        # Select the alternate adapter via the env var, run `plan`, and prove
        # the seam adds no activation-owned writes and does not touch
        # loop-state.json. The configured command writes only within the
        # planner boundary.
        cmd = self._write_helper(
            "_fake_planner_ok.py",
            "import pathlib\n"
            "pathlib.Path('.agent-loop/proposed-phase.md')"
            ".write_text('alternate-adapter proposal\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n",
        )
        before_md = self._snapshot_markdown()
        before_state = self.state_path.read_bytes()

        env = _clear_planner_env()
        env[agent_loop.ENV_PLANNER_CMD] = cmd
        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(
            agent_loop, "find_repo_root", return_value=self.repo.root
        ):
            rc = agent_loop.cmd_plan(argparse.Namespace())
        self.assertEqual(rc, 0)
        # Confirm the alternate adapter was actually selected and ran.
        self.assertTrue((self.repo.root / agent_loop.PROPOSAL_PATH_REL).exists())

        after_md = self._snapshot_markdown()
        for rel in _ACTIVATION_OWNED_MARKDOWN:
            self.assertEqual(
                before_md[rel], after_md[rel],
                f"adapter selection must not widen writes to {rel}",
            )
        self.assertEqual(
            before_state, self.state_path.read_bytes(),
            "the adapterized plan path must not write loop-state.json",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
