from __future__ import annotations

from typing import Any


def run_anomaly_diagnosis(data_metrics: dict[str, Any], simulation: dict[str, Any] | None = None) -> dict[str, Any]:
    root_causes: list[dict[str, Any]] = []

    for sku in data_metrics.get("low_stock", []):
        root_causes.append(
            {
                "type": "inventory",
                "severity": "high" if sku["coverage_days"] < 2 else "medium",
                "message": f"{sku['sku']} is below safety stock with a gap of {sku['gap']} units and {sku['coverage_days']} days of coverage.",
            }
        )

    for equipment in data_metrics.get("degraded_equipment", []):
        severity = "high" if equipment.get("risk") == "high" else "medium"
        root_causes.append(
            {
                "type": "equipment",
                "severity": severity,
                "message": f"{equipment['id']} status is {equipment['status']}, queue is {equipment['queue']}, and hourly throughput is below target.",
            }
        )

    if simulation:
        best = simulation.get("best_strategy", {})
        if best.get("sla_risk") != "low":
            root_causes.append(
                {
                    "type": "capacity",
                    "severity": best.get("sla_risk", "medium"),
                    "message": "Even with the best strategy, the peak hour still carries SLA risk and may require overtime labor or order wave splitting.",
                }
            )

    return {
        "root_causes": root_causes,
        "summary": "; ".join(item["message"] for item in root_causes) if root_causes else "No significant anomaly was found.",
    }