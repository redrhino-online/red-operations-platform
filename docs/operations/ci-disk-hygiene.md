# CI disk hygiene (the gitea-actions runner)

The Atlas Gitea Actions runner (`gitea-actions-runner-0` in the `gitea`
namespace) builds the RED images with a `docker:…-dind` sidecar. That sidecar
stores its images and build cache **in the container's writable layer**, which
lives on the node's ephemeral storage — so every build that leaves layers or
cache behind eats the node's disk.

On 2026-10-10 this filled `atlas-k3s-cp1`: the kubelet crossed its
ephemeral-storage eviction threshold, the node went `NotReady`, the runner was
killed mid-build, `redop-worker` was evicted, and `redop.atlas.lan` (which
resolves only to that node) went dark until the disk was grown and the node
reset. Pruning the dind is therefore required maintenance, and this page records
the layers of defence.

## Status

| Layer | Where | State |
| --- | --- | --- |
| 1. per-build prune | app repo, `.gitea/workflows/build.yaml` | in force (18a420a) |
| 2. dind daemon GC (buildkit) | Atlas repo, `apps/gitea-runner-hygiene/chart` ConfigMap, mounted via `helm/values/gitea-actions.yaml` | live 2026-10-10 |
| 3. dind storage isolation | Atlas repo, runner values: `/var/lib/docker` on a 15Gi `emptyDir` | live 2026-10-10 |
| 4. node-level timer | Atlas repo, `gitea-dind-prune` CronJob (hourly, RBAC to pods/exec) | live 2026-10-10 |

The layers 2-4 resources are owned by the `gitea-runner-hygiene` Argo
Application (in-house chart in the platform repo's
`apps/gitea-runner-hygiene/chart`).

## Layer 1 — per-build prune (in force)

`.gitea/workflows/build.yaml` ends with a `Prune the dind build cache` step that
runs on every build (`if: always()`, so it runs even when a build fails):

```yaml
      - name: Prune the dind build cache
        if: always()
        run: |
          docker container prune -f || true
          docker image prune -af || true
          docker builder prune -af --keep-storage 10GB || true
          docker system df || true
```

This bounds the build cache at 10 GB and drops the images the build pushed and
no longer needs. It does not touch a running image, so it is safe. This lives in
the app repository, so it ships with the workflow that triggers the builds.

## Layer 2 — dind daemon GC (live)

The workflow prune only runs on builds; a daemon-level GC keeps the build cache
bounded continuously. The `dind` container's `daemon.json` is the
`gitea-dind-daemon-json` ConfigMap (owned by the `gitea-runner-hygiene`
Application) mounted at `/etc/docker/daemon.json`, containing:

```json
{
  "builder": {
    "gc": {
      "enabled": true,
      "defaultKeepStorage": "10GB",
      "policy": [
        { "keepStorage": "10GB", "filter": ["unused-for=168h"] }
      ]
    }
  }
}
```

Keep only documented dockerd builder-GC keys: an unrecognized key stops
dockerd from starting and breaks CI (the dind `startupProbe` would fail). Once
present, buildkit garbage-collects automatically even if no build runs.

## Layer 3 — isolate dind storage (live)

The dind data is now an `emptyDir` with `sizeLimit: 15Gi` mounted at
`/var/lib/docker` (runner values): growth is pod-scoped, so a runaway build
evicts the runner pod instead of starving the node. It deliberately is not a
node-pinned `local-path` PVC: the runner must stay free to reschedule (it moved
cp1 → worker1 during the 2026-10-10 incident). The k3s kubelet image-GC
thresholds remain a further operator option (requires k3s restarts on every
node, so it was not applied).

## Layer 4 — scheduled prune (live)

The `gitea-dind-prune` CronJob (hourly at :17, `concurrencyPolicy: Forbid`)
execs into the dind and prunes containers, images unused for 48h, and builder
cache beyond 10GB. It uses the distroless `registry.k8s.io/kubectl` image, so
its command is exec-form and the shell runs on the dind side; its
ServiceAccount may only `get` pods and create `pods/exec` in the `gitea`
namespace. The same exec pattern works ad hoc:

```sh
kubectl -n gitea exec gitea-actions-runner-0 -c dind -- docker system prune -af
```

Prefer layers 1–3; a blind prune removes warm cache and slows the next build.

## Checking

```sh
# what the dind is holding
kubectl -n gitea exec gitea-actions-runner-0 -c dind -- docker system df
# the node the runner is on and its disk headroom
kubectl -n gitea get pod gitea-actions-runner-0 -o wide
```
