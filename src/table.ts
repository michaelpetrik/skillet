export function renderTable(rows: string[][]): string {
  if (rows.length === 0) {
    return "";
  }

  const widths = rows[0].map((_, columnIndex) =>
    Math.max(...rows.map((row) => (row[columnIndex] ?? "").length)),
  );

  return rows
    .map((row, rowIndex) => {
      const rendered = row
        .map((cell, columnIndex) => {
          const value = cell ?? "";
          if (columnIndex === row.length - 1) {
            return value;
          }
          return value.padEnd(widths[columnIndex]);
        })
        .join("  ")
        .trimEnd();

      if (rowIndex === 0) {
        const divider = widths.map((width) => "-".repeat(width)).join("  ");
        return `${rendered}\n${divider}`;
      }

      return rendered;
    })
    .join("\n");
}
