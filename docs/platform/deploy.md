# Deployment on Atlas

The prototype is deployed to the **Atlas k3s** home-lab cluster. Delivery is
GitOps: CI builds pinned images, a digest/tag update lands in the GitOps repo, and
Argo CD reconciles a Helm release.

## Topology

| Piece | Value |
| --- | --- |
| Cluster | k3s, 3 control-plane + 1 worker node, home LAN `10.0.0.0/8` |
| Namespace / release | `redop` |
| Ingress host | `redop.atlas.lan` (Traefik; `atlas-ca` TLS; `10.0.0.0/8` allowlist) |
| Images | `registry.atlas.lan/atlas-admin/redop-api` and `redop-ui` |
| PostgreSQL | in-cluster `postgres:16.4-alpine`, 10Gi `truenas-nfs` PVC, `redop-postgres` service |
| Secrets | `redop-secrets` (backend/auth/OpenRouter), `gitea-registry` (registry pull; sealed file `redop-registry.yaml`), `redop-postgres` (SealedSecrets) |
| GitOps repo | `atlas-admin/atlas` (Gitea) → `apps/redop/chart`, `gitops/apps/redop.yaml` |
| Chart source | `deploy/charts/redop` in this repo (Q48); Argo CD reconciles it into `redop` |
| Access | `KUBECONFIG=~/.kube/atlas-admin.yaml` |

## Delivery pipeline

```text
push/tag on atlas-admin/red-operations-platform
        │  (Gitea Actions: .gitea/workflows/build.yaml)
        ▼
build + push redop-api / redop-ui ──▶ registry.atlas.lan
        │
        └─ commit the tag into apps/redop/chart/values.yaml (atlas-admin/atlas)
                     │  Gitea webhook
                     ▼
              Argo CD syncs the redop Application
```

- The app repo's CI (`.gitea/workflows/build.yaml`) builds both images and
  promotes the tag on a push to `main` (`sha-<short>`) or a `v*` tag. The
  checkout initializes the vendored submodule (HTTPS upstream) and the API image
  applies the ADR 0011 overlay.
- Argo CD auto-syncs with self-heal. The migration Job runs **before** the API
  serves (condition 9): it is a Helm pre-install/pre-upgrade hook and an Argo CD
  PreSync hook at sync-wave -1, and the API Deployment (sync-wave 0) waits for
  the Job's success in a `wait-for-migration` initContainer.

## Health gate

`make done` `[6/6]` runs `scripts/check_deployed_red_health.sh`, which fetches
`REDOP_HEALTH_URL` (default `https://redop.atlas.lan/`) and requires the body to
carry the RED identity marker (`REDOP_RED_MARKER`, default `RED Operations`). A
bare 200 from the OpenExecutive shell (title "Open Executive") cannot satisfy
condition 9.

## Deploy inputs (owner decisions)

- **A1** replace the OpenExecutive shell release in `redop` (one release).
- **B1** production backup target: scheduled `pg_dump` to `truenas-nfs`
  (24h RPO / 8h RTO). Per ADR 0009/0010 this is a production-readiness gate, not
  a prototype condition.
- **C1** Q47 may proceed before Q30; migration Job on every deploy; reuse the
  existing `redop-postgres`, `redop-secrets`, `gitea-registry`; api + ui + worker;
  same-origin ingress (`/red/*` → api, `/` → ui).

## Operations

```sh
export KUBECONFIG=~/.kube/atlas-admin.yaml

kubectl -n argocd get application redop            # Synced/Healthy?
kubectl -n redop get deploy,po,svc,ingress,pvc

# force a sync
kubectl -n argocd annotate application redop argocd.argoproj.io/refresh=hard --overwrite

# reset the hosted /data volume (onboarding, profile, memory, index)
make reset-hosted      # or scripts/reset_redop_data.sh --yes
```

## Current status (as of the last cycle)

The `redop` release is Synced/Healthy but runs the **un-customized OpenExecutive
shell** (`v0.4.6-redop.2`), so `make done` fails only `[6/6]` condition 9. The
RED Helm chart now exists at `deploy/charts/redop` (Q48: api/ui, migration Job
ordered before the API serves, same-origin ingress, PDB, probes; worker present
but disabled until a RED worker entrypoint exists). The remaining path to a real
condition 9 is **Q49** (Argo CD Application reconciling the RED chart) and
**Q50** (secrets, `REDOP_HEALTH_URL`, deployment smoke). This is the prototype's
head blocker.

## Production-readiness phase (beyond the prototype)

Before production client data: choose/confirm the backup target and pass a
witnessed restore drill, and pass the GitOps rollback drill (revert the image
digest; prove migrations are backward compatible and reversible). Neither is a
prototype condition (ADR 0009, ADR 0010).
