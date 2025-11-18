import re
from difflib import SequenceMatcher


class NoiseFilter:

    GENERIC_PATTERNS = [
        r"^hey[, ]",                              # "Hey Lumisonic fam..."
        r"^hello[, ]",
        r"^hi[, ]",
        r"^yo[, ]",
        r"^what's up",
        r"^now[ .]*\[pause\]?$",                  # "Now… [pause]"
        r"^now[\s.]*$",                           # plain "Now..."
        r"^\[.*\]$",                              # only audio tags
    ]

    def __init__(self):
        self.prev_text = None

    def is_noise(self, text: str) -> bool:
        if not text or not text.strip():
            return True

        t = text.strip().lower()

        # 1. Generic boilerplate pattern filter
        for pat in self.GENERIC_PATTERNS:
            if re.match(pat, t):
                return True

        # 2. Repeated "Hey Lumisonic fam, it's Veenuo!"
        if self._is_repetitive_intro(t):
            return True

        # 3. Near-duplicate to previous line
        if self.prev_text:
            sim = SequenceMatcher(None, t, self.prev_text).ratio()
            if sim > 0.90:
                return True

        # If passed all checks → valid memory
        self.prev_text = t
        return False

    @staticmethod
    def _is_repetitive_intro(t: str) -> bool:
        """
        Detects repetitive DJ greetings.
        """
        # same structure: "hey <brand> fam", "it's <dj>"
        if "hey " in t and " fam" in t:
            return True
        if "it's veenuo" in t:
            return True
        if "it's manchine" in t:
            return True
        if "this is veenuo" in t:
            return True
        if "this is akee" in t:
            return True
        return False
