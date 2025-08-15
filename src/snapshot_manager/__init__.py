"""
Snapshot-based state management system for the Cua Agent SDK.

This package provides functionality to capture, store, and restore container
snapshots at defined intervals or events during agent execution.
"""

from .models import SnapshotMetadata, SnapshotConfig
from .manager import SnapshotManager
from .callback import SnapshotCallback
from .providers import DockerSnapshotProvider
from .storage import FileSystemSnapshotStorage

__version__ = "0.1.0"

__all__ = [
    "SnapshotMetadata",
    "SnapshotConfig", 
    "SnapshotManager",
    "SnapshotCallback",
    "DockerSnapshotProvider",
    "FileSystemSnapshotStorage",
]
