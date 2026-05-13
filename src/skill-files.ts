import fs from "node:fs";
import path from "node:path";

export const SKILL_FILE = "SKILL.md";
export const CHANGELOG_FILE = "CHANGELOG.md";

export function findCatalogSkillFiles(root: string): string[] {
  const results: string[] = [];
  const entries = fs.readdirSync(root, { withFileTypes: true });

  for (const entry of entries) {
    const fullPath = path.join(root, entry.name);
    if (entry.isDirectory()) {
      results.push(...findCatalogSkillFiles(fullPath));
      continue;
    }

    if (entry.isFile() && entry.name === SKILL_FILE) {
      results.push(fullPath);
    }
  }

  return results;
}

export function findInstalledSkillFiles(root: string): string[] {
  const results: string[] = [];
  const entries = fs.readdirSync(root, { withFileTypes: true });

  for (const entry of entries) {
    if (!entry.isDirectory()) {
      continue;
    }

    const fullPath = path.join(root, entry.name);
    const skillPath = path.join(fullPath, SKILL_FILE);
    if (fs.existsSync(skillPath)) {
      results.push(skillPath);
      continue;
    }

    results.push(...findInstalledSkillFiles(fullPath));
  }

  return results;
}
