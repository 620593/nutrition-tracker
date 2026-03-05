"""
This node generates personalised meal recommendations using Gemini-2.0-flash.
It reads the nutrient deficits from state['dashboard_data']['deficits'] and prompts
the model to suggest three Indian hostel-friendly foods that would help the user meet
their remaining daily targets.  The generated text is stored in state['recommendation']
and the full dashboard payload (today_total, daily_goal, recommendation,
calories_burned) is assembled in state['dashboard_data'] for the frontend.
"""

import os
import logging
from agents.state import NutritionState

logger = logging.getLogger(__name__)


def recommender(state: NutritionState) -> NutritionState:
    """
    Call Gemini with deficit context and produce a short, actionable recommendation.
    Populate state['recommendation'] and state['dashboard_data'].
    """
    # ── Lazy import ──────────────────────────────────────────────────────────
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        from langchain_core.messages import HumanMessage, SystemMessage
    except ImportError as exc:  # pragma: no cover
        state["error"] = f"recommender: missing dependency — {exc}"
        return state

    gemini_api_key: str | None = os.environ.get("GEMINI_API_KEY")
    if not gemini_api_key:
        state["error"] = "recommender: GEMINI_API_KEY environment variable is not set."
        return state

    # ── Pull deficit data from state ─────────────────────────────────────────
    dashboard: dict = dict(state.get("dashboard_data") or {})
    deficits: dict = dashboard.get("deficits", {
        "calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0
    })

    calorie_deficit: float = deficits.get("calories", 0.0)
    protein_deficit: float = deficits.get("protein",  0.0)
    carb_deficit:    float = deficits.get("carbs",    0.0)
    fat_deficit:     float = deficits.get("fat",      0.0)

    # ── Build prompt ─────────────────────────────────────────────────────────
    system_prompt = (
        "You are a friendly Indian nutrition coach helping a hostel student "
        "hit their daily nutritional targets. "
        "Suggest foods that are cheap, easy to find in an Indian hostel canteen or "
        "nearby dhaba, and do not require cooking equipment. "
        "Be warm, encouraging, and practical. "
        "Respond in plain conversational English in UNDER 150 words."
    )

    user_prompt = (
        "Based on the user's remaining daily nutritional needs, suggest exactly "
        "THREE specific Indian hostel-friendly foods. "
        "For each food:\n"
        "  1. Name the food clearly.\n"
        "  2. Explain why it helps meet the remaining targets (1 sentence).\n"
        "  3. Suggest a specific quantity (e.g. '2 rotis', '1 bowl', '200 g').\n\n"
        "Remaining daily targets:\n"
        f"  • Calories : {calorie_deficit:.0f} kcal\n"
        f"  • Protein  : {protein_deficit:.1f} g\n"
        f"  • Carbs    : {carb_deficit:.1f} g\n"
        f"  • Fat      : {fat_deficit:.1f} g\n\n"
        "Keep your response under 150 words. No bullet-point headers — "
        "write naturally as if talking to a friend."
    )

    # ── Initialise Gemini ─────────────────────────────────────────────────────
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=gemini_api_key,
    )

    # ── Call the model ────────────────────────────────────────────────────────
    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])
        recommendation: str = response.content.strip()
    except Exception as exc:
        state["error"] = f"recommender: Gemini API call failed — {exc}"
        return state

    # ── Write recommendation to state ─────────────────────────────────────────
    state["recommendation"] = recommendation

    # ── Assemble full dashboard payload for the frontend ──────────────────────
    dashboard["today_total"]    = state.get("today_total", {})
    dashboard["daily_goal"]     = state.get("daily_goal", {})
    dashboard["recommendation"] = recommendation
    dashboard["calories_burned"] = state.get("calories_burned", 0.0)
    state["dashboard_data"] = dashboard

    logger.info("recommender: generated recommendation (%d chars)", len(recommendation))
    return state
