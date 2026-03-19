# Antigravity IDE — Conversation History Recovery Tool

<p align="center">
  <strong>An unofficial, open-source workaround for the Google Antigravity IDE conversation history loss bug.</strong>
</p>

<p align="center">
  <a href="#quickstart">Quickstart</a> •
  <a href="#the-bug">The Bug</a> •
  <a href="#how-it-works">How It Works</a> •
  <a href="#compatibility">Compatibility</a> •
  <a href="#faq">FAQ</a> •
  <a href="#contributing">Contributing</a> •
  <a href="#license">License</a>
</p>

---

## The Bug

Google Antigravity IDE (a heavily modified VS Code fork powering agent-first AI development) has a recurring bug where **all conversation history disappears** from the UI sidebar after:

- Updating the IDE to a new version
- Restarting the application
- Certain shutdown sequences

The underlying `.pb` conversation data files remain **fully intact** on disk at `~/.gemini/antigravity/conversations/`, but the IDE's internal SQLite database (`state.vscdb`) loses its UI index mappings, causing the sidebar to display zero history.

This bug has been reported across multiple platforms:
- [Google Developer Forums](https://google.dev) — multiple threads
- [Reddit r/GoogleAntigravity](https://reddit.com) — widely discussed
- In-app bug reports via **Report Issue** (under profile icon)

**This tool rebuilds those internal indices from your intact `.pb` files, restoring your full conversation history.**

---

## Quickstart

### Prerequisites

- **Python 3.7+** (ships with most operating systems)
- **No external dependencies** — standard library only

### Steps

```bash
# 1. Close Antigravity IDE completely (mandatory!)

# 2. Download and run the recovery script
python antigravity_recover.py

# 3. Follow the interactive prompts

# 4. Reopen Antigravity IDE — your history is back!
```

> **⚠️ Important:** The IDE **must** be fully closed before running this tool. If the IDE is running, it will overwrite the patched database when it shuts down.

---

## How It Works

The Antigravity IDE stores conversation history in two parallel indices inside its SQLite database (`state.vscdb`):

| Index | Format | Key |
|-------|--------|-----|
| **Trajectory Summaries** | Base64-encoded Protobuf | `antigravityUnifiedStateSync.trajectorySummaries` |
| **Session Store** | JSON | `chat.ChatSessionStore.index` |

When the bug occurs, one or both of these indices lose their entries, even though the raw `.pb` conversation files remain on disk.

This tool:

1. **Discovers** all local `.pb` conversation files in `~/.gemini/antigravity/conversations/`
2. **Extracts titles** from brain artifacts (`task.md`, `implementation_plan.md`, `walkthrough.md`)
3. **Synthesizes** Protobuf entries with byte-accurate Wire Type 2 nested schemas (Fields 9 and 17)
4. **Merges** new entries into the existing indices without destroying cloud-only conversations
5. **Backs up** the database before any modifications (automatic, timestamped backup)
6. **Rolls back** automatically if any error occurs during the injection process

### Architecture

```
antigravity_recover.py
├── Logger              — Unified, severity-tagged console output
├── ProtobufEncoder     — Deterministic Protobuf Wire Format encoder
├── EnvironmentResolver — Cross-platform path discovery (Win/Mac/Linux)
├── ArtifactParser      — Brain artifact title extraction
├── prompt_workspace()  — Interactive CLI for project registration
├── safe_rollback()     — Fault-tolerant database restoration
└── main()              — 5-phase orchestration pipeline
```

### Execution Phases

| Phase | Description |
|-------|-------------|
| **1. Pre-flight Checks** | Verifies IDE is closed, database exists, permissions are correct |
| **2. Conversation Discovery** | Scans for `.pb` files and counts recoverable conversations |
| **3. Secure Backup** | Creates a timestamped copy of `state.vscdb` before any writes |
| **4. Database Injection** | Synthesizes Protobuf + JSON entries and commits to SQLite |
| **5. Summary Report** | Displays statistics: injected, skipped, total |

---

## Compatibility

| Platform | Database Path | Status |
|----------|---------------|--------|
| **Windows** | `%APPDATA%\antigravity\User\globalStorage\state.vscdb` | ✅ Tested |
| **macOS** | `~/Library/Application Support/antigravity/User/globalStorage/state.vscdb` | ✅ Supported |
| **Linux** | `~/.config/antigravity/User/globalStorage/state.vscdb` | ✅ Supported |

- **Python**: 3.7, 3.8, 3.9, 3.10, 3.11, 3.12, 3.13+
- **Dependencies**: None (uses only Python standard library)

---

## CLI Options

```bash
python antigravity_recover.py          # Interactive recovery
python antigravity_recover.py --help   # Display help documentation
python antigravity_recover.py --version # Display version number
```

### Debug Mode

Set the environment variable `AGMERCIUM_DEBUG=1` to enable verbose debug logging:

```bash
# Linux/macOS
AGMERCIUM_DEBUG=1 python antigravity_recover.py

# Windows (PowerShell)
$env:AGMERCIUM_DEBUG = "1"; python antigravity_recover.py
```

---

## Safety Guarantees

- **Automatic backup**: A timestamped copy of your database is created before any writes.
- **Non-destructive merge**: Existing index entries are preserved; only missing entries are injected.
- **Automatic rollback**: If any database error occurs, the backup is restored immediately.
- **Read-only on `.pb` files**: Your conversation data files are never modified.
- **No network access**: This tool operates entirely offline — zero external requests.

---

## Backup & Undo

After running the tool, your original database backup is preserved at:

```
<database_path>.agmercium_recovery_<timestamp>
```

To undo the recovery, simply copy the backup file over your `state.vscdb`:

```bash
# Example (Windows PowerShell)
Copy-Item "state.vscdb.agmercium_recovery_1710820594" -Destination "state.vscdb" -Force

# Example (Linux/macOS)
cp state.vscdb.agmercium_recovery_1710820594 state.vscdb
```

---

## FAQ

### Q: Will I lose any existing history?
**No.** The tool only *adds* missing entries. It never removes or overwrites existing index entries.

### Q: What if I have conversations from multiple projects?
Run the tool once per project. Each run will prompt you for the project workspace path.

### Q: Can I run this while the IDE is open?
**No.** The IDE will overwrite the database when it shuts down. You must close it first.

### Q: What if the tool crashes mid-run?
The automatic backup is created before any writes. Your database will be intact. You can also restore from the backup file manually.

### Q: Will the conversation titles be correct?
**Yes.** The tool extracts titles from your brain artifacts (`task.md`, `implementation_plan.md`, `walkthrough.md`). If no artifacts exist for a conversation, a clean timestamp-based title is generated (e.g., `Conversation (Mar 19) a1b2c3d4`).

---

## Reporting the Bug to Google

If you've been affected by this bug, please help the community by reporting it to Google through the official channels:

1. **In-App (Recommended)**: Click your profile icon → **Report Issue**
2. **In-App (Agent Manager)**: Click **Provide Feedback** in the bottom-left corner
3. **Google Developer Forums**: Post in the Antigravity IDE section at [google.dev](https://google.dev)
4. **Google Bug Hunters**: For security-related issues, visit [bughunters.google.com](https://bughunters.google.com)
5. **Support Tickets**: Visit the [Antigravity Support Center](https://antigravityide.help) for direct ticket submission

When reporting, include:
- Your OS and Antigravity IDE version
- Whether the history loss occurred after an update, restart, or crash
- The number of conversations affected

---

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## Disclaimer

This is an **unofficial** community tool. It is **not** affiliated with, endorsed by, or supported by Google LLC or the Antigravity IDE team. Use at your own discretion. The tool creates automatic backups before any modifications to minimize risk.

---

## License

This project is licensed under **The Unlicense** — dedicated to the public domain. See [LICENCE.md](LICENCE.md) for the full text.

You are free to copy, modify, distribute, and use this software for any purpose, commercial or non-commercial, without any restrictions whatsoever.

---

<p align="center">
  Made with ❤️ by <a href="https://agmercium.com">Donald R. Johnson</a> at <a href="https://agmercium.com">Agmercium</a>
</p>
