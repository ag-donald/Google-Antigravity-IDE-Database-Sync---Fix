# Google Antigravity IDE Database & Synchronisation Architecture

## 1. Introduction
The Google Antigravity IDE relies on a local SQLite database to persist core operational state, chat sessions, and AI context boundaries. This document outlines the deep mechanics of its primary storage mechanisms, specifically focusing on the synchronization of conversation history and workspace bindings.

## 2. Global Storage Structure (`state.vscdb`)

Like its upstream origins (VS Code / Cursor), Antigravity IDE stores global session state in a SQLite file named `state.vscdb`. This file can be found in the user-level global storage directory:
- **Windows**: `%APPDATA%\antigravity\User\globalStorage\state.vscdb`
- **macOS**: `~/Library/Application Support/antigravity/User/globalStorage/state.vscdb`
- **Linux**: `~/.config/antigravity/User/globalStorage/state.vscdb`

The database schema is extremely simple:
```sql
CREATE TABLE ItemTable (key TEXT PRIMARY KEY, value TEXT);
```

### 2.1 The Two Pillars of State Storage
The history and AI behavior rely on two master keys inside `ItemTable`:

1.  **JSON Metadata (`chat.ChatSessionStore.index`)**: 
    A lightweight, rapidly parseable JSON string managing the "surface level" metadata of conversations (titles, modified timestamps, staleness flags). This index dictates what populates the UI's sidebar list initially.

2.  **Protobuf Data (`antigravityUnifiedStateSync.trajectorySummaries`)**: 
    A complex, tightly-packed binary Base64 blob containing the deep state: workspace URIs, step counts, internal tree mappings, and detailed hierarchical state that grounds the AI to a specific project. 

## 3. Deep Analysis of Protobuf `trajectorySummaries`

The `PB_KEY` ("antigravityUnifiedStateSync.trajectorySummaries") contains a Protobuf Wire format payload wrapped in Base64. When unrolled, it defines a series of deeply nested hierarchical sub-messages.

### Protobuf Wire Schema Overview
The storage mechanism utilizes:
*   **Wire Type 0 (Varint)**: Integers, Booleans, Enums
*   **Wire Type 2 (Length-Delimited)**: Strings, embedded sub-messages (like Field 9 and Field 17)

### Protobuf Field Map for a Standard Entry

For a single conversation entry, the schema decomposes into:
*   **Field 1 (String)**: Title (`Conversation (Date) UUID`)
*   **Field 2 (Varint)**: Step count (number of turns / trajectories)
*   **Field 3 (Embedded Timestamp)**: Create time
*   **Field 4 (String)**: Parent session UUID
*   **Field 5 (Varint)**: Active Status
*   **Field 7 (Embedded Timestamp)**: Modified time
*   **Field 9 (Embedded Message)**: The core Workspace Hint.
    *   **Field 1 (String)**: URI encoded path (e.g. `file:///c%3A/Users/donro/...`)
    *   **Field 2 (String)**: URI encoded path
    *   **Field 3 (Embedded Message)**: Corpus and Git remotes
    *   **Field 4 (String)**: Branch target
*   **Field 10 (Embedded Timestamp)**: Last interaction time
*   **Field 15 (String)**: Unknown / Reserved padding
*   **Field 16 (Varint)**: Sync Status Code
*   **Field 17 (Embedded Message)**: Workspace parameters and session identifiers

---

## 4. Workspaces and the "Zero History" Bug

### 4.1 Strict URI Parsing
The Antigravity IDE strictly binds conversation histories to specific Workspace URIs. When the IDE opens a directory, it queries its internal state for conversations mapped structurally to that exact folder path. 

**Critical Windows Idiosyncrasy**: 
VS Code and upstream variants inherently enforce **lowercase drive letters** during internal path resolution (e.g., `file:///c%3A/Users/...` instead of `file:///C%3A/Users/...`). 

### 4.2 The Genesis of the Desync
During external recovery operations using the `antigravity_recover.py` script, the `build_workspace_dict` functionality dynamically binds raw paths directly through `urllib.parse.quote`. 
```python
# Flawed implementation
uri_path_encoded = urllib.parse.quote(path_normalized, safe="/")
uri_encoded = f"file:///{uri_path_encoded}"
```
If a user provided the absolute path `C:\Users\donro\OneDrive\...`, the system embedded `file:///C%3A/...` deep inside the Protobuf blob at Field 9 and Field 17. 

When the IDE started, its internal validation engine mismatched `file:///C%3A/...` (from PB payload) against its active session `file:///c%3A/...` (from active memory). Assuming the data to be either corrupted or irrelevant to the mapped workspace context, the IDE dropped the UI components entirely, resulting in "ZERO Conversation History". 
In some strict parsing scenarios, rejection of the Protobuf leads to subsequent flushing or invalidation of the corresponding JSON metadata.

### 4.3 The Final Fix
To guarantee enterprise-grade recovery alignment:
1.  All Windows absolute paths must have their initial drive letter intercepted and forced into lowercase (`c:/`) before being forwarded into the structural URI encodings.
2.  The `PB_KEY` generation logic in `ProtobufEncoder` must rigidly adhere to this normalization to ensure that Antigravity IDE flawlessly recognizes the injected `trajectorySummaries`.

---
## 5. IDE Persistence Lifecycle

1.  **Shutdown**: Flushes active UI memory to `.pb` caches in `~/.gemini/antigravity/conversations`.
2.  **State Sync**: Reconstructs `state.vscdb` by compacting `.pb` files into the core JSON and Base64 Protobuf payloads.
3.  **Startup**: Connects to `state.vscdb`, queries `chat.ChatSessionStore.index` for rendering the Sidebar UI, and then maps deep constraints by decoding `PB_KEY`.
