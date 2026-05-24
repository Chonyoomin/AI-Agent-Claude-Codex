# TASK.md

## Human Objective

Build the Agentic AI Coding Loop project from start to finish as a phase-gated local orchestration system where:

- Codex plans the work, updates task state, reviews implementation, and generates fix prompts
- Claude Code implements only the active phase
- the local orchestrator captures evidence and enforces loop state
- each phase stops for human approval before the next phase begins
- the system never auto-commits or auto-pushes

## Project Intent

The goal is to let a human provide the desired outcome once, then have the Codex and Claude loop carry the project forward phase by phase with review, fixes, and human gating between phases.

## Active Phase

Phase 3 - Scripted Orchestrator MVP

## Active Sub-Phase

Phase 3D - Subprocess-Driven Claude/Codex Adapters

## Phase Status

Phase 3C (automated fix-cycle handling) is complete and approved by the human to advance. Phase 3D replaces the manual-handoff Claude and Codex adapter stubs in `scripts/agent_loop.py` with real subprocess-driven adapters that invoke the user's configured Claude / Codex CLI command, while preserving the verdict loop, the fix-cycle, the fail-closed validators, the threshold-policy halt, the `halted_human_stop` persistence, and the `codex_version` null-note behavior. The manual-handoff adapters remain available as the fallback when the user has not configured a subprocess command.

## Active Task

Implement the next 3x sub-phase for Phase 3C: subprocess-driven Claude and Codex adapters in `scripts/agent_loop.py`. Add `SubprocessClaudeAdapter` and `SubprocessCodexAdapter` classes whose interface matches the existing manual-handoff classes; select adapters via `AGENT_LOOP_CLAUDE_CMD` / `AGENT_LOOP_CODEX_CMD` environment variables; resolve model identifiers via `AGENT_LOOP_CLAUDE_MODEL` / `AGENT_LOOP_CODEX_MODEL` with a sane fallback for Claude (command's first token, extracted via `shlex.split(posix=True)`) and a contract-correct null fallback for Codex (orchestrator's existing null-note path fires); execute the operator-provided command via `subprocess.run(self.command, shell=True, ...)` with `cwd` set to the repository root and the prompt file content piped to stdin (the platform shell - cmd.exe on Windows, /bin/sh on POSIX - parses operator quoting consistently, avoiding the Windows-backslash traps of pre-splitting the command into argv); capture exit code and wall-clock duration; confirm the expected output artifact exists and its mtime has advanced, preserving fail-closed-on-stale-mtime; never parse model-specific output formats inside the core loop. Bump `ORCHESTRATOR_VERSION` to `phase-3d-v0`.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 3 / 3D as active
- `.agent-loop/phase-plan.md` marks Phase 3C complete and contains a Phase 3D section
- `scripts/agent_loop.py` defines `SubprocessClaudeAdapter` and `SubprocessCodexAdapter`; selection factories pick the subprocess adapter when the corresponding `*_CMD` env var is set, otherwise fall back to the existing manual-handoff stub
- subprocess adapters honor the Phase 3A contract's adapter-boundary requirements: execute the operator-provided command via `subprocess.run(self.command, shell=True, ...)` with `cwd = repo_root` and the prompt piped to stdin, captured exit code and wall-clock duration, fail-closed mtime check, no model-specific output parsing in the core loop, contract-correct model_id resolution rules (Claude falls back via `shlex.split(posix=True)` to the first command token; Codex stays null and triggers the existing `orchestrator.log` note)
- `ORCHESTRATOR_VERSION = "phase-3d-v0"`; the running orchestrator persists this into `loop-state.json` on the next `run`
- `README.md` reflects the Phase 3D active status and documents the new env-var configuration plus the manual-handoff fallback
- no approval modes, no Git automation, and no editor integration are introduced in this sub-phase

## Next-Phase Gate

Do not start the next 3x sub-phase (approval modes, editor integration, package-layout refactor, etc.) until:

- this Phase 3D slice receives `APPROVED_FOR_HUMAN_REVIEW`
- the human explicitly approves moving to the next sub-phase
- Codex updates `TASK.md`, `.agent-loop/current-task.md`, and `.agent-loop/current-phase.md` for the next sub-phase

## Out Of Scope For Current Phase

- approval mode implementation (Phase 5)
- editor integration (Phase 7)
- MCP support (future)
- removal of the manual-handoff adapter classes (kept as the fallback)
- parsing of Claude / Codex CLI output formats inside the core loop (the Phase 3A contract forbids that; subprocess stdout/stderr is captured but not interpreted)
- streaming subprocess output to a TTY (subprocess output is captured, not streamed; future sub-phases can layer streaming on top)
- a `scripts/agent_loop/` package layout (single-file keeps the diff minimal)
- concurrent invocation of multiple Claude / Codex processes (single sequential subprocess per step)
- any change to the Phase 2A Evidence Collection Contract
- any change to `scripts/run_checks.sh`
- any change to the Phase 3A Orchestrator Contract body
- adding any real test/lint/typecheck/build suite to the repository (still a documentation-only project)
- Git automation (no commit, push, branch, stash, reset, checkout, tag)
