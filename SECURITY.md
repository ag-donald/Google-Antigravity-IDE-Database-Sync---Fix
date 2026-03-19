# Security Policy

## Scope

This tool operates **entirely offline** on local files. It:
- Makes **no network requests** of any kind
- Reads only from `~/.gemini/antigravity/` (conversations, brain artifacts)
- Writes only to the IDE's `state.vscdb` SQLite database
- Creates a timestamped backup before any modifications

## Reporting a Vulnerability

If you discover a security vulnerability in this tool, please report it responsibly:

1. **Do not open a public issue.**
2. Email the maintainer directly at: **security@agmercium.com**
3. Include:
   - A clear description of the vulnerability
   - Steps to reproduce
   - Potential impact
4. You will receive a response within 48 hours.

## Known Risks

This tool intentionally modifies the Antigravity IDE's SQLite database. While automatic backups are created, users should be aware that:

- Running the tool while the IDE is open may result in the IDE overwriting the patched database
- Corrupt `.pb` files could theoretically produce malformed index entries (the tool handles this gracefully)
- The tool requires read/write access to the database file, which is a normal user-level permission

## Dependencies

This tool uses **only Python standard library modules** and has zero external dependencies, eliminating supply-chain attack vectors.
