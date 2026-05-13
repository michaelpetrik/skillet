import test from "node:test";
import assert from "node:assert/strict";

import {
  choosePublicationVersion,
  compareInstalledVersion,
} from "../dist/domain.js";

test("compareInstalledVersion classifies current, outdated, newer, unknown, and different versions", () => {
  assert.deepEqual(compareInstalledVersion("1.2.3", "1.2.3"), {
    state: "current",
    label: "current",
  });
  assert.deepEqual(compareInstalledVersion("1.2.3", "1.2.2"), {
    state: "outdated",
    label: "1.2.2 -> 1.2.3",
  });
  assert.deepEqual(compareInstalledVersion("1.2.3", "1.2.4"), {
    state: "newer",
    label: "1.2.4 > 1.2.3",
  });
  assert.deepEqual(compareInstalledVersion("1.2.3", undefined), {
    state: "unknown",
    label: "unknown -> 1.2.3",
  });
  assert.deepEqual(compareInstalledVersion("latest", "1.2.3"), {
    state: "different",
    label: "1.2.3 -> latest",
  });
});

test("choosePublicationVersion preserves source version for new publishes", () => {
  assert.equal(choosePublicationVersion(undefined, "2.3.4", false, true), "2.3.4");
  assert.equal(choosePublicationVersion(undefined, undefined, false, true), "1.0.0");
});

test("choosePublicationVersion keeps existing version when unchanged", () => {
  assert.equal(choosePublicationVersion("1.2.3", "9.9.9", true, false), "1.2.3");
  assert.equal(choosePublicationVersion(undefined, "2.0.0", true, false), "2.0.0");
});

test("choosePublicationVersion bumps or accepts newer source versions when changed", () => {
  assert.equal(choosePublicationVersion("1.2.3", "1.2.4", true, true), "1.2.4");
  assert.equal(choosePublicationVersion("1.2.3", "1.2.3", true, true), "1.2.4");
  assert.equal(choosePublicationVersion("1.2.3", undefined, true, true), "1.2.4");
});
