import random
from typing import List, Dict, Any


def build_ad_intro_text(title: str, artist: str) -> str:
    return f"\nAdvertisement: Break — \"{title}\" by {artist}"


def build_draft(
    title: str,
    artist: str,
    ai_dj_name: str,
    brand: str,
    song_description: str = "",
    genres: List[str] = None,
    history: List[Dict[str, Any]] = None,
    context: List[Any] = None,
    dj_probability: float = 0.3,
    brand_probability: float = 0.4,
    combined_probability: float = 0.5,
    atmosphere_probability: float = 0.7
) -> str:
    intro_text = ""
    added = False

    if random.random() < combined_probability:
        intro_text += f"DJ Persona: {ai_dj_name}\nStation Brand: {brand}"
        added = True
    else:
        if random.random() < dj_probability:
            intro_text += f"DJ Persona: {ai_dj_name}"
            added = True
        if random.random() < brand_probability:
            if added:
                intro_text += "\n"
            intro_text += f"Station Brand: {brand}"
            added = True

    intro_text += f"\nNow playing: \"{title}\" by {artist}"

    if song_description:
        intro_text += f"\nDescription: {song_description}"
    if genres:
        intro_text += f"\nGenres: {', '.join(genres)}"
    if history:
        prev = history[-1]
        intro = prev.get("introSpeech", "")
        intro_text += f"\nHistory: Played \"{prev.get('title')}\" by {prev.get('artist')}."
        if intro:
            intro_text += f" Last intro speech was: {intro}"
    if context and random.random() < atmosphere_probability:
        if isinstance(context, list) and len(context) == 1 and isinstance(context[0], dict):
            ctx_lines = [f"{k}: {v}" for k, v in context[0].items() if v]
            ctx_text = ", ".join(ctx_lines)
        else:
            ctx_text = str(context)
        intro_text += f"\nAtmosphere hint: {ctx_text}"
    return intro_text
