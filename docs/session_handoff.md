# Antigravity IDE Database Sync - Session Handoff

This document contains the complete context, discoveries, deployed fixes, and future diagnostic steps regarding the "Zero History" bug in the Google Antigravity IDE. Provide this file to the next AI Assistant if the conversation history is still failing to display.

## 1. System Architecture & The "Zero History" Bug

The Antigravity IDE persists user conversation history locally in an SQLite database:
`%APPDATA%\antigravity\User\globalStorage\state.vscdb`

It relies on two primary keys in the `ItemTable`:
1.  **`chat.ChatSessionStore.index`**: A JSON string acting as a lightweight surface index (stores title, timestamps, staleness). This directly dictates what the UI sidebar renders.
2.  **`antigravityUnifiedStateSync.trajectorySummaries` (PB_KEY)**: A deeply nested Base64-encoded Protobuf blob containing the core structural logic, step counts, internal tree metadata, and **Workspace URIs**.

### The Root Cause Discovered
The IDE strictly associates conversation history with the currently loaded workspace. When parsing active workspaces, the IDE internally strictly enforces **lowercase Windows drive letters** (e.g., `file:///h%3A/Personal/Programming/...`).

The recovery script `antigravity_recover.py` was directly injecting uppercase user input (e.g., `H:\...` -> `file:///H%3A/...`) into `PB_KEY` Fields 9 and 17. 
Because the injected `H%3A` did not strictly match the IDE's internal `h%3A`, the IDE rejected the entire Protobuf payload, failed to map the workspace, refused to render the UI, and consequently zeroed out the `JSON Index` upon its next graceful exit.

## 2. Deployed Fixes (As of March 2026)

**1. Code Patch**: 
We permanently patched `build_workspace_dict` in `src/core/db_operations.py` (and `src/cli.py`) to systematically intercept and lowercase the drive letter component of Windows absolute paths prior to URI encoding:
```python
import sys
path_normalized = path.replace("\\", "/").rstrip("/")
if sys.platform.startswith("win") and len(path_normalized) >= 2 and path_normalized[1] == ":":
    path_normalized = path_normalized[0].lower() + path_normalized[1:]
```

**2. Database Migration**:
We performed a successful recovery on the database:
1.  Restored the 'before_ws_migrate' snapshot (Backup Index 2) which still possessed the intact 100-entry `JSON Index`.
2.  Executed the modified `migrate` command to inject the lowercase `Ag-Argus` workspace variables.
3.  Ran our `dump_ws.py` inspection script against the live `state.vscdb` to definitively prove the drive letter injected as `h%3A`.

## 3. The "Graceful Exit" Overwrite Danger

The IDE actively caches its memory matrix (the UI state). If you edit `state.vscdb` on disk, but the user currently has the IDE open, closing the IDE normally causes it to seamlessly flush its empty memory *over* the repaired database, obliterating the fix.

To counteract this, the IDE must either be abruptly force-killed (`taskkill /IM antigravity.exe /F`) OR the user must close the IDE, trigger the recovery pipeline scripts offline, and then boot the IDE cleanly.

## 4. Next Steps for Diagnostic AI (If issue persists)

If the user followed the force-kill instructions, booted a clean IDE, and the UI is STILL blank despite the `h%3A` lowercase patch, then the parsing engine is rejecting the Protobuf payload for an alternative reason. 

**Directives for the next AI:**
1.  **Re-verify the JSON Index**: Check if the IDE wiped the JSON Index again. If it is 0, the IDE is still maliciously rejecting the Protobuf fields.
2.  **Deep Protobuf Diff**: Use the provided extraction scripts to dump the `PB_KEY` binary structure of a brand-new, healthy, IDE-generated conversation versus our Python-rebuilt recovered conversation. Look for discrepancies in padding bytes, missing fields, or newly introduced schema properties (like `sync_status` integers or novel UUID formats).
3.  **Investigate `storage.json`**: Check if there are workspace binding references in the global JSON array that mismatch our injected db URIs.
4.  **Check IDE Logs**: Look for trace/debug outputs from the Antigravity internal `ChatSessionStore` indicating precisely *why* it dropped the state serialization.
