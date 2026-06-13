"""Focused tests for the Phase 6J optional-context file loading slice.

Scope of this suite (Phase 6J, narrow):
- `load_optional_context(repo_root, *, declared_paths, max_files,
  max_bytes_per_file, log_path)` reads an EXPLICITLY DECLARED list of
  in-repo file paths and returns a structured advisory-only payload.
- Each per-file dict carries `advisory_only = True`, the original
  declared `source_path`, `byte_size_on_disk`, `excerpt`,
  `excerpt_byte_size`, and a `truncated` flag.
- Refusal modes (all `halted_input_missing`): empty / non-list
  `declared_paths`, too many files relative to `max_files`,
  non-string / empty / absolute / glob-bearing / `..`-resolving /
  out-of-repo / duplicate paths, missing / directory / unreadable
  files, out-of-bound `max_files` (zero / negative / non-int / bool /
  above the cap), out-of-bound `max_bytes_per_file` (same shape).
- Canonical-precedence preservation: loading does NOT mutate
  `loop-state.json`, does NOT mutate any source file, does NOT
  create the output artifact (only the CLI handler does), and the
  `canonical_precedence_note` is the literal named constant.
- The `load-optional-context` CLI subcommand routes through
  `main(argv)` HANDLERS dispatch and writes the JSON payload to
  `.agent-loop/optional-context.json` (or the `--output` path).

This slice does not implement glob expansion, semantic retrieval,
arbitrary repo-file ingestion, framework-backed runtime paths, or any
widening of Phase 5 autonomy.
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

import agent_loop  # noqa: E402 - sys.path is set above


class _OptionalContextTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo_root = Path(self._tmp.name).resolve()
        self.al = self.repo_root / ".agent-loop"
        self.al.mkdir(parents=True, exist_ok=True)
        self.log_path = self.al / "orchestrator.log"
        self.output_default = (
            self.repo_root / agent_loop.OPTIONAL_CONTEXT_OUTPUT_REL
        )

    def _plant(self, rel: str, content: str) -> Path:
        p = self.repo_root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return p


# ----- load_optional_context: success shape -----


class LoadOptionalContextSuccessShapeTests(_OptionalContextTestCase):

    def test_single_path_returns_structured_payload(self) -> None:
        self._plant("docs/architecture.md", "architecture body")
        ctx = agent_loop.load_optional_context(
            self.repo_root,
            declared_paths=["docs/architecture.md"],
            log_path=self.log_path,
        )
        for key in (
            "context_signal_version", "loaded_at",
            "max_files_applied", "max_bytes_per_file_applied",
            "declared_paths", "files",
            "canonical_precedence_note",
        ):
            self.assertIn(key, ctx)
        self.assertEqual(
            ctx["context_signal_version"],
            agent_loop.OPTIONAL_CONTEXT_SIGNAL_VERSION,
        )
        self.assertEqual(ctx["declared_paths"], ["docs/architecture.md"])
        self.assertEqual(len(ctx["files"]), 1)
        entry = ctx["files"][0]
        self.assertEqual(entry["source_path"], "docs/architecture.md")
        self.assertEqual(entry["excerpt"], "architecture body")
        self.assertEqual(entry["byte_size_on_disk"], len("architecture body"))
        self.assertFalse(entry["truncated"])
        self.assertTrue(entry["advisory_only"])
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("optional-context loaded:", log_text)

    def test_multiple_paths_preserve_declaration_order(self) -> None:
        self._plant("a.txt", "a")
        self._plant("b.txt", "b")
        self._plant("c.txt", "c")
        ctx = agent_loop.load_optional_context(
            self.repo_root,
            declared_paths=["b.txt", "a.txt", "c.txt"],
        )
        ordered_paths = [f["source_path"] for f in ctx["files"]]
        self.assertEqual(ordered_paths, ["b.txt", "a.txt", "c.txt"])

    def test_canonical_precedence_note_is_literal_constant(self) -> None:
        self._plant("a.txt", "ok")
        ctx = agent_loop.load_optional_context(
            self.repo_root, declared_paths=["a.txt"],
        )
        self.assertIs(
            ctx["canonical_precedence_note"],
            agent_loop.OPTIONAL_CONTEXT_CANONICAL_PRECEDENCE_NOTE,
        )

    def test_default_limits_recorded_on_payload(self) -> None:
        self._plant("a.txt", "ok")
        ctx = agent_loop.load_optional_context(
            self.repo_root, declared_paths=["a.txt"],
        )
        self.assertEqual(
            ctx["max_files_applied"],
            agent_loop.OPTIONAL_CONTEXT_DEFAULT_MAX_FILES,
        )
        self.assertEqual(
            ctx["max_bytes_per_file_applied"],
            agent_loop.OPTIONAL_CONTEXT_DEFAULT_BYTES_PER_FILE,
        )


# ----- load_optional_context: bounded excerpts -----


class LoadOptionalContextBoundsTests(_OptionalContextTestCase):

    def test_file_over_limit_is_truncated_with_flag_set(self) -> None:
        self._plant("big.txt", "X" * 200)
        ctx = agent_loop.load_optional_context(
            self.repo_root,
            declared_paths=["big.txt"],
            max_bytes_per_file=50,
        )
        entry = ctx["files"][0]
        self.assertEqual(entry["byte_size_on_disk"], 200)
        self.assertEqual(entry["excerpt_byte_size"], 50)
        self.assertEqual(entry["excerpt"], "X" * 50)
        self.assertTrue(entry["truncated"])

    def test_file_under_limit_is_not_marked_truncated(self) -> None:
        self._plant("small.txt", "abcdef")
        ctx = agent_loop.load_optional_context(
            self.repo_root,
            declared_paths=["small.txt"],
            max_bytes_per_file=1024,
        )
        entry = ctx["files"][0]
        self.assertFalse(entry["truncated"])
        self.assertEqual(entry["excerpt"], "abcdef")

    def test_refuses_when_declared_paths_exceeds_max_files(self) -> None:
        for i in range(3):
            self._plant(f"f{i}.txt", f"body {i}")
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.load_optional_context(
                self.repo_root,
                declared_paths=["f0.txt", "f1.txt", "f2.txt"],
                max_files=2,
            )
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("max_files", cm.exception.reason)

    def test_refuses_on_max_files_zero(self) -> None:
        self._plant("a.txt", "ok")
        with self.assertRaises(agent_loop.HaltError):
            agent_loop.load_optional_context(
                self.repo_root,
                declared_paths=["a.txt"],
                max_files=0,
            )

    def test_refuses_on_max_files_above_cap(self) -> None:
        self._plant("a.txt", "ok")
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.load_optional_context(
                self.repo_root,
                declared_paths=["a.txt"],
                max_files=agent_loop.OPTIONAL_CONTEXT_MAX_MAX_FILES + 1,
            )
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn(
            "OPTIONAL_CONTEXT_MAX_MAX_FILES", cm.exception.reason,
        )

    def test_refuses_on_max_files_bool(self) -> None:
        self._plant("a.txt", "ok")
        with self.assertRaises(agent_loop.HaltError):
            agent_loop.load_optional_context(
                self.repo_root,
                declared_paths=["a.txt"],
                max_files=True,
            )

    def test_refuses_on_max_bytes_zero(self) -> None:
        self._plant("a.txt", "ok")
        with self.assertRaises(agent_loop.HaltError):
            agent_loop.load_optional_context(
                self.repo_root,
                declared_paths=["a.txt"],
                max_bytes_per_file=0,
            )

    def test_refuses_on_max_bytes_above_cap(self) -> None:
        self._plant("a.txt", "ok")
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.load_optional_context(
                self.repo_root,
                declared_paths=["a.txt"],
                max_bytes_per_file=(
                    agent_loop.OPTIONAL_CONTEXT_MAX_BYTES_PER_FILE + 1
                ),
            )
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn(
            "OPTIONAL_CONTEXT_MAX_BYTES_PER_FILE",
            cm.exception.reason,
        )

    def test_refuses_on_max_bytes_bool(self) -> None:
        self._plant("a.txt", "ok")
        with self.assertRaises(agent_loop.HaltError):
            agent_loop.load_optional_context(
                self.repo_root,
                declared_paths=["a.txt"],
                max_bytes_per_file=True,
            )


# ----- load_optional_context: declaration & path validation -----


class LoadOptionalContextPathValidationTests(_OptionalContextTestCase):

    def test_refuses_empty_declared_paths(self) -> None:
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.load_optional_context(
                self.repo_root, declared_paths=[],
            )
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("empty", cm.exception.reason)

    def test_refuses_non_list_declared_paths(self) -> None:
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.load_optional_context(
                self.repo_root, declared_paths="not-a-list",
            )
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("must be a list", cm.exception.reason)

    def test_refuses_non_string_path_entry(self) -> None:
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.load_optional_context(
                self.repo_root, declared_paths=[12345],
            )
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("must be a string", cm.exception.reason)

    def test_refuses_empty_string_path_entry(self) -> None:
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.load_optional_context(
                self.repo_root, declared_paths=[""],
            )
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("non-empty", cm.exception.reason)

    def test_refuses_absolute_path(self) -> None:
        absolute = (self.repo_root / "a.txt").resolve()
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.load_optional_context(
                self.repo_root, declared_paths=[str(absolute)],
            )
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("absolute", cm.exception.reason)

    def test_refuses_path_with_glob_star(self) -> None:
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.load_optional_context(
                self.repo_root, declared_paths=["docs/*.md"],
            )
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("glob", cm.exception.reason)

    def test_refuses_path_with_glob_question(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            agent_loop.load_optional_context(
                self.repo_root, declared_paths=["docs/a?.md"],
            )

    def test_refuses_path_with_glob_bracket(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            agent_loop.load_optional_context(
                self.repo_root, declared_paths=["docs/[abc].md"],
            )

    def test_refuses_path_resolving_outside_repo_via_dotdot(self) -> None:
        # The repo_root is `self._tmp.name`; `..` escapes to its
        # parent, which is outside repo_root. Refused fail-closed.
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.load_optional_context(
                self.repo_root, declared_paths=["../outside.txt"],
            )
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("outside the repo root", cm.exception.reason)

    def test_refuses_duplicate_paths(self) -> None:
        self._plant("a.txt", "ok")
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.load_optional_context(
                self.repo_root, declared_paths=["a.txt", "a.txt"],
            )
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("more than once", cm.exception.reason)

    def test_refuses_missing_file(self) -> None:
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.load_optional_context(
                self.repo_root, declared_paths=["missing.txt"],
            )
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("does not exist", cm.exception.reason)

    def test_refuses_directory_not_file(self) -> None:
        (self.repo_root / "docs").mkdir(parents=True, exist_ok=True)
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.load_optional_context(
                self.repo_root, declared_paths=["docs"],
            )
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("not a regular file", cm.exception.reason)

    def test_refuses_unreadable_file(self) -> None:
        # Mock Path.read_bytes to raise OSError for one declared path.
        self._plant("a.txt", "ok")
        target = (self.repo_root / "a.txt").resolve()
        real_read_bytes = Path.read_bytes

        def _side_effect(self_path: Path, *args, **kwargs):
            if self_path.resolve() == target:
                raise OSError("simulated read failure")
            return real_read_bytes(self_path, *args, **kwargs)

        with mock.patch.object(Path, "read_bytes", _side_effect):
            with self.assertRaises(agent_loop.HaltError) as cm:
                agent_loop.load_optional_context(
                    self.repo_root, declared_paths=["a.txt"],
                )
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("unreadable", cm.exception.reason)


# ----- load_optional_context: canonical-precedence -----


class LoadOptionalContextCanonicalPrecedenceTests(
    _OptionalContextTestCase,
):

    def test_loading_does_not_create_output_artifact(self) -> None:
        # The library function never writes the audit artifact; only
        # the CLI handler does. Pins the library / handler split.
        self._plant("a.txt", "ok")
        agent_loop.load_optional_context(
            self.repo_root, declared_paths=["a.txt"],
        )
        self.assertFalse(self.output_default.exists())

    def test_loading_does_not_mutate_source_files(self) -> None:
        path = self._plant("a.txt", "ok")
        before = path.read_bytes()
        agent_loop.load_optional_context(
            self.repo_root, declared_paths=["a.txt"],
        )
        self.assertEqual(path.read_bytes(), before)

    def test_advisory_only_marker_on_every_loaded_file(self) -> None:
        self._plant("a.txt", "1")
        self._plant("b.txt", "2")
        self._plant("c.txt", "3")
        ctx = agent_loop.load_optional_context(
            self.repo_root,
            declared_paths=["a.txt", "b.txt", "c.txt"],
        )
        for entry in ctx["files"]:
            self.assertTrue(entry["advisory_only"])

    def test_audit_log_not_appended_when_log_path_omitted(self) -> None:
        self._plant("a.txt", "ok")
        before = (
            self.log_path.read_bytes() if self.log_path.exists() else b""
        )
        agent_loop.load_optional_context(
            self.repo_root, declared_paths=["a.txt"],
        )
        after = (
            self.log_path.read_bytes() if self.log_path.exists() else b""
        )
        self.assertEqual(before, after)


# ----- cmd_load_optional_context + main(argv) -----


class CmdLoadOptionalContextTests(_OptionalContextTestCase):

    def _run_main(self, argv) -> int:
        with mock.patch.object(
            agent_loop, "find_repo_root", return_value=self.repo_root,
        ):
            return agent_loop.main(argv)

    def test_cli_writes_default_output_artifact(self) -> None:
        self._plant("docs/notes.md", "notes")
        rc = self._run_main([
            "load-optional-context",
            "--declared-path", "docs/notes.md",
        ])
        self.assertEqual(rc, 0)
        self.assertTrue(self.output_default.is_file())
        payload = json.loads(self.output_default.read_text(encoding="utf-8"))
        self.assertEqual(
            payload["context_signal_version"],
            agent_loop.OPTIONAL_CONTEXT_SIGNAL_VERSION,
        )
        self.assertEqual(payload["declared_paths"], ["docs/notes.md"])
        self.assertEqual(len(payload["files"]), 1)

    def test_cli_honors_multiple_declared_paths_in_order(self) -> None:
        self._plant("a.txt", "a")
        self._plant("b.txt", "b")
        rc = self._run_main([
            "load-optional-context",
            "--declared-path", "b.txt",
            "--declared-path", "a.txt",
        ])
        self.assertEqual(rc, 0)
        payload = json.loads(self.output_default.read_text(encoding="utf-8"))
        self.assertEqual(payload["declared_paths"], ["b.txt", "a.txt"])

    def test_cli_honors_explicit_output_override(self) -> None:
        self._plant("a.txt", "ok")
        # Phase 6J fix: --output must be repo-relative and stay inside
        # the repo root. The handler resolves the path under repo_root.
        rel = ".agent-loop/custom-context.json"
        custom = self.repo_root / rel
        rc = self._run_main([
            "load-optional-context",
            "--declared-path", "a.txt",
            "--output", rel,
        ])
        self.assertEqual(rc, 0)
        self.assertTrue(custom.is_file())
        self.assertFalse(self.output_default.exists())

    def test_cli_refuses_absolute_output_path(self) -> None:
        # Phase 6J fix: an absolute --output is refused fail-closed
        # through the existing HaltError / _halt flow. The artifact
        # must not be written.
        self._plant("a.txt", "ok")
        absolute = (self.repo_root / "elsewhere.json").resolve()
        self.assertTrue(absolute.is_absolute())
        rc = self._run_main([
            "load-optional-context",
            "--declared-path", "a.txt",
            "--output", str(absolute),
        ])
        self.assertEqual(rc, 2)
        self.assertFalse(absolute.exists())
        self.assertFalse(self.output_default.exists())

    def test_cli_refuses_output_path_escaping_repo_via_dotdot(
        self,
    ) -> None:
        # Phase 6J fix: a relative --output that resolves outside the
        # repo root (e.g. via `..`) is refused fail-closed. The escape
        # target must not be written and no default artifact appears.
        self._plant("a.txt", "ok")
        repo_root_abs = self.repo_root.resolve()
        escape_rel = "../outside-context.json"
        escape_resolved = (repo_root_abs / escape_rel).resolve()
        # Sanity check: the escape path is genuinely outside repo_root.
        with self.assertRaises(ValueError):
            escape_resolved.relative_to(repo_root_abs)
        rc = self._run_main([
            "load-optional-context",
            "--declared-path", "a.txt",
            "--output", escape_rel,
        ])
        self.assertEqual(rc, 2)
        self.assertFalse(escape_resolved.exists())
        self.assertFalse(self.output_default.exists())

    def test_cli_honors_explicit_limit_overrides(self) -> None:
        self._plant("big.txt", "Y" * 500)
        rc = self._run_main([
            "load-optional-context",
            "--declared-path", "big.txt",
            "--max-files", "4",
            "--max-bytes-per-file", "100",
        ])
        self.assertEqual(rc, 0)
        payload = json.loads(self.output_default.read_text(encoding="utf-8"))
        self.assertEqual(payload["max_files_applied"], 4)
        self.assertEqual(payload["max_bytes_per_file_applied"], 100)
        self.assertTrue(payload["files"][0]["truncated"])
        self.assertEqual(payload["files"][0]["excerpt_byte_size"], 100)

    def test_cli_overwrites_existing_artifact(self) -> None:
        self._plant("a.txt", "ok")
        self.output_default.parent.mkdir(parents=True, exist_ok=True)
        self.output_default.write_text("stale\n", encoding="utf-8")
        rc = self._run_main([
            "load-optional-context",
            "--declared-path", "a.txt",
        ])
        self.assertEqual(rc, 0)
        text = self.output_default.read_text(encoding="utf-8")
        self.assertNotIn("stale", text)
        payload = json.loads(text)
        self.assertEqual(
            payload["context_signal_version"],
            agent_loop.OPTIONAL_CONTEXT_SIGNAL_VERSION,
        )

    def test_cli_refuses_missing_required_declared_path_flag(self) -> None:
        # argparse rejects the required flag absence with SystemExit(2).
        with self.assertRaises(SystemExit) as cm:
            self._run_main(["load-optional-context"])
        self.assertEqual(cm.exception.code, 2)

    def test_cli_refuses_unknown_path_via_halt(self) -> None:
        # The library raises HaltError on a missing file; the CLI
        # handler routes it through _halt so loop-state.json (if any)
        # carries the structural failure vocabulary. The repo_root
        # has the .agent-loop dir but no loop-state.json yet, which
        # means the `_halt` call falls back to `current = {}`.
        rc = self._run_main([
            "load-optional-context",
            "--declared-path", "missing.txt",
        ])
        self.assertEqual(rc, 2)
        # No output artifact written on refusal.
        self.assertFalse(self.output_default.exists())


if __name__ == "__main__":
    unittest.main()
