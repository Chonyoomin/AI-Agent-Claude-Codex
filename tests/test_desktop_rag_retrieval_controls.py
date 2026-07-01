"""Phase 10W - RAG Local Index And Retrieval Controls tests.

Exercises:
  - module-level constants (signal version, precedence note,
    bounded caps, closed enumerations)
  - operator-input normalizer
  - controller-local scope check
  - bounded per-source content read (byte cap enforced)
  - tokenizer / score / excerpt helpers
  - approval-state computation
  - `build_desktop_rag_retrieval_controls_view(...)` shape +
    per-source retrieval-eligibility state + soft-fail on
    missing loop-state
  - `retrieve_local_rag_excerpts(...)` positive + every closed
    refusal branch (empty query, too-long query, missing
    identity, missing acknowledgement, no sources selected,
    approval mode strict, path outside controller root)
  - top-K clamp behavior
  - renderer per-line attribution
  - `build_desktop_rag_retrieval_controls(...)` widget shape
  - `cmd_view_desktop_rag_retrieval_controls(...)` and
    `cmd_run_local_rag_retrieval(...)` CLI handlers
  - integration into `assemble_desktop_app_view(...)` +
    `render_desktop_app_text(...)`
  - non-mutation invariants (no socket, no subprocess, no
    orchestrator.log append, no loop-state mutation, no
    `_halt(...)`, no Phase 10I cap widening, no persisted
    retrieval cache)
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
    (td / "AGENTS.md").write_text(
        "AGENTS standards content\n", encoding="utf-8",
    )
    (td / "CLAUDE.md").write_text("claude\n", encoding="utf-8")
    (td / "TASK.md").write_text(
        "# TASK.md\n## Human Objective\n\nphase 10w local rag "
        "retrieval controls task\n",
        encoding="utf-8",
    )
    (td / "README.md").write_text(
        "readme content about claude phase 10w retrieval\n",
        encoding="utf-8",
    )
    (td / ".agent-loop").mkdir()
    (td / ".agent-loop" / "loop-state.json").write_text(
        json.dumps({
            "phase": "Phase 10 - Future Product Features",
            "sub_phase": (
                "Phase 10W - RAG Local Index And Retrieval "
                "Controls"
            ),
            "task": "phase-10w-test",
            "status": status,
            "cycle_count": 1,
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
    (td / ".agent-loop" / "codex-review.md").write_text(
        "review notes\n", encoding="utf-8",
    )
    (td / ".agent-loop" / "git-diff.patch").write_text(
        "diff\n", encoding="utf-8",
    )
    return td


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
class ConstantsTests(unittest.TestCase):

    def test_signal_version(self) -> None:
        self.assertEqual(
            agent_loop.DESKTOP_RAG_RETRIEVAL_CONTROLS_SIGNAL_VERSION,
            "phase-10w-v1",
        )

    def test_precedence_note_pins_phase_10w_contract(self) -> None:
        note = (
            agent_loop.DESKTOP_RAG_RETRIEVAL_CONTROLS_PRECEDENCE_NOTE
        )
        for needle in (
            "Phase 10W",
            "Phase 10V",
            "Phase 10I",
            "Phase 10O",
            "CONTROLLER-LOCAL",
            "NEVER opens a network socket",
            "NEVER spawns a subprocess",
            "NEVER persists an index",
            "NEVER widens the Phase 10I cap",
        ):
            self.assertIn(needle, note)

    def test_bounded_caps(self) -> None:
        self.assertEqual(
            agent_loop.RAG_RETRIEVAL_QUERY_CHAR_CAP, 512,
        )
        self.assertEqual(
            agent_loop.RAG_RETRIEVAL_PER_SOURCE_BYTE_CAP, 8192,
        )
        self.assertEqual(agent_loop.RAG_RETRIEVAL_TOP_K_CAP, 5)
        self.assertEqual(
            agent_loop.RAG_RETRIEVAL_TOP_K_DEFAULT, 3,
        )
        self.assertEqual(
            agent_loop.RAG_RETRIEVAL_EXCERPT_WINDOW_CHARS, 240,
        )

    def test_index_states_closed_enum(self) -> None:
        self.assertEqual(
            agent_loop.RAG_RETRIEVAL_INDEX_STATES,
            (
                "empty",
                "built_this_invocation",
                "refused_until_policy_update",
            ),
        )

    def test_ranking_modes_closed_enum(self) -> None:
        self.assertEqual(
            agent_loop.RAG_RETRIEVAL_RANKING_MODES,
            (
                "term_overlap_bounded",
                "refused_until_policy_update",
            ),
        )

    def test_approval_requirements_closed_enum(self) -> None:
        self.assertEqual(
            agent_loop.RAG_RETRIEVAL_APPROVAL_REQUIREMENTS,
            (
                "operator_acknowledged_advisory_labeling",
                "operator_supplied_identity",
                "approval_mode_supports_retrieval",
                "phase_10w_runtime_available",
                "controller_local_scope_only",
                "query_within_char_cap",
                "per_source_within_byte_cap",
            ),
        )

    def test_refusal_reasons_closed_enum(self) -> None:
        self.assertEqual(
            agent_loop.RAG_RETRIEVAL_REFUSAL_REASONS,
            (
                "approval_mode_strict",
                "operator_identity_missing",
                "operator_acknowledgement_missing",
                "query_empty",
                "query_too_long",
                "no_sources_selected",
                "source_path_missing",
                "source_path_outside_controller_root",
                "runtime_not_available",
            ),
        )

    def test_permitted_approval_modes(self) -> None:
        self.assertEqual(
            agent_loop.RAG_RETRIEVAL_PERMITTED_APPROVAL_MODES,
            frozenset({"review", "autonomous"}),
        )


# ---------------------------------------------------------------------------
# Operator-input normalizer
# ---------------------------------------------------------------------------
class OperatorInputsNormalizerTests(unittest.TestCase):

    def test_none_returns_empty_defaults(self) -> None:
        result = (
            agent_loop._desktop_rag_retrieval_normalize_operator_inputs(
                None,
            )
        )
        self.assertEqual(result["identity"], "")
        self.assertEqual(
            result["acknowledged_source_ids"], frozenset(),
        )

    def test_strips_identity_whitespace(self) -> None:
        result = (
            agent_loop._desktop_rag_retrieval_normalize_operator_inputs(
                {"identity": "  me  "},
            )
        )
        self.assertEqual(result["identity"], "me")

    def test_coerces_list_to_frozenset(self) -> None:
        result = (
            agent_loop._desktop_rag_retrieval_normalize_operator_inputs(
                {
                    "acknowledged_source_ids": [
                        "repo_local_docs_readme",
                    ],
                },
            )
        )
        self.assertIsInstance(
            result["acknowledged_source_ids"], frozenset,
        )

    def test_refuses_non_dict(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_rag_retrieval_normalize_operator_inputs(
                ["nope"],
            )

    def test_refuses_non_string_identity(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_rag_retrieval_normalize_operator_inputs(
                {"identity": 42},
            )

    def test_refuses_non_iterable_ack_set(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_rag_retrieval_normalize_operator_inputs(
                {"acknowledged_source_ids": 42},
            )


# ---------------------------------------------------------------------------
# Controller-local scope check
# ---------------------------------------------------------------------------
class ControllerLocalScopeTests(unittest.TestCase):

    def test_inside_root_returns_true(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            target = controller / "README.md"
            self.assertTrue(
                agent_loop._desktop_rag_retrieval_source_path_inside_controller_root(
                    controller, target,
                )
            )

    def test_sibling_dir_returns_false(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            sibling = Path(td) / "sibling.md"
            sibling.write_text("x", encoding="utf-8")
            self.assertFalse(
                agent_loop._desktop_rag_retrieval_source_path_inside_controller_root(
                    controller, sibling,
                )
            )


# ---------------------------------------------------------------------------
# Bounded source read
# ---------------------------------------------------------------------------
class BoundedReadTests(unittest.TestCase):

    def test_small_file_read_completely(self) -> None:
        with TemporaryDirectory() as td:
            p = Path(td) / "small.txt"
            p.write_text("hello world", encoding="utf-8")
            text, n, truncated = (
                agent_loop._desktop_rag_retrieval_read_source_bounded(
                    p,
                )
            )
        self.assertEqual(text, "hello world")
        self.assertEqual(n, 11)
        self.assertFalse(truncated)

    def test_large_file_truncated_at_byte_cap(self) -> None:
        cap = agent_loop.RAG_RETRIEVAL_PER_SOURCE_BYTE_CAP
        with TemporaryDirectory() as td:
            p = Path(td) / "big.txt"
            p.write_bytes(b"a" * (cap + 1024))
            text, n, truncated = (
                agent_loop._desktop_rag_retrieval_read_source_bounded(
                    p,
                )
            )
        self.assertEqual(n, cap)
        self.assertTrue(truncated)
        self.assertEqual(len(text), cap)

    def test_missing_file_returns_empty(self) -> None:
        with TemporaryDirectory() as td:
            p = Path(td) / "nope.txt"
            text, n, truncated = (
                agent_loop._desktop_rag_retrieval_read_source_bounded(
                    p,
                )
            )
        self.assertEqual(text, "")
        self.assertEqual(n, 0)
        self.assertFalse(truncated)


# ---------------------------------------------------------------------------
# Tokenizer / score / excerpt helpers
# ---------------------------------------------------------------------------
class TokenizeScoreExcerptTests(unittest.TestCase):

    def test_tokenize_lowercase_alphanumeric(self) -> None:
        self.assertEqual(
            agent_loop._desktop_rag_retrieval_tokenize(
                "Hello, World! Phase-10w",
            ),
            ["hello", "world", "phase", "10w"],
        )

    def test_score_full_overlap(self) -> None:
        score, matched = (
            agent_loop._desktop_rag_retrieval_score_source(
                ["foo", "bar", "baz"],
                ["foo", "bar"],
            )
        )
        self.assertEqual(score, 1.0)
        self.assertEqual(matched, ("foo", "bar"))

    def test_score_partial_overlap(self) -> None:
        score, matched = (
            agent_loop._desktop_rag_retrieval_score_source(
                ["foo", "bar", "baz"],
                ["foo", "bar", "quux"],
            )
        )
        self.assertAlmostEqual(score, 2.0 / 3.0)
        self.assertEqual(sorted(matched), ["bar", "foo"])

    def test_score_empty_inputs(self) -> None:
        self.assertEqual(
            agent_loop._desktop_rag_retrieval_score_source(
                [], ["foo"],
            ),
            (0.0, ()),
        )
        self.assertEqual(
            agent_loop._desktop_rag_retrieval_score_source(
                ["foo"], [],
            ),
            (0.0, ()),
        )

    def test_excerpt_bounded_window(self) -> None:
        text = "prefix " * 500 + "TARGET HERE " + "suffix " * 500
        excerpt = (
            agent_loop._desktop_rag_retrieval_extract_excerpt(
                text, ["target"],
            )
        )
        self.assertLessEqual(
            len(excerpt),
            agent_loop.RAG_RETRIEVAL_EXCERPT_WINDOW_CHARS,
        )
        self.assertIn("target", excerpt.lower())

    def test_excerpt_no_match_returns_leading_window(
        self,
    ) -> None:
        excerpt = (
            agent_loop._desktop_rag_retrieval_extract_excerpt(
                "aaaaaaaaaa", ["nomatch"],
            )
        )
        self.assertEqual(excerpt, "aaaaaaaaaa")


# ---------------------------------------------------------------------------
# Approval-state computation
# ---------------------------------------------------------------------------
class ApprovalStateTests(unittest.TestCase):

    def test_all_unsatisfied_default(self) -> None:
        state = (
            agent_loop._desktop_rag_retrieval_compute_approval_state(
                approval_mode=None,
                phase_10w_runtime_available=False,
                operator_acknowledged_advisory_labeling=False,
                operator_supplied_identity=False,
                controller_local_scope_only=False,
                query_within_char_cap=False,
                per_source_within_byte_cap=False,
            )
        )
        for req in (
            agent_loop.RAG_RETRIEVAL_APPROVAL_REQUIREMENTS
        ):
            self.assertFalse(state[req]["satisfied"], req)

    def test_strict_mode_refuses(self) -> None:
        state = (
            agent_loop._desktop_rag_retrieval_compute_approval_state(
                approval_mode="strict",
                phase_10w_runtime_available=True,
                operator_acknowledged_advisory_labeling=True,
                operator_supplied_identity=True,
                controller_local_scope_only=True,
                query_within_char_cap=True,
                per_source_within_byte_cap=True,
            )
        )
        self.assertFalse(
            state["approval_mode_supports_retrieval"][
                "satisfied"
            ],
        )

    def test_review_mode_supports(self) -> None:
        state = (
            agent_loop._desktop_rag_retrieval_compute_approval_state(
                approval_mode="review",
                phase_10w_runtime_available=False,
                operator_acknowledged_advisory_labeling=False,
                operator_supplied_identity=False,
                controller_local_scope_only=False,
                query_within_char_cap=False,
                per_source_within_byte_cap=False,
            )
        )
        self.assertTrue(
            state["approval_mode_supports_retrieval"][
                "satisfied"
            ],
        )


# ---------------------------------------------------------------------------
# build_desktop_rag_retrieval_controls_view
# ---------------------------------------------------------------------------
class BuildControlsViewTests(unittest.TestCase):

    def test_view_shape_fields(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_rag_retrieval_controls_view(
                    controller,
                )
            )
        for key in (
            "view_signal_version",
            "controller_path_canonical",
            "current_loop_state_status",
            "controller_loop_state_approval_mode",
            "phase_10w_runtime_available",
            "index_state_default",
            "ranking_mode_default",
            "query_char_cap",
            "per_source_byte_cap",
            "top_k_cap",
            "top_k_default",
            "excerpt_window_chars",
            "operator_inputs",
            "index_states",
            "ranking_modes",
            "approval_requirements",
            "refusal_reasons",
            "sources",
            "precedence_note",
        ):
            self.assertIn(key, view, key)
        self.assertEqual(
            view["view_signal_version"], "phase-10w-v1",
        )
        self.assertTrue(view["phase_10w_runtime_available"])

    def test_source_ineligible_without_operator_inputs(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_rag_retrieval_controls_view(
                    controller,
                )
            )
        for source in view["sources"]:
            self.assertFalse(
                source["retrieval_eligible"], source["id"],
            )

    def test_source_eligible_when_inputs_supplied(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_rag_retrieval_controls_view(
                    controller,
                    operator_inputs={
                        "identity": "me",
                        "acknowledged_source_ids": [
                            "repo_local_docs_readme",
                        ],
                    },
                )
            )
        readme = next(
            s for s in view["sources"]
            if s["id"] == "repo_local_docs_readme"
        )
        self.assertTrue(readme["retrieval_eligible"])
        # Sources NOT acknowledged stay ineligible.
        other = next(
            s for s in view["sources"]
            if s["id"] != "repo_local_docs_readme"
        )
        self.assertFalse(other["retrieval_eligible"])

    def test_view_soft_fails_on_missing_loop_state(self) -> None:
        with TemporaryDirectory() as td:
            controller = Path(td) / "c"
            controller.mkdir()
            (controller / "AGENTS.md").write_text(
                "x", encoding="utf-8",
            )
            (controller / "CLAUDE.md").write_text(
                "x", encoding="utf-8",
            )
            (controller / "TASK.md").write_text(
                "x", encoding="utf-8",
            )
            (controller / "README.md").write_text(
                "x", encoding="utf-8",
            )
            (controller / ".agent-loop").mkdir()
            view = (
                agent_loop.build_desktop_rag_retrieval_controls_view(
                    controller,
                )
            )
        self.assertIsNone(view["current_loop_state_status"])
        self.assertIsNone(
            view["controller_loop_state_approval_mode"],
        )


# ---------------------------------------------------------------------------
# retrieve_local_rag_excerpts (positive + every refusal branch)
# ---------------------------------------------------------------------------
class RetrieveExcerptsTests(unittest.TestCase):

    def test_positive_returns_bounded_excerpts(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            result = agent_loop.retrieve_local_rag_excerpts(
                controller,
                operator_inputs={
                    "identity": "me",
                    "acknowledged_source_ids": [
                        "repo_local_docs_readme",
                    ],
                },
                query="claude phase",
                top_k=2,
            )
        self.assertIsNone(result["refusal_reason"])
        self.assertEqual(
            result["index_state"], "built_this_invocation",
        )
        self.assertGreaterEqual(len(result["excerpts"]), 1)
        for excerpt in result["excerpts"]:
            self.assertEqual(
                excerpt["provenance_tag"], "[rag-advisory]",
            )
            self.assertLessEqual(
                len(excerpt["excerpt_text"]),
                agent_loop.RAG_RETRIEVAL_EXCERPT_WINDOW_CHARS,
            )

    def test_empty_query_refuses(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            result = agent_loop.retrieve_local_rag_excerpts(
                controller,
                operator_inputs={
                    "identity": "me",
                    "acknowledged_source_ids": [
                        "repo_local_docs_readme",
                    ],
                },
                query="",
            )
        self.assertEqual(
            result["refusal_reason"], "query_empty",
        )

    def test_too_long_query_refuses(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            long_query = "x" * (
                agent_loop.RAG_RETRIEVAL_QUERY_CHAR_CAP + 1
            )
            result = agent_loop.retrieve_local_rag_excerpts(
                controller,
                operator_inputs={
                    "identity": "me",
                    "acknowledged_source_ids": [
                        "repo_local_docs_readme",
                    ],
                },
                query=long_query,
            )
        self.assertEqual(
            result["refusal_reason"], "query_too_long",
        )

    def test_missing_identity_refuses(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            result = agent_loop.retrieve_local_rag_excerpts(
                controller,
                operator_inputs={
                    "acknowledged_source_ids": [
                        "repo_local_docs_readme",
                    ],
                },
                query="claude",
            )
        self.assertEqual(
            result["refusal_reason"],
            "operator_identity_missing",
        )

    def test_no_acknowledgement_refuses(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            result = agent_loop.retrieve_local_rag_excerpts(
                controller,
                operator_inputs={"identity": "me"},
                query="claude",
            )
        self.assertEqual(
            result["refusal_reason"],
            "operator_acknowledgement_missing",
        )

    def test_strict_approval_mode_refuses(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(
                Path(td) / "c", approval_mode="strict",
            )
            result = agent_loop.retrieve_local_rag_excerpts(
                controller,
                operator_inputs={
                    "identity": "me",
                    "acknowledged_source_ids": [
                        "repo_local_docs_readme",
                    ],
                },
                query="claude",
            )
        self.assertEqual(
            result["refusal_reason"], "approval_mode_strict",
        )

    def test_no_sources_selected_refuses_when_paths_absent(
        self,
    ) -> None:
        # Delete every registered source path so nothing gets
        # indexed; retrieval MUST refuse with
        # `no_sources_selected`.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            for spec in (
                agent_loop._DESKTOP_RAG_SOURCE_SELECTION_REGISTRY
            ):
                p = controller / spec["path_canonical_rel"]
                if p.exists():
                    p.unlink()
            result = agent_loop.retrieve_local_rag_excerpts(
                controller,
                operator_inputs={
                    "identity": "me",
                    "acknowledged_source_ids": [
                        "repo_local_docs_readme",
                    ],
                },
                query="claude",
            )
        self.assertEqual(
            result["refusal_reason"], "no_sources_selected",
        )

    def test_top_k_clamped_to_cap(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            result = agent_loop.retrieve_local_rag_excerpts(
                controller,
                operator_inputs={
                    "identity": "me",
                    "acknowledged_source_ids": [
                        s["id"]
                        for s in (
                            agent_loop._DESKTOP_RAG_SOURCE_SELECTION_REGISTRY
                        )
                    ],
                },
                query="claude phase",
                top_k=999,
            )
        # Top-K MUST clamp to cap regardless of caller request.
        self.assertLessEqual(
            result["top_k_returned"],
            agent_loop.RAG_RETRIEVAL_TOP_K_CAP,
        )

    def test_bounded_read_per_source(self) -> None:
        # Inflate one source above the byte cap and verify
        # `bytes_read` on the returned excerpt is exactly the
        # cap (not the actual on-disk size).
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            readme = controller / "README.md"
            padding = "phase " * 4000
            readme.write_text(padding, encoding="utf-8")
            result = agent_loop.retrieve_local_rag_excerpts(
                controller,
                operator_inputs={
                    "identity": "me",
                    "acknowledged_source_ids": [
                        "repo_local_docs_readme",
                    ],
                },
                query="phase",
                top_k=1,
            )
        self.assertIsNone(result["refusal_reason"])
        excerpt = result["excerpts"][0]
        self.assertEqual(
            excerpt["bytes_read"],
            agent_loop.RAG_RETRIEVAL_PER_SOURCE_BYTE_CAP,
        )
        self.assertTrue(excerpt["source_was_truncated"])


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------
class RendererTests(unittest.TestCase):

    def test_render_controls_view(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_rag_retrieval_controls_view(
                    controller,
                )
            )
        output = "\n".join(
            agent_loop.render_desktop_rag_retrieval_controls_text(
                view,
            )
        )
        self.assertIn("phase-10w-v1", output)
        for tag in (
            "[refused]",
            "[rag-retrieval]",
            "[rag-provenance]",
            "[rag-freshness]",
            "[rag-approval]",
            "[advisory]",
            "[canonical mirror]",
        ):
            self.assertIn(tag, output, tag)

    def test_render_retrieval_result_positive(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            result = agent_loop.retrieve_local_rag_excerpts(
                controller,
                operator_inputs={
                    "identity": "me",
                    "acknowledged_source_ids": [
                        "repo_local_docs_readme",
                    ],
                },
                query="claude",
            )
        output = "\n".join(
            agent_loop.render_local_rag_retrieval_result_text(
                result,
            )
        )
        self.assertIn("[rag-advisory]", output)
        self.assertIn("[rag-retrieval]", output)

    def test_render_retrieval_result_refusal(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            result = agent_loop.retrieve_local_rag_excerpts(
                controller,
                operator_inputs={
                    "identity": "me",
                    "acknowledged_source_ids": [
                        "repo_local_docs_readme",
                    ],
                },
                query="",
            )
        output = "\n".join(
            agent_loop.render_local_rag_retrieval_result_text(
                result,
            )
        )
        self.assertIn("[refused]", output)
        self.assertIn("query_empty", output)


# ---------------------------------------------------------------------------
# build_desktop_rag_retrieval_controls
# ---------------------------------------------------------------------------
class BuildControlsTests(unittest.TestCase):

    def test_controls_one_per_source(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_rag_retrieval_controls_view(
                    controller,
                    operator_inputs={
                        "identity": "me",
                        "acknowledged_source_ids": [
                            "repo_local_docs_readme",
                        ],
                    },
                )
            )
        controls = (
            agent_loop.build_desktop_rag_retrieval_controls(view)
        )
        self.assertEqual(
            len(controls), len(view["sources"]),
        )
        for control in controls:
            self.assertEqual(
                control["dispatch_mode"], "copy_paste",
            )
            self.assertEqual(
                control["category"],
                "rag_retrieval_controls_ux",
            )
        readme = next(
            c for c in controls
            if c["id"] == "repo_local_docs_readme"
        )
        self.assertTrue(readme["enabled"])
        other = next(
            c for c in controls
            if c["id"] != "repo_local_docs_readme"
        )
        self.assertFalse(other["enabled"])


# ---------------------------------------------------------------------------
# CLI handlers
# ---------------------------------------------------------------------------
class CmdHandlerTests(unittest.TestCase):

    def _controls_args(self, **kwargs) -> argparse.Namespace:
        defaults = {
            "controller_root": None,
            "operator_identity": None,
            "acknowledge_source": None,
        }
        defaults.update(kwargs)
        return argparse.Namespace(**defaults)

    def _retrieval_args(self, **kwargs) -> argparse.Namespace:
        defaults = {
            "controller_root": None,
            "operator_identity": None,
            "acknowledge_source": None,
            "query": None,
            "top_k": None,
        }
        defaults.update(kwargs)
        return argparse.Namespace(**defaults)

    def test_controls_refuses_missing_controller_root(
        self,
    ) -> None:
        buf_err = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(
            buf_err,
        ):
            rc = (
                agent_loop.cmd_view_desktop_rag_retrieval_controls(
                    self._controls_args(),
                )
            )
        self.assertEqual(rc, 2)
        self.assertIn("REFUSED", buf_err.getvalue())

    def test_controls_phase_7c_exits_zero(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            buf_out = io.StringIO()
            with redirect_stdout(buf_out):
                rc = (
                    agent_loop.cmd_view_desktop_rag_retrieval_controls(
                        self._controls_args(
                            controller_root=str(controller),
                        ),
                    )
                )
        self.assertEqual(rc, 0)
        self.assertIn(
            "[desktop-rag-retrieval-controls]", buf_out.getvalue(),
        )

    def test_retrieval_refuses_missing_controller_root(
        self,
    ) -> None:
        buf_err = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(
            buf_err,
        ):
            rc = agent_loop.cmd_run_local_rag_retrieval(
                self._retrieval_args(),
            )
        self.assertEqual(rc, 2)
        self.assertIn("REFUSED", buf_err.getvalue())

    def test_retrieval_phase_7c_exits_zero_even_on_refusal(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            buf_out = io.StringIO()
            with redirect_stdout(buf_out):
                rc = agent_loop.cmd_run_local_rag_retrieval(
                    self._retrieval_args(
                        controller_root=str(controller),
                        query="",
                    ),
                )
        self.assertEqual(rc, 0)
        # Query-empty refusal surfaces on stdout with the
        # `[refused]` attribution.
        self.assertIn("[refused]", buf_out.getvalue())

    def test_retrieval_positive_end_to_end(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            buf_out = io.StringIO()
            with redirect_stdout(buf_out):
                rc = agent_loop.cmd_run_local_rag_retrieval(
                    self._retrieval_args(
                        controller_root=str(controller),
                        operator_identity="me",
                        acknowledge_source=[
                            "repo_local_docs_readme",
                        ],
                        query="claude phase",
                        top_k=2,
                    ),
                )
        self.assertEqual(rc, 0)
        output = buf_out.getvalue()
        self.assertIn("[rag-advisory]", output)
        self.assertIn("built_this_invocation", output)

    def test_handlers_registered(self) -> None:
        self.assertIn(
            "view-desktop-rag-retrieval-controls",
            agent_loop.HANDLERS,
        )
        self.assertIn(
            "run-local-rag-retrieval", agent_loop.HANDLERS,
        )

    def test_parser_accepts_both_subcommands(self) -> None:
        parser = agent_loop.build_parser()
        args = parser.parse_args([
            "view-desktop-rag-retrieval-controls",
            "--controller-root", ".",
            "--operator-identity", "me",
            "--acknowledge-source", "repo_local_docs_readme",
        ])
        self.assertEqual(
            args.cmd, "view-desktop-rag-retrieval-controls",
        )
        args2 = parser.parse_args([
            "run-local-rag-retrieval",
            "--controller-root", ".",
            "--operator-identity", "me",
            "--acknowledge-source", "repo_local_docs_readme",
            "--query", "claude phase",
            "--top-k", "3",
        ])
        self.assertEqual(
            args2.cmd, "run-local-rag-retrieval",
        )
        self.assertEqual(args2.query, "claude phase")
        self.assertEqual(args2.top_k, 3)


# ---------------------------------------------------------------------------
# Integration
# ---------------------------------------------------------------------------
class DesktopAppIntegrationTests(unittest.TestCase):

    def test_assemble_includes_rag_retrieval_controls_view_key(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.assemble_desktop_app_view(controller)
        self.assertIn("rag_retrieval_controls_view", view)
        sub = view["rag_retrieval_controls_view"]
        self.assertEqual(
            sub["view_signal_version"], "phase-10w-v1",
        )

    def test_render_includes_phase_10w_label(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.assemble_desktop_app_view(controller)
            lines = agent_loop.render_desktop_app_text(view)
        output = "\n".join(lines)
        self.assertIn(
            "=== RAG Retrieval Controls (Phase 10W) ===",
            output,
        )
        self.assertIn("phase-10w-v1", output)


# ---------------------------------------------------------------------------
# Non-mutation invariants
# ---------------------------------------------------------------------------
class NonMutationInvariantsTests(unittest.TestCase):

    def test_retrieval_does_not_open_socket(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            with mock.patch.object(
                socket, "socket",
            ) as patched_socket:
                agent_loop.retrieve_local_rag_excerpts(
                    controller,
                    operator_inputs={
                        "identity": "me",
                        "acknowledged_source_ids": [
                            "repo_local_docs_readme",
                        ],
                    },
                    query="claude",
                )
        patched_socket.assert_not_called()

    def test_retrieval_does_not_spawn_subprocess(self) -> None:
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
                agent_loop.retrieve_local_rag_excerpts(
                    controller,
                    operator_inputs={
                        "identity": "me",
                        "acknowledged_source_ids": [
                            "repo_local_docs_readme",
                        ],
                    },
                    query="claude",
                )
            finally:
                for p in patches:
                    p.stop()
        for m in mocks:
            m.assert_not_called()

    def test_retrieval_does_not_invoke_halt(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            with mock.patch.object(agent_loop, "_halt") as h:
                agent_loop.retrieve_local_rag_excerpts(
                    controller,
                    operator_inputs={
                        "identity": "me",
                        "acknowledged_source_ids": [
                            "repo_local_docs_readme",
                        ],
                    },
                    query="claude",
                )
        h.assert_not_called()

    def test_retrieval_does_not_mutate_loop_state(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            ls_path = (
                controller / ".agent-loop" / "loop-state.json"
            )
            before = ls_path.read_bytes()
            agent_loop.retrieve_local_rag_excerpts(
                controller,
                operator_inputs={
                    "identity": "me",
                    "acknowledged_source_ids": [
                        "repo_local_docs_readme",
                    ],
                },
                query="claude",
            )
            after = ls_path.read_bytes()
        self.assertEqual(before, after)

    def test_retrieval_does_not_append_orchestrator_log(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            log_path = (
                controller / ".agent-loop" / "orchestrator.log"
            )
            agent_loop.retrieve_local_rag_excerpts(
                controller,
                operator_inputs={
                    "identity": "me",
                    "acknowledged_source_ids": [
                        "repo_local_docs_readme",
                    ],
                },
                query="claude",
            )
        self.assertFalse(log_path.exists())

    def test_retrieval_does_not_persist_retrieval_cache(
        self,
    ) -> None:
        # The retrieval library MUST NOT persist an index / hit
        # log / cache to disk. Snapshot the controller root
        # before and after and assert only the expected files
        # exist.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            before = sorted(
                p.name for p in controller.iterdir()
            )
            before_dot = sorted(
                p.name
                for p in (controller / ".agent-loop").iterdir()
            )
            agent_loop.retrieve_local_rag_excerpts(
                controller,
                operator_inputs={
                    "identity": "me",
                    "acknowledged_source_ids": [
                        "repo_local_docs_readme",
                    ],
                },
                query="claude",
            )
            after = sorted(
                p.name for p in controller.iterdir()
            )
            after_dot = sorted(
                p.name
                for p in (controller / ".agent-loop").iterdir()
            )
        self.assertEqual(before, after)
        self.assertEqual(before_dot, after_dot)

    def test_does_not_widen_phase_10i_library_callable_cap(
        self,
    ) -> None:
        library_call_ids = {
            spec["id"]
            for spec in agent_loop._EXTERNAL_UI_CONTROL_REGISTRY
            if spec["dispatch_mode"] == "library_call"
        }
        self.assertEqual(
            library_call_ids,
            {
                "view-external-status",
                "view-external-controls",
                "inspect-external-target",
            },
            "Phase 10W MUST NOT widen the Phase 10I library-"
            "callable control surface beyond the three shipped "
            "controls",
        )


if __name__ == "__main__":
    unittest.main()
