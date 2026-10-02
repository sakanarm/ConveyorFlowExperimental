from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path


class EventLedger:
    def __init__(self) -> None:
        self.events: list[dict] = []
        self._hasher = hashlib.sha256()

    def emit(self, tick: int, event: str, **fields: object) -> None:
        record = {"tick": tick, "event": event, **fields}
        line = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        self._hasher.update(line.encode("utf-8"))
        self._hasher.update(b"\n")
        self.events.append(record)

    @property
    def sha256(self) -> str:
        return self._hasher.hexdigest()

    def write_gzip(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(path, "wt", encoding="utf-8", newline="\n") as handle:
            for record in self.events:
                handle.write(json.dumps(record, sort_keys=True, ensure_ascii=False))
                handle.write("\n")

