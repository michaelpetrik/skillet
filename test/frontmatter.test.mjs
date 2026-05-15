import test from "node:test";
import assert from "node:assert/strict";

import {
  canonicalSkillText,
  extractFrontmatterValue,
  extractH1,
  parseDocument,
  setFrontmatterFields,
} from "../dist/frontmatter.js";

test("parseDocument extracts LF frontmatter", () => {
  const document = parseDocument("---\nname: alpha\n---\n# Alpha\n");
  assert.equal(document.hasFrontmatter, true);
  assert.deepEqual(document.frontmatterLines, ["name: alpha"]);
  assert.equal(document.body, "# Alpha\n");
});

test("parseDocument extracts CRLF frontmatter", () => {
  const document = parseDocument("---\r\nname: alpha\r\n---\r\n# Alpha\r\n");
  assert.equal(document.hasFrontmatter, true);
  assert.deepEqual(document.frontmatterLines, ["name: alpha"]);
  assert.equal(document.body, "# Alpha\r\n");
});

test("parseDocument keeps original text when frontmatter delimiters are incomplete or empty", () => {
  const noOpening = parseDocument("# Alpha\n");
  assert.deepEqual(noOpening, {
    hasFrontmatter: false,
    frontmatterLines: [],
    body: "# Alpha\n",
  });

  const noClosing = parseDocument("---\nname: alpha\n# Alpha\n");
  assert.deepEqual(noClosing, {
    hasFrontmatter: false,
    frontmatterLines: [],
    body: "---\nname: alpha\n# Alpha\n",
  });

  const emptyFrontmatter = parseDocument("---\n---\n# Alpha\n");
  assert.deepEqual(emptyFrontmatter, {
    hasFrontmatter: false,
    frontmatterLines: [],
    body: "---\n---\n# Alpha\n",
  });
});

test("extractFrontmatterValue handles scalar, quoted, folded, and literal values", () => {
  assert.equal(extractFrontmatterValue(["name: 'alpha'"], "name"), "alpha");
  assert.equal(
    extractFrontmatterValue(["description: >", "  first line", "  second line", "category: General"], "description"),
    "first line second line",
  );
  assert.equal(
    extractFrontmatterValue(["description: |", "  first line", "  second line", "category: General"], "description"),
    "first line\nsecond line",
  );
});

test("extractFrontmatterValue supports block chomping indicators and missing keys", () => {
  assert.equal(
    extractFrontmatterValue(["description: >-", "  first line", "  second line", "category: General"], "description"),
    "first line second line",
  );
  assert.equal(
    extractFrontmatterValue(["description: |+", "  first line", "  second line", "category: General"], "description"),
    "first line\nsecond line",
  );
  assert.equal(extractFrontmatterValue(["name: alpha"], "description"), undefined);
});

test("setFrontmatterFields inserts category and version after description", () => {
  assert.deepEqual(
    setFrontmatterFields(["name: alpha", "description: Alpha skill"], "General", "1.2.3"),
    ["name: alpha", "description: Alpha skill", "category: General", "version: 1.2.3"],
  );
});

test("canonicalSkillText ignores category and version only", () => {
  const left = "---\nname: alpha\ndescription: Alpha\ncategory: General\nversion: 1.0.0\n---\n# Alpha\n";
  const right = "---\nname: alpha\ndescription: Alpha\ncategory: Coding\nversion: 9.9.9\n---\n# Alpha\n";
  assert.equal(canonicalSkillText(left), canonicalSkillText(right));
});

test("extractH1 returns the first H1 and ignores other headings", () => {
  assert.equal(extractH1("## Intro\n#  Alpha Skill  \n# Second\n"), "Alpha Skill");
  assert.equal(extractH1("## Intro\n### Details\n"), undefined);
});
