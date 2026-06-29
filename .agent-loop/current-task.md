# Current Task

## Phase
Phase 10 - Future Product Features

## Sub-Phase
Phase 10R - Desktop App PRD Intake And Project Start Flow

## Status
Phase 10Q is complete and approved to advance. Phase 10R is now active as the next mainline slice focused on adding the first desktop workflow for creating or selecting a target project, attaching a PRD or product brief, choosing the target folder, and starting a run without manual prompt-artifact preparation.

## Task
Implement Phase 10R for the agent loop. This slice should add the first desktop PRD-intake and project-start workflow so an operator can create or select a target project, attach a PRD or product brief, choose the target folder, and start a run without manually preparing prompt artifacts by hand.

## Notes

- keep this slice bounded to PRD intake and project start flow; do not jump into MCP runtime, RAG runtime, or concurrency work yet
- preserve the shipped ownership boundaries, phase gating, audit visibility, desktop-app boundaries, and canonical-artifact-first model while adding desktop-side project-start UX
- do not widen into hidden orchestration, silent in-flight loop mutation, credential capture, MCP runtime actions, RAG, policy-pack, packaging, or auto-update work
