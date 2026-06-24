# Current Task

## Phase
Phase 10 - Future Product Features

## Sub-Phase
Phase 10H - Minimal External UI Read-Only Status Surface

## Status
Phase 10H is active as the next implementation slice under Phase 10. The goal is to build the first bounded read-only external UI surface for external-workspace mode: a thin viewer over approved canonical artifacts that preserves the shipped CLI-first workflow, advisory-vs-canonical rule, and safety/approval boundaries without yet adding mutating UI controls.

## Task
Implement the Minimal External UI Read-Only Status Surface for the agent loop. This slice should add a thin external UI that can select an attached target, read the approved controller-side and target-side canonical artifacts, render active phase/task/status and related read-only views, and preserve the 10G advisory-vs-canonical, CLI-only, and source-of-truth boundaries without yet adding run/resume controls or any canonical-artifact writes from the UI.

## Notes

- keep this slice narrow: implement only the bounded read-only UI surface; do not broaden into mutating UI controls, target-side dispatch, or broader workflow control
- preserve existing Phase 2A / 3A / 4A contracts unchanged
- `.agent-loop/claude-done.json` is a routing signal, not proof of correctness
- preserve the existing Phase 5E post-review reconciliation behavior and the Phase 5F phase-start prompt-bootstrap path unchanged
- repo artifacts must remain the source of truth over any documentation surface
- any capacity-halt retry, re-probe, or automatic-resume decision must originate from canonical repo artifacts rather than transient UI/chat state or a parallel control plane
- any future bootstrap or target-dispatch decision must originate from explicit contract rules rather than transient UI/chat state or implicit path assumptions
- stale or inconsistent external-target state must refuse fail-closed rather than being silently repaired or inferred
- any UI runtime in this slice must remain advisory over canonical repo artifacts and must not gain a write path
- do not change the shipped `review`, `strict`, or bounded `autonomous` semantics
- keep future external attach/detach behavior aligned with the shipped halt/refusal vocabulary, checkpoint/resume behavior, ownership boundaries, and human approval requirements
