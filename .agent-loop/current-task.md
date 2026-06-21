# Current Task

## Phase
Phase 10 - Future Product Features

## Sub-Phase
Phase 10B - External Target Attach Record Contract

## Status
Phase 10B is active as the next planning slice under Phase 10. The goal is to define the controller-owned attach-record contract for external-workspace mode: schema, path-canonicalization metadata, audit expectations, stale-attach detection inputs, and the minimum information later attach/detach runtime slices must persist without blurring controller-owned and target-owned state.

## Task
Define the External Target Attach Record Contract for the agent loop. This slice should specify the controller-owned attach-record schema, what target-selection metadata it must persist, how canonicalized target paths and controller identity are represented, what audit/refusal fields are required, and how later Phase 10 attach/detach runtime slices depend on that record.

## Notes

- keep this slice narrow: define the attach-record contract only; do not broaden into attach runtime, bootstrap runtime, or UI implementation
- preserve existing Phase 2A / 3A / 4A contracts unchanged
- `.agent-loop/claude-done.json` is a routing signal, not proof of correctness
- preserve the existing Phase 5E post-review reconciliation behavior and the Phase 5F phase-start prompt-bootstrap path unchanged
- repo artifacts must remain the source of truth over any documentation surface
- any capacity-halt retry, re-probe, or automatic-resume decision must originate from canonical repo artifacts rather than transient UI/chat state or a parallel control plane
- any future attach/detach decision must originate from explicit contract rules rather than transient UI/chat state or implicit path assumptions
- do not change the shipped `review`, `strict`, or bounded `autonomous` semantics
- keep future external attach/detach behavior aligned with the shipped halt/refusal vocabulary, checkpoint/resume behavior, ownership boundaries, and human approval requirements
