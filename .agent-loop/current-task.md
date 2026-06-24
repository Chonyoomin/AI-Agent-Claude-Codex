# Current Task

## Phase
Fix Phases - Targeted Remediation Track

## Sub-Phase
Fix Phase A - Automatic Local Claude/Codex Invocation Reliability

## Status
Fix Phase A is active as a targeted remediation slice. The goal is to make the shipped Claude/Codex adapter seams reliable for real local automatic invocation: define the adapter contract, support wrapper execution, and prove the existing intra-phase loop can run without manual prompt transfer when both local commands are configured correctly.

## Task
Implement Fix Phase A for the agent loop. This slice should define and validate the real local adapter contract for `AGENT_LOOP_CLAUDE_CMD` and `AGENT_LOOP_CODEX_CMD`, provide first-party wrapper support or templates for invoking both CLIs automatically, and prove that the shipped intra-phase loop can run without manual prompt transfer when those adapter commands are configured correctly.

## Notes

- keep this slice narrow: implement only the local automatic invocation reliability work; do not broaden into fully autonomous PRD execution or unrelated roadmap features
- preserve existing Phase 2A / 3A / 4A contracts unchanged
- `.agent-loop/claude-done.json` is a routing signal, not proof of correctness
- preserve the existing Phase 5E post-review reconciliation behavior and the Phase 5F phase-start prompt-bootstrap path unchanged
- repo artifacts must remain the source of truth over any documentation surface
- automatic invocation must still fail closed when adapters do not produce fresh canonical artifacts
- do not claim that local automatic adapter execution equals fully autonomous phase-to-phase PRD completion
- do not change the shipped `review`, `strict`, or bounded `autonomous` semantics
- keep future autonomy work aligned with the shipped halt/refusal vocabulary, checkpoint/resume behavior, ownership boundaries, and human approval requirements
