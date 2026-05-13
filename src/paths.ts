import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

export function expandHome(value: string): string {
  if (value === "~") {
    return os.homedir();
  }

  if (value.startsWith("~/")) {
    return path.join(os.homedir(), value.slice(2));
  }

  return value;
}

export function resolvePath(value: string, base = process.cwd()): string {
  const expanded = expandHome(value);
  return path.resolve(base, expanded);
}

export function pathExists(value: string): boolean {
  return fs.existsSync(value);
}

export function findPackageRoot(startPath?: string): string {
  const start = startPath ?? path.dirname(fileURLToPath(import.meta.url));
  let current = fs.statSync(start).isDirectory() ? start : path.dirname(start);

  while (true) {
    if (fs.existsSync(path.join(current, "package.json")) && fs.existsSync(path.join(current, "skills"))) {
      return current;
    }

    const parent = path.dirname(current);
    if (parent === current) {
      throw new Error(`Could not find a Skillet package root from ${start}`);
    }
    current = parent;
  }
}

export function resolveCatalogRoot(value: string | undefined): string {
  if (value) {
    return resolvePath(value);
  }

  if (process.env.SKILLET_ROOT) {
    return resolvePath(process.env.SKILLET_ROOT);
  }

  return findPackageRoot();
}

export function resolveProjectRoot(value: string | undefined): string {
  return value ? resolvePath(value) : process.cwd();
}

export function resolveProjectSkillsRoot(projectRoot: string): string {
  return path.join(projectRoot, ".agents", "skills");
}

export function resolveGlobalSkillsRoot(value: string | undefined): string {
  if (value) {
    return resolvePath(value);
  }

  if (process.env.AGENTS_HOME) {
    return path.join(resolvePath(process.env.AGENTS_HOME), "skills");
  }

  return path.join(os.homedir(), ".agents", "skills");
}

export function relativeFrom(root: string, value: string): string {
  return path.relative(root, value).split(path.sep).join("/");
}
