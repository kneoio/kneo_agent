import random

from tools.dj_state import MergingType

_merge_pool = []

def get_random_merging_type():
    global _merge_pool
    if not _merge_pool:
        _merge_pool = [
            MergingType.SONG_INTRO_SONG,
            MergingType.INTRO_SONG_INTRO_SONG,
            #MergingType.SONG_CROSSFADE_SONG
        ]
        random.shuffle(_merge_pool)
    return _merge_pool.pop()
