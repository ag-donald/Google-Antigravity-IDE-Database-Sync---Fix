# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
