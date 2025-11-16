class BrandMemoryManager:
    def __init__(self):
        self.memory = {}

    @staticmethod
    def clean(text: str) -> str:
        return (
            text.replace("<result>", "")
                .replace("</result>", "")
                .strip()
        )

    def add(self, brand: str, text: str):
        cleaned = self.clean(text)
        m = self.memory.setdefault(brand, [])
        m.append(cleaned)
        if len(m) > 20:
            m[:] = m[-20:]

    def get(self, brand: str):
        return self.memory.get(brand, [])

    def clear(self, brand: str):
        self.memory.pop(brand, None)

    def clear_all(self):
        self.memory.clear()
