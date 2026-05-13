import path from "node:path";
import {
  InstalledScope,
  QueryScope,
  Skill,
  VersionDiff,
  compareInstalledVersion,
} from "./domain.js";
import type { InstalledSkillsByScope } from "./installations.js";

export interface ScopeStatus {
  scope: InstalledScope;
  version: string;
  state: VersionDiff["state"];
  diff: string;
  path?: string;
}

export interface ListRow {
  name: string;
  category: string;
  catalogVersion: string;
  project: ScopeStatus;
  global: ScopeStatus;
  diff: string;
}

export interface CheckPlan {
  checked: number;
  upgrades: ListRow[];
  unknown: ListRow[];
  newer: ListRow[];
  missing: ListRow[];
}

export interface UpgradePlan {
  skill: Skill;
  scope: InstalledScope;
}

export function buildListRows(catalog: Skill[], installed: InstalledSkillsByScope, scope: QueryScope): ListRow[] {
  return catalog.map((skill) => buildListRow(skill, installed, scope));
}

export function buildCheckPlan(rows: ListRow[], includeMissing: boolean): CheckPlan {
  const installedRows = rows.filter((row) => row.project.state !== "missing" || row.global.state !== "missing");
  const upgradeRows = installedRows.filter(
    (row) => isUpgradeAvailable(row.project.state) || isUpgradeAvailable(row.global.state),
  );
  const unknownRows = installedRows.filter((row) => row.project.state === "unknown" || row.global.state === "unknown");
  const newerRows = installedRows.filter((row) => row.project.state === "newer" || row.global.state === "newer");
  const missingRows = includeMissing
    ? rows.filter((row) => row.project.state === "missing" && row.global.state === "missing")
    : [];

  return {
    checked: installedRows.length,
    upgrades: upgradeRows,
    unknown: unknownRows,
    newer: newerRows,
    missing: missingRows,
  };
}

export function resolveInstallTargets(positionals: string[], catalog: Skill[]): Skill[] {
  if (positionals.length === 0) {
    throw new Error("install requires a skill name or all. Run \"skillet install --help\" for usage.");
  }

  if (positionals.includes("all")) {
    return catalog;
  }

  return positionals.map((name) => {
    const skill = findSkill(catalog, name);
    if (!skill) {
      throw new Error(`Unknown Skillet skill: ${name}`);
    }
    return skill;
  });
}

export function buildUpgradePlans(input: {
  positionals: string[];
  catalog: Skill[];
  installed: InstalledSkillsByScope;
  scope: QueryScope;
  force: boolean;
}): UpgradePlan[] {
  const targets = input.positionals.filter((value) => value !== "all");
  if (targets.length > 0) {
    return buildExplicitUpgradePlans(targets, input.catalog, input.installed, input.scope, input.force);
  }

  return buildDetectedUpgradePlans(input.catalog, input.installed, input.scope, input.force);
}

function buildListRow(skill: Skill, installed: InstalledSkillsByScope, scope: QueryScope): ListRow {
  const project = buildScopeStatus("project", skill, scope === "global" ? undefined : installed.project.get(skill.name));
  const global = buildScopeStatus("global", skill, scope === "project" ? undefined : installed.global.get(skill.name));
  const diffs = [project, global]
    .filter((status) => status.state !== "missing" && status.state !== "current")
    .map((status) => `${status.scope} ${status.diff}`);
  const installedCurrent = [project, global].some((status) => status.state === "current");

  return {
    name: skill.name,
    category: skill.category,
    catalogVersion: skill.version,
    project,
    global,
    diff: diffs.length > 0 ? diffs.join("; ") : installedCurrent ? "current" : "not installed",
  };
}

function buildScopeStatus(scope: InstalledScope, skill: Skill, installed: { version?: string; path?: string } | undefined): ScopeStatus {
  if (!installed) {
    return {
      scope,
      version: "missing",
      state: "missing",
      diff: "missing",
    };
  }

  const diff = compareInstalledVersion(skill.version, installed.version);
  return {
    scope,
    version: installed.version || "unknown",
    state: diff.state,
    diff: diff.label,
    path: installed.path,
  };
}

function buildDetectedUpgradePlans(
  catalog: Skill[],
  installed: InstalledSkillsByScope,
  scope: QueryScope,
  force: boolean,
): UpgradePlan[] {
  const plans: UpgradePlan[] = [];
  for (const skill of catalog) {
    for (const installedScope of selectedScopes(scope)) {
      const installedSkill = installed[installedScope].get(skill.name);
      if (!installedSkill) {
        continue;
      }

      const state = compareInstalledVersion(skill.version, installedSkill.version).state;
      if (force || isUpgradeable(state)) {
        plans.push({ skill, scope: installedScope });
      }
    }
  }

  return plans;
}

function buildExplicitUpgradePlans(
  targets: string[],
  catalog: Skill[],
  installed: InstalledSkillsByScope,
  scope: QueryScope,
  force: boolean,
): UpgradePlan[] {
  const plans: UpgradePlan[] = [];

  for (const target of targets) {
    const skill = findSkill(catalog, target);
    if (!skill) {
      throw new Error(`Unknown Skillet skill: ${target}`);
    }

    const scopes = selectedScopes(scope);
    const installedScopes = scopes.filter((installedScope) => installed[installedScope].has(skill.name));
    const targetScopes: InstalledScope[] = installedScopes.length > 0 ? installedScopes : [scope === "global" ? "global" : "project"];

    for (const targetScope of targetScopes) {
      const installedSkill = installed[targetScope].get(skill.name);
      const state = installedSkill ? compareInstalledVersion(skill.version, installedSkill.version).state : "missing";
      if (force || state === "missing" || isUpgradeable(state)) {
        plans.push({ skill, scope: targetScope });
      }
    }
  }

  return plans;
}

function findSkill(skills: Skill[], name: string): Skill | undefined {
  return skills.find((skill) => skill.name === name || path.basename(skill.path) === name);
}

function selectedScopes(scope: QueryScope): InstalledScope[] {
  if (scope === "both") {
    return ["project", "global"];
  }
  return [scope];
}

function isUpgradeable(state: VersionDiff["state"]): boolean {
  return state === "outdated" || state === "different" || state === "unknown";
}

function isUpgradeAvailable(state: VersionDiff["state"]): boolean {
  return state === "outdated" || state === "different";
}
