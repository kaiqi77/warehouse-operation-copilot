from __future__ import annotations

from typing import Any


def run_simulation(data_metrics: dict[str, Any]) -> dict[str, Any]:
    peak_outbound = data_metrics.get("peak_outbound", 0)
    labor_capacity = data_metrics.get("labor_capacity_per_hour", 0)
    sorter = next(
        (item for item in data_metrics.get("degraded_equipment", []) if item.get("type") == "sorter"),
        None,
    )
    sorter_capacity = sorter.get("throughput_per_hour", 900) if sorter else 900
    baseline_capacity = min(labor_capacity, sorter_capacity)

    strategies = [
        {"name": "baseline", "extra_heads": 0, "sorter_uplift": 0},
        {"name": "add_4_pickers", "extra_heads": 4, "sorter_uplift": 0},
        {"name": "sorter_priority_mode", "extra_heads": 0, "sorter_uplift": 0.15},
        {"name": "combined_peak_plan", "extra_heads": 4, "sorter_uplift": 0.15},
    ]

    results = []
    for strategy in strategies:
        labor_after = labor_capacity + strategy["extra_heads"] * 38
        sorter_after = sorter_capacity * (1 + strategy["sorter_uplift"])
        capacity = round(min(labor_after, sorter_after), 2)
        gap = max(0, peak_outbound - capacity)
        completion_rate = round(min(1, capacity / peak_outbound), 4) if peak_outbound else 1
        results.append(
            {
                "strategy": strategy["name"],
                "capacity_per_hour": capacity,
                "gap": round(gap, 2),
                "estimated_completion_rate": completion_rate,
                "sla_risk": "high" if completion_rate < 0.9 else "medium" if completion_rate < 0.96 else "low",
            }
        )

    best = max(results, key=lambda item: (item["estimated_completion_rate"], -item["gap"]))
    return {"baseline_capacity": baseline_capacity, "strategies": results, "best_strategy": best}