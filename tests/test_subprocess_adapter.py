"""Fix Phase A - Automatic Local Claude/Codex Invocation Reliability.

Focused tests for the subprocess adapter contract documented in
`docs/local-adapter-contract.md`. The suite exercises the four
required behaviors enumerated in the Codex review for this slice:

  1. missing binaries / launch failures (FileNotFoundError -> exit 127)
  2. wrapper commands that exit 0 without writing the target artifact
  3. wrapper commands that exit 0 but leave the target artifact with a
     stale or backdated mtime (mtime <= prev_mtime); both
     SubprocessClaudeAdapter and SubprocessCodexAdapter MUST reject
     these as stale/no-op invocations
  4. the orchestrator runs the wrapper with cwd set to the repo root
     (the directory containing the canonical artifact's parent)

All tests are self-contained, run against a TemporaryDirectory, and
do NOT mutate any real on-disk state.
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock


HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import agent_loop  # noqa: E402


def _make_repo(td: Path) -> tuple[Path, Path, Path]:
    """Set up a minimal controller-root layout the adapter can act on.

    Returns `(repo_root, summary_path, review_path)`.
    """
    (td / ".agent-loop").mkdir(parents=True, exist_ok=True)
    summary_path = td / ".agent-loop" / "claude-summary.md"
    review_path = td / ".agent-loop" / "codex-review.md"
    prompt_path = td / ".agent-loop" / "claude-prompt.md"
    prompt_path.write_text("# Active prompt\n", encoding="utf-8")
    return td, summary_path, review_path


# ---------------------------------------------------------------------------
# Issue 3 / case 1: missing binaries / launch failures
# ---------------------------------------------------------------------------
class MissingBinaryTests(unittest.TestCase):
    """A configured wrapper command that the platform shell cannot
    locate (FileNotFoundError) MUST return exit code 127 so the
    orchestrator halts via its existing `halted_input_missing` branch.
    """

    def test_claude_adapter_returns_127_on_FileNotFoundError(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            repo, summary, _ = _make_repo(Path(td))
            prompt = repo / ".agent-loop" / "claude-prompt.md"
            adapter = agent_loop.SubprocessClaudeAdapter(
                command="this-binary-does-not-exist-xyzzy",
            )
            with mock.patch.object(
                agent_loop.subprocess,
                "run",
                side_effect=FileNotFoundError(
                    "no such file: this-binary-does-not-exist-xyzzy",
                ),
            ):
                result = adapter.invoke(prompt, summary)
            self.assertEqual(result.exit_code, 127)
            self.assertIsNone(result.model_id)

    def test_codex_adapter_returns_127_on_FileNotFoundError(self) -> None:
        with TemporaryDirectory() as td:
            _, _, review = _make_repo(Path(td))
            adapter = agent_loop.SubprocessCodexAdapter(
                command="this-binary-does-not-exist-xyzzy",
            )
            with mock.patch.object(
                agent_loop.subprocess,
                "run",
                side_effect=FileNotFoundError(
                    "no such file: this-binary-does-not-exist-xyzzy",
                ),
            ):
                result = adapter.wait_for_review(review)
            self.assertEqual(result.exit_code, 127)
            self.assertIsNone(result.model_id)


# ---------------------------------------------------------------------------
# Issue 3 / case 2: wrapper exits 0 without writing the artifact
# ---------------------------------------------------------------------------
class SuccessfulExitButNoWriteTests(unittest.TestCase):
    """A wrapper that exits 0 but does NOT cause the target canonical
    artifact to be written is treated as a wrapper failure: the
    adapter returns a non-zero exit code so the orchestrator halts
    rather than treating a missing artifact as a fresh write.
    """

    def test_claude_adapter_rejects_zero_exit_with_missing_summary(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            repo, summary, _ = _make_repo(Path(td))
            prompt = repo / ".agent-loop" / "claude-prompt.md"
            # summary file intentionally absent
            self.assertFalse(summary.exists())
            adapter = agent_loop.SubprocessClaudeAdapter(
                command="echo no-write",
            )
            completed = mock.Mock(returncode=0, stdout="", stderr="")
            with mock.patch.object(
                agent_loop.subprocess, "run", return_value=completed,
            ):
                result = adapter.invoke(prompt, summary)
            self.assertNotEqual(result.exit_code, 0)
            self.assertIsNone(result.model_id)
            # Adapter did NOT fabricate the artifact.
            self.assertFalse(summary.exists())

    def test_codex_adapter_rejects_zero_exit_with_missing_review(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            _, _, review = _make_repo(Path(td))
            self.assertFalse(review.exists())
            adapter = agent_loop.SubprocessCodexAdapter(
                command="echo no-write",
            )
            completed = mock.Mock(returncode=0, stdout="", stderr="")
            with mock.patch.object(
                agent_loop.subprocess, "run", return_value=completed,
            ):
                result = adapter.wait_for_review(review)
            self.assertNotEqual(result.exit_code, 0)
            self.assertIsNone(result.model_id)
            self.assertFalse(review.exists())


# ---------------------------------------------------------------------------
# Issue 3 / case 3: stale / backdated artifact writes
# ---------------------------------------------------------------------------
class StaleArtifactRejectionTests(unittest.TestCase):
    """A wrapper that exits 0 and the target artifact exists, but the
    artifact's mtime is <= the pre-invocation snapshot mtime, MUST be
    refused as a stale/no-op invocation. This is the new Fix Phase A
    freshness rule: mtime must STRICTLY ADVANCE; merely differing is
    not enough (a backdated rewrite differs but is older).
    """

    def test_claude_adapter_rejects_unchanged_summary_mtime(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            repo, summary, _ = _make_repo(Path(td))
            prompt = repo / ".agent-loop" / "claude-prompt.md"
            summary.write_text("# stale summary\n", encoding="utf-8")
            prev_mtime = summary.stat().st_mtime
            adapter = agent_loop.SubprocessClaudeAdapter(
                command="echo no-touch",
            )
            completed = mock.Mock(returncode=0, stdout="", stderr="")
            with mock.patch.object(
                agent_loop.subprocess, "run", return_value=completed,
            ):
                result = adapter.invoke(prompt, summary)
            # mtime unchanged across the call -> failure
            self.assertEqual(summary.stat().st_mtime, prev_mtime)
            self.assertNotEqual(result.exit_code, 0)

    def test_claude_adapter_rejects_backdated_summary_mtime(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            repo, summary, _ = _make_repo(Path(td))
            prompt = repo / ".agent-loop" / "claude-prompt.md"
            summary.write_text("# current summary\n", encoding="utf-8")
            prev_mtime = summary.stat().st_mtime
            adapter = agent_loop.SubprocessClaudeAdapter(
                command="echo backdates",
            )
            completed = mock.Mock(returncode=0, stdout="", stderr="")

            def _run_then_backdate(*args, **kwargs):
                # The "wrapper" rewrites the artifact with a backdated
                # mtime (e.g. a buggy wrapper that touches the file to
                # an older timestamp, or a wrapper that restores from a
                # backup).
                summary.write_text(
                    "# backdated summary\n", encoding="utf-8",
                )
                os.utime(summary, (prev_mtime - 60, prev_mtime - 60))
                return completed

            with mock.patch.object(
                agent_loop.subprocess, "run",
                side_effect=_run_then_backdate,
            ):
                result = adapter.invoke(prompt, summary)
            # Post-call mtime is < prev_mtime; the differs-but-older
            # case the pre-Fix-Phase-A code would have accepted.
            self.assertLess(summary.stat().st_mtime, prev_mtime)
            self.assertNotEqual(
                result.exit_code, 0,
                "subprocess Claude adapter accepted a backdated "
                "artifact rewrite; the Fix Phase A freshness rule "
                "requires mtime to STRICTLY ADVANCE",
            )

    def test_codex_adapter_rejects_unchanged_review_mtime(self) -> None:
        with TemporaryDirectory() as td:
            _, _, review = _make_repo(Path(td))
            review.write_text("# stale review\n", encoding="utf-8")
            prev_mtime = review.stat().st_mtime
            adapter = agent_loop.SubprocessCodexAdapter(
                command="echo no-touch",
            )
            completed = mock.Mock(returncode=0, stdout="", stderr="")
            with mock.patch.object(
                agent_loop.subprocess, "run", return_value=completed,
            ):
                result = adapter.wait_for_review(review)
            self.assertEqual(review.stat().st_mtime, prev_mtime)
            self.assertNotEqual(result.exit_code, 0)

    def test_codex_adapter_rejects_backdated_review_mtime(self) -> None:
        with TemporaryDirectory() as td:
            _, _, review = _make_repo(Path(td))
            review.write_text("# current review\n", encoding="utf-8")
            prev_mtime = review.stat().st_mtime
            adapter = agent_loop.SubprocessCodexAdapter(
                command="echo backdates",
            )
            completed = mock.Mock(returncode=0, stdout="", stderr="")

            def _run_then_backdate(*args, **kwargs):
                review.write_text(
                    "# backdated review\n", encoding="utf-8",
                )
                os.utime(review, (prev_mtime - 60, prev_mtime - 60))
                return completed

            with mock.patch.object(
                agent_loop.subprocess, "run",
                side_effect=_run_then_backdate,
            ):
                result = adapter.wait_for_review(review)
            self.assertLess(review.stat().st_mtime, prev_mtime)
            self.assertNotEqual(
                result.exit_code, 0,
                "subprocess Codex adapter accepted a backdated "
                "artifact rewrite; the Fix Phase A freshness rule "
                "requires mtime to STRICTLY ADVANCE",
            )


# ---------------------------------------------------------------------------
# Issue 3 / case 4: cwd / repo-root assumption for configured wrappers
# ---------------------------------------------------------------------------
class CwdAssumptionTests(unittest.TestCase):
    """The orchestrator invokes the wrapper with cwd set to the repo
    root - specifically, the directory containing the canonical
    artifact's parent (`.agent-loop/`). The wrapper can therefore
    rely on `.agent-loop/claude-summary.md` and friends resolving
    against the repo root, exactly as documented in
    docs/local-adapter-contract.md.
    """

    def test_claude_adapter_runs_wrapper_with_repo_root_cwd(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            repo, summary, _ = _make_repo(Path(td))
            prompt = repo / ".agent-loop" / "claude-prompt.md"
            adapter = agent_loop.SubprocessClaudeAdapter(
                command="echo cwd-check",
            )
            captured_kwargs: dict = {}
            completed = mock.Mock(returncode=0, stdout="", stderr="")

            def _capture_and_write(*args, **kwargs):
                captured_kwargs.update(kwargs)
                # Wrapper "writes" the artifact so the freshness
                # check passes for this cwd-shape test.
                summary.write_text(
                    "# fresh summary\n", encoding="utf-8",
                )
                os.utime(summary, None)
                return completed

            with mock.patch.object(
                agent_loop.subprocess, "run",
                side_effect=_capture_and_write,
            ):
                result = adapter.invoke(prompt, summary)
            self.assertEqual(result.exit_code, 0)
            # The orchestrator computes cwd as `prompt.parent.parent`
            # (the `.agent-loop` directory's parent = the repo root).
            self.assertEqual(
                Path(captured_kwargs["cwd"]).resolve(),
                repo.resolve(),
                "subprocess Claude adapter did not set cwd to the "
                "repo root; the wrapper contract assumes "
                "`.agent-loop/claude-summary.md` resolves against "
                "the repo root",
            )

    def test_codex_adapter_runs_wrapper_with_repo_root_cwd(self) -> None:
        with TemporaryDirectory() as td:
            repo, _, review = _make_repo(Path(td))
            adapter = agent_loop.SubprocessCodexAdapter(
                command="echo cwd-check",
            )
            captured_kwargs: dict = {}
            completed = mock.Mock(returncode=0, stdout="", stderr="")

            def _capture_and_write(*args, **kwargs):
                captured_kwargs.update(kwargs)
                review.write_text(
                    "# fresh review\n", encoding="utf-8",
                )
                os.utime(review, None)
                return completed

            with mock.patch.object(
                agent_loop.subprocess, "run",
                side_effect=_capture_and_write,
            ):
                result = adapter.wait_for_review(review)
            self.assertEqual(result.exit_code, 0)
            self.assertEqual(
                Path(captured_kwargs["cwd"]).resolve(),
                repo.resolve(),
                "subprocess Codex adapter did not set cwd to the "
                "repo root",
            )

    def test_claude_adapter_pipes_prompt_text_on_stdin(self) -> None:
        # The Claude adapter contract pipes the active prompt text on
        # stdin so a wrapper can read it without re-opening the file.
        with TemporaryDirectory() as td:
            repo, summary, _ = _make_repo(Path(td))
            prompt = repo / ".agent-loop" / "claude-prompt.md"
            prompt.write_text(
                "# prompt body for stdin test\n", encoding="utf-8",
            )
            adapter = agent_loop.SubprocessClaudeAdapter(
                command="cat",
            )
            captured_kwargs: dict = {}
            completed = mock.Mock(returncode=0, stdout="", stderr="")

            def _capture_and_write(*args, **kwargs):
                captured_kwargs.update(kwargs)
                summary.write_text(
                    "# fresh summary\n", encoding="utf-8",
                )
                os.utime(summary, None)
                return completed

            with mock.patch.object(
                agent_loop.subprocess, "run",
                side_effect=_capture_and_write,
            ):
                adapter.invoke(prompt, summary)
            self.assertEqual(
                captured_kwargs["input"],
                "# prompt body for stdin test\n",
                "subprocess Claude adapter did not pipe the active "
                "prompt text on stdin per the adapter contract",
            )

    def test_codex_adapter_pipes_empty_stdin(self) -> None:
        # The Codex adapter contract pipes empty stdin; Codex reads
        # .agent-loop/ artifacts directly.
        with TemporaryDirectory() as td:
            _, _, review = _make_repo(Path(td))
            adapter = agent_loop.SubprocessCodexAdapter(
                command="cat",
            )
            captured_kwargs: dict = {}
            completed = mock.Mock(returncode=0, stdout="", stderr="")

            def _capture_and_write(*args, **kwargs):
                captured_kwargs.update(kwargs)
                review.write_text(
                    "# fresh review\n", encoding="utf-8",
                )
                os.utime(review, None)
                return completed

            with mock.patch.object(
                agent_loop.subprocess, "run",
                side_effect=_capture_and_write,
            ):
                adapter.wait_for_review(review)
            self.assertEqual(
                captured_kwargs["input"], "",
                "subprocess Codex adapter did not pipe empty stdin "
                "per the adapter contract",
            )


# ---------------------------------------------------------------------------
# Factory selection
# ---------------------------------------------------------------------------
class AdapterFactorySelectionTests(unittest.TestCase):
    """Sanity checks for the manual-handoff fallback path. When
    AGENT_LOOP_*_CMD is unset the factory returns the manual-handoff
    adapter; setting it returns the subprocess adapter. The Fix Phase A
    work preserves the manual-handoff fallback verbatim.
    """

    def test_manual_handoff_when_claude_cmd_unset(self) -> None:
        with mock.patch.dict(
            os.environ, {}, clear=False,
        ):
            os.environ.pop(agent_loop.ENV_CLAUDE_CMD, None)
            adapter = agent_loop.make_claude_adapter()
            self.assertIsInstance(
                adapter, agent_loop.ManualHandoffClaudeAdapter,
            )

    def test_subprocess_when_claude_cmd_set(self) -> None:
        with mock.patch.dict(
            os.environ,
            {agent_loop.ENV_CLAUDE_CMD: "echo hi"},
        ):
            adapter = agent_loop.make_claude_adapter()
            self.assertIsInstance(
                adapter, agent_loop.SubprocessClaudeAdapter,
            )

    def test_manual_handoff_when_codex_cmd_unset(self) -> None:
        with mock.patch.dict(
            os.environ, {}, clear=False,
        ):
            os.environ.pop(agent_loop.ENV_CODEX_CMD, None)
            adapter = agent_loop.make_codex_adapter()
            self.assertIsInstance(
                adapter, agent_loop.ManualHandoffCodexAdapter,
            )

    def test_subprocess_when_codex_cmd_set(self) -> None:
        with mock.patch.dict(
            os.environ,
            {agent_loop.ENV_CODEX_CMD: "echo hi"},
        ):
            adapter = agent_loop.make_codex_adapter()
            self.assertIsInstance(
                adapter, agent_loop.SubprocessCodexAdapter,
            )


if __name__ == "__main__":
    unittest.main()
