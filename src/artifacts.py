"""
Extracts human-readable conversation titles from brain artifacts.
"""

from __future__ import annotations

import os
import re
import platform

from .constants import MIN_TITLE_LENGTH, MAX_TITLE_LENGTH, TITLE_ARTIFACT_FILES, OVERVIEW_SUBPATH
from .logger import Logger


class ArtifactParser:
    """Extracts human-readable conversation titles from brain artifacts."""

    @staticmethod
    def extract_title(conv_uuid: str, brain_dir: str) -> str | None:
        """
        Attempts to extract a human-readable title from the brain artifacts
        for a given conversation UUID, utilizing a priority-ordered fallback chain.

        Fallback Sequence:
          1. First Markdown heading (#) in task.md / implementation_plan.md / walkthrough.md
          2. First strictly meaningful line in .system_generated/logs/overview.txt
          3. None (Caller will generate a timestamp-based fallback string)

        Args:
            conv_uuid (str): The specific conversation UUID.
            brain_dir (str): The absolute path to the .gemini/antigravity/brain/ cache.

        Returns:
            str | None: The extracted title string or None if unrecoverable.
        """
        target_dir = os.path.join(brain_dir, conv_uuid)
        if not os.path.isdir(target_dir):
            return None

        # Priority 1: Markdown artifact headings
        for artifact_file in TITLE_ARTIFACT_FILES:
            filepath = os.path.join(target_dir, artifact_file)
            if os.path.isfile(filepath):
                title = ArtifactParser._read_first_heading(filepath)
                if title:
                    return title

        # Priority 2: System-generated overview log
        overview_path = os.path.join(target_dir, OVERVIEW_SUBPATH)
        if os.path.isfile(overview_path):
            try:
                with open(overview_path, "r", encoding="utf-8", errors="replace") as fh:
                    for line in fh:
                        clean = line.strip()
                        if clean and not clean.startswith("#") and len(clean) > MIN_TITLE_LENGTH:
                            return clean[:MAX_TITLE_LENGTH]
            except OSError:
                Logger.debug(f"Could not read overview log for {conv_uuid}")

        return None

    @staticmethod
    def _read_first_heading(filepath: str) -> str | None:
        """Extracts the first Markdown heading (# ...) from a file."""
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    stripped = line.strip()
                    if stripped.startswith("#"):
                        # Remove all leading '#' characters, then strip whitespace
                        title = stripped.lstrip("#").strip()
                        if title:
                            return title[:MAX_TITLE_LENGTH]
        except OSError:
            pass
        return None

    @staticmethod
    def infer_workspace_from_brain(conv_uuid: str, brain_dir: str) -> str | None:
        """
        Heuristically scans internal metadata files (brain .md files) for embedded
        `file:///` uniform resource identifiers in order to infer the developer's workspace.

        The heuristic relies on counting frequency: whichever root directory appears
        most frequently across all associated markdown files is nominated as the workspace.

        Args:
            conv_uuid (str): The specific conversation UUID.
            brain_dir (str): The absolute path to the .gemini/antigravity/brain/ cache.

        Returns:
            str | None: An OS-native filesystem path string (e.g. 'C:\\Projects\\App'), or None.
        """
        target_dir = os.path.join(brain_dir, conv_uuid)
        if not os.path.isdir(target_dir):
            return None

        is_windows = platform.system() == "Windows"
        if is_windows:
            path_pattern = re.compile(r"file:///([A-Za-z](?:%3A|:)/[^)\s\"'\]>]+)")
        else:
            path_pattern = re.compile(r"file:///([^)\s\"'\]>]+)")

        path_counts: dict[str, int] = {}
        try:
            for name in os.listdir(target_dir):
                if not name.endswith(".md") or name.startswith("."):
                    continue
                filepath = os.path.join(target_dir, name)
                try:
                    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read(16384)
                    for match in path_pattern.finditer(content):
                        raw = match.group(1)
                        # Normalize ASCII URL encodings
                        raw = raw.replace("%3A", ":").replace("%3a", ":")
                        raw = raw.replace("%20", " ")
                        parts = raw.replace("\\", "/").split("/")

                        # Tally all parent directories to find the most specific common ancestor
                        depth_start = 4 if is_windows else 3
                        for d in range(depth_start, len(parts)):
                            ws = "/".join(parts[:d])
                            path_counts[ws] = path_counts.get(ws, 0) + 1
                except OSError:
                    pass
        except OSError:
            return None

        if not path_counts:
            return None

        # Find the max frequency
        max_count = max(path_counts.values())
        # Out of all paths that share the maximum frequency, pick the longest one (deepest common ancestor)
        best = max([k for k, v in path_counts.items() if v == max_count], key=len)
        
        candidate = best.replace("/", os.sep)
        # Traverse upwards to find the true workspace root (marked by .git)
        current = candidate
        while current and os.path.dirname(current) != current:
            if os.path.isdir(os.path.join(current, ".git")):
                return current
            current = os.path.dirname(current)
            
        return candidate
