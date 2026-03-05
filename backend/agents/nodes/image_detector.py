"""
This node classifies a food image using a locally stored Keras model
(models/food_classifier.keras).  The model is cached at module level so it is
loaded only once per process lifetime.  The image is loaded with PIL, resized to
224×224, normalised, and fed to model.predict().  The top-3 predicted Food-101 class
names are stored in state['detected_foods'], 150.0 g each as placeholder quantities,
and the raw softmax scores in state['confidence_scores'].
"""

import os
import logging
import numpy as np
from agents.state import NutritionState

logger = logging.getLogger(__name__)

# ── Module-level model cache (loaded only once) ───────────────────────────────
_keras_model = None

# ── Food-101 class labels (101 classes, alphabetical order) ───────────────────
FOOD101_CLASSES: list[str] = [
    "apple_pie", "baby_back_ribs", "baklava", "beef_carpaccio", "beef_tartare",
    "beet_salad", "beignets", "bibimbap", "bread_pudding", "breakfast_burrito",
    "bruschetta", "caesar_salad", "cannoli", "caprese_salad", "carrot_cake",
    "ceviche", "cheesecake", "cheese_plate", "chicken_curry", "chicken_quesadilla",
    "chicken_wings", "chocolate_cake", "chocolate_mousse", "churros", "clam_chowder",
    "club_sandwich", "crab_cakes", "creme_brulee", "croque_madame", "cup_cakes",
    "deviled_eggs", "donuts", "dumplings", "edamame", "eggs_benedict",
    "escargots", "falafel", "filet_mignon", "fish_and_chips", "foie_gras",
    "french_fries", "french_onion_soup", "french_toast", "fried_calamari",
    "fried_rice", "frozen_yogurt", "garlic_bread", "gnocchi", "greek_salad",
    "grilled_cheese_sandwich", "grilled_salmon", "guacamole", "gyoza", "hamburger",
    "hot_and_sour_soup", "hot_dog", "huevos_rancheros", "hummus", "ice_cream",
    "lasagna", "lobster_bisque", "lobster_roll_sandwich", "macaroni_and_cheese",
    "macarons", "miso_soup", "mussels", "nachos", "omelette", "onion_rings",
    "oysters", "pad_thai", "paella", "pancakes", "panna_cotta", "peking_duck",
    "pho", "pizza", "pork_chop", "poutine", "prime_rib", "pulled_pork_sandwich",
    "ramen", "ravioli", "red_velvet_cake", "risotto", "samosa", "sashimi",
    "scallops", "seaweed_salad", "shrimp_and_grits", "spaghetti_bolognese",
    "spaghetti_carbonara", "spring_rolls", "steak", "strawberry_shortcake",
    "sushi", "tacos", "takoyaki", "tiramisu", "tuna_tartare", "waffles",
]

# Guarantee exactly 101 entries (pad with placeholders if the list grows/shrinks)
assert len(FOOD101_CLASSES) == 101, (
    f"FOOD101_CLASSES must have 101 entries, got {len(FOOD101_CLASSES)}"
)


def _load_model():
    """Load the Keras model from disk (or return cached instance)."""
    global _keras_model
    if _keras_model is not None:
        return _keras_model

    # ── Lazy import of Keras / TensorFlow ────────────────────────────────────
    try:
        import tensorflow as tf  # noqa: F401 — needed to register Keras backend
        from tensorflow import keras
    except ImportError:
        try:
            import keras  # standalone keras ≥ 3.x
        except ImportError as exc:
            raise ImportError(
                "Neither tensorflow nor keras is installed. "
                "Install one of them to use image detection."
            ) from exc

    model_path = os.path.join(
        os.path.dirname(__file__),   # …/backend/agents/nodes/
        "..", "..", "models", "food_classifier.keras"
    )
    model_path = os.path.normpath(model_path)

    if not os.path.isfile(model_path):
        raise FileNotFoundError(
            f"Keras model not found at '{model_path}'. "
            "Please place food_classifier.keras in the models/ directory."
        )

    _keras_model = keras.models.load_model(model_path)
    logger.info("image_detector: loaded Keras model from %s", model_path)
    return _keras_model


def image_detector(state: NutritionState) -> NutritionState:
    """
    Load the image from state['image_path'], run the Food-101 Keras classifier,
    and store the top-3 predictions in state.
    """
    from PIL import Image  # required: Pillow

    image_path: str | None = state.get("image_path")

    if not image_path:
        state["error"] = "image_detector: state['image_path'] is None or missing."
        return state

    if not os.path.isfile(image_path):
        state["error"] = (
            f"image_detector: image file not found at path '{image_path}'."
        )
        return state

    # ── Load and preprocess the image ─────────────────────────────────────────
    try:
        img = Image.open(image_path).convert("RGB")
        img = img.resize((224, 224))
        img_array = np.array(img, dtype=np.float32) / 255.0   # normalise to [0, 1]
        img_array = np.expand_dims(img_array, axis=0)          # shape: (1, 224, 224, 3)
    except Exception as exc:
        state["error"] = f"image_detector: image preprocessing failed — {exc}"
        return state

    # ── Load model and run prediction ─────────────────────────────────────────
    try:
        model = _load_model()
    except FileNotFoundError as exc:
        state["error"] = str(exc)
        return state
    except Exception as exc:
        state["error"] = f"image_detector: model load error — {exc}"
        return state

    try:
        predictions = model.predict(img_array, verbose=0)  # shape: (1, 101)
        scores: np.ndarray = predictions[0]                # shape: (101,)
    except Exception as exc:
        state["error"] = f"image_detector: model.predict failed — {exc}"
        return state

    # ── Extract top-3 results ─────────────────────────────────────────────────
    top3_indices = np.argsort(scores)[::-1][:3]
    top3_labels = [FOOD101_CLASSES[i] for i in top3_indices]
    top3_scores = [float(scores[i]) for i in top3_indices]

    # ── Write to state ────────────────────────────────────────────────────────
    state["detected_foods"] = top3_labels
    state["detected_quantities"] = [150.0] * 3      # placeholder gram estimate
    state["confidence_scores"] = top3_scores

    logger.info(
        "image_detector: top-3 predictions — %s",
        list(zip(top3_labels, [f"{s:.3f}" for s in top3_scores])),
    )
    return state
