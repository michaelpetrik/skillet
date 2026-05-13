export interface FrontmatterDocument {
  hasFrontmatter: boolean;
  frontmatterLines: string[];
  body: string;
}

export function parseDocument(text: string): FrontmatterDocument {
  const openingDelimiter = /^---\r?\n/.exec(text);
  if (!openingDelimiter) {
    return {
      hasFrontmatter: false,
      frontmatterLines: [],
      body: text,
    };
  }

  const contentStart = openingDelimiter[0].length;
  const rest = text.slice(contentStart);
  const closingDelimiter = /\r?\n---\r?\n/.exec(rest);
  if (!closingDelimiter || closingDelimiter.index === undefined) {
    return {
      hasFrontmatter: false,
      frontmatterLines: [],
      body: text,
    };
  }

  return {
    hasFrontmatter: true,
    frontmatterLines: rest.slice(0, closingDelimiter.index).split(/\r?\n/),
    body: rest.slice(closingDelimiter.index + closingDelimiter[0].length),
  };
}

export function buildDocument(lines: string[], body: string): string {
  if (lines.length === 0) {
    return body;
  }

  return `---\n${lines.join("\n")}\n---\n${body}`;
}

export function extractFrontmatterValue(lines: string[], key: string): string | undefined {
  const prefix = `${key}:`;

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    if (!line.startsWith(prefix)) {
      continue;
    }

    const rawValue = line.slice(prefix.length).trim();
    if (/^[>|][+-]?$/.test(rawValue)) {
      const blockLines: string[] = [];
      for (let blockIndex = index + 1; blockIndex < lines.length; blockIndex += 1) {
        const blockLine = lines[blockIndex];
        if (/^[A-Za-z0-9_-]+:\s*/.test(blockLine)) {
          break;
        }
        blockLines.push(blockLine.replace(/^\s{1,4}/, ""));
      }

      return rawValue.startsWith(">")
        ? blockLines.join(" ").replace(/\s+/g, " ").trim()
        : blockLines.join("\n").trim();
    }

    return rawValue.replace(/^['"]|['"]$/g, "");
  }

  return undefined;
}

export function setFrontmatterFields(lines: string[], categoryTitle: string, version: string): string[] {
  const result = lines.filter((line) => !/^(category|version):\s*/.test(line));
  let insertAt = result.length;

  const descriptionIndex = result.findIndex((line) => /^description:\s*/.test(line));
  if (descriptionIndex !== -1) {
    insertAt = descriptionIndex + 1;
  }

  result.splice(insertAt, 0, `category: ${categoryTitle}`, `version: ${version}`);
  return result;
}

export function canonicalSkillText(text: string): string {
  const document = parseDocument(text);
  if (!document.hasFrontmatter) {
    return text;
  }

  const filtered = document.frontmatterLines.filter((line) => !/^(category|version):\s*/.test(line));
  return buildDocument(filtered, document.body);
}

export function extractH1(markdown: string): string | undefined {
  for (const line of markdown.split(/\r?\n/)) {
    if (line.startsWith("# ")) {
      return line.slice(2).trim();
    }
  }

  return undefined;
}
