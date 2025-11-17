from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Position:
    market_id: str
    side: str
    size: float
    price: float
    tx_hash: Optional[str] = None
    status: str = "open"


class PositionTracker:
    def __init__(self, storage_path: Path = Path("./positions.json")) -> None:
        self.storage_path = storage_path
        self.positions: List[Position] = []
        self._load()

    def record(self, position: Position) -> None:
        self.positions.append(position)
        logger.info("Recorded position", extra={"market": position.market_id, "side": position.side})
        self._persist()

    def update_status(self, tx_hash: str, status: str) -> None:
        for pos in self.positions:
            if pos.tx_hash == tx_hash:
                pos.status = status
                logger.info("Updated position status", extra={"tx": tx_hash, "status": status})
                break
        self._persist()

    def settle(self, market_id: str, status: str = "settled") -> None:
        for pos in self.positions:
            if pos.market_id == market_id:
                pos.status = status
        self._persist()

    def _persist(self) -> None:
        serialized: List[Dict] = [asdict(p) for p in self.positions]
        self.storage_path.write_text(json.dumps(serialized, indent=2))

    def _load(self) -> None:
        if not self.storage_path.exists():
            return
        try:
            data = json.loads(self.storage_path.read_text())
            for item in data:
                self.positions.append(Position(**item))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to load existing position log", extra={"error": str(exc)})
