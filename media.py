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
    
    @rating.setter
    def rating(self, value: float):
        if 0 <= value <= 10:
            self._rating = value
        else:
            raise ValueError(f"Incorrect rating: {value}")
        
    @property
    def status(self):
        return self._status
    
    @status.setter
    def status(self, value: Status):
        self._status = value

    @abstractmethod
    def get_duration(self, type: MediaType) -> float: 
        pass
    
    @abstractmethod
    def get_summary(self, type: MediaType) -> str:
        pass
    
    def __lt__(self, other):
        if isinstance(other, MediaItem):
            return self._rating < other._rating
        raise TypeError(f"Incorrect type: {type(other)}")
    
class Book(MediaItem):
    def __init__(self, *args, pages: int):
        super().__init__(*args)
        self.__pages = pages

    def get_duration(self, type: MediaType) -> float: 
        if type == MediaType.BOOK:
            return self.__pages
        raise TypeError(f"Incorrect type for the book: {type}")
        
    def get_summary(self, type: MediaType) -> str:
        if type == MediaType.BOOK:
            genres_str = ", ".join(self._genres)
            return (
                f"\tTitle: {self._title}\n"
                f"\tRelease date: {self._release_date}\n"
                f"\tRating: {self._rating}\n"
                f"\tPages: {self.__pages}\n"
                f"\tGenres: {genres_str}"
            )
        raise TypeError(f"Incorrect type for the book: {type}")

class Movie(MediaItem):
    def __init__(self, *args, minutes: int):
        super().__init__(*args)
        self.__minutes = minutes

    def get_duration(self, type: MediaType) -> float: 
        if type == MediaType.MOVIE:
            return self.__minutes
        raise TypeError(f"Incorrect type for the movie: {type}")
        
    def get_summary(self, type: MediaType) -> str:
        if type == MediaType.MOVIE:
            genres_str = ", ".join(self._genres)
            return (
                f"\tTitle: {self._title}\n"
                f"\tRelease date: {self._release_date}\n"
                f"\tRating: {self._rating}\n"
                f"\tTime: {self.__minutes}\n"
                f"\tGenres: {genres_str}"
            )
        raise TypeError(f"Incorrect type for the movie: {type}")

class TVSeries(MediaItem):
    def __init__(self, *args, seasons: dict[int,list[int]] | None = None):
        super().__init__(*args)
        self.__seasons = dict(seasons) if seasons else {}

    def get_duration(self, type: MediaType) -> float: 
        if type == MediaType.TV_SERIES:
            summary_time = sum(episode for season_episodes in self.__seasons.values() for episode in season_episodes)
            return summary_time
        raise TypeError(f"Incorrect type for TV Series: {type}")
        
    def get_summary(self, type: MediaType) -> str:
        if type == MediaType.TV_SERIES:
            number_of_seasons = len(self.__seasons)
            number_of_episodes = self.get_total_episodes(type)
            summary_time = sum(episode for season_episodes in self.__seasons.values() for episode in season_episodes)
            genres_str = ", ".join(self._genres)
            return (
                f"\tTitle: {self._title}\n"
                f"\tRelease date: {self._release_date}\n"
                f"\tRating: {self._rating}\n"
                f"\tSeasons: {number_of_seasons}\n"
                f"\tEpisodes: {number_of_episodes}\n"
                f"\tTime: {summary_time}\n"
                f"\tGenres: {genres_str}"
            )
        raise TypeError(f"Incorrect type for TV Series: {type}")
    
    def get_total_episodes(self, type: MediaType) -> int:
        if type == MediaType.TV_SERIES:
            number_of_episodes = sum(len(episodes) for episodes in self.__seasons.values())
            return number_of_episodes
        raise TypeError(f"Incorrect type for TV Series: {type}")

    

