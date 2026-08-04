from abc import ABC, abstractmethod
from datetime import date

from src.functionality.enums import MediaType, Status

class MediaItem(ABC):
    """Base class for media items."""

    def __init__(self, title: str, release_date: date,
                 rating: float, status: Status, genres: list[str],
                 description: str = "", authors: list[str] = None,
                 video_path: str = "", duration: int = 0):
        self._title = title
        self._release_date = release_date
        self._rating = rating
        self._status = status
        self._genres = genres.copy() if genres else []
        self._description = description
        self._authors = authors.copy() if authors else []
        self._video_path = video_path
        self._duration = duration
        self._db_id = None  # Database ID

    @property
    def rating(self):
        return self._rating

    @property
    def status(self):
        return self._status

    @property
    def title(self):
        return self._title

    @property
    def genres(self):
        return self._genres.copy()

    @property
    def release_date(self):
        return self._release_date

    @property
    def description(self):
        return self._description

    @property
    def authors(self):
        return self._authors.copy()

    @property
    def video_path(self):
        return self._video_path

    @property
    def duration(self):
        return self._duration

    @rating.setter
    def rating(self, value: float):
        if 0 <= value <= 10:
            self._rating = value
        else:
            raise ValueError(f"Incorrect rating: {value}")

    @status.setter
    def status(self, value: Status):
        self._status = value

    def get_duration(self) -> float:
        return self._duration

    def get_summary(self) -> tuple:
        """Get a summary tuple of item properties."""
        genres_str = ", ".join(self._genres)
        authors_str = ", ".join(self._authors)
        return (
            self._title,
            self._release_date,
            self._rating,
            self._duration,
            genres_str,
            authors_str,
            self._description,
            self._video_path
        )

    def get_media_type(self) -> MediaType:
        """Get the media type of this item."""
        return MediaType.VIDEO

    def __lt__(self, other):
        if isinstance(other, MediaItem):
            return self._rating < other._rating
        raise TypeError(f"Incorrect type: {type(other)}")