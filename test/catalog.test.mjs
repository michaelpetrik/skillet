import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import { findCatalogSkill, loadCatalogSkills, readSkill } from "../dist/catalog.js";

function withTempRoot(prefix, callback) {
  const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), prefix));
  try {
    callback(tempRoot);
  } finally {
    fs.rmSync(tempRoot, { recursive: true, force: true });
  }
}

function writeText(filePath, content = "") {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, content);
}

test("loadCatalogSkills throws when catalog root does not contain skills", () => {
  withTempRoot("skillet-catalog-missing-skills-", (catalogRoot) => {
    assert.throws(() => loadCatalogSkills(catalogRoot), /Catalog root does not contain a skills directory/);
  });
});

test("readSkill uses frontmatter/body/changelog/basename fallbacks with current precedence", () => {
  withTempRoot("skillet-catalog-read-skill-", (catalogRoot) => {
    const skillsRoot = path.join(catalogRoot, "skills");
    const skillPath = path.join(skillsRoot, "coding", "alpha-skill", "SKILL.md");
    const changelogPath = path.join(skillsRoot, "coding", "alpha-skill", "CHANGELOG.md");

    writeText(
      skillPath,
      `---\ndescription: >\n  First line\n  Second line\n---\n# Human Readable Alpha\nBody content\n`,
    );
    writeText(changelogPath, "## [2.3.4] - 2026-05-01\n\n- Added coverage\n");

    const skill = readSkill(skillPath, catalogRoot, skillsRoot);

    assert.equal(skill.name, "alpha-skill");
    assert.equal(skill.displayName, "Human Readable Alpha");
    assert.equal(skill.description, "First line Second line");
    assert.equal(skill.categorySlug, "coding");
    assert.equal(skill.category, "Coding");
    assert.equal(skill.version, "2.3.4");
    assert.equal(skill.relativePath, "skills/coding/alpha-skill");
  });
});

test("readSkill falls back to slug title display name and 0.0.0 version when metadata is absent", () => {
  withTempRoot("skillet-catalog-defaults-", (catalogRoot) => {
    const skillsRoot = path.join(catalogRoot, "skills");
    const skillPath = path.join(skillsRoot, "ops", "beta-skill", "SKILL.md");

    writeText(skillPath, "---\nname: custom_skill\n---\nNo heading present\n");

    const skill = readSkill(skillPath, catalogRoot, skillsRoot);

    assert.equal(skill.name, "custom_skill");
    assert.equal(skill.displayName, "Custom Skill");
    assert.equal(skill.version, "0.0.0");
    assert.equal(skill.description, "");
    assert.equal(skill.category, "Ops");
  });
});

test("findCatalogSkill resolves by explicit name and by path basename", () => {
  const skills = [
    {
      name: "canonical-name",
      displayName: "Canonical",
      description: "",
      category: "Coding",
      categorySlug: "coding",
      version: "1.0.0",
      path: "/catalog/skills/coding/dir-basename",
      relativePath: "skills/coding/dir-basename",
    },
  ];

  assert.equal(findCatalogSkill(skills, "canonical-name"), skills[0]);
  assert.equal(findCatalogSkill(skills, "dir-basename"), skills[0]);
  assert.equal(findCatalogSkill(skills, "missing"), undefined);
});
