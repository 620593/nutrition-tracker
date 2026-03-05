"""
This file defines and compiles the LangGraph StateGraph that powers the Nutrition Tracker
AI agent pipeline. It wires together all processing nodes (input router, STT, food parser,
image detector, nutrition lookup, goal analyzer, and recommender) with conditional edges
based on the user's input type. The compiled graph object `nutrition_graph` is ready to
receive user messages and stream structured NutritionState responses.

Supabase project reference: hyejucwqghkujckoshbr
"""

from langgraph.graph import StateGraph, END

from agents.state import NutritionState
from agents.nodes.input_router import input_router
from agents.nodes.stt_node import stt_node
from agents.nodes.food_parser import food_parser
from agents.nodes.image_detector import image_detector
from agents.nodes.nutrition_lookup import nutrition_lookup
from agents.nodes.goal_analyzer import goal_analyzer
from agents.nodes.recommender import recommender


# ── Routing helper ─────────────────────────────────────────────────────────────

def _route_by_input_type(state: NutritionState) -> str:
    """
    Conditional edge function called after input_router.
    Inspects state["input_type"] and returns the name of the next node.
    """
    input_type = state.get("input_type", "text")
    if input_type == "voice":
        return "stt_node"
    if input_type == "image":
        return "image_detector"
    # Default: plain text
    return "food_parser"


# ── Graph construction ─────────────────────────────────────────────────────────

_builder = StateGraph(NutritionState)

# Nodes — added in the required order
_builder.add_node("input_router", input_router)
_builder.add_node("stt_node", stt_node)
_builder.add_node("food_parser", food_parser)
_builder.add_node("image_detector", image_detector)
_builder.add_node("nutrition_lookup", nutrition_lookup)
_builder.add_node("goal_analyzer", goal_analyzer)
_builder.add_node("recommender", recommender)

# Entry point
_builder.set_entry_point("input_router")

# Conditional edge: input_router → stt_node | image_detector | food_parser
_builder.add_conditional_edges(
    "input_router",
    _route_by_input_type,
    {
        "stt_node": "stt_node",
        "image_detector": "image_detector",
        "food_parser": "food_parser",
    },
)

# Normal edges
_builder.add_edge("stt_node", "food_parser")
_builder.add_edge("food_parser", "nutrition_lookup")
_builder.add_edge("image_detector", "nutrition_lookup")
_builder.add_edge("nutrition_lookup", "goal_analyzer")
_builder.add_edge("goal_analyzer", "recommender")
_builder.add_edge("recommender", END)

# Compile — the public-facing graph object used throughout the application
nutrition_graph = _builder.compile()
