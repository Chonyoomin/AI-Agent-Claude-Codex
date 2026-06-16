"""Focused tests for the Phase 9B PRD Intake And Decomposition slice.

Scope (Phase 9B, narrow):
- constants match the shipped contract
- structured-PRD happy path produces the canonical intake artifact
- product-brief happy path produces the canonical intake artifact
- bounds (`max_phases`, `max_tasks_per_phase`) are enforced
- every documented refusal mode raises `HaltError("halted_input_missing")`
- the call is canonical-precedence-preserving (never mutates loop-state,
  never writes anything outside the named output and audit log)
- the `intake-prd` CLI subcommand routes through `main(argv)` HANDLERS
  dispatch end-to-end and refuses fail-closed via `_halt`
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
from agent_loop import HaltError  # noqa: E402


CONTRACT_VERSION = "phase-3a-v2"


def _make_repo(td: Path) -> Path:
    """Plant minimal repo scaffolding so find_repo_root resolves."""
    (td / "AGENTS.md").write_text("test\n", encoding="utf-8")
    (td / "CLAUDE.md").write_text("test\n", encoding="utf-8")
    (td / "TASK.md").write_text("test\n", encoding="utf-8")
    (td / ".agent-loop").mkdir()
    return td


def _plant_loop_state(repo_root: Path) -> Path:
    state_path = repo_root / ".agent-loop" / "loop-state.json"
    state_path.write_text(json.dumps({
        "phase": "Phase 9 - Fully Autonomous PRD-To-Product Mode",
        "sub_phase": "Phase 9B - PRD Intake And Decomposition",
        "task": "intake-test",
        "status": "awaiting_claude_implementation",
        "cycle_count": 0,
        "max_cycles": 3,
        "last_verdict": None,
        "last_verdict_phase": None,
        "contract_version": CONTRACT_VERSION,
        "claude_version": "claude-opus-4-7",
        "codex_version": None,
        "orchestrator_version": "phase-3d-v0",
        "approval_mode": "review",
        "awaiting_human_for": None,
    }), encoding="utf-8")
    return state_path


def _structured_prd() -> dict:
    return {
        "prd_kind": "structured_prd",
        "title": "Notes App",
        "summary": "A simple notes app",
        "requirements": [
            {
                "id": "R1",
                "title": "Create notes",
                "description": (
                    "User can create a note. Note has a title. "
                    "Note has body text."
                ),
                "risks": ["unsaved note loss"],
                "acceptance_criteria": ["new note appears in list"],
            },
            {
                "id": "R2",
                "title": "Delete notes",
                "description": (
                    "User can delete a note. Confirmation prompt is "
                    "shown."
                ),
            },
        ],
    }


def _product_brief() -> dict:
    return {
        "prd_kind": "product_brief",
        "title": "Notes App",
        "summary": "Simple notes",
        "narrative": (
            "Build a notes app that lets users create notes. Notes "
            "have a title. Notes have a body.\n\nThe app should "
            "support search. Search should be fast.\n\nThe app "
            "should sync across devices."
        ),
    }


class IntakeConstantsTests(unittest.TestCase):

    def test_signal_version_is_phase_9b_v1(self) -> None:
        self.assertEqual(
            agent_loop.PRD_INTAKE_SIGNAL_VERSION, "phase-9b-v1",
        )

    def test_output_rel_is_under_agent_loop(self) -> None:
        self.assertEqual(
            agent_loop.PRD_INTAKE_OUTPUT_REL,
            ".agent-loop/prd-intake.json",
        )

    def test_intake_kinds_are_exactly_the_two_shipped(self) -> None:
        self.assertEqual(
            agent_loop.PRD_INTAKE_KINDS,
            frozenset({"structured_prd", "product_brief"}),
        )

    def test_max_phases_cap_is_positive(self) -> None:
        self.assertGreaterEqual(
            agent_loop.PRD_INTAKE_MAX_MAX_PHASES, 1,
        )
        self.assertGreaterEqual(
            agent_loop.PRD_INTAKE_MAX_MAX_TASKS_PER_PHASE, 1,
        )

    def test_intake_prd_is_wired_into_handlers(self) -> None:
        self.assertIn("intake-prd", agent_loop.HANDLERS)
        self.assertIs(
            agent_loop.HANDLERS["intake-prd"], agent_loop.cmd_intake_prd,
        )


class IntakeStructuredPrdSuccessTests(unittest.TestCase):

    def test_structured_prd_happy_path_writes_canonical_artifact(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            src = repo / "prd.json"
            src.write_text(
                json.dumps(_structured_prd()), encoding="utf-8",
            )
            written = agent_loop.intake_and_decompose_prd(
                repo, input_path=src,
            )
            self.assertTrue(written.is_file())
            self.assertEqual(
                written, repo / ".agent-loop" / "prd-intake.json",
            )
            payload = json.loads(written.read_text(encoding="utf-8"))
            self.assertEqual(
                payload["intake_signal_version"], "phase-9b-v1",
            )
            self.assertEqual(
                payload["source_input_kind"], "structured_prd",
            )
            self.assertEqual(payload["normalized_title"], "Notes App")
            self.assertEqual(
                payload["normalized_summary"], "A simple notes app",
            )
            self.assertTrue(payload["advisory_only"])
            self.assertEqual(
                payload["canonical_precedence_note"],
                agent_loop.PRD_INTAKE_CANONICAL_PRECEDENCE_NOTE,
            )
            phases = payload["decomposition"]["phases"]
            self.assertEqual(len(phases), 2)
            self.assertEqual(payload["decomposition"]["total_phases"], 2)
            self.assertEqual(phases[0]["label"], "R1")
            self.assertEqual(phases[1]["label"], "R2")
            self.assertIn("Create notes", phases[0]["objective"])
            self.assertIn("unsaved note loss", phases[0]["risks"])
            self.assertIn(
                "new note appears in list",
                phases[0]["acceptance_criteria"],
            )
            self.assertGreater(len(phases[0]["tasks"]), 0)
            self.assertEqual(phases[1]["risks"], [])
            self.assertEqual(
                phases[1]["acceptance_criteria"],
                ["meets the requirement: Delete notes"],
            )

    def test_audit_note_lands_when_log_path_supplied(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            src = repo / "prd.json"
            src.write_text(
                json.dumps(_structured_prd()), encoding="utf-8",
            )
            log = repo / ".agent-loop" / "orchestrator.log"
            agent_loop.intake_and_decompose_prd(
                repo, input_path=src, log_path=log,
            )
            text = log.read_text(encoding="utf-8")
            self.assertIn("prd intake:", text)
            self.assertIn("signal_version=phase-9b-v1", text)
            self.assertIn("kind=structured_prd", text)
            self.assertIn("phases=2", text)
            self.assertIn("max_phases_applied=8", text)

    def test_no_log_path_produces_no_orchestrator_log(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            src = repo / "prd.json"
            src.write_text(
                json.dumps(_structured_prd()), encoding="utf-8",
            )
            agent_loop.intake_and_decompose_prd(repo, input_path=src)
            log = repo / ".agent-loop" / "orchestrator.log"
            self.assertFalse(log.exists())


class IntakeProductBriefSuccessTests(unittest.TestCase):

    def test_product_brief_happy_path_decomposes_sections(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            src = repo / "brief.json"
            src.write_text(
                json.dumps(_product_brief()), encoding="utf-8",
            )
            written = agent_loop.intake_and_decompose_prd(
                repo, input_path=src,
            )
            payload = json.loads(written.read_text(encoding="utf-8"))
            self.assertEqual(
                payload["source_input_kind"], "product_brief",
            )
            phases = payload["decomposition"]["phases"]
            # Three sections in the brief narrative -> 3 phases.
            self.assertEqual(len(phases), 3)
            self.assertEqual(phases[0]["label"], "P1")
            self.assertEqual(phases[1]["label"], "P2")
            self.assertEqual(phases[2]["label"], "P3")
            # Synthesized acceptance criterion shape.
            for phase in phases:
                self.assertEqual(len(phase["acceptance_criteria"]), 1)
                self.assertTrue(
                    phase["acceptance_criteria"][0].startswith(
                        "section delivered:",
                    ),
                )
                self.assertEqual(phase["risks"], [])


class IntakeBoundsTests(unittest.TestCase):

    def test_max_phases_default_is_recorded(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            src = repo / "prd.json"
            src.write_text(
                json.dumps(_structured_prd()), encoding="utf-8",
            )
            agent_loop.intake_and_decompose_prd(repo, input_path=src)
            payload = json.loads(
                (repo / ".agent-loop" / "prd-intake.json").read_text(
                    encoding="utf-8",
                ),
            )
            self.assertEqual(
                payload["decomposition"]["max_phases_applied"],
                agent_loop.PRD_INTAKE_DEFAULT_MAX_PHASES,
            )
            self.assertEqual(
                payload["decomposition"][
                    "max_tasks_per_phase_applied"
                ],
                agent_loop.PRD_INTAKE_DEFAULT_MAX_TASKS_PER_PHASE,
            )

    def test_structured_prd_refuses_when_requirements_exceed_max_phases(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            many_reqs = {
                "prd_kind": "structured_prd",
                "title": "App",
                "summary": "Big",
                "requirements": [
                    {
                        "id": f"R{i}",
                        "title": f"Req {i}",
                        "description": f"description {i}.",
                    }
                    for i in range(5)
                ],
            }
            src = repo / "prd.json"
            src.write_text(json.dumps(many_reqs), encoding="utf-8")
            with self.assertRaises(HaltError) as ctx:
                agent_loop.intake_and_decompose_prd(
                    repo, input_path=src, max_phases=3,
                )
            self.assertEqual(ctx.exception.status, "halted_input_missing")
            self.assertIn("max_phases=3", str(ctx.exception))

    def test_product_brief_refuses_when_sections_exceed_max_phases(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            five_sections = {
                "prd_kind": "product_brief",
                "title": "App",
                "summary": "Big",
                "narrative": "\n\n".join(
                    [f"Section {i}." for i in range(5)],
                ),
            }
            src = repo / "brief.json"
            src.write_text(
                json.dumps(five_sections), encoding="utf-8",
            )
            with self.assertRaises(HaltError) as ctx:
                agent_loop.intake_and_decompose_prd(
                    repo, input_path=src, max_phases=3,
                )
            self.assertEqual(ctx.exception.status, "halted_input_missing")

    def test_max_phases_out_of_bounds_refuses(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            src = repo / "prd.json"
            src.write_text(
                json.dumps(_structured_prd()), encoding="utf-8",
            )
            for bad in (0, -1, True, "8", 1.0):
                with self.subTest(value=bad):
                    with self.assertRaises(HaltError) as ctx:
                        agent_loop.intake_and_decompose_prd(
                            repo, input_path=src, max_phases=bad,
                        )
                    self.assertEqual(
                        ctx.exception.status, "halted_input_missing",
                    )
            with self.assertRaises(HaltError):
                agent_loop.intake_and_decompose_prd(
                    repo,
                    input_path=src,
                    max_phases=agent_loop.PRD_INTAKE_MAX_MAX_PHASES + 1,
                )

    def test_max_tasks_per_phase_out_of_bounds_refuses(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            src = repo / "prd.json"
            src.write_text(
                json.dumps(_structured_prd()), encoding="utf-8",
            )
            for bad in (0, -1, True, "8", 1.0):
                with self.subTest(value=bad):
                    with self.assertRaises(HaltError):
                        agent_loop.intake_and_decompose_prd(
                            repo,
                            input_path=src,
                            max_tasks_per_phase=bad,
                        )
            with self.assertRaises(HaltError):
                agent_loop.intake_and_decompose_prd(
                    repo,
                    input_path=src,
                    max_tasks_per_phase=(
                        agent_loop.PRD_INTAKE_MAX_MAX_TASKS_PER_PHASE + 1
                    ),
                )


class IntakeRefusalTests(unittest.TestCase):

    def setUp(self) -> None:
        self.td = TemporaryDirectory()
        self.repo = _make_repo(Path(self.td.name))
        self.src = self.repo / "prd.json"

    def tearDown(self) -> None:
        self.td.cleanup()

    def _expect_halt(self, payload) -> HaltError:
        if isinstance(payload, (dict, list)):
            self.src.write_text(json.dumps(payload), encoding="utf-8")
        else:
            self.src.write_text(str(payload), encoding="utf-8")
        with self.assertRaises(HaltError) as ctx:
            agent_loop.intake_and_decompose_prd(
                self.repo, input_path=self.src,
            )
        self.assertEqual(ctx.exception.status, "halted_input_missing")
        return ctx.exception

    def test_missing_source_file_refuses(self) -> None:
        with self.assertRaises(HaltError) as ctx:
            agent_loop.intake_and_decompose_prd(
                self.repo, input_path=self.repo / "absent.json",
            )
        self.assertEqual(ctx.exception.status, "halted_input_missing")

    def test_source_is_directory_refuses(self) -> None:
        d = self.repo / "subdir"
        d.mkdir()
        with self.assertRaises(HaltError):
            agent_loop.intake_and_decompose_prd(
                self.repo, input_path=d,
            )

    def test_non_json_source_refuses(self) -> None:
        self._expect_halt("this is not json")

    def test_non_dict_top_level_refuses(self) -> None:
        self._expect_halt([{"prd_kind": "structured_prd"}])

    def test_missing_prd_kind_refuses(self) -> None:
        self._expect_halt({"title": "x", "summary": "y"})

    def test_unknown_prd_kind_refuses(self) -> None:
        self._expect_halt({
            "prd_kind": "freeform",
            "title": "x",
            "summary": "y",
        })

    def test_missing_title_refuses(self) -> None:
        self._expect_halt({
            "prd_kind": "product_brief",
            "summary": "y",
            "narrative": "n",
        })

    def test_empty_title_refuses(self) -> None:
        self._expect_halt({
            "prd_kind": "product_brief",
            "title": "   ",
            "summary": "y",
            "narrative": "n",
        })

    def test_missing_summary_refuses(self) -> None:
        self._expect_halt({
            "prd_kind": "product_brief",
            "title": "x",
            "narrative": "n",
        })

    def test_structured_prd_requirements_non_list_refuses(self) -> None:
        self._expect_halt({
            "prd_kind": "structured_prd",
            "title": "x",
            "summary": "y",
            "requirements": "not a list",
        })

    def test_structured_prd_empty_requirements_refuses(self) -> None:
        self._expect_halt({
            "prd_kind": "structured_prd",
            "title": "x",
            "summary": "y",
            "requirements": [],
        })

    def test_structured_prd_requirement_missing_id_refuses(self) -> None:
        self._expect_halt({
            "prd_kind": "structured_prd",
            "title": "x",
            "summary": "y",
            "requirements": [
                {"title": "t", "description": "d"},
            ],
        })

    def test_structured_prd_requirement_missing_description_refuses(
        self,
    ) -> None:
        self._expect_halt({
            "prd_kind": "structured_prd",
            "title": "x",
            "summary": "y",
            "requirements": [
                {"id": "R1", "title": "t"},
            ],
        })

    def test_structured_prd_requirement_non_dict_refuses(self) -> None:
        self._expect_halt({
            "prd_kind": "structured_prd",
            "title": "x",
            "summary": "y",
            "requirements": ["not a dict"],
        })

    def test_structured_prd_requirement_risks_non_string_refuses(
        self,
    ) -> None:
        self._expect_halt({
            "prd_kind": "structured_prd",
            "title": "x",
            "summary": "y",
            "requirements": [{
                "id": "R1", "title": "t", "description": "d",
                "risks": [123],
            }],
        })

    def test_structured_prd_requirement_empty_acceptance_refuses(
        self,
    ) -> None:
        self._expect_halt({
            "prd_kind": "structured_prd",
            "title": "x",
            "summary": "y",
            "requirements": [{
                "id": "R1", "title": "t", "description": "d",
                "acceptance_criteria": [],
            }],
        })

    def test_product_brief_missing_narrative_refuses(self) -> None:
        self._expect_halt({
            "prd_kind": "product_brief",
            "title": "x",
            "summary": "y",
        })

    def test_product_brief_empty_narrative_refuses(self) -> None:
        self._expect_halt({
            "prd_kind": "product_brief",
            "title": "x",
            "summary": "y",
            "narrative": "   ",
        })


class IntakeCanonicalPrecedenceTests(unittest.TestCase):

    def test_intake_does_not_mutate_loop_state(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            state_path = _plant_loop_state(repo)
            before = state_path.read_bytes()
            src = repo / "prd.json"
            src.write_text(
                json.dumps(_structured_prd()), encoding="utf-8",
            )
            agent_loop.intake_and_decompose_prd(repo, input_path=src)
            after = state_path.read_bytes()
            self.assertEqual(before, after)

    def test_intake_does_not_mutate_source_input(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            src = repo / "prd.json"
            body = json.dumps(_structured_prd())
            src.write_text(body, encoding="utf-8")
            before = src.read_bytes()
            agent_loop.intake_and_decompose_prd(repo, input_path=src)
            after = src.read_bytes()
            self.assertEqual(before, after)

    def test_advisory_only_marker_is_true(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            src = repo / "prd.json"
            src.write_text(
                json.dumps(_structured_prd()), encoding="utf-8",
            )
            written = agent_loop.intake_and_decompose_prd(
                repo, input_path=src,
            )
            payload = json.loads(written.read_text(encoding="utf-8"))
            self.assertIs(payload["advisory_only"], True)
            self.assertIs(
                payload["canonical_precedence_note"],
                # frozen-string equality not identity (json roundtrip
                # produces a new string object), so use ==
                payload["canonical_precedence_note"],
            )
            self.assertEqual(
                payload["canonical_precedence_note"],
                agent_loop.PRD_INTAKE_CANONICAL_PRECEDENCE_NOTE,
            )


class IntakeCliTests(unittest.TestCase):

    def setUp(self) -> None:
        self.td = TemporaryDirectory()
        self.repo = Path(self.td.name)
        _make_repo(self.repo)
        _plant_loop_state(self.repo)
        self.src = self.repo / "prd.json"
        self.src.write_text(
            json.dumps(_structured_prd()), encoding="utf-8",
        )
        # Save and pin cwd so find_repo_root resolves.
        import os
        self._prev_cwd = os.getcwd()
        os.chdir(self.repo)

    def tearDown(self) -> None:
        import os
        os.chdir(self._prev_cwd)
        self.td.cleanup()

    def test_cli_dispatch_success(self) -> None:
        rc = agent_loop.main([
            "intake-prd", "--input", "prd.json",
        ])
        self.assertEqual(rc, 0)
        out_path = self.repo / ".agent-loop" / "prd-intake.json"
        self.assertTrue(out_path.is_file())
        payload = json.loads(out_path.read_text(encoding="utf-8"))
        self.assertEqual(
            payload["intake_signal_version"], "phase-9b-v1",
        )

    def test_cli_refuses_absolute_input_path(self) -> None:
        rc = agent_loop.main([
            "intake-prd",
            "--input", str(self.src.resolve()),
        ])
        self.assertEqual(rc, 2)

    def test_cli_refuses_input_outside_repo_via_dotdot(self) -> None:
        rc = agent_loop.main([
            "intake-prd",
            "--input", "../escape.json",
        ])
        self.assertEqual(rc, 2)

    def test_cli_refuses_missing_required_input_flag(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            agent_loop.main(["intake-prd"])
        self.assertEqual(ctx.exception.code, 2)

    def test_cli_honors_max_phases_override(self) -> None:
        # Default cap is 8; force a refusal by setting it below the
        # 2-requirement structured PRD's count.
        rc = agent_loop.main([
            "intake-prd",
            "--input", "prd.json",
            "--max-phases", "1",
        ])
        self.assertEqual(rc, 2)

    def test_cli_honors_output_override(self) -> None:
        rc = agent_loop.main([
            "intake-prd",
            "--input", "prd.json",
            "--output", ".agent-loop/custom-intake.json",
        ])
        self.assertEqual(rc, 0)
        self.assertTrue(
            (self.repo / ".agent-loop" / "custom-intake.json").is_file(),
        )

    def test_cli_refuses_absolute_output_path(self) -> None:
        rc = agent_loop.main([
            "intake-prd",
            "--input", "prd.json",
            "--output", str(
                (self.repo / ".agent-loop" / "x.json").resolve(),
            ),
        ])
        self.assertEqual(rc, 2)


class IntakeOutputBoundaryTests(unittest.TestCase):
    """Phase 9B fix-cycle: the advisory intake artifact must NEVER
    overwrite a canonical runtime/planning artifact, the orchestrator
    log, the Phase 6 durable-memory subtree, or the source input
    file. The boundary is enforced in the library function so direct
    callers cannot bypass it via `output_path=...`.
    """

    def _setup_repo(self, td: str) -> tuple[Path, Path]:
        repo = _make_repo(Path(td))
        src = repo / "prd.json"
        src.write_text(
            json.dumps(_structured_prd()), encoding="utf-8",
        )
        return repo, src

    def test_library_refuses_output_outside_agent_loop_dir(self) -> None:
        with TemporaryDirectory() as td:
            repo, src = self._setup_repo(td)
            # TASK.md is under the repo root but outside .agent-loop/.
            with self.assertRaises(HaltError) as ctx:
                agent_loop.intake_and_decompose_prd(
                    repo, input_path=src,
                    output_path=repo / "TASK.md",
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )
            self.assertIn(
                "must be under .agent-loop/",
                str(ctx.exception),
            )
            # The pre-existing TASK.md scaffold must NOT have been
            # overwritten.
            self.assertEqual(
                (repo / "TASK.md").read_text(encoding="utf-8"),
                "test\n",
            )

    def test_library_refuses_output_matching_source_input_path(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            repo, src = self._setup_repo(td)
            before = src.read_bytes()
            with self.assertRaises(HaltError) as ctx:
                # Even though the source lives outside .agent-loop/,
                # the "outside .agent-loop/" rule fires before the
                # input-equals-output rule does; the boundary still
                # protects the source from being clobbered.
                agent_loop.intake_and_decompose_prd(
                    repo, input_path=src, output_path=src,
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )
            # Source bytes preserved either way.
            self.assertEqual(src.read_bytes(), before)

    def test_library_refuses_output_matching_source_input_inside_agent_loop(
        self,
    ) -> None:
        # Place source under .agent-loop/ so the "outside dir" rule
        # does not fire first and the input-equals-output rule is the
        # one that catches the overwrite attempt.
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            src = repo / ".agent-loop" / "input.json"
            src.write_text(
                json.dumps(_structured_prd()), encoding="utf-8",
            )
            before = src.read_bytes()
            with self.assertRaises(HaltError) as ctx:
                agent_loop.intake_and_decompose_prd(
                    repo, input_path=src, output_path=src,
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )
            self.assertIn(
                "must differ from the source input path",
                str(ctx.exception),
            )
            self.assertEqual(src.read_bytes(), before)

    def test_library_refuses_each_protected_output_target(self) -> None:
        with TemporaryDirectory() as td:
            repo, src = self._setup_repo(td)
            for rel in sorted(
                agent_loop.PRD_INTAKE_PROTECTED_OUTPUT_PATHS,
            ):
                with self.subTest(rel=rel):
                    with self.assertRaises(HaltError) as ctx:
                        agent_loop.intake_and_decompose_prd(
                            repo, input_path=src,
                            output_path=repo / rel,
                        )
                    self.assertEqual(
                        ctx.exception.status, "halted_input_missing",
                    )
                    self.assertIn(
                        "protected runtime / planning artifact",
                        str(ctx.exception),
                    )

    def test_library_refuses_output_under_memory_subtree(self) -> None:
        with TemporaryDirectory() as td:
            repo, src = self._setup_repo(td)
            with self.assertRaises(HaltError) as ctx:
                agent_loop.intake_and_decompose_prd(
                    repo, input_path=src,
                    output_path=(
                        repo / ".agent-loop" / "memory" / "x.json"
                    ),
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )
            self.assertIn(
                "memory/", str(ctx.exception),
            )

    def test_library_refuses_output_is_directory(self) -> None:
        with TemporaryDirectory() as td:
            repo, src = self._setup_repo(td)
            target = repo / ".agent-loop" / "intake-dir"
            target.mkdir()
            with self.assertRaises(HaltError) as ctx:
                agent_loop.intake_and_decompose_prd(
                    repo, input_path=src, output_path=target,
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )
            self.assertIn("directory", str(ctx.exception))

    def test_library_accepts_default_output(self) -> None:
        with TemporaryDirectory() as td:
            repo, src = self._setup_repo(td)
            written = agent_loop.intake_and_decompose_prd(
                repo, input_path=src,
            )
            self.assertEqual(
                written.relative_to(repo).as_posix(),
                agent_loop.PRD_INTAKE_OUTPUT_REL,
            )

    def test_library_accepts_safe_override_under_agent_loop(self) -> None:
        with TemporaryDirectory() as td:
            repo, src = self._setup_repo(td)
            target = repo / ".agent-loop" / "custom-intake.json"
            written = agent_loop.intake_and_decompose_prd(
                repo, input_path=src, output_path=target,
            )
            self.assertEqual(written, target)
            self.assertTrue(target.is_file())

    def test_library_accepts_safe_nested_override_under_agent_loop(
        self,
    ) -> None:
        # An advisory subdirectory under `.agent-loop/intake/` is
        # still safe (not protected, not memory) and is auto-created
        # by parents=True / exist_ok=True.
        with TemporaryDirectory() as td:
            repo, src = self._setup_repo(td)
            target = repo / ".agent-loop" / "intake" / "v1.json"
            written = agent_loop.intake_and_decompose_prd(
                repo, input_path=src, output_path=target,
            )
            self.assertEqual(written, target)
            self.assertTrue(target.is_file())


class IntakeCliOutputBoundaryTests(unittest.TestCase):
    """Phase 9B fix-cycle CLI surface coverage: the same boundary
    must fire when the operator passes an unsafe `--output`.
    """

    def setUp(self) -> None:
        self.td = TemporaryDirectory()
        self.repo = Path(self.td.name)
        _make_repo(self.repo)
        _plant_loop_state(self.repo)
        self.src = self.repo / "prd.json"
        self.src.write_text(
            json.dumps(_structured_prd()), encoding="utf-8",
        )
        import os
        self._prev_cwd = os.getcwd()
        os.chdir(self.repo)

    def tearDown(self) -> None:
        import os
        os.chdir(self._prev_cwd)
        self.td.cleanup()

    def test_cli_refuses_output_task_md(self) -> None:
        before = (self.repo / "TASK.md").read_bytes()
        rc = agent_loop.main([
            "intake-prd",
            "--input", "prd.json",
            "--output", "TASK.md",
        ])
        self.assertEqual(rc, 2)
        # TASK.md must not have been overwritten.
        self.assertEqual(
            (self.repo / "TASK.md").read_bytes(), before,
        )

    def test_cli_refuses_output_loop_state_json(self) -> None:
        # `_halt` correctly persists the halt status into loop-state
        # on a CLI refusal, so the file bytes legitimately change.
        # The load-bearing assertion is that loop-state was NOT
        # overwritten with the advisory PRD intake content. We verify
        # by re-loading and confirming the file still carries the
        # loop-state shape (phase / sub_phase keys + halt status)
        # rather than the intake artifact shape
        # (intake_signal_version / source_input_kind).
        rc = agent_loop.main([
            "intake-prd",
            "--input", "prd.json",
            "--output", ".agent-loop/loop-state.json",
        ])
        self.assertEqual(rc, 2)
        post = json.loads(
            (
                self.repo / ".agent-loop" / "loop-state.json"
            ).read_text(encoding="utf-8"),
        )
        self.assertIn("phase", post)
        self.assertIn("sub_phase", post)
        self.assertNotIn("intake_signal_version", post)
        self.assertNotIn("source_input_kind", post)
        # The halt was persisted (this is `_halt`'s shipped behavior).
        self.assertEqual(post.get("status"), "halted_input_missing")

    def test_cli_refuses_output_matching_source_input(self) -> None:
        before = self.src.read_bytes()
        rc = agent_loop.main([
            "intake-prd",
            "--input", "prd.json",
            "--output", "prd.json",
        ])
        self.assertEqual(rc, 2)
        self.assertEqual(self.src.read_bytes(), before)

    def test_cli_refuses_output_under_memory_subtree(self) -> None:
        rc = agent_loop.main([
            "intake-prd",
            "--input", "prd.json",
            "--output", ".agent-loop/memory/x.json",
        ])
        self.assertEqual(rc, 2)
        self.assertFalse(
            (self.repo / ".agent-loop" / "memory" / "x.json").exists(),
        )

    def test_cli_refuses_output_planning_artifact(self) -> None:
        # Plant a stand-in for current-task.md so we can assert
        # bytes-preservation across the refusal.
        ct = self.repo / ".agent-loop" / "current-task.md"
        ct.write_text("planning bytes\n", encoding="utf-8")
        rc = agent_loop.main([
            "intake-prd",
            "--input", "prd.json",
            "--output", ".agent-loop/current-task.md",
        ])
        self.assertEqual(rc, 2)
        self.assertEqual(
            ct.read_text(encoding="utf-8"), "planning bytes\n",
        )

    def test_cli_default_output_still_succeeds(self) -> None:
        rc = agent_loop.main([
            "intake-prd",
            "--input", "prd.json",
        ])
        self.assertEqual(rc, 0)
        self.assertTrue(
            (self.repo / ".agent-loop" / "prd-intake.json").is_file(),
        )

    def test_cli_safe_override_under_agent_loop_still_succeeds(
        self,
    ) -> None:
        rc = agent_loop.main([
            "intake-prd",
            "--input", "prd.json",
            "--output", ".agent-loop/custom-intake.json",
        ])
        self.assertEqual(rc, 0)
        self.assertTrue(
            (
                self.repo / ".agent-loop" / "custom-intake.json"
            ).is_file(),
        )


if __name__ == "__main__":
    unittest.main()
