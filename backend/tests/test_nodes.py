"""
test_nodes.py — Unit tests for all 7 LangGraph nodes.

All external API calls (Groq LLM, USDA API, Supabase, HuggingFace) are mocked
using pytest monkeypatch / unittest.mock so tests run without real credentials.
"""

import sys
import os
import json
import pytest
from unittest.mock import MagicMock, patch, PropertyMock

# Ensure backend/ is on sys.path
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from agents.state import default_nutrition_state


# ══════════════════════════════════════════════════════════════════════════════
# 1. input_router
# ══════════════════════════════════════════════════════════════════════════════

class TestInputRouter:
    """Tests for agents/nodes/input_router.py — pure logic, no mocks needed."""

    def _state(self, raw_input="", image_path=None):
        s = default_nutrition_state()
        s["raw_input"] = raw_input
        s["image_path"] = image_path
        return s

    def test_text_input_sets_text_type(self):
        from agents.nodes.input_router import input_router
        result = input_router(self._state(raw_input="2 eggs and rice"))
        assert result["input_type"] == "text"

    def test_image_path_sets_image_type(self):
        from agents.nodes.input_router import input_router
        result = input_router(self._state(image_path="/tmp/meal.jpg"))
        assert result["input_type"] == "image"

    def test_audio_prefix_sets_voice_type(self):
        from agents.nodes.input_router import input_router
        result = input_router(self._state(raw_input="AUDIO_FILE:/tmp/voice.wav"))
        assert result["input_type"] == "voice"
        assert result["image_path"] == "/tmp/voice.wav"

    def test_image_takes_priority_over_audio(self):
        from agents.nodes.input_router import input_router
        result = input_router(self._state(raw_input="AUDIO_FILE:/tmp/voice.wav", image_path="/tmp/food.jpg"))
        assert result["input_type"] == "image"

    def test_empty_input_defaults_to_text(self):
        from agents.nodes.input_router import input_router
        result = input_router(self._state(raw_input=""))
        assert result["input_type"] == "text"


# ══════════════════════════════════════════════════════════════════════════════
# 2. food_parser
# ══════════════════════════════════════════════════════════════════════════════

class TestFoodParser:
    """Tests for agents/nodes/food_parser.py — Groq LLM patched directly."""

    def _state(self, raw_input="2 eggs and rice"):
        s = default_nutrition_state()
        s["raw_input"] = raw_input
        return s

    def _mock_llm_response(self, foods, quantities):
        payload = json.dumps({"foods": foods, "quantities": quantities})
        mock_msg = MagicMock()
        mock_msg.content = payload
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_msg
        return mock_llm

    def test_parses_two_eggs_and_rice(self):
        mock_llm = self._mock_llm_response(["egg", "rice"], [100.0, 200.0])
        with patch("agents.nodes.food_parser.ChatGroq", return_value=mock_llm):
            from agents.nodes.food_parser import food_parser
            result = food_parser(self._state("2 eggs and rice"))
        assert len(result.get("detected_foods", [])) >= 2
        assert len(result.get("detected_quantities", [])) == len(result["detected_foods"])

    def test_quantities_same_length_as_foods(self):
        mock_llm = self._mock_llm_response(["dal", "roti", "sabzi"], [150.0, 80.0, 100.0])
        with patch("agents.nodes.food_parser.ChatGroq", return_value=mock_llm):
            from agents.nodes.food_parser import food_parser
            result = food_parser(self._state("dal roti and sabzi"))
        assert len(result.get("detected_foods", [])) == len(result.get("detected_quantities", []))

    def test_empty_raw_input_sets_error(self):
        from agents.nodes.food_parser import food_parser
        s = default_nutrition_state()
        s["raw_input"] = ""
        result = food_parser(s)
        assert result.get("error") is not None

    def test_confidence_scores_all_one_for_text(self):
        mock_llm = self._mock_llm_response(["banana"], [120.0])
        with patch("agents.nodes.food_parser.ChatGroq", return_value=mock_llm):
            from agents.nodes.food_parser import food_parser
            result = food_parser(self._state("banana"))
        for score in result.get("confidence_scores", []):
            assert score == 1.0

    def test_invalid_json_sets_error(self):
        mock_msg = MagicMock()
        mock_msg.content = "NOT VALID JSON {{"
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_msg
        with patch("agents.nodes.food_parser.ChatGroq", return_value=mock_llm):
            from agents.nodes.food_parser import food_parser
            result = food_parser(self._state("scrambled eggs"))
        assert result.get("error") is not None

    def test_llm_exception_sets_error(self):
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("Groq quota exceeded")
        with patch("agents.nodes.food_parser.ChatGroq", return_value=mock_llm):
            from agents.nodes.food_parser import food_parser
            result = food_parser(self._state("rice"))
        assert result.get("error") is not None
        assert "LLM API call failed" in result["error"]


# ══════════════════════════════════════════════════════════════════════════════
# 3. nutrition_lookup
# ══════════════════════════════════════════════════════════════════════════════

class TestNutritionLookup:
    """Tests for agents/nodes/nutrition_lookup.py — USDA HTTP calls patched."""

    def _state(self, foods, quantities):
        s = default_nutrition_state()
        s["detected_foods"] = foods
        s["detected_quantities"] = quantities
        return s

    def _usda_mock(self, calories=155.0, protein=13.0, carbs=1.1, fat=11.0):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "foods": [{
                "fdcId": 748967,
                "description": "Egg, whole, raw",
                "dataType": "SR Legacy",
                "foodNutrients": [
                    {"nutrientId": 1008, "value": calories},
                    {"nutrientId": 1003, "value": protein},
                    {"nutrientId": 1005, "value": carbs},
                    {"nutrientId": 1004, "value": fat},
                ],
            }]
        }
        return mock_resp

    def test_egg_returns_positive_nutrition(self, monkeypatch):
        monkeypatch.setenv("USDA_API_KEY", "test-key")
        with patch("agents.nodes.nutrition_lookup.httpx.get", return_value=self._usda_mock()):
            from agents.nodes.nutrition_lookup import nutrition_lookup
            result = nutrition_lookup(self._state(["egg"], [100.0]))
        assert result.get("error") is None
        assert result["nutrition"]["calories"] > 0
        assert result["nutrition"]["protein"] > 0

    def test_scales_by_quantity(self, monkeypatch):
        monkeypatch.setenv("USDA_API_KEY", "test-key")
        with patch("agents.nodes.nutrition_lookup.httpx.get",
                   return_value=self._usda_mock(calories=100.0, protein=10.0, carbs=0.0, fat=0.0)):
            from agents.nodes.nutrition_lookup import nutrition_lookup
            result = nutrition_lookup(self._state(["test_food"], [200.0]))
        assert abs(result["nutrition"]["calories"] - 200.0) < 0.01
        assert abs(result["nutrition"]["protein"] - 20.0)  < 0.01

    def test_fallback_when_all_zeros(self, monkeypatch):
        monkeypatch.setenv("USDA_API_KEY", "test-key")
        zero_resp = MagicMock()
        zero_resp.raise_for_status = MagicMock()
        zero_resp.json.return_value = {"foods": [{
            "fdcId": 1,
            "dataType": "Branded",
            "foodNutrients": [
                {"nutrientId": 1008, "value": 0.0},
                {"nutrientId": 1003, "value": 0.0},
                {"nutrientId": 1005, "value": 0.0},
                {"nutrientId": 1004, "value": 0.0},
            ],
        }]}
        with patch("agents.nodes.nutrition_lookup.httpx.get", return_value=zero_resp):
            from agents.nodes.nutrition_lookup import nutrition_lookup
            result = nutrition_lookup(self._state(["mystery_food"], [100.0]))
        # Fallback values are used → calories must be > 0
        assert result["nutrition"]["calories"] > 0

    def test_no_api_key_sets_error(self, monkeypatch):
        monkeypatch.delenv("USDA_API_KEY", raising=False)
        from agents.nodes.nutrition_lookup import nutrition_lookup
        s = default_nutrition_state()
        s["detected_foods"] = ["egg"]
        result = nutrition_lookup(s)
        assert result.get("error") is not None

    def test_empty_foods_sets_error(self, monkeypatch):
        monkeypatch.setenv("USDA_API_KEY", "test-key")
        from agents.nodes.nutrition_lookup import nutrition_lookup
        s = default_nutrition_state()
        s["detected_foods"] = []
        result = nutrition_lookup(s)
        assert result.get("error") is not None


# ══════════════════════════════════════════════════════════════════════════════
# 4. goal_analyzer
# ══════════════════════════════════════════════════════════════════════════════

class TestGoalAnalyzer:
    """Tests for agents/nodes/goal_analyzer.py — Supabase patched."""

    def _build_supabase(self, goals_data=None, logs_data=None):
        """Build a fully chainable mock Supabase client."""
        client = MagicMock()

        def table_side(name):
            chain = MagicMock()
            chain.select.return_value = chain
            chain.eq.return_value = chain
            chain.insert.return_value = chain
            chain.update.return_value = chain

            if name == "daily_goals":
                chain.execute.return_value = MagicMock(data=goals_data or [])
            elif name == "daily_logs":
                chain.execute.return_value = MagicMock(data=logs_data or [])
            else:
                chain.execute.return_value = MagicMock(data=[])
            return chain

        client.table.side_effect = table_side
        return client

    def test_calculates_deficits_correctly(self, monkeypatch, sample_state):
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-key")

        goals = [{"calorie_goal": 2000.0, "protein_goal": 80.0, "carb_goal": 250.0, "fat_goal": 70.0}]
        logs  = [{"total_calories": 350.0, "total_protein": 18.0, "total_carbs": 58.0, "total_fat": 8.0}]
        mock_sb = self._build_supabase(goals_data=goals, logs_data=logs)

        with patch("agents.nodes.goal_analyzer._get_supabase", return_value=mock_sb):
            from agents.nodes.goal_analyzer import goal_analyzer
            s = dict(sample_state)
            s["nutrition"] = {"calories": 350.0, "protein": 18.0, "carbs": 58.0, "fat": 8.0}
            result = goal_analyzer(s)

        deficits = result.get("dashboard_data", {}).get("deficits", {})
        assert deficits.get("calories", 0) > 0
        assert deficits.get("protein", 0) > 0

    def test_empty_user_id_sets_error(self, sample_state):
        from agents.nodes.goal_analyzer import goal_analyzer
        s = dict(sample_state)
        s["user_id"] = ""
        result = goal_analyzer(s)
        assert result.get("error") is not None

    def test_defaults_when_no_goal_row(self, monkeypatch, sample_state):
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-key")

        mock_sb = self._build_supabase(goals_data=[], logs_data=[])

        with patch("agents.nodes.goal_analyzer._get_supabase", return_value=mock_sb):
            from agents.nodes.goal_analyzer import goal_analyzer
            s = dict(sample_state)
            result = goal_analyzer(s)

        assert result.get("error") is None
        assert result.get("daily_goal", {}).get("calorie_goal") == 2000.0


# ══════════════════════════════════════════════════════════════════════════════
# 5. recommender
# ══════════════════════════════════════════════════════════════════════════════

class TestRecommender:
    """Tests for agents/nodes/recommender.py — Groq LLM patched directly."""

    def _mock_llm(self, content="Eat dal and rice!"):
        mock_msg = MagicMock()
        mock_msg.content = content
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_msg
        return mock_llm

    def test_returns_non_empty_recommendation(self, sample_state):
        mock_llm = self._mock_llm("Hey! Try dal tadka with 3 rotis for your protein and carb goals.")
        with patch("agents.nodes.recommender.ChatGroq", return_value=mock_llm):
            from agents.nodes.recommender import recommender
            result = recommender(dict(sample_state))
        assert isinstance(result.get("recommendation"), str)
        assert len(result["recommendation"]) > 0

    def test_dashboard_data_populated(self, sample_state):
        mock_llm = self._mock_llm("Eat more dal and rice!")
        with patch("agents.nodes.recommender.ChatGroq", return_value=mock_llm):
            from agents.nodes.recommender import recommender
            result = recommender(dict(sample_state))
        dashboard = result.get("dashboard_data", {})
        assert "today_total" in dashboard
        assert "daily_goal" in dashboard
        assert "recommendation" in dashboard

    def test_llm_error_sets_state_error(self, sample_state):
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("Groq API quota exceeded")
        with patch("agents.nodes.recommender.ChatGroq", return_value=mock_llm):
            from agents.nodes.recommender import recommender
            result = recommender(dict(sample_state))
        assert result.get("error") is not None
        assert "Groq API quota exceeded" in result["error"]


# ══════════════════════════════════════════════════════════════════════════════
# 6. stt_node
# ══════════════════════════════════════════════════════════════════════════════

class TestSttNode:
    """Tests for agents/nodes/stt_node.py — HF pipeline patched."""

    def test_missing_audio_path_sets_error(self):
        from agents.nodes.stt_node import stt_node
        s = default_nutrition_state()
        s["input_type"] = "voice"
        s["image_path"] = None
        result = stt_node(s)
        assert result.get("error") is not None

    def test_nonexistent_file_sets_error(self):
        from agents.nodes.stt_node import stt_node
        s = default_nutrition_state()
        s["input_type"] = "voice"
        s["image_path"] = "/nonexistent/audio.wav"
        result = stt_node(s)
        assert result.get("error") is not None

    def test_dict_result_extracted_correctly(self, tmp_path):
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"\x00" * 100)

        mock_pipe = MagicMock(return_value={"text": "I ate 2 eggs and toast"})
        mock_hf = MagicMock(return_value=mock_pipe)

        with patch("agents.nodes.stt_node.hf_pipeline", mock_hf):
            from agents.nodes.stt_node import stt_node
            s = default_nutrition_state()
            s["input_type"] = "voice"
            s["image_path"] = str(audio_file)
            result = stt_node(s)

        assert result.get("raw_input") == "I ate 2 eggs and toast"
        assert result.get("input_type") == "text"

    def test_list_result_joined_correctly(self, tmp_path):
        audio_file = tmp_path / "test2.wav"
        audio_file.write_bytes(b"\x00" * 100)

        mock_pipe = MagicMock(return_value=[{"text": "I had"}, {"text": "dal rice"}])
        mock_hf = MagicMock(return_value=mock_pipe)

        with patch("agents.nodes.stt_node.hf_pipeline", mock_hf):
            from agents.nodes.stt_node import stt_node
            s = default_nutrition_state()
            s["input_type"] = "voice"
            s["image_path"] = str(audio_file)
            result = stt_node(s)

        assert "dal rice" in result.get("raw_input", "")


# ══════════════════════════════════════════════════════════════════════════════
# 7. image_detector
# ══════════════════════════════════════════════════════════════════════════════

class TestImageDetector:
    """Tests for agents/nodes/image_detector.py — Keras model patched."""

    def test_missing_image_path_sets_error(self):
        from agents.nodes.image_detector import image_detector
        s = default_nutrition_state()
        s["image_path"] = None
        result = image_detector(s)
        assert result.get("error") is not None

    def test_nonexistent_file_sets_error(self):
        from agents.nodes.image_detector import image_detector
        s = default_nutrition_state()
        s["image_path"] = "/nonexistent/image.jpg"
        result = image_detector(s)
        assert result.get("error") is not None

    def test_model_none_returns_unknown_fallback(self, tmp_path):
        """When _keras_model is None, image_detector returns 'unknown' gracefully."""
        import agents.nodes.image_detector as id_mod

        # Force model to None (simulates missing/corrupt model)
        id_mod._keras_model = None
        id_mod._model_load_attempted = True

        # Create a dummy image file so the path check passes
        img_file = tmp_path / "food.jpg"
        img_file.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

        from agents.nodes.image_detector import image_detector
        s = default_nutrition_state()
        s["image_path"] = str(img_file)
        result = image_detector(s)

        assert result.get("detected_foods") == ["unknown"]
        assert result.get("confidence_scores") == [0.0]
        assert result.get("detected_quantities") == [150.0]
