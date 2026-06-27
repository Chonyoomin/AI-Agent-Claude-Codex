# Current Task

## Phase
Phase 10 - Future Product Features

## Sub-Phase
Phase 10P - Desktop App Operator Setup And CLI Onboarding

## Status
Phase 10O is complete and approved to advance. Phase 10P is now active as the next mainline slice focused on adding guided desktop setup for controller-root selection, target/work-folder validation, and local Claude/Codex CLI onboarding without weakening the shipped safety and artifact boundaries.

## Task
Implement Phase 10P for the agent loop. This slice should add the first guided desktop setup flow for selecting a controller root, validating a target/work folder, configuring local Claude/Codex CLI adapter commands, checking required local-tool availability, and surfacing fail-closed refusal messages when the environment is not ready.

## Notes

- keep this slice bounded to guided desktop setup and CLI onboarding; do not jump into PRD intake, MCP runtime, RAG runtime, or concurrency work yet
- preserve the shipped ownership boundaries, phase gating, audit visibility, desktop-app boundaries, and canonical-artifact-first model while adding setup UX
- do not widen into hidden orchestration, credential capture, MCP runtime actions, RAG, policy-pack, packaging, or auto-update work
