from app.agent.graph import WarehouseAgentGraph


def main() -> None:
    graph = WarehouseAgentGraph()
    state = graph.run(
        "Will today's outbound peak create shipment delays? Diagnose inventory and equipment risks, then provide a wave planning recommendation.",
        "tester",
        "high",
    )
    print(state["answer"])
    print(f"steps={len(state['steps'])}")


if __name__ == "__main__":
    main()