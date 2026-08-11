# Claude Code Fix Task

## Phase
Fix Phase C2 - Project Folder Picker And Classification Surface

## Claude-owned fixes

### Issue 1 - Remove the duplicate default folder flow
The C2 Project section is not the only visible folder-selection path. The
legacy `Select Project Folder` control remains packed in the default control
column and its callback exposes raw `full_target` and CLI guidance. Retire or
move that legacy path behind the existing Advanced/details surface so the C2
Project section is the single default folder flow and all default copy remains
plain English.

### Issue 2 - Audit picker cancellation
The C2 folder-picker callback returns without writing an audit line when the
operator cancels the native picker. The C1 contract requires every first-run
operator gesture to be auditable through `.agent-loop/orchestrator.log`.
Add a dedicated closed C2 cancellation category such as
cancelled_folder_picker to the C2 audit vocabulary. Emit the bounded C2
audit line with that category and the current signal version whenever the
operator cancels the picker. Preserve the current classification/folder
payload exactly; cancellation must not clear it, trigger classification, or
dispatch any attach/bootstrap/run action. Add regression coverage that proves
the cancellation audit line is written, uses the closed category, and leaves
the current payload unchanged. Update any C2 vocabulary documentation or
consistency tests needed to keep the category closed and auditable.

Do not modify Codex-owned planning artifacts. After fixing, update
`.agent-loop/claude-summary.md` with the changes and validation performed.
