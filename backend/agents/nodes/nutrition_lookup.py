"""
This node fetches nutritional data from the USDA FoodData Central API for each food item
detected in state['detected_foods'].  Per-100 g macros (calories, protein, carbs, fat) are
retrieved from the search results and scaled to the actual portion size recorded in
state['detected_quantities'].  All foods are summed into a single nutrition dict that is
stored in state['nutrition'].

The USDA search filters to Foundation and SR Legacy data types to avoid branded/junk results.
If the first result returns zero for all nutrients, the second result is tried before falling
back to hardcoded values.  If the API returns no result at all, hardcoded fallback values are
used and a warning is logged.
"""

import os
import logging
import httpx
from agents.state import NutritionState

logger = logging.getLogger(__name__)

USDA_BASE_URL = "https://api.nal.usda.gov/fdc/v1"

# Fallback values (per 100 g) used when a food is not found or has zero nutrition data.
_FALLBACK_PER_100G = {"calories": 100.0, "protein": 5.0, "carbs": 15.0, "fat": 3.0}

# USDA nutrient IDs for the four macros we care about
_NUTRIENT_ID_MAP = {
    1008: "calories",   # Energy (kcal)
    1003: "protein",    # Protein (g)
    1005: "carbs",      # Carbohydrate, by difference (g)
    1004: "fat",        # Total lipid (fat) (g)
}


def _extract_nutrients(food_item: dict) -> dict[str, float]:
    """
    Extract macro nutrients from a single USDA food item dict.
    Returns a dict with keys: calories, protein, carbs, fat.
    All values default to 0.0 if the nutrient is not present.
    """
    nutrients_raw = food_item.get("foodNutrients", [])
    per_100g: dict[str, float] = {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0}
    for nutrient in nutrients_raw:
        nid = nutrient.get("nutrientId")
        if nid in _NUTRIENT_ID_MAP:
            key = _NUTRIENT_ID_MAP[nid]
            per_100g[key] = float(nutrient.get("value", 0.0))
    return per_100g


def _is_zero_nutrition(per_100g: dict[str, float]) -> bool:
    """Return True if all macro values are zero (likely a branded food with missing data)."""
    return all(v == 0.0 for v in per_100g.values())


def _fetch_nutrients_per_100g(food_name: str, api_key: str) -> dict[str, float]:
    """
    Query the USDA /foods/search endpoint and return macros per 100 g.

    Search is filtered to Foundation and SR Legacy data types to avoid branded candy
    and other junk results.  If the first result has all-zero nutrients, the second
    result is tried before using the hardcoded fallback.

    Returns the fallback dict if:
    - No results are found
    - The API call fails
    - All fetched results have zero nutrition data
    """
    try:
        response = httpx.get(
            f"{USDA_BASE_URL}/foods/search",
            params={
                "query": food_name,
                "dataType": "Foundation,SR Legacy",
                "pageSize": 5,
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

    # Try results in order until we find one with non-zero nutrition
    for i, food_item in enumerate(foods[:5]):
        per_100g = _extract_nutrients(food_item)
        if not _is_zero_nutrition(per_100g):
            if i > 0:
                logger.info(
                    "nutrition_lookup: result[0] had zero nutrients for '%s'; used result[%d].",
                    food_name, i,
                )
            return per_100g

    # All results had zero nutrition — use fallback
    logger.warning(
        "nutrition_lookup: all %d USDA results for '%s' had zero nutrition — using fallback values.",
        len(foods[:5]),
        food_name,
    )
    return dict(_FALLBACK_PER_100G)


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
