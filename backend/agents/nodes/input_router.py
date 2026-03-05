"""
This node acts as the entry gate for every user request entering the LangGraph pipeline.
It inspects the incoming NutritionState to determine whether the input is plain text,
a voice audio file, or an uploaded food image.  It sets state['input_type'] accordingly
and (for voice) copies the audio file path into state['image_path'] so the stt_node can
find it.  No API calls are made here — this is pure routing logic.
"""

from agents.state import NutritionState


def input_router(state: NutritionState) -> NutritionState:
    """
    Detect the input modality and tag the state with the correct input_type.

    Resolution order (highest priority first):
      1. image  — state['image_path'] is not None
      2. voice  — state['raw_input'] starts with the prefix "AUDIO_FILE:"
      3. text   — everything else
    """
    image_path: str | None = state.get("image_path")
    raw_input: str = state.get("raw_input", "")

    if image_path is not None:
        # An image was uploaded — classify as image input.
        state["input_type"] = "image"

    elif raw_input.startswith("AUDIO_FILE:"):
        # The caller encoded an audio file path as "AUDIO_FILE:/path/to/audio.wav".
        # Extract the file path and store it where stt_node expects to find it.
        audio_path = raw_input[len("AUDIO_FILE:"):].strip()
        state["input_type"] = "voice"
        state["image_path"] = audio_path

    else:
        # Plain natural-language text from the user.
        state["input_type"] = "text"

    return state
