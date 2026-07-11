from __future__ import annotations

from typing import Any

from app.services.wms_mcp import WmsMcpClient


def run_equipment_control(client: WmsMcpClient, diagnosis: dict[str, Any]) -> dict[str, Any]:
    actions: list[dict[str, Any]] = []
    messages = " ".join(item.get("message", "") for item in diagnosis.get("root_causes", []))

    if "SORTER" in messages or "sorter" in messages:
        actions.append(
            client.request_action(
                "set_sorter_mode",
                {"equipment_id": "SORTER-01", "mode": "priority_wave", "duration_minutes": 90},
            )
        )

    if "AGV" in messages or "agv" in messages or "congested" in messages or "congestion" in messages:
        actions.append(
            client.request_action(
                "rebalance_agv_routes",
                {"fleet_id": "AGV-FLEET", "strategy": "avoid_congested_aisles", "approval_owner": "shift_manager"},
            )
        )

    if "below safety stock" in messages:
        actions.append(
            client.request_action(
                "create_replenishment_task",
                {"priority": "urgent", "source": "reserve_zone", "target": "forward_pick_zone"},
            )
        )

    return {
        "actions": actions,
        "safe_to_auto_execute": [action for action in actions if action["status"] == "ready_to_execute"],
        "approval_required": [action for action in actions if action["status"] == "approval_required"],
    }