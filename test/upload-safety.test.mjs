import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import { uploadSkill } from "../dist/upload.js";

function withFixture(callback) {
  const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), "skillet-upload-safety-"));
  try {
    const repoRoot = path.join(tempRoot, "repo");
    const sourceRoot = path.join(tempRoot, "source-skill");
    fs.mkdirSync(path.join(repoRoot, "skills"), { recursive: true });
    fs.mkdirSync(sourceRoot, { recursive: true });
    fs.writeFileSync(path.join(repoRoot, "skills", "README.md"), "# Skillet Skills\n");
    fs.writeFileSync(
      path.join(sourceRoot, "SKILL.md"),
      "---\nname: source-skill\ndescription: Source skill\nversion: 1.0.0\n---\n# Source Skill\n",
    );

    callback({ repoRoot, sourceRoot });
  } finally {
    fs.rmSync(tempRoot, { recursive: true, force: true });
  }
}

function runUpload(input) {
  return uploadSkill({
    source: input.sourceRoot,
    category: "coding",
    repo: input.repoRoot,
    branch: "main",
    dryRun: input.dryRun,
    keepTemp: false,
    targetName: input.targetName,
    commandRunner: {
      run: () => ({ status: 1, stdout: "", stderr: "no git remote" }),
    },
  });
}

const unsafeTargetNames = [
  ["empty", ""],
  ["dot", "."],
  ["absolute", path.resolve(os.tmpdir(), "escape")],
  ["traversal", "../escape"],
  ["newline", "bad\nname"],
  ["control character", "bad\u0001name"],
];

for (const [label, targetName] of unsafeTargetNames) {
  test(`uploadSkill rejects ${label} target names before live mutations`, () => {
    withFixture(({ repoRoot, sourceRoot }) => {
      assert.throws(
        () => runUpload({ repoRoot, sourceRoot, targetName, dryRun: false }),
        /Invalid target name/,
      );
      assert.deepEqual(fs.readdirSync(path.join(repoRoot, "skills")).sort(), ["README.md"]);
    });
  });
}

test("uploadSkill rejects unsafe target names before dry-run reporting", () => {
  withFixture(({ repoRoot, sourceRoot }) => {
    assert.throws(
      () => runUpload({ repoRoot, sourceRoot, targetName: "../escape", dryRun: true }),
      /Invalid target name/,
    );
  });
});

test("uploadSkill reports canonical targets under the skills root", () => {
  withFixture(({ repoRoot, sourceRoot }) => {
    const result = runUpload({
      repoRoot,
      sourceRoot,
      targetName: "safe-skill",
      dryRun: true,
    });

    const skillsRoot = path.resolve(repoRoot, "skills");
    const relativeToSkills = path.relative(skillsRoot, result.targetRoot);
    assert.equal(result.targetRelativeRoot, "skills/coding/safe-skill");
    assert.equal(path.resolve(result.targetRoot), path.join(skillsRoot, "coding", "safe-skill"));
    assert.equal(relativeToSkills.startsWith(".."), false);
    assert.equal(path.isAbsolute(relativeToSkills), false);
  });
});
