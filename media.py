from abc import ABC, abstractmethod
from datetime import date
from enums import MediaType, Status

class MediaItem(ABC):
    def __init__(self, title: str, release_date: date,
                 rating: float, status: Status, genres: list[str]):
        self._title = title
        self._release_date = release_date
        self._rating = rating
        self._status = status
        self._genres = genres

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
        return self._genres

    @property
    def release_date(self):
        return self._release_date
    
    @rating.setter
    def rating(self, value: float):
        if 0 <= value <= 10:
            self._rating = value
        else:
            raise ValueError(f"Incorrect rating: {value}")
    
    @status.setter
    def status(self, value: Status):
        self._status = value

    @abstractmethod
    def get_duration(self) -> float: 
        pass
    
    @abstractmethod
    def get_summary(self) -> tuple:
        pass

    @abstractmethod
    def get_media_type(self) -> MediaType:
        pass
    
    def __lt__(self, other):
        if isinstance(other, MediaItem):
            return self._rating < other._rating
        raise TypeError(f"Incorrect type: {type(other)}")
    
class Book(MediaItem):
    def __init__(self, title: str, release_date: date,
                 rating: float, status: Status, genres: list[str], pages: int):
        super().__init__(title, release_date, rating, status, genres)
        self.__pages = pages

    def get_duration(self) -> float: 
        return self.__pages
        
    def get_summary(self) -> tuple:
        genres_str = ", ".join(self._genres)
        return (
            self._title,
            self._release_date,
            self._rating,
            self.__pages,
            genres_str
        )

    def get_media_type(self) -> MediaType:
            return MediaType.BOOK

class Movie(MediaItem):
    def __init__(self, title: str, release_date: date,
                 rating: float, status: Status, genres: list[str],
                 minutes: int):
        super().__init__(title, release_date, rating, status, genres)
        self.__minutes = minutes

    def get_duration(self) -> float: 
        return self.__minutes
        
    def get_summary(self) -> tuple:
        genres_str = ", ".join(self._genres)
        return (
            self._title,
            self._release_date,
            self._rating,
            self.__minutes,
            genres_str
        )

    def get_media_type(self) -> MediaType:
        return MediaType.MOVIE

class TVSeries(MediaItem):
    def __init__(self, title: str, release_date: date,
                 rating: float, status: Status, 
                 genres: list[str], seasons: dict[int,list[int]] | None = None):
        super().__init__(title, release_date, rating, status, genres)
        self.__seasons = dict(seasons) if seasons else {}

    def get_duration(self) -> float: 
        summary_time = sum(episode for season_episodes in self.__seasons.values() for episode in season_episodes)
        return summary_time
    
    def get_summary(self) -> tuple:
        number_of_seasons = len(self.__seasons)
        number_of_episodes = self.get_total_episodes(type)
        summary_time = sum(episode for season_episodes in self.__seasons.values() for episode in season_episodes)
        genres_str = ", ".join(self._genres)
        return (
            self._title,
            self._release_date,
            self._rating,
            number_of_seasons,
            number_of_episodes,
            summary_time,
            genres_str
        )
            
    def get_total_episodes(self) -> int:
        number_of_episodes = sum(len(episodes) for episodes in self.__seasons.values())
        return number_of_episodes

    def get_media_type(self) -> MediaType:
            return MediaType.TV_SERIES

