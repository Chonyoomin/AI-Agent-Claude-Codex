"""Phase 10AA - Human-Facing Memory Vault Export Contract And Initial
Slice tests.

Exercises:
  - module-level constants (signal version, precedence note,
    closed enumerations)
  - operator-input normalizer
  - closed export registry + descriptor validator
  - pure freshness probe (`Path.stat()` + optional
    `Path.iterdir()`; NEVER reads source content)
  - approval-state / enablement-state helpers
  - `build_desktop_memory_vault_view(...)` shape + soft-fail on
    missing loop-state + fail-closed default (every export
    surfaces as `refused_until_policy_update`)
  - renderer per-line attribution
  - `build_desktop_memory_vault_controls(...)` widget shape
    (COPY-PASTE only; every button clickable for clipboard-copy;
    per-export `runtime_enabled` mirrors the deferred runtime
    state and the label discloses the enablement state; matches
    the Phase 10Z fix-cycle affordance contract)
  - `cmd_view_desktop_memory_vault(...)` CLI handler + Phase 7C
    exit-0 pattern
  - integration into `assemble_desktop_app_view(...)` +
    `render_desktop_app_text(...)`
  - non-mutation invariants (no socket, no subprocess, no
    orchestrator.log append, no loop-state mutation, no
    `_halt(...)`, no Phase 10I library-callable cap widening,
    no persisted export cache, NEVER reads durable-memory or
    canonical-artifact CONTENT)
"""
from __future__ import annotations

import argparse
import io
import json
import socket
import sys
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock


HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import agent_loop  # noqa: E402


CONTRACT_VERSION = "phase-3a-v2"


def _make_controller(
    td: Path,
    status: str = "awaiting_claude_implementation",
    approval_mode: str = "review",
) -> Path:
    td.mkdir(parents=True, exist_ok=True)
    (td / "AGENTS.md").write_text("agents\n", encoding="utf-8")
    (td / "CLAUDE.md").write_text("claude\n", encoding="utf-8")
    (td / "TASK.md").write_text("# TASK.md\n", encoding="utf-8")
    (td / "README.md").write_text("readme\n", encoding="utf-8")
    (td / ".agent-loop").mkdir()
    (td / ".agent-loop" / "loop-state.json").write_text(
        json.dumps({
            "phase": "Phase 10 - Future Product Features",
            "sub_phase": (
                "Phase 10AA - Human-Facing Memory Vault Export "
                "Contract And Initial Slice"
            ),
            "task": "phase-10aa-test",
            "status": status,
            "cycle_count": 0,
            "max_cycles": 3,
            "last_verdict": None,
            "last_verdict_phase": None,
            "contract_version": CONTRACT_VERSION,
            "claude_version": "claude-opus-4-7",
            "codex_version": None,
            "orchestrator_version": "phase-3d-v0",
            "approval_mode": approval_mode,
            "awaiting_human_for": None,
        }),
        encoding="utf-8",
    )
    return td


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
class ConstantsTests(unittest.TestCase):

    def test_signal_version(self) -> None:
        self.assertEqual(
            agent_loop.DESKTOP_MEMORY_VAULT_SIGNAL_VERSION,
            "phase-10aa-v1",
        )

    def test_precedence_note_pins_phase_10aa_contract(self) -> None:
        note = agent_loop.DESKTOP_MEMORY_VAULT_PRECEDENCE_NOTE
        for needle in (
            "Phase 10AA",
            "Phase 6A/6B durable-memory storage layer",
            "advisory-vs-canonical mirror rule",
            "Phase 10I",
            "refused_until_policy_update",
            "NEVER mutates any canonical artifact",
            "NEVER writes an export file",
            "NEVER persists an export cache",
            "NEVER opens a network socket",
            # Phase 10AA fix cycle: the surface DOES surface a
            # bounded readable excerpt / name-only index. The
            # precedence note must pin the bounded-read
            # boundary explicitly.
            "MEMORY_VAULT_EXCERPT_BYTE_LIMIT",
            "MEMORY_VAULT_ENTRY_INDEX_LIMIT",
            "NEVER reads durable-memory JSON BODY content",
            "NEVER reads MORE than",
        ):
            self.assertIn(needle, note, needle)

    def test_export_categories_closed_enum(self) -> None:
        self.assertEqual(
            agent_loop.MEMORY_VAULT_EXPORT_CATEGORIES,
            (
                "durable_memory_entry",
                "decision_summary",
                "architecture_snapshot",
            ),
        )

    def test_source_kinds_closed_enum(self) -> None:
        self.assertEqual(
            agent_loop.MEMORY_VAULT_SOURCE_KINDS,
            ("shipped_memory_json", "canonical_artifact_mirror"),
        )

    def test_advisory_labels_closed_enum(self) -> None:
        self.assertEqual(
            agent_loop.MEMORY_VAULT_ADVISORY_LABELS,
            (
                "advisory_only_no_canonical_substitution",
                "canonical_mirror_read_only",
                "refused_until_policy_update",
            ),
        )

    def test_freshness_states_closed_enum(self) -> None:
        self.assertEqual(
            agent_loop.MEMORY_VAULT_FRESHNESS_STATES,
            ("fresh", "stale", "missing", "unknown"),
        )

    def test_enablement_states_closed_enum(self) -> None:
        self.assertEqual(
            agent_loop.MEMORY_VAULT_ENABLEMENT_STATES,
            (
                "disabled_by_default",
                "enabled_pending_runtime",
                "refused_until_policy_update",
            ),
        )

    def test_approval_requirements_closed_enum(self) -> None:
        self.assertEqual(
            agent_loop.MEMORY_VAULT_APPROVAL_REQUIREMENTS,
            (
                "operator_acknowledged_advisory_labeling",
                "operator_supplied_identity",
                "approval_mode_supports_export",
                "phase_10aa_runtime_available",
                "source_present_in_repo",
            ),
        )

    def test_refusal_reasons_closed_enum(self) -> None:
        self.assertEqual(
            agent_loop.MEMORY_VAULT_REFUSAL_REASONS,
            (
                "approval_mode_strict",
                "operator_identity_missing",
                "operator_acknowledgement_missing",
                "source_missing",
                "runtime_not_available",
            ),
        )

    def test_permitted_approval_modes(self) -> None:
        self.assertEqual(
            agent_loop.MEMORY_VAULT_PERMITTED_APPROVAL_MODES,
            frozenset({"review", "autonomous"}),
        )

    def test_freshness_stale_threshold_seconds(self) -> None:
        # 30 days worth of seconds; matches the Phase 10V precedent.
        self.assertEqual(
            agent_loop.MEMORY_VAULT_FRESHNESS_STALE_THRESHOLD_SECONDS,
            30 * 24 * 3600,
        )

    def test_excerpt_byte_limit(self) -> None:
        # Phase 10AA fix cycle: canonical-artifact mirror sources
        # surface a head-bounded excerpt truncated at this many
        # bytes so the shipped desktop app / CLI actually renders
        # a readable human-facing memory-vault export body.
        self.assertEqual(
            agent_loop.MEMORY_VAULT_EXCERPT_BYTE_LIMIT, 2000,
        )

    def test_entry_index_limit(self) -> None:
        # Phase 10AA fix cycle: shipped memory JSON directory
        # sources surface a name-only index bounded at this many
        # most-recent shipped `.json` filenames.
        self.assertEqual(
            agent_loop.MEMORY_VAULT_ENTRY_INDEX_LIMIT, 10,
        )


# ---------------------------------------------------------------------------
# Registry + descriptor validator
# ---------------------------------------------------------------------------
class RegistryTests(unittest.TestCase):

    def test_registry_ships_five_exports(self) -> None:
        self.assertEqual(
            len(agent_loop._DESKTOP_MEMORY_VAULT_REGISTRY), 5,
        )

    def test_registry_covers_every_closed_category(self) -> None:
        categories = {
            spec["export_category"]
            for spec in agent_loop._DESKTOP_MEMORY_VAULT_REGISTRY
        }
        self.assertEqual(
            categories,
            set(agent_loop.MEMORY_VAULT_EXPORT_CATEGORIES),
        )

    def test_registry_uses_both_source_kinds(self) -> None:
        kinds = {
            spec["source_kind"]
            for spec in agent_loop._DESKTOP_MEMORY_VAULT_REGISTRY
        }
        self.assertEqual(
            kinds, set(agent_loop.MEMORY_VAULT_SOURCE_KINDS),
        )

    def test_every_registry_entry_passes_validator(self) -> None:
        for spec in agent_loop._DESKTOP_MEMORY_VAULT_REGISTRY:
            agent_loop._desktop_memory_vault_validate_descriptor(spec)


class ValidatorTests(unittest.TestCase):

    def _valid(self):
        return {
            "id": "x",
            "display_name": "X",
            "export_category": "durable_memory_entry",
            "source_kind": "shipped_memory_json",
            "advisory_label_rule": (
                "advisory_only_no_canonical_substitution"
            ),
            "path_canonical_rel": ".agent-loop/memory/decision",
            "description": "d",
            "safety_copy": "s",
            "approval_requirements": (
                "operator_acknowledged_advisory_labeling",
            ),
            "deferred_runtime_marker": "m",
            "refusal_reason_template": "t",
        }

    def test_non_dict_refuses(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_memory_vault_validate_descriptor(
                ["not", "a", "dict"],
            )

    def test_missing_string_field_refuses(self) -> None:
        spec = self._valid()
        del spec["export_category"]
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_memory_vault_validate_descriptor(spec)

    def test_unknown_export_category_refuses(self) -> None:
        spec = self._valid()
        spec["export_category"] = "not_a_category"
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_memory_vault_validate_descriptor(spec)

    def test_unknown_source_kind_refuses(self) -> None:
        spec = self._valid()
        spec["source_kind"] = "not_a_source"
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_memory_vault_validate_descriptor(spec)

    def test_unknown_advisory_label_refuses(self) -> None:
        spec = self._valid()
        spec["advisory_label_rule"] = "not_a_label"
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_memory_vault_validate_descriptor(spec)

    def test_unknown_approval_requirement_refuses(self) -> None:
        spec = self._valid()
        spec["approval_requirements"] = ("not_a_requirement",)
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_memory_vault_validate_descriptor(spec)

    def test_non_tuple_approval_requirements_refuses(self) -> None:
        spec = self._valid()
        spec["approval_requirements"] = [
            "operator_acknowledged_advisory_labeling",
        ]
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_memory_vault_validate_descriptor(spec)

    def test_backslash_in_path_rel_refuses(self) -> None:
        spec = self._valid()
        spec["path_canonical_rel"] = ".agent-loop\\memory\\decision"
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_memory_vault_validate_descriptor(spec)

    def test_absolute_path_rel_refuses(self) -> None:
        spec = self._valid()
        spec["path_canonical_rel"] = "/etc/passwd"
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_memory_vault_validate_descriptor(spec)

    def test_windows_drive_prefix_refuses(self) -> None:
        spec = self._valid()
        spec["path_canonical_rel"] = "C:/Users/root/mem"
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_memory_vault_validate_descriptor(spec)

    def test_parent_directory_traversal_refuses(self) -> None:
        spec = self._valid()
        spec["path_canonical_rel"] = "a/../b"
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_memory_vault_validate_descriptor(spec)


# ---------------------------------------------------------------------------
# Operator-input normalizer
# ---------------------------------------------------------------------------
class OperatorInputsNormalizerTests(unittest.TestCase):

    def test_none_returns_empty_defaults(self) -> None:
        got = (
            agent_loop._desktop_memory_vault_normalize_operator_inputs(
                None,
            )
        )
        self.assertEqual(got["identity"], "")
        self.assertEqual(got["acknowledged_export_ids"], frozenset())

    def test_non_dict_refuses(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_memory_vault_normalize_operator_inputs(
                ["not", "a", "dict"],
            )

    def test_iterable_ids_normalized(self) -> None:
        got = (
            agent_loop._desktop_memory_vault_normalize_operator_inputs(
                {
                    "identity": " me ",
                    "acknowledged_export_ids": [
                        "durable_memory_decision_index",
                    ],
                },
            )
        )
        self.assertEqual(got["identity"], "me")
        self.assertIn(
            "durable_memory_decision_index",
            got["acknowledged_export_ids"],
        )

    def test_wrong_identity_type_refuses(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_memory_vault_normalize_operator_inputs(
                {"identity": 42, "acknowledged_export_ids": []},
            )

    def test_wrong_ack_type_refuses(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_memory_vault_normalize_operator_inputs(
                {
                    "identity": "me",
                    "acknowledged_export_ids": "not-iterable",
                },
            )


# ---------------------------------------------------------------------------
# Freshness probe
# ---------------------------------------------------------------------------
class FreshnessProbeTests(unittest.TestCase):

    def test_missing_source_reports_missing(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            spec = dict(
                agent_loop._DESKTOP_MEMORY_VAULT_REGISTRY[0],
            )
            probe = (
                agent_loop._desktop_memory_vault_probe_freshness(
                    controller, spec,
                )
            )
        self.assertFalse(probe["exists"])
        self.assertEqual(probe["freshness_state"], "missing")
        self.assertIsNone(probe["last_modified_utc"])
        self.assertIsNone(probe["size_bytes"])
        self.assertIsNone(probe["entry_count"])

    def test_present_file_reports_fresh_and_stat(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            (controller / ".agent-loop"
             / "claude-summary.md").write_text(
                "# summary\n", encoding="utf-8",
            )
            spec = next(
                dict(s) for s in (
                    agent_loop._DESKTOP_MEMORY_VAULT_REGISTRY
                )
                if s["id"] == (
                    "decision_summary_from_claude_summary"
                )
            )
            probe = (
                agent_loop._desktop_memory_vault_probe_freshness(
                    controller, spec,
                )
            )
        self.assertTrue(probe["exists"])
        self.assertEqual(probe["freshness_state"], "fresh")
        self.assertIsNotNone(probe["last_modified_utc"])
        self.assertIsNotNone(probe["size_bytes"])
        self.assertIsNone(probe["entry_count"])

    def test_present_directory_reports_entry_count(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            decision_dir = (
                controller / ".agent-loop" / "memory" / "decision"
            )
            decision_dir.mkdir(parents=True)
            (decision_dir / "a.json").write_text(
                "{}", encoding="utf-8",
            )
            (decision_dir / "b.json").write_text(
                "{}", encoding="utf-8",
            )
            (decision_dir / "c.txt").write_text(
                "x", encoding="utf-8",
            )
            spec = next(
                dict(s) for s in (
                    agent_loop._DESKTOP_MEMORY_VAULT_REGISTRY
                )
                if s["id"] == "durable_memory_decision_index"
            )
            probe = (
                agent_loop._desktop_memory_vault_probe_freshness(
                    controller, spec,
                )
            )
        self.assertTrue(probe["exists"])
        # Only .json files are counted; the .txt is ignored.
        self.assertEqual(probe["entry_count"], 2)

    def test_probe_never_reads_source_content(self) -> None:
        # The freshness probe is still a pure stat / iterdir
        # helper; it MUST NOT read source CONTENT. The Phase 10AA
        # fix cycle introduces a SEPARATE `_desktop_memory_vault_
        # read_excerpt(...)` helper for the bounded readable
        # excerpt; the probe stays a metadata-only primitive.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            sentinels = {}
            for i, spec in enumerate(
                agent_loop._DESKTOP_MEMORY_VAULT_REGISTRY
            ):
                sentinel = (
                    f"PHASE_10AA_TEST_SENTINEL_"
                    f"{i}_DO_NOT_LEAK"
                )
                path = controller / spec["path_canonical_rel"]
                if spec["source_kind"] == (
                    "shipped_memory_json"
                ):
                    path.mkdir(parents=True, exist_ok=True)
                    (path / "sentinel.json").write_text(
                        json.dumps({"sentinel": sentinel}),
                        encoding="utf-8",
                    )
                else:
                    path.parent.mkdir(
                        parents=True, exist_ok=True,
                    )
                    path.write_text(
                        sentinel, encoding="utf-8",
                    )
                sentinels[spec["id"]] = sentinel
            for spec in (
                agent_loop._DESKTOP_MEMORY_VAULT_REGISTRY
            ):
                probe = (
                    agent_loop._desktop_memory_vault_probe_freshness(
                        controller, spec,
                    )
                )
                serialized = json.dumps(probe)
                self.assertNotIn(
                    sentinels[spec["id"]], serialized, spec["id"],
                )


# ---------------------------------------------------------------------------
# Bounded excerpt reader (Phase 10AA fix cycle)
# ---------------------------------------------------------------------------
class ExcerptReaderTests(unittest.TestCase):

    def _canonical_spec(self):
        return next(
            dict(s) for s in (
                agent_loop._DESKTOP_MEMORY_VAULT_REGISTRY
            )
            if s["id"] == "decision_summary_from_claude_summary"
        )

    def _memory_spec(self):
        return next(
            dict(s) for s in (
                agent_loop._DESKTOP_MEMORY_VAULT_REGISTRY
            )
            if s["id"] == "durable_memory_decision_index"
        )

    def test_missing_source_returns_empty_envelope(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            envelope = (
                agent_loop._desktop_memory_vault_read_excerpt(
                    controller, self._canonical_spec(),
                )
            )
        self.assertIsNone(envelope["excerpt_text"])
        self.assertIsNone(envelope["entry_index"])

    def test_canonical_mirror_short_file_reads_full_body(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            body = "# summary\n\nHuman-readable body.\n"
            # Write bytes directly so Windows universal newline
            # translation does not turn `\n` into `\r\n` and
            # mismatch the excerpt byte count / content.
            (controller / ".agent-loop"
             / "claude-summary.md").write_bytes(
                body.encode("utf-8"),
            )
            envelope = (
                agent_loop._desktop_memory_vault_read_excerpt(
                    controller, self._canonical_spec(),
                )
            )
        self.assertEqual(envelope["excerpt_text"], body)
        self.assertFalse(envelope["excerpt_truncated"])
        self.assertEqual(
            envelope["excerpt_bytes_read"],
            len(body.encode("utf-8")),
        )

    def test_canonical_mirror_long_file_is_truncated_at_cap(
        self,
    ) -> None:
        # Write a canonical mirror source LARGER than the cap
        # and assert the excerpt is truncated at the byte limit.
        # This locks the "never reads more than the cap" invariant.
        cap = agent_loop.MEMORY_VAULT_EXCERPT_BYTE_LIMIT
        large_body = "A" * (cap * 3)
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            (controller / ".agent-loop"
             / "claude-summary.md").write_text(
                large_body, encoding="utf-8",
            )
            envelope = (
                agent_loop._desktop_memory_vault_read_excerpt(
                    controller, self._canonical_spec(),
                )
            )
        self.assertTrue(envelope["excerpt_truncated"])
        self.assertEqual(envelope["excerpt_bytes_read"], cap)
        self.assertEqual(len(envelope["excerpt_text"]), cap)

    def test_canonical_mirror_never_reads_tail(self) -> None:
        # Sentinel written PAST the byte cap MUST NOT appear in
        # the returned excerpt. The head-of-file bound must be
        # exact.
        cap = agent_loop.MEMORY_VAULT_EXCERPT_BYTE_LIMIT
        sentinel = "PHASE_10AA_TAIL_SENTINEL_DO_NOT_LEAK"
        head = "A" * cap
        body = head + sentinel
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            (controller / ".agent-loop"
             / "claude-summary.md").write_text(
                body, encoding="utf-8",
            )
            envelope = (
                agent_loop._desktop_memory_vault_read_excerpt(
                    controller, self._canonical_spec(),
                )
            )
        self.assertNotIn(sentinel, envelope["excerpt_text"])
        self.assertTrue(envelope["excerpt_truncated"])

    def test_directory_source_returns_json_filenames_only(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            decision_dir = (
                controller / ".agent-loop" / "memory" / "decision"
            )
            decision_dir.mkdir(parents=True)
            (decision_dir / "20260701T000000Z-aaaa.json").write_text(
                "{}", encoding="utf-8",
            )
            (decision_dir / "20260702T000000Z-bbbb.json").write_text(
                "{}", encoding="utf-8",
            )
            (decision_dir / "ignore.txt").write_text(
                "x", encoding="utf-8",
            )
            envelope = (
                agent_loop._desktop_memory_vault_read_excerpt(
                    controller, self._memory_spec(),
                )
            )
        self.assertIsNone(envelope["excerpt_text"])
        # Newest-first: filenames are reverse-sorted so the
        # newest shipped entry is at index 0.
        self.assertEqual(
            envelope["entry_index"],
            [
                "20260702T000000Z-bbbb.json",
                "20260701T000000Z-aaaa.json",
            ],
        )
        self.assertFalse(envelope["entry_index_truncated"])

    def test_directory_source_index_bounded_by_limit(self) -> None:
        cap = agent_loop.MEMORY_VAULT_ENTRY_INDEX_LIMIT
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            decision_dir = (
                controller / ".agent-loop" / "memory" / "decision"
            )
            decision_dir.mkdir(parents=True)
            for i in range(cap * 2):
                (
                    decision_dir
                    / f"2026070{i:02d}T000000Z-hash.json"
                ).write_text("{}", encoding="utf-8")
            envelope = (
                agent_loop._desktop_memory_vault_read_excerpt(
                    controller, self._memory_spec(),
                )
            )
        self.assertEqual(len(envelope["entry_index"]), cap)
        self.assertTrue(envelope["entry_index_truncated"])

    def test_directory_source_never_reads_json_body(self) -> None:
        # Write a sentinel INSIDE a shipped memory JSON file
        # (as body content) and assert the sentinel does NOT
        # appear in the returned envelope. The surface may
        # surface the filename but MUST NOT surface the body.
        sentinel = "PHASE_10AA_MEMORY_BODY_SENTINEL_DO_NOT_LEAK"
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            decision_dir = (
                controller / ".agent-loop" / "memory" / "decision"
            )
            decision_dir.mkdir(parents=True)
            (
                decision_dir
                / "20260702T000000Z-bbbb.json"
            ).write_text(
                json.dumps({"body_sentinel": sentinel}),
                encoding="utf-8",
            )
            envelope = (
                agent_loop._desktop_memory_vault_read_excerpt(
                    controller, self._memory_spec(),
                )
            )
        serialized = json.dumps(envelope, default=str)
        self.assertNotIn(sentinel, serialized)


# ---------------------------------------------------------------------------
# Approval / enablement helpers
# ---------------------------------------------------------------------------
class ApprovalStateTests(unittest.TestCase):

    def _spec(self):
        return dict(
            agent_loop._DESKTOP_MEMORY_VAULT_REGISTRY[0],
        )

    def test_all_unsatisfied_default(self) -> None:
        state = (
            agent_loop._desktop_memory_vault_compute_approval_state(
                self._spec(),
                approval_mode=None,
                phase_10aa_runtime_available=False,
                operator_acknowledged_advisory_labeling=False,
                operator_supplied_identity=False,
                source_present_in_repo=False,
            )
        )
        for req in agent_loop.MEMORY_VAULT_APPROVAL_REQUIREMENTS:
            self.assertFalse(state[req]["satisfied"], req)

    def test_strict_mode_refuses_export(self) -> None:
        state = (
            agent_loop._desktop_memory_vault_compute_approval_state(
                self._spec(),
                approval_mode="strict",
                phase_10aa_runtime_available=True,
                operator_acknowledged_advisory_labeling=True,
                operator_supplied_identity=True,
                source_present_in_repo=True,
            )
        )
        self.assertFalse(
            state["approval_mode_supports_export"]["satisfied"],
        )

    def test_review_and_autonomous_modes_are_permitted(self) -> None:
        for mode in ("review", "autonomous"):
            state = (
                agent_loop._desktop_memory_vault_compute_approval_state(
                    self._spec(),
                    approval_mode=mode,
                    phase_10aa_runtime_available=False,
                    operator_acknowledged_advisory_labeling=False,
                    operator_supplied_identity=False,
                    source_present_in_repo=False,
                )
            )
            self.assertTrue(
                state["approval_mode_supports_export"][
                    "satisfied"
                ],
                mode,
            )


class EnablementStateTests(unittest.TestCase):

    def _spec(self):
        return dict(
            agent_loop._DESKTOP_MEMORY_VAULT_REGISTRY[0],
        )

    def _approval_all_true(self, spec):
        return (
            agent_loop._desktop_memory_vault_compute_approval_state(
                spec,
                approval_mode="review",
                phase_10aa_runtime_available=True,
                operator_acknowledged_advisory_labeling=True,
                operator_supplied_identity=True,
                source_present_in_repo=True,
            )
        )

    def test_runtime_unavailable_forces_refused(self) -> None:
        spec = self._spec()
        state = (
            agent_loop._desktop_memory_vault_compute_approval_state(
                spec,
                approval_mode="review",
                phase_10aa_runtime_available=False,
                operator_acknowledged_advisory_labeling=True,
                operator_supplied_identity=True,
                source_present_in_repo=True,
            )
        )
        enablement, _ = (
            agent_loop._desktop_memory_vault_compute_enablement_state(
                spec, approval_state=state,
            )
        )
        self.assertEqual(enablement, "refused_until_policy_update")

    def test_source_missing_forces_refused(self) -> None:
        spec = self._spec()
        state = (
            agent_loop._desktop_memory_vault_compute_approval_state(
                spec,
                approval_mode="review",
                phase_10aa_runtime_available=True,
                operator_acknowledged_advisory_labeling=True,
                operator_supplied_identity=True,
                source_present_in_repo=False,
            )
        )
        enablement, _ = (
            agent_loop._desktop_memory_vault_compute_enablement_state(
                spec, approval_state=state,
            )
        )
        self.assertEqual(enablement, "refused_until_policy_update")

    def test_runtime_available_source_present_all_met_promotes(
        self,
    ) -> None:
        spec = self._spec()
        state = self._approval_all_true(spec)
        enablement, _ = (
            agent_loop._desktop_memory_vault_compute_enablement_state(
                spec, approval_state=state,
            )
        )
        self.assertEqual(enablement, "enabled_pending_runtime")

    def test_operator_requirement_missing_disabled_by_default(
        self,
    ) -> None:
        spec = self._spec()
        state = (
            agent_loop._desktop_memory_vault_compute_approval_state(
                spec,
                approval_mode="review",
                phase_10aa_runtime_available=True,
                operator_acknowledged_advisory_labeling=False,
                operator_supplied_identity=True,
                source_present_in_repo=True,
            )
        )
        enablement, _ = (
            agent_loop._desktop_memory_vault_compute_enablement_state(
                spec, approval_state=state,
            )
        )
        self.assertEqual(enablement, "disabled_by_default")

    def test_refused_advisory_label_short_circuits(self) -> None:
        spec = self._spec()
        spec["advisory_label_rule"] = "refused_until_policy_update"
        state = self._approval_all_true(spec)
        enablement, _ = (
            agent_loop._desktop_memory_vault_compute_enablement_state(
                spec, approval_state=state,
            )
        )
        self.assertEqual(enablement, "refused_until_policy_update")


# ---------------------------------------------------------------------------
# build_desktop_memory_vault_view
# ---------------------------------------------------------------------------
class BuildMemoryVaultViewTests(unittest.TestCase):

    def test_view_shape_fields(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.build_desktop_memory_vault_view(
                controller,
            )
        for key in (
            "view_signal_version",
            "controller_path_canonical",
            "current_loop_state_status",
            "controller_loop_state_approval_mode",
            "phase_10aa_runtime_available",
            "freshness_stale_threshold_seconds",
            "operator_inputs",
            "export_categories",
            "source_kinds",
            "advisory_labels",
            "freshness_states",
            "enablement_states",
            "approval_requirements",
            "refusal_reasons",
            "exports",
            "precedence_note",
        ):
            self.assertIn(key, view, key)
        self.assertEqual(
            view["view_signal_version"], "phase-10aa-v1",
        )
        self.assertFalse(view["phase_10aa_runtime_available"])

    def test_every_export_refused_by_default(self) -> None:
        # Fail-closed default: since runtime is not available,
        # every export surfaces as `refused_until_policy_update`
        # regardless of operator input.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            (controller / ".agent-loop"
             / "claude-summary.md").write_text(
                "x", encoding="utf-8",
            )
            (controller / ".agent-loop"
             / "phase-plan.md").write_text(
                "x", encoding="utf-8",
            )
            (
                controller / ".agent-loop" / "memory" / "decision"
            ).mkdir(parents=True)
            (
                controller / ".agent-loop" / "memory" / "summary"
            ).mkdir(parents=True)
            view = agent_loop.build_desktop_memory_vault_view(
                controller,
                operator_inputs={
                    "identity": "me",
                    "acknowledged_export_ids": [
                        s["id"] for s in (
                            agent_loop._DESKTOP_MEMORY_VAULT_REGISTRY
                        )
                    ],
                },
            )
        for export in view["exports"]:
            self.assertEqual(
                export["enablement_state"],
                "refused_until_policy_update",
                export["id"],
            )

    def test_view_soft_fails_on_missing_loop_state(self) -> None:
        with TemporaryDirectory() as td:
            controller = Path(td) / "c"
            controller.mkdir()
            for name in ("AGENTS.md", "CLAUDE.md", "TASK.md",
                         "README.md"):
                (controller / name).write_text(
                    "x", encoding="utf-8",
                )
            (controller / ".agent-loop").mkdir()
            view = agent_loop.build_desktop_memory_vault_view(
                controller,
            )
        self.assertIsNone(view["current_loop_state_status"])
        self.assertIsNone(
            view["controller_loop_state_approval_mode"],
        )

    def test_operator_inputs_mirrored_in_view(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.build_desktop_memory_vault_view(
                controller,
                operator_inputs={
                    "identity": "me",
                    "acknowledged_export_ids": [
                        "durable_memory_decision_index",
                    ],
                },
            )
        self.assertEqual(view["operator_inputs"]["identity"], "me")
        self.assertIn(
            "durable_memory_decision_index",
            view["operator_inputs"]["acknowledged_export_ids"],
        )


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------
class RendererTests(unittest.TestCase):

    def test_render_includes_attribution_tags(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.build_desktop_memory_vault_view(
                controller,
            )
        output = "\n".join(
            agent_loop.render_desktop_memory_vault_text(view),
        )
        for tag in (
            "phase-10aa-v1",
            "[canonical mirror]",
            "[advisory]",
            "[vault-source]",
            "[vault-freshness]",
            "[vault-approval]",
            "[vault-enablement]",
            "[deferred-runtime]",
            "[refused]",
        ):
            self.assertIn(tag, output, tag)


# ---------------------------------------------------------------------------
# build_desktop_memory_vault_controls
# ---------------------------------------------------------------------------
class MemoryVaultControlsBuilderTests(unittest.TestCase):

    def test_controls_one_per_export(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.build_desktop_memory_vault_view(
                controller,
            )
            controls = (
                agent_loop.build_desktop_memory_vault_controls(
                    view,
                )
            )
        self.assertEqual(
            len(controls), len(view["exports"]),
        )
        for control in controls:
            self.assertEqual(
                control["dispatch_mode"], "copy_paste",
            )
            self.assertEqual(
                control["category"], "memory_vault_export_ux",
            )
            # Copy affordance stays clickable in every slice --
            # the click ONLY copies a template into the OS
            # clipboard, so it is non-mutating even when the
            # underlying export runtime is deferred (matches the
            # Phase 10Z fix-cycle affordance pattern).
            self.assertTrue(control["enabled"], control["id"])
            # The underlying export-runtime state IS gated by
            # phase_10aa_runtime_available -- surface it on a
            # distinct descriptor field so future consumers can
            # branch on it independently of the copy affordance.
            self.assertFalse(
                control["runtime_enabled"], control["id"],
            )

    def test_clipboard_payload_is_operator_visible_template(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.build_desktop_memory_vault_view(
                controller,
            )
            controls = (
                agent_loop.build_desktop_memory_vault_controls(
                    view,
                )
            )
        for control in controls:
            payload = control["clipboard_payload"]
            self.assertIn("export_id:", payload)
            self.assertIn(
                "requested_action: enable_pending_runtime",
                payload,
            )
            self.assertIn(
                "operator_identity: <NAME>",
                payload,
            )
            # No actual CLI invocation - the payload is a copy-
            # paste request template, not a shipped subcommand.
            self.assertNotIn(
                "python scripts/agent_loop.py", payload,
            )

    def test_controls_stay_clickable_when_every_operator_input_supplied(
        self,
    ) -> None:
        # Anchor the same affordance pattern shipped by the
        # Phase 10Z fix cycle: even when every operator-side
        # input is supplied and the underlying export-runtime
        # state stays `refused_until_policy_update`, the shipped
        # copy-to-clipboard button MUST stay clickable.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.build_desktop_memory_vault_view(
                controller,
                operator_inputs={
                    "identity": "me",
                    "acknowledged_export_ids": [
                        s["id"] for s in (
                            agent_loop._DESKTOP_MEMORY_VAULT_REGISTRY
                        )
                    ],
                },
            )
            controls = (
                agent_loop.build_desktop_memory_vault_controls(
                    view,
                )
            )
        self.assertTrue(controls)
        for control in controls:
            self.assertTrue(control["enabled"], control["id"])
            self.assertFalse(
                control["runtime_enabled"], control["id"],
            )
            self.assertEqual(
                control["enablement_state"],
                "refused_until_policy_update",
                control["id"],
            )

    def test_control_label_discloses_enablement_state(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.build_desktop_memory_vault_view(
                controller,
            )
            controls = (
                agent_loop.build_desktop_memory_vault_controls(
                    view,
                )
            )
        for control in controls:
            self.assertIn(
                f"[{control['enablement_state']}]",
                control["label"],
                control["id"],
            )
            self.assertIn(
                "Copy memory-vault export request template:",
                control["label"],
                control["id"],
            )

    def test_click_only_copies_template_never_runs_runtime(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.build_desktop_memory_vault_view(
                controller,
            )
            controls = (
                agent_loop.build_desktop_memory_vault_controls(
                    view,
                )
            )
        forbidden = {
            "runtime_command",
            "on_click",
            "subprocess",
            "library_call",
            "callable",
            "handler",
        }
        for control in controls:
            for field in forbidden:
                self.assertNotIn(field, control, control["id"])
            self.assertIsInstance(
                control["clipboard_payload"], str,
            )


# ---------------------------------------------------------------------------
# CLI handler
# ---------------------------------------------------------------------------
class CmdViewDesktopMemoryVaultTests(unittest.TestCase):

    def _args(self, **kwargs):
        defaults = {
            "controller_root": None,
            "operator_identity": None,
            "acknowledge_export": None,
        }
        defaults.update(kwargs)
        return argparse.Namespace(**defaults)

    def test_refuses_missing_controller_root(self) -> None:
        buf_err = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(
            buf_err,
        ):
            rc = agent_loop.cmd_view_desktop_memory_vault(
                self._args(),
            )
        self.assertEqual(rc, 2)
        self.assertIn(
            "[desktop-memory-vault] REFUSED",
            buf_err.getvalue(),
        )

    def test_refuses_invalid_controller_root(self) -> None:
        with TemporaryDirectory() as td:
            buf_err = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(
                buf_err,
            ):
                rc = agent_loop.cmd_view_desktop_memory_vault(
                    self._args(controller_root=str(td)),
                )
        self.assertEqual(rc, 2)
        self.assertIn("REFUSED", buf_err.getvalue())

    def test_phase_7c_exits_zero_on_valid_root(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            buf_out = io.StringIO()
            with redirect_stdout(buf_out):
                rc = agent_loop.cmd_view_desktop_memory_vault(
                    self._args(controller_root=str(controller)),
                )
        self.assertEqual(rc, 0)
        self.assertIn(
            "[desktop-memory-vault]", buf_out.getvalue(),
        )

    def test_handler_registered(self) -> None:
        self.assertIn(
            "view-desktop-memory-vault", agent_loop.HANDLERS,
        )

    def test_parser_accepts_subcommand_and_flags(self) -> None:
        parser = agent_loop.build_parser()
        args = parser.parse_args([
            "view-desktop-memory-vault",
            "--controller-root", ".",
            "--operator-identity", "me",
            "--acknowledge-export",
            "durable_memory_decision_index",
        ])
        self.assertEqual(args.cmd, "view-desktop-memory-vault")
        self.assertEqual(args.operator_identity, "me")
        self.assertEqual(
            args.acknowledge_export,
            ["durable_memory_decision_index"],
        )


# ---------------------------------------------------------------------------
# Integration into the Phase 10M desktop app view
# ---------------------------------------------------------------------------
class DesktopAppIntegrationTests(unittest.TestCase):

    def test_assemble_includes_memory_vault_view_key(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.assemble_desktop_app_view(controller)
        self.assertIn("memory_vault_view", view)
        sv = view["memory_vault_view"]
        self.assertIsInstance(sv, dict)
        self.assertEqual(sv["view_signal_version"], "phase-10aa-v1")

    def test_render_includes_phase_10aa_label(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.assemble_desktop_app_view(controller)
            lines = agent_loop.render_desktop_app_text(view)
        output = "\n".join(lines)
        self.assertIn(
            "=== Memory Vault Export (Phase 10AA) ===", output,
        )
        self.assertIn("phase-10aa-v1", output)


# ---------------------------------------------------------------------------
# Non-mutation invariants
# ---------------------------------------------------------------------------
class NonMutationInvariantsTests(unittest.TestCase):

    def test_view_does_not_open_socket(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            with mock.patch.object(socket, "socket") as p:
                agent_loop.build_desktop_memory_vault_view(
                    controller,
                )
        p.assert_not_called()

    def test_view_does_not_spawn_subprocess(self) -> None:
        import subprocess
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            patches = [
                mock.patch.object(subprocess, "run"),
                mock.patch.object(subprocess, "Popen"),
                mock.patch.object(subprocess, "call"),
                mock.patch.object(subprocess, "check_call"),
                mock.patch.object(subprocess, "check_output"),
                mock.patch("os.system"),
            ]
            mocks = [p.start() for p in patches]
            try:
                agent_loop.build_desktop_memory_vault_view(
                    controller,
                )
            finally:
                for p in patches:
                    p.stop()
        for m in mocks:
            m.assert_not_called()

    def test_view_does_not_invoke_halt(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            with mock.patch.object(agent_loop, "_halt") as h:
                agent_loop.build_desktop_memory_vault_view(
                    controller,
                )
        h.assert_not_called()

    def test_view_does_not_mutate_loop_state(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            ls = controller / ".agent-loop" / "loop-state.json"
            before = ls.read_bytes()
            agent_loop.build_desktop_memory_vault_view(controller)
            after = ls.read_bytes()
        self.assertEqual(before, after)

    def test_view_does_not_append_orchestrator_log(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            log_path = (
                controller / ".agent-loop" / "orchestrator.log"
            )
            agent_loop.build_desktop_memory_vault_view(controller)
        self.assertFalse(log_path.exists())

    def test_view_does_not_persist_export_cache(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            before_root = sorted(
                p.name for p in controller.iterdir()
            )
            before_dot = sorted(
                p.name
                for p in (controller / ".agent-loop").iterdir()
            )
            agent_loop.build_desktop_memory_vault_view(controller)
            after_root = sorted(
                p.name for p in controller.iterdir()
            )
            after_dot = sorted(
                p.name
                for p in (controller / ".agent-loop").iterdir()
            )
        self.assertEqual(before_root, after_root)
        self.assertEqual(before_dot, after_dot)

    def test_view_never_reads_durable_memory_json_body(self) -> None:
        # Phase 10AA fix cycle: the surface surfaces canonical-
        # artifact excerpts AND durable-memory JSON filenames,
        # but MUST NEVER surface the JSON BODY of any shipped
        # durable-memory entry. The shipped `read_memory_entry(...)`
        # primitive remains the sole reader for the JSON body.
        sentinel = "PHASE_10AA_MEMORY_BODY_SENTINEL_DO_NOT_LEAK"
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            for spec in (
                agent_loop._DESKTOP_MEMORY_VAULT_REGISTRY
            ):
                if spec["source_kind"] != (
                    "shipped_memory_json"
                ):
                    continue
                path = controller / spec["path_canonical_rel"]
                path.mkdir(parents=True, exist_ok=True)
                (path / "sentinel.json").write_text(
                    json.dumps({"body_sentinel": sentinel}),
                    encoding="utf-8",
                )
            view = agent_loop.build_desktop_memory_vault_view(
                controller,
            )
            rendered = "\n".join(
                agent_loop.render_desktop_memory_vault_text(view),
            )
        serialized_view = json.dumps(view, default=str)
        self.assertNotIn(sentinel, serialized_view)
        self.assertNotIn(sentinel, rendered)

    def test_view_never_reads_canonical_artifact_tail_past_cap(
        self,
    ) -> None:
        # A canonical-artifact mirror source LARGER than the
        # excerpt cap surfaces the head only; a sentinel written
        # past the cap MUST NOT appear in the assembled view or
        # rendered text.
        cap = agent_loop.MEMORY_VAULT_EXCERPT_BYTE_LIMIT
        sentinel = "PHASE_10AA_TAIL_SENTINEL_DO_NOT_LEAK"
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            (controller / ".agent-loop"
             / "claude-summary.md").write_text(
                ("A" * cap) + sentinel, encoding="utf-8",
            )
            view = agent_loop.build_desktop_memory_vault_view(
                controller,
            )
            rendered = "\n".join(
                agent_loop.render_desktop_memory_vault_text(view),
            )
        self.assertNotIn(sentinel, json.dumps(view, default=str))
        self.assertNotIn(sentinel, rendered)

    def test_view_surfaces_readable_canonical_mirror_excerpt(
        self,
    ) -> None:
        # Phase 10AA fix cycle contract: when a canonical-
        # artifact mirror source exists, its head-bounded excerpt
        # MUST appear in the assembled view and the rendered
        # text. Without this, the shipped Phase 10AA surface
        # would only report metadata and the phase contract
        # ("bounded human-facing memory-vault export surface with
        # optional human-readable memory views") would drift out
        # of scope again.
        marker = "PHASE_10AA_EXCERPT_BODY_MARKER"
        body = f"# summary\n{marker}\nbody line two\n"
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            # Bypass Windows universal newline translation so
            # `body` matches the file byte-for-byte.
            (controller / ".agent-loop"
             / "claude-summary.md").write_bytes(
                body.encode("utf-8"),
            )
            view = agent_loop.build_desktop_memory_vault_view(
                controller,
            )
            rendered = "\n".join(
                agent_loop.render_desktop_memory_vault_text(view),
            )
        target_export = next(
            e for e in view["exports"]
            if e["id"] == "decision_summary_from_claude_summary"
        )
        self.assertEqual(target_export["excerpt_text"], body)
        self.assertFalse(target_export["excerpt_truncated"])
        self.assertIn(marker, rendered)
        # The excerpt line prefix is present in the rendered
        # text so a downstream tool can identify the excerpt
        # rows unambiguously.
        self.assertIn("[vault-excerpt]", rendered)

    def test_view_surfaces_durable_memory_filename_index(
        self,
    ) -> None:
        # Phase 10AA fix cycle: when a durable-memory JSON
        # directory source exists, the shipped view MUST surface
        # a name-only index of its most-recent shipped `.json`
        # filenames so the operator sees WHICH shipped decision /
        # summary entries exist without letting the surface read
        # the JSON body.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            decision_dir = (
                controller / ".agent-loop" / "memory" / "decision"
            )
            decision_dir.mkdir(parents=True)
            for name in (
                "20260701T000000Z-first.json",
                "20260702T000000Z-second.json",
            ):
                (decision_dir / name).write_text(
                    json.dumps({"stub": True}),
                    encoding="utf-8",
                )
            view = agent_loop.build_desktop_memory_vault_view(
                controller,
            )
            rendered = "\n".join(
                agent_loop.render_desktop_memory_vault_text(view),
            )
        target = next(
            e for e in view["exports"]
            if e["id"] == "durable_memory_decision_index"
        )
        self.assertIsNone(target["excerpt_text"])
        self.assertEqual(
            target["entry_index"],
            [
                "20260702T000000Z-second.json",
                "20260701T000000Z-first.json",
            ],
        )
        self.assertIn("[vault-entry-index]", rendered)
        self.assertIn(
            "20260702T000000Z-second.json", rendered,
        )

    def test_phase_10i_library_callable_cap_not_widened(
        self,
    ) -> None:
        # The Phase 10AA memory-vault export UX MUST NOT
        # introduce any new library-callable control. Every
        # descriptor is `dispatch_mode='copy_paste'`.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.build_desktop_memory_vault_view(
                controller,
            )
            controls = (
                agent_loop.build_desktop_memory_vault_controls(
                    view,
                )
            )
        for control in controls:
            self.assertEqual(
                control["dispatch_mode"], "copy_paste",
                control["id"],
            )
        library_callable = [
            c for c in agent_loop._EXTERNAL_UI_CONTROL_REGISTRY
            if c.get("dispatch_mode") == "library_call"
        ]
        self.assertEqual(
            {c["id"] for c in library_callable},
            {
                "view-external-status",
                "view-external-controls",
                "inspect-external-target",
            },
        )


if __name__ == "__main__":
    unittest.main()
