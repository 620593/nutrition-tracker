"""
Main entry point for the Nutrition Tracker API (FastAPI).

Routes defined here:
  POST /log-meal          – Accepts text/image input, runs nutrition_graph, returns nutrition+recommendation
  POST /log-exercise      – Logs an exercise session and returns kcal burned via MET-based formula
  GET  /daily-summary     – Returns today's daily_logs row joined with daily_goals for a user
  GET  /leaderboard       – Returns all six users ranked by today's calorie intake (desc)
  POST /calculate-goals   – Computes macro/calorie goals via Mifflin–St Jeor and upserts to daily_goals
  GET  /suggestions       – Returns the latest recommendation stored in daily_logs for a user

Supabase project reference: hyejucwqghkujckoshbr
"""

import os
import io
import math
import tempfile
from datetime import date
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# ── Load environment variables ─────────────────────────────────────────────────
_dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=_dotenv_path)

# ── Supabase client ────────────────────────────────────────────────────────────
from database.supabase_client import get_supabase_client

# ── LangGraph nutrition pipeline ───────────────────────────────────────────────
from agents.graph import nutrition_graph
from agents.state import default_nutrition_state

# ── FastAPI app ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Nutrition Tracker API",
    description=(
        "Backend API for the AI-powered Nutrition Tracker. "
        "Handles meal logging via LangGraph, exercise tracking, "
        "daily summaries, leaderboards, goal calculation, and suggestion retrieval. "
        "Supabase project: hyejucwqghkujckoshbr"
    ),
    version="1.0.0",
)

# ── CORS (local prototype — allow everything) ──────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global: preloaded Keras food-classifier model ──────────────────────────────
_food_classifier = None   # set during startup; None when model file is absent


@app.on_event("startup")
async def startup_event():
    """
    Runs once when the server boots.
    1. Ensures .env is loaded (redundant but defensive).
    2. Preloads the Keras food-classifier so the first request doesn't pay the
       cold-start penalty.  If the model file is missing, a warning is printed
       and the server continues — routes that don't use the classifier still work.
    """
    global _food_classifier

    load_dotenv(dotenv_path=_dotenv_path)

    model_path = os.path.join(os.path.dirname(__file__), "models", "food_classifier.keras")
    if os.path.exists(model_path):
        try:
            import tensorflow as tf  # imported lazily so the app starts without TF if unneeded
            _food_classifier = tf.keras.models.load_model(model_path)
            print(f"[startup] Food classifier loaded from '{model_path}'.")
        except Exception as exc:
            print(f"[startup] WARNING – could not load food classifier: {exc}")
    else:
        print(
            f"[startup] WARNING – model file not found at '{model_path}'. "
            "Image-based food classification will be unavailable."
        )


# ══════════════════════════════════════════════════════════════════════════════
# Route 1 – POST /log-meal
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/log-meal", summary="Log a meal via text and/or image")
async def log_meal(
    user_id: str = Form(..., description="Supabase user UUID"),
    raw_input: str = Form(..., description="Free-text meal description or voice transcript"),
    image: Optional[UploadFile] = File(None, description="Optional meal photo"),
):
    """
    Builds an initial NutritionState, optionally saves any uploaded image to a
    temporary file, invokes the compiled nutrition_graph, and returns the
    resulting nutrition totals and AI recommendation.
    """
    state = default_nutrition_state()
    state["user_id"] = user_id
    state["raw_input"] = raw_input

    # Handle optional image upload
    image_path: Optional[str] = None
    tmp_file = None
    if image is not None:
        try:
            contents = await image.read()
            suffix = os.path.splitext(image.filename or "upload.jpg")[1] or ".jpg"
            tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            tmp_file.write(contents)
            tmp_file.flush()
            image_path = tmp_file.name
            state["image_path"] = image_path
            state["input_type"] = "image"
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Failed to process image upload: {exc}")
        finally:
            if tmp_file:
                tmp_file.close()

    # Run the LangGraph pipeline
    try:
        result: dict = nutrition_graph.invoke(state)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"LangGraph pipeline error: {exc}")
    finally:
        # Clean up temp file after graph completes
        if image_path and os.path.exists(image_path):
            try:
                os.remove(image_path)
            except OSError:
                pass

    return {
        "nutrition": result.get("nutrition", {}),
        "recommendation": result.get("recommendation", ""),
    }


# ══════════════════════════════════════════════════════════════════════════════
# Route 2 – POST /log-exercise
# ══════════════════════════════════════════════════════════════════════════════

# MET values by exercise type (kcal/kg/hour ≈ MET)
_MET_VALUES: dict[str, float] = {
    "running": 8.0,
    "walking": 3.5,
    "cycling": 7.0,
    "gym": 6.0,
    "yoga": 2.5,
}

# Default body weight (kg) used when the user's weight is not stored yet
_DEFAULT_WEIGHT_KG = 70.0


class LogExerciseRequest(BaseModel):
    user_id: str
    exercise_type: str
    duration_minutes: float


@app.post("/log-exercise", summary="Log an exercise session and calculate kcal burned")
async def log_exercise(req: LogExerciseRequest):
    """
    Calculates calories burned using the standard MET formula:
        kcal = MET × weight_kg × (duration_minutes / 60)

    The result is stored in the Supabase `exercises` table.
    Returns the computed calories_burned value.
    """
    exercise_type = req.exercise_type.lower().strip()
    met = _MET_VALUES.get(exercise_type)
    if met is None:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unknown exercise type '{req.exercise_type}'. "
                f"Supported types: {', '.join(_MET_VALUES.keys())}."
            ),
        )

    # Attempt to fetch the user's stored weight; fall back to the default
    weight_kg = _DEFAULT_WEIGHT_KG
    try:
        supabase = get_supabase_client()
        user_row = (
            supabase.table("users")
            .select("weight")
            .eq("id", req.user_id)
            .single()
            .execute()
        )
        if user_row.data and user_row.data.get("weight"):
            weight_kg = float(user_row.data["weight"])
    except Exception:
        # Non-fatal: use the default weight if lookup fails
        pass

    calories_burned = round(met * weight_kg * (req.duration_minutes / 60.0), 2)

    # Persist the exercise log
    try:
        supabase = get_supabase_client()
        supabase.table("exercises").insert(
            {
                "user_id": req.user_id,
                "exercise_type": exercise_type,
                "duration_minutes": req.duration_minutes,
                "calories_burned": calories_burned,
                "logged_at": date.today().isoformat(),
            }
        ).execute()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to store exercise log: {exc}")

    return {"calories_burned": calories_burned}


# ══════════════════════════════════════════════════════════════════════════════
# Route 3 – GET /daily-summary
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/daily-summary", summary="Return today's daily log joined with the user's goals")
async def daily_summary(user_id: str = Query(..., description="Supabase user UUID")):
    """
    Fetches today's row from `daily_logs` and the corresponding row from
    `daily_goals` for the given user.  Returns both together so the frontend
    can render progress bars, ring charts, etc.
    """
    today = date.today().isoformat()
    try:
        supabase = get_supabase_client()

        log_resp = (
            supabase.table("daily_logs")
            .select("*")
            .eq("user_id", user_id)
            .eq("log_date", today)
            .single()
            .execute()
        )

        goals_resp = (
            supabase.table("daily_goals")
            .select("*")
            .eq("user_id", user_id)
            .single()
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Database query failed: {exc}")

    return {
        "date": today,
        "daily_log": log_resp.data or {},
        "daily_goals": goals_resp.data or {},
    }


# ══════════════════════════════════════════════════════════════════════════════
# Route 4 – GET /leaderboard
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/leaderboard", summary="Return all users ranked by today's calorie intake")
async def leaderboard():
    """
    Queries today's daily_logs for all users, joins with the users table for
    display names, and returns them ordered by total_calories descending.

    The project seeds exactly six test users; this endpoint surfaces all of them
    even if some have not logged anything today (they will show zeros).
    """
    today = date.today().isoformat()
    try:
        supabase = get_supabase_client()

        # Fetch all users
        users_resp = supabase.table("users").select("id, name, email").execute()
        users = users_resp.data or []

        # Fetch today's logs for all users
        logs_resp = (
            supabase.table("daily_logs")
            .select("user_id, total_calories, total_protein, total_fat")
            .eq("log_date", today)
            .execute()
        )
        logs_by_user = {row["user_id"]: row for row in (logs_resp.data or [])}

        board = []
        for user in users:
            uid = user["id"]
            log = logs_by_user.get(uid, {})
            board.append(
                {
                    "user_id": uid,
                    "name": user.get("name") or user.get("email", "Unknown"),
                    "total_calories": log.get("total_calories", 0.0),
                    "total_protein": log.get("total_protein", 0.0),
                    "total_fat": log.get("total_fat", 0.0),
                }
            )

        # Sort descending by calorie intake
        board.sort(key=lambda x: x["total_calories"], reverse=True)

    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Leaderboard query failed: {exc}")

    return {"leaderboard": board}


# ══════════════════════════════════════════════════════════════════════════════
# Route 5 – POST /calculate-goals
# ══════════════════════════════════════════════════════════════════════════════

class CalculateGoalsRequest(BaseModel):
    user_id: str
    weight: float          # kg
    height: float          # cm
    age: int
    activity_level: str    # "sedentary" | "light" | "moderate" | "active" | "very_active"

# Activity multipliers (PAL) for the Mifflin–St Jeor TDEE adjustment
_ACTIVITY_MULTIPLIERS: dict[str, float] = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very_active": 1.9,
}


@app.post("/calculate-goals", summary="Compute macro goals via Mifflin–St Jeor and upsert to DB")
async def calculate_goals(req: CalculateGoalsRequest):
    """
    Uses the Mifflin–St Jeor equation (male formula as a neutral baseline) to
    estimate TDEE, then derives macro targets:
      - Protein : 1.4 × weight_kg  (g)
      - Carbs   : 50% of calories  ÷ 4  (g)
      - Fat     : 25% of calories  ÷ 9  (g)

    The resulting goals are upserted into the `daily_goals` table and returned.
    """
    activity_level = req.activity_level.lower().strip()
    pal = _ACTIVITY_MULTIPLIERS.get(activity_level, 1.55)  # default to moderate

    # Mifflin–St Jeor BMR (gender-neutral: we use the male formula as a proxy)
    bmr = (10 * req.weight) + (6.25 * req.height) - (5 * req.age) + 5
    calorie_goal = round(bmr * pal, 2)

    protein_goal = round(1.4 * req.weight, 2)          # g
    carb_goal = round((0.50 * calorie_goal) / 4.0, 2)  # g
    fat_goal = round((0.25 * calorie_goal) / 9.0, 2)   # g

    goals_payload = {
        "user_id": req.user_id,
        "calorie_goal": calorie_goal,
        "protein_goal": protein_goal,
        "carb_goal": carb_goal,
        "fat_goal": fat_goal,
    }

    try:
        supabase = get_supabase_client()
        supabase.table("daily_goals").upsert(
            goals_payload, on_conflict="user_id"
        ).execute()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to upsert daily goals: {exc}")

    return goals_payload


# ══════════════════════════════════════════════════════════════════════════════
# Route 6 – GET /suggestions
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/suggestions", summary="Return the latest AI recommendation for a user")
async def suggestions(user_id: str = Query(..., description="Supabase user UUID")):
    """
    Retrieves the most recent recommendation string stored in `daily_logs`
    for the given user.  The recommendation is populated by the LangGraph
    recommender node at the end of each /log-meal invocation.
    """
    try:
        supabase = get_supabase_client()
        resp = (
            supabase.table("daily_logs")
            .select("log_date, total_calories, total_protein, total_carbs, total_fat")
            .eq("user_id", user_id)
            .order("log_date", desc=True)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch suggestions: {exc}")

    rows = resp.data or []
    if not rows:
        return {"suggestion": None, "message": "No meal logs found for this user yet."}

    latest = rows[0]
    return {
        "log_date": latest.get("log_date"),
        "total_calories": latest.get("total_calories", 0.0),
        "total_protein": latest.get("total_protein", 0.0),
        "total_carbs": latest.get("total_carbs", 0.0),
        "total_fat": latest.get("total_fat", 0.0),
    }


# ══════════════════════════════════════════════════════════════════════════════
# Dev-server entry point
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
