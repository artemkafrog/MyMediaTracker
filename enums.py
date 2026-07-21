from enum import StrEnum, auto

class MediaType(StrEnum):
    MOVIE = auto()      # movie
    TV_SERIES = auto()  # tv_series
    BOOK = auto()       # book

class Status(StrEnum):
    WATCHED = auto()    # watched
    WATCHING = auto()   # watching
    PLANNED = auto()    # planned
    ON_HOLD = auto()    # on_hold
