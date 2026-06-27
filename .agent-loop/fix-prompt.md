# Claude Code Fix Task

## Objective
Fix only the current Claude-owned Phase 10L review issue found by Codex.

## Context
The latest Phase 10L implementation was reviewed by Codex and received the verdict `NEEDS_FIXES`.

Read:
- `CLAUDE.md`
- `.agent-loop/claude-prompt.md`
- `.agent-loop/codex-review.md`
- `ROADMAP.md`
- `docs/desktop-app-contract.md`
- `README.md`

## Required fixes
- Fix the later-phase routing mismatch in the Phase 10L desktop-app contract and README.
  The canonical roadmap now defines:
  - `Phase 10M` = `Desktop App Read-Only Runtime Initial Slice`
  - `Phase 10N` = `Desktop App Action Bridge Initial Slice`
  - controlled-concurrency work later at `Phase 10AB` / `10AC` / `10AD`
  But the current Phase 10L contract and README still describe `Phase 10N` as the bucket for controlled-concurrency, multi-target desktop sessions, and packaging work. Update the documentation so it points implementers at the correct next slices and no longer misstates what `10N` means.
- Keep the fix bounded to documentation/test alignment for Phase 10L.
  Do not add runtime code, new CLI surfaces, or new desktop behavior.
- Update focused documentation-consistency tests if needed so this roadmap alignment is pinned and cannot silently drift again.

## Constraints
- Fix only the listed issue.
- Do not redesign unrelated documentation.
- Do not expand the product scope.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not edit `.agent-loop/loop-state.json` or `.agent-loop/orchestrator.log` by hand.
- Do not delete files unless explicitly required and approved.
- Preserve the original Phase 10L objective.
- Prefer minimal, targeted changes.

## Required output
After applying fixes, update `.agent-loop/claude-summary.md` using the required Claude Implementation Summary format.
