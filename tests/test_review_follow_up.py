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
import test_planner  # noqa: E402


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class _ReviewFollowUpTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = test_planner._Repo(Path(self._tmp.name))
        self.state_path = self.repo.root / ".agent-loop" / "loop-state.json"
        self.review_path = self.repo.root / ".agent-loop" / "codex-review.md"
        self.fix_prompt_path = self.repo.root / ".agent-loop" / "fix-prompt.md"
        self.log_path = self.repo.root / ".agent-loop" / "orchestrator.log"

    def _state(self) -> dict:
        return _read_json(self.state_path)

    def _write_review(self, issues: str, *, fix_prompt: str = "") -> None:
        body = "\n".join([
            "# Codex Review",
            "",
            "## Verdict",
            "NEEDS_FIXES",
            "",
            "## Review summary",
            "Review found issues that need routing.",
            "",
            "## Claude summary accuracy",
            "Accurate",
            "",
            "## Scope control",
            "In scope",
            "",
            "## Validation result",
            "Passed",
            "",
            "## Issues found",
            issues.strip(),
            "",
        ])
        if fix_prompt:
            body += "\n".join([
                "## Fix prompt for Claude",
                fix_prompt.strip(),
                "",
            ])
        self.review_path.write_text(body, encoding="utf-8")


class ParseCodexReviewTests(_ReviewFollowUpTestCase):
    def test_issue_owner_inferred_from_codex_owned_paths(self) -> None:
        self._write_review(
            """
### Issue 1
Severity: Medium
Category: Other
File(s): .agent-loop/fix-prompt.md
Problem:
Prompt is stale.

Evidence:
Diff shows old content.

Required fix:
Rewrite the fix prompt from the review findings.

### Issue 2
Severity: High
Category: Bug
File(s): scripts/agent_loop.py
Problem:
Runtime behavior is incorrect.

Evidence:
Observed in review.

Required fix:
Preserve strict-mode semantics on resume.
            """
        )
        review = agent_loop.parse_codex_review(self.review_path)
        self.assertEqual(review.issues[0].owner, agent_loop.ISSUE_OWNER_CODEX)
        self.assertEqual(review.issues[1].owner, agent_loop.ISSUE_OWNER_CLAUDE)


class NeedsFixesFollowUpTests(_ReviewFollowUpTestCase):
    def test_mixed_owner_review_syncs_fix_prompt_and_applies_codex_action(self) -> None:
        data = self._state()
        data["phase"] = "Phase 5 - Approval Modes"
        data["sub_phase"] = "Phase 5C - Strict Mode Pauses"
        data["cycle_count"] = data["max_cycles"]
        self.state_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        self._write_review(
            """
### Issue 1
Severity: Medium
Category: Other
File(s): .agent-loop/loop-state.json
Owner: Codex
Codex action: sync_phase5_runtime_defaults
Problem:
Phase 5 runtime fields are missing from loop-state.

Evidence:
The persisted state artifact omits approval_mode and awaiting_human_for.

Required fix:
Backfill approval_mode=review and awaiting_human_for=null for this Phase 5 state.

### Issue 2
Severity: High
Category: Bug
File(s): scripts/agent_loop.py, tests/test_approval_modes.py
Problem:
Strict-mode resume can bypass strict gates after a mode mutation.

Evidence:
The review and tests show resume succeeding after changing approval_mode mid-cycle.

Required fix:
Refuse resume if the paused cycle is no longer in strict mode and update the tests.
            """,
            fix_prompt="Keep the repair narrow and preserve the shipped review-mode behavior.",
        )
        review = agent_loop.parse_codex_review(self.review_path)
        rc = agent_loop._handle_verdict_loop(
            self.state_path,
            self._state(),
            review.verdict,
            self.repo.root,
            self.log_path,
            review=review,
        )
        self.assertEqual(rc, 2)
        after = self._state()
        self.assertEqual(after["approval_mode"], agent_loop.DEFAULT_APPROVAL_MODE)
        self.assertIn("awaiting_human_for", after)
        fix_prompt = self.fix_prompt_path.read_text(encoding="utf-8")
        self.assertIn("# Claude Code Fix Task", fix_prompt)
        self.assertIn(
            "- Refuse resume if the paused cycle is no longer in strict mode and update the tests.",
            fix_prompt,
        )
        self.assertIn("Keep the repair narrow", fix_prompt)

    def test_codex_owned_issue_without_supported_action_refuses(self) -> None:
        data = self._state()
        data["cycle_count"] = data["max_cycles"]
        self.state_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        self._write_review(
            """
### Issue 1
Severity: Medium
Category: Other
File(s): .agent-loop/phase-plan.md
Owner: Codex
Problem:
Planning artifact needs manual adjustment.

Evidence:
Review found a mismatch.

Required fix:
Rewrite the phase-plan section.
            """
        )
        review = agent_loop.parse_codex_review(self.review_path)
        rc = agent_loop._handle_verdict_loop(
            self.state_path,
            self._state(),
            review.verdict,
            self.repo.root,
            self.log_path,
            review=review,
        )
        self.assertEqual(rc, 2)
        self.assertFalse(self.fix_prompt_path.exists())
        self.assertEqual(self._state()["status"], "halted_input_missing")

    def test_only_codex_owned_issues_refuse_empty_claude_fix_cycle(self) -> None:
        data = self._state()
        data["phase"] = "Phase 5 - Approval Modes"
        data["sub_phase"] = "Phase 5C - Strict Mode Pauses"
        data["cycle_count"] = data["max_cycles"]
        self.state_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        self._write_review(
            """
### Issue 1
Severity: Medium
Category: Other
File(s): .agent-loop/loop-state.json
Owner: Codex
Codex action: sync_phase5_runtime_defaults
Problem:
Phase 5 runtime fields are missing from loop-state.

Evidence:
The persisted state artifact omits approval_mode and awaiting_human_for.

Required fix:
Backfill approval_mode=review and awaiting_human_for=null for this Phase 5 state.
            """
        )
        review = agent_loop.parse_codex_review(self.review_path)
        rc = agent_loop._handle_verdict_loop(
            self.state_path,
            self._state(),
            review.verdict,
            self.repo.root,
            self.log_path,
            review=review,
        )
        self.assertEqual(rc, 2)
        self.assertFalse(self.fix_prompt_path.exists())
        self.assertEqual(self._state()["status"], "halted_input_missing")


if __name__ == "__main__":
    unittest.main()
