import assert from "node:assert/strict";
import test from "node:test";
import {
  ADVANCED_GROUPS,
  ADVANCED_ITEMS,
  PROFILE_NAV,
  SETTINGS_SECTIONS,
  advancedItemsByGroup,
  buildMobilePrimary,
  buildPrimaryNav,
  profileWording,
} from "../src/components/shell/navConfig.ts";

const shape = (groups) =>
  groups.map((g) => ({ key: g.key, label: g.label, items: g.items.map((i) => `${i.label} → ${i.href}`) }));

const RED_LINKS = [
  "Portfolio command center → /operations/command-center",
  "Client workspace → /operations/client-workspace",
  "Source and claim explorer → /operations/source-explorer",
  "Transformation map → /operations/transformation-map",
  "Offer and journey editor → /operations/offer-and-journey",
  "Build board → /operations/build-board",
  "Approval inbox → /operations/approval-inbox",
  "Workflow run detail → /operations/workflow-run-detail",
  "Launch readiness → /operations/launch-readiness",
  "Performance review → /operations/performance-review",
  "Portfolio opportunities → /operations/portfolio-opportunities",
  "Authority settings → /operations/authority-settings",
];

const TEAM = [
  { key: "red", label: "RED Operations", items: RED_LINKS },
  { key: "workspace", label: "Workspace", items: ["Workflows → /jobs", "Documents → /artifacts", "Watch list → /watchlist"] },
  { key: "company", label: "Company", items: ["Goals → /goals", "Company profile → /company-profile"] },
  { key: "knowledge", label: "Knowledge", items: ["Knowledge base → /knowledge"] },
];

const ROLE_KINDS = ["owner", "in_house", "independent", "other", null, undefined];

test("team nav includes the RED Operations screens", () => {
  assert.deepEqual(shape(buildPrimaryNav()), TEAM);
  assert.deepEqual(buildPrimaryNav({ mode: "team" }), buildPrimaryNav());
  const notOnboarded = shape(buildPrimaryNav({ isOnboarded: false }));
  assert.deepEqual(notOnboarded[2].items, ["Goals → /goals", "Set up company → /onboard"]);
  const profile = buildPrimaryNav()[2].items[1];
  assert.equal(profile.description, "Your company's identity and strategy — set up once, edited any time.");
});

test("team nav ignores the role", () => {
  for (const roleKind of ROLE_KINDS) {
    assert.deepEqual(buildPrimaryNav({ roleKind }), buildPrimaryNav());
    assert.deepEqual(buildPrimaryNav({ roleKind, isOnboarded: false }), buildPrimaryNav({ isOnboarded: false }));
  }
});

test("solo swaps the Company group for You while keeping RED Operations", () => {
  const solo = shape(buildPrimaryNav({ mode: "solo", roleKind: "owner" }));
  assert.deepEqual(solo[2], { key: "you", label: "You", items: ["Goals → /goals", "Business profile → /company-profile"] });
  assert.deepEqual([solo[0], solo[1], solo[3]], [TEAM[0], TEAM[1], TEAM[3]]);
  assert.ok(!JSON.stringify(solo).includes("/departments"));
});

test("solo: an owner's profile is their business", () => {
  const item = buildPrimaryNav({ mode: "solo", roleKind: "owner" })[2].items[1];
  assert.equal(item.label, "Business profile");
  assert.equal(item.description, "Your business — what you offer, who you serve, your priorities.");
  const notOnboarded = buildPrimaryNav({ mode: "solo", roleKind: "owner", isOnboarded: false })[2].items[1];
  assert.deepEqual([notOnboarded.label, notOnboarded.href], ["Set up your business", "/onboard"]);
});

test("solo: any other role, or none, is 'Your work'", () => {
  for (const roleKind of ["in_house", "independent", "other", null, undefined]) {
    const item = buildPrimaryNav({ mode: "solo", roleKind })[2].items[1];
    assert.deepEqual([item.label, item.href], ["Your work", "/company-profile"], String(roleKind));
    assert.equal(item.description, "Your work — the organisation you work in, who it serves, your priorities.");
    assert.ok(!/business|company/i.test(item.label + item.description), String(roleKind));
    const notOnboarded = buildPrimaryNav({ mode: "solo", roleKind, isOnboarded: false })[2].items[1];
    assert.deepEqual([notOnboarded.label, notOnboarded.href], ["Set up your work", "/onboard"]);
  }
  assert.deepEqual(buildPrimaryNav({ mode: "solo" }), buildPrimaryNav({ mode: "solo", roleKind: null }));
});

test("profileWording: company for a team, business for a solo owner, work otherwise", () => {
  for (const roleKind of ROLE_KINDS) assert.equal(profileWording("team", roleKind), "company");
  assert.equal(profileWording(), "company");
  assert.equal(profileWording("solo", "owner"), "business");
  for (const roleKind of ["in_house", "independent", "other", null, undefined]) {
    assert.equal(profileWording("solo", roleKind), "work");
  }
  for (const [wording, copy] of Object.entries(PROFILE_NAV)) {
    for (const [key, text] of Object.entries(copy)) assert.ok(text.trim(), `${wording}.${key}`);
  }
});

test("the review badge rides on Knowledge in both modes", () => {
  for (const mode of ["team", "solo"]) {
    const kb = buildPrimaryNav({ mode, reviewBadge: 4 }).find((group) => group.key === "knowledge").items[0];
    assert.equal(kb.badge, 4);
  }
});

test("mobile bar: solo swaps People for Goals", () => {
  assert.deepEqual(buildMobilePrimary().map((i) => i.href), ["/", "/memories", "/?new=1", "/people", "/jobs"]);
  assert.deepEqual(buildMobilePrimary("team"), buildMobilePrimary());
  assert.deepEqual(buildMobilePrimary("solo").map((i) => i.href), ["/", "/memories", "/?new=1", "/goals", "/jobs"]);
});

test("every destination explains itself", () => {
  for (const mode of ["team", "solo"]) {
    for (const roleKind of ROLE_KINDS) {
      const items = [...buildPrimaryNav({ mode, roleKind }).flatMap((g) => g.items), ...buildMobilePrimary(mode)];
      for (const item of items) assert.ok(item.description.trim(), `${item.href} needs a description`);
    }
  }
});

test("every Settings tool is in exactly one group, and no group is empty", () => {
  const keys = ADVANCED_GROUPS.map((g) => g.key);
  for (const item of ADVANCED_ITEMS) {
    assert.ok(keys.includes(item.group), `${item.href} has group ${item.group}`);
    assert.ok(item.description.trim(), `${item.href} needs a description`);
  }
  assert.equal(new Set(ADVANCED_ITEMS.map((i) => i.href)).size, ADVANCED_ITEMS.length);
  for (const group of advancedItemsByGroup()) assert.ok(group.items.length > 0, group.key);
});

test("Settings groups omit the generic Agent Council", () => {
  const grouped = advancedItemsByGroup().map((g) => ({ key: g.key, label: g.label, items: g.items.map((i) => `${i.label} → ${i.href}`) }));
  assert.deepEqual(grouped, [
    { key: "diagnose", label: "Check & diagnose", items: ["Setup status → /settings/status", "Audit log → /audit", "Token usage → /audit/usage"] },
    { key: "configure", label: "Configure", items: ["Company Simulator → /demo", "Client Companies → /clients"] },
    { key: "learn", label: "Learn", items: ["User Guide → /guide", "Architecture → /architecture"] },
  ]);
  assert.equal(grouped.flatMap((g) => g.items).length, ADVANCED_ITEMS.length);
});

test("the Settings sections have unique ids and a label each", () => {
  const ids = SETTINGS_SECTIONS.map((s) => s.id);
  assert.deepEqual(ids, ["executive", "workspace", "act-as-me", "tools", "about"]);
  assert.equal(new Set(ids).size, ids.length);
  for (const s of SETTINGS_SECTIONS) assert.ok(s.label.trim(), s.id);
});
