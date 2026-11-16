"""Part 3.3: subgraphs - a compiled graph used as a node inside another graph.
Run: python -m part3.subgraph
"""
import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph


# The child graph has its own state. Keys it SHARES with the parent ('log') flow in and out.
class TravelState(TypedDict):
    destination: str
    log: Annotated[list[str], operator.add]


def choose_flights(state: TravelState) -> dict:
    return {"log": [f"flights chosen for {state['destination']}"]}


def choose_hotel(state: TravelState) -> dict:
    return {"log": [f"hotel chosen in {state['destination']}"]}


travel = StateGraph(TravelState)
travel.add_node("choose_flights", choose_flights)
travel.add_node("choose_hotel", choose_hotel)
travel.add_edge(START, "choose_flights")
travel.add_edge("choose_flights", "choose_hotel")
travel.add_edge("choose_hotel", END)
travel_graph = travel.compile()


class TripState(TypedDict):
    destination: str
    log: Annotated[list[str], operator.add]


def approve(state: TripState) -> dict:
    return {"log": ["trip approved"]}


parent = StateGraph(TripState)
parent.add_node("travel_team", travel_graph)       # the whole child graph is ONE node here
parent.add_node("approve", approve)
parent.add_edge(START, "travel_team")
parent.add_edge("travel_team", "approve")
parent.add_edge("approve", END)
trip_graph = parent.compile()

if __name__ == "__main__":
    print(trip_graph.invoke({"destination": "BER", "log": []})["log"])
    for ns_, update in trip_graph.stream({"destination": "BER", "log": []}, subgraphs=True, stream_mode="updates"):
        print(ns_, update)                          # ns_ shows which (sub)graph the update came from
