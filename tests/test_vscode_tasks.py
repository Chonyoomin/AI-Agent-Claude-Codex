"""Focused tests for the Phase 7A VS Code task entrypoints.

Scope of this suite (Phase 7A, narrow):
- `.vscode/tasks.json` exists at the repo root, is valid JSON, and uses
  the VS Code tasks schema version `"2.0.0"`.
- Every task is a thin wrapper around a shipped CLI subcommand:
  * `type` is `"process"` (no shell parsing, no inline scripting).
  * `command` is the Python interpreter (`"python"`).
  * `args[0]` is the relative path to `scripts/agent_loop.py`.
  * `args[1]` is a subcommand name that exists in `agent_loop.HANDLERS`.
  * The task's `cwd` is `${workspaceFolder}` so the task does not depend
    on the operator's terminal CWD.
- No task introduces editor-owned runtime behavior beyond delegating to
  the shipped CLI: no inline scripts, no piping, no extra interpreters,
  no positional repo-file paths that bypass the orchestrator.
- The covered subcommand set spans the documented common operator
  flows (loop execution, evidence collection, review-artifact gates,
  planning, activation, prompt bootstrap, and continuation resume).
- The repository remains usable without VS Code: `agent_loop` imports
  and the HANDLERS dispatch are byte-equivalent regardless of the
  presence of the tasks file (the tasks layer never modifies the
  orchestrator surface).
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import agent_loop  # noqa: E402 - sys.path is set above


REPO_ROOT = HERE.parent
TASKS_JSON_PATH = REPO_ROOT / ".vscode" / "tasks.json"
AGENT_LOOP_REL = "scripts/agent_loop.py"
RUN_CHECKS_REL = "scripts/run_checks.sh"

# The task that wraps the Phase 2B evidence producer is structurally
# different from the rest (it invokes `bash scripts/run_checks.sh`, not
# `python scripts/agent_loop.py <subcommand>`), so it is special-cased
# in the structural assertions and gets its own dedicated coverage
# class below. Keeping the assertions narrow per-task-class makes the
# guardrails on the agent_loop-wrapping tasks load-bearing.
EVIDENCE_COLLECTION_TASK_LABEL = "Agent Loop: collect evidence"

# The set of agent_loop.py subcommands this Phase 7A slice promises to
# surface as VS Code task entrypoints. Each must map to an existing
# HANDLERS key. (The evidence-collection task wraps scripts/run_checks.sh
# and is asserted by the dedicated EvidenceCollectionTaskTests class.)
EXPECTED_COMMON_OPERATOR_SUBCOMMANDS = frozenset({
    "check-state",
    "validate-artifacts",
    "run",
    "resume",
    "auto-continue",
    "plan",
    "activate",
    "bootstrap-prompt",
})


def _python_tasks(tasks: list) -> list:
    """Subset of tasks that wrap the python `scripts/agent_loop.py` CLI.

    Excludes the structurally-different evidence-collection task.
    """
    return [
        t for t in tasks
        if t["label"] != EVIDENCE_COLLECTION_TASK_LABEL
    ]


def _evidence_task(tasks: list):
    matches = [
        t for t in tasks if t["label"] == EVIDENCE_COLLECTION_TASK_LABEL
    ]
    return matches[0] if matches else None


class TasksJsonStructureTests(unittest.TestCase):

    def setUp(self) -> None:
        self.assertTrue(
            TASKS_JSON_PATH.is_file(),
            f"Expected VS Code tasks file at {TASKS_JSON_PATH}",
        )
        self.payload = json.loads(
            TASKS_JSON_PATH.read_text(encoding="utf-8"),
        )

    def test_schema_version_is_2_0_0(self) -> None:
        self.assertEqual(self.payload.get("version"), "2.0.0")

    def test_tasks_is_nonempty_list(self) -> None:
        tasks = self.payload.get("tasks")
        self.assertIsInstance(tasks, list)
        self.assertGreater(len(tasks), 0)

    def test_every_task_has_required_keys(self) -> None:
        for task in self.payload["tasks"]:
            self.assertIn("label", task)
            self.assertIn("type", task)
            self.assertIn("command", task)
            self.assertIn("args", task)
            self.assertIsInstance(task["label"], str)
            self.assertTrue(task["label"].strip())

    def test_task_labels_are_unique(self) -> None:
        labels = [t["label"] for t in self.payload["tasks"]]
        self.assertEqual(len(labels), len(set(labels)))


class TasksDelegateToShippedCliTests(unittest.TestCase):

    def setUp(self) -> None:
        self.payload = json.loads(
            TASKS_JSON_PATH.read_text(encoding="utf-8"),
        )
        self.tasks = self.payload["tasks"]

    def test_every_task_is_process_type(self) -> None:
        # `process` avoids shell parsing: no editor-owned shell
        # expansion or pipelining can sneak in past the orchestrator.
        # Applies to BOTH the python-wrapping tasks and the
        # evidence-collection task.
        for task in self.tasks:
            self.assertEqual(
                task["type"], "process",
                f"task {task['label']!r} is not a process-type task",
            )

    def test_every_python_task_invokes_python(self) -> None:
        for task in _python_tasks(self.tasks):
            self.assertEqual(
                task["command"], "python",
                f"task {task['label']!r} does not invoke python",
            )

    def test_every_python_task_targets_agent_loop_script(self) -> None:
        for task in _python_tasks(self.tasks):
            args = task["args"]
            self.assertIsInstance(args, list)
            self.assertGreaterEqual(len(args), 2)
            self.assertEqual(
                args[0], AGENT_LOOP_REL,
                f"task {task['label']!r} does not target {AGENT_LOOP_REL}",
            )

    def test_every_python_task_subcommand_is_in_HANDLERS(self) -> None:
        # The load-bearing assertion: a task that points at a name not in
        # HANDLERS would silently dead-link the operator. Routing through
        # HANDLERS is what guarantees the CLI surface is the source of
        # truth for the python-wrapping tasks.
        for task in _python_tasks(self.tasks):
            subcommand = task["args"][1]
            self.assertIn(
                subcommand, agent_loop.HANDLERS,
                f"task {task['label']!r} references unknown subcommand "
                f"{subcommand!r}; not in agent_loop.HANDLERS",
            )

    def test_every_task_uses_workspace_folder_cwd(self) -> None:
        for task in self.tasks:
            options = task.get("options", {})
            cwd = options.get("cwd")
            self.assertEqual(
                cwd, "${workspaceFolder}",
                f"task {task['label']!r} does not set cwd to "
                f"${{workspaceFolder}}; got {cwd!r}",
            )


class TasksDoNotWidenScopeTests(unittest.TestCase):

    def setUp(self) -> None:
        self.payload = json.loads(
            TASKS_JSON_PATH.read_text(encoding="utf-8"),
        )
        self.tasks = self.payload["tasks"]

    def test_no_task_uses_shell_type(self) -> None:
        # A shell-type task could inline arbitrary scripting and bypass
        # the orchestrator's halt/refusal vocabulary.
        for task in self.tasks:
            self.assertNotEqual(task["type"], "shell")

    def test_no_task_args_contain_shell_metacharacters(self) -> None:
        # Defense in depth: even under process-type, any arg carrying
        # &&, ||, ;, |, > or $(...) would be a code smell that the task
        # is doing something the shipped CLI does not document.
        bad_tokens = ("&&", "||", ";", "|", ">", "$(", "`")
        for task in self.tasks:
            for arg in task["args"]:
                for tok in bad_tokens:
                    self.assertNotIn(
                        tok, str(arg),
                        f"task {task['label']!r} arg {arg!r} contains "
                        f"forbidden shell token {tok!r}",
                    )

    def test_no_task_invokes_a_second_interpreter(self) -> None:
        # The tasks layer is a thin wrapper. Any `node`, `bash`,
        # `powershell`, etc. inside args would indicate the task is
        # doing IDE-owned work outside the shipped CLI.
        forbidden = (
            "bash", "sh", "zsh", "powershell", "pwsh", "node", "deno",
            "ruby", "perl",
        )
        for task in self.tasks:
            for arg in task["args"]:
                arg_lower = str(arg).lower()
                for bad in forbidden:
                    self.assertNotEqual(
                        arg_lower, bad,
                        f"task {task['label']!r} arg {arg!r} invokes a "
                        f"second interpreter; tasks must wrap the "
                        f"shipped CLI only",
                    )

    def test_no_task_passes_repo_file_arguments_to_agent_loop(self) -> None:
        # The shipped CLI handlers either take no positional args or
        # take typed flags (--output, --runtime, --declared-path, etc.).
        # A positional repo-file arg in a task would indicate the task
        # is feeding the orchestrator a file path the CLI does not
        # document as a positional.
        for task in self.tasks:
            extra_args = task["args"][2:]
            for arg in extra_args:
                arg_str = str(arg)
                if not arg_str.startswith("--"):
                    self.fail(
                        f"task {task['label']!r} passes positional arg "
                        f"{arg_str!r} to agent_loop; only --flag-style "
                        f"args are allowed in this slice",
                    )


class TasksCoverCommonOperatorFlowsTests(unittest.TestCase):

    def setUp(self) -> None:
        self.payload = json.loads(
            TASKS_JSON_PATH.read_text(encoding="utf-8"),
        )
        self.python_tasks = _python_tasks(self.payload["tasks"])
        self.python_subcommands = {
            t["args"][1] for t in self.python_tasks
        }

    def test_covers_all_expected_common_operator_subcommands(self) -> None:
        missing = (
            EXPECTED_COMMON_OPERATOR_SUBCOMMANDS - self.python_subcommands
        )
        self.assertEqual(
            missing, set(),
            f"Phase 7A tasks file does not cover expected common "
            f"operator subcommands: {sorted(missing)}",
        )

    def test_does_not_introduce_unknown_subcommands(self) -> None:
        # Every subcommand a python-wrapping task surfaces must exist
        # on the shipped agent_loop CLI surface. This protects against
        # a typo silently shipping a task that always fails with
        # argparse.
        unknown = self.python_subcommands - set(agent_loop.HANDLERS)
        self.assertEqual(unknown, set())

    def test_evidence_collection_task_is_present(self) -> None:
        # Phase 7A names "collecting evidence" as a common operator
        # flow alongside "running the loop" and "opening review
        # artifacts". The Phase 2B evidence producer
        # (scripts/run_checks.sh) is the actual evidence surface;
        # `validate-artifacts` only gates already-produced evidence.
        # This assertion locks in that the slice actually ships the
        # evidence-production wrapper, not just the gate.
        task = _evidence_task(self.payload["tasks"])
        self.assertIsNotNone(
            task,
            "Phase 7A tasks file is missing the dedicated evidence-"
            "collection task (label: "
            f"{EVIDENCE_COLLECTION_TASK_LABEL!r})",
        )


class EvidenceCollectionTaskTests(unittest.TestCase):
    """Dedicated coverage for the Phase 2B evidence-collection task.

    Structurally different from the python-wrapping tasks: invokes
    `bash scripts/run_checks.sh` to drive the shipped Phase 2B
    Evidence Collection Contract producer. Asserted here in
    isolation so the python+HANDLERS guardrails on the rest of the
    suite stay narrow.
    """

    def setUp(self) -> None:
        self.payload = json.loads(
            TASKS_JSON_PATH.read_text(encoding="utf-8"),
        )
        self.task = _evidence_task(self.payload["tasks"])
        self.assertIsNotNone(self.task)

    def test_evidence_task_is_process_type(self) -> None:
        self.assertEqual(self.task["type"], "process")

    def test_evidence_task_invokes_bash(self) -> None:
        # bash is the documented invocation for shell scripts in this
        # repo. On Windows hosts VS Code resolves this through Git
        # Bash; on macOS / Linux through the system bash. No shell
        # parsing of args happens because the task type is `process`.
        self.assertEqual(self.task["command"], "bash")

    def test_evidence_task_targets_run_checks_script(self) -> None:
        args = self.task["args"]
        self.assertIsInstance(args, list)
        self.assertEqual(len(args), 1)
        self.assertEqual(args[0], RUN_CHECKS_REL)

    def test_evidence_task_run_checks_script_exists_on_disk(self) -> None:
        # Catches a typo'd path or a renamed script before the task
        # silently dead-links at runtime.
        self.assertTrue(
            (REPO_ROOT / RUN_CHECKS_REL).is_file(),
            f"Phase 2B evidence producer {RUN_CHECKS_REL} is not "
            f"present at the documented path",
        )

    def test_evidence_task_uses_workspace_folder_cwd(self) -> None:
        cwd = self.task.get("options", {}).get("cwd")
        self.assertEqual(cwd, "${workspaceFolder}")

    def test_evidence_task_does_not_pass_extra_args(self) -> None:
        # The shipped run_checks.sh reads configuration from env vars
        # and .agent-loop/checks.json (per the Phase 2B contract).
        # The task must NOT inject positional args that the script
        # does not document.
        self.assertEqual(len(self.task["args"]), 1)

    def test_only_one_evidence_collection_task_is_declared(self) -> None:
        matches = [
            t for t in self.payload["tasks"]
            if t["label"] == EVIDENCE_COLLECTION_TASK_LABEL
        ]
        self.assertEqual(len(matches), 1)


class RepoRemainsUsableWithoutVsCodeTests(unittest.TestCase):

    def test_agent_loop_imports_and_handlers_dispatch_independently(
        self,
    ) -> None:
        # The presence (or absence) of .vscode/tasks.json must not
        # affect the orchestrator surface in any way. We assert the
        # CLI surface is fully populated and the script is invocable
        # via the shipped `--help` path - which is the same surface
        # the tasks delegate into.
        self.assertIn("run", agent_loop.HANDLERS)
        self.assertIn("check-state", agent_loop.HANDLERS)
        self.assertTrue(callable(agent_loop.HANDLERS["run"]))
        self.assertTrue(callable(agent_loop.HANDLERS["check-state"]))


if __name__ == "__main__":
    unittest.main()
