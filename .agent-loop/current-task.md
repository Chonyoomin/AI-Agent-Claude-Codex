# Current Task

## Phase
Phase 10 - Future Product Features

## Sub-Phase
Phase 10U - MCP Action Guardrails And Per-Tool Approval Policies

## Status
Phase 10T is complete and approved to advance. Phase 10U is now active as the next mainline slice focused on adding the mutation boundaries, refusal behavior, auditing, per-tool allow-lists, and approval prompts required before any non-read-only MCP-assisted runtime action is allowed through the desktop app.

## Task
Implement Phase 10U for the agent loop. This slice should add the mutation boundaries, refusal behavior, auditing, per-tool allow-lists, and approval prompts required before any non-read-only MCP-assisted runtime action is allowed through the desktop app.

## Notes

- keep this slice bounded to mutation-capable MCP guardrails and approval policy in the desktop app; do not jump into RAG runtime or concurrency work yet
- preserve the shipped ownership boundaries, evidence-review model, approval semantics, desktop-app boundaries, and canonical-artifact-first model while adding bounded MCP action guardrails
- do not widen into hidden orchestration, silent in-flight loop mutation, credential capture beyond explicit operator approval flow, RAG, policy-pack, packaging, or auto-update work
