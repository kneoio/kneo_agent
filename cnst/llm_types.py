from enum import Enum


class LlmType(Enum):
    CLAUDE = "CLAUDE"
    OPENAI = "OPENAI"
    GROQ = "GROQ"
    GROK = "GROK"
    KIMI = "KIMI"
    DEEPSEEK = "DEEPSEEK"
    OPENROUTER = "OPENROUTER"
    MOONSHOT = "MOONSHOT"
    GOOGLE = "GOOGLE"
