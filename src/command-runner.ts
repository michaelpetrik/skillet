import { spawnSync } from "node:child_process";
import { Runner, formatCommand } from "./domain.js";

export interface CommandRunOptions {
  cwd?: string;
  stdio?: "inherit" | "pipe";
}

export interface CommandRunResult {
  status: number | null;
  stdout: string;
  stderr: string;
  error?: Error;
}

export interface CommandRunner {
  run(command: string, args: readonly string[], options?: CommandRunOptions): CommandRunResult;
}

export interface SkillsAddCommand {
  command: Runner;
  args: string[];
}

export const nodeCommandRunner: CommandRunner = {
  run(command: string, args: readonly string[], options: CommandRunOptions = {}): CommandRunResult {
    const result = spawnSync(command, [...args], {
      cwd: options.cwd,
      encoding: "utf8",
      stdio: options.stdio || "pipe",
    });

    return {
      status: result.status,
      stdout: commandOutput(result.stdout),
      stderr: commandOutput(result.stderr),
      error: result.error,
    };
  },
};

export function buildSkillsAddCommand(input: {
  runner: Runner;
  repo: string;
  skillName: string;
  global: boolean;
}): SkillsAddCommand {
  const args = input.runner === "npx" ? ["-y", "skills", "add", input.repo] : ["skills", "add", input.repo];
  args.push("--skill", input.skillName);
  if (input.global) {
    args.push("-g", "-y");
  } else {
    args.push("-y");
  }
  return { command: input.runner, args };
}

export function runSkillsAddCommand(input: {
  runner: Runner;
  repo: string;
  skillName: string;
  global: boolean;
  dryRun: boolean;
  commandRunner?: CommandRunner;
  writeLine?: (line: string) => void;
}): void {
  const { command, args } = buildSkillsAddCommand(input);
  const writeLine = input.writeLine || console.log;
  writeLine(formatCommand(command, args));

  if (input.dryRun) {
    return;
  }

  const result = (input.commandRunner || nodeCommandRunner).run(command, args, {
    stdio: "inherit",
  });

  if (result.status !== 0) {
    const detail = result.error ? `: ${result.error.message}` : "";
    throw new Error(`${command} exited with status ${result.status ?? "unknown"}${detail}.`);
  }
}

export function runGitCommand(
  args: readonly string[],
  options: { cwd: string; commandRunner?: CommandRunner; throwOnError: true },
): { ok: true; stdout: string; stderr: string };
export function runGitCommand(
  args: readonly string[],
  options: { cwd: string; commandRunner?: CommandRunner; throwOnError: false },
): { ok: boolean; stdout: string; stderr: string };
export function runGitCommand(
  args: readonly string[],
  options: { cwd: string; commandRunner?: CommandRunner; throwOnError: boolean },
): { ok: boolean; stdout: string; stderr: string } {
  const result = (options.commandRunner || nodeCommandRunner).run("git", args, {
    cwd: options.cwd,
  });
  const ok = result.status === 0;

  if (!ok && options.throwOnError) {
    throw new Error(
      [
        `git command failed: ${formatCommand("git", [...args])}`,
        `cwd: ${options.cwd}`,
        result.stdout ? `stdout:\n${result.stdout}` : undefined,
        result.stderr ? `stderr:\n${result.stderr}` : undefined,
        result.error ? `error: ${result.error.message}` : undefined,
      ]
        .filter(Boolean)
        .join("\n"),
    );
  }

  return { ok, stdout: result.stdout, stderr: result.stderr };
}

function commandOutput(value: string | Buffer | null): string {
  if (!value) {
    return "";
  }
  return typeof value === "string" ? value : value.toString("utf8");
}
