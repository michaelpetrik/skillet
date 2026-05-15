import test from "node:test";
import assert from "node:assert/strict";
import os from "node:os";
import path from "node:path";

import {
  expandHome,
  resolveCatalogRoot,
  resolveGlobalSkillsRoot,
  resolvePath,
} from "../dist/paths.js";

function withEnv(overrides, callback) {
  const previous = {};
  for (const key of Object.keys(overrides)) {
    previous[key] = process.env[key];
    const value = overrides[key];
    if (value === undefined) {
      delete process.env[key];
    } else {
      process.env[key] = value;
    }
  }

  try {
    callback();
  } finally {
    for (const key of Object.keys(overrides)) {
      const value = previous[key];
      if (value === undefined) {
        delete process.env[key];
      } else {
        process.env[key] = value;
      }
    }
  }
}

test("expandHome expands tilde-only and tilde-prefix paths", () => {
  assert.equal(expandHome("~"), os.homedir());
  assert.equal(expandHome("~/skills/demo"), path.join(os.homedir(), "skills", "demo"));
  assert.equal(expandHome("relative/path"), "relative/path");
});

test("resolvePath expands home before resolving against base path", () => {
  const base = path.join(path.sep, "workspace", "repo");
  assert.equal(resolvePath("skills/demo", base), path.resolve(base, "skills/demo"));
  assert.equal(resolvePath("~/skills/demo", base), path.join(os.homedir(), "skills", "demo"));
});

test("resolveCatalogRoot prefers explicit argument over SKILLET_ROOT", () => {
  withEnv({ SKILLET_ROOT: path.join(path.sep, "env", "catalog") }, () => {
    const explicit = path.join(path.sep, "explicit", "catalog");
    assert.equal(resolveCatalogRoot(explicit), path.resolve(explicit));
  });
});

test("resolveCatalogRoot uses SKILLET_ROOT when explicit argument is missing", () => {
  withEnv({ SKILLET_ROOT: path.join(path.sep, "env", "catalog") }, () => {
    assert.equal(resolveCatalogRoot(undefined), path.resolve(path.join(path.sep, "env", "catalog")));
  });
});

test("resolveGlobalSkillsRoot prefers explicit argument over AGENTS_HOME", () => {
  withEnv({ AGENTS_HOME: path.join(path.sep, "env", ".agents") }, () => {
    const explicit = path.join(path.sep, "custom", "global-skills");
    assert.equal(resolveGlobalSkillsRoot(explicit), path.resolve(explicit));
  });
});

test("resolveGlobalSkillsRoot uses AGENTS_HOME when explicit argument is missing", () => {
  withEnv({ AGENTS_HOME: path.join(path.sep, "env", ".agents") }, () => {
    assert.equal(
      resolveGlobalSkillsRoot(undefined),
      path.join(path.resolve(path.join(path.sep, "env", ".agents")), "skills"),
    );
  });
});
