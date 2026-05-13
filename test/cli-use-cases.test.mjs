import test from "node:test";
import assert from "node:assert/strict";

import {
  buildCheckPlan,
  buildListRows,
  buildUpgradePlans,
  resolveInstallTargets,
} from "../dist/cli-use-cases.js";

function skill(name, version, extra = {}) {
  return {
    name,
    displayName: name,
    description: "",
    category: "Coding",
    categorySlug: "coding",
    version,
    path: `/catalog/skills/coding/${name}`,
    relativePath: `skills/coding/${name}`,
    ...extra,
  };
}

function installedSkill(name, version, scope) {
  return {
    name,
    displayName: name,
    description: "",
    version,
    scope,
    path: `/installed/${scope}/${name}`,
  };
}

function installedByScope(projectEntries = [], globalEntries = []) {
  return {
    project: new Map(projectEntries.map((entry) => [entry.name, entry])),
    global: new Map(globalEntries.map((entry) => [entry.name, entry])),
  };
}

test("buildListRows and buildCheckPlan summarize installed catalog state without rendering", () => {
  const catalog = [
    skill("current-skill", "1.0.0"),
    skill("outdated-skill", "2.0.0"),
    skill("unknown-skill", "1.0.0"),
    skill("missing-skill", "1.0.0"),
  ];
  const installed = installedByScope(
    [
      installedSkill("current-skill", "1.0.0", "project"),
      installedSkill("outdated-skill", "1.0.0", "project"),
    ],
    [installedSkill("unknown-skill", undefined, "global")],
  );

  const rows = buildListRows(catalog, installed, "both");
  const plan = buildCheckPlan(rows, true);

  assert.equal(plan.checked, 3);
  assert.deepEqual(plan.upgrades.map((row) => row.name), ["outdated-skill"]);
  assert.deepEqual(plan.unknown.map((row) => row.name), ["unknown-skill"]);
  assert.deepEqual(plan.missing.map((row) => row.name), ["missing-skill"]);
});

test("resolveInstallTargets expands all and rejects unknown names before execution", () => {
  const catalog = [skill("alpha", "1.0.0"), skill("beta", "1.0.0")];

  assert.deepEqual(resolveInstallTargets(["all"], catalog).map((target) => target.name), ["alpha", "beta"]);
  assert.deepEqual(resolveInstallTargets(["beta"], catalog).map((target) => target.name), ["beta"]);
  assert.throws(() => resolveInstallTargets(["missing"], catalog), /Unknown Skillet skill: missing/);
});

test("buildUpgradePlans detects upgradeable installed skills without spawning a runner", () => {
  const catalog = [skill("alpha", "2.0.0"), skill("beta", "1.0.0"), skill("gamma", "1.0.0")];
  const installed = installedByScope(
    [installedSkill("alpha", "1.0.0", "project")],
    [
      installedSkill("beta", "2.0.0", "global"),
      installedSkill("gamma", undefined, "global"),
    ],
  );

  const plans = buildUpgradePlans({
    positionals: [],
    catalog,
    installed,
    scope: "both",
    force: false,
  });

  assert.deepEqual(
    plans.map((plan) => `${plan.skill.name}:${plan.scope}`),
    ["alpha:project", "gamma:global"],
  );
});

test("buildUpgradePlans targets explicit missing skills in the selected scope", () => {
  const catalog = [skill("alpha", "1.0.0")];
  const installed = installedByScope();

  const projectPlans = buildUpgradePlans({
    positionals: ["alpha"],
    catalog,
    installed,
    scope: "both",
    force: false,
  });
  const globalPlans = buildUpgradePlans({
    positionals: ["alpha"],
    catalog,
    installed,
    scope: "global",
    force: false,
  });

  assert.deepEqual(projectPlans.map((plan) => `${plan.skill.name}:${plan.scope}`), ["alpha:project"]);
  assert.deepEqual(globalPlans.map((plan) => `${plan.skill.name}:${plan.scope}`), ["alpha:global"]);
});
