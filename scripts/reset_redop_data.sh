#!/usr/bin/env bash
# Throw away the hosted OpenExecutive instance's onboarding state at any time.
#
# Clears the instance's /data volume (onboarding session, company profile,
# people and approvers, episodic memory, ChromaDB index, integration
# credentials) and restarts the pods so the running processes drop any in-memory
# state. The volume itself is kept, so Argo CD's self-heal never fights this
# script, and the instance comes back as a clean, un-onboarded OpenExecutive.
#
# RED domain code, the platform chart, and the sealed secrets are untouched.
#
# Usage: scripts/reset_redop_data.sh [--yes] [--namespace=redop] [--pvc=redop-data]
# Environment: KUBECONFIG (default ~/.kube/atlas-admin.yaml), REDOP_NAMESPACE,
# REDOP_PVC, REDOP_ARGO_NAMESPACE, REDOP_ARGO_APP, REDOP_ASSUME_YES.

set -Eeuo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/reset_redop_data.sh [--yes] [--namespace=redop] [--pvc=redop-data]

Clears the hosted instance's /data volume (onboarding, company profile, people,
episodic memory, ChromaDB index, credentials) and restarts its pods, giving a
clean, un-onboarded OpenExecutive. RED code and platform config untouched.
Requires --yes for non-interactive runs.
EOF
}

NAMESPACE="${REDOP_NAMESPACE:-redop}"
PVC_NAME="${REDOP_PVC:-redop-data}"
ARGO_NS="${REDOP_ARGO_NAMESPACE:-argocd}"
ARGO_APP="${REDOP_ARGO_APP:-redop}"
API_DEPLOY="${REDOP_API_DEPLOY:-redop-api}"
UI_DEPLOY="${REDOP_UI_DEPLOY:-redop-ui}"
ASSUME_YES="${REDOP_ASSUME_YES:-no}"

for arg in "$@"; do
  case "$arg" in
    --yes|-y) ASSUME_YES=yes ;;
    --namespace=*) NAMESPACE="${arg#*=}" ;;
    --pvc=*) PVC_NAME="${arg#*=}" ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'unknown argument: %s\n' "$arg" >&2; usage; exit 2 ;;
  esac
done

die() { printf 'reset: %s\n' "$*" >&2; exit 1; }

command -v kubectl >/dev/null 2>&1 || die "kubectl is unavailable"
export KUBECONFIG="${KUBECONFIG:-$HOME/.kube/atlas-admin.yaml}"
[[ -f "$KUBECONFIG" ]] || die "no kubeconfig: set KUBECONFIG or create ~/.kube/atlas-admin.yaml"
kubectl -n "$NAMESPACE" get pvc "$PVC_NAME" >/dev/null 2>&1 \
  || die "data volume $NAMESPACE/$PVC_NAME not found; the instance may be down"

printf 'This clears %s/%s (all onboarding data, people, memory). It cannot be undone.\n' "$NAMESPACE" "$PVC_NAME"
if [[ "$ASSUME_YES" != yes ]]; then
  read -r -p 'Type the data volume name to confirm: ' answer
  [[ "$answer" == "$PVC_NAME" ]] || die "aborted"
fi

wait_for() { # $1=description $2=max-attempts ... $3+=command
  local desc="$1" attempts="$2"; shift 2
  local i
  for ((i = 0; i < attempts; i++)); do
    if "$@" >/dev/null 2>&1; then printf 'ok: %s\n' "$desc"; return 0; fi
    sleep 5
  done
  "$@" 2>&1 | head -5 || true
  die "timed out waiting for: $desc"
}

api_get() { # $1=path  -> prints the JSON body
  kubectl -n "$NAMESPACE" exec deploy/"$API_DEPLOY" -- python -c "
import os, urllib.request
req = urllib.request.Request('http://localhost:8000/$1', headers={'x-api-key': os.environ.get('BACKEND_SHARED_SECRET', '')})
print(urllib.request.urlopen(req, timeout=10).read().decode())
"
}

printf 'reset: clearing /data inside %s\n' "$API_DEPLOY"
kubectl -n "$NAMESPACE" exec deploy/"$API_DEPLOY" -- sh -c \
  'cd /data && rm -rf ./* ./.[!.]* ..?* 2>/dev/null; true'

# The API process may recreate working directories as it runs, so the check is
# on the durable state files that onboarding writes, not on an empty listing.
leftover="$(kubectl -n "$NAMESPACE" exec deploy/"$API_DEPLOY" -- sh -c 'ls -A /data 2>/dev/null | grep -v chroma_db || true')"
[[ -z "$leftover" ]] || die "durable state files still present after the wipe: $leftover"

printf 'reset: restarting the pods to drop in-memory state\n'
kubectl -n "$NAMESPACE" rollout restart deployment/"$API_DEPLOY" deployment/"$UI_DEPLOY" >/dev/null
wait_for "pods ready" 72 \
  bash -c "[[ \"\$(kubectl -n $NAMESPACE get pods 2>/dev/null | grep -c ' 1/1 ')\" == 2 ]]"
wait_for "api health endpoint ok" 40 \
  kubectl -n "$NAMESPACE" exec deploy/"$API_DEPLOY" -- python -c "import urllib.request;urllib.request.urlopen('http://localhost:8000/health', timeout=5)"

# The real proof is the API's own view: no people and no workspace profile.
people="$(api_get people 2>/dev/null)"
[[ "$people" == "[]" ]] || { printf 'reset: people still present: %s\n' "$people" >&2; die "onboarding state survived the reset"; }
workspace="$(api_get workspace 2>/dev/null)"
[[ "${workspace//[[:space:]]/}" == *'"role_kind":null'* ]] \
  || { printf 'reset: workspace still has a role: %s\n' "$workspace" >&2; die "onboarding state survived the reset"; }

printf 'reset: done. The instance is a clean, un-onboarded OpenExecutive again.\n'
printf 'reset: /data is empty; complete onboarding at https://redop.atlas.lan/onboard\n'
