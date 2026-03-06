"""
This node uses an LLM (Groq llama-3.3-70b-versatile) to parse a natural-language food
description into structured food items and their quantities.  It sends state['raw_input']
to the model via langchain_groq and expects a JSON response with two keys: 'foods'
(list of food name strings) and 'quantities' (list of gram floats).  The parsed values
are stored in state['detected_foods'], state['detected_quantities'], and
state['confidence_scores'] (all 1.0 for text-derived inputs).
"""

import json
import os
import logging
from agents.state import NutritionState

logger = logging.getLogger(__name__)

# ── Module-level imports so tests can patch agents.nodes.food_parser.ChatGroq ──
try:
    from langchain_groq import ChatGroq  # type: ignore
    from langchain_core.messages import HumanMessage, SystemMessage  # type: ignore
except ImportError:
    ChatGroq = None  # type: ignore
    HumanMessage = None  # type: ignore
    SystemMessage = None  # type: ignore

# System prompt sent to Groq LLaMA to enforce strict JSON output
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
    Parse state['raw_input'] with Groq LLaMA and populate state['detected_foods'],
    state['detected_quantities'], and state['confidence_scores'].
    """
    if ChatGroq is None:
        state["error"] = "food_parser: langchain_groq is not installed."
        return state

    raw_input: str = state.get("raw_input", "").strip()
    if not raw_input:
        state["error"] = "food_parser: state['raw_input'] is empty."
        return state

    # ── Initialise the Groq LLM ─────────────────────────────────────────────
    llm = ChatGroq(model="llama-3.3-70b-versatile", groq_api_key=os.getenv("GROQ_API_KEY"))

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

    # ── Call Groq LLaMA ──────────────────────────────────────────────────────
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
        state["error"] = f"food_parser: LLM API call failed — {exc}"
        return state

    # ── Parse the JSON response ──────────────────────────────────────────────
    try:
        parsed = json.loads(raw_json)
        foods: list[str] = [str(f) for f in parsed.get("foods", [])]
        quantities: list[float] = [float(q) for q in parsed.get("quantities", [])]
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        state["error"] = (
            f"food_parser: could not parse LLM JSON response — {exc}. "
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
