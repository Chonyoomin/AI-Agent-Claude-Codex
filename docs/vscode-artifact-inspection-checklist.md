# VS Code Artifact Inspection Checklist

Use this checklist when verifying the Phase 7B VS Code artifact-inspection
workflow in a live editor session. The Phase 7B test suite proves the task,
settings, and CLI surfaces are structurally correct; this checklist covers the
remaining runtime/editor behaviors that a headless test run cannot exercise.

## Preconditions

- Open the repository root in VS Code.
- Make sure `.vscode/tasks.json` and `.vscode/settings.json` from this repo are
  active in the workspace.
- Ensure the `.agent-loop/` artifact set exists. The inspection view is still
  valid when some artifacts are missing, but at least one present artifact makes
  the verification easier to observe.

## Acceptance Checks

1. Run `Agent Loop: inspect artifacts` from the VS Code task runner.
2. Confirm the task exits successfully and prints the
   `Phase 7B artifact inspection (signal_version=phase-7b-v1)` header.
3. Confirm the artifact rows in the task terminal use repo-relative paths such
   as `.agent-loop/codex-review.md` rather than absolute filesystem paths.
4. Confirm at least one printed repo-relative artifact path is clickable in the
   VS Code terminal and opens the expected file.
5. In the Explorer, confirm `git-diff.patch` is nested under
   `git-status.log`.
6. In the Explorer, confirm `current-task.md` is nested under
   `current-phase.md`.
7. In the Explorer, confirm `fix-prompt.md` is nested under
   `claude-prompt.md`.
8. Open `.agent-loop/git-diff.patch` from the Explorer and confirm VS Code
   renders it with the diff viewer association rather than only as plain text.
9. Confirm the inspection task does not create or modify canonical loop
   artifacts as a side effect.

## Failure Interpretation

- If the CLI task fails to run, treat that as a task/runtime problem.
- If the CLI task runs but the terminal paths are not clickable, treat that as
  a VS Code terminal-behavior or local-settings problem.
- If file nesting does not appear, first check whether the user or workspace has
  disabled Explorer nesting globally.
- If `git-diff.patch` does not open as a diff, first check whether another
  editor association is overriding the workspace setting.

## Scope Note

This checklist is an operator verification aid only. It does not replace the
canonical repo-artifact workflow, and it does not grant VS Code ownership over
runtime state, review state, or evidence truth.
