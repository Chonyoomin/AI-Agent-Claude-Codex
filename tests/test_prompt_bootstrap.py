"""Focused tests for the Phase 5F phase-start Claude prompt bootstrap.

Scope of this suite (Phase 5F, narrow):
- the `bootstrap-prompt` subcommand synthesizes
  `.agent-loop/claude-prompt.md` from canonical active phase/task
  artifacts when the four sources are present, non-empty, and mutually
  consistent and loop-state.json is in the post-activation
  `awaiting_claude_implementation` status
- the bootstrap refuses with `halted_input_missing` and writes no
  prompt when:
  - any required source artifact is missing or empty
  - any required section / subsection is missing or empty
  - loop-state.json phase / sub_phase / task disagrees with TASK.md /
    current-task.md / current-phase.md
  - the active sub-phase has no `## <sub_phase>` section in
    phase-plan.md, or that section's `### Status` does not begin with
    `Active`
  - loop-state.json status is not `awaiting_claude_implementation`
- the bootstrap is purely additive: it never modifies the fix-prompt
  path, never touches loop-state.json's planning fields, and only
  writes `.agent-loop/claude-prompt.md` plus an audit `note:` line in
  `.agent-loop/orchestrator.log` on success
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
sys.path.insert(0, str(HERE))

import agent_loop  # noqa: E402


PHASE = "Phase 5 - Approval Modes"
SUB_PHASE = "Phase 5Z - Synthetic Bootstrap Slice"
TASK = "Synthesize the bootstrapped prompt from canonical artifacts."


class _BootstrapRepo:
    """Minimal repo tree for the Phase 5F bootstrap. Independent of
    `tests/test_planner._Repo` so the fixture's defaults exactly match
    the active sub-phase the test wants to exercise."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.al = root / ".agent-loop"
        self.al.mkdir(parents=True, exist_ok=True)
        # Repo-root markers.
        (root / "AGENTS.md").write_text("# AGENTS\n", encoding="utf-8")
        (root / "CLAUDE.md").write_text("# CLAUDE\n", encoding="utf-8")
        (root / "README.md").write_text("# README\n", encoding="utf-8")
        # Coherent canonical sources for the active phase/sub_phase.
        self.write_task_md()
        self.write_current_task_md()
        self.write_current_phase_md()
        self.write_phase_plan_md()
        self.write_loop_state()

    # ----- canonical writers -----

    def write_task_md(self, *, active_phase: str = PHASE,
                      active_sub_phase: str = SUB_PHASE,
                      active_task: str = TASK,
                      phase_outcome: str = "- artifact A is created\n- artifact B is updated",
                      out_of_scope: str = "- no Git automation\n- no contract edits") -> None:
        (self.root / "TASK.md").write_text(
            "# TASK.md\n\n"
            "## Human Objective\n\nBuild the thing.\n\n"
            "## Project Intent\n\nDeliver phase by phase.\n\n"
            f"## Active Phase\n\n{active_phase}\n\n"
            f"## Active Sub-Phase\n\n{active_sub_phase}\n\n"
            "## Phase Status\n\nActive.\n\n"
            f"## Active Task\n\n{active_task}\n\n"
            f"## Phase Outcome Required Now\n\n{phase_outcome}\n\n"
            "## Next-Phase Gate\n\nHuman approval required.\n\n"
            f"## Out Of Scope For Current Phase\n\n{out_of_scope}\n",
            encoding="utf-8",
        )

    def write_current_task_md(self, *, phase: str = PHASE,
                              sub_phase: str = SUB_PHASE,
                              task: str = TASK) -> None:
        (self.al / "current-task.md").write_text(
            "# Current Task\n\n"
            f"## Phase\n{phase}\n\n"
            f"## Sub-Phase\n{sub_phase}\n\n"
            f"## Status\n{sub_phase} active.\n\n"
            f"## Task\n{task}\n",
            encoding="utf-8",
        )

    def write_current_phase_md(self, *, phase: str = PHASE,
                               sub_phase: str = SUB_PHASE) -> None:
        (self.al / "current-phase.md").write_text(
            f"# Current Phase\n\n{phase} (sub-phase: {sub_phase})\n",
            encoding="utf-8",
        )

    def write_phase_plan_md(self, *, sub_phase: str = SUB_PHASE,
                            status_line: str = "Active. Implementation in flight.",
                            objective: str = "Synthesize a phase-start prompt.",
                            definition_of_done: str = "- bullet one\n- bullet two",
                            exclusions: str = "- no broad scope\n- no contract edits") -> None:
        (self.al / "phase-plan.md").write_text(
            "# Phase Plan\n\n"
            "## Active Phase\n\n"
            f"{PHASE} (sub-phase: {sub_phase})\n\n"
            "## Phase 5A - Approval Modes Contract\n\n"
            "### Status\n\nComplete. Approved.\n\n"
            f"## {sub_phase}\n\n"
            f"### Status\n\n{status_line}\n\n"
            f"### Objective\n\n{objective}\n\n"
            f"### Definition of done\n\n{definition_of_done}\n\n"
            f"### Exclusions\n\n{exclusions}\n",
            encoding="utf-8",
        )

    def write_loop_state(self, *, phase: str = PHASE, sub_phase: str = SUB_PHASE,
                         task: str = TASK,
                         status: str = "awaiting_claude_implementation") -> None:
        state = {
            "phase": phase,
            "sub_phase": sub_phase,
            "task": task,
            "status": status,
            "cycle_count": 0,
            "max_cycles": 3,
            "last_verdict": None,
            "last_verdict_phase": None,
            "contract_version": "phase-3a-v2",
            "claude_version": "stub-claude",
            "codex_version": None,
            "orchestrator_version": "phase-3d-v0",
            "approval_mode": "review",
            "awaiting_human_for": None,
        }
        (self.al / "loop-state.json").write_text(
            json.dumps(state, indent=2) + "\n", encoding="utf-8",
        )

    # ----- read helpers -----

    def state(self) -> dict:
        return json.loads(
            (self.al / "loop-state.json").read_text(encoding="utf-8"),
        )

    def prompt_text(self) -> str:
        p = self.al / "claude-prompt.md"
        return p.read_text(encoding="utf-8") if p.exists() else ""

    def log_text(self) -> str:
        p = self.al / "orchestrator.log"
        return p.read_text(encoding="utf-8") if p.exists() else ""


class _PromptBootstrapTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = _BootstrapRepo(Path(self._tmp.name))


# ----- success path -----

class PromptBootstrapSuccessTests(_PromptBootstrapTestCase):

    def test_writes_prompt_with_canonical_fields_when_artifacts_consistent(
        self,
    ) -> None:
        rc = agent_loop.bootstrap_claude_prompt(self.repo.root)
        self.assertEqual(rc, 0)
        prompt = self.repo.prompt_text()
        self.assertTrue(prompt, "claude-prompt.md must be written on success")
        # Required headers.
        for header in (
            "# Claude Code Task",
            "## Phase",
            "## Objective",
            "## Context",
            "## Required work",
            "## Constraints",
            "## Required output",
        ):
            self.assertIn(header, prompt, f"prompt is missing header {header!r}")
        # Canonical fields landed in the expected sections.
        self.assertIn(SUB_PHASE, prompt)
        self.assertIn(TASK, prompt)
        self.assertIn("Synthesize a phase-start prompt.", prompt)  # phase-plan Objective
        self.assertIn("- bullet one", prompt)  # phase-plan Definition of done
        self.assertIn("- no broad scope", prompt)  # phase-plan Exclusions
        self.assertIn("After implementation, write `.agent-loop/claude-summary.md`", prompt)
        # Audit-trail note recorded.
        self.assertIn("prompt bootstrap:", self.repo.log_text())
        self.assertIn(SUB_PHASE, self.repo.log_text())

    def test_bootstrap_does_not_modify_loop_state_planning_fields(self) -> None:
        before = self.repo.state()
        agent_loop.bootstrap_claude_prompt(self.repo.root)
        after = self.repo.state()
        for k in ("phase", "sub_phase", "task", "status", "cycle_count",
                  "max_cycles", "approval_mode", "awaiting_human_for"):
            self.assertEqual(
                after.get(k), before.get(k),
                f"bootstrap must not modify loop-state field {k!r}",
            )

    def test_bootstrap_does_not_touch_fix_prompt(self) -> None:
        # Pre-write a fix-prompt to prove it survives untouched.
        fix_prompt_path = self.repo.al / "fix-prompt.md"
        fix_prompt_path.write_text("preserved", encoding="utf-8")
        agent_loop.bootstrap_claude_prompt(self.repo.root)
        self.assertEqual(fix_prompt_path.read_text(encoding="utf-8"), "preserved")


# ----- refusal paths -----

class PromptBootstrapStatusRefusalTests(_PromptBootstrapTestCase):

    def test_refuses_when_status_is_not_awaiting_claude_implementation(self) -> None:
        for status in (
            "claude_implementing", "evidence_capture", "awaiting_codex_review",
            "phase_complete_awaiting_human_approval",
            "halted_failed_requires_human",
            "halted_awaiting_human_pre_claude_prompt",
        ):
            with self.subTest(status=status):
                self.repo.write_loop_state(status=status)
                rc = agent_loop.bootstrap_claude_prompt(self.repo.root)
                self.assertEqual(rc, 2)
                self.assertFalse(
                    (self.repo.al / "claude-prompt.md").exists(),
                    "no prompt may be written on a status refusal",
                )
                self.assertTrue(
                    self.repo.state()["status"].startswith("halted_"),
                    "status must be halted_* after the refusal",
                )


class PromptBootstrapMissingSourceRefusalTests(_PromptBootstrapTestCase):

    def test_refuses_when_task_md_missing(self) -> None:
        (self.repo.root / "TASK.md").unlink()
        rc = agent_loop.bootstrap_claude_prompt(self.repo.root)
        self.assertEqual(rc, 2)
        self.assertFalse((self.repo.al / "claude-prompt.md").exists())

    def test_refuses_when_current_task_md_missing(self) -> None:
        (self.repo.al / "current-task.md").unlink()
        rc = agent_loop.bootstrap_claude_prompt(self.repo.root)
        self.assertEqual(rc, 2)
        self.assertFalse((self.repo.al / "claude-prompt.md").exists())

    def test_refuses_when_current_phase_md_missing(self) -> None:
        (self.repo.al / "current-phase.md").unlink()
        rc = agent_loop.bootstrap_claude_prompt(self.repo.root)
        self.assertEqual(rc, 2)
        self.assertFalse((self.repo.al / "claude-prompt.md").exists())

    def test_refuses_when_phase_plan_md_missing(self) -> None:
        (self.repo.al / "phase-plan.md").unlink()
        rc = agent_loop.bootstrap_claude_prompt(self.repo.root)
        self.assertEqual(rc, 2)
        self.assertFalse((self.repo.al / "claude-prompt.md").exists())

    def test_refuses_when_task_md_active_task_section_missing(self) -> None:
        # Re-author TASK.md without an `## Active Task` section.
        self.repo.write_task_md(active_task="")  # empty body
        rc = agent_loop.bootstrap_claude_prompt(self.repo.root)
        self.assertEqual(rc, 2)
        self.assertFalse((self.repo.al / "claude-prompt.md").exists())


class PromptBootstrapCrossArtifactRefusalTests(_PromptBootstrapTestCase):

    def test_refuses_when_loop_state_phase_disagrees_with_task_md(self) -> None:
        self.repo.write_loop_state(phase="Phase 4 - Phase Planning Automation")
        rc = agent_loop.bootstrap_claude_prompt(self.repo.root)
        self.assertEqual(rc, 2)
        self.assertFalse((self.repo.al / "claude-prompt.md").exists())

    def test_refuses_when_loop_state_sub_phase_disagrees_with_current_task(
        self,
    ) -> None:
        self.repo.write_current_task_md(sub_phase="Phase 5Y - Bogus Sub-Phase")
        rc = agent_loop.bootstrap_claude_prompt(self.repo.root)
        self.assertEqual(rc, 2)
        self.assertFalse((self.repo.al / "claude-prompt.md").exists())

    def test_refuses_when_loop_state_task_disagrees_with_task_md(self) -> None:
        self.repo.write_loop_state(task="A different task entirely.")
        rc = agent_loop.bootstrap_claude_prompt(self.repo.root)
        self.assertEqual(rc, 2)
        self.assertFalse((self.repo.al / "claude-prompt.md").exists())

    def test_refuses_when_current_phase_md_omits_sub_phase(self) -> None:
        # Strip the sub_phase out of current-phase.md.
        (self.repo.al / "current-phase.md").write_text(
            f"# Current Phase\n\n{PHASE}\n", encoding="utf-8",
        )
        rc = agent_loop.bootstrap_claude_prompt(self.repo.root)
        self.assertEqual(rc, 2)
        self.assertFalse((self.repo.al / "claude-prompt.md").exists())


class PromptBootstrapPhasePlanRefusalTests(_PromptBootstrapTestCase):

    def test_refuses_when_phase_plan_lacks_active_sub_phase_section(self) -> None:
        # Re-author phase-plan.md without a section for the active sub_phase.
        (self.repo.al / "phase-plan.md").write_text(
            "# Phase Plan\n\n## Active Phase\n\n"
            f"{PHASE}\n\n"
            "## Phase 5A - Approval Modes Contract\n\n"
            "### Status\n\nComplete. Approved.\n",
            encoding="utf-8",
        )
        rc = agent_loop.bootstrap_claude_prompt(self.repo.root)
        self.assertEqual(rc, 2)
        self.assertFalse((self.repo.al / "claude-prompt.md").exists())

    def test_refuses_when_phase_plan_sub_phase_status_is_not_active(self) -> None:
        self.repo.write_phase_plan_md(status_line="Complete. Approved.")
        rc = agent_loop.bootstrap_claude_prompt(self.repo.root)
        self.assertEqual(rc, 2)
        self.assertFalse((self.repo.al / "claude-prompt.md").exists())

    def test_refuses_when_phase_plan_sub_phase_objective_is_empty(self) -> None:
        self.repo.write_phase_plan_md(objective="")
        rc = agent_loop.bootstrap_claude_prompt(self.repo.root)
        self.assertEqual(rc, 2)
        self.assertFalse((self.repo.al / "claude-prompt.md").exists())

    def test_refuses_when_phase_plan_sub_phase_definition_of_done_is_empty(
        self,
    ) -> None:
        self.repo.write_phase_plan_md(definition_of_done="")
        rc = agent_loop.bootstrap_claude_prompt(self.repo.root)
        self.assertEqual(rc, 2)
        self.assertFalse((self.repo.al / "claude-prompt.md").exists())


class PromptBootstrapPreserveFixPromptTests(_PromptBootstrapTestCase):
    """The bootstrap is a phase-START path; it must not interfere with
    the Phase 5E fix-prompt path. A pre-existing fix-prompt is
    preserved by both the success and refusal paths (the bootstrap only
    writes claude-prompt.md)."""

    def test_refusal_preserves_existing_fix_prompt(self) -> None:
        fix_prompt_path = self.repo.al / "fix-prompt.md"
        fix_prompt_path.write_text("preserved-on-refusal", encoding="utf-8")
        self.repo.write_loop_state(status="halted_failed_requires_human")
        rc = agent_loop.bootstrap_claude_prompt(self.repo.root)
        self.assertEqual(rc, 2)
        self.assertEqual(
            fix_prompt_path.read_text(encoding="utf-8"),
            "preserved-on-refusal",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
