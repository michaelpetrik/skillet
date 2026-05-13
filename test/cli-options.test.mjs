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

test("flag options reject explicit values", () => {
  const result = runCli(["list", "--json=true"]);
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /Option --json does not accept a value/);
});

test("known help flag still works", () => {
  const result = runCli(["list", "--help"]);
  assert.equal(result.status, 0);
  assert.match(result.stdout, /List Skillet catalog skills/);
});
