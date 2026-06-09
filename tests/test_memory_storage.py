"""Focused tests for the Phase 6B structured durable memory storage.

Scope of this suite (Phase 6B, narrow):
- writing one valid entry for each of the five Phase 6A categories
  (`decision`, `failure`, `preference`, `summary`, `checkpoint`)
- enforcing the Phase 6A required metadata fields on every written
  entry (`category`, `phase`, `sub_phase`, `cycle_count`,
  `source_artifact_path`, `created_at`, `signal_version`) so a partial
  call refuses before any file is created
- refusing an out-of-vocabulary `category` so the contract's
  exhaustive five-category set cannot be silently extended at runtime
- append-mostly behavior: a new write creates a new file, never
  overwrites an existing entry; supersession of a prior entry is
  recorded only via an explicit `supersedes` reference field
- write-boundary enforcement: every write is scoped to
  `.agent-loop/memory/`; a path that would resolve outside that
  directory is refused
- read-side schema validation: a malformed entry on disk is refused
  with the same fail-closed `halted_input_missing` halt vocabulary
  the orchestrator uses elsewhere
- list semantics: a sorted return that is empty when the memory
  directory is absent, restricted when `category` is provided, and
  refused on an out-of-vocabulary `category`

The Phase 6B implementation is storage only; no test in this suite
exercises retrieval into prompts, checkpoint-driven resume, or any
continuation runtime behavior, because those are deferred to later 6x
slices.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import agent_loop  # noqa: E402 - sys.path is set above


_BASE_META = dict(
    phase="Phase 6 - Durable Memory and Optional Context Layer",
    sub_phase="Phase 6B - Structured Durable Memory Storage",
    cycle_count=0,
    source_artifact_path=".agent-loop/current-task.md",
)


class _MemoryTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo_root = Path(self._tmp.name)
        self.memory_dir = self.repo_root / agent_loop.MEMORY_DIR_REL
        self.log_path = self.repo_root / ".agent-loop" / "orchestrator.log"
        (self.repo_root / ".agent-loop").mkdir(parents=True, exist_ok=True)

    def _write_one(self, **overrides):
        kwargs = {**_BASE_META, "category": agent_loop.MEMORY_CATEGORY_DECISION,
                  "body": "default body"}
        kwargs.update(overrides)
        return agent_loop.write_memory_entry(self.repo_root, **kwargs)


class WritePerCategoryTests(_MemoryTestCase):
    """Each of the five Phase 6A categories writes a valid entry."""

    def test_each_category_writes_a_valid_entry(self) -> None:
        for category in (
            agent_loop.MEMORY_CATEGORY_DECISION,
            agent_loop.MEMORY_CATEGORY_FAILURE,
            agent_loop.MEMORY_CATEGORY_PREFERENCE,
            agent_loop.MEMORY_CATEGORY_SUMMARY,
            agent_loop.MEMORY_CATEGORY_CHECKPOINT,
        ):
            with self.subTest(category=category):
                path = self._write_one(category=category, body=f"body-{category}")
                self.assertTrue(path.is_file())
                self.assertEqual(path.parent.name, category)
                payload = agent_loop.read_memory_entry(path)
                self.assertEqual(payload["category"], category)
                self.assertEqual(
                    payload["signal_version"],
                    agent_loop.MEMORY_SIGNAL_VERSION,
                )
                for field in agent_loop.MEMORY_REQUIRED_FIELDS:
                    self.assertIn(field, payload)
                self.assertEqual(payload["body"], f"body-{category}")
                self.assertIsNone(payload["supersedes"])


class InvalidCategoryRefusalTests(_MemoryTestCase):

    def test_unknown_category_refuses_before_any_file_write(self) -> None:
        with self.assertRaises(agent_loop.HaltError) as cm:
            self._write_one(category="bogus")
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("bogus", cm.exception.reason)
        self.assertFalse(
            self.memory_dir.exists(),
            "no file or directory may be created on a refused category",
        )

    def test_list_memory_entries_refuses_unknown_category(self) -> None:
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.list_memory_entries(self.repo_root, category="bogus")
        self.assertEqual(cm.exception.status, "halted_input_missing")


class MissingMetadataRefusalTests(_MemoryTestCase):
    """The Phase 6A required metadata fields are non-optional."""

    def test_empty_phase_refuses(self) -> None:
        with self.assertRaises(agent_loop.HaltError) as cm:
            self._write_one(phase="")
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("phase", cm.exception.reason)

    def test_empty_sub_phase_refuses(self) -> None:
        with self.assertRaises(agent_loop.HaltError) as cm:
            self._write_one(sub_phase="")
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("sub_phase", cm.exception.reason)

    def test_empty_source_artifact_path_refuses(self) -> None:
        with self.assertRaises(agent_loop.HaltError) as cm:
            self._write_one(source_artifact_path="")
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("source_artifact_path", cm.exception.reason)

    def test_non_int_cycle_count_refuses(self) -> None:
        with self.assertRaises(agent_loop.HaltError) as cm:
            self._write_one(cycle_count="zero")
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("cycle_count", cm.exception.reason)


class AppendMostlyAndSupersedesTests(_MemoryTestCase):

    def test_two_writes_create_two_distinct_files(self) -> None:
        p1 = self._write_one(body="first body")
        p2 = self._write_one(body="second body")
        self.assertNotEqual(p1, p2)
        self.assertTrue(p1.is_file())
        self.assertTrue(p2.is_file())
        # Original entry is byte-identical to its first write.
        first = agent_loop.read_memory_entry(p1)
        self.assertEqual(first["body"], "first body")
        self.assertIsNone(first["supersedes"])

    def test_supersedes_reference_is_recorded_without_mutating_prior(
        self,
    ) -> None:
        original = self._write_one(body="superseded body")
        before = original.read_bytes()
        superseded_rel = original.relative_to(self.repo_root).as_posix()
        replacement = self._write_one(
            body="fresh body", supersedes=superseded_rel,
        )
        # Replacement carries the explicit supersedes reference.
        repl_payload = agent_loop.read_memory_entry(replacement)
        self.assertEqual(repl_payload["supersedes"], superseded_rel)
        self.assertEqual(repl_payload["body"], "fresh body")
        # Original is untouched on disk (append-mostly: no silent mutation).
        self.assertEqual(original.read_bytes(), before)
        original_payload = agent_loop.read_memory_entry(original)
        self.assertIsNone(original_payload["supersedes"])
        self.assertEqual(original_payload["body"], "superseded body")

    def test_existing_file_collision_refuses(self) -> None:
        # Pre-create a file at the deterministic filename the writer
        # would target, then prove the writer refuses rather than
        # overwrite. Reuses the writer's filename helper to compute the
        # collision path exactly.
        category = agent_loop.MEMORY_CATEGORY_DECISION
        cat_dir = self.memory_dir / category
        cat_dir.mkdir(parents=True, exist_ok=True)
        # Pre-create the file the next write would target. We cannot
        # easily predict the exact `created_at` second; instead, write a
        # first entry to learn the writer's filename shape, then create
        # a colliding sibling at a name we control.
        first = self._write_one(body="body-for-collision-discovery")
        collision = first.parent / first.name  # the exact same path
        # Re-create the existing file to assert the writer refuses
        # in-place mutation when the exact filename target already
        # exists. The writer's filename is derived from created_at +
        # body hash; the simplest way to force a collision is to call
        # the writer with the same body in the same wall-clock second,
        # but that is timing-sensitive. Instead, exercise the
        # collision guard directly by pre-creating the expected name
        # via the helper.
        # Compute a deterministic next-filename and pre-place it:
        forced_name = agent_loop._memory_entry_filename(
            agent_loop._utc_iso_now(), "forced-collision-body"
        )
        forced_path = cat_dir / forced_name
        forced_path.write_text("{}", encoding="utf-8")
        # Patch _utc_iso_now + _memory_entry_filename to return the
        # exact same target so the writer collides.
        import unittest.mock as mock
        with mock.patch.object(
            agent_loop, "_memory_entry_filename", return_value=forced_name,
        ):
            with self.assertRaises(agent_loop.HaltError) as cm:
                self._write_one(body="forced-collision-body")
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("already exists", cm.exception.reason)
        # Pre-placed file is unchanged (no silent overwrite).
        self.assertEqual(forced_path.read_text(encoding="utf-8"), "{}")


class WriteBoundaryEnforcementTests(_MemoryTestCase):

    def test_traversal_via_resolved_path_is_refused(self) -> None:
        # The scope check uses Path.resolve(), so a constructed path
        # under the memory directory but with `..` components that
        # escape it is refused. We exercise the helper directly with a
        # synthesized escape path.
        escape_target = (self.repo_root / "outside.json").resolve()
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop._ensure_memory_path_in_scope(
                escape_target, self.repo_root,
            )
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("outside the memory directory", cm.exception.reason)

    def test_in_scope_path_passes(self) -> None:
        in_scope = self.memory_dir / "decision" / "anything.json"
        in_scope.parent.mkdir(parents=True, exist_ok=True)
        # Must not raise.
        agent_loop._ensure_memory_path_in_scope(in_scope, self.repo_root)

    def test_writer_does_not_modify_canonical_artifacts(self) -> None:
        # Pre-create a canonical artifact and snapshot it. A full
        # write+list+read cycle must leave the canonical file
        # byte-identical.
        canonical = self.repo_root / ".agent-loop" / "loop-state.json"
        canonical.write_text('{"phase":"canonical"}\n', encoding="utf-8")
        before = canonical.read_bytes()
        self._write_one(body="memory write")
        agent_loop.list_memory_entries(self.repo_root)
        self.assertEqual(canonical.read_bytes(), before)


class ReadEntrySchemaTests(_MemoryTestCase):

    def _bad_entry(self, payload: dict) -> Path:
        cat_dir = self.memory_dir / agent_loop.MEMORY_CATEGORY_DECISION
        cat_dir.mkdir(parents=True, exist_ok=True)
        path = cat_dir / "20260609T000000Z-deadbeef.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_read_refuses_missing_required_field(self) -> None:
        # Drop `signal_version` from an otherwise-complete payload.
        payload = {
            "category": agent_loop.MEMORY_CATEGORY_DECISION,
            "phase": "p",
            "sub_phase": "sp",
            "cycle_count": 0,
            "source_artifact_path": "human",
            "created_at": "2026-06-08T00:00:00Z",
            "supersedes": None,
            "body": "x",
        }
        path = self._bad_entry(payload)
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.read_memory_entry(path)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("signal_version", cm.exception.reason)

    def test_read_refuses_unknown_category_on_disk(self) -> None:
        payload = {
            "signal_version": agent_loop.MEMORY_SIGNAL_VERSION,
            "category": "bogus",
            "phase": "p",
            "sub_phase": "sp",
            "cycle_count": 0,
            "source_artifact_path": "human",
            "created_at": "2026-06-08T00:00:00Z",
            "supersedes": None,
            "body": "x",
        }
        path = self._bad_entry(payload)
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.read_memory_entry(path)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("bogus", cm.exception.reason)

    def test_read_refuses_unrecognized_signal_version(self) -> None:
        payload = {
            "signal_version": "phase-99z-vbogus",
            "category": agent_loop.MEMORY_CATEGORY_DECISION,
            "phase": "p",
            "sub_phase": "sp",
            "cycle_count": 0,
            "source_artifact_path": "human",
            "created_at": "2026-06-08T00:00:00Z",
            "supersedes": None,
            "body": "x",
        }
        path = self._bad_entry(payload)
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.read_memory_entry(path)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("signal_version", cm.exception.reason)

    def test_read_refuses_empty_or_malformed_json(self) -> None:
        path = self._bad_entry({})  # placeholder
        path.write_text("", encoding="utf-8")
        with self.assertRaises(agent_loop.HaltError):
            agent_loop.read_memory_entry(path)
        path.write_text("{not json", encoding="utf-8")
        with self.assertRaises(agent_loop.HaltError):
            agent_loop.read_memory_entry(path)

    def test_read_refuses_missing_file(self) -> None:
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.read_memory_entry(
                self.memory_dir / "decision" / "does-not-exist.json",
            )
        self.assertEqual(cm.exception.status, "halted_input_missing")


class ListEntriesTests(_MemoryTestCase):

    def test_empty_when_memory_dir_absent(self) -> None:
        self.assertEqual(
            agent_loop.list_memory_entries(self.repo_root), [],
        )

    def test_returns_only_requested_category_when_filtered(self) -> None:
        self._write_one(category=agent_loop.MEMORY_CATEGORY_DECISION,
                        body="d1")
        self._write_one(category=agent_loop.MEMORY_CATEGORY_FAILURE,
                        body="f1")
        self._write_one(category=agent_loop.MEMORY_CATEGORY_FAILURE,
                        body="f2")
        decisions = agent_loop.list_memory_entries(
            self.repo_root, category=agent_loop.MEMORY_CATEGORY_DECISION,
        )
        failures = agent_loop.list_memory_entries(
            self.repo_root, category=agent_loop.MEMORY_CATEGORY_FAILURE,
        )
        self.assertEqual(len(decisions), 1)
        self.assertEqual(len(failures), 2)
        self.assertTrue(all(p.parent.name == "decision" for p in decisions))
        self.assertTrue(all(p.parent.name == "failure" for p in failures))


class AuditNoteTests(_MemoryTestCase):

    def test_write_appends_memory_write_audit_note(self) -> None:
        self.log_path.write_text("", encoding="utf-8")
        self._write_one(body="audited body", log_path=self.log_path)
        log = self.log_path.read_text(encoding="utf-8")
        self.assertIn("memory write:", log)
        self.assertIn("category='decision'", log)
        self.assertIn("phase='Phase 6 - Durable Memory", log)


if __name__ == "__main__":
    unittest.main(verbosity=2)
