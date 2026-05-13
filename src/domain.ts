export const DEFAULT_INSTALL_REPO = "michaelpetrik/skillet";

export type InstalledScope = "project" | "global";
export type QueryScope = InstalledScope | "both";
export type Runner = "npx" | "bunx";

export interface Skill {
  name: string;
  displayName: string;
  description: string;
  category: string;
  categorySlug: string;
  version: string;
  path: string;
  relativePath: string;
}

export interface InstalledSkill {
  name: string;
  displayName: string;
  description: string;
  category?: string;
  version?: string;
  scope: InstalledScope;
  path: string;
}

export type VersionState = "missing" | "current" | "outdated" | "newer" | "unknown" | "different";

export interface VersionDiff {
  state: VersionState;
  label: string;
}

export function isSemver(value: string | undefined): value is string {
  return typeof value === "string" && /^\d+\.\d+\.\d+$/.test(value);
}

export function compareSemver(left: string, right: string): number {
  const leftParts = left.split(".").map(Number);
  const rightParts = right.split(".").map(Number);

  for (let index = 0; index < 3; index += 1) {
    const diff = leftParts[index] - rightParts[index];
    if (diff !== 0) {
      return diff > 0 ? 1 : -1;
    }
  }

  return 0;
}

export function bumpPatch(value: string | undefined): string {
  if (!isSemver(value)) {
    return "1.0.0";
  }

  const [major, minor, patch] = value.split(".").map(Number);
  return `${major}.${minor}.${patch + 1}`;
}

export function choosePublicationVersion(
  existing: string | undefined,
  source: string | undefined,
  targetExists: boolean,
  changed: boolean,
): string {
  if (!targetExists) {
    return isSemver(source) ? source : "1.0.0";
  }

  if (!changed) {
    if (isSemver(existing)) {
      return existing;
    }
    return isSemver(source) ? source : "1.0.0";
  }

  if (isSemver(source) && isSemver(existing) && compareSemver(source, existing) > 0) {
    return source;
  }

  if (isSemver(source) && !isSemver(existing)) {
    return source;
  }

  return bumpPatch(existing);
}

export function compareInstalledVersion(catalogVersion: string, installedVersion: string | undefined): VersionDiff {
  if (!installedVersion) {
    return { state: "unknown", label: `unknown -> ${catalogVersion}` };
  }

  if (!isSemver(catalogVersion) || !isSemver(installedVersion)) {
    if (catalogVersion === installedVersion) {
      return { state: "current", label: "current" };
    }

    const installed = installedVersion || "unknown";
    return { state: "different", label: `${installed} -> ${catalogVersion}` };
  }

  const comparison = compareSemver(installedVersion, catalogVersion);
  if (comparison === 0) {
    return { state: "current", label: "current" };
  }

  if (comparison < 0) {
    return { state: "outdated", label: `${installedVersion} -> ${catalogVersion}` };
  }

  return { state: "newer", label: `${installedVersion} > ${catalogVersion}` };
}

export function normalizeCategorySlug(value: string): string {
  return value
    .trim()
    .replace(/\\/g, "/")
    .replace(/^\/+|\/+$/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9/_-]+/g, "-")
    .replace(/_+/g, "-")
    .replace(/-+/g, "-");
}

export function slugToTitle(slug: string): string {
  return slug
    .replace(/_/g, "-")
    .split("-")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function shellQuote(value: string): string {
  if (/^[A-Za-z0-9_./:@=-]+$/.test(value)) {
    return value;
  }

  return `'${value.replace(/'/g, "'\\''")}'`;
}

export function formatCommand(command: string, args: string[]): string {
  return [command, ...args].map(shellQuote).join(" ");
}
