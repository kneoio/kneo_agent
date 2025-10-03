from typing import List, Dict, Any


def build_ad_intro_text(title: str, artist: str) -> str:
    return f"\nAdvertisement: Break — \"{title}\" by {artist}"


def build_song_intro_text(
    title: str,
    artist: str,
    ai_dj_name: str,
    brand: str,
    song_description: str = "",
    genres: List[str] = None,
    history: List[Dict[str, Any]] = None,
    context: List[Any] = None
) -> str:
    intro_text = f"DJ Persona: {ai_dj_name}\nStation Brand: {brand}"
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
    if context:
        if isinstance(context, list) and len(context) == 1 and isinstance(context[0], dict):
            ctx_lines = [f"{k}: {v}" for k, v in context[0].items() if v]
            ctx_text = ", ".join(ctx_lines)
        else:
            ctx_text = str(context)
        intro_text += f"\nAtmosphere hint: {ctx_text}"
    return intro_text
