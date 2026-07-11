from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MEMORY_FILE = Path(__file__).resolve().parents[1] / "data" / "decision_memory.json"


class DecisionMemory:
    def list_records(self) -> list[dict[str, Any]]:
        return self._read()

    def search(self, question: str, limit: int = 3) -> list[dict[str, Any]]:
        keywords = {token.lower() for token in question.replace("？", " ").replace("，", " ").split() if token}
        records = self._read()
        scored: list[tuple[int, dict[str, Any]]] = []
        for record in records:
            haystack = json.dumps(record, ensure_ascii=False).lower()
            score = sum(1 for keyword in keywords if keyword in haystack)
            if score:
                scored.append((score, record))
        return [record for _, record in sorted(scored, key=lambda item: item[0], reverse=True)[:limit]]

    def append(self, record: dict[str, Any]) -> None:
        records = self._read()
        records.append({"created_at": datetime.now(timezone.utc).isoformat(), **record})
        MEMORY_FILE.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    def update_adoption(self, task_id: str, adopted: bool) -> bool:
        records = self._read()
        updated = False
        for record in records:
            if record.get("task_id") == task_id:
                record["adopted"] = adopted
                record["adopted_at"] = datetime.now(timezone.utc).isoformat()
                updated = True
        if updated:
            MEMORY_FILE.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        return updated

    def _read(self) -> list[dict[str, Any]]:
        MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        if not MEMORY_FILE.exists():
            MEMORY_FILE.write_text("[]", encoding="utf-8")
        return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))