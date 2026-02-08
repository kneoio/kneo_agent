from pydantic import BaseModel
from cnst.translation_types import TranslationType


class TranslateRequest(BaseModel):
    toTranslate: str
    translationType: TranslationType
    language: str  # PT_PT | EN_US and so on
