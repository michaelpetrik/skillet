import fs from "node:fs";
import path from "node:path";
import { Skill, slugToTitle } from "./domain.js";
import { extractFrontmatterValue, extractH1, parseDocument } from "./frontmatter.js";
import { relativeFrom } from "./paths.js";
import { CHANGELOG_FILE, findCatalogSkillFiles } from "./skill-files.js";

export function loadCatalogSkills(catalogRoot: string): Skill[] {
  const skillsRoot = path.join(catalogRoot, "skills");
  if (!fs.existsSync(skillsRoot)) {
    throw new Error(`Catalog root does not contain a skills directory: ${catalogRoot}`);
  }

  return findCatalogSkillFiles(skillsRoot)
    .map((skillPath) => readSkill(skillPath, catalogRoot, skillsRoot))
    .sort((left, right) => left.name.localeCompare(right.name));
}

export function readSkill(skillPath: string, catalogRoot: string, skillsRoot?: string): Skill {
  const text = fs.readFileSync(skillPath, "utf8");
  const document = parseDocument(text);
  const skillRoot = path.dirname(skillPath);
  const root = skillsRoot ?? path.join(catalogRoot, "skills");
  const relativeToSkills = relativeFrom(root, skillPath);
  const segments = relativeToSkills.split("/");
  const categorySlug = segments.length > 2 ? segments[0] : "";
  const fallbackName = path.basename(skillRoot);
  const name = extractFrontmatterValue(document.frontmatterLines, "name") || fallbackName;
  const category = extractFrontmatterValue(document.frontmatterLines, "category") || slugToTitle(categorySlug);
  const changelogVersion = readLatestChangelogVersion(path.join(skillRoot, CHANGELOG_FILE));
  const version = extractFrontmatterValue(document.frontmatterLines, "version") || changelogVersion || "0.0.0";
  const displayName = extractH1(document.body) || slugToTitle(name);
  const description = extractFrontmatterValue(document.frontmatterLines, "description") || "";

  return {
    name,
    displayName,
    description,
    category,
    categorySlug,
    version,
    path: skillRoot,
    relativePath: relativeFrom(catalogRoot, skillRoot),
  };
}

export function findCatalogSkill(skills: Skill[], name: string): Skill | undefined {
  return skills.find((skill) => skill.name === name || path.basename(skill.path) === name);
}

function readLatestChangelogVersion(changelogPath: string): string | undefined {
  if (!fs.existsSync(changelogPath)) {
    return undefined;
  }

  const changelog = fs.readFileSync(changelogPath, "utf8");
  const match = /^## \[([0-9]+\.[0-9]+\.[0-9]+)]/m.exec(changelog);
  return match?.[1];
}
