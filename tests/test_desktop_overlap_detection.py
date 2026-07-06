"""Phase 10AC - Overlap-Safe Detection Initial Slice tests.

Exercises:
  - module-level constants (signal version, precedence note,
    closed enumerations)
  - operator-input normalizer
  - closed signal registry + descriptor validator (re-uses the
    Phase 10AB `CONCURRENCY_INVALIDATION_TRIGGERS` and
    `CONCURRENCY_RECOVERY_ACTIONS` closed vocabularies verbatim)
  - pure mtime-pair probe (`Path.stat()` only; NEVER reads
    artifact BODY content)
  - per-signal evaluate helper (triggered / severity / state
    matrix)
  - overall-state derivation helper (refusal short-circuit,
    warning aggregation, unknown fallback, no-signal baseline)
  - `build_desktop_overlap_detection_view(...)` shape + soft-
    fail on missing loop-state + no-trigger baseline
  - renderer per-line attribution
  - `build_desktop_overlap_detection_controls(...)` widget
    shape (COPY-PASTE only; every button clickable per the
    Phase 10Z / 10AA / 10AB fix-cycle affordance pattern)
  - `cmd_view_desktop_overlap_detection(...)` CLI + Phase 7C
  - integration into `assemble_desktop_app_view(...)` +
    `render_desktop_app_text(...)`
  - non-mutation invariants (no socket, no subprocess, no
    orchestrator.log append, no loop-state mutation, no
    `_halt(...)`, no Phase 10I library-callable cap widening,
    no persisted detection cache, no actual concurrent Codex/
    Claude runtime launched, NEVER reads artifact BODY content)
"""
from __future__ import annotations

import argparse
import io
import json
import os
import socket
import sys
import time
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
                "Phase 10AC - Overlap-Safe Detection Initial "
                "Slice"
            ),
            "task": "phase-10ac-test",
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


def _write_bytes(path: Path, body: bytes, mtime: float) -> None:
    """Write bytes and force the on-disk mtime to a deterministic
    value so signal-triggered / no-trigger assertions are stable
    across the shipped test suite (Windows universal-newline
    translation is also bypassed by writing bytes directly).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    os.utime(path, (mtime, mtime))


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
class ConstantsTests(unittest.TestCase):

    def test_signal_version(self) -> None:
        self.assertEqual(
            agent_loop.DESKTOP_OVERLAP_DETECTION_SIGNAL_VERSION,
            "phase-10ac-v1",
        )

    def test_precedence_note_pins_phase_10ac_contract(self) -> None:
        note = (
            agent_loop.DESKTOP_OVERLAP_DETECTION_PRECEDENCE_NOTE
        )
        for needle in (
            "Phase 10AC",
            "Phase 10AB Controlled Concurrent Operation "
            "Contract",
            "CONCURRENCY_INVALIDATION_TRIGGERS",
            "CONCURRENCY_RECOVERY_ACTIONS",
            "Phase 10I",
            "NEVER launches or coordinates any actual "
            "concurrent Codex/Claude runtime",
            "NEVER reads any artifact BODY content",
        ):
            self.assertIn(needle, note, needle)

    def test_signal_states_closed_enum(self) -> None:
        self.assertEqual(
            agent_loop.OVERLAP_DETECTION_SIGNAL_STATES,
            (
                "no_signal",
                "signal_detected",
                "refused_pending_recovery",
                "unknown",
            ),
        )

    def test_severity_levels_closed_enum(self) -> None:
        self.assertEqual(
            agent_loop.OVERLAP_DETECTION_SEVERITY_LEVELS,
            ("info", "warning", "refusal", "unknown"),
        )

    def test_reuses_phase_10ab_invalidation_triggers(self) -> None:
        # Every registered signal's `invalidation_trigger` MUST
        # be a member of the shipped Phase 10AB closed
        # enumeration.
        for spec in (
            agent_loop._DESKTOP_OVERLAP_DETECTION_SIGNAL_REGISTRY
        ):
            self.assertIn(
                spec["invalidation_trigger"],
                agent_loop.CONCURRENCY_INVALIDATION_TRIGGERS,
                spec["id"],
            )

    def test_reuses_phase_10ab_recovery_actions(self) -> None:
        for spec in (
            agent_loop._DESKTOP_OVERLAP_DETECTION_SIGNAL_REGISTRY
        ):
            self.assertIn(
                spec["recovery_action"],
                agent_loop.CONCURRENCY_RECOVERY_ACTIONS,
                spec["id"],
            )


# ---------------------------------------------------------------------------
# Registry + descriptor validator
# ---------------------------------------------------------------------------
class RegistryTests(unittest.TestCase):

    def test_registry_ships_five_signals(self) -> None:
        self.assertEqual(
            len(
                agent_loop._DESKTOP_OVERLAP_DETECTION_SIGNAL_REGISTRY
            ),
            5,
        )

    def test_every_registry_entry_passes_validator(self) -> None:
        for spec in (
            agent_loop._DESKTOP_OVERLAP_DETECTION_SIGNAL_REGISTRY
        ):
            agent_loop._desktop_overlap_detection_validate_signal_descriptor(
                spec,
            )


class ValidatorTests(unittest.TestCase):

    def _valid(self):
        return {
            "id": "x",
            "display_name": "X",
            "invalidation_trigger": (
                "codex_review_verdict_changed"
            ),
            "recovery_action": "re_read_codex_review",
            "reference_path_canonical_rel": (
                ".agent-loop/codex-review.md"
            ),
            "target_path_canonical_rel": (
                ".agent-loop/claude-summary.md"
            ),
            "severity_when_triggered": "refusal",
            "description": "d",
            "safety_copy": "s",
            "deferred_runtime_marker": "m",
            "refusal_reason_template": "t",
        }

    def test_non_dict_refuses(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_overlap_detection_validate_signal_descriptor(
                ["not", "a", "dict"],
            )

    def test_missing_string_field_refuses(self) -> None:
        spec = self._valid()
        del spec["invalidation_trigger"]
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_overlap_detection_validate_signal_descriptor(
                spec,
            )

    def test_unknown_invalidation_trigger_refuses(self) -> None:
        spec = self._valid()
        spec["invalidation_trigger"] = "not_a_trigger"
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_overlap_detection_validate_signal_descriptor(
                spec,
            )

    def test_unknown_recovery_action_refuses(self) -> None:
        spec = self._valid()
        spec["recovery_action"] = "not_a_recovery"
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_overlap_detection_validate_signal_descriptor(
                spec,
            )

    def test_unknown_severity_refuses(self) -> None:
        spec = self._valid()
        spec["severity_when_triggered"] = "not_a_severity"
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_overlap_detection_validate_signal_descriptor(
                spec,
            )

    def test_backslash_path_refuses(self) -> None:
        spec = self._valid()
        spec["reference_path_canonical_rel"] = (
            ".agent-loop\\codex-review.md"
        )
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_overlap_detection_validate_signal_descriptor(
                spec,
            )

    def test_absolute_path_refuses(self) -> None:
        spec = self._valid()
        spec["target_path_canonical_rel"] = "/etc/passwd"
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_overlap_detection_validate_signal_descriptor(
                spec,
            )

    def test_drive_prefix_refuses(self) -> None:
        spec = self._valid()
        spec["reference_path_canonical_rel"] = "C:/x"
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_overlap_detection_validate_signal_descriptor(
                spec,
            )

    def test_parent_traversal_refuses(self) -> None:
        spec = self._valid()
        spec["target_path_canonical_rel"] = "a/../b"
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_overlap_detection_validate_signal_descriptor(
                spec,
            )


# ---------------------------------------------------------------------------
# Operator-input normalizer
# ---------------------------------------------------------------------------
class OperatorInputsNormalizerTests(unittest.TestCase):

    def test_none_returns_empty_defaults(self) -> None:
        got = (
            agent_loop._desktop_overlap_detection_normalize_operator_inputs(
                None,
            )
        )
        self.assertEqual(got["identity"], "")
        self.assertEqual(
            got["acknowledged_signal_ids"], frozenset(),
        )

    def test_non_dict_refuses(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_overlap_detection_normalize_operator_inputs(
                ["not", "a", "dict"],
            )

    def test_iterable_ids_normalized(self) -> None:
        got = (
            agent_loop._desktop_overlap_detection_normalize_operator_inputs(
                {
                    "identity": " me ",
                    "acknowledged_signal_ids": [
                        "codex_review_supersedes_claude_"
                        "summary",
                    ],
                },
            )
        )
        self.assertEqual(got["identity"], "me")
        self.assertIn(
            "codex_review_supersedes_claude_summary",
            got["acknowledged_signal_ids"],
        )

    def test_wrong_identity_type_refuses(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_overlap_detection_normalize_operator_inputs(
                {"identity": 42},
            )

    def test_wrong_ack_type_refuses(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_overlap_detection_normalize_operator_inputs(
                {
                    "identity": "me",
                    "acknowledged_signal_ids": "not-iterable",
                },
            )


# ---------------------------------------------------------------------------
# Mtime-pair probe
# ---------------------------------------------------------------------------
class MtimePairProbeTests(unittest.TestCase):

    def test_both_missing_returns_none_flag(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            probe = (
                agent_loop._desktop_overlap_detection_probe_mtime_pair(
                    controller,
                    ".agent-loop/codex-review.md",
                    ".agent-loop/claude-summary.md",
                )
            )
        self.assertFalse(probe["reference_exists"])
        self.assertFalse(probe["target_exists"])
        self.assertIsNone(probe["reference_newer_than_target"])

    def test_reference_only_reports_none_flag(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            _write_bytes(
                controller / ".agent-loop" / "codex-review.md",
                b"x",
                mtime=time.time(),
            )
            probe = (
                agent_loop._desktop_overlap_detection_probe_mtime_pair(
                    controller,
                    ".agent-loop/codex-review.md",
                    ".agent-loop/claude-summary.md",
                )
            )
        self.assertTrue(probe["reference_exists"])
        self.assertFalse(probe["target_exists"])
        self.assertIsNone(probe["reference_newer_than_target"])

    def test_reference_newer_returns_true(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            base = time.time()
            _write_bytes(
                controller / ".agent-loop" / "claude-summary.md",
                b"target",
                mtime=base,
            )
            _write_bytes(
                controller / ".agent-loop" / "codex-review.md",
                b"reference",
                mtime=base + 60,
            )
            probe = (
                agent_loop._desktop_overlap_detection_probe_mtime_pair(
                    controller,
                    ".agent-loop/codex-review.md",
                    ".agent-loop/claude-summary.md",
                )
            )
        self.assertTrue(probe["reference_newer_than_target"])

    def test_reference_older_returns_false(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            base = time.time()
            _write_bytes(
                controller / ".agent-loop" / "codex-review.md",
                b"reference",
                mtime=base,
            )
            _write_bytes(
                controller / ".agent-loop" / "claude-summary.md",
                b"target",
                mtime=base + 60,
            )
            probe = (
                agent_loop._desktop_overlap_detection_probe_mtime_pair(
                    controller,
                    ".agent-loop/codex-review.md",
                    ".agent-loop/claude-summary.md",
                )
            )
        self.assertFalse(probe["reference_newer_than_target"])

    def test_probe_never_reads_body(self) -> None:
        sentinel = (
            "PHASE_10AC_MTIME_PAIR_SENTINEL_DO_NOT_LEAK"
        )
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            base = time.time()
            _write_bytes(
                controller / ".agent-loop" / "codex-review.md",
                sentinel.encode("utf-8"),
                mtime=base,
            )
            _write_bytes(
                controller / ".agent-loop" / "claude-summary.md",
                sentinel.encode("utf-8"),
                mtime=base,
            )
            probe = (
                agent_loop._desktop_overlap_detection_probe_mtime_pair(
                    controller,
                    ".agent-loop/codex-review.md",
                    ".agent-loop/claude-summary.md",
                )
            )
        self.assertNotIn(
            sentinel, json.dumps(probe, default=str),
        )


# ---------------------------------------------------------------------------
# Per-signal evaluate helper
# ---------------------------------------------------------------------------
class EvaluateSignalTests(unittest.TestCase):

    def _spec(self):
        return next(
            dict(s) for s in (
                agent_loop._DESKTOP_OVERLAP_DETECTION_SIGNAL_REGISTRY
            )
            if s["id"] == "codex_review_supersedes_claude_summary"
        )

    def test_reference_newer_and_refusal_severity_produces_refusal(
        self,
    ) -> None:
        spec = self._spec()
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            base = time.time()
            _write_bytes(
                controller / ".agent-loop" / "claude-summary.md",
                b"target",
                mtime=base,
            )
            _write_bytes(
                controller / ".agent-loop" / "codex-review.md",
                b"reference",
                mtime=base + 60,
            )
            envelope = (
                agent_loop._desktop_overlap_detection_evaluate_signal(
                    spec, controller,
                )
            )
        self.assertTrue(envelope["triggered"])
        self.assertEqual(envelope["severity"], "refusal")
        self.assertEqual(
            envelope["signal_state"],
            "refused_pending_recovery",
        )

    def test_reference_newer_and_warning_severity_produces_warning(
        self,
    ) -> None:
        spec = next(
            dict(s) for s in (
                agent_loop._DESKTOP_OVERLAP_DETECTION_SIGNAL_REGISTRY
            )
            if s["id"] == "loop_state_advanced_past_summary"
        )
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            base = time.time()
            _write_bytes(
                controller / ".agent-loop" / "claude-summary.md",
                b"target",
                mtime=base,
            )
            _write_bytes(
                controller / ".agent-loop" / "loop-state.json",
                b"reference",
                mtime=base + 60,
            )
            envelope = (
                agent_loop._desktop_overlap_detection_evaluate_signal(
                    spec, controller,
                )
            )
        self.assertTrue(envelope["triggered"])
        self.assertEqual(envelope["severity"], "warning")
        self.assertEqual(
            envelope["signal_state"], "signal_detected",
        )

    def test_reference_older_produces_no_signal(self) -> None:
        spec = self._spec()
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            base = time.time()
            _write_bytes(
                controller / ".agent-loop" / "codex-review.md",
                b"reference",
                mtime=base,
            )
            _write_bytes(
                controller / ".agent-loop" / "claude-summary.md",
                b"target",
                mtime=base + 60,
            )
            envelope = (
                agent_loop._desktop_overlap_detection_evaluate_signal(
                    spec, controller,
                )
            )
        self.assertFalse(envelope["triggered"])
        self.assertEqual(envelope["signal_state"], "no_signal")
        self.assertEqual(envelope["severity"], "info")

    def test_missing_artifact_produces_unknown(self) -> None:
        spec = self._spec()
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            envelope = (
                agent_loop._desktop_overlap_detection_evaluate_signal(
                    spec, controller,
                )
            )
        self.assertFalse(envelope["triggered"])
        self.assertEqual(envelope["signal_state"], "unknown")
        self.assertEqual(envelope["severity"], "unknown")


# ---------------------------------------------------------------------------
# Overall-state derivation
# ---------------------------------------------------------------------------
class OverallStateTests(unittest.TestCase):

    def _sig(self, state, severity, sid="s"):
        return {"id": sid, "signal_state": state, "severity": severity}

    def test_no_signals_returns_no_signal(self) -> None:
        got = (
            agent_loop._desktop_overlap_detection_derive_overall_state(
                [
                    self._sig("no_signal", "info", "a"),
                    self._sig("no_signal", "info", "b"),
                ],
            )
        )
        self.assertEqual(
            got["overall_signal_state"], "no_signal",
        )
        self.assertEqual(got["overall_severity"], "info")

    def test_any_refusal_short_circuits(self) -> None:
        got = (
            agent_loop._desktop_overlap_detection_derive_overall_state(
                [
                    self._sig("no_signal", "info", "a"),
                    self._sig("signal_detected", "warning", "b"),
                    self._sig(
                        "refused_pending_recovery", "refusal", "c",
                    ),
                ],
            )
        )
        self.assertEqual(
            got["overall_signal_state"],
            "refused_pending_recovery",
        )
        self.assertEqual(got["overall_severity"], "refusal")
        self.assertIn("c", got["refusal_signal_ids"])

    def test_warning_only_returns_signal_detected(self) -> None:
        got = (
            agent_loop._desktop_overlap_detection_derive_overall_state(
                [
                    self._sig("no_signal", "info", "a"),
                    self._sig("signal_detected", "warning", "b"),
                ],
            )
        )
        self.assertEqual(
            got["overall_signal_state"], "signal_detected",
        )
        self.assertEqual(got["overall_severity"], "warning")

    def test_all_unknown_returns_unknown(self) -> None:
        got = (
            agent_loop._desktop_overlap_detection_derive_overall_state(
                [
                    self._sig("unknown", "unknown", "a"),
                    self._sig("unknown", "unknown", "b"),
                ],
            )
        )
        self.assertEqual(
            got["overall_signal_state"], "unknown",
        )
        self.assertEqual(got["overall_severity"], "unknown")
        self.assertIn("every Phase 10AC signal is `unknown`", got["reason"])

    # -----------------------------------------------------------------
    # Phase 10AC fix cycle: mixed-known / mixed-unknown regression.
    # Previously `_desktop_overlap_detection_derive_overall_state` only
    # returned `unknown` when every signal was `unknown`; otherwise it
    # fell through to `no_signal` even when some overlap evidence was
    # unknowable. The fixed helper MUST fail closed to `unknown` when
    # any required overlap evidence is unknown (i.e. any signal reports
    # `unknown`) and no refusal / warning signal supersedes it.
    # -----------------------------------------------------------------

    def test_mixed_no_signal_and_unknown_returns_unknown(self) -> None:
        got = (
            agent_loop._desktop_overlap_detection_derive_overall_state(
                [
                    self._sig("no_signal", "info", "a"),
                    self._sig("unknown", "unknown", "b"),
                ],
            )
        )
        self.assertEqual(
            got["overall_signal_state"], "unknown",
        )
        self.assertEqual(got["overall_severity"], "unknown")
        self.assertEqual(got["unknown_signal_ids"], ["b"])
        self.assertEqual(got["refusal_signal_ids"], [])
        self.assertEqual(got["warning_signal_ids"], [])
        # The fixed reason must explicitly call out the partial-unknown
        # (i.e. mixed-known) case rather than pretending every signal
        # is unknown.
        self.assertIn("one or more required Phase 10AC signals", got["reason"])
        self.assertNotIn("every Phase 10AC signal is `unknown`", got["reason"])

    def test_mixed_all_no_signal_but_first_unknown_returns_unknown(
        self,
    ) -> None:
        got = (
            agent_loop._desktop_overlap_detection_derive_overall_state(
                [
                    self._sig("unknown", "unknown", "u1"),
                    self._sig("no_signal", "info", "n1"),
                    self._sig("no_signal", "info", "n2"),
                ],
            )
        )
        self.assertEqual(
            got["overall_signal_state"], "unknown",
        )
        self.assertEqual(got["overall_severity"], "unknown")
        self.assertEqual(got["unknown_signal_ids"], ["u1"])

    def test_refusal_still_short_circuits_over_partial_unknown(
        self,
    ) -> None:
        # A refused signal in a mixed-known set MUST still short-
        # circuit the aggregate to `refused_pending_recovery`; the
        # partial-unknown fix does not weaken the refusal short-
        # circuit.
        got = (
            agent_loop._desktop_overlap_detection_derive_overall_state(
                [
                    self._sig("no_signal", "info", "n"),
                    self._sig("unknown", "unknown", "u"),
                    self._sig(
                        "refused_pending_recovery", "refusal", "r",
                    ),
                ],
            )
        )
        self.assertEqual(
            got["overall_signal_state"],
            "refused_pending_recovery",
        )
        self.assertEqual(got["overall_severity"], "refusal")
        self.assertEqual(got["refusal_signal_ids"], ["r"])
        self.assertEqual(got["unknown_signal_ids"], ["u"])

    def test_warning_still_wins_over_partial_unknown(self) -> None:
        # A warning signal in a mixed-known set still surfaces as
        # `signal_detected` (the warning is a real observation that
        # deserves surfacing); the partial-unknown fix only replaces
        # the previous `no_signal` fall-through with `unknown`.
        got = (
            agent_loop._desktop_overlap_detection_derive_overall_state(
                [
                    self._sig("signal_detected", "warning", "w"),
                    self._sig("unknown", "unknown", "u"),
                ],
            )
        )
        self.assertEqual(
            got["overall_signal_state"], "signal_detected",
        )
        self.assertEqual(got["overall_severity"], "warning")
        self.assertEqual(got["warning_signal_ids"], ["w"])
        self.assertEqual(got["unknown_signal_ids"], ["u"])

    def test_reason_partial_unknown_names_required_evidence(self) -> None:
        # Anchor the reason vocabulary: the partial-unknown reason
        # must talk about "required overlap evidence" being unknowable
        # so the surface can never be mistaken for "no signal / overlap
        # safe" when in fact some evidence is missing.
        got = (
            agent_loop._desktop_overlap_detection_derive_overall_state(
                [
                    self._sig("no_signal", "info", "n"),
                    self._sig("unknown", "unknown", "u"),
                ],
            )
        )
        self.assertIn("required overlap evidence", got["reason"])
        self.assertIn("unknowable", got["reason"])


# ---------------------------------------------------------------------------
# build_desktop_overlap_detection_view
# ---------------------------------------------------------------------------
class BuildOverlapDetectionViewTests(unittest.TestCase):

    def test_view_shape_fields(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_overlap_detection_view(
                    controller,
                )
            )
        for key in (
            "view_signal_version",
            "controller_path_canonical",
            "current_loop_state_status",
            "controller_loop_state_approval_mode",
            "current_loop_state_phase",
            "current_loop_state_sub_phase",
            "current_loop_state_cycle_count",
            "phase_10ac_runtime_available",
            "operator_inputs",
            "signal_states",
            "severity_levels",
            "invalidation_triggers",
            "recovery_actions",
            "signals",
            "overall",
            "precedence_note",
        ):
            self.assertIn(key, view, key)
        self.assertEqual(
            view["view_signal_version"], "phase-10ac-v1",
        )
        self.assertFalse(view["phase_10ac_runtime_available"])

    def test_no_targets_baseline_is_unknown(self) -> None:
        # A fresh controller with no target artifacts surfaces
        # every signal as `unknown` and the overall state as
        # `unknown` (fail-closed baseline).
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_overlap_detection_view(
                    controller,
                )
            )
        for sig in view["signals"]:
            self.assertEqual(
                sig["signal_state"], "unknown", sig["id"],
            )
        self.assertEqual(
            view["overall"]["overall_signal_state"], "unknown",
        )

    def test_all_targets_current_produces_no_signal(self) -> None:
        # When every reference artifact is OLDER than the
        # target, every signal reports `no_signal` and the
        # overall state is `no_signal`.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            base = time.time()
            for path in (
                ".agent-loop/codex-review.md",
                ".agent-loop/claude-prompt.md",
                ".agent-loop/fix-prompt.md",
                ".agent-loop/current-phase.md",
            ):
                _write_bytes(
                    controller / path, b"reference",
                    mtime=base,
                )
            # Force loop-state.json mtime to be older than the
            # summary so the shipped loop-state advance signal
            # also reports `no_signal`.
            _write_bytes(
                controller / ".agent-loop" / "loop-state.json",
                (controller / ".agent-loop"
                 / "loop-state.json").read_bytes(),
                mtime=base,
            )
            _write_bytes(
                controller / ".agent-loop" / "claude-summary.md",
                b"target",
                mtime=base + 60,
            )
            view = (
                agent_loop.build_desktop_overlap_detection_view(
                    controller,
                )
            )
        for sig in view["signals"]:
            self.assertEqual(
                sig["signal_state"], "no_signal", sig["id"],
            )
        self.assertEqual(
            view["overall"]["overall_signal_state"], "no_signal",
        )

    def test_high_severity_trigger_produces_refusal_overall(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            base = time.time()
            _write_bytes(
                controller / ".agent-loop" / "claude-summary.md",
                b"target",
                mtime=base,
            )
            _write_bytes(
                controller / ".agent-loop" / "codex-review.md",
                b"reference",
                mtime=base + 60,
            )
            view = (
                agent_loop.build_desktop_overlap_detection_view(
                    controller,
                )
            )
        self.assertEqual(
            view["overall"]["overall_signal_state"],
            "refused_pending_recovery",
        )
        self.assertIn(
            "codex_review_supersedes_claude_summary",
            view["overall"]["refusal_signal_ids"],
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
            view = (
                agent_loop.build_desktop_overlap_detection_view(
                    controller,
                )
            )
        self.assertIsNone(view["current_loop_state_status"])
        self.assertIsNone(
            view["controller_loop_state_approval_mode"],
        )


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------
class RendererTests(unittest.TestCase):

    def test_render_includes_attribution_tags(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            base = time.time()
            _write_bytes(
                controller / ".agent-loop" / "claude-summary.md",
                b"target",
                mtime=base,
            )
            _write_bytes(
                controller / ".agent-loop" / "codex-review.md",
                b"reference",
                mtime=base + 60,
            )
            view = (
                agent_loop.build_desktop_overlap_detection_view(
                    controller,
                )
            )
        output = "\n".join(
            agent_loop.render_desktop_overlap_detection_text(view),
        )
        for tag in (
            "phase-10ac-v1",
            "[canonical mirror]",
            "[advisory]",
            "[overlap-signal]",
            "[overlap-severity]",
            "[overlap-recovery]",
            "[overlap-overall]",
            "[deferred-runtime]",
            "[refused]",
        ):
            self.assertIn(tag, output, tag)


# ---------------------------------------------------------------------------
# build_desktop_overlap_detection_controls
# ---------------------------------------------------------------------------
class OverlapDetectionControlsBuilderTests(unittest.TestCase):

    def test_controls_one_per_signal(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_overlap_detection_view(
                    controller,
                )
            )
            controls = (
                agent_loop.build_desktop_overlap_detection_controls(
                    view,
                )
            )
        self.assertEqual(
            len(controls), len(view["signals"]),
        )
        for control in controls:
            self.assertEqual(
                control["dispatch_mode"], "copy_paste",
            )
            self.assertEqual(
                control["category"],
                "overlap_detection_ux",
            )
            self.assertTrue(control["enabled"], control["id"])
            self.assertFalse(
                control["runtime_enabled"], control["id"],
            )

    def test_clipboard_payload_is_acknowledgement_template(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_overlap_detection_view(
                    controller,
                )
            )
            controls = (
                agent_loop.build_desktop_overlap_detection_controls(
                    view,
                )
            )
        for control in controls:
            payload = control["clipboard_payload"]
            self.assertIn("signal_id:", payload)
            self.assertIn("invalidation_trigger:", payload)
            self.assertIn(
                "requested_action: acknowledge_and_recover",
                payload,
            )
            self.assertIn(
                "operator_identity: <NAME>", payload,
            )
            self.assertNotIn(
                "python scripts/agent_loop.py", payload,
            )

    def test_control_label_discloses_signal_state(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_overlap_detection_view(
                    controller,
                )
            )
            controls = (
                agent_loop.build_desktop_overlap_detection_controls(
                    view,
                )
            )
        for control in controls:
            self.assertIn(
                f"[{control['signal_state']}]",
                control["label"],
                control["id"],
            )
            self.assertIn(
                "Copy overlap-recovery acknowledgement "
                "template:",
                control["label"],
                control["id"],
            )

    def test_click_only_copies_template_never_runs_runtime(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_overlap_detection_view(
                    controller,
                )
            )
            controls = (
                agent_loop.build_desktop_overlap_detection_controls(
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
class CmdViewDesktopOverlapDetectionTests(unittest.TestCase):

    def _args(self, **kwargs):
        defaults = {
            "controller_root": None,
            "operator_identity": None,
            "acknowledge_signal": None,
        }
        defaults.update(kwargs)
        return argparse.Namespace(**defaults)

    def test_refuses_missing_controller_root(self) -> None:
        buf_err = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(
            buf_err,
        ):
            rc = agent_loop.cmd_view_desktop_overlap_detection(
                self._args(),
            )
        self.assertEqual(rc, 2)
        self.assertIn(
            "[desktop-overlap-detection] REFUSED",
            buf_err.getvalue(),
        )

    def test_refuses_invalid_controller_root(self) -> None:
        with TemporaryDirectory() as td:
            buf_err = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(
                buf_err,
            ):
                rc = (
                    agent_loop.cmd_view_desktop_overlap_detection(
                        self._args(controller_root=str(td)),
                    )
                )
        self.assertEqual(rc, 2)
        self.assertIn("REFUSED", buf_err.getvalue())

    def test_phase_7c_exits_zero_on_valid_root(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            buf_out = io.StringIO()
            with redirect_stdout(buf_out):
                rc = (
                    agent_loop.cmd_view_desktop_overlap_detection(
                        self._args(
                            controller_root=str(controller),
                        ),
                    )
                )
        self.assertEqual(rc, 0)
        self.assertIn(
            "[desktop-overlap-detection]", buf_out.getvalue(),
        )

    def test_handler_registered(self) -> None:
        self.assertIn(
            "view-desktop-overlap-detection",
            agent_loop.HANDLERS,
        )

    def test_parser_accepts_subcommand_and_flags(self) -> None:
        parser = agent_loop.build_parser()
        args = parser.parse_args([
            "view-desktop-overlap-detection",
            "--controller-root", ".",
            "--operator-identity", "me",
            "--acknowledge-signal",
            "codex_review_supersedes_claude_summary",
        ])
        self.assertEqual(
            args.cmd, "view-desktop-overlap-detection",
        )
        self.assertEqual(args.operator_identity, "me")
        self.assertEqual(
            args.acknowledge_signal,
            ["codex_review_supersedes_claude_summary"],
        )


# ---------------------------------------------------------------------------
# Integration into the Phase 10M desktop app view
# ---------------------------------------------------------------------------
class DesktopAppIntegrationTests(unittest.TestCase):

    def test_assemble_includes_overlap_detection_view_key(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.assemble_desktop_app_view(controller)
        self.assertIn("overlap_detection_view", view)
        sv = view["overlap_detection_view"]
        self.assertIsInstance(sv, dict)
        self.assertEqual(sv["view_signal_version"], "phase-10ac-v1")

    def test_render_includes_phase_10ac_label(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.assemble_desktop_app_view(controller)
            lines = agent_loop.render_desktop_app_text(view)
        output = "\n".join(lines)
        self.assertIn(
            "=== Overlap-Safe Detection (Phase 10AC) ===",
            output,
        )
        self.assertIn("phase-10ac-v1", output)


# ---------------------------------------------------------------------------
# Non-mutation invariants
# ---------------------------------------------------------------------------
class NonMutationInvariantsTests(unittest.TestCase):

    def test_view_does_not_open_socket(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            with mock.patch.object(socket, "socket") as p:
                agent_loop.build_desktop_overlap_detection_view(
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
                agent_loop.build_desktop_overlap_detection_view(
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
                agent_loop.build_desktop_overlap_detection_view(
                    controller,
                )
        h.assert_not_called()

    def test_view_does_not_mutate_loop_state(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            ls = controller / ".agent-loop" / "loop-state.json"
            before = ls.read_bytes()
            agent_loop.build_desktop_overlap_detection_view(
                controller,
            )
            after = ls.read_bytes()
        self.assertEqual(before, after)

    def test_view_does_not_append_orchestrator_log(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            log_path = (
                controller / ".agent-loop" / "orchestrator.log"
            )
            agent_loop.build_desktop_overlap_detection_view(
                controller,
            )
        self.assertFalse(log_path.exists())

    def test_view_does_not_persist_detection_cache(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            before_root = sorted(
                p.name for p in controller.iterdir()
            )
            before_dot = sorted(
                p.name
                for p in (controller / ".agent-loop").iterdir()
            )
            agent_loop.build_desktop_overlap_detection_view(
                controller,
            )
            after_root = sorted(
                p.name for p in controller.iterdir()
            )
            after_dot = sorted(
                p.name
                for p in (controller / ".agent-loop").iterdir()
            )
        self.assertEqual(before_root, after_root)
        self.assertEqual(before_dot, after_dot)

    def test_view_never_reads_artifact_body(self) -> None:
        # Write unique sentinels into every reference / target
        # artifact and assert the sentinel does NOT appear in
        # the assembled view dict OR rendered text.
        sentinels = []
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            base = time.time()
            for i, spec in enumerate(
                agent_loop._DESKTOP_OVERLAP_DETECTION_SIGNAL_REGISTRY
            ):
                for j, key in enumerate((
                    "reference_path_canonical_rel",
                    "target_path_canonical_rel",
                )):
                    sentinel = (
                        f"PHASE_10AC_ARTIFACT_BODY_SENTINEL_"
                        f"{i}_{j}_DO_NOT_LEAK"
                    )
                    path = controller / spec[key]
                    _write_bytes(
                        path,
                        sentinel.encode("utf-8"),
                        mtime=base + i,
                    )
                    sentinels.append(sentinel)
            view = (
                agent_loop.build_desktop_overlap_detection_view(
                    controller,
                )
            )
            rendered = "\n".join(
                agent_loop.render_desktop_overlap_detection_text(
                    view,
                ),
            )
        serialized_view = json.dumps(view, default=str)
        for sentinel in sentinels:
            self.assertNotIn(
                sentinel, serialized_view, sentinel,
            )
            self.assertNotIn(sentinel, rendered, sentinel)

    def test_view_never_launches_concurrent_runtime(self) -> None:
        import threading
        import multiprocessing
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            patches = [
                mock.patch.object(threading, "Thread"),
                mock.patch.object(multiprocessing, "Process"),
                mock.patch.object(multiprocessing, "Pool"),
            ]
            mocks = [p.start() for p in patches]
            try:
                agent_loop.build_desktop_overlap_detection_view(
                    controller,
                )
            finally:
                for p in patches:
                    p.stop()
        for m in mocks:
            m.assert_not_called()

    def test_phase_10i_library_callable_cap_not_widened(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_overlap_detection_view(
                    controller,
                )
            )
            controls = (
                agent_loop.build_desktop_overlap_detection_controls(
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


# ---------------------------------------------------------------------------
# Phase 10AC fix cycle: shipped runtime refusal gate
# `enforce_overlap_safe_runtime_gate(...)`.
#
# The gate MUST raise HaltError(HALTED_OVERLAP_UNSAFE_CONTEXT, ...) when
# the aggregate `overall_signal_state` is `refused_pending_recovery`, and
# MUST return None silently for `no_signal`, `signal_detected`, and
# `unknown`. The gate MUST remain bounded per the Phase 10AC contract:
# no subprocess spawn, no socket open, no concurrent-runtime launch, no
# background watcher, no loop-state mutation.
# ---------------------------------------------------------------------------
class OverlapSafeRuntimeGateTests(unittest.TestCase):

    def _fake_view(self, state, refusal_ids=(), reason="synthetic"):
        return {
            "overall": {
                "overall_signal_state": state,
                "overall_severity": {
                    "refused_pending_recovery": "refusal",
                    "signal_detected": "warning",
                    "unknown": "unknown",
                    "no_signal": "info",
                }[state],
                "refusal_signal_ids": list(refusal_ids),
                "warning_signal_ids": [],
                "unknown_signal_ids": [],
                "reason": reason,
                "triggered_count": len(refusal_ids),
            },
            "signals": [],
        }

    def test_halt_status_constant_exposed(self) -> None:
        self.assertEqual(
            agent_loop.HALTED_OVERLAP_UNSAFE_CONTEXT,
            "halted_overlap_unsafe_context",
        )

    def test_refused_state_raises_halt_error(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            with mock.patch.object(
                agent_loop,
                "build_desktop_overlap_detection_view",
                return_value=self._fake_view(
                    "refused_pending_recovery",
                    refusal_ids=["codex_review_supersedes_claude_summary"],
                    reason="synthetic-refusal",
                ),
            ):
                with self.assertRaises(agent_loop.HaltError) as cm:
                    agent_loop.enforce_overlap_safe_runtime_gate(controller)
        self.assertEqual(
            cm.exception.status,
            agent_loop.HALTED_OVERLAP_UNSAFE_CONTEXT,
        )
        self.assertIn(
            "codex_review_supersedes_claude_summary",
            cm.exception.reason,
        )
        self.assertIn("synthetic-refusal", cm.exception.reason)
        self.assertIn(
            "view-desktop-overlap-detection", cm.exception.reason,
        )

    def test_no_signal_returns_none_silently(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            with mock.patch.object(
                agent_loop,
                "build_desktop_overlap_detection_view",
                return_value=self._fake_view("no_signal"),
            ):
                self.assertIsNone(
                    agent_loop.enforce_overlap_safe_runtime_gate(
                        controller,
                    ),
                )

    def test_signal_detected_returns_none_silently(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            with mock.patch.object(
                agent_loop,
                "build_desktop_overlap_detection_view",
                return_value=self._fake_view("signal_detected"),
            ):
                self.assertIsNone(
                    agent_loop.enforce_overlap_safe_runtime_gate(
                        controller,
                    ),
                )

    def test_unknown_returns_none_silently(self) -> None:
        # Per the Phase 10AC contract only `refused_pending_recovery`
        # raises the gate. `unknown` is fail-closed at the reporting
        # layer (the caller sees the aggregate as unknown) but does
        # NOT itself refuse the shipped runtime gate; a future runtime
        # slice may widen the gate to also refuse on `unknown`.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            with mock.patch.object(
                agent_loop,
                "build_desktop_overlap_detection_view",
                return_value=self._fake_view("unknown"),
            ):
                self.assertIsNone(
                    agent_loop.enforce_overlap_safe_runtime_gate(
                        controller,
                    ),
                )

    def test_gate_fires_from_real_view_on_stale_summary(self) -> None:
        # End-to-end: write a controller where codex-review.md is
        # newer than claude-summary.md (a real
        # `codex_review_supersedes_claude_summary` refusal) and
        # assert the gate raises the Phase 10AC halt status.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            base = time.time()
            _write_bytes(
                controller / ".agent-loop" / "claude-summary.md",
                b"# Claude Implementation Summary\n",
                mtime=base,
            )
            _write_bytes(
                controller / ".agent-loop" / "codex-review.md",
                b"# Codex Review\n",
                mtime=base + 60,
            )
            with self.assertRaises(agent_loop.HaltError) as cm:
                agent_loop.enforce_overlap_safe_runtime_gate(controller)
        self.assertEqual(
            cm.exception.status,
            agent_loop.HALTED_OVERLAP_UNSAFE_CONTEXT,
        )

    def test_gate_does_not_spawn_subprocess(self) -> None:
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
                try:
                    agent_loop.enforce_overlap_safe_runtime_gate(controller)
                except agent_loop.HaltError:
                    pass
            finally:
                for p in patches:
                    p.stop()
        for m in mocks:
            m.assert_not_called()

    def test_gate_does_not_open_socket(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            with mock.patch.object(socket, "socket") as p:
                try:
                    agent_loop.enforce_overlap_safe_runtime_gate(controller)
                except agent_loop.HaltError:
                    pass
        p.assert_not_called()

    def test_gate_does_not_launch_concurrent_runtime(self) -> None:
        import threading
        import multiprocessing
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            patches = [
                mock.patch.object(threading, "Thread"),
                mock.patch.object(multiprocessing, "Process"),
                mock.patch.object(multiprocessing, "Pool"),
            ]
            mocks = [p.start() for p in patches]
            try:
                try:
                    agent_loop.enforce_overlap_safe_runtime_gate(controller)
                except agent_loop.HaltError:
                    pass
            finally:
                for p in patches:
                    p.stop()
        for m in mocks:
            m.assert_not_called()

    def test_gate_does_not_mutate_loop_state(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            ls = controller / ".agent-loop" / "loop-state.json"
            before = ls.read_bytes()
            try:
                agent_loop.enforce_overlap_safe_runtime_gate(controller)
            except agent_loop.HaltError:
                pass
            after = ls.read_bytes()
        self.assertEqual(before, after)


# ---------------------------------------------------------------------------
# Phase 10AC fix cycle: `_run_normal_cycle_from_increment` integration.
#
# The shipped runtime gate is wired at the pre-Codex-review point in
# `_run_normal_cycle_from_increment`. It MUST persist
# HALTED_OVERLAP_UNSAFE_CONTEXT to loop-state.json when the overlap-
# detection aggregate reports `refused_pending_recovery`. It MUST NOT
# fire on `no_signal`, `signal_detected`, or `unknown` aggregate
# states. Placement rationale: at the post-Claude / post-evidence
# point the freshly written `claude-summary.md` is the newest canonical
# artifact, so any `reference-newer-than-summary` refusal signal is a
# real observable overlap anomaly rather than a benign cycle-start
# pre-condition.
# ---------------------------------------------------------------------------
class RunNormalCycleOverlapGateTests(unittest.TestCase):

    def _write_controller(
        self, root: Path, approval_mode: str = "autonomous",
    ) -> Path:
        root.mkdir(parents=True, exist_ok=True)
        (root / "AGENTS.md").write_text("agents\n", encoding="utf-8")
        (root / "CLAUDE.md").write_text("claude\n", encoding="utf-8")
        (root / "TASK.md").write_text("# TASK.md\n", encoding="utf-8")
        (root / "README.md").write_text("readme\n", encoding="utf-8")
        (root / "ROADMAP.md").write_text("roadmap\n", encoding="utf-8")
        (root / ".agent-loop").mkdir()
        (root / ".agent-loop" / "loop-state.json").write_text(
            json.dumps({
                "phase": "Phase 10 - Future Product Features",
                "sub_phase": (
                    "Phase 10AC - Overlap-Safe Detection "
                    "Initial Slice"
                ),
                "task": "phase-10ac-runtime-gate-test",
                "status": "awaiting_claude_implementation",
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
        (root / ".agent-loop" / "claude-prompt.md").write_text(
            "# Claude Code Task\n\n## Phase\nP\n\n## Objective\no\n\n"
            "## Context\nc\n\n## Required work\n- x\n\n"
            "## Constraints\n- y\n\n## Required output\n- z\n",
            encoding="utf-8",
        )
        return root

    def _fake_claude_adapter_factory(self, phase, sub_phase):
        def _factory():
            class _A:
                default_model_id = "stub-claude"

                def invoke(self, prompt_path, summary_path):
                    summary_text = (
                        "# Claude Implementation Summary\n\n"
                        f"## Phase\n{phase} "
                        f"(sub-phase: {sub_phase})\n\n"
                        "## Task\nt\n\n"
                        "## Files changed\n- f: change\n\n"
                        "## What was implemented\n- x\n\n"
                        "## What was not implemented\n- y\n\n"
                        "## Tests added or changed\n- None\n\n"
                        "## Validation run\n- Not run\n\n"
                        "## Assumptions\n- None\n\n"
                        "## Risk areas\n- None identified\n"
                    )
                    summary_path.write_text(
                        summary_text, encoding="utf-8",
                    )
                    return agent_loop.ExecutionResult(
                        exit_code=0,
                        model_id="stub-claude",
                        duration_seconds=0.0,
                    )
            return _A()
        return _factory

    def _stub_evidence(self):
        return (
            mock.patch.object(
                agent_loop, "invoke_run_checks", return_value=None,
            ),
            mock.patch.object(
                agent_loop,
                "validate_evidence_files",
                return_value=None,
            ),
        )

    def test_run_normal_cycle_halts_on_refused_pending_recovery(self) -> None:
        # Placement rationale: the shipped runtime gate fires at the
        # post-Claude / post-evidence point in
        # `_run_normal_cycle_from_increment` (BEFORE Codex review
        # begins). At that point the freshly written claude-summary.md
        # is the newest canonical artifact for a clean cycle, so any
        # reference-newer-than-summary refusal signal is a real
        # observable overlap anomaly.
        with TemporaryDirectory() as td:
            controller = self._write_controller(
                Path(td) / "c", approval_mode="autonomous",
            )
            state_path = controller / ".agent-loop" / "loop-state.json"
            fake_view = {
                "overall": {
                    "overall_signal_state": (
                        "refused_pending_recovery"
                    ),
                    "overall_severity": "refusal",
                    "refusal_signal_ids": [
                        "codex_review_supersedes_claude_summary",
                    ],
                    "warning_signal_ids": [],
                    "unknown_signal_ids": [],
                    "reason": "synthetic-refusal-for-runtime-gate",
                    "triggered_count": 1,
                },
                "signals": [],
            }
            claude_factory = self._fake_claude_adapter_factory(
                "Phase 10 - Future Product Features",
                "Phase 10AC - Overlap-Safe Detection Initial Slice",
            )
            checks_patch, evidence_patch = self._stub_evidence()
            with mock.patch.object(
                agent_loop,
                "build_desktop_overlap_detection_view",
                return_value=fake_view,
            ), mock.patch.object(
                agent_loop,
                "make_claude_adapter",
                claude_factory,
            ), checks_patch, evidence_patch:
                rc = agent_loop.run_normal_cycle(controller)
            after = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(rc, 2)
        self.assertEqual(
            after["status"],
            agent_loop.HALTED_OVERLAP_UNSAFE_CONTEXT,
        )

    def _run_with_aggregate(self, controller: Path, aggregate: dict) -> str:
        """Drive `run_normal_cycle` with a synthetic overlap-detection
        aggregate and return the post-run loop-state status. Claude is
        stubbed to write a valid summary and evidence is stubbed as
        already-captured so the cycle reaches the pre-Codex-review
        gate. Codex is stubbed to return a null review so the cycle
        deterministically halts AFTER the Phase 10AC gate at a
        downstream `halted_input_missing` branch. The point of these
        tests is to prove the overlap gate did NOT fire; the specific
        downstream halt status is not the assertion.
        """
        state_path = controller / ".agent-loop" / "loop-state.json"
        fake_view = {
            "overall": aggregate,
            "signals": [],
        }
        claude_factory = self._fake_claude_adapter_factory(
            "Phase 10 - Future Product Features",
            "Phase 10AC - Overlap-Safe Detection Initial Slice",
        )

        def _fake_codex_factory():
            class _C:
                default_model_id = "stub-codex"

                def wait_for_review(self, review_path):
                    return agent_loop.ExecutionResult(
                        exit_code=2,
                        model_id=None,
                        duration_seconds=0.0,
                    )
            return _C()

        checks_patch, evidence_patch = self._stub_evidence()
        with mock.patch.object(
            agent_loop,
            "build_desktop_overlap_detection_view",
            return_value=fake_view,
        ), mock.patch.object(
            agent_loop, "make_claude_adapter", claude_factory,
        ), mock.patch.object(
            agent_loop, "make_codex_adapter", _fake_codex_factory,
        ), checks_patch, evidence_patch:
            agent_loop.run_normal_cycle(controller)
        return json.loads(
            state_path.read_text(encoding="utf-8"),
        )["status"]

    def test_run_normal_cycle_advances_past_gate_on_no_signal(self) -> None:
        with TemporaryDirectory() as td:
            controller = self._write_controller(
                Path(td) / "c", approval_mode="autonomous",
            )
            status = self._run_with_aggregate(
                controller,
                {
                    "overall_signal_state": "no_signal",
                    "overall_severity": "info",
                    "refusal_signal_ids": [],
                    "warning_signal_ids": [],
                    "unknown_signal_ids": [],
                    "reason": "synthetic-no-signal",
                    "triggered_count": 0,
                },
            )
        self.assertNotEqual(
            status, agent_loop.HALTED_OVERLAP_UNSAFE_CONTEXT,
        )

    def test_run_normal_cycle_advances_past_gate_on_signal_detected(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = self._write_controller(
                Path(td) / "c", approval_mode="autonomous",
            )
            status = self._run_with_aggregate(
                controller,
                {
                    "overall_signal_state": "signal_detected",
                    "overall_severity": "warning",
                    "refusal_signal_ids": [],
                    "warning_signal_ids": [
                        "loop_state_advanced_past_summary",
                    ],
                    "unknown_signal_ids": [],
                    "reason": "synthetic-warning",
                    "triggered_count": 1,
                },
            )
        self.assertNotEqual(
            status, agent_loop.HALTED_OVERLAP_UNSAFE_CONTEXT,
        )

    def test_run_normal_cycle_advances_past_gate_on_unknown(self) -> None:
        with TemporaryDirectory() as td:
            controller = self._write_controller(
                Path(td) / "c", approval_mode="autonomous",
            )
            status = self._run_with_aggregate(
                controller,
                {
                    "overall_signal_state": "unknown",
                    "overall_severity": "unknown",
                    "refusal_signal_ids": [],
                    "warning_signal_ids": [],
                    "unknown_signal_ids": ["u1", "u2"],
                    "reason": "synthetic-unknown",
                    "triggered_count": 0,
                },
            )
        self.assertNotEqual(
            status, agent_loop.HALTED_OVERLAP_UNSAFE_CONTEXT,
        )


if __name__ == "__main__":
    unittest.main()
