from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal


DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "sample_warehouse.json"
AUDIT_FILE = Path(__file__).resolve().parents[1] / "data" / "mcp_audit.json"


@dataclass(frozen=True)
class McpPolicy:
    allowed_read_resources: tuple[str, ...] = ("orders", "inventory", "equipment", "labor", "sla", "snapshot")
    allowed_write_actions: tuple[str, ...] = ("set_sorter_mode", "rebalance_agv_routes", "create_replenishment_task")
    high_risk_actions: tuple[str, ...] = ("rebalance_agv_routes",)


class WmsMcpClient:
    """A local MCP-style safety boundary for WMS interactions.

    The class mimics MCP tool calls and policy checks. Replace `_load_data` and
    `request_action` internals when connecting to real WMS/WCS services.
    """

    def __init__(self, policy: McpPolicy | None = None) -> None:
        self.policy = policy or McpPolicy()

    def read_resource(self, resource: str) -> Any:
        if resource not in self.policy.allowed_read_resources:
            raise PermissionError(f"Read resource is not allowed: {resource}")

        data = self._load_data()
        if resource == "snapshot":
            return data
        return data[resource]

    def request_action(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        if action not in self.policy.allowed_write_actions:
            result = {
                "action": action,
                "status": "blocked",
                "risk": "critical",
                "reason": "Action is outside MCP allowlist.",
                "payload": payload,
            }
            self._audit("write", result)
            return result

        risk: Literal["low", "medium", "high"] = "high" if action in self.policy.high_risk_actions else "medium"
        status = "approval_required" if risk == "high" else "ready_to_execute"
        result = {
            "action": action,
            "status": status,
            "risk": risk,
            "reason": "High risk actions require human approval." if risk == "high" else "Action passed MCP policy checks.",
            "payload": payload,
        }
        self._audit("write", result)
        return result

    def _load_data(self) -> dict[str, Any]:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))

    def _audit(self, operation: str, record: dict[str, Any]) -> None:
        AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
        logs: list[dict[str, Any]] = []
        if AUDIT_FILE.exists():
            logs = json.loads(AUDIT_FILE.read_text(encoding="utf-8"))
        logs.append({"operation": operation, "timestamp": datetime.now(timezone.utc).isoformat(), **record})
        AUDIT_FILE.write_text(json.dumps(logs, ensure_ascii=False, indent=2), encoding="utf-8")