#!/usr/bin/env bash
# Verify the RED agent charters SPEC.md section 5 requires exist and each carries
# the operating-contract sections. Called by scripts/check_definition_of_done.sh
# [5/6] as part of DoD condition 8 (RED branding and retained notices).
#
# SPEC.md section 5: "Every agent has a versioned charter, allowed tools, input
# schema, output schema, context budget, evidence policy, quality rubric,
# escalation rules, and budget limit." docs/agents/ held only the two capability
# slots, so condition 8's "agent charters are RED" evidence was incomplete. The
# check is data-driven: docs/agents/agent-charters.txt declares each required
# charter as "<slot> <file>"; every listed file must exist and contain each
# required section heading, so a future cycle adds a charter without editing this
# script.
#
# Usage: check_agent_charters.sh <agents-dir>
set -Eeuo pipefail

agents_dir="${1:?agents directory required}"

fail() { printf 'agent charters: %s\n' "$*" >&2; exit 1; }

[[ -d "$agents_dir" ]] || fail \
  "docs/agents/ is missing; SPEC.md section 5 requires agent charters"

manifest="$agents_dir/agent-charters.txt"
[[ -f "$manifest" ]] || fail \
  "missing $manifest; declare each charter as '<slot> <file>'"

# The section 5 operating contract every charter must state.
required_sections=(
  "## Mission"
  "## Responsibilities"
  "## Allowed tools"
  "## Inputs"
  "## Outputs"
  "## Evidence policy"
  "## Context budget"
  "## Quality rubric"
  "## Escalation rules"
  "## Budget limit"
)

declare -A slot_seen
count=0
while read -r slot file _; do
  [[ -z "${slot:-}" || "$slot" == \#* ]] && continue
  [[ -n "${file:-}" ]] || fail "manifest line for slot '$slot' needs a charter file"
  [[ -z "${slot_seen[$slot]:-}" ]] || fail "duplicate slot '$slot' in agent-charters.txt"
  slot_seen["$slot"]=1
  path="$agents_dir/$file"
  [[ -f "$path" ]] || fail "declared charter for slot $slot is missing: $file"
  for section in "${required_sections[@]}"; do
    grep -qF "$section" "$path" \
      || fail "charter $file is missing required section '$section'"
  done
  count=$((count + 1))
done < "$manifest"

(( count > 0 )) || fail "agent-charters.txt declares no charters"

printf 'agent charters ok: %d chartered agents with the section 5 contract\n' "$count"
