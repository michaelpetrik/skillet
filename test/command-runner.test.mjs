import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import {
  buildSkillsAddCommand,
  runGitCommand,
  runSkillsAddCommand,
} from "../dist/command-runner.js";
import { uploadSkill } from "../dist/upload.js";

function fakeRunner(results = [{ status: 0, stdout: "", stderr: "" }]) {
  const calls = [];
  let index = 0;
  return {
    calls,
    runner: {
      run(command, args, options = {}) {
        calls.push({ command, args: [...args], options: { ...options } });
        const result = results[index] || { status: 0, stdout: "", stderr: "" };
        index += 1;
        return result;
      },
    },
  };
}

test("buildSkillsAddCommand preserves npx and bunx argument vectors", () => {
  assert.deepEqual(buildSkillsAddCommand({ runner: "npx", repo: "owner/repo", skillName: "alpha", global: false }), {
    command: "npx",
    args: ["-y", "skills", "add", "owner/repo", "--skill", "alpha", "-y"],
  });
  assert.deepEqual(buildSkillsAddCommand({ runner: "bunx", repo: "owner/repo", skillName: "alpha", global: true }), {
    command: "bunx",
    args: ["skills", "add", "owner/repo", "--skill", "alpha", "-g", "-y"],
  });
});

test("runSkillsAddCommand passes raw arguments to the injected runner", () => {
  const repo = "owner/repo with spaces; echo nope";
  const skillName = "alpha beta";
  const fake = fakeRunner();
  const lines = [];

  runSkillsAddCommand({
    runner: "npx",
    repo,
    skillName,
    global: true,
    dryRun: false,
    commandRunner: fake.runner,
    writeLine: (line) => lines.push(line),
  });

  assert.deepEqual(fake.calls, [
    {
      command: "npx",
      args: ["-y", "skills", "add", repo, "--skill", skillName, "-g", "-y"],
      options: { stdio: "inherit" },
    },
  ]);
  assert.equal(lines.length, 1);
});

test("runSkillsAddCommand supports dry-run and surfaces runner failures", () => {
  const dryRun = fakeRunner();
  runSkillsAddCommand({
    runner: "bunx",
    repo: "owner/repo",
    skillName: "alpha",
    global: false,
    dryRun: true,
    commandRunner: dryRun.runner,
    writeLine: () => {},
  });
  assert.deepEqual(dryRun.calls, []);

  const failure = fakeRunner([{ status: 7, stdout: "", stderr: "failed" }]);
  assert.throws(
    () =>
      runSkillsAddCommand({
        runner: "npx",
        repo: "owner/repo",
        skillName: "alpha",
        global: false,
        dryRun: false,
        commandRunner: failure.runner,
        writeLine: () => {},
      }),
    /npx exited with status 7/,
  );
});

test("runGitCommand passes Git arguments as arrays and handles non-throwing failures", () => {
  const fake = fakeRunner([{ status: 1, stdout: "", stderr: "not a git repository" }]);
  const result = runGitCommand(["remote", "get-url", "origin"], {
    cwd: "/tmp/work tree",
    commandRunner: fake.runner,
    throwOnError: false,
  });

  assert.deepEqual(result, { ok: false, stdout: "", stderr: "not a git repository" });
  assert.deepEqual(fake.calls, [
    {
      command: "git",
      args: ["remote", "get-url", "origin"],
      options: { cwd: "/tmp/work tree" },
    },
  ]);
});

test("runGitCommand includes command, cwd, and stderr when throwing", () => {
  const fake = fakeRunner([{ status: 128, stdout: "", stderr: "push rejected" }]);

  assert.throws(
    () =>
      runGitCommand(["push", "origin", "main"], {
        cwd: "/tmp/repo",
        commandRunner: fake.runner,
        throwOnError: true,
      }),
    /git command failed: git push origin main[\s\S]*cwd: \/tmp\/repo[\s\S]*stderr:\npush rejected/,
  );
});

test("uploadSkill uses the injected Git runner for local repository metadata", () => {
  const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), "skillet-command-runner-"));
  try {
    const repoRoot = path.join(tempRoot, "repo");
    const sourceRoot = path.join(tempRoot, "source");
    fs.mkdirSync(path.join(repoRoot, "skills"), { recursive: true });
    fs.mkdirSync(sourceRoot, { recursive: true });
    fs.writeFileSync(path.join(repoRoot, "skills", "README.md"), "# Skillet Skills\n");
    fs.writeFileSync(
      path.join(sourceRoot, "SKILL.md"),
      "---\nname: alpha\ndescription: Alpha skill\nversion: 1.0.0\n---\n# Alpha\n",
    );

    const fake = fakeRunner([{ status: 0, stdout: "git@github.com:owner/custom.git\n", stderr: "" }]);
    const result = uploadSkill({
      source: sourceRoot,
      category: "coding",
      repo: repoRoot,
      branch: "main",
      dryRun: true,
      keepTemp: false,
      commandRunner: fake.runner,
    });

    assert.equal(result.installRepoSlug, "owner/custom");
    assert.deepEqual(fake.calls, [
      {
        command: "git",
        args: ["remote", "get-url", "origin"],
        options: { cwd: repoRoot },
      },
    ]);
  } finally {
    fs.rmSync(tempRoot, { recursive: true, force: true });
  }
});
