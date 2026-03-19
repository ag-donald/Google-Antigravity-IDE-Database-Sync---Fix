# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.2.0] - 2026-03-19

### Fixed
- **macOS launcher crash**: `run.sh` used GNU-only `grep -oP` which fails on macOS BSD grep — replaced with portable `sed`+`cut`

### Added
- Platform-specific launcher scripts: `run.bat` (Windows CMD), `run.ps1` (PowerShell), `run.sh` (Linux/macOS)
- Modular `src/` package architecture: `constants`, `logger`, `protobuf`, `environment`, `artifacts`, `cli`, `recovery`
- Project Structure section in `CONTRIBUTING.md`

### Changed
- Refactored monolithic script into 7 focused modules for maintainability
- Updated README Architecture section to reflect `src/` package layout
- Updated `CONTRIBUTING.md` syntax validation commands to cover all modules
- Version bumped to 1.2.0

## [1.1.0] - 2026-03-19

### Fixed
- **Missing database keys**: Script no longer dies fatally when `trajectorySummaries` key is missing from database — creates it from scratch instead
- **Silent write failures**: Replaced `UPDATE` statements with `INSERT OR REPLACE` for both Protobuf and JSON index writes, ensuring the script works on completely blank or corrupted databases
- **License reference**: Updated docstring from MIT to Unlicense to match `LICENCE.md`

### Added
- Multi-workspace limitation warning displayed during interactive workspace registration
- SSH remote session guidance in the interactive prompt
- Covers all 11 documented community failure modes (verified against Google AI Dev Forum reports)

### Changed
- Version bumped to 1.1.0

## [1.0.0] - 2026-03-19

### Added
- Initial release of the Antigravity IDE History Recovery Tool
- Cross-platform support (Windows, macOS, Linux)
- Interactive CLI with project workspace registration
- Automatic database backup with timestamped filenames
- Protobuf Wire Type 2 encoder with byte-accurate nested schemas (Fields 9, 17)
- Non-destructive JSON index merge (preserves existing entries)
- Brain artifact title extraction from `task.md`, `implementation_plan.md`, `walkthrough.md`
- Fallback title generation using overview logs and timestamps
- Automatic rollback on database errors via `safe_rollback()` helper
- `--help` and `--version` CLI flags
- Debug mode via `AGMERCIUM_DEBUG=1` environment variable
- Unified `Logger` class with consistent severity tags
- Phase 5 summary statistics table
- Comprehensive README with FAQ, architecture docs, and official bug reporting channels
- LICENCE.md (The Unlicense — public domain)
- CONTRIBUTING.md with code standards and submission guidelines
- SECURITY.md with responsible disclosure policy
