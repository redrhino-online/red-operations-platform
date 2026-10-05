# Frontend

The UI is a thin Next.js client. It holds **no RED business logic** (ADR 0007);
it calls the RED backend REST surface under `/red` and renders state, provenance,
dependencies, versions and next actions.

## Stack

- Next.js 16 (App Router), React 19, TypeScript.
- `output: "standalone"` so the Docker image runs a minimal `server.js`.
- Vitest + Testing Library for the browser suite.
- Located in `frontend/src/`; the standalone build container is
  `Dockerfile.ui`.

## Section 8 screens (all twelve)

Registered in `frontend/dod-screens.txt`; the condition 6 gate
`scripts/check_frontend_screens.sh` requires all twelve.

| Screen | Route |
| --- | --- |
| Portfolio command center | `/command-center` |
| Client workspace overview | `/client-workspace` |
| Source and claim explorer | `/source-explorer` |
| Transformation map | `/transformation-map` |
| Offer and journey editor | `/offer-and-journey` |
| Build board with dependency view | `/build-board` |
| Approval inbox with exact version diff | `/approval-inbox` |
| Workflow run detail | `/workflow-run-detail` |
| Launch readiness | `/launch-readiness` |
| Performance review | `/performance-review` |
| Portfolio opportunities | `/portfolio-opportunities` |
| Authority settings | `/authority-settings` |

## Rules

- A client approver sees only the approved scope and review items assigned to them.
- Every artifact view shows state, provenance, dependencies, version history and
  next action.
- **No silent state change** after AI-generated content appears.

## Build and test

```sh
cd frontend
npm ci
npm run build     # next build
npm test          # vitest run
```

Gates: `scripts/check_frontend_screens.sh` (all screens present) and
`scripts/check_frontend_build.sh` (build + browser suite) run in DoD `[5/6]`.
