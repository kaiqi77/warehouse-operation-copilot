from __future__ import annotations

from typing import Any, Literal, TypedDict


class AgentState(TypedDict, total=False):
    task_id: str
    question: str
    user_id: str
    urgency: Literal["low", "medium", "high"]
    plan: list[str]
    current_skill: str
    completed_skills: list[str]
    observations: dict[str, Any]
    steps: list[dict[str, Any]]
    recommendations: list[str]
    risks: list[str]
    next_actions: list[dict[str, Any]]
    memories: list[dict[str, Any]]
    answer: str
    started_at: float
    response_time_ms: int