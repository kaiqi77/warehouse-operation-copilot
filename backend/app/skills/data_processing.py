from __future__ import annotations

from typing import Any

from app.services.wms_mcp import WmsMcpClient


def run_data_processing(client: WmsMcpClient) -> dict[str, Any]:
    snapshot = client.read_resource("snapshot")
    orders = snapshot["orders"]
    inventory = snapshot["inventory"]
    equipment = snapshot["equipment"]
    labor = snapshot["labor"]

    total_outbound = sum(item["outbound"] for item in orders)
    peak = max(orders, key=lambda item: item["outbound"])
    labor_capacity = labor["available_heads"] * labor["pick_rate_per_head"]
    low_stock = [
        {
            "sku": item["sku"],
            "gap": item["safety_stock"] - item["on_hand"],
            "coverage_days": round(item["on_hand"] / item["daily_demand"], 2),
        }
        for item in inventory
        if item["on_hand"] < item["safety_stock"]
    ]
    degraded_equipment = [item for item in equipment if item["status"] != "running"]

    risk_signals: list[str] = []
    if peak["outbound"] > labor_capacity:
        risk_signals.append("Order peak exceeds current hourly picking labor capacity.")
    if low_stock:
        risk_signals.append("One or more SKUs are below safety stock.")
    if degraded_equipment:
        risk_signals.append("One or more pieces of equipment are degraded or congested.")

    return {
        "total_outbound": total_outbound,
        "peak_hour": peak["hour"],
        "peak_outbound": peak["outbound"],
        "labor_capacity_per_hour": labor_capacity,
        "low_stock": low_stock,
        "degraded_equipment": degraded_equipment,
        "risk_signals": risk_signals,
    }