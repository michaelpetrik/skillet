import test from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";

const cli = new URL("../dist/cli.js", import.meta.url);

function runCli(args) {
  return spawnSync(process.execPath, [cli.pathname, ...args], {
    encoding: "utf8",
  });
}

test("unknown long options fail before command execution", () => {
  const result = runCli(["list", "--dryrun"]);
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /Unknown option: --dryrun/);
});

test("missing values for value options fail fast", () => {
  const missingScope = runCli(["list", "--scope"]);
  assert.notEqual(missingScope.status, 0);
  assert.match(missingScope.stderr, /Missing value for --scope/);

  const missingRepo = runCli(["upload", "--repo", "--dry-run"]);
  assert.notEqual(missingRepo.status, 0);
  assert.match(missingRepo.stderr, /Missing value for --repo/);
});

test("flag options reject explicit values", () => {
  const result = runCli(["list", "--json=true"]);
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /Option --json does not accept a value/);
});

test("unknown commands produce a dedicated command error", () => {
  const result = runCli(["does-not-exist"]);
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /Unknown command: does-not-exist/);
});

test("invalid enum values are rejected by command validators", () => {
  const invalidScope = runCli(["list", "--scope", "workspace"]);
  assert.notEqual(invalidScope.status, 0);
  assert.match(invalidScope.stderr, /Invalid scope: workspace\. Expected project, global, or both/);

  const invalidRunner = runCli(["install", "all", "--runner", "pnpm"]);
  assert.notEqual(invalidRunner.status, 0);
  assert.match(invalidRunner.stderr, /Invalid runner: pnpm\. Expected npx or bunx/);
});

test("known help flag still works", () => {
  const result = runCli(["list", "--help"]);
  assert.equal(result.status, 0);
  assert.match(result.stdout, /List Skillet catalog skills/);
});

test("command aliases resolve through shared help metadata", () => {
  const result = runCli(["help", "ls"]);
  assert.equal(result.status, 0);
  assert.match(result.stdout, /Usage:\n  skillet list \[options\]/);
});

test("publish alias resolves through shared help metadata", () => {
  const result = runCli(["help", "publish"]);
  assert.equal(result.status, 0);
  assert.match(result.stdout, /Usage:\n  skillet upload <source-dir\|SKILL\.md> <category> \[options\]/);
});

test("metadata-backed option parsing accepts command options before help", () => {
  const result = runCli(["upload", "--target-name", "demo-skill", "--help"]);
  assert.equal(result.status, 0);
  assert.match(result.stdout, /--target-name <name>/);
});
