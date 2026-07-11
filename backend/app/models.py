from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class AgentRunRequest(BaseModel):
    question: str = Field(..., min_length=2, description="Frontline operation question")
    user_id: str = Field(default="operator", description="User identifier")
    urgency: Literal["low", "medium", "high"] = "medium"


class AgentStep(BaseModel):
    name: str
    thought: str
    action: str
    observation: dict[str, Any]


class AgentRunResponse(BaseModel):
    task_id: str
    answer: str
    recommendations: list[str]
    risks: list[str]
    next_actions: list[dict[str, Any]]
    steps: list[AgentStep]
    metrics: dict[str, Any]


class AdoptionUpdate(BaseModel):
    task_id: str
    adopted: bool