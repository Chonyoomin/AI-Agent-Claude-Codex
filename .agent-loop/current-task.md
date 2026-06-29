# Current Task

## Phase
Phase 10 - Future Product Features

## Sub-Phase
Phase 10T - MCP Read-Only Assistance In Desktop App

## Status
Phase 10S is complete and approved to advance. Phase 10T is now active as the next mainline slice focused on implementing the first user-selectable MCP read-only assistance surfaces in the desktop app without mutating canonical artifacts or bypassing evidence review.

## Task
Implement Phase 10T for the agent loop. This slice should add the first user-selectable MCP read-only assistance surfaces in the desktop app so operators can enable approved context-gathering tools from the desktop app without mutating canonical artifacts or bypassing evidence review.

## Notes

- keep this slice bounded to read-only MCP assistance in the desktop app; do not jump into mutation-capable MCP actions, RAG runtime, or concurrency work yet
- preserve the shipped ownership boundaries, evidence-review model, approval semantics, desktop-app boundaries, and canonical-artifact-first model while adding the first user-facing MCP assistance surface
- do not widen into hidden orchestration, silent in-flight loop mutation, credential capture, mutation-capable MCP runtime, RAG, policy-pack, packaging, or auto-update work
