"""
This node uses the Gemini LLM to parse a natural-language food description into
structured food items and their quantities.  It sends state['raw_input'] to
gemini-2.0-flash via langchain_google_genai and expects a JSON response with two
keys: 'foods' (list of food name strings) and 'quantities' (list of gram floats).
The parsed values are stored in state['detected_foods'], state['detected_quantities'],
and state['confidence_scores'] (all 1.0 for text-derived inputs).
"""

import json
import os
import logging
from agents.state import NutritionState

logger = logging.getLogger(__name__)

# System prompt sent to Gemini to enforce strict JSON output
_SYSTEM_PROMPT = (
    "You are a nutrition assistant. "
    "When given a natural-language description of food consumed by a user, "
    "extract all individual food items and their quantities in grams. "
    "Respond ONLY with a valid JSON object — no markdown fences, no extra text. "
    'The JSON must have exactly two keys: "foods" (array of strings) and '
    '"quantities" (array of numbers representing grams). '
    "If a quantity is not mentioned, estimate a reasonable serving size in grams."
)


def food_parser(state: NutritionState) -> NutritionState:
    """
    Parse state['raw_input'] with Gemini and populate state['detected_foods'],
    state['detected_quantities'], and state['confidence_scores'].
    """
    # ── Lazy import ──────────────────────────────────────────────────────────
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        from langchain.schema import HumanMessage, SystemMessage
    except ImportError as exc:  # pragma: no cover
        state["error"] = f"food_parser: missing dependency — {exc}"
        return state

    raw_input: str = state.get("raw_input", "").strip()
    if not raw_input:
        state["error"] = "food_parser: state['raw_input'] is empty."
        return state

    gemini_api_key: str | None = os.environ.get("GEMINI_API_KEY")
    if not gemini_api_key:
        state["error"] = "food_parser: GEMINI_API_KEY environment variable is not set."
        return state

    # ── Initialise the Gemini LLM ────────────────────────────────────────────
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=gemini_api_key,
    )

    # ── Build the prompt ─────────────────────────────────────────────────────
    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(
            content=(
                f"Here is the user's food description:\n\n{raw_input}\n\n"
                "Extract the food items and their quantities in grams. "
                'Return ONLY the JSON object with keys "foods" and "quantities".'
            )
        ),
    ]

    # ── Call Gemini ──────────────────────────────────────────────────────────
    try:
        response = llm.invoke(messages)
        raw_json: str = response.content.strip()

        # Strip possible markdown code fences if the model ignores the instruction
        if raw_json.startswith("```"):
            raw_json = raw_json.split("```")[1]
            if raw_json.startswith("json"):
                raw_json = raw_json[4:]
            raw_json = raw_json.strip()

    except Exception as exc:
        state["error"] = f"food_parser: Gemini API call failed — {exc}"
        return state

    # ── Parse the JSON response ──────────────────────────────────────────────
    try:
        parsed = json.loads(raw_json)
        foods: list[str] = [str(f) for f in parsed.get("foods", [])]
        quantities: list[float] = [float(q) for q in parsed.get("quantities", [])]
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        state["error"] = (
            f"food_parser: could not parse Gemini JSON response — {exc}. "
            f"Raw response was: {raw_json!r}"
        )
        return state

    # Ensure parallel lists have the same length (trim the longer one)
    min_len = min(len(foods), len(quantities))
    foods = foods[:min_len]
    quantities = quantities[:min_len]

    # ── Write results to state ───────────────────────────────────────────────
    state["detected_foods"] = foods
    state["detected_quantities"] = quantities
    # Text-derived items all get confidence 1.0
    state["confidence_scores"] = [1.0] * len(foods)

    logger.info("food_parser: detected %d food item(s): %s", len(foods), foods)
    return state
