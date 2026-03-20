"""
Database introspection and backup scanning module.
Provides read-only analysis of `.vscdb` states and parses their contents.
"""

from __future__ import annotations

import base64
import glob
import json
import os
import sqlite3
import time
from dataclasses import dataclass
from typing import Optional

from .constants import PB_KEY, JSON_KEY, BACKUP_PREFIX, DB_FILENAME
from .protobuf import ProtobufEncoder


@dataclass(frozen=True)
class DatabaseSnapshot:
    """Immutable representation of a scanned SQLite database file's metadata and contents."""
    path: str
    label: str
    size_bytes: int
    modified_at: float
    conversation_count: int
    titled_count: int
    workspace_count: int
    json_entry_count: int
    is_current: bool
    error: Optional[str] = None


def extract_existing_metadata(decoded: bytes) -> tuple[dict[str, str], dict[str, bytes]]:
    """
    Parses the raw SQLite `trajectorySummaries` database payload to extract the actual
    human-readable titles and their raw, intact inner Protobuf binary states.

    Args:
        decoded (bytes): The Base64-decoded Wire Type 2 byte string from the database.

    Returns:
        tuple[dict[str, str], dict[str, bytes]]:
            - titles: A dictionary strictly mapping `conversation_uuid` -> `title`.
            - inner_blobs: A dictionary mapping `conversation_uuid` -> `raw_inner_bytes`.
    """
    titles = {}
    inner_blobs = {}
    pos = 0

    while pos < len(decoded):
        try:
            tag, pos = ProtobufEncoder.decode_varint(decoded, pos)
        except Exception:
            break
        wire_type = tag & 7

        if wire_type != 2:
            break

        length, pos = ProtobufEncoder.decode_varint(decoded, pos)
        outer_entry = decoded[pos:pos + length]
        pos += length

        ep = 0
        try:
            t, ep = ProtobufEncoder.decode_varint(outer_entry, ep)
            if (t >> 3) == 1 and (t & 7) == 2:
                l, ep = ProtobufEncoder.decode_varint(outer_entry, ep)
                entry = outer_entry[ep:ep + l]
            else:
                entry = outer_entry
        except Exception:
            entry = outer_entry

        ep, uid, info_b64 = 0, None, None
        while ep < len(entry):
            try:
                t, ep = ProtobufEncoder.decode_varint(entry, ep)
            except Exception:
                break
            fn, wt = t >> 3, t & 7
            if wt == 2:
                l, ep = ProtobufEncoder.decode_varint(entry, ep)
                content = entry[ep:ep + l]
                ep += l
                if fn == 1:
                    uid = content.decode('utf-8', errors='replace')
                elif fn == 2:
                    sp = 0
                    try:
                        _, sp = ProtobufEncoder.decode_varint(content, sp)
                        sl, sp = ProtobufEncoder.decode_varint(content, sp)
                        info_b64 = content[sp:sp + sl].decode('utf-8', errors='replace')
                    except Exception:
                        pass
            elif wt == 0:
                _, ep = ProtobufEncoder.decode_varint(entry, ep)
            elif wt == 1:
                ep += 8
            elif wt == 5:
                ep += 4
            else:
                break

        if uid and info_b64:
            assert info_b64 is not None
            try:
                raw_inner = base64.b64decode(info_b64)
                inner_blobs[uid] = raw_inner

                ip = 0
                _, ip = ProtobufEncoder.decode_varint(raw_inner, ip)
                il, ip = ProtobufEncoder.decode_varint(raw_inner, ip)
                title = raw_inner[ip:ip + il].decode('utf-8', errors='replace')
                if not title.startswith("Conversation (") and not title.startswith("Conversation "):
                    titles[uid] = title
            except Exception:
                pass

    return titles, inner_blobs


def extract_workspace_count(inner_blobs: dict[str, bytes]) -> int:
    """Helper to detect how many parsed trajectories have a real workspace encoded in them."""
    ws_count = 0
    for uid, raw_inner in inner_blobs.items():
        # A quick heuristic to verify if 'file:///' exists in the blob, 
        # which strongly indicates a workspace was assigned.
        if b"file:///" in raw_inner:
            ws_count += 1
    return ws_count


def scan_database(db_path: str, label: str, is_current: bool = False) -> DatabaseSnapshot:
    """
    Connects to the given SQLite database in read-only mode, extracts the
    Protobuf and JSON indices, and summarizes their current metrics.
    """
    if not os.path.isfile(db_path):
        return DatabaseSnapshot(db_path, label, 0, 0, 0, 0, 0, 0, is_current, error="File not found")

    try:
        size_bytes = os.path.getsize(db_path)
        modified_at = os.path.getmtime(db_path)
    except Exception as e:
        return DatabaseSnapshot(db_path, label, 0, 0, 0, 0, 0, 0, is_current, error=f"Stat error: {e}")

    try:
        # uri=True enables read-only opening in sqlite3
        db_uri = f"file:{db_path}?mode=ro"
        conn = sqlite3.connect(db_uri, uri=True, timeout=5)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Extract PB count
        cursor.execute("SELECT value FROM ItemTable WHERE key = ?", (PB_KEY,))
        row = cursor.fetchone()
        conversation_count = 0
        titled_count = 0
        workspace_count = 0
        if row:
            pb_payload = row["value"]
            if pb_payload:
                decoded = base64.b64decode(pb_payload)
                titles, inner_blobs = extract_existing_metadata(decoded)
                conversation_count = len(inner_blobs)
                titled_count = len(titles)
                workspace_count = extract_workspace_count(inner_blobs)

        # Extract JSON count
        cursor.execute("SELECT value FROM ItemTable WHERE key = ?", (JSON_KEY,))
        row_json = cursor.fetchone()
        json_entry_count = 0
        if row_json:
            j_payload = row_json["value"]
            try:
                j_obj = json.loads(j_payload)
                if "entries" in j_obj and isinstance(j_obj["entries"], dict):
                    json_entry_count = len(j_obj["entries"])
            except Exception:
                pass

        conn.close()
        
        return DatabaseSnapshot(
            path=db_path,
            label=label,
            size_bytes=size_bytes,
            modified_at=modified_at,
            conversation_count=conversation_count,
            titled_count=titled_count,
            workspace_count=workspace_count,
            json_entry_count=json_entry_count,
            is_current=is_current
        )
    except Exception as e:
        return DatabaseSnapshot(db_path, label, size_bytes, modified_at, 0, 0, 0, 0, is_current, error=f"DB error: {e}")


def discover_backups(db_dir: str) -> list[str]:
    """Finds all recovery backups within the globalStorage directory, sorted newest first."""
    pattern = os.path.join(db_dir, f"{DB_FILENAME}.{BACKUP_PREFIX}_*")
    matches = glob.glob(pattern)
    # Sort files by creation/modification time in descending order (newest first)
    matches.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return matches


def scan_all(current_db_path: str) -> list[DatabaseSnapshot]:
    """
    Scans the current DB and all available backups.
    Returns the current DB at index 0, followed by backups newest-first.
    """
    snapshots = []
    
    # 1. Scan current
    sn_current = scan_database(current_db_path, "CURRENT", is_current=True)
    snapshots.append(sn_current)
    
    # 2. Discover & scan backups
    db_dir = os.path.dirname(current_db_path)
    backups = discover_backups(db_dir)
    
    for b in backups:
        try:
            # Extract timestamp from filename like `state.vscdb.agmercium_recovery_1710000000`
            basename = os.path.basename(b)
            ts_str = basename.rsplit(f"{BACKUP_PREFIX}_", 1)[-1]
            epoch = int(ts_str)
            label = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(epoch))
        except Exception:
            label = "Unknown Backup"
            
        sn = scan_database(b, label, is_current=False)
        snapshots.append(sn)
        
    return snapshots


def format_snapshot_table(snapshots: list[DatabaseSnapshot]) -> list[str]:
    """Generates the formatted terminal analysis table."""
    def format_size(b: int) -> str:
        mb = b / (1024 * 1024)
        return f"{mb:.1f} MB"

    lines = []
    lines.append("  +-----+----------------------+----------+-------+--------+------+------------+")
    lines.append("  |  #  | Label                | Size     | Convs | Titled |  WS  | JSON Index |")
    lines.append("  +-----+----------------------+----------+-------+--------+------+------------+")

    for idx, snap in enumerate(snapshots):
        if snap.is_current:
            lbl = f"* {snap.label}"
        else:
            lbl = snap.label

        if snap.error:
            lines.append(f"  | {idx:^3} | {lbl:<20} | {format_size(snap.size_bytes):>8} | {snap.error:<42} |")
        else:
            lines.append(f"  | {idx:^3} | {lbl:<20} | {format_size(snap.size_bytes):>8} | {snap.conversation_count:>5} | {snap.titled_count:>6} | {snap.workspace_count:>4} | {snap.json_entry_count:>10} |")

    lines.append("  +-----+----------------------+----------+-------+--------+------+------------+")
    return lines
