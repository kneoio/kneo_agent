import random
from tools.dj_state import MergingType

def get_random_merging_type(
    intro_song_intro_prob: float = 0.4,
    song_intro_prob: float = 0.4,
    crossfade_prob: float = 0.6
):
    choices = [
        MergingType.INTRO_SONG_INTRO_SONG,
        MergingType.SONG_INTRO_SONG,
        MergingType.SONG_CROSSFADE_SONG,
    ]
    weights = [intro_song_intro_prob, song_intro_prob, crossfade_prob]
    return random.choices(choices, weights=weights, k=1)[0]
