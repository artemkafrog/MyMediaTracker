import pandas as pd
import os
from pathlib import Path
from src.catalog import MediaCatalog
from src.media import Movie, TVSeries, Book
from src.enums import MediaType

def export_to_csv(catalog: MediaCatalog, output_dir: str = "exports") -> dict[str, str]:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    exported_files = {}
    
    movies = catalog.get_by_type(MediaType.MOVIE)
    if movies:
        filepath = os.path.join(output_dir, "movies.csv")
        _export_movies(movies, filepath)
        exported_files["movies"] = filepath
    
    books = catalog.get_by_type(MediaType.BOOK)
    if books:
        filepath = os.path.join(output_dir, "books.csv")
        _export_books(books, filepath)
        exported_files["books"] = filepath
    
    tv_series = catalog.get_by_type(MediaType.TV_SERIES)
    if tv_series:
        filepath = os.path.join(output_dir, "tv_series.csv")
        _export_tv_series(tv_series, filepath)
        exported_files["tv_series"] = filepath
    
    return exported_files


def _export_movies(movies: list[Movie], filepath: str) -> None:
    data = []
    for movie in movies:
        data.append({
            'title': movie.title,
            'release_date': movie.release_date,
            'rating': movie.rating,
            'status': movie.status.value,
            'genres': ';'.join(movie.genres),
            'minutes': movie.get_duration(),
            'media_type': movie.get_media_type().value
        })
    
    df = pd.DataFrame(data)
    df.to_csv(filepath, index=False, encoding='utf-8')

def _export_books(books: list[Book], filepath: str) -> None:
    data = []
    for book in books:
        data.append({
            'title': book.title,
            'release_date': book.release_date,
            'rating': book.rating,
            'status': book.status.value,
            'genres': ';'.join(book.genres),
            'pages': book.get_duration(),
            'media_type': book.get_media_type().value
        })
    
    df = pd.DataFrame(data)
    df.to_csv(filepath, index=False, encoding='utf-8')

def _export_tv_series(series_list: list[TVSeries], filepath: str) -> None:
    data = []
    for series in series_list:
        seasons = series.seasons
        data.append({
            'title': series.title,
            'release_date': series.release_date,
            'rating': series.rating,
            'status': series.status.value,
            'genres': ';'.join(series.genres),
            'total_episodes': series.get_total_episodes(),
            'total_minutes': series.get_duration(),
            'seasons_count': len(seasons),
            'seasons_data': _serialize_seasons(seasons),
            'media_type': series.get_media_type().value
        })
    
    df = pd.DataFrame(data)
    df.to_csv(filepath, index=False, encoding='utf-8')

def _serialize_seasons(seasons: dict[int, list[int]]) -> str:
    parts = []
    for season_num, episodes in sorted(seasons.items()):
        episodes_str = ','.join(str(minutes) for minutes in episodes)
        parts.append(f"{season_num}:{episodes_str}")
    return ';'.join(parts)


def _deserialize_seasons(seasons_str: str) -> dict[int, list[int]]:
    if not seasons_str or pd.isna(seasons_str):
        return {}
    
    seasons = {}
    for season_part in seasons_str.split(';'):
        if ':' in season_part:
            season_num_str, episodes_str = season_part.split(':', 1)
            season_num = int(season_num_str)
            episodes = [int(x) for x in episodes_str.split(',') if x]
            seasons[season_num] = episodes
    return seasons