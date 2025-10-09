from cnst.play_list_item_type import PlaylistItemType
from models.sound_fragment import SoundFragment
from tools.dj_state import DJState
from tools.draft_builder import build_ad_intro_text


async def build_ad_intro(self, state: DJState) -> DJState:
    ad_list = await self.sound_fragments_mcp.get_brand_sound_fragment(
        brand=self.brand,
        fragment_type=PlaylistItemType.ADVERTISEMENT.value
    )
    if ad_list:
        ad = SoundFragment.from_dict(ad_list[0])
        ad.draft_intro = build_ad_intro_text(ad.title, ad.artist)
        state["song_fragments"] = [ad]
    else:
        self.logger.warning("No advertisement fragment available — skipping ad broadcast")
        state["broadcast_success"] = False
        state["__end__"] = True
    self._reset_event(state["events"])
    return state
