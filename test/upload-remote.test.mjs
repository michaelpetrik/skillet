import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import { uploadSkill } from "../dist/upload.js";

function withFixture(callback) {
  const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), "skillet-upload-remote-"));
  try {
    const sourceRoot = path.join(tempRoot, "source-skill");
    fs.mkdirSync(sourceRoot, { recursive: true });
    fs.writeFileSync(
      path.join(sourceRoot, "SKILL.md"),
      "---\nname: remote-skill\ndescription: Remote skill\nversion: 1.2.3\n---\n# Remote Skill\n",
    );
    fs.writeFileSync(path.join(sourceRoot, "asset.txt"), "asset contents\n");
    callback({ sourceRoot });
  } finally {
    fs.rmSync(tempRoot, { recursive: true, force: true });
  }
}

function seedClonedRepo(repoRoot) {
  fs.mkdirSync(path.join(repoRoot, "skills"), { recursive: true });
  fs.writeFileSync(path.join(repoRoot, "skills", "README.md"), "# Skillet Skills\n");
}

function createRemoteRunner({ statusOutput, commitSha = "deadbeefcafebabe", setupCloneRepo = seedClonedRepo }) {
  const calls = [];
  return {
    calls,
    runner: {
      run(command, args, options = {}) {
        calls.push({ command, args: [...args], options: { ...options } });
        if (command !== "git") {
          return { status: 1, stdout: "", stderr: `unexpected command: ${command}` };
        }
        if (args[0] === "clone") {
          setupCloneRepo(args[args.length - 1]);
          return { status: 0, stdout: "", stderr: "" };
        }
        if (args[0] === "status") {
          return { status: 0, stdout: statusOutput, stderr: "" };
        }
        if (args[0] === "rev-parse") {
          return { status: 0, stdout: `${commitSha}\n`, stderr: "" };
        }
        return { status: 0, stdout: "", stderr: "" };
      },
    },
  };
}

function runRemoteUpload({ sourceRoot, commandRunner }) {
  return uploadSkill({
    source: sourceRoot,
    category: "coding",
    remote: "owner/remote-catalog",
    branch: "main",
    dryRun: false,
    keepTemp: false,
    targetName: "remote-skill",
    commandRunner,
  });
}

test("uploadSkill remote flow short-circuits commit and push when git status is empty", () => {
  withFixture(({ sourceRoot }) => {
    const fake = createRemoteRunner({ statusOutput: "" });
    const result = runRemoteUpload({ sourceRoot, commandRunner: fake.runner });

    assert.equal(result.mode, "remote");
    assert.equal(result.pushed, false);
    assert.equal(result.gitStatus, "");
    assert.equal(result.commitSha, undefined);
    assert.equal(result.noChanges, false);
    assert.deepEqual(
      fake.calls.map((call) => call.args[0]),
      ["clone", "add", "status"],
    );
    assert.deepEqual(fake.calls[1].args, ["add", "-A", "skills/README.md", "skills/coding/remote-skill"]);
    assert.deepEqual(
      fake.calls[2].args,
      ["status", "--short", "--", "skills/README.md", "skills/coding/remote-skill"],
    );
  });
});

test("uploadSkill remote flow commits and pushes when tracked paths change", () => {
  withFixture(({ sourceRoot }) => {
    const fake = createRemoteRunner({
      statusOutput: "M skills/README.md\nA skills/coding/remote-skill/SKILL.md\n",
      commitSha: "0123456789abcdef",
    });
    const result = runRemoteUpload({ sourceRoot, commandRunner: fake.runner });
    const cloneRepoRoot = fake.calls[0].args[fake.calls[0].args.length - 1];

    assert.equal(result.mode, "remote");
    assert.equal(result.pushed, true);
    assert.equal(result.commitSha, "0123456789abcdef");
    assert.equal(
      result.commitMessage,
      "Publish skill remote-skill to skills/coding/remote-skill (v1.2.3)",
    );
    assert.equal(result.gitStatus, "M skills/README.md\nA skills/coding/remote-skill/SKILL.md");
    assert.deepEqual(
      fake.calls.map((call) => call.args[0]),
      ["clone", "add", "status", "commit", "rev-parse", "push"],
    );
    assert.deepEqual(fake.calls[3].args, ["commit", "-m", result.commitMessage]);
    assert.deepEqual(fake.calls[5].args, ["push", "origin", "main"]);
    for (const call of fake.calls.slice(1)) {
      assert.equal(call.options.cwd, cloneRepoRoot);
    }
  });
});
