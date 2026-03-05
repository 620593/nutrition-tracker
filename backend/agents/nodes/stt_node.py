"""
This node handles speech-to-text conversion for voice-based meal logging inputs.
It uses the HuggingFace transformers pipeline with the openai/whisper-small checkpoint
to transcribe an audio file whose path is stored in state['image_path'].  The resulting
transcript overwrites state['raw_input'] and state['input_type'] is set back to 'text'
so the downstream food_parser node can process it identically to regular text input.
"""

import os
import logging
from agents.state import NutritionState

logger = logging.getLogger(__name__)


def stt_node(state: NutritionState) -> NutritionState:
    """
    Transcribe the audio file referenced by state['image_path'] using Whisper
    (openai/whisper-small via HuggingFace transformers) and store the transcript
    in state['raw_input'].  On success, state['input_type'] is reset to 'text'.
    On any error, state['error'] is set and the state is returned early.
    """
    # ── Lazy import to keep startup fast when voice is not used ───────────────
    try:
        from transformers import pipeline as hf_pipeline
    except ImportError as exc:  # pragma: no cover
        state["error"] = f"transformers library not installed: {exc}"
        return state

    audio_path: str | None = state.get("image_path")

    # Guard: audio file path must be present
    if not audio_path:
        state["error"] = "stt_node: no audio file path found in state['image_path']."
        return state

    # Guard: audio file must exist on disk
    if not os.path.isfile(audio_path):
        state["error"] = (
            f"stt_node: audio file not found at path '{audio_path}'. "
            "Please check the file path and try again."
        )
        return state

    # ── Load the Whisper pipeline (uses HF_TOKEN for authenticated downloads) ──
    hf_token: str | None = os.environ.get("HF_TOKEN")

    try:
        whisper = hf_pipeline(
            task="automatic-speech-recognition",
            model="openai/whisper-small",
            token=hf_token,          # None is accepted when the model is public
        )
    except Exception as exc:
        state["error"] = f"stt_node: failed to load Whisper model — {exc}"
        return state

    # ── Run transcription ─────────────────────────────────────────────────────
    try:
        result = whisper(audio_path)
        transcript: str = result.get("text", "").strip()
    except Exception as exc:
        state["error"] = f"stt_node: transcription failed — {exc}"
        return state

    # ── Update state so food_parser can handle the transcript as normal text ──
    state["raw_input"] = transcript
    state["input_type"] = "text"   # downstream nodes treat it as regular text

    logger.info("stt_node: transcription complete (%d chars)", len(transcript))
    return state
