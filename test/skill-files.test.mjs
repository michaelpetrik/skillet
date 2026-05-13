import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import {
  findCatalogSkillFiles,
  findInstalledSkillFiles,
  SKILL_FILE,
} from "../dist/skill-files.js";

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

function relativePaths(root, files) {
  return files.map((file) => path.relative(root, file).split(path.sep).join("/")).sort();
}

test("findCatalogSkillFiles scans every SKILL.md under the catalog skills root", () => {
  withTempRoot("skillet-catalog-skill-files-", (tempRoot) => {
    const skillsRoot = path.join(tempRoot, "skills");
    writeText(path.join(skillsRoot, SKILL_FILE));
    writeText(path.join(skillsRoot, "coding", "alpha", SKILL_FILE));
    writeText(path.join(skillsRoot, "coding", "alpha", "references", "nested", SKILL_FILE));
    writeText(path.join(skillsRoot, "coding", "alpha", "notes.md"));

    assert.deepEqual(relativePaths(skillsRoot, findCatalogSkillFiles(skillsRoot)), [
      "SKILL.md",
      "coding/alpha/SKILL.md",
      "coding/alpha/references/nested/SKILL.md",
    ]);
  });
});

test("findInstalledSkillFiles stops traversal at installed skill roots", () => {
  withTempRoot("skillet-installed-skill-files-", (tempRoot) => {
    writeText(path.join(tempRoot, SKILL_FILE));
    writeText(path.join(tempRoot, "alpha", SKILL_FILE));
    writeText(path.join(tempRoot, "alpha", "references", "nested", SKILL_FILE));
    writeText(path.join(tempRoot, "group", "beta", SKILL_FILE));
    writeText(path.join(tempRoot, "group", "gamma", "child", SKILL_FILE));

    assert.deepEqual(relativePaths(tempRoot, findInstalledSkillFiles(tempRoot)), [
      "alpha/SKILL.md",
      "group/beta/SKILL.md",
      "group/gamma/child/SKILL.md",
    ]);
  });
});
