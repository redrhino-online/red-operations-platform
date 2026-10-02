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

`ralph_cycle.sh` is a small tool for building the platform with the OpenCode CLI. It gives OpenCode the product spec and the build plan. It asks OpenCode to inspect the real repo and pick one ready item that matters most. OpenCode then works on that item, checks the result, updates the plan with what it learned, and stops.

The script blocks a second run while one run is active. It writes a log in the target repo's `.ralph` folder. It does not commit code, push changes, deploy the app, or give client approval. Review the code and plan change after each run.

To use it, put this README, `SPEC.md`, `IMPLEMENTATION_PLAN.md`, `ralph_cycle.sh`, and `Makefile` together. Install OpenCode and run one cycle against a Git checkout of the fork:

```bash
make run REPO=/path/to/your/fork
```

For several cycles, set `n` to a positive whole number. The count variable accepts either lowercase or uppercase `n`. The command name ignores letter case. Each cycle starts after the previous one ends and reads the updated plan:

```bash
make loop n=5 REPO=/path/to/your/fork
```

For a different count, replace `5` with the number of cycles you want. `make LOOP N=5` also works. Each cycle still handles one item and stops. The loop stops if OpenCode reports an error. If the files live elsewhere, set `RALPH_SPEC` and `RALPH_PLAN` to their full paths. You can set `RALPH_MODEL` to choose a model. The plan file must be writable.

## 4. The Ralph method

A Ralph cycle is one small pass through the build:

1. Read the goal, plan, code, tests, and last results.
2. Pick the most important task that is ready now. Fix a serious blocker first if it stops later work.
3. For new code, write a test that fails for the right reason. Make it pass with the smallest clear change. Clean up the code.
4. Run a useful check. Say what passed and what failed.
5. Update the plan with new facts, defects, and the next ready task. Stop.

The next run reads the changed plan and picks again. The script runs one cycle at a time. The Makefile can start a set number of cycles in order. It stops on the first error. This keeps each change small enough to review. The code plan calls for domain rules to stay apart from web code, databases, and AI tools. Each new part should have one clear job and use a small, clear interface.

## 5. Files the harness reads

| File | Use |
| --- | --- |
| `SPEC.md` | Says what the platform must do, what each stage needs, and which actions need human approval. |
| `IMPLEMENTATION_PLAN.md` | Lists build phases, tests, open choices, and the next ready item. OpenCode updates this file after each cycle. |
| `ralph_cycle.sh` | Starts one OpenCode run and saves its log. It points OpenCode to the two files above. |
| `Makefile` | Provides `make run` for one cycle and `make loop n=5` for a set number of cycles. Command names ignore letter case, and the count accepts `n` or `N`. |
| `README.md` | Gives a quick map for people. The script does not need to read it. |

OpenCode may also read the repo's own rules, code, tests, Git state, and past run notes to check what is true. The RED training files are background sources for the product. They are not a license to claim that a client has approved a draft.
