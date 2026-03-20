# Antigravity IDE Database Sync - Session Handoff v2

This document contains the complete context, discoveries, deployed fixes, and future diagnostic steps regarding the "Zero History" bug in the Google Antigravity IDE. Provide this file to the next AI Assistant if the conversation history is **still** failing to display despite the efforts of two previous AI sessions.

## 1. System Architecture & The "Zero History" Bug

The Antigravity IDE persists user conversation history locally in an SQLite database:
`%APPDATA%\antigravity\User\globalStorage\state.vscdb`

It relies on two primary keys in the `ItemTable`:
1.  **`chat.ChatSessionStore.index`**: A JSON string acting as a lightweight surface index (stores title, timestamps, staleness). This directly dictates what the UI sidebar renders.
2.  **`antigravityUnifiedStateSync.trajectorySummaries` (PB_KEY)**: A deeply nested Base64-encoded Protobuf blob containing the core structural logic, step counts, internal tree metadata, and **Workspace URIs**.

### The Root Causes Addressed Thus Far
1. **Windows Path Casing**: The IDE strictly requires **lowercase Windows drive letters** (e.g., `file:///h%3A/...`) for workspace validation, which we fixed using a Python normalization patch.
2. **Canonical Protobuf Tag Ordering**: The IDE uses an extremely strict Protobuf parser. The initial recovery script was appending `Field 9` and `Field 17` at the end of the byte array (making `Field 9` follow `Field 16`). We fixed this by rewriting the Python Protobuf encoding engine (`src/protobuf.py`) to fully parse the inner blob, inject new fields, mathematically sort all fields ascending by their tag number, and restitch the encoding. Our `golden_build.py` suite validated this.

## 2. Next Steps for Diagnostic AI (If issue persists)

If the user followed the force-kill instructions, booted a clean IDE with the new `state.vscdb.golden_build` injected, and the UI is STILL reverting the JSON Index to `0`, then the parsing engine is silently rejecting the Protobuf payload for an even more obscure reason.

**Directives for the next AI:**
1.  **Check Developer Trace / IDE Logs**: The most critical lacking piece of context so far is the actual error thrown by the Antigravity `ChatSessionStore`. Instruct the user on how to obtain the IDE's core extension logs (e.g. from `%APPDATA%\antigravity\logs\` or from the IDE's Developer Tools Console) to find the exact exception text.
2.  **Missing Field Dependency (e.g., Field 8)**: During deep Protobuf analysis, we noticed the IDE's pristine blobs occasionally contained `Field 8 (Length 0): Empty String`. Our rebuilt script currently ignores or strips fields it doesn't recognize. Validate if Antigravity *requires* `Field 8` to exist, even if empty.
3.  **JSON Index / Protobuf Synchronization**: Double-check `chat.ChatSessionStore.index`. Are the `version` parameters matched? Does the JSON array contain staleness properties that conflict with the `Status: ACTIVE` (Field 5) flag in the Protobuf? 
4.  **Novel UUIDs or Schema Changes**: The UUID generation matches length (36), but ensure the IDE hasn't migrated to a newer binary format or additional field signatures (like `sync_status` integers) that we inadvertently failed to mock in `antigravity_recover.py`.
5.  **Examine `.pb` Backup Files**: The raw Protobuf payloads used to rebuild the history are loaded from `.pb` files in `.gemini\antigravity\conversations`. Use `recursive_pb_dump.py` inside `.agents\tmp\scripts` to ensure the disk files themselves haven't suffered bit-rot or schema structural rot prior to being injected into SQLite.
