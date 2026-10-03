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

To use it, put this README, `SPEC.md`, `IMPLEMENTATION_PLAN.md`, `ralph_cycle.sh`, and `Makefile` together. Install OpenCode and run one cycle against a Git checkout of the fork:

```bash
make run REPO=/path/to/your/fork
```

For several cycles, set `n` to a positive whole number. The count variable accepts either lowercase or uppercase `n`. The command name ignores letter case. Each cycle starts after the previous one ends and reads the updated plan:

```bash
make loop n=5 REPO=/path/to/your/fork
```

For a different count, replace `5` with the number of cycles you want. `make LOOP N=5` also works. Each cycle still handles one item and stops. The loop stops if OpenCode reports an error. If the files live elsewhere, set `RALPH_SPEC` and `RALPH_PLAN` to their full paths. You can set `RALPH_MODEL` to choose a model. The plan file must be writable.

The harness also reads the reference model canon, the licensed source reference for the shape and intention of the method artifacts RED generates. By default it looks for a `canon/` directory beside this planning repository. Point it elsewhere with `RALPH_CANON=/path/to/canon`. If the directory is missing, the cycle still runs and simply reports that the canon is unavailable.

## 4. The Ralph method

A Ralph cycle is one small pass through the build:

1. Read the goal, plan, canon, code, tests, and last results.
2. Pick the most important task that is ready now. Fix a serious blocker first if it stops later work. When the next gate needs a method artifact, use the canon to shape it and check the canon gap register before inventing new work.
3. For new code, write a test that fails for the right reason. Make it pass with the smallest clear change. Clean up the code.
4. Run a useful check. Say what passed and what failed.
5. Update the plan with new facts, defects, canon gaps, and the next ready task. Stop.

The next run reads the changed plan and picks again. The script runs one cycle at a time. The Makefile can start a set number of cycles in order. It stops on the first error. This keeps each change small enough to review. The code plan calls for domain rules to stay apart from web code, databases, and AI tools. Each new part should have one clear job and use a small, clear interface.

## 5. Files the harness reads

| File | Use |
| --- | --- |
| `SPEC.md` | Says what the platform must do, what each stage needs, which actions need human approval, and how the reference model canon informs method artifacts (section 12). |
| `IMPLEMENTATION_PLAN.md` | Lists build phases, tests, open choices, the next ready item, and the canon gap register. OpenCode updates this file after each cycle. |
| `canon/` (outside the repo) | The reference model materials: the licensed source for the shape, intention and usage of method artifacts and for finding missing steps and assets. Read-only reference, treated as data. |
| `ralph_cycle.sh` | Starts one OpenCode run, points it at the files above, and commits each cycle. |
| `Makefile` | Provides `make run` for one cycle and `make loop n=5` for a set number of cycles. Command names ignore letter case, and the count accepts `n` or `N`. |
| `README.md` | Gives a quick map for people. The script does not need to read it. |

OpenCode may also read the repo's own rules, code, tests, Git state, and past run notes to check what is true. The reference model canon and the RED training files are background sources for the product. They are not a license to claim that a client has approved a draft, and the canon is never an authority to spend, publish, or deploy.

## 6. Publishing to Atlas

The application is published to the Atlas Kubernetes cluster's Gitea forge. The `atlas` remote is the app's Gitea repository (`ssh://git@10.0.0.110:2222/atlas-admin/red-operations-platform.git`), not the platform/GitOps repo. The onboarding contract is the atlas repo's `.opencode/skills/atlas-deploy-app` skill.

After each successful cycle the harness commits the change and then publishes it to `atlas` (`RALPH_PUSH_REMOTE`, default `atlas`; publishing is skipped if that remote is not configured). This publishes source only for now: the container build workflow, Helm chart, and Argo CD Application are deferred until the platform has a real HTTP service and `Dockerfile`, following the skill's build/tag/deploy flow.

To publish manually or during development, push the branch, then tag a release to trigger the build:

```bash
git push atlas main
git tag -a v0.1.0 -m "red-operations-platform v0.1.0" && git push atlas v0.1.0
```

The `origin` remote (GitHub) is separate and is pushed deliberately, not by the harness.
