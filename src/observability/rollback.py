"""
Rollback manager — maintains versioned snapshots of agent configs,
tool registrations, and model assignments. Provides one-click rollback
to a known-good state on failure detection.
"""

from __future__ import annotations

import copy
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ConfigSnapshot:
    """A point-in-time snapshot of the system configuration."""

    id: str
    timestamp: str
    description: str
    config: dict = field(default_factory=dict)
    agent_configs: dict = field(default_factory=dict)
    tool_registry: list[dict] = field(default_factory=list)


class RollbackManager:
    """
    Versioned configuration manager with rollback support.

    Features:
    - Snapshots the full system state (agent configs, tool registry, router settings).
    - Supports named snapshots for deployments/releases.
    - Rollback to any previous snapshot by ID.
    - Rollforward (re-apply a previously rolled-back snapshot).
    - Audit log of all rollback events.
    """

    def __init__(self) -> None:
        self._snapshots: list[ConfigSnapshot] = []
        self._current_snapshot: ConfigSnapshot | None = None
        self._rollback_log: list[dict] = []

    def snapshot(self, config: dict, description: str = "") -> str:
        """
        Take a full system configuration snapshot.

        Args:
            config: The current system configuration dict.
            description: Optional human-readable description.

        Returns:
            Snapshot ID string.
        """
        import uuid
        snap_id = str(uuid.uuid4())[:12]
        snapshot = ConfigSnapshot(
            id=snap_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            description=description or f"Snapshot {len(self._snapshots) + 1}",
            config=copy.deepcopy(config),
        )
        self._snapshots.append(snapshot)
        self._current_snapshot = snapshot
        logger.info("Snapshot %s: %s", snap_id, description)
        return snap_id

    def list_snapshots(self) -> list[dict]:
        """List all available snapshots (ID, timestamp, description)."""
        return [
            {
                "id": s.id,
                "timestamp": s.timestamp,
                "description": s.description,
                "is_current": s is self._current_snapshot,
            }
            for s in self._snapshots
        ]

    def rollback_to(self, snapshot_id: str) -> dict | None:
        """
        Rollback the system to a previous snapshot.

        Args:
            snapshot_id: The target snapshot ID.

        Returns:
            The restored configuration dict, or None if not found.
        """
        target = next((s for s in self._snapshots if s.id == snapshot_id), None)
        if not target:
            logger.error("Snapshot %s not found for rollback.", snapshot_id)
            return None

        self._current_snapshot = target
        self._rollback_log.append({
            "action": "rollback",
            "snapshot_id": snapshot_id,
            "description": target.description,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        logger.warning("ROLLBACK to snapshot %s (%s)", snapshot_id, target.description)
        return copy.deepcopy(target.config)

    def rollforward(self, snapshot_id: str) -> dict | None:
        """
        Re-apply a previously rolled-back snapshot (rollforward).

        Args:
            snapshot_id: The snapshot to re-apply.

        Returns:
            The restored configuration dict, or None if not found.
        """
        target = next((s for s in self._snapshots if s.id == snapshot_id), None)
        if not target:
            logger.error("Snapshot %s not found for rollforward.", snapshot_id)
            return None

        self._current_snapshot = target
        self._rollback_log.append({
            "action": "rollforward",
            "snapshot_id": snapshot_id,
            "description": target.description,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        logger.info("ROLLFORWARD to snapshot %s (%s)", snapshot_id, target.description)
        return copy.deepcopy(target.config)

    def get_rollback_history(self) -> list[dict]:
        """Get the full rollback audit log."""
        return list(self._rollback_log)

    @property
    def current_snapshot_id(self) -> str | None:
        return self._current_snapshot.id if self._current_snapshot else None
