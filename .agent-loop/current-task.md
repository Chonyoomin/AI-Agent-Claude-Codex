# Current Task

## Phase
Fix Phase B - Desktop Empty-Target Bootstrap Flow

## Sub-Phase
Fix Phase B3 - Desktop Bootstrap Dispatch And Post-Bootstrap Handoff

## Status
Fix Phase B2 is complete and approved to advance. Fix Phase B3 is now active
as the next remediation slice focused on wiring the validated desktop bootstrap
flow into the shipped bootstrap runtime and surfacing a clear post-bootstrap
handoff without weakening controller-vs-target boundaries.

## Task
Implement Fix Phase B3 for the agent loop. This slice should wire the validated
desktop bootstrap form into the shipped `attach-external-target --bootstrap`
runtime path, refresh the attached-target view after success, and surface the
first explicit post-bootstrap next-step guidance without introducing a second
bootstrap runtime or hidden desktop-only state plane.

## Notes

- keep this slice focused on bounded bootstrap dispatch and post-bootstrap
  handoff; do not widen into first-phase activation or hidden desktop
  automation beyond the shipped runtime call
- preserve the shipped operator-input rule: no hidden defaults for
  `attached_by`, `bootstrapped_by`, `human_objective`, or `project_intent`
- preserve the shipped empty/full/partial/malformed target vocabulary and
  refusal boundaries instead of inventing a second UI-only state plane
