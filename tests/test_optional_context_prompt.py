"""Focused tests for the Phase 6K optional-context prompt-integration
slice.

Scope of this suite (Phase 6K, narrow):
- `integrate_optional_context(repo_root, *, source_path, log_path)`
  reads the shipped Phase 6J payload at
  `.agent-loop/optional-context.json` (or the override) and returns a
  structured advisory-only integration dict suitable for surfacing in
  a later prompt / context path.
- The integration preserves canonical task / phase / loop-state /
  checkpoint precedence (advisory_only is structural and present
  per-entry AND at the top level).
- The integration preserves the 6J bounded inclusion contract
  (source_path, byte_size_on_disk, excerpt, excerpt_byte_size,
  truncated, advisory_only).
- Refusal modes (all `halted_input_missing`): missing / unreadable /
  non-file source; empty or non-JSON source; top-level not a dict;
  missing required source keys; unsupported `context_signal_version`;
  contradictory `canonical_precedence_note`; out-of-bound
  `max_files_applied` or `max_bytes_per_file_applied`; `files` length
  contradicting `declared_paths`; `files` length above
  `max_files_applied`; file entry missing required keys; file entry
  with `advisory_only` not True; `excerpt_byte_size` above
  `max_bytes_per_file_applied`; source-path / declared-path mismatch;
  non-list `declared_paths` and non-string entries.
- Canonical-precedence preservation: integration does NOT mutate
  loop-state, does NOT re-read any declared source file, does NOT
  create the output artifact (only the CLI handler does).
- The `integrate-optional-context` CLI subcommand routes through
  `main(argv)` HANDLERS dispatch and writes the JSON payload to
  `.agent-loop/optional-context-prompt.json` (or the `--output`
  path); both `--source` and `--output` reject absolute / repo-
  escaping paths.

This slice does not implement repo-file re-reading, semantic
retrieval, framework-backed runtime paths, or any widening of Phase
5 autonomy.
"""

from __future__ import annotations

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


def _valid_payload(repo_root: Path) -> dict:
    """A minimal Phase 6J payload shape the integration accepts."""
    return {
        "context_signal_version": (
            agent_loop.OPTIONAL_CONTEXT_SIGNAL_VERSION
        ),
        "loaded_at": "2026-06-13T00:00:00Z",
        "max_files_applied": (
            agent_loop.OPTIONAL_CONTEXT_DEFAULT_MAX_FILES
        ),
        "max_bytes_per_file_applied": (
            agent_loop.OPTIONAL_CONTEXT_DEFAULT_BYTES_PER_FILE
        ),
        "declared_paths": ["docs/a.md", "docs/b.md"],
        "files": [
            {
                "source_path": "docs/a.md",
                "byte_size_on_disk": 5,
                "excerpt": "alpha",
                "excerpt_byte_size": 5,
                "truncated": False,
                "advisory_only": True,
            },
            {
                "source_path": "docs/b.md",
                "byte_size_on_disk": 4,
                "excerpt": "beta",
                "excerpt_byte_size": 4,
                "truncated": False,
                "advisory_only": True,
            },
        ],
        "canonical_precedence_note": (
            agent_loop.OPTIONAL_CONTEXT_CANONICAL_PRECEDENCE_NOTE
        ),
    }


class _IntegrationTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo_root = Path(self._tmp.name).resolve()
        self.al = self.repo_root / ".agent-loop"
        self.al.mkdir(parents=True, exist_ok=True)
        self.log_path = self.al / "orchestrator.log"
        self.source_default = (
            self.repo_root
            / agent_loop.OPTIONAL_CONTEXT_PROMPT_SOURCE_REL
        )
        self.output_default = (
            self.repo_root
            / agent_loop.OPTIONAL_CONTEXT_PROMPT_OUTPUT_REL
        )

    def _plant_source(self, payload: dict) -> Path:
        self.source_default.parent.mkdir(parents=True, exist_ok=True)
        self.source_default.write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8",
        )
        return self.source_default

    def _plant_loop_state(self, data: dict) -> Path:
        sp = self.al / "loop-state.json"
        sp.write_text(json.dumps(data) + "\n", encoding="utf-8")
        return sp


# ----- integrate_optional_context: success shape -----


class IntegrateOptionalContextSuccessShapeTests(_IntegrationTestCase):

    def test_returns_dict_with_every_schema_stable_key(self) -> None:
        self._plant_source(_valid_payload(self.repo_root))
        out = agent_loop.integrate_optional_context(
            self.repo_root, log_path=self.log_path,
        )
        for key in (
            "integration_signal_version",
            "integrated_at",
            "source_artifact",
            "source_signal_version",
            "source_loaded_at",
            "max_files_applied",
            "max_bytes_per_file_applied",
            "advisory_only",
            "canonical_precedence_note",
            "source_canonical_precedence_note",
            "declared_paths",
            "files",
            "prompt_block",
        ):
            self.assertIn(key, out)

    def test_top_level_advisory_marker_is_true(self) -> None:
        self._plant_source(_valid_payload(self.repo_root))
        out = agent_loop.integrate_optional_context(self.repo_root)
        self.assertIs(out["advisory_only"], True)

    def test_signal_versions_are_literal_constants(self) -> None:
        self._plant_source(_valid_payload(self.repo_root))
        out = agent_loop.integrate_optional_context(self.repo_root)
        self.assertEqual(
            out["integration_signal_version"],
            agent_loop.OPTIONAL_CONTEXT_PROMPT_SIGNAL_VERSION,
        )
        self.assertEqual(
            out["source_signal_version"],
            agent_loop.OPTIONAL_CONTEXT_SIGNAL_VERSION,
        )

    def test_canonical_precedence_notes_are_literal_constants(
        self,
    ) -> None:
        self._plant_source(_valid_payload(self.repo_root))
        out = agent_loop.integrate_optional_context(self.repo_root)
        self.assertIs(
            out["canonical_precedence_note"],
            agent_loop.OPTIONAL_CONTEXT_PROMPT_CANONICAL_PRECEDENCE_NOTE,
        )
        self.assertEqual(
            out["source_canonical_precedence_note"],
            agent_loop.OPTIONAL_CONTEXT_CANONICAL_PRECEDENCE_NOTE,
        )

    def test_declared_paths_and_files_preserve_order(self) -> None:
        self._plant_source(_valid_payload(self.repo_root))
        out = agent_loop.integrate_optional_context(self.repo_root)
        self.assertEqual(out["declared_paths"], ["docs/a.md", "docs/b.md"])
        self.assertEqual(
            [f["source_path"] for f in out["files"]],
            ["docs/a.md", "docs/b.md"],
        )

    def test_every_file_entry_carries_advisory_only_true(self) -> None:
        self._plant_source(_valid_payload(self.repo_root))
        out = agent_loop.integrate_optional_context(self.repo_root)
        for f in out["files"]:
            self.assertIs(f["advisory_only"], True)

    def test_max_bounds_passed_through_from_source(self) -> None:
        payload = _valid_payload(self.repo_root)
        payload["max_files_applied"] = 5
        payload["max_bytes_per_file_applied"] = 1024
        self._plant_source(payload)
        out = agent_loop.integrate_optional_context(self.repo_root)
        self.assertEqual(out["max_files_applied"], 5)
        self.assertEqual(out["max_bytes_per_file_applied"], 1024)

    def test_prompt_block_contains_every_source_path(self) -> None:
        self._plant_source(_valid_payload(self.repo_root))
        out = agent_loop.integrate_optional_context(self.repo_root)
        for sp in ("docs/a.md", "docs/b.md"):
            self.assertIn(sp, out["prompt_block"])

    def test_prompt_block_contains_every_excerpt(self) -> None:
        self._plant_source(_valid_payload(self.repo_root))
        out = agent_loop.integrate_optional_context(self.repo_root)
        self.assertIn("alpha", out["prompt_block"])
        self.assertIn("beta", out["prompt_block"])

    def test_audit_log_line_lands_when_log_path_supplied(self) -> None:
        self._plant_source(_valid_payload(self.repo_root))
        agent_loop.integrate_optional_context(
            self.repo_root, log_path=self.log_path,
        )
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("optional-context prompt integrated:", log_text)
        self.assertIn("phase-6k-v1", log_text)

    def test_audit_log_is_byte_equivalent_when_log_path_omitted(
        self,
    ) -> None:
        self._plant_source(_valid_payload(self.repo_root))
        before = (
            self.log_path.read_bytes()
            if self.log_path.exists() else b""
        )
        agent_loop.integrate_optional_context(self.repo_root)
        after = (
            self.log_path.read_bytes()
            if self.log_path.exists() else b""
        )
        self.assertEqual(before, after)

    def test_empty_declared_payload_renders_no_files_block(
        self,
    ) -> None:
        # A 6J payload with zero declared files is still structurally
        # valid (len(files) == len(declared) == 0). The integration
        # surfaces an explicit "no files" rendering rather than
        # producing an empty / silent prompt block.
        payload = _valid_payload(self.repo_root)
        payload["declared_paths"] = []
        payload["files"] = []
        self._plant_source(payload)
        out = agent_loop.integrate_optional_context(self.repo_root)
        self.assertEqual(out["files"], [])
        self.assertIn("No optional-context files", out["prompt_block"])


# ----- integrate_optional_context: contradictory / out-of-bound -----


class IntegrateOptionalContextContradictoryRefusalTests(
    _IntegrationTestCase,
):

    def test_refuses_unsupported_source_signal_version(self) -> None:
        payload = _valid_payload(self.repo_root)
        payload["context_signal_version"] = "phase-6z-vX"
        self._plant_source(payload)
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.integrate_optional_context(self.repo_root)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("context_signal_version", cm.exception.reason)

    def test_refuses_canonical_precedence_note_drift(self) -> None:
        payload = _valid_payload(self.repo_root)
        payload["canonical_precedence_note"] = "different text"
        self._plant_source(payload)
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.integrate_optional_context(self.repo_root)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("canonical_precedence", cm.exception.reason)

    def test_refuses_files_length_mismatch_declared_paths(self) -> None:
        payload = _valid_payload(self.repo_root)
        payload["files"] = payload["files"][:1]  # 1 vs 2
        self._plant_source(payload)
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.integrate_optional_context(self.repo_root)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("contradicts declared_paths", cm.exception.reason)

    def test_refuses_files_length_above_max_files_applied(self) -> None:
        payload = _valid_payload(self.repo_root)
        # Force max_files_applied below the actual file count.
        payload["max_files_applied"] = 1
        self._plant_source(payload)
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.integrate_optional_context(self.repo_root)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("max_files_applied", cm.exception.reason)

    def test_refuses_max_files_applied_above_safety_cap(self) -> None:
        payload = _valid_payload(self.repo_root)
        payload["max_files_applied"] = (
            agent_loop.OPTIONAL_CONTEXT_MAX_MAX_FILES + 1
        )
        self._plant_source(payload)
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.integrate_optional_context(self.repo_root)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("max_files_applied", cm.exception.reason)

    def test_refuses_max_bytes_applied_above_safety_cap(self) -> None:
        payload = _valid_payload(self.repo_root)
        payload["max_bytes_per_file_applied"] = (
            agent_loop.OPTIONAL_CONTEXT_MAX_BYTES_PER_FILE + 1
        )
        self._plant_source(payload)
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.integrate_optional_context(self.repo_root)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn(
            "max_bytes_per_file_applied", cm.exception.reason,
        )

    def test_refuses_max_files_applied_zero(self) -> None:
        payload = _valid_payload(self.repo_root)
        payload["max_files_applied"] = 0
        self._plant_source(payload)
        with self.assertRaises(agent_loop.HaltError):
            agent_loop.integrate_optional_context(self.repo_root)

    def test_refuses_max_bytes_applied_negative(self) -> None:
        payload = _valid_payload(self.repo_root)
        payload["max_bytes_per_file_applied"] = -1
        self._plant_source(payload)
        with self.assertRaises(agent_loop.HaltError):
            agent_loop.integrate_optional_context(self.repo_root)

    def test_refuses_advisory_only_false_on_file_entry(self) -> None:
        payload = _valid_payload(self.repo_root)
        payload["files"][0]["advisory_only"] = False
        self._plant_source(payload)
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.integrate_optional_context(self.repo_root)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("advisory_only", cm.exception.reason)

    def test_refuses_excerpt_byte_size_above_max_bytes(self) -> None:
        payload = _valid_payload(self.repo_root)
        payload["max_bytes_per_file_applied"] = 3
        # excerpt_byte_size=5 on the first file violates the cap.
        self._plant_source(payload)
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.integrate_optional_context(self.repo_root)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("excerpt_byte_size", cm.exception.reason)

    def test_refuses_source_path_mismatch_declared(self) -> None:
        payload = _valid_payload(self.repo_root)
        payload["files"][0]["source_path"] = "docs/different.md"
        self._plant_source(payload)
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.integrate_optional_context(self.repo_root)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("does not match declared_paths", cm.exception.reason)


# ----- integrate_optional_context: malformed / missing -----


class IntegrateOptionalContextMalformedRefusalTests(
    _IntegrationTestCase,
):

    def test_refuses_missing_source_artifact(self) -> None:
        # No source planted.
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.integrate_optional_context(self.repo_root)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("does not exist", cm.exception.reason)

    def test_refuses_source_path_is_directory(self) -> None:
        self.source_default.parent.mkdir(parents=True, exist_ok=True)
        self.source_default.mkdir()
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.integrate_optional_context(self.repo_root)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("not a regular file", cm.exception.reason)

    def test_refuses_unreadable_source(self) -> None:
        self._plant_source(_valid_payload(self.repo_root))
        target = self.source_default.resolve()
        real_read = Path.read_text

        def _side_effect(self_path: Path, *args, **kwargs):
            if self_path.resolve() == target:
                raise OSError("simulated read failure")
            return real_read(self_path, *args, **kwargs)

        with mock.patch.object(Path, "read_text", _side_effect):
            with self.assertRaises(agent_loop.HaltError) as cm:
                agent_loop.integrate_optional_context(self.repo_root)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("unreadable", cm.exception.reason)

    def test_refuses_non_json_source(self) -> None:
        self.source_default.parent.mkdir(parents=True, exist_ok=True)
        self.source_default.write_text("not json {", encoding="utf-8")
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.integrate_optional_context(self.repo_root)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("not valid JSON", cm.exception.reason)

    def test_refuses_top_level_not_dict(self) -> None:
        self.source_default.parent.mkdir(parents=True, exist_ok=True)
        self.source_default.write_text("[]", encoding="utf-8")
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.integrate_optional_context(self.repo_root)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("JSON object", cm.exception.reason)

    def test_refuses_missing_required_top_level_key(self) -> None:
        payload = _valid_payload(self.repo_root)
        payload.pop("loaded_at")
        self._plant_source(payload)
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.integrate_optional_context(self.repo_root)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("missing required key", cm.exception.reason)

    def test_refuses_files_not_list(self) -> None:
        payload = _valid_payload(self.repo_root)
        payload["files"] = "not-a-list"
        self._plant_source(payload)
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.integrate_optional_context(self.repo_root)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("files must be a list", cm.exception.reason)

    def test_refuses_file_entry_not_dict(self) -> None:
        payload = _valid_payload(self.repo_root)
        payload["files"][0] = "string"
        self._plant_source(payload)
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.integrate_optional_context(self.repo_root)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("must be a JSON object", cm.exception.reason)

    def test_refuses_file_entry_missing_required_key(self) -> None:
        payload = _valid_payload(self.repo_root)
        payload["files"][0].pop("excerpt")
        self._plant_source(payload)
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.integrate_optional_context(self.repo_root)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("missing required key", cm.exception.reason)

    def test_refuses_declared_paths_not_list(self) -> None:
        payload = _valid_payload(self.repo_root)
        payload["declared_paths"] = "docs/a.md"
        self._plant_source(payload)
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.integrate_optional_context(self.repo_root)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("declared_paths must be a list", cm.exception.reason)

    def test_refuses_declared_paths_non_string_entry(self) -> None:
        payload = _valid_payload(self.repo_root)
        payload["declared_paths"][0] = 123
        self._plant_source(payload)
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.integrate_optional_context(self.repo_root)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("non-empty string", cm.exception.reason)


# ----- integrate_optional_context: canonical-precedence -----


class IntegrateOptionalContextCanonicalPrecedenceTests(
    _IntegrationTestCase,
):

    def test_integration_does_not_create_output_artifact(self) -> None:
        self._plant_source(_valid_payload(self.repo_root))
        agent_loop.integrate_optional_context(self.repo_root)
        self.assertFalse(self.output_default.exists())

    def test_integration_does_not_mutate_source_artifact(self) -> None:
        self._plant_source(_valid_payload(self.repo_root))
        before = self.source_default.read_bytes()
        agent_loop.integrate_optional_context(self.repo_root)
        self.assertEqual(self.source_default.read_bytes(), before)

    def test_integration_does_not_re_read_declared_source_files(
        self,
    ) -> None:
        # Plant the JSON payload but do NOT plant the underlying repo
        # files referenced by declared_paths. The integration must
        # still succeed because it never re-reads those files.
        self._plant_source(_valid_payload(self.repo_root))
        for declared in ("docs/a.md", "docs/b.md"):
            self.assertFalse(
                (self.repo_root / declared).exists(),
                f"setup planted {declared!r}; it must not exist",
            )
        out = agent_loop.integrate_optional_context(self.repo_root)
        self.assertEqual(len(out["files"]), 2)

    def test_integration_does_not_mutate_loop_state(self) -> None:
        sp = self._plant_loop_state({
            "phase": "Phase 6",
            "sub_phase": "6K",
            "task": "integrate",
            "cycle_count": 0,
        })
        before = sp.read_bytes()
        self._plant_source(_valid_payload(self.repo_root))
        agent_loop.integrate_optional_context(self.repo_root)
        self.assertEqual(sp.read_bytes(), before)


# ----- integrate_optional_context: bounded inclusion -----


class IntegrateOptionalContextBoundedInclusionTests(
    _IntegrationTestCase,
):

    def test_truncated_flag_preserved_from_source(self) -> None:
        payload = _valid_payload(self.repo_root)
        payload["files"][0]["truncated"] = True
        self._plant_source(payload)
        out = agent_loop.integrate_optional_context(self.repo_root)
        self.assertTrue(out["files"][0]["truncated"])
        self.assertFalse(out["files"][1]["truncated"])

    def test_excerpt_byte_size_preserved_from_source(self) -> None:
        self._plant_source(_valid_payload(self.repo_root))
        out = agent_loop.integrate_optional_context(self.repo_root)
        self.assertEqual(out["files"][0]["excerpt_byte_size"], 5)
        self.assertEqual(out["files"][1]["excerpt_byte_size"], 4)

    def test_excerpt_bytes_equal_source_excerpt(self) -> None:
        self._plant_source(_valid_payload(self.repo_root))
        out = agent_loop.integrate_optional_context(self.repo_root)
        self.assertEqual(out["files"][0]["excerpt"], "alpha")
        self.assertEqual(out["files"][1]["excerpt"], "beta")

    def test_prompt_block_reports_truncation_flag(self) -> None:
        payload = _valid_payload(self.repo_root)
        payload["files"][0]["truncated"] = True
        self._plant_source(payload)
        out = agent_loop.integrate_optional_context(self.repo_root)
        self.assertIn("truncated=true", out["prompt_block"])
        self.assertIn("truncated=false", out["prompt_block"])


# ----- cmd_integrate_optional_context_prompt + main(argv) -----


class CmdIntegrateOptionalContextPromptTests(_IntegrationTestCase):

    def _run_main(self, argv) -> int:
        with mock.patch.object(
            agent_loop, "find_repo_root", return_value=self.repo_root,
        ):
            return agent_loop.main(argv)

    def test_cli_writes_default_output_artifact(self) -> None:
        self._plant_source(_valid_payload(self.repo_root))
        rc = self._run_main(["integrate-optional-context"])
        self.assertEqual(rc, 0)
        self.assertTrue(self.output_default.is_file())
        payload = json.loads(
            self.output_default.read_text(encoding="utf-8"),
        )
        self.assertEqual(
            payload["integration_signal_version"],
            agent_loop.OPTIONAL_CONTEXT_PROMPT_SIGNAL_VERSION,
        )
        self.assertEqual(len(payload["files"]), 2)

    def test_cli_honors_relative_output_override(self) -> None:
        self._plant_source(_valid_payload(self.repo_root))
        rel = ".agent-loop/custom-prompt.json"
        custom = self.repo_root / rel
        rc = self._run_main([
            "integrate-optional-context", "--output", rel,
        ])
        self.assertEqual(rc, 0)
        self.assertTrue(custom.is_file())
        self.assertFalse(self.output_default.exists())

    def test_cli_honors_relative_source_override(self) -> None:
        # Plant the source at a non-default location and pass it via
        # --source. The default source path must remain absent.
        rel = ".agent-loop/other-context.json"
        custom = self.repo_root / rel
        custom.parent.mkdir(parents=True, exist_ok=True)
        custom.write_text(
            json.dumps(_valid_payload(self.repo_root)) + "\n",
            encoding="utf-8",
        )
        self.assertFalse(self.source_default.exists())
        rc = self._run_main([
            "integrate-optional-context", "--source", rel,
        ])
        self.assertEqual(rc, 0)
        self.assertTrue(self.output_default.is_file())

    def test_cli_refuses_absolute_output_path(self) -> None:
        self._plant_source(_valid_payload(self.repo_root))
        absolute = (self.repo_root / "elsewhere.json").resolve()
        self.assertTrue(absolute.is_absolute())
        rc = self._run_main([
            "integrate-optional-context", "--output", str(absolute),
        ])
        self.assertEqual(rc, 2)
        self.assertFalse(absolute.exists())
        self.assertFalse(self.output_default.exists())

    def test_cli_refuses_output_escaping_repo_via_dotdot(self) -> None:
        self._plant_source(_valid_payload(self.repo_root))
        repo_root_abs = self.repo_root.resolve()
        escape_rel = "../escape-prompt.json"
        escape_resolved = (repo_root_abs / escape_rel).resolve()
        with self.assertRaises(ValueError):
            escape_resolved.relative_to(repo_root_abs)
        rc = self._run_main([
            "integrate-optional-context", "--output", escape_rel,
        ])
        self.assertEqual(rc, 2)
        self.assertFalse(escape_resolved.exists())
        self.assertFalse(self.output_default.exists())

    def test_cli_refuses_absolute_source_path(self) -> None:
        self._plant_source(_valid_payload(self.repo_root))
        absolute = self.source_default.resolve()
        self.assertTrue(absolute.is_absolute())
        rc = self._run_main([
            "integrate-optional-context", "--source", str(absolute),
        ])
        self.assertEqual(rc, 2)
        self.assertFalse(self.output_default.exists())

    def test_cli_refuses_source_escaping_repo_via_dotdot(self) -> None:
        self._plant_source(_valid_payload(self.repo_root))
        rc = self._run_main([
            "integrate-optional-context",
            "--source", "../outside.json",
        ])
        self.assertEqual(rc, 2)
        self.assertFalse(self.output_default.exists())

    def test_cli_refuses_missing_source_via_halt(self) -> None:
        # No source planted; CLI must refuse via _halt and not create
        # the output artifact.
        rc = self._run_main(["integrate-optional-context"])
        self.assertEqual(rc, 2)
        self.assertFalse(self.output_default.exists())

    def test_cli_overwrites_existing_output_artifact(self) -> None:
        self._plant_source(_valid_payload(self.repo_root))
        self.output_default.parent.mkdir(parents=True, exist_ok=True)
        self.output_default.write_text("stale\n", encoding="utf-8")
        rc = self._run_main(["integrate-optional-context"])
        self.assertEqual(rc, 0)
        text = self.output_default.read_text(encoding="utf-8")
        self.assertNotIn("stale", text)
        payload = json.loads(text)
        self.assertEqual(
            payload["integration_signal_version"],
            agent_loop.OPTIONAL_CONTEXT_PROMPT_SIGNAL_VERSION,
        )

    def test_cli_refuses_contradictory_source_via_halt(self) -> None:
        payload = _valid_payload(self.repo_root)
        payload["canonical_precedence_note"] = "drifted text"
        self._plant_source(payload)
        rc = self._run_main(["integrate-optional-context"])
        self.assertEqual(rc, 2)
        self.assertFalse(self.output_default.exists())


if __name__ == "__main__":
    unittest.main()
