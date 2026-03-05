"""
This file defines the NutritionState TypedDict that is shared across all nodes in the
LangGraph pipeline. It acts as the single source of truth for all intermediate data
produced and consumed during one agent invocation, including the raw user input,
detected food items, nutrition totals, goal progress, and final recommendations.
Every node reads from and writes to this shared state object.
"""

from typing import TypedDict, Optional, List, Dict, Any


class NutritionState(TypedDict, total=False):
    # ── Identity ──────────────────────────────────────────────────────────────
    user_id: str                          # Supabase user UUID (project: hyejucwqghkujckoshbr)
    raw_input: str                        # Raw text, transcript, or file path from the user

    # ── Routing ───────────────────────────────────────────────────────────────
    input_type: str                       # "text" | "image" | "voice"
    image_path: Optional[str]            # Absolute/relative path to uploaded image; None if N/A

    # ── Food Detection ────────────────────────────────────────────────────────
    detected_foods: List[str]            # e.g. ["chicken breast", "brown rice"]
    detected_quantities: List[float]     # Parallel list of quantities in common units
    confidence_scores: List[float]       # Per-food detection confidence [0.0 – 1.0]

    # ── Nutrition per Meal ────────────────────────────────────────────────────
    nutrition: Dict[str, float]          # {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0}

    # ── Daily Goal & Totals ───────────────────────────────────────────────────
    daily_goal: Dict[str, float]         # {"calorie_goal": 0.0, "protein_goal": 0.0, "carb_goal": 0.0, "fat_goal": 0.0}
    today_total: Dict[str, float]        # Same structure as `nutrition` but accumulated for the full day

    # ── Exercise ──────────────────────────────────────────────────────────────
    exercise_logs: List[Dict[str, Any]]  # List of exercise log dicts from Supabase
    calories_burned: float               # Total kcal burned today from all logged exercises

    # ── Output ────────────────────────────────────────────────────────────────
    recommendation: str                  # LLM-generated dietary/exercise recommendation string
    dashboard_data: Dict[str, Any]       # Aggregated payload sent back to the frontend dashboard

    # ── Error Handling ────────────────────────────────────────────────────────
    error: Optional[str]                 # Human-readable error message; None if no error occurred


# ── Default state factory ──────────────────────────────────────────────────────
def default_nutrition_state() -> NutritionState:
    """
    Returns a NutritionState with every optional/collection field initialised to
    its documented default so that node authors never have to guard against
    KeyError when reading unpopulated fields.
    """
    return NutritionState(
        user_id="",
        raw_input="",
        input_type="text",
        image_path=None,
        detected_foods=[],
        detected_quantities=[],
        confidence_scores=[],
        nutrition={"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0},
        daily_goal={"calorie_goal": 0.0, "protein_goal": 0.0, "carb_goal": 0.0, "fat_goal": 0.0},
        today_total={"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0},
        exercise_logs=[],
        calories_burned=0.0,
        recommendation="",
        dashboard_data={},
        error=None,
    )
