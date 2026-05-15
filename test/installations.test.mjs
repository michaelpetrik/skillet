import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import { loadInstalledScope, loadInstalledSkills } from "../dist/installations.js";

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

test("loadInstalledScope returns empty map for undefined or missing roots", () => {
  assert.equal(loadInstalledScope("project", undefined).size, 0);

  withTempRoot("skillet-installed-missing-", (tempRoot) => {
    const missingRoot = path.join(tempRoot, "does-not-exist");
    assert.equal(loadInstalledScope("global", missingRoot).size, 0);
  });
});

test("loadInstalledScope uses frontmatter/body/basename fallbacks and keeps current name keying", () => {
  withTempRoot("skillet-installed-fallbacks-", (root) => {
    writeText(
      path.join(root, "alpha", "SKILL.md"),
      `---\ndescription: >\n  First line\n  Second line\ncategory: Utilities\n---\n# Alpha Display\n`,
    );

    writeText(path.join(root, "beta", "SKILL.md"), "---\nname: custom_name\n---\nNo heading\n");

    const installed = loadInstalledScope("project", root);

    const alpha = installed.get("alpha");
    assert.ok(alpha);
    assert.equal(alpha.name, "alpha");
    assert.equal(alpha.displayName, "Alpha Display");
    assert.equal(alpha.description, "First line Second line");
    assert.equal(alpha.category, "Utilities");
    assert.equal(alpha.version, undefined);
    assert.equal(alpha.scope, "project");

    const custom = installed.get("custom_name");
    assert.ok(custom);
    assert.equal(custom.name, "custom_name");
    assert.equal(custom.displayName, "Custom Name");

    assert.equal(installed.has("beta"), false);
  });
});

test("loadInstalledSkills respects selected scope for project/global/both", () => {
  withTempRoot("skillet-installed-scopes-", (tempRoot) => {
    const projectRoot = path.join(tempRoot, "project");
    const globalRoot = path.join(tempRoot, "global");

    writeText(path.join(projectRoot, "project-skill", "SKILL.md"), "# Project skill\n");
    writeText(path.join(globalRoot, "global-skill", "SKILL.md"), "# Global skill\n");

    const projectOnly = loadInstalledSkills("project", { project: projectRoot, global: globalRoot });
    assert.equal(projectOnly.project.size, 1);
    assert.equal(projectOnly.project.has("project-skill"), true);
    assert.equal(projectOnly.global.size, 0);

    const globalOnly = loadInstalledSkills("global", { project: projectRoot, global: globalRoot });
    assert.equal(globalOnly.project.size, 0);
    assert.equal(globalOnly.global.size, 1);
    assert.equal(globalOnly.global.has("global-skill"), true);

    const both = loadInstalledSkills("both", { project: projectRoot, global: globalRoot });
    assert.equal(both.project.size, 1);
    assert.equal(both.global.size, 1);
  });
});
