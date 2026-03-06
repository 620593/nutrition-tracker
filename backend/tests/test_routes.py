"""
test_routes.py — Integration tests for all 6 FastAPI routes.

Uses FastAPI's TestClient with all Supabase calls mocked via dependency_overrides
and unittest.mock.patch so tests run without a real database connection.
The LangGraph pipeline is also mocked for the /log-meal route.
"""

import sys
import os
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

# Ensure backend/ is on sys.path
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)


# ── Build a realistic mock Supabase client ────────────────────────────────────

def _make_mock_supabase():
    """Fully chainable mock Supabase client with realistic per-table data."""
    client = MagicMock()

    _users = [
        {"id": "u1", "full_name": "Alice", "email": "alice@test.com", "weight": 60.0},
        {"id": "u2", "full_name": "Bob",   "email": "bob@test.com",   "weight": 75.0},
    ]
    _logs = [{
        "user_id": "u1", "log_date": "2026-03-06",
        "total_calories": 350.0, "total_protein": 18.0,
        "total_carbs": 58.0, "total_fat": 8.0, "total_calories_burned": 0.0,
    }]
    _goals = [{"user_id": "u1", "calorie_goal": 2000.0, "protein_goal": 80.0, "carb_goal": 250.0, "fat_goal": 70.0}]

    def _chain(data):
        c = MagicMock()
        c.select.return_value = c
        c.insert.return_value = c
        c.update.return_value = c
        c.upsert.return_value = c
        c.eq.return_value = c
        c.order.return_value = c
        c.limit.return_value = c
        c.single.return_value = c
        c.execute.return_value = MagicMock(data=data)
        return c

    def _table(name):
        if name == "users":      return _chain(_users)
        if name == "daily_logs": return _chain(_logs)
        if name == "daily_goals":return _chain(_goals)
        return _chain([])

    client.table.side_effect = _table
    return client


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    """
    Create a TestClient.

    Patches:
    - database.supabase_client.get_supabase_client → mock Supabase
    - agents.graph.nutrition_graph (imported into main) → mock graph
    """
    mock_sb = _make_mock_supabase()

    mock_graph = MagicMock()
    mock_graph.invoke.return_value = {
        "nutrition": {"calories": 350.0, "protein": 18.0, "carbs": 58.0, "fat": 8.0},
        "recommendation": "Try dal and roti for dinner!",
    }

    # Patch the Supabase factory at its source so every call in main.py uses the mock
    with patch("database.supabase_client.get_supabase_client", return_value=mock_sb):
        # Patch the compiled graph object that main.py imported
        with patch("agents.graph.nutrition_graph", mock_graph):
            from main import app           # import AFTER patches are active
            import main as main_mod
            main_mod.nutrition_graph = mock_graph   # also replace the reference main holds
            client = TestClient(app, raise_server_exceptions=False)
            yield client


# ══════════════════════════════════════════════════════════════════════════════
# Route 1 — POST /log-meal
# ══════════════════════════════════════════════════════════════════════════════

class TestLogMeal:
    def test_text_returns_200(self, client):
        response = client.post("/log-meal", data={"user_id": "u1", "raw_input": "2 eggs and rice"})
        assert response.status_code == 200, response.text
        body = response.json()
        assert "nutrition" in body
        assert "recommendation" in body

    def test_nutrition_has_required_keys(self, client):
        response = client.post("/log-meal", data={"user_id": "u1", "raw_input": "banana"})
        nutrition = response.json().get("nutrition", {})
        assert "calories" in nutrition
        assert "protein" in nutrition

    def test_missing_user_id_returns_422(self, client):
        response = client.post("/log-meal", data={"raw_input": "2 eggs"})
        assert response.status_code == 422

    def test_missing_raw_input_returns_422(self, client):
        response = client.post("/log-meal", data={"user_id": "u1"})
        assert response.status_code == 422


# ══════════════════════════════════════════════════════════════════════════════
# Route 2 — POST /log-exercise
# ══════════════════════════════════════════════════════════════════════════════

class TestLogExercise:
    def test_running_30_min_returns_positive_calories(self, client):
        response = client.post(
            "/log-exercise",
            json={"user_id": "u1", "exercise_type": "running", "duration_minutes": 30},
        )
        assert response.status_code == 200, response.text
        assert response.json()["calories_burned"] > 0

    def test_walking_burns_less_than_running(self, client):
        run  = client.post("/log-exercise", json={"user_id": "u1", "exercise_type": "running", "duration_minutes": 30})
        walk = client.post("/log-exercise", json={"user_id": "u1", "exercise_type": "walking", "duration_minutes": 30})
        assert run.json()["calories_burned"] > walk.json()["calories_burned"]

    def test_unknown_exercise_returns_400(self, client):
        response = client.post(
            "/log-exercise",
            json={"user_id": "u1", "exercise_type": "skydiving", "duration_minutes": 30},
        )
        assert response.status_code == 400

    def test_all_supported_types_return_200(self, client):
        for ex in ["running", "walking", "cycling", "gym", "yoga"]:
            r = client.post("/log-exercise", json={"user_id": "u1", "exercise_type": ex, "duration_minutes": 30})
            assert r.status_code == 200, f"{ex} failed: {r.text}"


# ══════════════════════════════════════════════════════════════════════════════
# Route 3 — POST /calculate-goals
# ══════════════════════════════════════════════════════════════════════════════

class TestCalculateGoals:
    _VALID = {"user_id": "u1", "weight": 70.0, "height": 175.0, "age": 25, "activity_level": "moderate"}

    def test_valid_inputs_return_200(self, client):
        response = client.post("/calculate-goals", json=self._VALID)
        assert response.status_code == 200, response.text

    def test_calorie_goal_greater_than_1000(self, client):
        response = client.post("/calculate-goals", json=self._VALID)
        assert response.json()["calorie_goal"] > 1000.0

    def test_response_has_all_macro_keys(self, client):
        response = client.post("/calculate-goals", json=self._VALID)
        body = response.json()
        for key in ("calorie_goal", "protein_goal", "carb_goal", "fat_goal"):
            assert key in body, f"Missing key: {key}"

    def test_missing_required_field_returns_422(self, client):
        response = client.post("/calculate-goals", json={"user_id": "u1", "weight": 70.0})
        assert response.status_code == 422

    def test_very_active_has_higher_goal_than_sedentary(self, client):
        active    = dict(self._VALID, activity_level="very_active")
        sedentary = dict(self._VALID, activity_level="sedentary")
        r_a = client.post("/calculate-goals", json=active)
        r_s = client.post("/calculate-goals", json=sedentary)
        assert r_a.json()["calorie_goal"] > r_s.json()["calorie_goal"]


# ══════════════════════════════════════════════════════════════════════════════
# Route 4 — GET /leaderboard
# ══════════════════════════════════════════════════════════════════════════════

class TestLeaderboard:
    def test_returns_200(self, client):
        assert client.get("/leaderboard").status_code == 200

    def test_returns_leaderboard_list(self, client):
        body = client.get("/leaderboard").json()
        assert "leaderboard" in body
        assert isinstance(body["leaderboard"], list)

    def test_entries_have_required_fields(self, client):
        board = client.get("/leaderboard").json().get("leaderboard", [])
        if board:
            for key in ("user_id", "name", "total_calories"):
                assert key in board[0], f"Missing: {key}"

    def test_sorted_descending_by_calories(self, client):
        board = client.get("/leaderboard").json().get("leaderboard", [])
        cals = [e["total_calories"] for e in board]
        assert cals == sorted(cals, reverse=True)


# ══════════════════════════════════════════════════════════════════════════════
# Route 5 — GET /daily-summary
# ══════════════════════════════════════════════════════════════════════════════

class TestDailySummary:
    def test_returns_200_valid_user(self, client):
        assert client.get("/daily-summary", params={"user_id": "u1"}).status_code == 200

    def test_response_structure(self, client):
        body = client.get("/daily-summary", params={"user_id": "u1"}).json()
        assert "date" in body
        assert "daily_log" in body
        assert "daily_goals" in body

    def test_missing_user_id_returns_422(self, client):
        assert client.get("/daily-summary").status_code == 422


# ══════════════════════════════════════════════════════════════════════════════
# Route 6 — GET /suggestions
# ══════════════════════════════════════════════════════════════════════════════

class TestSuggestions:
    def test_returns_200_valid_user(self, client):
        assert client.get("/suggestions", params={"user_id": "u1"}).status_code == 200

    def test_response_has_expected_keys(self, client):
        body = client.get("/suggestions", params={"user_id": "u1"}).json()
        assert ("log_date" in body) or ("message" in body)

    def test_missing_user_id_returns_422(self, client):
        assert client.get("/suggestions").status_code == 422
