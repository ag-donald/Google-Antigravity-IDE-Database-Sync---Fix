"""
Interactive backup discovery menu and safe database restoration logic.
Implements the Phase 0 entry point that runs before the standard recovery pipeline.
"""

from __future__ import annotations

import os
import shutil
import time

from .constants import BACKUP_PREFIX, DB_FILENAME
from .db_scanner import scan_all, format_snapshot_table
from .logger import Logger


def restore_backup(backup_path: str, target_path: str) -> None:
    """
    Safely restores a backup database over the current live database.

    Before overwriting, creates a 'pre_restore_' safety snapshot of the
    current file so the user can undo the restore if needed.

    Args:
        backup_path: Absolute path to the backup file to restore.
        target_path: Absolute path to the live state.vscdb file.

    Raises:
        OSError: If the copy operation fails.
    """
    # Create a safety snapshot of the current DB before overwriting
    safety_label = f"pre_restore_{int(time.time())}"
    safety_path = f"{target_path}.{safety_label}"

    if os.path.isfile(target_path):
        shutil.copy2(target_path, safety_path)
        Logger.info(f"Safety snapshot saved: {safety_path}")

    shutil.copy2(backup_path, target_path)
    Logger.success(f"Restored backup: {os.path.basename(backup_path)}")
    Logger.success(f"Database has been replaced with the selected backup.")
    Logger.info(f"To undo this restore, copy '{os.path.basename(safety_path)}' back over '{DB_FILENAME}'.")


def run_backup_menu(db_path: str) -> str:
    """
    Phase 0 entry point. Scans for all available database backups,
    displays a comparison table, and prompts the user for an action.

    Returns:
        "recover"  — User chose to proceed with standard recovery.
        "restored" — A backup was successfully restored; caller should exit.
        "exit"     — User chose to quit without changes.
    """
    Logger.header("Phase 0: Database Backup Scanner")
    print()
    Logger.info("Scanning for database snapshots...")
    print()

    snapshots = scan_all(db_path)

    # If there is only the current DB and no backups, skip the menu
    backup_snapshots = [s for s in snapshots if not s.is_current]
    if not backup_snapshots:
        Logger.info("No previous backups found. Proceeding to recovery.")
        return "recover"

    # Display comparison table
    table_lines = format_snapshot_table(snapshots)
    for line in table_lines:
        print(line)
    print()

    # Display options
    max_backup_idx = len(snapshots) - 1
    print("  Options:")
    print("    [R] Recover / rebuild current database (standard recovery)")
    if max_backup_idx >= 1:
        if max_backup_idx == 1:
            print("    [1] Restore this backup")
        else:
            print(f"    [1-{max_backup_idx}] Restore a specific backup")
    print("    [Q] Quit without changes")
    print()

    while True:
        try:
            raw = input("  Your choice: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print()
            return "exit"

        if raw in ("r", ""):
            return "recover"

        if raw == "q":
            Logger.info("Exiting without changes.")
            return "exit"

        # Try to parse a numeric backup selection
        try:
            idx = int(raw)
        except ValueError:
            print(f"  Invalid selection '{raw}'. Enter R, 1-{max_backup_idx}, or Q.")
            continue

        if idx < 1 or idx > max_backup_idx:
            print(f"  Invalid index. Please enter a number between 1 and {max_backup_idx}.")
            continue

        selected = snapshots[idx]
        if selected.error:
            Logger.warn(f"That backup has an error: {selected.error}")
            Logger.warn("Please select a different backup.")
            continue

        # Confirm restore
        print()
        Logger.info(f"Selected: [{idx}] {selected.label}")
        Logger.info(f"  Conversations: {selected.conversation_count}  |  "
                     f"Titled: {selected.titled_count}  |  "
                     f"Workspaces: {selected.workspace_count}")
        print()

        try:
            confirm = input("  Restore this backup? (y/N): ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print()
            return "exit"

        if confirm != "y":
            print("  Cancelled. Choose again or press Q to quit.")
            continue

        # Perform the restore
        try:
            restore_backup(selected.path, db_path)
            return "restored"
        except Exception as exc:
            Logger.error(f"Restore failed: {exc}")
            Logger.warn("The original database is still intact.")
            return "exit"
