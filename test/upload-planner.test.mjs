import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import { uploadSkill } from "../dist/upload.js";

const fixedClock = () => new Date("2026-02-03T04:05:06.000Z");
const laterClock = () => new Date("2026-02-04T04:05:06.000Z");
const commandRunner = {
  run: () => ({ status: 1, stdout: "", stderr: "no git remote" }),
};

function withFixture(callback) {
  const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), "skillet-upload-planner-"));
  try {
    const repoRoot = path.join(tempRoot, "repo");
    const sourceRoot = path.join(tempRoot, "source-skill");
    fs.mkdirSync(path.join(repoRoot, "skills"), { recursive: true });
    fs.mkdirSync(sourceRoot, { recursive: true });
    fs.writeFileSync(path.join(repoRoot, "skills", "README.md"), "# Skillet Skills\n");
    fs.writeFileSync(
      path.join(sourceRoot, "SKILL.md"),
      "---\nname: planned-skill\ndescription: Planned skill\nversion: 1.2.3\n---\n# Planned Skill\n",
    );
    fs.writeFileSync(path.join(sourceRoot, "asset.txt"), "asset contents\n");

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
    targetName: "planned-skill",
    commandRunner,
    clock: input.clock ?? fixedClock,
  });
}

function withoutDryRun(result) {
  const { dryRun, ...rest } = result;
  return rest;
}

test("uploadSkill derives dry-run and live results from the same planned operations", () => {
  withFixture(({ repoRoot, sourceRoot }) => {
    const dryRun = runUpload({ repoRoot, sourceRoot, dryRun: true });
    assert.equal(fs.existsSync(dryRun.targetRoot), false);

    const live = runUpload({ repoRoot, sourceRoot, dryRun: false });

    assert.deepEqual(withoutDryRun(dryRun), withoutDryRun(live));
    assert.deepEqual(live.filesWritten, [
      "skills/coding/planned-skill/asset.txt",
      "skills/coding/planned-skill/SKILL.md",
      "skills/coding/planned-skill/CHANGELOG.md",
      "skills/README.md",
    ]);
    assert.deepEqual(live.filesRemoved, []);
    assert.equal(live.changelogUpdated, true);
    assert.match(
      fs.readFileSync(path.join(live.targetRoot, "CHANGELOG.md"), "utf8"),
      /^## \[1\.2\.3] - 2026-02-03/m,
    );
  });
});

test("uploadSkill does not duplicate CHANGELOG entries when the plan has no content changes", () => {
  withFixture(({ repoRoot, sourceRoot }) => {
    const first = runUpload({ repoRoot, sourceRoot, dryRun: false, clock: fixedClock });
    const second = runUpload({ repoRoot, sourceRoot, dryRun: false, clock: laterClock });

    assert.equal(first.changelogUpdated, true);
    assert.equal(second.noChanges, true);
    assert.equal(second.changelogUpdated, false);
    assert.deepEqual(second.filesWritten, []);

    const changelog = fs.readFileSync(path.join(first.targetRoot, "CHANGELOG.md"), "utf8");
    assert.equal([...changelog.matchAll(/^## \[/gm)].length, 1);
    assert.match(changelog, /^## \[1\.2\.3] - 2026-02-03/m);
    assert.doesNotMatch(changelog, /2026-02-04/);
  });
});
