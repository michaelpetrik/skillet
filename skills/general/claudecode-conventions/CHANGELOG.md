# Changelog

All notable changes to this skill are documented in this file.

The format is based on Keep a Changelog and this project uses Semantic Versioning.

## [1.2.1] - 2026-03-04
### Changed
- Added explicit precondition validation that `AGENTS.md` must exist before any `CLAUDE.md` migration step.
- Clarified rule migration behavior to merge actionable rules without duplication.
- Added deterministic symlink capability detection using a temporary symlink in the same directory.
- Added fallback-on-failure behavior when symlink replacement fails for any reason.
- Added explicit postcondition verification for both valid end states:
  - `CLAUDE.md` is a symlink resolving to `AGENTS.md`, or
  - `CLAUDE.md` is a regular file containing exactly `@AGENTS.md`.

## [1.2.0] - 2026-03-04
### Changed
- Updated the `CLAUDE.md` handling workflow to test symlink support first.
- When symlinks are available, the workflow now deletes `CLAUDE.md` and creates a symlink to `AGENTS.md`.
- When symlinks are unavailable, the workflow falls back to a plain `CLAUDE.md` containing exactly `@AGENTS.md`.

## [1.1.0] - 2026-03-04
### Changed
- Renamed the skill identifier to `claudecode-conventions` in `SKILL.md` so `--skill claudecode-conventions` matches during install.
- Updated the `CLAUDE.md` reset content to the canonical single line: `@AGENTS.md`.
- Added explicit versioning metadata to `SKILL.md`.
- Recorded changelog history for the skill.

## [1.0.0] - 2026-03-02
### Added
- Initial release of the "Claude Code Conventions" skill.
