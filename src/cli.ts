#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import {
  DEFAULT_INSTALL_REPO,
  InstalledScope,
  QueryScope,
  Runner,
  Skill,
  VersionDiff,
  compareInstalledVersion,
  formatCommand,
} from "./domain.js";
import { findCatalogSkill, loadCatalogSkills } from "./catalog.js";
import { InstalledSkillsByScope, loadInstalledSkills } from "./installations.js";
import {
  resolveCatalogRoot,
  resolveGlobalSkillsRoot,
  resolveProjectRoot,
  resolveProjectSkillsRoot,
} from "./paths.js";
import { renderTable } from "./table.js";
import { UploadResult, uploadSkill } from "./upload.js";

interface ParsedArgs {
  command: string | undefined;
  positionals: string[];
  options: Map<string, string | boolean>;
}

interface ScopeStatus {
  scope: InstalledScope;
  version: string;
  state: VersionDiff["state"];
  diff: string;
  path?: string;
}

const VALUE_OPTIONS = new Set([
  "branch",
  "catalog",
  "category",
  "commit-message",
  "global-dir",
  "project",
  "remote",
  "remote-url",
  "repo",
  "runner",
  "scope",
  "target-name",
]);
const BOOLEAN_OPTIONS = new Set([
  "dry-run",
  "force",
  "global",
  "help",
  "include-missing",
  "json",
  "keep-temp",
  "project-only",
  "yes",
]);

function main(): void {
  try {
    const parsed = parseArgs(process.argv.slice(2));

    if (!parsed.command || parsed.options.get("help") === true || parsed.options.get("h") === true) {
      printHelp(parsed.command);
      return;
    }

    if (parsed.command === "help") {
      printHelp(parsed.positionals[0]);
      return;
    }

    switch (parsed.command) {
      case "list":
      case "ls":
        commandList(parsed);
        return;
      case "check":
      case "update":
        commandCheck(parsed);
        return;
      case "install":
      case "add":
        commandInstall(parsed);
        return;
      case "upgrade":
        commandUpgrade(parsed);
        return;
      case "upload":
      case "publish":
        commandUpload(parsed);
        return;
      default:
        throw new Error(`Unknown command: ${parsed.command}. Run "skillet --help" for usage.`);
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error(`Error: ${message}`);
    process.exitCode = 1;
  }
}

function parseArgs(argv: string[]): ParsedArgs {
  const options = new Map<string, string | boolean>();
  const positionals: string[] = [];
  let command: string | undefined;

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];

    if (arg === "--") {
      positionals.push(...argv.slice(index + 1));
      break;
    }

    if (arg.startsWith("--")) {
      const equalsIndex = arg.indexOf("=");
      const key = arg.slice(2, equalsIndex === -1 ? undefined : equalsIndex);
      if (!key) {
        continue;
      }

      if (equalsIndex !== -1) {
        if (BOOLEAN_OPTIONS.has(key)) {
          throw new Error(`Option --${key} does not accept a value.`);
        }
        if (!VALUE_OPTIONS.has(key)) {
          throw new Error(`Unknown option: --${key}.`);
        }
        options.set(key, arg.slice(equalsIndex + 1));
        continue;
      }

      if (VALUE_OPTIONS.has(key)) {
        const value = argv[index + 1];
        if (!value || value.startsWith("-")) {
          throw new Error(`Missing value for --${key}.`);
        }
        options.set(key, value);
        index += 1;
        continue;
      }

      if (!BOOLEAN_OPTIONS.has(key)) {
        throw new Error(`Unknown option: --${key}.`);
      }

      options.set(key, true);
      continue;
    }

    if (arg.startsWith("-") && arg.length > 1) {
      for (const flag of arg.slice(1)) {
        switch (flag) {
          case "g":
            options.set("global", true);
            break;
          case "h":
            options.set("help", true);
            break;
          case "y":
            options.set("yes", true);
            break;
          default:
            throw new Error(`Unknown short option: -${flag}.`);
        }
      }
      continue;
    }

    if (!command) {
      command = arg;
    } else {
      positionals.push(arg);
    }
  }

  return { command, positionals, options };
}

function commandList(parsed: ParsedArgs): void {
  const context = loadContext(parsed);
  const scope = parseScope(stringOption(parsed, "scope") || (boolOption(parsed, "global") ? "global" : "both"));
  const installed = loadInstalledSkills(scope, context.installationRoots);
  const rows = context.catalog.map((skill) => buildListRow(skill, installed, scope));

  if (boolOption(parsed, "json")) {
    printJson(rows);
    return;
  }

  const tableRows =
    scope === "both"
      ? [
          ["Skill", "Category", "Catalog", "Project", "Global", "Diff"],
          ...rows.map((row) => [row.name, row.category, row.catalogVersion, row.project.version, row.global.version, row.diff]),
        ]
      : [
          ["Skill", "Category", "Catalog", "Installed", "Diff"],
          ...rows.map((row) => {
            const status = scope === "project" ? row.project : row.global;
            return [row.name, row.category, row.catalogVersion, status.version, status.diff];
          }),
        ];

  console.log(renderTable(tableRows));
}

function commandCheck(parsed: ParsedArgs): void {
  const context = loadContext(parsed);
  const scope = parseScope(stringOption(parsed, "scope") || (boolOption(parsed, "global") ? "global" : "both"));
  const installed = loadInstalledSkills(scope, context.installationRoots);
  const rows = context.catalog.map((skill) => buildListRow(skill, installed, scope));
  const installedRows = rows.filter((row) => row.project.state !== "missing" || row.global.state !== "missing");
  const upgradeRows = installedRows.filter(
    (row) => isUpgradeAvailable(row.project.state) || isUpgradeAvailable(row.global.state),
  );
  const unknownRows = installedRows.filter((row) => row.project.state === "unknown" || row.global.state === "unknown");
  const newerRows = installedRows.filter((row) => row.project.state === "newer" || row.global.state === "newer");
  const missingRows = boolOption(parsed, "include-missing")
    ? rows.filter((row) => row.project.state === "missing" && row.global.state === "missing")
    : [];

  if (boolOption(parsed, "json")) {
    printJson({
      checked: installedRows.length,
      upgrades: upgradeRows,
      unknown: unknownRows,
      newer: newerRows,
      missing: missingRows,
    });
    return;
  }

  if (installedRows.length === 0) {
    console.log("No installed Skillet skills found in the selected .agents scope.");
    return;
  }

  if (upgradeRows.length === 0 && unknownRows.length === 0) {
    console.log(`All installed Skillet skills are current. Checked ${installedRows.length} skill(s).`);
  } else {
    console.log("Skillet skill upgrades are available:");
    console.log(renderTable([["Skill", "Project", "Global"], ...upgradeRows.map((row) => [row.name, row.project.diff, row.global.diff])]));
  }

  if (unknownRows.length > 0) {
    console.log("");
    console.log("Installed skills with unknown versions:");
    console.log(renderTable([["Skill", "Project", "Global"], ...unknownRows.map((row) => [row.name, row.project.diff, row.global.diff])]));
  }

  if (newerRows.length > 0) {
    console.log("");
    console.log("Installed skills newer than this catalog:");
    console.log(renderTable([["Skill", "Project", "Global"], ...newerRows.map((row) => [row.name, row.project.diff, row.global.diff])]));
  }

  if (missingRows.length > 0) {
    console.log("");
    console.log("Catalog skills not installed:");
    console.log(renderTable([["Skill", "Catalog"], ...missingRows.map((row) => [row.name, row.catalogVersion])]));
  }
}

function commandInstall(parsed: ParsedArgs): void {
  const context = loadContext(parsed);
  const runner = parseRunner(stringOption(parsed, "runner"));
  const repo = stringOption(parsed, "repo") || DEFAULT_INSTALL_REPO;
  const dryRun = boolOption(parsed, "dry-run");
  const global = boolOption(parsed, "global");
  const targets = resolveInstallTargets(parsed.positionals, context.catalog);

  for (const target of targets) {
    runSkillsAdd({ runner, repo, skillName: target.name, global, dryRun });
  }
}

function commandUpgrade(parsed: ParsedArgs): void {
  const context = loadContext(parsed);
  const runner = parseRunner(stringOption(parsed, "runner"));
  const repo = stringOption(parsed, "repo") || DEFAULT_INSTALL_REPO;
  const dryRun = boolOption(parsed, "dry-run");
  const force = boolOption(parsed, "force");
  const scope = parseUpgradeScope(parsed);
  const installed = loadInstalledSkills(scope, context.installationRoots);
  const targets = parsed.positionals.filter((value) => value !== "all");
  const plans = targets.length > 0
    ? buildExplicitUpgradePlans(targets, context.catalog, installed, scope, force)
    : buildDetectedUpgradePlans(context.catalog, installed, scope, force);

  if (plans.length === 0) {
    console.log("No Skillet skill upgrades are available in the selected .agents scope.");
    return;
  }

  for (const plan of plans) {
    runSkillsAdd({ runner, repo, skillName: plan.skill.name, global: plan.scope === "global", dryRun });
  }
}

function commandUpload(parsed: ParsedArgs): void {
  const [source, category] = parsed.positionals;
  if (!source || !category) {
    throw new Error("upload requires <source> and <category>. Run \"skillet upload --help\" for usage.");
  }

  const result = uploadSkill({
    source,
    category,
    repo: stringOption(parsed, "repo"),
    remote: stringOption(parsed, "remote"),
    remoteUrl: stringOption(parsed, "remote-url"),
    branch: stringOption(parsed, "branch") || "main",
    commitMessage: stringOption(parsed, "commit-message"),
    targetName: stringOption(parsed, "target-name"),
    dryRun: boolOption(parsed, "dry-run"),
    keepTemp: boolOption(parsed, "keep-temp"),
  });

  if (boolOption(parsed, "json")) {
    printJson(result);
    return;
  }

  printUploadResult(result);
}

function loadContext(parsed: ParsedArgs): {
  catalogRoot: string;
  catalog: Skill[];
  installationRoots: { project: string; global: string };
} {
  const catalogRoot = resolveCatalogRoot(stringOption(parsed, "catalog"));
  const projectRoot = resolveProjectRoot(stringOption(parsed, "project"));
  const globalRoot = resolveGlobalSkillsRoot(stringOption(parsed, "global-dir"));
  return {
    catalogRoot,
    catalog: loadCatalogSkills(catalogRoot),
    installationRoots: {
      project: resolveProjectSkillsRoot(projectRoot),
      global: globalRoot,
    },
  };
}

function buildListRow(skill: Skill, installed: InstalledSkillsByScope, scope: QueryScope): {
  name: string;
  category: string;
  catalogVersion: string;
  project: ScopeStatus;
  global: ScopeStatus;
  diff: string;
} {
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

function resolveInstallTargets(positionals: string[], catalog: Skill[]): Skill[] {
  if (positionals.length === 0) {
    throw new Error("install requires a skill name or all. Run \"skillet install --help\" for usage.");
  }

  if (positionals.includes("all")) {
    return catalog;
  }

  return positionals.map((name) => {
    const skill = findCatalogSkill(catalog, name);
    if (!skill) {
      throw new Error(`Unknown Skillet skill: ${name}`);
    }
    return skill;
  });
}

function buildDetectedUpgradePlans(
  catalog: Skill[],
  installed: InstalledSkillsByScope,
  scope: QueryScope,
  force: boolean,
): Array<{ skill: Skill; scope: InstalledScope }> {
  const plans: Array<{ skill: Skill; scope: InstalledScope }> = [];
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
): Array<{ skill: Skill; scope: InstalledScope }> {
  const plans: Array<{ skill: Skill; scope: InstalledScope }> = [];

  for (const target of targets) {
    const skill = findCatalogSkill(catalog, target);
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

function runSkillsAdd(input: {
  runner: Runner;
  repo: string;
  skillName: string;
  global: boolean;
  dryRun: boolean;
}): void {
  const args = buildSkillsAddArgs(input.runner, input.repo, input.skillName, input.global);
  const command = input.runner;
  console.log(formatCommand(command, args));

  if (input.dryRun) {
    return;
  }

  const result = spawnSync(command, args, {
    stdio: "inherit",
  });

  if (result.status !== 0) {
    throw new Error(`${command} exited with status ${result.status ?? "unknown"}.`);
  }
}

function buildSkillsAddArgs(runner: Runner, repo: string, skillName: string, global: boolean): string[] {
  const args = runner === "npx" ? ["-y", "skills", "add", repo] : ["skills", "add", repo];
  args.push("--skill", skillName);
  if (global) {
    args.push("-g", "-y");
  } else {
    args.push("-y");
  }
  return args;
}

function parseScope(value: string | undefined): QueryScope {
  if (!value) {
    return "both";
  }

  if (value === "project" || value === "global" || value === "both") {
    return value;
  }

  throw new Error(`Invalid scope: ${value}. Expected project, global, or both.`);
}

function parseUpgradeScope(parsed: ParsedArgs): QueryScope {
  if (boolOption(parsed, "global")) {
    return "global";
  }
  if (boolOption(parsed, "project-only")) {
    return "project";
  }
  return parseScope(stringOption(parsed, "scope") || "both");
}

function parseRunner(value: string | undefined): Runner {
  if (!value) {
    return "npx";
  }

  if (value === "npx" || value === "bunx") {
    return value;
  }

  throw new Error(`Invalid runner: ${value}. Expected npx or bunx.`);
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

function stringOption(parsed: ParsedArgs, key: string): string | undefined {
  const value = parsed.options.get(key);
  return typeof value === "string" ? value : undefined;
}

function boolOption(parsed: ParsedArgs, key: string): boolean {
  return parsed.options.get(key) === true;
}

function printJson(value: unknown): void {
  console.log(JSON.stringify(value, null, 2));
}

function printUploadResult(result: UploadResult): void {
  const prefix = result.dryRun ? "Dry run:" : "Uploaded:";
  console.log(`${prefix} ${result.skillName} -> ${result.targetRelativeRoot} (v${result.version})`);

  if (result.noChanges) {
    console.log("No changes detected.");
    return;
  }

  if (result.filesWritten.length > 0) {
    console.log("");
    console.log("Files written:");
    for (const file of result.filesWritten) {
      console.log(`  ${file}`);
    }
  }

  if (result.filesRemoved.length > 0) {
    console.log("");
    console.log("Files removed:");
    for (const file of result.filesRemoved) {
      console.log(`  ${file}`);
    }
  }

  console.log("");
  console.log(`CHANGELOG.md updated: ${result.changelogUpdated ? "yes" : "no"}`);
  console.log(`skills/README.md updated: ${result.readmeUpdated ? "yes" : "no"}`);

  if (result.mode === "remote") {
    console.log(`Remote pushed: ${result.pushed ? "yes" : "no"}`);
    if (result.commitSha) {
      console.log(`Commit: ${result.commitSha}`);
    }
  }
}

function printHelp(command: string | undefined): void {
  switch (command) {
    case "list":
    case "ls":
      console.log(LIST_HELP);
      return;
    case "check":
    case "update":
      console.log(CHECK_HELP);
      return;
    case "install":
    case "add":
      console.log(INSTALL_HELP);
      return;
    case "upgrade":
      console.log(UPGRADE_HELP);
      return;
    case "upload":
    case "publish":
      console.log(UPLOAD_HELP);
      return;
    default:
      console.log(ROOT_HELP);
  }
}

const ROOT_HELP = `Skillet skill administration CLI.

Usage:
  skillet <command> [options]
  skillet -h | --help

Commands:
  list      List catalog skills with installed version diffs.
  check     Check installed Skillet skills for available upgrades.
  install   Install one skill or all catalog skills via skills add.
  upgrade   Upgrade installed Skillet skills via skills add.
  upload    Publish or sync a local skill bundle into Skillet.
  help      Show help for a command.

Global options:
  --catalog <path>      Use a different Skillet catalog root.
  --project <path>      Project root for project-scoped .agents lookup.
  --global-dir <path>   Global .agents skills directory.
  -h, --help            Show help.

Examples:
  skillet list
  skillet check
  skillet install repo-quality-guardrails
  skillet install repo-quality-guardrails --global
  skillet install all --runner bunx --dry-run
  skillet upgrade
  skillet upload ~/.codex/skills/my-skill coding --dry-run
`;

const LIST_HELP = `List Skillet catalog skills with installed version diffs.

Usage:
  skillet list [options]

Options:
  --scope <scope>       project, global, or both. Default: both.
  --json                Print machine-readable JSON.
  --catalog <path>      Use a different Skillet catalog root.
  --project <path>      Project root for project-scoped .agents lookup.
  --global-dir <path>   Global .agents skills directory.
  -g, --global          Shortcut for --scope global.
  -h, --help            Show help.
`;

const CHECK_HELP = `Check installed Skillet skills for available upgrades.

Usage:
  skillet check [options]

Options:
  --scope <scope>       project, global, or both. Default: both.
  --include-missing     Include catalog skills that are not installed.
  --json                Print machine-readable JSON.
  --catalog <path>      Use a different Skillet catalog root.
  --project <path>      Project root for project-scoped .agents lookup.
  --global-dir <path>   Global .agents skills directory.
  -g, --global          Shortcut for --scope global.
  -h, --help            Show help.
`;

const INSTALL_HELP = `Install one or more Skillet skills through skills add.

Usage:
  skillet install <skill|all> [skill...] [options]

Options:
  --runner <runner>     npx or bunx. Default: npx.
  --repo <owner/repo>   Source repository for skills add. Default: ${DEFAULT_INSTALL_REPO}.
  -g, --global          Install globally with -g -y.
  --dry-run             Print commands without running them.
  --catalog <path>      Use a different Skillet catalog root.
  -h, --help            Show help.

Examples:
  skillet install claudecode-conventions
  skillet install repo-quality-guardrails --global
  skillet install all --runner bunx --dry-run
`;

const UPGRADE_HELP = `Upgrade installed Skillet skills through skills add.

Usage:
  skillet upgrade [skill...] [options]

Without skill names, upgrades all outdated installed Skillet skills in the selected .agents scope.

Options:
  --scope <scope>       project, global, or both. Default: both.
  --runner <runner>     npx or bunx. Default: npx.
  --repo <owner/repo>   Source repository for skills add. Default: ${DEFAULT_INSTALL_REPO}.
  --force               Re-run skills add even when the installed version is current.
  --project-only        Only upgrade the project-scoped .agents directory.
  -g, --global          Only upgrade the global .agents directory.
  --dry-run             Print commands without running them.
  --catalog <path>      Use a different Skillet catalog root.
  --project <path>      Project root for project-scoped .agents lookup.
  --global-dir <path>   Global .agents skills directory.
  -h, --help            Show help.
`;

const UPLOAD_HELP = `Publish or sync a local skill bundle into Skillet.

Usage:
  skillet upload <source-dir|SKILL.md> <category> [options]

Options:
  --repo <path>               Local Skillet checkout. Default: current directory.
  --remote <owner/repo>       Clone, commit, and push to a remote GitHub repo.
  --remote-url <git-url>      Clone URL for --remote.
  --branch <branch>           Remote branch for --remote. Default: main.
  --commit-message <message>  Commit message for --remote.
  --target-name <name>        Published skill directory name.
  --dry-run                   Compute the publication plan without writing or pushing.
  --keep-temp                 Keep temporary remote checkout for inspection.
  --json                      Print machine-readable JSON.
  -h, --help                  Show help.

Examples:
  skillet upload ~/.codex/skills/codex-langfuse-hook tracing --dry-run
  skillet upload ./my-skill coding --repo ~/Projects/skillet
  skillet upload ./my-skill coding --remote michaelpetrik/skillet
`;

main();
