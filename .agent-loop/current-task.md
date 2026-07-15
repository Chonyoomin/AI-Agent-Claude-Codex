# Current Task

## Phase
Phase 10 - Future Product Features

## Sub-Phase
Phase 10AG - Desktop Codex Conversation Surface Initial Slice

## Status
Active and ready for implementation.

## Task
Implement the first bounded desktop-side Codex interaction surface so the
operator can compose an in-app Codex request, inspect Codex response mirrors,
and route approved Codex-owned actions through the shipped adapter/artifact
model instead of separate chat windows.

## Notes

- this is the first runtime slice for the desktop Codex conversation surface
- the shipped desktop app must remain canonical-artifact-first; this phase must
  not invent a hidden UI-only request/reply state plane
- preserve the Phase 10AF closed intent vocabulary, refusal vocabulary, audit
  expectations, and adapter routing rules
