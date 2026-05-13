import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {
  DEFAULT_INSTALL_REPO,
  choosePublicationVersion,
  normalizeCategorySlug,
  slugToTitle,
} from "./domain.js";
import { CommandRunner, runGitCommand } from "./command-runner.js";
import {
  buildDocument,
  canonicalSkillText,
  extractFrontmatterValue,
  extractH1,
  parseDocument,
  setFrontmatterFields,
} from "./frontmatter.js";
import { relativeFrom, resolvePath } from "./paths.js";

const SKILL_FILE = "SKILL.md";
const CHANGELOG_FILE = "CHANGELOG.md";
const README_RELATIVE_PATH = path.join("skills", "README.md");

export interface UploadOptions {
  source: string;
  category: string;
  repo?: string;
  remote?: string;
  remoteUrl?: string;
  branch: string;
  commitMessage?: string;
  targetName?: string;
  dryRun: boolean;
  keepTemp: boolean;
  commandRunner?: CommandRunner;
  clock?: () => Date;
}

export interface UploadResult {
  sourceRoot: string;
  repoRoot: string;
  targetRoot: string;
  targetRelativeRoot: string;
  targetName: string;
  targetPreviouslyExisted: boolean;
  skillName: string;
  displayName: string;
  category: string;
  categoryTitle: string;
  installRepoSlug: string;
  version: string;
  added: string[];
  changed: string[];
  removed: string[];
  filesWritten: string[];
  filesRemoved: string[];
  changelogUpdated: boolean;
  readmeUpdated: boolean;
  dryRun: boolean;
  noChanges: boolean;
  mode: "local" | "remote";
  remote?: string;
  remoteBranch?: string;
  remoteUrl?: string;
  temporaryRepoRoot?: string;
  pushed?: boolean;
  commitMessage?: string;
  commitSha?: string;
  gitStatus?: string;
}

interface FileMap {
  [relative: string]: string;
}

interface SkillTargetPaths {
  targetRoot: string;
  targetRelativeRoot: string;
}

interface UploadWriteOperation {
  type: "write";
  targetPath: string;
  targetRelativePath: string;
  content: string;
}

interface UploadCopyOperation {
  type: "copy";
  sourcePath: string;
  targetPath: string;
  targetRelativePath: string;
}

interface UploadRemoveOperation {
  type: "remove";
  targetPath: string;
  targetRelativePath: string;
}

type UploadOperation = UploadWriteOperation | UploadCopyOperation | UploadRemoveOperation;

interface UploadPlan {
  result: UploadResult;
  operations: UploadOperation[];
}

export function uploadSkill(options: UploadOptions): UploadResult {
  if (options.remote && options.repo) {
    throw new Error("Use either --repo or --remote, not both.");
  }
  if (options.remoteUrl && options.repo) {
    throw new Error("--remote-url cannot be combined with --repo.");
  }

  const sourceRoot = resolveSourceRoot(options.source);
  const categorySlug = normalizeCategorySlug(options.category);
  if (!categorySlug) {
    throw new Error("Category must not be empty.");
  }

  const targetName = validateTargetName(options.targetName ?? path.basename(sourceRoot));
  let tempParent: string | undefined;
  let repoRoot: string;
  let installRepoSlug: string;
  let mode: "local" | "remote";
  let remoteSlug: string | undefined;
  const commandRunner = options.commandRunner;

  if (options.remote) {
    remoteSlug = options.remote;
    const checkout = prepareRemoteCheckout(remoteSlug, options.remoteUrl, options.branch, commandRunner);
    tempParent = checkout.tempParent;
    repoRoot = checkout.repoRoot;
    installRepoSlug = remoteSlug;
    mode = "remote";
  } else {
    repoRoot = resolvePath(options.repo || process.cwd());
    installRepoSlug = resolveInstallRepoSlug(repoRoot, commandRunner);
    mode = "local";
  }

  try {
    const plan = planUploadIntoRepo({
      repoRoot,
      sourceRoot,
      categorySlug,
      targetName,
      dryRun: options.dryRun,
      installRepoSlug,
      clock: options.clock ?? systemClock,
    });

    if (!options.dryRun) {
      applyUploadPlan(plan);
    }
    const result = plan.result;
    result.mode = mode;

    if (mode === "remote") {
      result.remote = remoteSlug;
      result.remoteBranch = options.branch;
      result.remoteUrl = options.remoteUrl || `https://github.com/${remoteSlug}.git`;
      result.temporaryRepoRoot = repoRoot;

      if (!options.dryRun && !result.noChanges) {
        const pushResult = commitAndPushRemoteCheckout(
          repoRoot,
          result,
          options.branch,
          buildCommitMessage(result, options.commitMessage),
          commandRunner,
        );
        Object.assign(result, pushResult);
      } else {
        result.pushed = false;
      }
    }

    return result;
  } finally {
    if (tempParent && !options.keepTemp) {
      fs.rmSync(tempParent, { recursive: true, force: true });
    }
  }
}

function resolveSourceRoot(source: string): string {
  const sourcePath = resolvePath(source);
  if (!fs.existsSync(sourcePath)) {
    throw new Error(`Source path does not exist: ${sourcePath}`);
  }

  const stat = fs.statSync(sourcePath);
  if (stat.isFile()) {
    if (path.basename(sourcePath) !== SKILL_FILE) {
      throw new Error(`Expected ${SKILL_FILE} or a skill directory, got: ${sourcePath}`);
    }
    return path.dirname(sourcePath);
  }

  if (stat.isDirectory()) {
    return sourcePath;
  }

  throw new Error(`Unsupported source path: ${sourcePath}`);
}

function planUploadIntoRepo(input: {
  repoRoot: string;
  sourceRoot: string;
  categorySlug: string;
  targetName: string;
  dryRun: boolean;
  installRepoSlug: string;
  clock: () => Date;
}): UploadPlan {
  const { repoRoot, sourceRoot, categorySlug, targetName, dryRun, installRepoSlug, clock } = input;

  if (!fs.existsSync(repoRoot)) {
    throw new Error(`Skillet repo does not exist: ${repoRoot}`);
  }
  if (!fs.existsSync(path.join(repoRoot, "skills"))) {
    throw new Error(`Skillet repo does not contain a skills directory: ${repoRoot}`);
  }

  const sourceSkillPath = path.join(sourceRoot, SKILL_FILE);
  if (!fs.existsSync(sourceSkillPath)) {
    throw new Error(`Source skill is missing ${SKILL_FILE}: ${sourceSkillPath}`);
  }

  const safeTargetName = validateTargetName(targetName);
  const categoryTitle = slugToTitle(categorySlug);
  const { targetRoot, targetRelativeRoot } = resolveSkillTargetPaths(repoRoot, categorySlug, safeTargetName);
  const targetSkillPath = path.join(targetRoot, SKILL_FILE);
  const targetPreviouslyExisted = fs.existsSync(targetRoot);

  const sourceSkillText = fs.readFileSync(sourceSkillPath, "utf8");
  const sourceDocument = parseDocument(sourceSkillText);
  const sourceName = extractFrontmatterValue(sourceDocument.frontmatterLines, "name") || safeTargetName;
  const sourceDescription = extractFrontmatterValue(sourceDocument.frontmatterLines, "description") || "";
  const sourceVersion = extractFrontmatterValue(sourceDocument.frontmatterLines, "version");
  const displayName = extractH1(sourceDocument.body) || slugToTitle(sourceName);

  const sourceFiles = collectFiles(sourceRoot);
  const targetFiles = targetPreviouslyExisted ? collectFiles(targetRoot) : {};
  const added: string[] = [];
  const changed: string[] = [];
  const removed: string[] = [];

  for (const [relative, sourcePath] of Object.entries(sourceFiles)) {
    const targetPath = path.join(targetRoot, relative);
    if (!fs.existsSync(targetPath)) {
      added.push(relative);
      continue;
    }

    if (relative === SKILL_FILE) {
      const sourceCanonical = canonicalSkillText(fs.readFileSync(sourcePath, "utf8"));
      const targetCanonical = canonicalSkillText(fs.readFileSync(targetPath, "utf8"));
      if (sourceCanonical !== targetCanonical) {
        changed.push(relative);
      }
      continue;
    }

    if (fileDigest(sourcePath) !== fileDigest(targetPath)) {
      changed.push(relative);
    }
  }

  for (const relative of Object.keys(targetFiles)) {
    if (relative === CHANGELOG_FILE) {
      continue;
    }
    if (!sourceFiles[relative]) {
      removed.push(relative);
    }
  }

  const publicationChanged = added.length > 0 || changed.length > 0 || removed.length > 0 || !targetPreviouslyExisted;
  const existingSkillText = fs.existsSync(targetSkillPath) ? fs.readFileSync(targetSkillPath, "utf8") : "";
  const existingDocument = parseDocument(existingSkillText);
  const existingVersion = extractFrontmatterValue(existingDocument.frontmatterLines, "version");
  const version = choosePublicationVersion(existingVersion, sourceVersion, targetPreviouslyExisted, publicationChanged);

  const publishedFrontmatter = setFrontmatterFields(sourceDocument.frontmatterLines, categoryTitle, version);
  const publishedSkillText = buildDocument(publishedFrontmatter, sourceDocument.body);
  const targetSkillNeedsWrite = !fs.existsSync(targetSkillPath) || fs.readFileSync(targetSkillPath, "utf8") !== publishedSkillText;

  const changelogPath = path.join(targetRoot, CHANGELOG_FILE);
  let changelogUpdated = false;
  let changelogContent = "";
  if (!targetPreviouslyExisted || publicationChanged) {
    const changelog = updateChangelog({
      changelogPath,
      version,
      skillName: sourceName,
      categoryTitle,
      added,
      changed,
      removed,
      initialRelease: !targetPreviouslyExisted,
      publicationDate: formatPublicationDate(clock),
    });
    changelogUpdated = changelog.changed;
    changelogContent = changelog.content;
  }

  const readme = updateReadme({
    readmePath: path.join(repoRoot, README_RELATIVE_PATH),
    categorySlug,
    categoryTitle,
    targetName: safeTargetName,
    displayName,
    description: sourceDescription,
    installRepoSlug,
  });

  const operations: UploadOperation[] = [];

  for (const [relative, sourcePath] of Object.entries(sourceFiles)) {
    const targetPath = path.join(targetRoot, relative);
    const targetRelativePath = relativeFrom(repoRoot, targetPath);

    if (relative === SKILL_FILE) {
      if (targetSkillNeedsWrite) {
        operations.push({
          type: "write",
          targetPath,
          targetRelativePath,
          content: publishedSkillText,
        });
      }
      continue;
    }

    const needsCopy = !fs.existsSync(targetPath) || fileDigest(sourcePath) !== fileDigest(targetPath);
    if (needsCopy) {
      operations.push({
        type: "copy",
        sourcePath,
        targetPath,
        targetRelativePath,
      });
    }
  }

  for (const relative of removed) {
    const targetPath = path.join(targetRoot, relative);
    operations.push({
      type: "remove",
      targetPath,
      targetRelativePath: relativeFrom(repoRoot, targetPath),
    });
  }

  if (changelogUpdated) {
    operations.push({
      type: "write",
      targetPath: changelogPath,
      targetRelativePath: relativeFrom(repoRoot, changelogPath),
      content: changelogContent,
    });
  }

  if (readme.changed) {
    operations.push({
      type: "write",
      targetPath: path.join(repoRoot, README_RELATIVE_PATH),
      targetRelativePath: README_RELATIVE_PATH.split(path.sep).join("/"),
      content: readme.content,
    });
  }

  const filesWritten = operations
    .filter(
      (operation): operation is UploadWriteOperation | UploadCopyOperation =>
        operation.type === "write" || operation.type === "copy",
    )
    .map((operation) => operation.targetRelativePath);
  const filesRemoved = operations
    .filter((operation): operation is UploadRemoveOperation => operation.type === "remove")
    .map((operation) => operation.targetRelativePath);

  return {
    operations,
    result: {
      sourceRoot,
      repoRoot,
      targetRoot,
      targetRelativeRoot,
      targetName: safeTargetName,
      targetPreviouslyExisted,
      skillName: sourceName,
      displayName,
      category: categorySlug,
      categoryTitle,
      installRepoSlug,
      version,
      added,
      changed,
      removed,
      filesWritten,
      filesRemoved,
      changelogUpdated,
      readmeUpdated: readme.changed,
      dryRun,
      noChanges: operations.length === 0,
      mode: "local",
    },
  };
}

function applyUploadPlan(plan: UploadPlan): void {
  if (plan.operations.length === 0) {
    return;
  }

  ensureDirectory(plan.result.targetRoot);
  for (const operation of plan.operations) {
    if (operation.type === "write") {
      writeText(operation.targetPath, operation.content);
      continue;
    }

    if (operation.type === "copy") {
      copyFile(operation.sourcePath, operation.targetPath);
      continue;
    }

    removePath(operation.targetPath);
  }
}

function validateTargetName(value: string): string {
  if (value.length === 0 || value.trim().length === 0) {
    throw new Error("Invalid target name: target name must not be empty.");
  }

  if (value === "." || value === "..") {
    throw new Error("Invalid target name: target name must be a skill directory name.");
  }

  if (path.isAbsolute(value) || path.posix.isAbsolute(value) || path.win32.isAbsolute(value)) {
    throw new Error("Invalid target name: absolute paths are not allowed.");
  }

  if (value.includes("/") || value.includes("\\")) {
    throw new Error("Invalid target name: path separators are not allowed.");
  }

  if (/[\u0000-\u001F\u007F]/.test(value)) {
    throw new Error("Invalid target name: control characters are not allowed.");
  }

  return value;
}

function resolveSkillTargetPaths(repoRoot: string, categorySlug: string, targetName: string): SkillTargetPaths {
  const skillsRoot = path.resolve(repoRoot, "skills");
  const targetRoot = path.resolve(skillsRoot, categorySlug, targetName);

  if (!isPathInside(skillsRoot, targetRoot)) {
    throw new Error("Resolved upload target must stay under the skills directory.");
  }

  return {
    targetRoot,
    targetRelativeRoot: relativeFrom(repoRoot, targetRoot),
  };
}

function isPathInside(parent: string, child: string): boolean {
  const relative = path.relative(parent, child);
  return relative === "" || (relative !== ".." && !relative.startsWith(`..${path.sep}`) && !path.isAbsolute(relative));
}

function collectFiles(root: string): FileMap {
  const files: FileMap = {};
  if (!fs.existsSync(root)) {
    return files;
  }

  for (const entry of fs.readdirSync(root, { withFileTypes: true })) {
    const fullPath = path.join(root, entry.name);
    if (entry.isDirectory()) {
      if (entry.name === "__pycache__") {
        continue;
      }
      const nested = collectFiles(fullPath);
      for (const [relative, nestedPath] of Object.entries(nested)) {
        files[path.join(entry.name, relative).split(path.sep).join("/")] = nestedPath;
      }
      continue;
    }

    if (!entry.isFile()) {
      continue;
    }

    if (entry.name.endsWith(".pyc") || entry.name === ".DS_Store") {
      continue;
    }

    files[entry.name] = fullPath;
  }

  return Object.fromEntries(Object.entries(files).sort(([left], [right]) => left.localeCompare(right)));
}

function fileDigest(filePath: string): string {
  const digest = crypto.createHash("sha256");
  digest.update(fs.readFileSync(filePath));
  return digest.digest("hex");
}

function ensureDirectory(directory: string): void {
  fs.mkdirSync(directory, { recursive: true });
}

function writeText(filePath: string, content: string): void {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, content);
}

function copyFile(source: string, target: string): void {
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.copyFileSync(source, target);
}

function removePath(target: string): void {
  fs.rmSync(target, { recursive: true, force: true });
}

function buildReadmeEntry(input: {
  categorySlug: string;
  targetName: string;
  displayName: string;
  description: string;
  installRepoSlug: string;
}): string {
  return [
    `- **[${input.displayName}](./${input.categorySlug}/${input.targetName}/SKILL.md)**: ${input.description}`,
    "",
    "  **Install using skills.sh:**",
    "",
    "  With `npm`:",
    "  ```bash",
    `  npx skills add ${input.installRepoSlug} --skill ${input.targetName}`,
    "  ```",
    "",
    "  With `bun`:",
    "  ```bash",
    `  bunx skills add ${input.installRepoSlug} --skill ${input.targetName}`,
    "  ```",
    "",
  ].join("\n");
}

function updateReadme(input: {
  readmePath: string;
  categorySlug: string;
  categoryTitle: string;
  targetName: string;
  displayName: string;
  description: string;
  installRepoSlug: string;
}): { content: string; changed: boolean } {
  const intro = [
    "# Skillet Skills",
    "",
    "This directory contains specialized skills that extend the capabilities of AI agents working on this project.",
    "",
  ].join("\n");
  const current = fs.existsSync(input.readmePath) ? fs.readFileSync(input.readmePath, "utf8") : intro;
  const entry = buildReadmeEntry(input);

  const entryPattern = new RegExp(
    `^- \\*\\*\\[[^\\]]+]\\(\\./${escapeRegExp(input.categorySlug)}/${escapeRegExp(
      input.targetName,
    )}/SKILL\\.md\\)\\*\\*:.*?(?=^## |$(?![\\s\\S]))`,
    "ms",
  );

  if (entryPattern.test(current)) {
    const content = current.replace(entryPattern, entry);
    return { content: ensureTrailingNewline(content), changed: content !== current };
  }

  const sectionPattern = new RegExp(`^## ${escapeRegExp(input.categoryTitle)}\\n(.*?)(?=^## |$(?![\\s\\S]))`, "ms");
  const sectionMatch = sectionPattern.exec(current);
  if (sectionMatch) {
    const sectionBody = sectionMatch[1].trimEnd();
    const replacement = sectionBody
      ? `## ${input.categoryTitle}\n\n${sectionBody}\n\n${entry.trimEnd()}\n`
      : `## ${input.categoryTitle}\n\n${entry.trimEnd()}\n`;
    const content = current.slice(0, sectionMatch.index) + replacement + current.slice(sectionMatch.index + sectionMatch[0].length);
    return { content: ensureTrailingNewline(content), changed: content !== current };
  }

  const content = `${current.trimEnd()}\n\n## ${input.categoryTitle}\n\n${entry}`;
  return { content: ensureTrailingNewline(content), changed: content !== current };
}

function updateChangelog(input: {
  changelogPath: string;
  version: string;
  skillName: string;
  categoryTitle: string;
  added: string[];
  changed: string[];
  removed: string[];
  initialRelease: boolean;
  publicationDate: string;
}): { content: string; changed: boolean } {
  const header = [
    "# Changelog",
    "",
    "All notable changes to this skill are documented in this file.",
    "",
    "The format is based on Keep a Changelog and this project uses Semantic Versioning.",
    "",
  ].join("\n");
  const current = fs.existsSync(input.changelogPath) ? fs.readFileSync(input.changelogPath, "utf8") : header;
  const entry = buildChangelogEntry(input);
  const headerMatch = /^(# Changelog[\s\S]*?Semantic Versioning\.\n\n)/.exec(current);
  const content = headerMatch
    ? headerMatch[1] + entry + current.slice(headerMatch[0].length).replace(/^\n+/, "")
    : header + entry + current.slice(current.startsWith(header) ? header.length : 0).replace(/^\n+/, "");

  return { content: ensureTrailingNewline(content), changed: content !== current };
}

function buildChangelogEntry(input: {
  version: string;
  skillName: string;
  categoryTitle: string;
  added: string[];
  changed: string[];
  removed: string[];
  initialRelease: boolean;
  publicationDate: string;
}): string {
  const lines = [`## [${input.version}] - ${input.publicationDate}`];

  if (input.initialRelease) {
    lines.push("### Added", `- Initial publication of the \`${input.skillName}\` skill in the \`${input.categoryTitle}\` category.`);
    for (const relative of input.added) {
      if (relative !== SKILL_FILE) {
        lines.push(`- Added bundled resource \`${relative}\`.`);
      }
    }
    return `${lines.join("\n")}\n`;
  }

  if (input.added.length > 0) {
    lines.push("### Added");
    for (const relative of input.added) {
      lines.push(relative === SKILL_FILE ? "- Added the published `SKILL.md` entry." : `- Added bundled resource \`${relative}\`.`);
    }
  }

  if (input.changed.length > 0) {
    lines.push("### Changed", "- Synchronized the published skill bundle with the source skill.");
    for (const relative of input.changed) {
      lines.push(`- Updated \`${relative}\`.`);
    }
  }

  if (input.removed.length > 0) {
    lines.push("### Removed");
    for (const relative of input.removed) {
      lines.push(`- Removed stale published file \`${relative}\`.`);
    }
  }

  return `${lines.join("\n")}\n`;
}

function resolveInstallRepoSlug(repoRoot: string, commandRunner: CommandRunner | undefined): string {
  const result = runGitCommand(["remote", "get-url", "origin"], {
    cwd: repoRoot,
    commandRunner,
    throwOnError: false,
  });
  if (!result.ok) {
    return DEFAULT_INSTALL_REPO;
  }

  const remoteUrl = result.stdout.trim();
  const patterns = [
    /^https:\/\/github\.com\/(?<slug>[^/]+\/[^/.]+)(?:\.git)?$/,
    /^git@github\.com:(?<slug>[^/]+\/[^/.]+)(?:\.git)?$/,
  ];

  for (const pattern of patterns) {
    const match = pattern.exec(remoteUrl);
    if (match?.groups?.slug) {
      return match.groups.slug;
    }
  }

  return DEFAULT_INSTALL_REPO;
}

function prepareRemoteCheckout(
  remoteSlug: string,
  remoteUrl: string | undefined,
  branch: string,
  commandRunner: CommandRunner | undefined,
): { repoRoot: string; tempParent: string } {
  const tempParent = fs.mkdtempSync(path.join(os.tmpdir(), "skillet-upload-"));
  const repoRoot = path.join(tempParent, "repo");
  const cloneUrl = remoteUrl || `https://github.com/${remoteSlug}.git`;
  runGitCommand(["clone", "--depth", "1", "--branch", branch, cloneUrl, repoRoot], {
    cwd: tempParent,
    commandRunner,
    throwOnError: true,
  });
  return { repoRoot, tempParent };
}

function buildCommitMessage(result: UploadResult, explicitMessage: string | undefined): string {
  if (explicitMessage) {
    return explicitMessage;
  }

  const verb = result.targetPreviouslyExisted ? "Update" : "Publish";
  return `${verb} skill ${result.skillName} to ${result.targetRelativeRoot} (v${result.version})`;
}

function commitAndPushRemoteCheckout(
  repoRoot: string,
  result: UploadResult,
  branch: string,
  commitMessage: string,
  commandRunner: CommandRunner | undefined,
): Partial<UploadResult> {
  const trackedPaths = [README_RELATIVE_PATH.split(path.sep).join("/"), result.targetRelativeRoot];
  runGitCommand(["add", "-A", ...trackedPaths], {
    cwd: repoRoot,
    commandRunner,
    throwOnError: true,
  });
  const status = runGitCommand(["status", "--short", "--", ...trackedPaths], {
    cwd: repoRoot,
    commandRunner,
    throwOnError: true,
  }).stdout.trim();

  if (!status) {
    return {
      pushed: false,
      commitMessage,
      commitSha: undefined,
      gitStatus: "",
    };
  }

  runGitCommand(["commit", "-m", commitMessage], {
    cwd: repoRoot,
    commandRunner,
    throwOnError: true,
  });
  const commitSha = runGitCommand(["rev-parse", "HEAD"], {
    cwd: repoRoot,
    commandRunner,
    throwOnError: true,
  }).stdout.trim();
  runGitCommand(["push", "origin", branch], {
    cwd: repoRoot,
    commandRunner,
    throwOnError: true,
  });

  return {
    pushed: true,
    commitMessage,
    commitSha,
    gitStatus: status,
  };
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function ensureTrailingNewline(value: string): string {
  return value.endsWith("\n") ? value : `${value}\n`;
}

function systemClock(): Date {
  return new Date();
}

function formatPublicationDate(clock: () => Date): string {
  return clock().toISOString().slice(0, 10);
}
