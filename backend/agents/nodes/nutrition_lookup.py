"""
This node fetches nutritional data from the USDA FoodData Central API for each food item
detected in state['detected_foods'].  Per-100 g macros (calories, protein, carbs, fat) are
retrieved from the first search result and scaled to the actual portion size recorded in
state['detected_quantities'].  All foods are summed into a single nutrition dict that is
stored in state['nutrition'].  If the API returns no result for a food, hardcoded fallback
values are used and a warning is logged.
"""

import os
import logging
import httpx
from agents.state import NutritionState

logger = logging.getLogger(__name__)

USDA_BASE_URL = "https://api.nal.usda.gov/fdc/v1"

# Fallback values (per actual quantity, i.e. already scaled) used when a food is not found.
_FALLBACK_PER_100G = {"calories": 100.0, "protein": 5.0, "carbs": 15.0, "fat": 3.0}


def _fetch_nutrients_per_100g(food_name: str, api_key: str) -> dict[str, float]:
    """
    Query the USDA /foods/search endpoint and return macros per 100 g for the
    first result.  Returns the fallback dict if no results are found or if the
    API call fails.
    """
    try:
        response = httpx.get(
            f"{USDA_BASE_URL}/foods/search",
            params={
                "query": food_name,
                "pageSize": 1,
                "api_key": api_key,
            },
            timeout=10.0,
        )
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPError as exc:
        raise RuntimeError(f"USDA API network error for '{food_name}': {exc}") from exc

    foods = data.get("foods", [])
    if not foods:
        logger.warning(
            "nutrition_lookup: no USDA result for '%s' — using fallback values.",
            food_name,
        )
        return dict(_FALLBACK_PER_100G)

    food_item = foods[0]
    nutrients_raw = food_item.get("foodNutrients", [])

    # USDA nutrient IDs for the four macros we care about
    NUTRIENT_ID_MAP = {
        1008: "calories",   # Energy (kcal)
        1003: "protein",    # Protein (g)
        1005: "carbs",      # Carbohydrate, by difference (g)
        1004: "fat",        # Total lipid (fat) (g)
    }

    per_100g: dict[str, float] = {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0}
    for nutrient in nutrients_raw:
        nid = nutrient.get("nutrientId")
        if nid in NUTRIENT_ID_MAP:
            key = NUTRIENT_ID_MAP[nid]
            per_100g[key] = float(nutrient.get("value", 0.0))

    return per_100g


def nutrition_lookup(state: NutritionState) -> NutritionState:
    """
    For each food in state['detected_foods'], fetch USDA nutritional data, scale by
    the corresponding quantity in state['detected_quantities'], and accumulate totals
    into state['nutrition'].
    """
    api_key: str | None = os.environ.get("USDA_API_KEY")
    if not api_key:
        state["error"] = "nutrition_lookup: USDA_API_KEY environment variable is not set."
        return state

    detected_foods: list[str] = state.get("detected_foods", [])
    detected_quantities: list[float] = state.get("detected_quantities", [])

    if not detected_foods:
        state["error"] = "nutrition_lookup: no foods to look up (detected_foods is empty)."
        return state

    # Ensure quantities list matches foods length (default 100 g if missing)
    quantities: list[float] = list(detected_quantities)
    while len(quantities) < len(detected_foods):
        quantities.append(100.0)

    totals: dict[str, float] = {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0}

    for food, qty in zip(detected_foods, quantities):
        try:
            per_100g = _fetch_nutrients_per_100g(food, api_key)
        except RuntimeError as exc:
            # Network error — abort and surface the error
            state["error"] = str(exc)
            return state

        scale = qty / 100.0
        for key in totals:
            totals[key] += per_100g[key] * scale

    # Round to two decimal places for cleanliness
    state["nutrition"] = {k: round(v, 2) for k, v in totals.items()}

    logger.info(
        "nutrition_lookup: computed nutrition for %d food(s): %s",
        len(detected_foods),
        state["nutrition"],
    )
    return state
