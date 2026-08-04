from enum import StrEnum, auto

class MediaType(StrEnum):
    """Media types supported by the system."""
    VIDEO = auto()

class Status(StrEnum):
    """Status types for media items."""
    WATCHED = auto()
    WATCHING = auto()
    PLANNED = auto()
    ON_HOLD = auto()

class Genre(StrEnum):
    """Genre definitions."""
    pass