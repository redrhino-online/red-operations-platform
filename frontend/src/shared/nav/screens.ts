// Single source of truth for the RED app's navigation (Q51; SPEC.md section 8).
//
// The sidebar (`shared/nav/AppNav.tsx`) and the landing dashboard
// (`app/page.tsx`) both build from this list, so a screen is added once. Every
// route here must match `frontend/dod-screens.txt`, which the condition 6 gate
// (`scripts/check_frontend_screens.sh`) verifies against the canonical section 8
// screen ids.

export interface RedScreen {
  /** Canonical section 8 screen id (matches dod-screens.txt). */
  id: string;
  /** App Router route. */
  route: string;
  label: string;
  description: string;
}

export interface RedNavGroup {
  key: string;
  label: string;
  screens: RedScreen[];
}

export const RED_NAV_GROUPS: RedNavGroup[] = [
  {
    key: "command",
    label: "Command",
    screens: [
      {
        id: "portfolio-command-center",
        route: "/command-center",
        label: "Portfolio command center",
        description: "Ranked interventions across the portfolio.",
      },
      {
        id: "client-workspace-overview",
        route: "/client-workspace",
        label: "Client workspace overview",
        description: "A client engagement at a glance.",
      },
      {
        id: "authority-settings",
        route: "/authority-settings",
        label: "Authority settings",
        description: "Who holds authority and approves each stage.",
      },
    ],
  },
  {
    key: "knowledge-method",
    label: "Knowledge & Method",
    screens: [
      {
        id: "source-and-claim-explorer",
        route: "/source-explorer",
        label: "Source and claim explorer",
        description: "Sources and the claims grounded on them.",
      },
      {
        id: "transformation-map",
        route: "/transformation-map",
        label: "Transformation map",
        description: "The signature solution's transformation steps.",
      },
    ],
  },
  {
    key: "commercial-production",
    label: "Commercial & Production",
    screens: [
      {
        id: "offer-and-journey-editor",
        route: "/offer-and-journey",
        label: "Offer and journey editor",
        description: "Offers and the journey that delivers them.",
      },
      {
        id: "build-board",
        route: "/build-board",
        label: "Build board",
        description: "Builds, their states and dependencies.",
      },
    ],
  },
  {
    key: "governance",
    label: "Governance",
    screens: [
      {
        id: "approval-inbox",
        route: "/approval-inbox",
        label: "Approval inbox",
        description: "Approvals with the exact version diff.",
      },
      {
        id: "workflow-run-detail",
        route: "/workflow-run-detail",
        label: "Workflow run detail",
        description: "A workflow run's transition log.",
      },
    ],
  },
  {
    key: "delivery-insight",
    label: "Delivery & Insight",
    screens: [
      {
        id: "launch-readiness",
        route: "/launch-readiness",
        label: "Launch readiness",
        description: "Stage 9 QA checks and traffic authorization.",
      },
      {
        id: "performance-review",
        route: "/performance-review",
        label: "Performance review",
        description: "The stage 10 baseline and post-launch milestones.",
      },
      {
        id: "portfolio-opportunities",
        route: "/portfolio-opportunities",
        label: "Portfolio opportunities",
        description: "Grow proposals grounded on approved assets.",
      },
    ],
  },
];

export const RED_SCREENS: RedScreen[] = RED_NAV_GROUPS.flatMap(
  (group) => group.screens,
);
