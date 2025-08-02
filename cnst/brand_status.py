from enum import Enum


class BrandStatus(Enum):
    WAITING_FOR_CURATOR = 'WAITING_FOR_CURATOR'
    ON_LINE = 'ON_LINE'
    WARMING_UP = 'WARMING_UP'
    IDLE = 'IDLE'
    QUEUE_SATURATED = 'QUEUE_SATURATED'
