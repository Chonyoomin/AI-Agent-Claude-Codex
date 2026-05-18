#!/usr/bin/env bash
# scripts/run_checks.sh
#
# Phase 2B implementation of the Evidence Collection Contract defined in
# .agent-loop/phase-plan.md under "## Phase 2A - Evidence Collection Contract".
# Implements the contract; does not extend it.
#
# Captures:
#   .agent-loop/git-status.log   - always
#   .agent-loop/git-diff.patch   - always (git diff HEAD, text diffs only)
#   .agent-loop/test-output.log
#   .agent-loop/lint-output.log
#   .agent-loop/typecheck-output.log
#   .agent-loop/build-output.log
#
# Validation command discovery (highest precedence first):
#   1. env vars: AGENT_LOOP_{TEST,LINT,TYPECHECK,BUILD}_CMD
#   2. .agent-loop/checks.json: {"test": "...", "lint": null, ...}
#
# State vocabulary (per contract):
#   Passed | Failed | Not run | Inconclusive
#
# Exit code: 0 iff every command's state is Passed or Not run.

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

EVIDENCE_DIR=".agent-loop"
CHECKS_JSON="$EVIDENCE_DIR/checks.json"

mkdir -p "$EVIDENCE_DIR"

ANY_NON_PASS=0

iso_utc_now() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

# Read a string value for KEY from CHECKS_JSON via python3.
# stdout: the string value if present and non-null; empty otherwise.
# return: 0 on success or "key missing/null", 2 if python3 unavailable,
#         3 if checks.json present but unparseable.
read_check_value() {
  local key="$1"
  if ! command -v python3 >/dev/null 2>&1; then
    return 2
  fi
  python3 - "$CHECKS_JSON" "$key" <<'PY'
import json, sys
path, key = sys.argv[1], sys.argv[2]
try:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
except Exception:
    sys.exit(3)
val = data.get(key)
if val is None or val == "":
    sys.exit(0)
print(val)
PY
}

# Write a single contract-format header to FILE (truncating it).
# Args: file logical captured_at command exit_code state reason
write_header() {
  local file="$1" logical="$2" captured_at="$3" cmd="$4"
  local exit_code="$5" state="$6" reason="$7"
  {
    printf '# %s\n' "$logical"
    printf 'captured_at: %s\n' "$captured_at"
    printf 'command: %s\n' "$cmd"
    printf 'exit_code: %s\n' "$exit_code"
    printf 'state: %s\n' "$state"
    if [ -n "$reason" ]; then
      printf 'reason: %s\n' "$reason"
    fi
    printf -- '----\n'
  } > "$file"
}

# Translate an exit code to (state, reason) per the contract.
# Sets globals STATE and REASON.
classify_exit() {
  local rc="$1"
  if [ "$rc" -eq 0 ]; then
    STATE="Passed"
    REASON=""
  elif [ "$rc" -eq 127 ]; then
    STATE="Failed"
    REASON="command not found"
  elif [ "$rc" -ge 128 ] && [ "$rc" -le 192 ]; then
    # Conventionally 128+signum when terminated by a signal.
    STATE="Inconclusive"
    REASON="killed by signal $((rc - 128))"
  else
    STATE="Failed"
    REASON="non-zero exit"
  fi
}

capture_git() {
  local logical="$1" cmd_str="$2" file="$3"
  local captured_at
  captured_at="$(iso_utc_now)"
  local tmp
  tmp="$(mktemp)"
  # shellcheck disable=SC2086
  $cmd_str > "$tmp" 2>&1
  local rc=$?
  classify_exit "$rc"
  write_header "$file" "$logical" "$captured_at" "$cmd_str" "$rc" "$STATE" "$REASON"
  cat "$tmp" >> "$file"
  rm -f "$tmp"
  if [ "$STATE" != "Passed" ] && [ "$STATE" != "Not run" ]; then
    ANY_NON_PASS=1
  fi
}

run_validation() {
  local logical="$1" env_var="$2"
  local file="$EVIDENCE_DIR/${logical}-output.log"
  local captured_at
  captured_at="$(iso_utc_now)"

  local resolved_cmd=""
  local env_val="${!env_var-}"
  if [ -n "$env_val" ]; then
    resolved_cmd="$env_val"
  elif [ -f "$CHECKS_JSON" ]; then
    local from_file
    from_file="$(read_check_value "$logical")"
    local rc=$?
    if [ "$rc" -eq 2 ]; then
      write_header "$file" "$logical" "$captured_at" "(not configured)" "n/a" \
        "Failed" "checks.json present but no JSON parser available (need python3)"
      ANY_NON_PASS=1
      return
    elif [ "$rc" -eq 3 ]; then
      write_header "$file" "$logical" "$captured_at" "(not configured)" "n/a" \
        "Failed" "checks.json present but could not be parsed as JSON"
      ANY_NON_PASS=1
      return
    fi
    resolved_cmd="$from_file"
  fi

  if [ -z "$resolved_cmd" ]; then
    write_header "$file" "$logical" "$captured_at" "(not configured)" "n/a" \
      "Not run" "no $env_var env var and no '$logical' key in $CHECKS_JSON"
    return
  fi

  local tmp
  tmp="$(mktemp)"
  bash -c "$resolved_cmd" > "$tmp" 2>&1
  local rc=$?
  classify_exit "$rc"

  write_header "$file" "$logical" "$captured_at" "$resolved_cmd" "$rc" "$STATE" "$REASON"
  cat "$tmp" >> "$file"
  rm -f "$tmp"

  if [ "$STATE" != "Passed" ] && [ "$STATE" != "Not run" ]; then
    ANY_NON_PASS=1
  fi
}

capture_git "git status" "git status" "$EVIDENCE_DIR/git-status.log"
capture_git "git diff (working tree vs HEAD)" "git diff HEAD" "$EVIDENCE_DIR/git-diff.patch"

run_validation test      AGENT_LOOP_TEST_CMD
run_validation lint      AGENT_LOOP_LINT_CMD
run_validation typecheck AGENT_LOOP_TYPECHECK_CMD
run_validation build     AGENT_LOOP_BUILD_CMD

if [ "$ANY_NON_PASS" -ne 0 ]; then
  exit 1
fi
exit 0
