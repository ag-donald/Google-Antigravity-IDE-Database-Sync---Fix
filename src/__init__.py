"""
Agmercium Recovery Suite
========================

The core python package implementing the deterministic Protobuf and SQLite
injection logic required to recover the Antigravity IDE UI indices.
"""

from .constants import VERSION

__version__ = VERSION
__all__ = [
    "ArtifactParser",
    "DatabaseSnapshot",
    "EnvironmentResolver",
    "Logger",
    "ProtobufEncoder",
    "interactive_workspace_assignment",
    "run_backup_menu",
    "main",
]
