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

## Layer 2 — dind daemon GC (recommended durable fix, Atlas repo)

The workflow prune only runs on builds; a daemon-level GC keeps the build cache
bounded continuously. Give the `dind` container a `daemon.json` with buildkit
GC (mounted from a ConfigMap), for example:

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

That file is part of the runner's StatefulSet in the **Atlas infra repository**
(not this app repo). Mount it at `/etc/docker/daemon.json` on the `dind`
container. Once present, buildkit garbage-collects automatically even if no
build runs.

## Layer 3 — isolate dind storage (recommended)

Because the dind data is the container's writable layer, it is charged to the
node's `nodefs` and can evict unrelated pods. Give the `dind` container its own
volume (a `local-path` PVC or an `emptyDir` with a `sizeLimit`) for
`/var/lib/docker`, so growth is bounded and attributed to the runner, not the
node. Also consider raising the k3s kubelet image-GC thresholds
(`/etc/rancher/k3s/config.yaml`: `kubelet-arg: ["image-gc-high-threshold=70",
"image-gc-low-threshold=60"]`).

## Layer 4 — node-level timer (fallback)

If the runner config is not under change control, a host `systemd` timer or a
CronJob can run `docker system prune -af` inside the dind periodically:

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
