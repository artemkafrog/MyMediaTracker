import sqlite3
import json
import pandas as pd
from pathlib import Path
from datetime import date
from src.functionality.decorators import cache_result

class AnalyticsDataLoader:
    def __init__(self, db_path: str = "data/media_tracker.db"):
        self._db_path = db_path
        self._data = None

    @cache_result
    def load_all_data(self) -> pd.DataFrame:
        if not Path(self.db_path).exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")

        conn = sqlite3.connect(self._db_path)
        query = "SELECT * FROM media_items"
        df = pd.read_sql_query(query, conn)
        conn.close()

        df['genres'] = df['genres'].apply(
            lambda x: json.loads(x) if x and x != "null" else []
        )
        df['authors'] = df['authors'].apply(
            lambda x: json.loads(x) if x and x != "null" else []
        )

        today = date.today()
        df['days_since_release'] = df['release_date'].apply(
            lambda x: (today - x).days if x else 0
        )
        df['release_year'] = df['release_date'].apply(
           lambda d: d.year if d else 0
        )

        self._data = df
        return df

    def get_genre_exploded(self) -> pd.DataFrame:
        if self._data is None:
            raise ValueError("Data not loaded. Call load_all_data() first.")

        df_exploded = self._data.copy()
        df_exploded = df_exploded.explode('genres')
        df_exploded = df_exploded.rename(columns={'genres' : 'genre'})
        df_exploded = df_exploded[df_exploded['genre'] != '']
        df_exploded = df_exploded[df_exploded['genre'].notna()]
        
        return df_exploded

    def get_stats_dataframe(self) -> dict[str, pd.DataFrame | dict]:
        if self._data is None:
            raise ValueError("Data not loaded. Call load_all_data() first.")

        df = self._data
        result = {}

        summary = pd.DataFrame({
            'metric': [
                'total_items',
                'avg_rating',
                'max_rating',
                'min_rating',
                'total_duration',
                'unique_genres',
                'watched_count',
                'planned_count',
                'watching_count',
                'on_hold_count'
            ],
            'value': [
                len(df),
                df['rating'].mean(),
                df['rating'].max(),
                df['rating'].min(),
                df['duration'].sum(),
                len(set().union(*df['genres'])),
                len(df[df['status'] == 'WATCHED']),
                len(df[df['status'] == 'PLANNED']),
                len(df[df['status'] == 'WATCHING']),
                len(df[df['status'] == 'ON_HOLD'])
            ]
        })
        result['summary'] = summary

        by_status = df.groupby('status').agg({
            'id': 'count',
            'rating': ['mean', 'min', 'max']
        }).round(2)
        by_status.columns = ['count', 'avg_rating', 'min_rating', 'max_rating']
        by_status = by_status.reset_index()
        result['by_status'] = by_status
        
        df_exploded = self.get_genre_exploded()
        by_genre = df_exploded.groupby('genre').agg({
            'id': 'count',
            'rating': 'mean'
        }).round(2)
        by_genre.columns = ['count', 'avg_rating']
        by_genre = by_genre.reset_index()
        by_genre = by_genre.sort_values('count', ascending=False)
        result['by_genre'] = by_genre
        
        by_year = df.groupby('release_year').agg({
            'id': 'count',
            'rating': 'mean'
        }).round(2)
        by_year.columns = ['count', 'avg_rating']
        by_year = by_year.reset_index()
        by_year = by_year[by_year['release_year'] > 0]
        result['by_year'] = by_year
        
        top_rated = df.nlargest(10, 'rating')[['id', 'title', 'rating', 'status', 'genres']]
        result['top_rated'] = top_rated
        
        result['duration_stats'] = {
            'min': df['duration'].min(),
            'max': df['duration'].max(),
            'mean': df['duration'].mean(),
            'median': df['duration'].median(),
            'total': df['duration'].sum()
        }
        
        return result

    def get_correlation_matrix(self) -> pd.DataFrame:
        if self._data is None:
            raise ValueError("Data not loaded. Call load_all_data() first.")
    
        df = self._data.copy()
        df['num_genres'] = df['genres'].apply(len)
        
        numeric_cols = ['rating', 'duration', 'days_since_release', 'release_year', 'num_genres']
        return df[numeric_cols].corr()