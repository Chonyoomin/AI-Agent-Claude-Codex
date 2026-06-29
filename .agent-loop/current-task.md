# Current Task

## Phase
Phase 10 - Future Product Features

## Sub-Phase
Phase 10S - MCP Server Selection UX Contract

## Status
Phase 10R is complete and approved to advance. Phase 10S is now active as the next mainline slice focused on defining how the desktop app should present available MCP servers, permission classes, read-only versus deferred-mutating capability labels, per-server safety copy, and operator approval requirements before MCP enablement becomes user-facing.

## Task
Implement Phase 10S for the agent loop. This slice should define the MCP server selection UX contract for the desktop app so operators can understand which MCP servers exist, what each server is allowed to do, which permission class or capability category it belongs to, what safety boundaries apply, and what explicit approvals are required before any MCP enablement becomes user-facing.

## Notes

- keep this slice bounded to the MCP server selection UX contract; do not jump into MCP runtime execution, RAG runtime, or concurrency work yet
- preserve the shipped ownership boundaries, approval semantics, desktop-app boundaries, and canonical-artifact-first model while defining the user-facing MCP selection surface
- do not widen into hidden orchestration, silent in-flight loop mutation, credential capture, actual MCP tool execution, RAG, policy-pack, packaging, or auto-update work
