# RED Operations Platform

## 1. Vision

RED Operations Platform helps RED turn a client's knowledge into a working business system. It tracks the work from intake to the first campaign, then keeps tracking results and improvements.

Each client has a workspace. The workspace shows what must be built, what is done, what is approved, and what is blocked. It shows who owns the next step. RED staff, client reviewers, and AI agents can work from the same record.

The core path has stages 0 through 10. It starts with intake and market research. It then defines the result, builds the client's method and offer, makes the message and video, connects the sales path, tests it, and launches a campaign. Each stage has a required asset and a review gate. Work done is not the same as work approved. A later stage cannot use an unapproved asset as final. A campaign launch starts a new period of measurement and improvement. It does not end the job.

## 2. Use of OpenExecutive

The plan is to fork OpenExecutive and shape it for RED. A fork is our own copy of the code that we can change. We first need to inspect its code, license, tests, and setup. The OpenExecutive source code is not part of these files, so reuse has not been verified.

We plan to keep useful parts when they pass review, such as the app shell, agent routing, work flows, stored client data, review steps, and alerts. We will replace the general business roles with RED agents. One RED Operations Director will guide the work and show a clear view of it. People keep the right to approve client methods, offers, claims, spending, and launch steps.

The target home is a Kubernetes cluster on a home network. Helm will define the app. Argo CD will apply changes from Git. Those tools belong to the delivery plan; the cluster and fork still need to be checked.

## 3. The build harness

`ralph_cycle.sh` is a small tool for building the platform with the OpenCode CLI. It gives OpenCode the product spec, the build plan, and the reference model canon. It asks OpenCode to inspect the real repo and pick one ready item that matters most. OpenCode then works on that item, checks the result, updates the plan with what it learned, and stops.

The script blocks a second run while one run is active. It writes a log in the target repo's `.ralph` folder. It does not push changes, deploy the app, or give client approval; it does commit each cycle's changes with the message the cycle writes. Review the code and plan change after each run.

The loop stops on `.ralph/STOP`, when the prototype meets its definition of done (SPEC section 13, checked by `make done`), or after `MAX_FAILURES` consecutive failures (default 5; a failed cycle retries the same round after `RETRY_SLEEP` seconds). A canon change after the run starts is an explicit, labeled halt: `make run` and `make loop` print `CANON DRIFT` and stop cleanly (no retry, no generic error); the harness itself exits 4. Re-lock with `make canon-pin`. A crashed cycle's lock is reclaimed automatically once its recorded pid is gone, so a hard kill does not wedge the loop. See `.env.example` for the local database the harness and `make check` use.

To use it, put this README, `SPEC.md`, `IMPLEMENTATION_PLAN.md`, `ralph_cycle.sh`, and `Makefile` together. Install OpenCode and run one cycle against a Git checkout of the fork:

```bash
make run REPO=/path/to/your/fork
```

For several cycles, set `n` to a positive whole number; if `n` is omitted it defaults to 1. For `n=-1`, it runs continuously until the definition of done, a `.ralph/STOP` file, or a hard error. The count variable accepts either lowercase or uppercase `n`, and the command name ignores letter case. Each cycle starts after the previous one ends and reads the updated plan:

```bash
make loop n=5 REPO=/path/to/your/fork
make loop n=-1 REPO=/path/to/your/fork
```

For a different count, replace `5` with the number of cycles you want. `make LOOP N=5` also works. Each cycle handles one item and stops. A failed cycle retries the same round up to `MAX_FAILURES` consecutive times before the loop halts. If the files live elsewhere, set `RALPH_SPEC` and `RALPH_PLAN` to their full paths. You can set `RALPH_MODEL` to choose a model. The plan file must be writable.

The harness also reads the reference model canon, the licensed source reference for the shape and intention of the method artifacts RED generates. By default it looks for a `canon/` directory beside this planning repository. Point it elsewhere with `RALPH_CANON=/path/to/canon`. If the directory is missing, the cycle still runs and simply reports that the canon is unavailable.

## 4. The Ralph method

A Ralph cycle is one small pass through the build:

1. Read the goal, plan, canon, code, tests, and last results.
2. Pick the most important task that is ready now. Fix a serious blocker first if it stops later work. When the next gate needs a method artifact, use the canon to shape it and check the canon gap register before inventing new work.
3. For new code, write a test that fails for the right reason. Make it pass with the smallest clear change. Clean up the code.
4. Run a useful check. Say what passed and what failed.
5. Update the plan with new facts, defects, canon gaps, and the next ready task. Stop.

The next run reads the changed plan and picks again. The script runs one cycle at a time. The Makefile can start a set number of cycles in order. It stops on the first error. This keeps each change small enough to review. The code plan calls for domain rules to stay apart from web code, databases, and AI tools. Each new part should have one clear job and use a small, clear interface.

Cycles are token-disciplined: they use the Serena code-memory MCP for an indexed first pass (symbol overview and search, and project memories) and read narrowly with offsets instead of loading the repository, and they record durable facts as memories so later cycles do not rediscover them. The harness prompt carries this as a hard rule.

## 5. Files the harness reads

| File | Use |
| --- | --- |
| `SPEC.md` | Says what the platform must do, what each stage needs, which actions need human approval, and how the reference model canon informs method artifacts (section 12). |
| `IMPLEMENTATION_PLAN.md` | Lists build phases, tests, open choices, the next ready item, and the canon gap register. OpenCode updates this file after each cycle. |
| `canon/` (outside the repo) | The reference model materials: the licensed source for the shape, intention and usage of method artifacts and for finding missing steps and assets. Read-only reference, treated as data. |
| `canon.lock` | The pinned sha256 of the canon content. `make run` and `make loop` lock it at the start (`make canon-lock`); a mid-run canon change halts the loop until `make canon-pin` re-pins it (`RALPH_CANON_STRICT=0` overrides). |
| `ralph_cycle.sh` | Starts one OpenCode run, points it at the files above, and commits each cycle. |
| `Makefile` | Provides `make run` for one cycle and `make loop n=5` for a set number of cycles. Command names ignore letter case, and the count accepts `n` or `N`. |
| `vendor/openexecutive/` | The absorbed OpenExecutive fork: ordinary tracked source in this repository (ADR 0014), pinned upstream commit recorded in `docs/fork_inventory.md`. RED changes inside it are additive. |
| `README.md` | Gives a quick map for people. The script does not need to read it. |

OpenCode may also read the repo's own rules, code, tests, Git state, and past run notes to check what is true. The reference model canon and the RED training files are background sources for the product. They are not a license to claim that a client has approved a draft, and the canon is never an authority to spend, publish, or deploy.

## 6. The OpenExecutive dependency

The application is this repository. RED code lives under `backend/redops/`
together with the RED backend entry points (`docs/adr/0008`). OpenExecutive is
absorbed into this repository at `vendor/openexecutive/` as ordinary tracked
source (ADR 0014), pinned at upstream commit `31e55338db7f7a0eb7ff30b4cb8942a1ece551bd`
(v0.4.6) and consumed through ports and composition. RED changes inside the
vendor tree are additive by default; RED-adopted surfaces and owner-approved
exceptions (recorded in `docs/fork_inventory.md`) are the only modifications,
enforced by `scripts/check_vendor_additive.sh`.

Run cycles against this repository:

```bash
make run
# or
make loop n=5
```

RED changes and enhancements that OpenExecutive does not provide are built here,
in `backend/redops/`, as SOLID, clean, onion-architecture code behind ports; the
cockpit overhaul adds screens and surfaces inside the vendor tree additively
(ADR 0013, ADR 0014). `docs/adr/0002` (port RED into the fork and target it) is
superseded by `docs/adr/0008`.

## 7. Publishing

The harness publishes after each successful cycle. `RALPH_PUSH_REMOTES` (default
`origin`) lists the remotes to push the repository to; `RALPH_PLAN_PUSH_REMOTES`
(default: the same) does so for the spec/plan superproject (identical here). A
remote that is not configured is skipped. The `upstream` fork remote
(SenteLabsAI) is never pushed.

- `make run` and every non-final `make loop` cycle push to `origin` only. The
  final cycle of a `make loop` also pushes to `atlas`, so a long run does not
  push an unfinished branch to Atlas until the last round. Override with
  `PUSH_REMOTES` and `FINAL_PUSH_REMOTES`.
- This repository's `atlas` remote is the Atlas Gitea repository, reached as
  `ssh://gitea-atlas/atlas-admin/red-operations-platform.git` (the `gitea-atlas`
  ssh alias uses `~/.ssh/id_rsa` on port 2222), not the platform/GitOps repo
  (`github.com/211lab/atlas`).

Publishing is no longer source-only: a push to `atlas` `main` (or a `v*` tag)
triggers the Gitea build workflow (`.gitea/workflows/build.yaml`), which builds
the RED API and cockpit images, pushes them to `registry.atlas.lan`, and
promotes the tag into the GitOps repo (`atlas-admin/atlas`,
`apps/redop/chart/values.yaml`). Argo CD reconciles the `redop` application from
that repo, running the migration Job before the API serves.

The deployed app is the single-shell cockpit (ADR 0013): the rebranded
OpenExecutive cockpit at `https://redop.atlas.lan/` is the only user-facing UI,
serving the twelve RED Operations screens at native `/operations/*` routes with
the portfolio command center as the landing surface. The separate `/screens`
thin client is retired — there is no `frontend/` app, no `Dockerfile.ui`, no
`redop-ui` Deployment and no `/screens` ingress route (K7) — so the chart
carries only the API, cockpit, worker, migration Job and PostgreSQL. The
definition-of-done gate (`make done`) proves the single shell live as its
`[7/7]` check.

To publish manually, push the branch, then tag a release:

```bash
git push atlas main && git push origin main
git tag -a v0.1.0 -m "red-operations-platform v0.1.0" && git push atlas v0.1.0
```

## 8. Stopping a loop

While `make loop` is running, create a stop file in the target repository:

```bash
touch .ralph/STOP
```

Before each cycle the harness checks for `.ralph/STOP`. If present it skips the
cycle and the loop halts cleanly (exit status 3, not an error). The file is not
removed, so the loop stays stopped until you delete it:

```bash
rm .ralph/STOP
```

When running against another target with `REPO=...`, the file is
`$REPO/.ralph/STOP`. A single `make run` also honours the stop file.

