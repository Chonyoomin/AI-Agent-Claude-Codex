# Current Task

## Phase
Phase 10 - Future Product Features

## Sub-Phase
Phase 10Q - Desktop App Run Profiles And Approval Controls

## Status
Phase 10P is complete and approved to advance. Phase 10Q is now active as the next mainline slice focused on adding a first-class desktop surface for selecting run profiles, approval mode, autonomy level, and PRD-to-completion vs bounded-run execution policies without introducing hidden UI-only state.

## Task
Implement Phase 10Q for the agent loop. This slice should add the first desktop run-profile and approval-controls surface so an operator can inspect and deliberately choose approval mode, autonomy level, PRD-to-completion vs bounded-run mode, and related execution policies through explicit controls that map back to canonical runtime state instead of hidden desktop-only settings.

## Notes

- keep this slice bounded to run profiles and approval controls; do not jump into PRD intake, MCP runtime, RAG runtime, or concurrency work yet
- preserve the shipped ownership boundaries, phase gating, audit visibility, desktop-app boundaries, and canonical-artifact-first model while adding operator-selectable execution-policy UX
- do not widen into hidden orchestration, silent in-flight mode mutation, credential capture, MCP runtime actions, RAG, policy-pack, packaging, or auto-update work
