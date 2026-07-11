from __future__ import annotations

from statistics import mean
from typing import Any

from app.services.memory import DecisionMemory


class EvaluationService:
    def __init__(self, memory: DecisionMemory | None = None) -> None:
        self.memory = memory or DecisionMemory()

    def metrics(self) -> dict[str, Any]:
        records = self.memory.list_records()
        total = len(records)
        completed = [record for record in records if record.get("status") == "completed"]
        adopted = [record for record in completed if record.get("adopted") is True]
        response_times = [record.get("response_time_ms", 0) for record in completed if record.get("response_time_ms")]
        automated_steps = sum(record.get("automated_steps", 0) for record in completed)
        total_steps = sum(record.get("total_steps", 0) for record in completed)

        return {
            "total_tasks": total,
            "completed_tasks": len(completed),
            "task_completion_rate": round(len(completed) / total, 4) if total else 0,
            "solution_adoption_rate": round(len(adopted) / len(completed), 4) if completed else 0,
            "average_response_time_ms": round(mean(response_times), 2) if response_times else 0,
            "automation_coverage_rate": round(automated_steps / total_steps, 4) if total_steps else 0,
        }