"""Focused tests for the Phase 7B artifact-inspection layer.

Scope of this suite (Phase 7B, narrow):
- `INSPECTION_SIGNAL_VERSION`, `INSPECTION_ARTIFACTS`, and the four
  `INSPECTION_GROUP_*` constants are present and structured.
- `inspect_artifacts(repo_root)` returns one structured record per
  artifact in `INSPECTION_ARTIFACTS` (same order), records are dicts
  carrying `group`, `rel_path`, `present`, `size`, and `modified`,
  present artifacts get an integer size and ISO-8601 UTC mtime,
  missing artifacts get `present=False` with `size=None` and
  `modified=None`, the inspection is purely read-only (no canonical
  artifact mutated, no log file created), and the function never
  raises on a partially-populated workspace.
- `_render_inspection_table(...)` produces a deterministic header
  carrying the signal version, one line per record (present or
  missing), and a trailing summary line carrying total / present /
  missing counts.
- `cmd_inspect_artifacts` routes through `main(argv)` HANDLERS
  dispatch end-to-end, exits 0 regardless of which artifacts are
  present, prints to stdout only (never writes to
  `.agent-loop/orchestrator.log`), and never mutates any artifact
  on disk.
"""

from __future__ import annotations

import io
import json
import re
import sys
import unittest
import unittest.mock as mock
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory


HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
DOCS_CHECKLIST_PATH = HERE.parent / "docs" / "vscode-artifact-inspection-checklist.md"

import agent_loop  # noqa: E402 - sys.path is set above


ISO_UTC_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"
)


class _InspectionTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo_root = Path(self._tmp.name).resolve()
        (self.repo_root / ".agent-loop").mkdir(parents=True)

    def _write(self, rel_path: str, body: str) -> Path:
        # write_bytes (not write_text) so the on-disk size matches the
        # source string exactly. Windows' text-mode write would
        # otherwise expand `\n` to `\r\n` and throw off byte-size
        # assertions.
        p = self.repo_root / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(body.encode("utf-8"))
        return p

    def _snapshot(self) -> dict:
        snap: dict = {}
        for path in self.repo_root.rglob("*"):
            if path.is_file():
                rel = path.relative_to(self.repo_root).as_posix()
                snap[rel] = path.read_bytes()
        return snap


# ----- constants -----


class InspectionConstantsTests(unittest.TestCase):

    def test_signal_version_is_phase_7b_v1(self) -> None:
        self.assertEqual(
            agent_loop.INSPECTION_SIGNAL_VERSION, "phase-7b-v1",
        )

    def test_inspection_artifacts_is_non_empty_ordered_tuple(self) -> None:
        self.assertIsInstance(agent_loop.INSPECTION_ARTIFACTS, tuple)
        self.assertGreater(len(agent_loop.INSPECTION_ARTIFACTS), 0)

    def test_inspection_artifacts_cover_required_set(self) -> None:
        # The active prompt names the artifacts the inspection slice
        # must surface. This assertion locks them in so a regression
        # (a removed row) surfaces as a test failure rather than a
        # silently narrower inspector.
        required = {
            ".agent-loop/codex-review.md",
            ".agent-loop/fix-prompt.md",
            ".agent-loop/current-task.md",
            ".agent-loop/current-phase.md",
            ".agent-loop/git-status.log",
            ".agent-loop/git-diff.patch",
            ".agent-loop/test-output.log",
            ".agent-loop/lint-output.log",
            ".agent-loop/typecheck-output.log",
            ".agent-loop/build-output.log",
        }
        rel_paths = {
            rel for _grp, rel in agent_loop.INSPECTION_ARTIFACTS
        }
        missing = required - rel_paths
        self.assertEqual(
            missing, set(),
            f"INSPECTION_ARTIFACTS missing required entries: "
            f"{sorted(missing)}",
        )

    def test_every_group_in_records_is_a_known_group(self) -> None:
        known = set(agent_loop.INSPECTION_GROUPS)
        for grp, rel in agent_loop.INSPECTION_ARTIFACTS:
            self.assertIn(
                grp, known,
                f"row {rel!r} uses unknown group {grp!r}",
            )


class VscodeAcceptanceChecklistTests(unittest.TestCase):

    def test_checklist_exists(self) -> None:
        self.assertTrue(
            DOCS_CHECKLIST_PATH.is_file(),
            f"Expected Phase 7B checklist at {DOCS_CHECKLIST_PATH}",
        )

    def test_checklist_mentions_live_editor_checks(self) -> None:
        text = DOCS_CHECKLIST_PATH.read_text(encoding="utf-8")
        for required_snippet in (
            "Agent Loop: inspect artifacts",
            "clickable",
            "git-diff.patch",
            "current-task.md",
            "fix-prompt.md",
            "diff viewer",
            "file nesting",
        ):
            self.assertIn(
                required_snippet, text,
                f"checklist missing required live-editor check "
                f"{required_snippet!r}",
            )


# ----- inspect_artifacts library function -----


class InspectArtifactsLibraryTests(_InspectionTestCase):

    def test_returns_one_record_per_artifact_in_order(self) -> None:
        records = agent_loop.inspect_artifacts(self.repo_root)
        self.assertEqual(
            len(records), len(agent_loop.INSPECTION_ARTIFACTS),
        )
        for r, (grp, rel) in zip(
            records, agent_loop.INSPECTION_ARTIFACTS,
        ):
            self.assertEqual(r["group"], grp)
            self.assertEqual(r["rel_path"], rel)

    def test_missing_artifact_has_present_false_and_none_fields(
        self,
    ) -> None:
        records = agent_loop.inspect_artifacts(self.repo_root)
        for r in records:
            self.assertFalse(r["present"])
            self.assertIsNone(r["size"])
            self.assertIsNone(r["modified"])

    def test_present_artifact_has_size_and_iso_mtime(self) -> None:
        self._write(".agent-loop/codex-review.md", "verdict: x\n")
        records = agent_loop.inspect_artifacts(self.repo_root)
        review = next(
            r for r in records
            if r["rel_path"] == ".agent-loop/codex-review.md"
        )
        self.assertTrue(review["present"])
        self.assertIsInstance(review["size"], int)
        self.assertEqual(review["size"], len(b"verdict: x\n"))
        self.assertIsInstance(review["modified"], str)
        self.assertRegex(review["modified"], ISO_UTC_RE)

    def test_mixed_presence_is_reported_per_record(self) -> None:
        self._write(".agent-loop/fix-prompt.md", "fix instructions\n")
        records = agent_loop.inspect_artifacts(self.repo_root)
        by_rel = {r["rel_path"]: r for r in records}
        self.assertTrue(by_rel[".agent-loop/fix-prompt.md"]["present"])
        self.assertFalse(by_rel[".agent-loop/codex-review.md"]["present"])

    def test_inspect_does_not_mutate_any_artifact(self) -> None:
        self._write(".agent-loop/current-task.md", "task body\n")
        self._write(".agent-loop/git-status.log", "git status\n")
        before = self._snapshot()
        agent_loop.inspect_artifacts(self.repo_root)
        after = self._snapshot()
        self.assertEqual(before, after)

    def test_inspect_does_not_create_orchestrator_log(self) -> None:
        log_path = self.repo_root / ".agent-loop" / "orchestrator.log"
        self.assertFalse(log_path.exists())
        agent_loop.inspect_artifacts(self.repo_root)
        self.assertFalse(log_path.exists())


# ----- _render_inspection_table -----


class RenderInspectionTableTests(_InspectionTestCase):

    def test_header_carries_signal_version(self) -> None:
        records = agent_loop.inspect_artifacts(self.repo_root)
        text = agent_loop._render_inspection_table(records)
        self.assertIn(
            agent_loop.INSPECTION_SIGNAL_VERSION, text,
        )
        self.assertIn("Phase 7B artifact inspection", text)

    def test_every_record_renders_one_line(self) -> None:
        self._write(".agent-loop/codex-review.md", "x\n")
        records = agent_loop.inspect_artifacts(self.repo_root)
        text = agent_loop._render_inspection_table(records)
        for r in records:
            self.assertIn(r["rel_path"], text)

    def test_present_lines_carry_size_and_modified(self) -> None:
        self._write(".agent-loop/codex-review.md", "abc\n")
        records = agent_loop.inspect_artifacts(self.repo_root)
        text = agent_loop._render_inspection_table(records)
        review_line = next(
            line for line in text.splitlines()
            if ".agent-loop/codex-review.md" in line
            and "missing" not in line
        )
        self.assertIn("present", review_line)
        self.assertIn("size=4 bytes", review_line)
        self.assertIn("modified=", review_line)

    def test_missing_lines_say_missing(self) -> None:
        records = agent_loop.inspect_artifacts(self.repo_root)
        text = agent_loop._render_inspection_table(records)
        for r in records:
            line = next(
                ln for ln in text.splitlines()
                if r["rel_path"] in ln
            )
            self.assertIn("missing", line)

    def test_trailing_summary_line_carries_totals(self) -> None:
        self._write(".agent-loop/codex-review.md", "x\n")
        records = agent_loop.inspect_artifacts(self.repo_root)
        text = agent_loop._render_inspection_table(records)
        last = text.splitlines()[-1]
        self.assertIn(
            f"total={len(records)}", last,
        )
        self.assertIn("present=1", last)
        self.assertIn(
            f"missing={len(records) - 1}", last,
        )


# ----- cmd_inspect_artifacts via main(argv) -----


class CmdInspectArtifactsTests(_InspectionTestCase):

    def _run_main(self, argv) -> tuple:
        buf = io.StringIO()
        with mock.patch.object(
            agent_loop, "find_repo_root",
            return_value=self.repo_root,
        ):
            with redirect_stdout(buf):
                rc = agent_loop.main(argv)
        return rc, buf.getvalue()

    def test_cli_returns_zero_when_no_artifacts_present(self) -> None:
        rc, out = self._run_main(["inspect-artifacts"])
        self.assertEqual(rc, 0)
        self.assertIn(
            agent_loop.INSPECTION_SIGNAL_VERSION, out,
        )
        self.assertIn("missing", out)

    def test_cli_returns_zero_when_all_artifacts_present(self) -> None:
        for _grp, rel in agent_loop.INSPECTION_ARTIFACTS:
            self._write(rel, "body\n")
        rc, out = self._run_main(["inspect-artifacts"])
        self.assertEqual(rc, 0)
        self.assertIn("present", out)
        self.assertNotIn("missing", out.splitlines()[1])

    def test_cli_does_not_create_orchestrator_log(self) -> None:
        log_path = self.repo_root / ".agent-loop" / "orchestrator.log"
        self.assertFalse(log_path.exists())
        self._run_main(["inspect-artifacts"])
        self.assertFalse(log_path.exists())

    def test_cli_does_not_mutate_any_artifact(self) -> None:
        self._write(".agent-loop/codex-review.md", "v\n")
        self._write(".agent-loop/fix-prompt.md", "f\n")
        self._write(".agent-loop/loop-state.json", json.dumps({}))
        before = self._snapshot()
        self._run_main(["inspect-artifacts"])
        after = self._snapshot()
        self.assertEqual(before, after)

    def test_cli_routes_through_handlers_dispatch(self) -> None:
        # Defense in depth: prove the wiring goes through HANDLERS
        # rather than being a separate inspector that bypasses the
        # documented CLI surface.
        self.assertIn("inspect-artifacts", agent_loop.HANDLERS)
        self.assertIs(
            agent_loop.HANDLERS["inspect-artifacts"],
            agent_loop.cmd_inspect_artifacts,
        )

    def test_cli_output_paths_are_repo_relative(self) -> None:
        # Repo-relative paths make the VS Code terminal auto-linkify
        # the artifact rows. An absolute path would break that and
        # would also leak the operator's home dir.
        self._write(".agent-loop/codex-review.md", "x\n")
        rc, out = self._run_main(["inspect-artifacts"])
        self.assertEqual(rc, 0)
        self.assertNotIn(str(self.repo_root), out)


if __name__ == "__main__":
    unittest.main()
