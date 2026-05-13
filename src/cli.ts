#!/usr/bin/env node
import {
  DEFAULT_INSTALL_REPO,
  QueryScope,
  Runner,
  Skill,
} from "./domain.js";
import { loadCatalogSkills } from "./catalog.js";
import {
  buildCheckPlan,
  buildListRows,
  buildUpgradePlans,
  resolveInstallTargets,
} from "./cli-use-cases.js";
import { loadInstalledSkills } from "./installations.js";
import {
  resolveCatalogRoot,
  resolveGlobalSkillsRoot,
  resolveProjectRoot,
  resolveProjectSkillsRoot,
} from "./paths.js";
import { renderTable } from "./table.js";
import { UploadResult, uploadSkill } from "./upload.js";
import { runSkillsAddCommand } from "./command-runner.js";

interface ParsedArgs {
  command: string | undefined;
  positionals: string[];
  options: Map<string, string | boolean>;
}

type OptionKind = "boolean" | "value";

interface CliOption {
  name: string;
  kind: OptionKind;
  short?: string;
}

interface CommandSpec {
  name: string;
  aliases: string[];
  description: string;
  help: () => string;
  handler: (parsed: ParsedArgs) => void;
  options: readonly CliOption[];
}

const HELP_OPTION: CliOption = { name: "help", kind: "boolean", short: "h" };
const CATALOG_OPTION: CliOption = { name: "catalog", kind: "value" };
const PROJECT_OPTION: CliOption = { name: "project", kind: "value" };
const GLOBAL_DIR_OPTION: CliOption = { name: "global-dir", kind: "value" };
const GLOBAL_SCOPE_OPTION: CliOption = { name: "global", kind: "boolean", short: "g" };
const YES_OPTION: CliOption = { name: "yes", kind: "boolean", short: "y" };
const SCOPE_OPTION: CliOption = { name: "scope", kind: "value" };
const JSON_OPTION: CliOption = { name: "json", kind: "boolean" };
const INCLUDE_MISSING_OPTION: CliOption = { name: "include-missing", kind: "boolean" };
const RUNNER_OPTION: CliOption = { name: "runner", kind: "value" };
const REPO_OPTION: CliOption = { name: "repo", kind: "value" };
const DRY_RUN_OPTION: CliOption = { name: "dry-run", kind: "boolean" };
const FORCE_OPTION: CliOption = { name: "force", kind: "boolean" };
const PROJECT_ONLY_OPTION: CliOption = { name: "project-only", kind: "boolean" };
const REMOTE_OPTION: CliOption = { name: "remote", kind: "value" };
const REMOTE_URL_OPTION: CliOption = { name: "remote-url", kind: "value" };
const BRANCH_OPTION: CliOption = { name: "branch", kind: "value" };
const COMMIT_MESSAGE_OPTION: CliOption = { name: "commit-message", kind: "value" };
const TARGET_NAME_OPTION: CliOption = { name: "target-name", kind: "value" };
const CATEGORY_OPTION: CliOption = { name: "category", kind: "value" };
const KEEP_TEMP_OPTION: CliOption = { name: "keep-temp", kind: "boolean" };

const GLOBAL_OPTIONS: readonly CliOption[] = [
  HELP_OPTION,
  CATALOG_OPTION,
  PROJECT_OPTION,
  GLOBAL_DIR_OPTION,
  YES_OPTION,
];

function main(): void {
  try {
    const parsed = parseArgs(process.argv.slice(2));

    if (!parsed.command || boolOption(parsed, "help")) {
      printHelp(parsed.command);
      return;
    }

    const command = findCommandSpec(parsed.command);
    if (!command) {
      throw new Error(`Unknown command: ${parsed.command}. Run "skillet --help" for usage.`);
    }

    command.handler(parsed);
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

      const option = LONG_OPTIONS.get(key);
      if (equalsIndex !== -1) {
        if (!option) {
          throw new Error(`Unknown option: --${key}.`);
        }
        if (option.kind === "boolean") {
          throw new Error(`Option --${key} does not accept a value.`);
        }
        options.set(option.name, arg.slice(equalsIndex + 1));
        continue;
      }

      if (!option) {
        throw new Error(`Unknown option: --${key}.`);
      }

      if (option.kind === "value") {
        const value = argv[index + 1];
        if (!value || value.startsWith("-")) {
          throw new Error(`Missing value for --${key}.`);
        }
        options.set(option.name, value);
        index += 1;
        continue;
      }

      options.set(option.name, true);
      continue;
    }

    if (arg.startsWith("-") && arg.length > 1) {
      for (const flag of arg.slice(1)) {
        const option = SHORT_OPTIONS.get(flag);
        if (!option) {
          throw new Error(`Unknown short option: -${flag}.`);
        }
        if (option.kind === "value") {
          throw new Error(`Short option -${flag} requires long form --${option.name}.`);
        }
        options.set(option.name, true);
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
  const rows = buildListRows(context.catalog, installed, scope);

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
  const rows = buildListRows(context.catalog, installed, scope);
  const plan = buildCheckPlan(rows, boolOption(parsed, "include-missing"));

  if (boolOption(parsed, "json")) {
    printJson(plan);
    return;
  }

  if (plan.checked === 0) {
    console.log("No installed Skillet skills found in the selected .agents scope.");
    return;
  }

  if (plan.upgrades.length === 0 && plan.unknown.length === 0) {
    console.log(`All installed Skillet skills are current. Checked ${plan.checked} skill(s).`);
  } else {
    console.log("Skillet skill upgrades are available:");
    console.log(renderTable([["Skill", "Project", "Global"], ...plan.upgrades.map((row) => [row.name, row.project.diff, row.global.diff])]));
  }

  if (plan.unknown.length > 0) {
    console.log("");
    console.log("Installed skills with unknown versions:");
    console.log(renderTable([["Skill", "Project", "Global"], ...plan.unknown.map((row) => [row.name, row.project.diff, row.global.diff])]));
  }

  if (plan.newer.length > 0) {
    console.log("");
    console.log("Installed skills newer than this catalog:");
    console.log(renderTable([["Skill", "Project", "Global"], ...plan.newer.map((row) => [row.name, row.project.diff, row.global.diff])]));
  }

  if (plan.missing.length > 0) {
    console.log("");
    console.log("Catalog skills not installed:");
    console.log(renderTable([["Skill", "Catalog"], ...plan.missing.map((row) => [row.name, row.catalogVersion])]));
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
    runSkillsAddCommand({ runner, repo, skillName: target.name, global, dryRun });
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
  const plans = buildUpgradePlans({
    positionals: parsed.positionals,
    catalog: context.catalog,
    installed,
    scope,
    force,
  });

  if (plans.length === 0) {
    console.log("No Skillet skill upgrades are available in the selected .agents scope.");
    return;
  }

  for (const plan of plans) {
    runSkillsAddCommand({ runner, repo, skillName: plan.skill.name, global: plan.scope === "global", dryRun });
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

function commandHelp(parsed: ParsedArgs): void {
  printHelp(parsed.positionals[0]);
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
  console.log(findCommandSpec(command)?.help() ?? formatRootHelp());
}

function findCommandSpec(command: string | undefined): CommandSpec | undefined {
  return command ? COMMANDS_BY_NAME.get(command) : undefined;
}

function buildCommandMap(commands: readonly CommandSpec[]): Map<string, CommandSpec> {
  const map = new Map<string, CommandSpec>();
  for (const command of commands) {
    for (const name of [command.name, ...command.aliases]) {
      if (map.has(name)) {
        throw new Error(`Duplicate command name or alias: ${name}`);
      }
      map.set(name, command);
    }
  }
  return map;
}

function buildLongOptionMap(options: readonly CliOption[]): Map<string, CliOption> {
  const map = new Map<string, CliOption>();
  for (const option of options) {
    const existing = map.get(option.name);
    if (existing && existing.kind !== option.kind) {
      throw new Error(`Conflicting option kind for --${option.name}`);
    }
    map.set(option.name, option);
  }
  return map;
}

function buildShortOptionMap(options: readonly CliOption[]): Map<string, CliOption> {
  const map = new Map<string, CliOption>();
  for (const option of options) {
    if (!option.short) {
      continue;
    }

    const existing = map.get(option.short);
    if (existing && existing.name !== option.name) {
      throw new Error(`Conflicting short option -${option.short}`);
    }
    map.set(option.short, option);
  }
  return map;
}

function formatRootHelp(): string {
  const commandWidth = Math.max(...COMMAND_SPECS.map((command) => command.name.length));
  const commands = COMMAND_SPECS
    .map((command) => `  ${command.name.padEnd(commandWidth)}  ${command.description}`)
    .join("\n");

  return `Skillet skill administration CLI.

Usage:
  skillet <command> [options]
  skillet -h | --help

Commands:
${commands}

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
}

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

const COMMAND_SPECS: readonly CommandSpec[] = [
  {
    name: "list",
    aliases: ["ls"],
    description: "List catalog skills with installed version diffs.",
    help: () => LIST_HELP,
    handler: commandList,
    options: [SCOPE_OPTION, JSON_OPTION, GLOBAL_SCOPE_OPTION],
  },
  {
    name: "check",
    aliases: ["update"],
    description: "Check installed Skillet skills for available upgrades.",
    help: () => CHECK_HELP,
    handler: commandCheck,
    options: [SCOPE_OPTION, INCLUDE_MISSING_OPTION, JSON_OPTION, GLOBAL_SCOPE_OPTION],
  },
  {
    name: "install",
    aliases: ["add"],
    description: "Install one skill or all catalog skills via skills add.",
    help: () => INSTALL_HELP,
    handler: commandInstall,
    options: [RUNNER_OPTION, REPO_OPTION, GLOBAL_SCOPE_OPTION, DRY_RUN_OPTION],
  },
  {
    name: "upgrade",
    aliases: [],
    description: "Upgrade installed Skillet skills via skills add.",
    help: () => UPGRADE_HELP,
    handler: commandUpgrade,
    options: [SCOPE_OPTION, RUNNER_OPTION, REPO_OPTION, FORCE_OPTION, PROJECT_ONLY_OPTION, GLOBAL_SCOPE_OPTION, DRY_RUN_OPTION],
  },
  {
    name: "upload",
    aliases: ["publish"],
    description: "Publish or sync a local skill bundle into Skillet.",
    help: () => UPLOAD_HELP,
    handler: commandUpload,
    options: [
      REPO_OPTION,
      REMOTE_OPTION,
      REMOTE_URL_OPTION,
      BRANCH_OPTION,
      COMMIT_MESSAGE_OPTION,
      TARGET_NAME_OPTION,
      DRY_RUN_OPTION,
      KEEP_TEMP_OPTION,
      JSON_OPTION,
      CATEGORY_OPTION,
    ],
  },
  {
    name: "help",
    aliases: [],
    description: "Show help for a command.",
    help: formatRootHelp,
    handler: commandHelp,
    options: [],
  },
];

const OPTION_SCHEMA: readonly CliOption[] = [
  ...GLOBAL_OPTIONS,
  ...COMMAND_SPECS.flatMap((command) => command.options),
];
const COMMANDS_BY_NAME = buildCommandMap(COMMAND_SPECS);
const LONG_OPTIONS = buildLongOptionMap(OPTION_SCHEMA);
const SHORT_OPTIONS = buildShortOptionMap(OPTION_SCHEMA);

main();
