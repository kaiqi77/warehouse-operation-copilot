from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.agent.graph import WarehouseAgentGraph
from app.models import AdoptionUpdate, AgentRunRequest, AgentRunResponse
from app.services.evaluation import EvaluationService
from app.services.memory import DecisionMemory
from app.services.wms_mcp import WmsMcpClient


app = FastAPI(title="Warehouse Operation Copilot", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = WarehouseAgentGraph()
memory = DecisionMemory()
evaluation = EvaluationService(memory)
wms = WmsMcpClient()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/dashboard")
def dashboard() -> dict:
    return wms.read_resource("snapshot")


@app.post("/api/agent/run", response_model=AgentRunResponse)
def run_agent(request: AgentRunRequest) -> AgentRunResponse:
    state = agent.run(request.question, request.user_id, request.urgency)
    return AgentRunResponse(
        task_id=state["task_id"],
        answer=state["answer"],
        recommendations=state.get("recommendations", []),
        risks=state.get("risks", []),
        next_actions=state.get("next_actions", []),
        steps=state.get("steps", []),
        metrics=evaluation.metrics(),
    )


@app.get("/api/memory")
def list_memory() -> list[dict]:
    return memory.list_records()


@app.get("/api/evaluations")
def get_evaluations() -> dict:
    return evaluation.metrics()


@app.post("/api/evaluations/adoption")
def update_adoption(update: AdoptionUpdate) -> dict[str, bool | str]:
    updated = memory.update_adoption(update.task_id, update.adopted)
    if not updated:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task_id": update.task_id, "updated": True}