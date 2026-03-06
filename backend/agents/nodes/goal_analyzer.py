"""
This node compares today's accumulated nutritional intake against the user's daily goals
stored in Supabase.  It queries the 'daily_goals' table for the user's targets and the
'daily_logs' table for today's running totals.  If no log row exists for today it inserts
one at zero.  It then adds state['nutrition'] to the running totals, writes the updated
row back to Supabase, and stores the deficit for each macro in state['dashboard_data'].
"""

import os
import logging
from datetime import date, datetime
from agents.state import NutritionState

logger = logging.getLogger(__name__)


def _get_supabase():
    """Initialise and return a Supabase client using environment variables."""
    try:
        from supabase import create_client, Client  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "supabase-py is not installed. Add it to requirements.txt."
        ) from exc

    url: str | None = os.environ.get("SUPABASE_URL")
    service_key: str | None = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not service_key:
        raise EnvironmentError(
            "goal_analyzer: SUPABASE_URL and/or SUPABASE_SERVICE_ROLE_KEY "
            "environment variables are not set."
        )

    return create_client(url, service_key)


def goal_analyzer(state: NutritionState) -> NutritionState:
    """
    1. Fetch the user's daily_goal row from Supabase.
    2. Fetch (or create) today's daily_log row.
    3. Add state['nutrition'] to the log totals and upsert the row.
    4. Calculate deficits and populate state['dashboard_data']['deficits'].
    """
    user_id: str = state.get("user_id", "")
    if not user_id:
        state["error"] = "goal_analyzer: state['user_id'] is empty."
        return state

    new_nutrition: dict = state.get("nutrition", {
        "calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0
    })
    today_str: str = date.today().isoformat()   # e.g. "2026-03-05"

    try:
        supabase = _get_supabase()
    except (ImportError, EnvironmentError) as exc:
        state["error"] = str(exc)
        return state

    # ── 1. Fetch the user's daily goal ────────────────────────────────────────
    try:
        goal_resp = (
            supabase.table("daily_goals")
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )
        goal_rows = goal_resp.data or []
    except Exception as exc:
        state["error"] = f"goal_analyzer: failed to query daily_goals — {exc}"
        return state

    if not goal_rows:
        # Provide sensible defaults if the user hasn't set goals yet
        daily_goal: dict = {
            "calorie_goal": 2000.0,
            "protein_goal": 50.0,
            "carb_goal": 250.0,
            "fat_goal": 70.0,
        }
        logger.warning("goal_analyzer: no daily_goals row for user %s — using defaults.", user_id)
    else:
        g = goal_rows[0]
        daily_goal = {
            "calorie_goal": float(g.get("calorie_goal", 2000.0)),
            "protein_goal": float(g.get("protein_goal", 50.0)),
            "carb_goal": float(g.get("carb_goal", 250.0)),
            "fat_goal": float(g.get("fat_goal", 70.0)),
        }

    # ── 2. Fetch today's daily_log row ────────────────────────────────────────
    try:
        log_resp = (
            supabase.table("daily_logs")
            .select("*")
            .eq("user_id", user_id)
            .eq("log_date", today_str)
            .execute()
        )
        log_rows = log_resp.data or []
    except Exception as exc:
        state["error"] = f"goal_analyzer: failed to query daily_logs — {exc}"
        return state

    if not log_rows:
        # Insert a blank log row for today
        blank_log = {
            "user_id": user_id,
            "log_date": today_str,
            "total_calories": 0.0,
            "total_protein": 0.0,
            "total_carbs": 0.0,
            "total_fat": 0.0,
        }
        try:
            insert_resp = (
                supabase.table("daily_logs")
                .insert(blank_log)
                .execute()
            )
            existing_log = (insert_resp.data or [blank_log])[0]
        except Exception as exc:
            state["error"] = f"goal_analyzer: failed to insert daily_log — {exc}"
            return state
    else:
        existing_log = log_rows[0]

    # ── 3. Add the current meal's nutrition to the running daily totals ────────
    updated_totals = {
        "total_calories": float(existing_log.get("total_calories", 0.0)) + new_nutrition.get("calories", 0.0),
        "total_protein":  float(existing_log.get("total_protein",  0.0)) + new_nutrition.get("protein",  0.0),
        "total_carbs":    float(existing_log.get("total_carbs",    0.0)) + new_nutrition.get("carbs",    0.0),
        "total_fat":      float(existing_log.get("total_fat",      0.0)) + new_nutrition.get("fat",      0.0),
    }

    # Upsert (update) the daily_log row with the new totals
    try:
        supabase.table("daily_logs").update(updated_totals).eq(
            "user_id", user_id
        ).eq("log_date", today_str).execute()
    except Exception as exc:
        state["error"] = f"goal_analyzer: failed to update daily_log — {exc}"
        return state

    # ── 4. Map into standardised state keys ──────────────────────────────────
    today_total = {
        "calories": round(updated_totals["total_calories"], 2),
        "protein":  round(updated_totals["total_protein"],  2),
        "carbs":    round(updated_totals["total_carbs"],    2),
        "fat":      round(updated_totals["total_fat"],      2),
    }

    # Deficits: goal minus actual (positive = still needed, negative = exceeded)
    deficits = {
        "calories": round(daily_goal["calorie_goal"] - today_total["calories"], 2),
        "protein":  round(daily_goal["protein_goal"] - today_total["protein"],  2),
        "carbs":    round(daily_goal["carb_goal"]    - today_total["carbs"],    2),
        "fat":      round(daily_goal["fat_goal"]     - today_total["fat"],      2),
    }

    # ── Write to state ────────────────────────────────────────────────────────
    state["today_total"] = today_total
    state["daily_goal"] = daily_goal

    dashboard = dict(state.get("dashboard_data") or {})
    dashboard["deficits"] = deficits
    state["dashboard_data"] = dashboard

    logger.info(
        "goal_analyzer: user=%s today_total=%s deficits=%s",
        user_id, today_total, deficits,
    )
    return state
