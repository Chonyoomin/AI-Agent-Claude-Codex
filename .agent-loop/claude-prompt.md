# Claude Code Task

## Phase
Phase 10AF - Desktop Codex Conversation And Intervention Contract

## Objective
Define the bounded contract for an in-app desktop surface that lets the
operator communicate with Codex for reviews, fix routing, roadmap changes, and
targeted repo changes without bypassing canonical artifacts, ownership rules,
review evidence, or shipped approval/audit boundaries.

## Context
`Phase 10AF` is now the active mainline slice. The repo already ships a
desktop app shell, action bridges, artifact/status dashboards, MCP/RAG
selection surfaces, controlled-concurrency rules, overlap-safe detection, and
a bounded Codex-owned concurrent-work slice. What does NOT yet exist is the
contract for how the desktop app should expose an operator-to-Codex request
surface without inventing a hidden second control plane.

This phase is contract-definition first. It should establish the request
types, artifact routing, safety boundaries, canonical-vs-advisory state rules,
approval boundaries, refusal cases, and desktop-surface expectations for a
future implementation slice (`Phase 10AG`).

Work against the actual repo state. Do not rely on prior chat context.

## Required work
- add the bounded `Phase 10AF` contract artifact(s) for desktop Codex
  conversation and intervention
- define which operator intents are in scope, such as:
  - ask Codex for a review
  - ask Codex to classify issues by owner
  - ask Codex to update roadmap/planning artifacts
  - ask Codex for targeted Codex-owned repo changes
- define how desktop-side requests map back to canonical artifacts rather than
  becoming a hidden UI-only request/reply store
- define how the surface distinguishes:
  - advisory request composition
  - canonical artifact mutation
  - Claude-owned follow-up versus Codex-owned follow-up
- define the safety, refusal, approval, and audit boundaries the future runtime
  must preserve
- add or update focused tests covering README/doc consistency for the new
  contract
- update `README.md` if the documented current implementation focus changes

## Constraints
- Follow `CLAUDE.md`.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Keep this slice contract-only unless a tiny bounded runtime helper is
  necessary for testable documentation alignment.
- Do not implement the actual desktop chat/runtime panel that belongs to
  `Phase 10AG`.
- Do not create a hidden UI-only request queue, reply cache, or operator state
  plane outside canonical artifacts.
- Do not weaken ownership boundaries, evidence review, approval gating,
  overlap-safe rules, or canonical-artifact-first behavior.

## Important guardrails
- Codex conversation from the desktop app must remain a routing surface over
  the shipped artifact model, not a separate autonomous orchestrator.
- Any operator request that would change canonical artifacts must still route
  through the same explicit ownership model already used elsewhere in the repo.
- Claude-owned implementation work must still become a prompt/fix-prompt style
  handoff rather than a direct hidden desktop-side mutation.
- Future desktop responses may be advisory mirrors, but the contract must make
  clear which artifacts remain canonical.

## Likely files
- `README.md`
- `docs/` new contract file(s)
- `tests/test_documentation_consistency.py`
- any desktop-contract consistency tests already present in the repo

## Required output
After implementation, write `.agent-loop/claude-summary.md` using the required
Claude Implementation Summary format and include the validation you ran.
