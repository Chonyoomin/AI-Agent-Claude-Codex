"""Focused tests for the Phase 9C Orchestrator-Driven Prompt Handoff slice.

Scope (Phase 9C, narrow):
- constants match the shipped contract
- happy paths for both `mode="implementation"` (reads claude-prompt.md)
  and `mode="fix"` (reads fix-prompt.md)
- auto-mode detection: `last_verdict == "NEEDS_FIXES"` -> fix;
  otherwise -> implementation
- every documented refusal mode raises `HaltError("halted_input_missing")`
  (or the contract-version mismatch status when applicable)
- canonical-precedence preservation: never mutates loop-state, never
  mutates the canonical prompt artifacts, writes only the named output
  plus the audit log when supplied
- the output-write boundary mirrors the Phase 9B intake boundary:
  refuses output outside `.agent-loop/`, output in the protected set
  (including the Phase 9B intake artifact), output under the memory
  subtree, output that resolves to a directory
- the `dispatch-prompt-handoff` CLI subcommand routes through
  `main(argv)` HANDLERS dispatch end-to-end and refuses fail-closed via
  `_halt`
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

VALID_CLAUDE_PROMPT = (
    "# Claude Code Task\n"
    "\n"
    "## Phase\n"
    "Phase 9C - Orchestrator-Driven Prompt Handoff\n"
    "\n"
    "## Objective\n"
    "Test prompt.\n"
)

VALID_FIX_PROMPT = (
    "# Claude Code Fix Task\n"
    "\n"
    "## Objective\n"
    "Fix prompt body.\n"
    "\n"
    "## Context\n"
    "Test context.\n"
    "\n"
    "## Required fixes\n"
    "Test fixes.\n"
    "\n"
    "## Constraints\n"
    "Test constraints.\n"
    "\n"
    "## Required output\n"
    "Test output.\n"
)


def _make_repo(td: Path) -> Path:
    (td / "AGENTS.md").write_text("test\n", encoding="utf-8")
    (td / "CLAUDE.md").write_text("test\n", encoding="utf-8")
    (td / "TASK.md").write_text("test\n", encoding="utf-8")
    (td / ".agent-loop").mkdir()
    return td


def _plant_loop_state(
    repo_root: Path,
    *,
    last_verdict: str = None,
    status: str = "awaiting_claude_implementation",
) -> Path:
    state_path = repo_root / ".agent-loop" / "loop-state.json"
    state_path.write_text(json.dumps({
        "phase": "Phase 9 - Fully Autonomous PRD-To-Product Mode",
        "sub_phase": "Phase 9C - Orchestrator-Driven Prompt Handoff",
        "task": "handoff-test",
        "status": status,
        "cycle_count": 0,
        "max_cycles": 3,
        "last_verdict": last_verdict,
        "last_verdict_phase": None,
        "contract_version": CONTRACT_VERSION,
        "claude_version": "claude-opus-4-7",
        "codex_version": None,
        "orchestrator_version": "phase-3d-v0",
        "approval_mode": "review",
        "awaiting_human_for": None,
    }), encoding="utf-8")
    return state_path


def _plant_prompts(repo_root: Path) -> tuple[Path, Path]:
    al = repo_root / ".agent-loop"
    claude_prompt = al / "claude-prompt.md"
    fix_prompt = al / "fix-prompt.md"
    claude_prompt.write_text(VALID_CLAUDE_PROMPT, encoding="utf-8")
    fix_prompt.write_text(VALID_FIX_PROMPT, encoding="utf-8")
    return claude_prompt, fix_prompt


class HandoffConstantsTests(unittest.TestCase):

    def test_signal_version_is_phase_9c_v1(self) -> None:
        self.assertEqual(
            agent_loop.PROMPT_HANDOFF_SIGNAL_VERSION, "phase-9c-v1",
        )

    def test_output_rel_is_under_agent_loop(self) -> None:
        self.assertEqual(
            agent_loop.PROMPT_HANDOFF_OUTPUT_REL,
            ".agent-loop/prompt-handoff.json",
        )

    def test_modes_are_exactly_implementation_and_fix(self) -> None:
        self.assertEqual(
            agent_loop.PROMPT_HANDOFF_MODES,
            frozenset({"implementation", "fix"}),
        )

    def test_dispatch_prompt_handoff_is_wired_into_handlers(self) -> None:
        self.assertIn("dispatch-prompt-handoff", agent_loop.HANDLERS)
        self.assertIs(
            agent_loop.HANDLERS["dispatch-prompt-handoff"],
            agent_loop.cmd_dispatch_prompt_handoff,
        )

    def test_protected_output_set_includes_intake_artifact(self) -> None:
        # The Phase 9C handoff must not overwrite the Phase 9B
        # intake artifact and vice versa.
        self.assertIn(
            ".agent-loop/prd-intake.json",
            agent_loop.PROMPT_HANDOFF_PROTECTED_OUTPUT_PATHS,
        )
        self.assertIn(
            ".agent-loop/prompt-handoff.json",
            agent_loop.PRD_INTAKE_PROTECTED_OUTPUT_PATHS,
        )

    def test_protected_output_set_excludes_self_default_path(self) -> None:
        # The handoff is allowed to write to its OWN default; the
        # protected set must not block the slice's own output.
        self.assertNotIn(
            ".agent-loop/prompt-handoff.json",
            agent_loop.PROMPT_HANDOFF_PROTECTED_OUTPUT_PATHS,
        )
        self.assertNotIn(
            ".agent-loop/prd-intake.json",
            agent_loop.PRD_INTAKE_PROTECTED_OUTPUT_PATHS,
        )


class HandoffHappyPathTests(unittest.TestCase):

    def test_explicit_implementation_mode_writes_descriptor(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            claude_prompt, _ = _plant_prompts(repo)
            written = agent_loop.dispatch_prompt_handoff(
                repo, mode="implementation",
            )
            payload = json.loads(written.read_text(encoding="utf-8"))
            self.assertEqual(
                payload["handoff_signal_version"], "phase-9c-v1",
            )
            self.assertEqual(payload["mode"], "implementation")
            self.assertEqual(
                payload["source_prompt_path"],
                ".agent-loop/claude-prompt.md",
            )
            self.assertEqual(
                payload["source_prompt_byte_size"],
                claude_prompt.stat().st_size,
            )
            self.assertIs(payload["advisory_only"], True)
            self.assertEqual(
                payload["canonical_precedence_note"],
                agent_loop.PROMPT_HANDOFF_CANONICAL_PRECEDENCE_NOTE,
            )
            self.assertEqual(payload["task"], "handoff-test")
            self.assertEqual(payload["approval_mode"], "review")
            self.assertEqual(payload["cycle_count"], 0)

    def test_explicit_fix_mode_reads_fix_prompt(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo, last_verdict="NEEDS_FIXES")
            _, fix_prompt = _plant_prompts(repo)
            written = agent_loop.dispatch_prompt_handoff(
                repo, mode="fix",
            )
            payload = json.loads(written.read_text(encoding="utf-8"))
            self.assertEqual(payload["mode"], "fix")
            self.assertEqual(
                payload["source_prompt_path"],
                ".agent-loop/fix-prompt.md",
            )
            self.assertEqual(
                payload["source_prompt_byte_size"],
                fix_prompt.stat().st_size,
            )

    def test_audit_note_lands_when_log_path_supplied(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            _plant_prompts(repo)
            log = repo / ".agent-loop" / "orchestrator.log"
            agent_loop.dispatch_prompt_handoff(
                repo, mode="implementation", log_path=log,
            )
            text = log.read_text(encoding="utf-8")
            self.assertIn("prompt handoff:", text)
            self.assertIn("signal_version=phase-9c-v1", text)
            self.assertIn("mode=implementation", text)
            self.assertIn(
                "source=.agent-loop/claude-prompt.md", text,
            )

    def test_no_log_path_produces_no_orchestrator_log(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            _plant_prompts(repo)
            agent_loop.dispatch_prompt_handoff(
                repo, mode="implementation",
            )
            self.assertFalse(
                (repo / ".agent-loop" / "orchestrator.log").exists(),
            )

    def test_safe_override_under_agent_loop(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            _plant_prompts(repo)
            target = repo / ".agent-loop" / "custom-handoff.json"
            written = agent_loop.dispatch_prompt_handoff(
                repo, mode="implementation", output_path=target,
            )
            self.assertEqual(written, target)
            self.assertTrue(target.is_file())


class HandoffAutoModeDetectionTests(unittest.TestCase):

    def test_no_last_verdict_infers_implementation(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo, last_verdict=None)
            _plant_prompts(repo)
            written = agent_loop.dispatch_prompt_handoff(repo)
            payload = json.loads(written.read_text(encoding="utf-8"))
            self.assertEqual(payload["mode"], "implementation")

    def test_needs_fixes_infers_fix(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo, last_verdict="NEEDS_FIXES")
            _plant_prompts(repo)
            written = agent_loop.dispatch_prompt_handoff(repo)
            payload = json.loads(written.read_text(encoding="utf-8"))
            self.assertEqual(payload["mode"], "fix")

    def test_approved_verdict_still_infers_implementation(self) -> None:
        # An APPROVED verdict means the next dispatch (if any) is a
        # new implementation cycle, not another fix.
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(
                repo, last_verdict="APPROVED_FOR_HUMAN_REVIEW",
            )
            _plant_prompts(repo)
            written = agent_loop.dispatch_prompt_handoff(repo)
            payload = json.loads(written.read_text(encoding="utf-8"))
            self.assertEqual(payload["mode"], "implementation")


class HandoffRefusalTests(unittest.TestCase):

    def test_missing_loop_state_refuses(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            with self.assertRaises(HaltError) as ctx:
                agent_loop.dispatch_prompt_handoff(repo)
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )

    def test_unsupported_contract_version_refuses(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            state_path = repo / ".agent-loop" / "loop-state.json"
            state_path.write_text(json.dumps({
                "phase": "Phase X",
                "sub_phase": "Phase X-A",
                "task": "t",
                "status": "awaiting_claude_implementation",
                "cycle_count": 0,
                "max_cycles": 3,
                "last_verdict": None,
                "last_verdict_phase": None,
                "contract_version": "phase-99-unknown",
                "claude_version": "x",
                "codex_version": None,
                "orchestrator_version": "x",
                "approval_mode": "review",
                "awaiting_human_for": None,
            }), encoding="utf-8")
            _plant_prompts(repo)
            with self.assertRaises(HaltError) as ctx:
                agent_loop.dispatch_prompt_handoff(repo)
            self.assertEqual(
                ctx.exception.status,
                "halted_contract_version_mismatch",
            )

    def test_unknown_mode_refuses(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            _plant_prompts(repo)
            with self.assertRaises(HaltError) as ctx:
                agent_loop.dispatch_prompt_handoff(
                    repo, mode="freeform",
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )
            self.assertIn(
                "not in shipped vocabulary", str(ctx.exception),
            )

    def test_non_string_mode_refuses(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            _plant_prompts(repo)
            with self.assertRaises(HaltError) as ctx:
                agent_loop.dispatch_prompt_handoff(repo, mode=42)
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )

    def test_missing_implementation_prompt_refuses(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            # Plant only the fix prompt.
            (repo / ".agent-loop" / "fix-prompt.md").write_text(
                VALID_FIX_PROMPT, encoding="utf-8",
            )
            with self.assertRaises(HaltError) as ctx:
                agent_loop.dispatch_prompt_handoff(
                    repo, mode="implementation",
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )

    def test_empty_prompt_refuses(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            (repo / ".agent-loop" / "claude-prompt.md").write_text(
                "   \n  \n", encoding="utf-8",
            )
            with self.assertRaises(HaltError) as ctx:
                agent_loop.dispatch_prompt_handoff(
                    repo, mode="implementation",
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )

    def test_missing_fix_prompt_under_needs_fixes_refuses(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo, last_verdict="NEEDS_FIXES")
            # Plant only the implementation prompt.
            (repo / ".agent-loop" / "claude-prompt.md").write_text(
                VALID_CLAUDE_PROMPT, encoding="utf-8",
            )
            with self.assertRaises(HaltError) as ctx:
                agent_loop.dispatch_prompt_handoff(repo)
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )


class HandoffOutputBoundaryTests(unittest.TestCase):

    def _setup(self, td: str) -> Path:
        repo = _make_repo(Path(td))
        _plant_loop_state(repo)
        _plant_prompts(repo)
        return repo

    def test_refuses_output_outside_agent_loop_dir(self) -> None:
        with TemporaryDirectory() as td:
            repo = self._setup(td)
            with self.assertRaises(HaltError) as ctx:
                agent_loop.dispatch_prompt_handoff(
                    repo, mode="implementation",
                    output_path=repo / "TASK.md",
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )
            self.assertIn(
                "must be under .agent-loop/", str(ctx.exception),
            )

    def test_refuses_each_protected_output_target(self) -> None:
        with TemporaryDirectory() as td:
            repo = self._setup(td)
            for rel in sorted(
                agent_loop.PROMPT_HANDOFF_PROTECTED_OUTPUT_PATHS,
            ):
                with self.subTest(rel=rel):
                    with self.assertRaises(HaltError) as ctx:
                        agent_loop.dispatch_prompt_handoff(
                            repo, mode="implementation",
                            output_path=repo / rel,
                        )
                    self.assertEqual(
                        ctx.exception.status, "halted_input_missing",
                    )

    def test_refuses_output_overwriting_intake_artifact(self) -> None:
        # Cross-slice protection: the Phase 9C handoff cannot
        # overwrite the Phase 9B intake artifact.
        with TemporaryDirectory() as td:
            repo = self._setup(td)
            with self.assertRaises(HaltError) as ctx:
                agent_loop.dispatch_prompt_handoff(
                    repo, mode="implementation",
                    output_path=(
                        repo / ".agent-loop" / "prd-intake.json"
                    ),
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )

    def test_refuses_output_under_memory_subtree(self) -> None:
        with TemporaryDirectory() as td:
            repo = self._setup(td)
            with self.assertRaises(HaltError) as ctx:
                agent_loop.dispatch_prompt_handoff(
                    repo, mode="implementation",
                    output_path=(
                        repo / ".agent-loop" / "memory" / "x.json"
                    ),
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )

    def test_refuses_output_is_directory(self) -> None:
        with TemporaryDirectory() as td:
            repo = self._setup(td)
            target = repo / ".agent-loop" / "handoff-dir"
            target.mkdir()
            with self.assertRaises(HaltError) as ctx:
                agent_loop.dispatch_prompt_handoff(
                    repo, mode="implementation",
                    output_path=target,
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )


class HandoffCanonicalPrecedenceTests(unittest.TestCase):

    def test_does_not_mutate_loop_state(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            state_path = _plant_loop_state(repo)
            _plant_prompts(repo)
            before = state_path.read_bytes()
            agent_loop.dispatch_prompt_handoff(
                repo, mode="implementation",
            )
            after = state_path.read_bytes()
            self.assertEqual(before, after)

    def test_does_not_mutate_canonical_prompt_artifacts(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            cp, fp = _plant_prompts(repo)
            cp_before = cp.read_bytes()
            fp_before = fp.read_bytes()
            agent_loop.dispatch_prompt_handoff(
                repo, mode="implementation",
            )
            agent_loop.dispatch_prompt_handoff(repo, mode="fix")
            self.assertEqual(cp.read_bytes(), cp_before)
            self.assertEqual(fp.read_bytes(), fp_before)


class HandoffCliTests(unittest.TestCase):

    def setUp(self) -> None:
        self.td = TemporaryDirectory()
        self.repo = Path(self.td.name)
        _make_repo(self.repo)
        _plant_loop_state(self.repo)
        _plant_prompts(self.repo)
        import os
        self._prev_cwd = os.getcwd()
        os.chdir(self.repo)

    def tearDown(self) -> None:
        import os
        os.chdir(self._prev_cwd)
        self.td.cleanup()

    def test_cli_dispatch_success_default_mode(self) -> None:
        rc = agent_loop.main(["dispatch-prompt-handoff"])
        self.assertEqual(rc, 0)
        out = self.repo / ".agent-loop" / "prompt-handoff.json"
        self.assertTrue(out.is_file())
        payload = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(payload["mode"], "implementation")

    def test_cli_dispatch_success_explicit_fix_mode(self) -> None:
        rc = agent_loop.main([
            "dispatch-prompt-handoff", "--mode", "fix",
        ])
        self.assertEqual(rc, 0)
        out = self.repo / ".agent-loop" / "prompt-handoff.json"
        payload = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(payload["mode"], "fix")

    def test_cli_refuses_unknown_mode_via_argparse(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            agent_loop.main([
                "dispatch-prompt-handoff", "--mode", "freeform",
            ])
        self.assertEqual(ctx.exception.code, 2)

    def test_cli_refuses_absolute_output(self) -> None:
        rc = agent_loop.main([
            "dispatch-prompt-handoff",
            "--output", str(
                (self.repo / ".agent-loop" / "x.json").resolve(),
            ),
        ])
        self.assertEqual(rc, 2)

    def test_cli_refuses_output_under_memory_subtree(self) -> None:
        rc = agent_loop.main([
            "dispatch-prompt-handoff",
            "--output", ".agent-loop/memory/x.json",
        ])
        self.assertEqual(rc, 2)

    def test_cli_refuses_output_overwriting_intake_artifact(
        self,
    ) -> None:
        rc = agent_loop.main([
            "dispatch-prompt-handoff",
            "--output", ".agent-loop/prd-intake.json",
        ])
        self.assertEqual(rc, 2)

    def test_cli_safe_override_succeeds(self) -> None:
        rc = agent_loop.main([
            "dispatch-prompt-handoff",
            "--output", ".agent-loop/custom-handoff.json",
        ])
        self.assertEqual(rc, 0)
        self.assertTrue(
            (
                self.repo / ".agent-loop" / "custom-handoff.json"
            ).is_file(),
        )


if __name__ == "__main__":
    unittest.main()
