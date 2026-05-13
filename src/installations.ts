import fs from "node:fs";
import path from "node:path";
import { InstalledScope, InstalledSkill, QueryScope, slugToTitle } from "./domain.js";
import { extractFrontmatterValue, extractH1, parseDocument } from "./frontmatter.js";

export interface InstallationRoots {
  project?: string;
  global?: string;
}

export interface InstalledSkillsByScope {
  project: Map<string, InstalledSkill>;
  global: Map<string, InstalledSkill>;
}

export function loadInstalledSkills(scope: QueryScope, roots: InstallationRoots): InstalledSkillsByScope {
  return {
    project: scope === "global" ? new Map() : loadInstalledScope("project", roots.project),
    global: scope === "project" ? new Map() : loadInstalledScope("global", roots.global),
  };
}

export function loadInstalledScope(scope: InstalledScope, root: string | undefined): Map<string, InstalledSkill> {
  const installed = new Map<string, InstalledSkill>();
  if (!root || !fs.existsSync(root)) {
    return installed;
  }

  for (const skillPath of findSkillFiles(root)) {
    const text = fs.readFileSync(skillPath, "utf8");
    const document = parseDocument(text);
    const skillRoot = path.dirname(skillPath);
    const fallbackName = path.basename(skillRoot);
    const name = extractFrontmatterValue(document.frontmatterLines, "name") || fallbackName;
    installed.set(name, {
      name,
      displayName: extractH1(document.body) || slugToTitle(name),
      description: extractFrontmatterValue(document.frontmatterLines, "description") || "",
      category: extractFrontmatterValue(document.frontmatterLines, "category"),
      version: extractFrontmatterValue(document.frontmatterLines, "version"),
      scope,
      path: skillRoot,
    });
  }

  return installed;
}

function findSkillFiles(root: string): string[] {
  const results: string[] = [];
  const entries = fs.readdirSync(root, { withFileTypes: true });

  for (const entry of entries) {
    const fullPath = path.join(root, entry.name);
    if (entry.isDirectory()) {
      const skillPath = path.join(fullPath, "SKILL.md");
      if (fs.existsSync(skillPath)) {
        results.push(skillPath);
      } else {
        results.push(...findSkillFiles(fullPath));
      }
    }
  }

  return results;
}
