from enum import Enum


class MemoryType(Enum):
    UNKNOWN = "unknown"
    AUDIENCE_CONTEXT = "environment"
    LISTENER_CONTEXT = "listeners"
    CONVERSATION_HISTORY = "history"
    EVENT = "events"
    INSTANT_MESSAGE = "messages"

    @classmethod
    def from_value(cls, value: str):
        for memory_type in cls:
            if memory_type.value == value:
                return memory_type
        return cls.UNKNOWN

    def __str__(self):
        return self.value
