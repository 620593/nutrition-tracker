"""
conftest.py — Shared pytest fixtures for all backend tests.

Fixtures:
    sample_state    → a fully-populated NutritionState dict for node tests
    mock_supabase   → a realistic mock Supabase client
"""

import sys
import os

# Ensure backend/ is on sys.path so all imports resolve
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

import pytest
from unittest.mock import MagicMock
from agents.state import default_nutrition_state


# ── sample_state fixture ──────────────────────────────────────────────────────

@pytest.fixture
def sample_state() -> dict:
    """
    Return a fully-populated NutritionState dict that mimics a real mid-pipeline
    state (after food detection and nutrition lookup, before recommender).
    """
    state = default_nutrition_state()
    state.update({
        "user_id": "user-test-001",
        "raw_input": "2 eggs and rice",
        "input_type": "text",
        "image_path": None,
        "detected_foods": ["egg", "rice"],
        "detected_quantities": [100.0, 200.0],
        "confidence_scores": [1.0, 1.0],
        "nutrition": {"calories": 350.0, "protein": 18.0, "carbs": 58.0, "fat": 8.0},
        "daily_goal": {
            "calorie_goal": 2000.0,
            "protein_goal": 80.0,
            "carb_goal": 250.0,
            "fat_goal": 70.0,
        },
        "today_total": {
            "calories": 350.0,
            "protein": 18.0,
            "carbs": 58.0,
            "fat": 8.0,
        },
        "exercise_logs": [
            {"exercise_type": "running", "duration_minutes": 30, "calories_burned": 280.0}
        ],
        "calories_burned": 280.0,
        "dashboard_data": {
            "today_total":    {"calories": 350.0, "protein": 18.0, "carbs": 58.0, "fat": 8.0},
            "daily_goal":     {"calorie_goal": 2000.0, "protein_goal": 80.0, "carb_goal": 250.0, "fat_goal": 70.0},
            "deficits":       {"calories": 1650.0, "protein": 62.0, "carbs": 192.0, "fat": 62.0},
            "calories_burned":280.0,
        },
        "recommendation": "",
        "error": None,
    })
    return state


# ── mock_supabase fixture ─────────────────────────────────────────────────────

@pytest.fixture
def mock_supabase() -> MagicMock:
    """
    Return a fully chainable mock Supabase client that simulates realistic
    per-table responses for users, daily_logs, daily_goals, and exercises.
    """
    client = MagicMock()

    _users = [
        {"id": "user-test-001", "full_name": "Test User", "email": "test@test.com", "weight": 65.0},
        {"id": "user-test-002", "full_name": "Second User", "email": "s@test.com",  "weight": 80.0},
    ]
    _logs = [{
        "user_id":              "user-test-001",
        "log_date":             "2026-03-06",
        "total_calories":       350.0,
        "total_protein":        18.0,
        "total_carbs":          58.0,
        "total_fat":            8.0,
        "total_calories_burned": 280.0,
        "recommendation":       "Try dal and roti!",
    }]
    _goals = [{
        "user_id":      "user-test-001",
        "calorie_goal": 2000.0,
        "protein_goal": 80.0,
        "carb_goal":    250.0,
        "fat_goal":     70.0,
    }]
    _exercises = [{
        "user_id":          "user-test-001",
        "exercise_type":    "running",
        "duration_minutes": 30,
        "calories_burned":  280.0,
    }]

    def _chain(data):
        c = MagicMock()
        for method in ("select", "insert", "update", "upsert", "eq",
                        "order", "limit", "single", "delete"):
            getattr(c, method).return_value = c
        c.execute.return_value = MagicMock(data=data)
        return c

    def _table(name):
        if name == "users":       return _chain(_users)
        if name == "daily_logs":  return _chain(_logs)
        if name == "daily_goals": return _chain(_goals)
        if name == "exercises":   return _chain(_exercises)
        return _chain([])

    client.table.side_effect = _table
    return client
