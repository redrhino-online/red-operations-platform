#!/usr/bin/env bash

# RED Operations Platform: exactly one OpenCode implementation cycle.
# Usage: ./ralph_cycle.sh [repository-directory]
# The target repository (arg 1, default: the script directory) is where OpenCode
# works. The spec and plan come from RALPH_SPEC / RALPH_PLAN (default: the script
# directory). When the target repository differs from the spec/plan repository,
# the cycle commits code in the target and spec/plan changes in their own repo.
# Optional environment: RALPH_SPEC, RALPH_PLAN, RALPH_CANON, RALPH_OPENCODE,
# RALPH_MODEL, RALPH_SESSION_ID, RALPH_PUSH_REMOTES, RALPH_PLAN_PUSH_REMOTES,
# RALPH_DB_PREFLIGHT, RALPH_DB_WAIT, RALPH_DB_PROBE_TIMEOUT, RALPH_SNAPSHOT,
# RALPH_OPENCODE_CONFIG.

set -Eeuo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
readonly REPO_DIR="$(cd "${1:-$SCRIPT_DIR}" && pwd -P)"
readonly SPEC_FILE="${RALPH_SPEC:-$SCRIPT_DIR/SPEC.md}"
readonly PLAN_FILE="${RALPH_PLAN:-$SCRIPT_DIR/IMPLEMENTATION_PLAN.md}"
readonly CANON_DIR="${RALPH_CANON:-$(cd "$SCRIPT_DIR/.." && pwd -P)/canon}"
readonly OPENCODE_BIN="${RALPH_OPENCODE:-opencode}"
# Space-separated remote names to publish to. Each is skipped when the
# repository does not have that remote configured. Never pushes to `upstream`.
# Default is origin only; `make loop` asks for `origin atlas` on its final cycle.
readonly PUSH_REMOTES="${RALPH_PUSH_REMOTES-${RALPH_PUSH_REMOTE-origin}}"
readonly PLAN_PUSH_REMOTES="${RALPH_PLAN_PUSH_REMOTES-$PUSH_REMOTES}"

# Local development database. The docker-compose postgres service exposes this
# URL; exporting it keeps the persistence adapter and migration tests running
# instead of skipping. An explicit environment value wins; a local .env is
# loaded first when present. See .env.example.
if [[ -f "$SCRIPT_DIR/.env" ]]; then
  set -a; . "$SCRIPT_DIR/.env"; set +a
fi
: "${DATABASE_URL:=postgresql://redops:redops@localhost:5432/redops}"
export DATABASE_URL

readonly RUN_DIR="$REPO_DIR/.ralph"
readonly LOCK_DIR="$RUN_DIR/cycle.lock"

die() { printf 'ralph: %s\n' "$*" >&2; exit 1; }
release_lock() { rm -rf "$LOCK_DIR"; }

# A single static OpenCode session per project: every cycle continues the same
# session so the OpenRouter call carries one stable session id across the whole
# run (request affinity/caching and one continuous run history) instead of a new
# session per cycle. RALPH_SESSION_ID overrides; otherwise the id is created once
# with a minimal run and persisted in .ralph/session-id. Creation is best effort:
# on failure the cycle proceeds without --session and tries again next time.
project_session_exists() {
  "$OPENCODE_BIN" session list 2>/dev/null | awk '{print $1}' | grep -qx "$1"
}

create_project_session() {
  local args=(run --format json) out
  if [[ -n "${RALPH_MODEL:-}" ]]; then
    args+=(--model "$RALPH_MODEL")
  fi
  args+=("Reply with exactly: OK")
  out="$("$OPENCODE_BIN" "${args[@]}" 2>/dev/null || true)"
  printf '%s' "$out" | grep -o '"sessionID":"[^"]*"' | head -n1 | cut -d'"' -f4 || true
}

# Acquire the single-cycle lock. A lock whose recorded pid is gone (a hard kill,
# host restart or OOM) is reclaimed instead of wedging the loop. A lock with no
# pid younger than the grace period is treated as an acquisition in progress.
acquire_lock() {
  local grace="${RALPH_LOCK_GRACE:-120}" owner started age now
  while true; do
    if mkdir "$LOCK_DIR" 2>/dev/null; then
      printf '%s\n' "$$" > "$LOCK_DIR/pid"
      printf '%s\n' "$(date -u +%FT%TZ)" > "$LOCK_DIR/started"
      return 0
    fi
    owner=""
    [[ -f "$LOCK_DIR/pid" ]] && owner="$(cat "$LOCK_DIR/pid" 2>/dev/null || true)"
    if [[ -n "$owner" ]] && kill -0 "$owner" 2>/dev/null; then
      die "another cycle is active (pid $owner); if that process is gone, remove $LOCK_DIR"
    fi
    now="$(date +%s)"
    started="$(stat -c %Y "$LOCK_DIR" 2>/dev/null || printf '%s' "$now")"
    age=$(( now - started ))
    if [[ -z "$owner" && "$age" -lt "$grace" ]]; then
      die "another cycle may be starting (lock age ${age}s); remove $LOCK_DIR if the process is gone"
    fi
    printf 'ralph: reclaiming stale lock at %s (owner %s not running, age %ss)\n' \
      "$LOCK_DIR" "${owner:-unknown}" "$age" >&2
    rm -rf "$LOCK_DIR"
  done
}

push_to_remotes() { # $1=repo $2=branch $3=space-separated remote names
  local repo="$1" branch="$2" remotes="$3" remote pushed=0
  for remote in $remotes; do
    git -C "$repo" remote get-url "$remote" >/dev/null 2>&1 || continue
    git -C "$repo" push "$remote" "HEAD:refs/heads/$branch" \
      || die "failed to publish $branch to remote $remote in $repo"
    printf 'ralph: published %s to %s (%s)\n' "$branch" "$remote" "$repo"
    pushed=1
  done
  (( pushed )) || printf 'ralph: no publish remote among [%s] configured in %s; skipping publish\n' "$remotes" "$repo"
}

[[ -d "$REPO_DIR" ]] || die "repository directory does not exist: $REPO_DIR"
[[ -f "$SPEC_FILE" && -r "$SPEC_FILE" ]] || die "spec is missing or unreadable: $SPEC_FILE"
[[ -f "$PLAN_FILE" && -r "$PLAN_FILE" && -w "$PLAN_FILE" ]] || die "plan must be readable and writable: $PLAN_FILE"
command -v "$OPENCODE_BIN" >/dev/null 2>&1 || die "OpenCode CLI is unavailable: $OPENCODE_BIN"

# Cooperative stop: `touch .ralph/STOP` in the target repository halts a loop
# before this cycle starts. Exit status 3 means "stopped cleanly", so the loop
# driver breaks instead of treating it as a failure. The file is not removed.
# The database preflight below also writes this file when it cannot reach the
# database, so a wedged database stops the loop instead of hanging it.
if [[ -e "$RUN_DIR/STOP" ]]; then
  printf 'ralph: STOP present at %s; not starting a cycle\n' "$RUN_DIR/STOP" >&2
  exit 3
fi
# Success stop: the loop reaches its definition of done (SPEC.md section 13) when
# `make done` passes. The agent touches .ralph/DONE; the loop then halts cleanly.
if [[ -e "$RUN_DIR/DONE" ]]; then
  printf 'ralph: DONE present at %s; definition of done reached\n' "$RUN_DIR/DONE" >&2
  exit 3
fi

# A repository is required so the agent can inspect changes and the operator can review them.
git -C "$REPO_DIR" rev-parse --show-toplevel >/dev/null 2>&1 || die "target must be a git repository"
mkdir -p "$RUN_DIR"

# Database preflight. `make check` runs the Postgres-backed persistence and
# migration tests. When the local database is down, psycopg's connect hangs
# (WSL drops the SYN instead of refusing), so the cycle wedges with no log
# output. Verify the endpoint before the agent runs, start the compose service
# when it is local and available, and, if it still cannot be reached, leave a
# STOP file so the loop halts cleanly for a human instead of hanging. Disable
# with RALPH_DB_PREFLIGHT=0.
if [[ "${RALPH_DB_PREFLIGHT:-1}" == "1" ]]; then
  db_url="${DATABASE_URL:-}"
  db_rest="${db_url#*://}"
  db_hostport="${db_rest##*@}"
  db_hostport="${db_hostport%%/*}"
  db_host="${db_hostport%%:*}"
  db_port="${db_hostport##*:}"
  [[ -z "$db_port" || "$db_port" == "$db_host" ]] && db_port=5432
  [[ -n "$db_host" ]] || db_host=localhost

  db_reachable() {
    timeout "${RALPH_DB_PROBE_TIMEOUT:-3}" \
      bash -c "exec 3<>/dev/tcp/$db_host/$db_port" 2>/dev/null
  }

  if ! db_reachable; then
    case "$db_host" in
      localhost|127.0.0.1|::1) db_local=1 ;;
      *) db_local=0 ;;
    esac
    if (( db_local )) && command -v docker >/dev/null 2>&1 \
       && [[ -f "$SCRIPT_DIR/docker-compose.yml" ]]; then
      printf 'ralph: database %s:%s unreachable; starting compose postgres\n' \
        "$db_host" "$db_port" >&2
      docker compose -f "$SCRIPT_DIR/docker-compose.yml" up -d postgres >&2 || true
      deadline=$(( $(date +%s) + ${RALPH_DB_WAIT:-60} ))
      while ! db_reachable; do
        if (( $(date +%s) >= deadline )); then break; fi
        sleep 2
      done
    fi
  fi

  if ! db_reachable; then
    {
      printf 'Database preflight failed: %s:%s is not reachable.\n' "$db_host" "$db_port"
      printf 'DATABASE_URL=%s\n' "$DATABASE_URL"
      printf '\n'
      printf 'make check runs the Postgres-backed tests; with the database down the\n'
      printf 'connection hangs instead of failing, so the cycle would wedge.\n'
      printf '\n'
      printf 'Fix: start the database (docker compose up -d postgres), then remove\n'
      printf 'this file to let the loop resume.\n'
      printf '\n'
      printf 'Written %s by ralph_cycle.sh (pid %s).\n' "$(date -u +%FT%TZ)" "$$"
    } > "$RUN_DIR/STOP"
    printf 'ralph: database preflight failed; wrote %s and stopping cleanly\n' \
      "$RUN_DIR/STOP" >&2
    exit 3
  fi
  printf 'ralph: database preflight ok (%s:%s)\n' "$db_host" "$db_port" >&2
fi

# Keep the harness's own run directory out of commits without relying on the
# target repository's .gitignore. Adding an ignored path as an explicit git
# pathspec makes `git add` fail, so we register the exclusion in the repo-local
# exclude file and then stage with a plain `.` pathspec.
GIT_EXCLUDE_FILE="$(git -C "$REPO_DIR" rev-parse --git-path info/exclude)"
mkdir -p "$(dirname "$GIT_EXCLUDE_FILE")"
for excluded in '.ralph/' '.serena/'; do
  grep -qxF "$excluded" "$GIT_EXCLUDE_FILE" 2>/dev/null || printf '%s\n' "$excluded" >> "$GIT_EXCLUDE_FILE"
done
if [[ "${RALPH_PROMPT_TEST:-0}" != "1" ]]; then
  acquire_lock
  trap release_lock EXIT
fi

readonly RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$$"
readonly LOG_FILE="$RUN_DIR/$RUN_ID.log"
readonly COMMIT_MSG_FILE="$RUN_DIR/$RUN_ID.commit-msg.txt"
readonly SESSION_FILE="$RUN_DIR/session-id"
readonly SPEC_PATH="$(cd "$(dirname "$SPEC_FILE")" && pwd -P)/$(basename "$SPEC_FILE")"
readonly PLAN_PATH="$(cd "$(dirname "$PLAN_FILE")" && pwd -P)/$(basename "$PLAN_FILE")"

# When the target is a git submodule (e.g. vendor/openexecutive), the spec and
# plan live in the superproject. Run OpenCode from the superproject so the spec,
# plan and submodule are all in-project, and after committing inside the
# submodule commit the spec/plan and the moved submodule pointer in the
# superproject. SUPER_ROOT is empty for an ordinary single-repository target.
SUPER_ROOT="$(git -C "$REPO_DIR" rev-parse --show-superproject-working-tree 2>/dev/null || true)"
RUN_CWD="${RALPH_RUN_CWD:-${SUPER_ROOT:-$REPO_DIR}}"
if [[ -n "$SUPER_ROOT" ]]; then
  SUPER_EXCLUDE="$(git -C "$SUPER_ROOT" rev-parse --git-path info/exclude)"
  mkdir -p "$(dirname "$SUPER_EXCLUDE")"
  for excluded in '.ralph/' '.serena/'; do
    grep -qxF "$excluded" "$SUPER_EXCLUDE" 2>/dev/null || printf '%s\n' "$excluded" >> "$SUPER_EXCLUDE"
  done
fi

# The reference model canon is the licensed source reference for method
# artifacts. It lives outside the repository, so point the agent at it only when
# it is actually present and never require it for a cycle to run.
CANON_PATH=""
CANON_REFERENCE="Canon (reference model materials): not available in this environment; proceed from the spec and plan only and do not invent method content."
if [[ -d "$CANON_DIR" ]]; then
  CANON_PATH="$(cd "$CANON_DIR" && pwd -P)"
  CANON_HASH="$("$SCRIPT_DIR/scripts/canon_hash.sh" "$CANON_PATH" 2>/dev/null || true)"
  CANON_LOCK="${RALPH_CANON_LOCK:-$SCRIPT_DIR/canon.lock}"
  if [[ -n "$CANON_HASH" ]]; then
    if [[ -f "$CANON_LOCK" ]]; then
      pinned="$(awk 'NR==1{print $1}' "$CANON_LOCK")"
      if [[ "$pinned" != "$CANON_HASH" ]]; then
        if [[ "${RALPH_CANON_STRICT:-1}" == "1" ]]; then
          printf 'ralph: CANON DRIFT: canon content changed (pinned %s, now %s); re-pin with make canon-pin, or set RALPH_CANON_STRICT=0 to override (exit 4)\n' "$pinned" "$CANON_HASH" >&2
          exit 4
        fi
        printf 'ralph: WARNING canon content changed (pinned %s, now %s) and RALPH_CANON_STRICT=0\n' "$pinned" "$CANON_HASH" >&2
      fi
    else
      printf '%s %s\n' "$CANON_HASH" "$(date -u +%FT%TZ)" > "$CANON_LOCK"
      printf 'ralph: pinned canon content %s to %s\n' "$CANON_HASH" "$CANON_LOCK" >&2
    fi
    CANON_REFERENCE="Canon (reference model materials; the RED Method is its licensed implementation): $CANON_PATH (content sha256 $CANON_HASH; pinned in canon.lock)"
  else
    CANON_REFERENCE="Canon (reference model materials; the RED Method is its licensed implementation): $CANON_PATH"
  fi
else
  printf 'ralph: canon reference directory not found at %s; proceeding without it\n' "$CANON_DIR" >&2
fi

"$SCRIPT_DIR/scripts/ralph_state.sh" prepare "$RUN_CWD"

read -r -d '' PROMPT <<'EOF' || true
One Ralph cycle. One bounded item. Repo: @REPO_DIR@. Cycle: @RUN_ID@.

Stable-first context order:
1. Read @SPEC_PATH@ once, fully.
2. Read Serena memories `definition-of-done-gate` and `atlas-deploy`.
3. Read generated @STATE_PATH@ for queue, dependencies, blockers and next item.
4. Read only selected plan rows in @PLAN_PATH@. Read cited canon source only.
5. Last, inspect `git status`, `git log -5` and latest Ralph log.

Pick highest-value ready item; state why it beats alternatives. Do only that item.
For new behavior, failing test first; smallest passing change; then refactor.
Run smallest meaningful checks. Update current plan entry and record evidence,
blockers and next ready item. Keep two newest cycle entries; harness archives
the rest to `docs/plan-history.md`. Write commit message to @COMMIT_MSG_FILE@.
If `make done` passes, touch `.ralph/DONE`. If no ready work remains, record
blocker and touch `.ralph/DONE`. Stop; harness commits and publishes.

Canon: @CANON_REFERENCE@
Final response: selected item, changed files, checks/results, plan update, next
ready item or blocker. Be brief and accurate.
EOF

PROMPT="${PROMPT//@REPO_DIR@/$REPO_DIR}"
PROMPT="${PROMPT//@RUN_ID@/$RUN_ID}"
PROMPT="${PROMPT//@SPEC_PATH@/$SPEC_PATH}"
PROMPT="${PROMPT//@PLAN_PATH@/$PLAN_PATH}"
PROMPT="${PROMPT//@STATE_PATH@/$RUN_CWD/.ralph/STATE.md}"
PROMPT="${PROMPT//@CANON_REFERENCE@/$CANON_REFERENCE}"
PROMPT="${PROMPT//@COMMIT_MSG_FILE@/$COMMIT_MSG_FILE}"

# Use per-cycle config: no snapshots, project-only rules and larger context
# preservation. The file is an additional config layer; global model/MCP remain.
RALPH_OPENCODE_CONFIG="${RALPH_OPENCODE_CONFIG:-$RUN_DIR/opencode.json}"
python3 - "$RALPH_OPENCODE_CONFIG" "$SCRIPT_DIR/.opencode/instructions/ralph.md" "${RALPH_SNAPSHOT:-0}" <<'PY'
import json, pathlib, sys
path, instructions, snapshot = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3] == "1"
path.parent.mkdir(parents=True, exist_ok=True)
config = {
    "$schema": "https://opencode.ai/config.json",
    "snapshot": snapshot,
    "instructions": [str(pathlib.Path(instructions).resolve())],
    "compaction": {
        "auto": True,
        "prune": True,
        "tail_turns": 20,
        "preserve_recent_tokens": 80000,
    },
}
path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
PY
export OPENCODE_CONFIG="$RALPH_OPENCODE_CONFIG"

# Prompt-only mode keeps regression tests from invoking OpenCode.
if [[ "${RALPH_PROMPT_TEST:-0}" == "1" ]]; then
  printf '%s' "$PROMPT"
  exit 0
fi

printf 'ralph: starting one cycle; log: %s\n' "$LOG_FILE"
cd "$RUN_CWD"

# Resolve the static project session (see project_session_* above). An explicit
# RALPH_SESSION_ID wins; otherwise the persisted id is reused, recreated when it
# no longer exists, and created once when absent.
session_id="${RALPH_SESSION_ID:-}"
session_from_env=0
[[ -n "$session_id" ]] && session_from_env=1
if [[ -z "$session_id" && -s "$SESSION_FILE" ]]; then
  session_id="$(head -n1 "$SESSION_FILE")"
fi
if [[ -n "$session_id" ]] && ! project_session_exists "$session_id"; then
  if (( session_from_env )); then
    printf 'ralph: RALPH_SESSION_ID %s does not exist; continuing without --session\n' "$session_id" >&2
  else
    printf 'ralph: project session %s no longer exists; recreating\n' "$session_id" >&2
  fi
  session_id=""
fi
if [[ -z "$session_id" && "$session_from_env" == "0" ]]; then
  session_id="$(create_project_session || true)"
  if [[ -n "$session_id" ]]; then
    printf '%s\n' "$session_id" > "$SESSION_FILE"
    printf 'ralph: created static project session %s\n' "$session_id"
  else
    printf 'ralph: could not create a project session; continuing without --session\n' >&2
  fi
fi

opencode_args=(run)
if [[ -n "${RALPH_MODEL:-}" ]]; then
  opencode_args+=(--model "$RALPH_MODEL")
fi
if [[ -n "$session_id" ]]; then
  opencode_args+=(--session "$session_id")
fi
opencode_args+=("$PROMPT")

set +e
"$OPENCODE_BIN" "${opencode_args[@]}" 2>&1 | tee "$LOG_FILE"
run_status=${PIPESTATUS[0]}
set -e
if (( run_status != 0 )); then
  printf 'ralph: OpenCode failed with status %s; inspect %s\n' "$run_status" "$LOG_FILE" >&2
  exit "$run_status"
fi

"$SCRIPT_DIR/scripts/ralph_state.sh" finish "$RUN_CWD"

# Commit the cycle's changes so every loop produces an auditable checkpoint.
if [[ -n "$(git -C "$REPO_DIR" status --porcelain --untracked-files=all -- .)" ]]; then
  [[ -s "$COMMIT_MSG_FILE" ]] || die "agent did not write a commit message to $COMMIT_MSG_FILE; refusing to commit without the why"
  commit_subject="$(sed -n '1p' "$COMMIT_MSG_FILE")"
  cc_re='^(build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test)(\([^)]+\))?!?:[[:space:]].+'
  if [[ ! "$commit_subject" =~ $cc_re ]]; then
    die "commit subject is not Conventional Commits style: $commit_subject"
  fi
  if [[ "$(sed -n '2p' "$COMMIT_MSG_FILE")" != "" || -z "$(sed -n '3p' "$COMMIT_MSG_FILE")" ]]; then
    die "commit message needs a blank second line followed by a body explaining why the change was made"
  fi
  git -C "$REPO_DIR" add -A -- .
  git -C "$REPO_DIR" -c user.name="${RALPH_GIT_NAME:-ralph}" \
    -c user.email="${RALPH_GIT_EMAIL:-ralph@localhost}" \
    commit -F "$COMMIT_MSG_FILE" || die "failed to commit cycle changes"
  printf 'ralph: committed cycle changes as %s\n' "$(git -C "$REPO_DIR" rev-parse --short HEAD)"
else
  printf 'ralph: no repository changes to commit\n'
fi

# Publish the target repository (for a submodule target, this is the fork
# itself) to each configured remote, then, for a submodule target, record the
# moved submodule pointer and any spec/plan change in the superproject.
push_branch="$(git -C "$REPO_DIR" symbolic-ref --quiet --short HEAD || printf 'main')"
push_to_remotes "$REPO_DIR" "$push_branch" "$PUSH_REMOTES"

target_root="$(git -C "$REPO_DIR" rev-parse --show-toplevel)"
if [[ -n "$SUPER_ROOT" && "$SUPER_ROOT" != "$target_root" ]]; then
  sub_rel="$(realpath --relative-to="$SUPER_ROOT" "$target_root")"
  super_changed=0
  for f in "$SPEC_PATH" "$PLAN_PATH"; do
    if [[ -n "$(git -C "$SUPER_ROOT" status --porcelain --untracked-files=all -- "$f")" ]]; then
      git -C "$SUPER_ROOT" add -- "$f"
      super_changed=1
    fi
  done
  if [[ -n "$(git -C "$SUPER_ROOT" status --porcelain -- "$sub_rel")" ]]; then
    git -C "$SUPER_ROOT" add -- "$sub_rel"
    super_changed=1
  fi
  if (( super_changed )); then
    [[ -s "$COMMIT_MSG_FILE" ]] || die "spec/plan or submodule pointer changed but the agent wrote no commit message to $COMMIT_MSG_FILE"
    git -C "$SUPER_ROOT" -c user.name="${RALPH_GIT_NAME:-ralph}" \
      -c user.email="${RALPH_GIT_EMAIL:-ralph@localhost}" \
      commit -F "$COMMIT_MSG_FILE" || die "failed to commit spec/plan and submodule pointer in $SUPER_ROOT"
    printf 'ralph: committed spec/plan and submodule pointer in %s as %s\n' \
      "$SUPER_ROOT" "$(git -C "$SUPER_ROOT" rev-parse --short HEAD)"
    super_branch="$(git -C "$SUPER_ROOT" symbolic-ref --quiet --short HEAD || printf 'main')"
    push_to_remotes "$SUPER_ROOT" "$super_branch" "$PLAN_PUSH_REMOTES"
  else
    printf 'ralph: no spec/plan or submodule pointer changes to commit in %s\n' "$SUPER_ROOT"
  fi
fi
# Success stop: if the agent flagged the definition of done (or the ready queue
# is empty and it wrote a blocker plus .ralph/DONE), halt the loop cleanly.
if [[ -e "$RUN_DIR/DONE" ]]; then
  printf 'ralph: DONE present at %s; definition of done reached; halting loop\n' "$RUN_DIR/DONE" >&2
  exit 3
fi
printf 'ralph: cycle finished; review repository diff and %s\n' "$LOG_FILE"
