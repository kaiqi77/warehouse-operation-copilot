from __future__ import annotations

import time
import uuid
from typing import Any, Literal

from langgraph.graph import END, StateGraph

from app.agent.state import AgentState
from app.services.evaluation import EvaluationService
from app.services.memory import DecisionMemory
from app.services.wms_mcp import WmsMcpClient
from app.skills.anomaly_diagnosis import run_anomaly_diagnosis
from app.skills.data_processing import run_data_processing
from app.skills.equipment_control import run_equipment_control
from app.skills.simulation import run_simulation


SkillName = Literal["data_processing", "simulation", "anomaly_diagnosis", "equipment_control"]


def _append_step(state: AgentState, name: str, thought: str, action: str, observation: dict[str, Any]) -> None:
    state.setdefault("steps", []).append(
        {"name": name, "thought": thought, "action": action, "observation": observation}
    )


class WarehouseAgentGraph:
    def __init__(self) -> None:
        self.client = WmsMcpClient()
        self.memory = DecisionMemory()
        self.evaluation = EvaluationService(self.memory)
        self.graph = self._build_graph()

    def run(self, question: str, user_id: str, urgency: str) -> AgentState:
        initial_state: AgentState = {
            "task_id": str(uuid.uuid4()),
            "question": question,
            "user_id": user_id,
            "urgency": urgency,  # type: ignore[typeddict-item]
            "completed_skills": [],
            "observations": {},
            "steps": [],
            "recommendations": [],
            "risks": [],
            "next_actions": [],
            "started_at": time.perf_counter(),
        }
        return self.graph.invoke(initial_state)

    def _build_graph(self):
        graph = StateGraph(AgentState)
        graph.add_node("plan", self._plan)
        graph.add_node("act", self._act)
        graph.add_node("observe", self._observe)
        graph.add_node("final", self._final)

        graph.set_entry_point("plan")
        graph.add_edge("plan", "act")
        graph.add_edge("act", "observe")
        graph.add_conditional_edges("observe", self._route, {"act": "act", "final": "final"})
        graph.add_edge("final", END)
        return graph.compile()

    def _plan(self, state: AgentState) -> AgentState:
        question = state["question"].lower()
        plan: list[SkillName] = ["data_processing"]

        if any(keyword in question for keyword in ["simulation", "simulate", "capacity", "peak", "sla", "delay", "wave", "planning", "staffing"]):
            plan.append("simulation")
        if any(keyword in question for keyword in ["anomaly", "diagnose", "diagnosis", "root cause", "inventory", "stock", "drop", "congestion", "congested", "risk"]):
            plan.append("anomaly_diagnosis")
        if any(keyword in question for keyword in ["equipment", "agv", "sorter", "control", "conveyor", "congestion", "congested", "routing"]):
            plan.append("equipment_control")

        if "simulation" not in plan:
            plan.append("simulation")
        if "anomaly_diagnosis" not in plan:
            plan.append("anomaly_diagnosis")

        similar_memories = self.memory.search(state["question"])
        state["plan"] = plan
        state["memories"] = similar_memories
        _append_step(
            state,
            "plan",
            "Decompose the task into an executable Skill sequence based on question keywords and historical memory.",
            "create_react_plan",
            {"plan": plan, "similar_memory_count": len(similar_memories)},
        )
        return state

    def _act(self, state: AgentState) -> AgentState:
        completed = state.setdefault("completed_skills", [])
        next_skill = next(skill for skill in state["plan"] if skill not in completed)
        observations = state.setdefault("observations", {})

        if next_skill == "data_processing":
            result = run_data_processing(self.client)
            thought = "Aggregate order, inventory, equipment, and labor data first to identify baseline risk signals."
        elif next_skill == "simulation":
            result = run_simulation(observations.get("data_processing", {}))
            thought = "Run a lightweight simulation for peak capacity and candidate strategies to compare SLA risk."
        elif next_skill == "anomaly_diagnosis":
            result = run_anomaly_diagnosis(
                observations.get("data_processing", {}), observations.get("simulation")
            )
            thought = "Use KPI and simulation observations to locate inventory, equipment, and capacity root causes."
        elif next_skill == "equipment_control":
            result = run_equipment_control(self.client, observations.get("anomaly_diagnosis", {}))
            thought = "Convert diagnosis results into equipment or replenishment actions constrained by MCP policy."
        else:
            raise ValueError(f"Unsupported skill: {next_skill}")

        observations[next_skill] = result
        completed.append(next_skill)
        state["current_skill"] = next_skill
        _append_step(state, next_skill, thought, f"run_{next_skill}", result)
        return state

    def _observe(self, state: AgentState) -> AgentState:
        current_skill = state.get("current_skill", "unknown")
        observation = state.get("observations", {}).get(current_skill, {})
        _append_step(
            state,
            "observe",
            "Inspect the previous Skill output and decide whether more Skills are needed.",
            "inspect_observation",
            {"current_skill": current_skill, "has_observation": bool(observation)},
        )
        return state

    def _route(self, state: AgentState) -> str:
        completed = set(state.get("completed_skills", []))
        plan = state.get("plan", [])
        return "final" if all(skill in completed for skill in plan) else "act"

    def _final(self, state: AgentState) -> AgentState:
        observations = state.get("observations", {})
        data_metrics = observations.get("data_processing", {})
        simulation = observations.get("simulation", {})
        diagnosis = observations.get("anomaly_diagnosis", {})
        control = observations.get("equipment_control", {})

        recommendations = self._recommendations(data_metrics, simulation, diagnosis, control)
        risks = self._risks(data_metrics, simulation, diagnosis, control)
        next_actions = control.get("actions", [])
        response_time_ms = int((time.perf_counter() - state["started_at"]) * 1000)

        answer = "Operation diagnosis completed: " + " ".join(recommendations[:3])
        if risks:
            answer += " Main risks: " + "; ".join(risks[:3])

        state["answer"] = answer
        state["recommendations"] = recommendations
        state["risks"] = risks
        state["next_actions"] = next_actions
        state["response_time_ms"] = response_time_ms

        self.memory.append(
            {
                "task_id": state["task_id"],
                "question": state["question"],
                "answer": answer,
                "recommendations": recommendations,
                "risks": risks,
                "status": "completed",
                "adopted": False,
                "response_time_ms": response_time_ms,
                "automated_steps": len(state.get("completed_skills", [])),
                "total_steps": len(state.get("plan", [])),
            }
        )
        _append_step(
            state,
            "final",
            "Summarize observations, produce recommendations, and update decision memory plus evaluation metrics.",
            "finalize_decision",
            {"response_time_ms": response_time_ms, "evaluation": self.evaluation.metrics()},
        )
        return state

    def _recommendations(
        self,
        data_metrics: dict[str, Any],
        simulation: dict[str, Any],
        diagnosis: dict[str, Any],
        control: dict[str, Any],
    ) -> list[str]:
        recommendations = []
        best = simulation.get("best_strategy")
        if best:
            recommendations.append(
                f"For peak hour {data_metrics.get('peak_hour')}, use {best['strategy']} with an estimated completion rate of {best['estimated_completion_rate'] * 100:.1f}%."
            )
        for item in data_metrics.get("low_stock", []):
            recommendations.append(f"Create urgent replenishment for {item['sku']}; current safety-stock gap is {item['gap']} units.")
        if control.get("safe_to_auto_execute"):
            recommendations.append("Ready low/medium-risk actions: " + ", ".join(action["action"] for action in control["safe_to_auto_execute"]))
        if control.get("approval_required"):
            recommendations.append("High-risk actions requiring shift-lead approval: " + ", ".join(action["action"] for action in control["approval_required"]))
        if not recommendations and diagnosis.get("summary"):
            recommendations.append(diagnosis["summary"])
        return recommendations

    def _risks(
        self,
        data_metrics: dict[str, Any],
        simulation: dict[str, Any],
        diagnosis: dict[str, Any],
        control: dict[str, Any],
    ) -> list[str]:
        risks = list(data_metrics.get("risk_signals", []))
        best = simulation.get("best_strategy", {})
        if best.get("sla_risk") in {"medium", "high"}:
            risks.append(f"The best strategy still has {best['sla_risk']} SLA risk with a capacity gap of {best['gap']} units.")
        risks.extend(item["message"] for item in diagnosis.get("root_causes", []) if item.get("severity") == "high")
        risks.extend(action["reason"] for action in control.get("approval_required", []))
        return risks