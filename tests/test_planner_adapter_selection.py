"""Focused tests for the Phase 4F planner-adapter SELECTION and write-boundary
enforcement behavior in `scripts/agent_loop.py`.

Phase 4E introduced the seam (`make_planner_adapter()` + `LocalPlannerAdapter`);
Phase 4F makes the seam selectable behind the `AGENT_LOOP_PLANNER_CMD` env var:

- statically-invalid configuration -> the default in-process
  `LocalPlannerAdapter` (the fallback), behavior unchanged. "Statically
  invalid" means unset, empty, whitespace-only, or unparseable (e.g. an
  unbalanced quote). A parseable-but-broken command is NOT a fallback case;
  it is selected and surfaced through its exit code or the boundary refusal.
- a statically-valid command -> exactly one alternate, the out-of-process
  `SubprocessPlannerAdapter`

The Phase 4F fix hardens the alternate adapter so it cannot violate the
planner write boundary: it snapshots the repo, runs the command, and if the
command left any change outside the allowed planner set
(`.agent-loop/proposed-phase.md`, `.agent-loop/planner.log`) - in particular
any activation-owned file - it rolls the repo back to the snapshot and fails
closed with exit 2. In-bound writes are kept and the exit code passes through.

These tests drive the REAL snapshot / detect / restore enforcement code on
real files, but stub `subprocess.run` so the "configured command" is a
deterministic in-process callable (it performs the file mutations a command
would, and returns a chosen exit code). This keeps the suite fast,
cross-platform, and free of real-subprocess-spawning flakiness while still
exercising the enforcement logic and asserting how the shell is invoked.
The synthetic repository reuses `test_planner._Repo` (a planner-success setup).
"""

from __future__ import annotations

import argparse
import os
import subprocess
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


def _fake_run(mutate=None, returncode: int = 0):
    """Build a stand-in for `subprocess.run` that simulates the configured
    command: it applies `mutate(cwd)` (the file writes a real command would
    perform) and returns a CompletedProcess with `returncode`. This lets the
    adapter's real snapshot / detect / rollback code run against real files
    without spawning a process."""

    def _run(command, **kwargs):
        if mutate is not None:
            mutate(Path(kwargs["cwd"]))
        return subprocess.CompletedProcess(command, returncode, "", "")

    return _run


def _write_proposal(root: Path) -> None:
    (root / ".agent-loop" / "proposed-phase.md").write_text(
        "alternate-adapter proposal\n", encoding="utf-8"
    )


class _SelectionTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = test_planner._Repo(Path(self._tmp.name))
        self.state_path = self.repo.root / ".agent-loop" / "loop-state.json"


# ----- selection / fallback -----

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


class InvalidConfigFallbackTests(_SelectionTestCase):

    def test_unparseable_command_falls_back_to_local(self) -> None:
        env = _clear_planner_env()
        env[agent_loop.ENV_PLANNER_CMD] = '"'  # unbalanced quote -> unparseable
        with mock.patch.dict(os.environ, env, clear=True):
            adapter = agent_loop.make_planner_adapter()
        self.assertIsInstance(
            adapter, agent_loop.LocalPlannerAdapter,
            "an unparseable command string must fall back to the local adapter",
        )

    def test_parseable_but_broken_command_still_selects_subprocess(self) -> None:
        env = _clear_planner_env()
        env[agent_loop.ENV_PLANNER_CMD] = "definitely-not-a-real-program-xyz --go"
        with mock.patch.dict(os.environ, env, clear=True):
            adapter = agent_loop.make_planner_adapter()
        self.assertIsInstance(adapter, agent_loop.SubprocessPlannerAdapter)

    def test_validity_helper_matches_contract(self) -> None:
        self.assertFalse(agent_loop._planner_command_is_valid(None))
        self.assertFalse(agent_loop._planner_command_is_valid(""))
        self.assertFalse(agent_loop._planner_command_is_valid("   \t "))
        self.assertFalse(agent_loop._planner_command_is_valid('"'))
        self.assertTrue(agent_loop._planner_command_is_valid("planner --x"))


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


# ----- alternate adapter: invocation + exit-code passthrough -----

class SubprocessAdapterTests(_SelectionTestCase):

    def test_invokes_shell_with_repo_root_cwd(self) -> None:
        with mock.patch.object(
            agent_loop.subprocess, "run",
            side_effect=_fake_run(mutate=_write_proposal, returncode=0),
        ) as m:
            rc = agent_loop.SubprocessPlannerAdapter("planner-cmd").run(self.repo.root)
        self.assertEqual(rc, 0)
        m.assert_called_once()
        _, kwargs = m.call_args
        self.assertTrue(kwargs["shell"])
        self.assertEqual(kwargs["cwd"], str(self.repo.root))
        self.assertTrue((self.repo.root / agent_loop.PROPOSAL_PATH_REL).exists())

    def test_passes_refusal_code_through(self) -> None:
        with mock.patch.object(
            agent_loop.subprocess, "run",
            side_effect=_fake_run(mutate=None, returncode=2),
        ):
            rc = agent_loop.SubprocessPlannerAdapter("planner-cmd").run(self.repo.root)
        self.assertEqual(rc, 2, "a refusal exit code must pass through unchanged")

    def test_maps_missing_shell_to_127(self) -> None:
        with mock.patch.object(
            agent_loop.subprocess, "run", side_effect=FileNotFoundError()
        ):
            rc = agent_loop.SubprocessPlannerAdapter("anything").run(self.repo.root)
        self.assertEqual(rc, 127)


# ----- alternate adapter: write-boundary enforcement -----

class BoundaryEnforcementTests(_SelectionTestCase):

    def _run_with_mutation(self, mutate, returncode: int = 0) -> int:
        with mock.patch.object(
            agent_loop.subprocess, "run",
            side_effect=_fake_run(mutate=mutate, returncode=returncode),
        ):
            return agent_loop.SubprocessPlannerAdapter("cmd").run(self.repo.root)

    def test_new_out_of_bound_file_fails_closed_and_is_removed(self) -> None:
        before = agent_loop._snapshot_repo_files(self.repo.root)

        def mutate(root: Path) -> None:
            _write_proposal(root)
            (root / "evil.txt").write_text("boom", encoding="utf-8")

        rc = self._run_with_mutation(mutate)
        self.assertEqual(rc, 2, "an out-of-bound write must fail closed (exit 2)")
        self.assertFalse(
            (self.repo.root / "evil.txt").exists(),
            "the out-of-bound file must be rolled back (removed)",
        )
        self.assertFalse(
            (self.repo.root / agent_loop.PROPOSAL_PATH_REL).exists(),
            "a violating run must not leave a partial proposal behind",
        )
        self.assertEqual(
            agent_loop._detect_out_of_bound_writes(self.repo.root, before), set(),
            "the in-scope repo must match the pre-run snapshot after rollback",
        )

    def test_activation_json_write_fails_closed(self) -> None:
        before_state = self.state_path.read_bytes()

        def mutate(root: Path) -> None:
            _write_proposal(root)
            (root / ".agent-loop" / "loop-state.json").write_text(
                "{}", encoding="utf-8"
            )

        rc = self._run_with_mutation(mutate)
        self.assertEqual(rc, 2)
        self.assertEqual(
            before_state, self.state_path.read_bytes(),
            "loop-state.json (activation-owned) must be rolled back unchanged",
        )

    def test_activation_markdown_write_fails_closed(self) -> None:
        before_task = (self.repo.root / "TASK.md").read_bytes()

        def mutate(root: Path) -> None:
            _write_proposal(root)
            (root / "TASK.md").write_text("# HACKED\n", encoding="utf-8")

        rc = self._run_with_mutation(mutate)
        self.assertEqual(rc, 2)
        self.assertEqual(
            before_task, (self.repo.root / "TASK.md").read_bytes(),
            "TASK.md (activation-owned) must be rolled back unchanged",
        )

    def test_violation_is_logged_to_planner_log(self) -> None:
        def mutate(root: Path) -> None:
            (root / "evil.txt").write_text("boom", encoding="utf-8")

        self._run_with_mutation(mutate)
        log = (self.repo.root / agent_loop.PLANNER_LOG_PATH_REL).read_text(
            encoding="utf-8"
        )
        self.assertIn("planner_write_boundary", log)
        self.assertIn("evil.txt", log)

    def test_in_bound_writes_are_kept(self) -> None:
        def mutate(root: Path) -> None:
            (root / ".agent-loop" / "proposed-phase.md").write_text(
                "p\n", encoding="utf-8"
            )
            (root / ".agent-loop" / "planner.log").write_text(
                "note: alt\n", encoding="utf-8"
            )

        rc = self._run_with_mutation(mutate, returncode=0)
        self.assertEqual(rc, 0)
        self.assertTrue((self.repo.root / agent_loop.PROPOSAL_PATH_REL).exists())
        self.assertIn(
            "note: alt",
            (self.repo.root / agent_loop.PLANNER_LOG_PATH_REL).read_text(
                encoding="utf-8"
            ),
        )


class SnapshotRollbackUnitTests(_SelectionTestCase):

    def test_detect_and_restore_roundtrip(self) -> None:
        root = self.repo.root
        snap = agent_loop._snapshot_repo_files(root)
        (root / "TASK.md").write_text("# changed\n", encoding="utf-8")
        (root / "newfile.txt").write_text("new", encoding="utf-8")

        violations = agent_loop._detect_out_of_bound_writes(root, snap)
        self.assertIn("TASK.md", violations)
        self.assertIn("newfile.txt", violations)

        agent_loop._restore_repo_files(root, snap)
        self.assertEqual((root / "TASK.md").read_bytes(), snap["TASK.md"])
        self.assertFalse((root / "newfile.txt").exists())

    def test_allowed_writes_are_not_violations(self) -> None:
        root = self.repo.root
        snap = agent_loop._snapshot_repo_files(root)
        (root / ".agent-loop" / "proposed-phase.md").write_text(
            "p\n", encoding="utf-8"
        )
        (root / ".agent-loop" / "planner.log").write_text(
            "note: x\n", encoding="utf-8"
        )
        self.assertEqual(
            agent_loop._detect_out_of_bound_writes(root, snap), set(),
            "writing only allowed planner files is not a boundary violation",
        )


# ----- selection through the `plan` and post-approval paths -----

class NoWideningSelectionTests(_SelectionTestCase):

    def _snapshot_markdown(self) -> dict:
        snap: dict = {}
        for rel in _ACTIVATION_OWNED_MARKDOWN:
            p = self.repo.root / rel
            snap[rel] = p.read_bytes() if p.is_file() else None
        return snap

    def test_alternate_adapter_plan_does_not_widen_writes(self) -> None:
        before_md = self._snapshot_markdown()
        before_state = self.state_path.read_bytes()

        env = _clear_planner_env()
        env[agent_loop.ENV_PLANNER_CMD] = "planner-cmd"
        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(
            agent_loop, "find_repo_root", return_value=self.repo.root
        ), mock.patch.object(
            agent_loop.subprocess, "run",
            side_effect=_fake_run(mutate=_write_proposal, returncode=0),
        ):
            rc = agent_loop.cmd_plan(argparse.Namespace())
        self.assertEqual(rc, 0)
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


class PostApprovalSelectionTests(_SelectionTestCase):

    def _log_path(self) -> Path:
        return self.repo.root / ".agent-loop" / "orchestrator.log"

    def test_post_approval_success_with_selection_active(self) -> None:
        env = _clear_planner_env()
        env[agent_loop.ENV_PLANNER_CMD] = "planner-cmd"
        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(
            agent_loop.subprocess, "run",
            side_effect=_fake_run(mutate=_write_proposal, returncode=0),
        ):
            rc = agent_loop._invoke_post_approval_planner(
                self.repo.root, self._log_path()
            )
        self.assertEqual(rc, 0)
        log = self._log_path().read_text(encoding="utf-8")
        self.assertIn("post-approval planner invoked", log)
        self.assertIn("planner_exit_code=0", log)

    def test_post_approval_boundary_violation_not_regressed(self) -> None:
        # With selection active, a boundary-violating command on the
        # post-approval path fails closed (exit 2 from the adapter) without
        # raising; the hook logs a normal exit code (not the exception
        # sentinel) and the activation-owned file is rolled back.
        before_task = (self.repo.root / "TASK.md").read_bytes()

        def mutate(root: Path) -> None:
            (root / "TASK.md").write_text("# HACKED\n", encoding="utf-8")

        env = _clear_planner_env()
        env[agent_loop.ENV_PLANNER_CMD] = "planner-cmd"
        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(
            agent_loop.subprocess, "run",
            side_effect=_fake_run(mutate=mutate, returncode=0),
        ):
            rc = agent_loop._invoke_post_approval_planner(
                self.repo.root, self._log_path()
            )
        self.assertEqual(rc, 2)
        self.assertNotEqual(rc, agent_loop.POST_APPROVAL_PLANNER_EXCEPTION_CODE)
        self.assertEqual(
            before_task, (self.repo.root / "TASK.md").read_bytes(),
            "post-approval boundary violation must roll back TASK.md",
        )
        log = self._log_path().read_text(encoding="utf-8")
        self.assertIn("post-approval planner invoked", log)
        self.assertIn("planner_exit_code=2", log)


if __name__ == "__main__":
    unittest.main(verbosity=2)
