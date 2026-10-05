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
| Secrets | `redop-secrets` (backend/auth/OpenRouter), `redop-registry`, `redop-postgres` (SealedSecrets) |
| GitOps repo | `211lab/atlas` → `apps/redop/chart`, `gitops/apps/redop.yaml` |
| Access | `KUBECONFIG=~/.kube/atlas-admin.yaml` |

## Delivery pipeline

```text
push/tag on atlas-admin/red-operations-platform
        │  (Gitea Actions: .gitea/workflows/build.yaml)
        ▼
build + push redop-api / redop-ui ──▶ registry.atlas.lan
        │
        └─ commit the tag into apps/redop/chart/values.yaml (211lab/atlas)
                     │  Gitea webhook
                     ▼
              Argo CD syncs the redop Application
```

- The app repo's CI (`.gitea/workflows/build.yaml`) builds both images on a push
  to `main` and, on a `v*` tag, promotes the tag into the GitOps chart values.
- Argo CD auto-syncs with self-heal. The migration Job runs **before** the API
  serves (condition 9).

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
  existing `redop-postgres`, `redop-secrets`, `redop-registry`; api + ui + worker;
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
shell** (`v0.4.6-redop.2`), so `make done` fails only `[6/6]` condition 9. The path
to a real condition 9 is the **Q47-Q50** slice: Dockerfile + health endpoint, Helm
chart, Argo CD Application with migration-before-serve ordering, secrets + smoke.
This is the prototype's head blocker.

## Production-readiness phase (beyond the prototype)

Before production client data: choose/confirm the backup target and pass a
witnessed restore drill, and pass the GitOps rollback drill (revert the image
digest; prove migrations are backward compatible and reversible). Neither is a
prototype condition (ADR 0009, ADR 0010).
