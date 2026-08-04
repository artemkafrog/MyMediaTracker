import json
import pandas as pd
import seaborn as sns
from datetime import datetime
from pathlib import Path
from matplotlib import pyplot as plt

class ExploratoryAnalyzer:
    """Generates exploratory data analysis plots and reports."""

    def __init__(self, df: pd.DataFrame, output_dir_path: str = "reports/"):
        self._df = df.copy()
        self._output_dir_path = Path(output_dir_path)
        self._output_dir_path.mkdir(parents=True, exist_ok=True)

        self._figures_path = self._output_dir_path / "figures"
        self._figures_path.mkdir(exist_ok=True)

        self._stats_cache = {}

    def _save_or_show(self, plt_obj, save: bool, show: bool) -> Path | None:
        """Helper to save and/or display a plot."""
        file_path = None
        if save:
            timestamp = datetime.now().timestamp()
            file_name = f"{plt_obj.__name__}_{timestamp}.png"
            file_path = self._figures_path / file_name
            plt.savefig(file_path, dpi=300, bbox_inches="tight")
        if show:
            plt.show()
        plt.close()
        return file_path

    def get_plot_rating_distribution(self, save: bool = True, show: bool = True) -> Path | None:
        """Plot histogram of ratings with mean and median lines."""
        plt.figure(figsize=(10, 6))
        ratings = self._df['rating'].dropna()

        if ratings.empty:
            plt.close()
            return None

        avg_value = ratings.mean()
        median_value = ratings.median()

        plt.hist(ratings, bins=10, color="blue", edgecolor="black")
        plt.axvline(avg_value, color="red", linestyle='-', linewidth=2,
                    label=f"avg value: {avg_value:.2f}")
        plt.axvline(median_value, color="orange", linestyle="--", linewidth=2,
                    label=f"median value: {median_value:.2f}")
        plt.xlabel("Rating")
        plt.ylabel("Amount")
        plt.title("Rating distribution")
        plt.legend()
        plt.grid(axis='y', alpha=0.3)

        return self._save_or_show(plt, save, show)

    def get_plot_status_pie(self, save: bool = True, show: bool = True) -> Path | None:
        """Plot pie chart of status distribution."""
        plt.figure(figsize=(10, 8))
        status_counts = self._df["status"].value_counts()

        if status_counts.empty:
            plt.close()
            return None

        colors = {
            "WATCHED": "#2ecc71",
            "WATCHING": "#3498db",
            "PLANNED": "#f39c12",
            "ON_HOLD": "#e76f3c"
        }
        status_labels = [s.upper() if hasattr(s, 'upper') else s for s in status_counts.index]
        pie_colors = [colors.get(status, "#95a5a6") for status in status_labels]

        plt.pie(
            status_counts.values,
            labels=status_counts.index,
            colors=pie_colors,
            autopct='%.1f%%',
            startangle=90,
            explode=[0.05] * len(status_counts),
        )
        plt.title("Status distribution", fontsize=14)
        plt.axis("equal")

        return self._save_or_show(plt, save, show)

    def get_plot_rating_by_status(self, save: bool = True, show: bool = True) -> Path | None:
        """Plot boxplot of ratings grouped by status."""
        plt.figure(figsize=(10, 8))

        data_for_boxplot = []
        statuses = []
        colors = ['#2ecc71', '#3498db', '#f39c12', "#e76f3c"]

        for _, status in enumerate(self._df['status'].unique()):
            ratings = self._df[self._df['status'] == status]['rating'].dropna()
            if not ratings.empty:
                data_for_boxplot.append(ratings)
                statuses.append(status)

        if not data_for_boxplot:
            plt.close()
            return None

        positions = range(1, len(statuses) + 1)
        box = plt.boxplot(data_for_boxplot, positions=positions, patch_artist=True)
        plt.xticks(positions, statuses)

        for patch, color in zip(box['boxes'], colors[:len(statuses)]):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)

        plt.xlabel("Status")
        plt.ylabel("Rating")
        plt.title("Rating Distribution by Status", fontsize=14)
        plt.grid(axis='y', alpha=0.3)

        return self._save_or_show(plt, save, show)

    def get_plot_releases_over_time(self, freq: str = 'Y', save: bool = True,
                                    show: bool = True) -> Path | None:
        """Plot releases per year with rolling mean."""
        plt.figure(figsize=(12, 6))

        df_copy = self._df.copy()
        df_copy['release_year'] = pd.to_datetime(df_copy['release_date']).dt.year
        releases_by_year = df_copy.groupby('release_year').size()

        if releases_by_year.empty:
            plt.close()
            return None

        plt.plot(releases_by_year.index, releases_by_year.values,
                 marker='o', linewidth=2, markersize=8, label='Releases')

        if len(releases_by_year) >= 3:
            rolling_mean = releases_by_year.rolling(3, min_periods=1).mean()
            plt.plot(rolling_mean.index, rolling_mean.values,
                     linestyle='--', color='red', linewidth=2,
                     label='Rolling Mean (3 years)')

        plt.xlabel("Year")
        plt.ylabel("Count")
        plt.title("Content Releases Over Time", fontsize=14)
        plt.legend()
        plt.grid(True, alpha=0.3)

        return self._save_or_show(plt, save, show)

    def get_plot_duration_distribution(self, save: bool = True,
                                       show: bool = True) -> Path | None:
        """Plot histogram of durations."""
        plt.figure(figsize=(10, 6))

        durations = self._df['duration'].dropna()

        if durations.empty:
            plt.close()
            return None

        median_value = durations.median()

        plt.hist(durations, bins=20, color='seagreen', edgecolor='black', alpha=0.7)
        plt.axvline(median_value, color='red', linestyle='-', linewidth=2,
                    label=f'Median: {median_value:.0f} min')
        plt.xlabel("Duration (min)")
        plt.ylabel("Count")
        plt.title("Duration Distribution", fontsize=14)
        plt.legend()
        plt.grid(axis='y', alpha=0.3)

        return self._save_or_show(plt, save, show)

    def get_plot_correlation_heatmap(self, save: bool = True,
                                     show: bool = True) -> Path | None:
        """Plot correlation heatmap."""
        plt.figure(figsize=(8, 6))

        df_copy = self._df.copy()
        numeric_cols = ['rating', 'duration']
        if 'release_date' in df_copy.columns:
            df_copy['year'] = pd.to_datetime(df_copy['release_date']).dt.year
            numeric_cols.append('year')

        corr_matrix = df_copy[numeric_cols].corr()

        if corr_matrix.empty:
            plt.close()
            return None

        sns.heatmap(
            corr_matrix,
            annot=True,
            fmt='.2f',
            cmap='coolwarm',
            center=0,
            square=True,
            linewidths=0.5,
            cbar_kws={'shrink': 0.8}
        )
        plt.title("Correlation Heatmap", fontsize=14)

        return self._save_or_show(plt, save, show)

    def get_plot_genre_popularity(self, save: bool = True,
                                  show: bool = True) -> Path | None:
        """Plot bar chart of top genres."""
        plt.figure(figsize=(12, 6))

        genres_exploded = self._df['genres'].explode()
        genre_counts = genres_exploded.value_counts().head(15)

        if genre_counts.empty:
            plt.close()
            return None

        plt.barh(genre_counts.index, genre_counts.values, color='skyblue')
        plt.xlabel("Count")
        plt.ylabel("Genre")
        plt.title("Top 15 Genres", fontsize=14)
        plt.grid(axis='x', alpha=0.3)

        return self._save_or_show(plt, save, show)

    def generate_full_report(self) -> dict[str, dict]:
        """Generate all plots and compile statistics."""
        print("\nGenerating full report...")

        # Generate all plots
        self.get_plot_rating_distribution(save=True, show=False)
        self.get_plot_status_pie(save=True, show=False)
        self.get_plot_genre_popularity(save=True, show=False)
        self.get_plot_rating_by_status(save=True, show=False)
        self.get_plot_releases_over_time(save=True, show=False)
        self.get_plot_duration_distribution(save=True, show=False)
        self.get_plot_correlation_heatmap(save=True, show=False)

        # Collect statistics
        stats = {}
        stats['total_items'] = len(self._df)
        stats['avg_rating'] = round(self._df['rating'].mean(), 2) if not self._df['rating'].isna().all() else 0
        stats['median_rating'] = round(self._df['rating'].median(), 2) if not self._df['rating'].isna().all() else 0
        stats['min_rating'] = round(self._df['rating'].min(), 2) if not self._df['rating'].isna().all() else 0
        stats['max_rating'] = round(self._df['rating'].max(), 2) if not self._df['rating'].isna().all() else 0

        stats['status_counts'] = self._df['status'].value_counts().to_dict()

        genres_exploded = self._df['genres'].explode()
        genre_counts = genres_exploded.value_counts()
        if not genre_counts.empty:
            stats['most_common_genre'] = genre_counts.index[0]
            stats['most_common_genre_count'] = int(genre_counts.iloc[0])
        else:
            stats['most_common_genre'] = 'No data'
            stats['most_common_genre_count'] = 0
        stats['genre_counts'] = genre_counts.to_dict()

        stats['total_duration'] = int(self._df['duration'].sum()) if not self._df['duration'].isna().all() else 0
        stats['avg_duration'] = round(self._df['duration'].mean(), 2) if not self._df['duration'].isna().all() else 0

        if 'release_date' in self._df.columns:
            df_copy = self._df.copy()
            df_copy['release_year'] = pd.to_datetime(df_copy['release_date']).dt.year
            stats['items_by_year'] = df_copy.groupby('release_year').size().to_dict()
        else:
            stats['items_by_year'] = {}

        # Save JSON report
        stats_file = self._output_dir_path / "stats.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False, default=str)

        # Save text report
        txt_file = self._output_dir_path / "statistics.txt"
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write("=" * 50 + "\n")
            f.write("DATA ANALYSIS REPORT\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Total items: {stats['total_items']}\n")
            f.write(f"Average rating: {stats['avg_rating']}\n")
            f.write(f"Median rating: {stats['median_rating']}\n")
            f.write(f"Min rating: {stats['min_rating']}\n")
            f.write(f"Max rating: {stats['max_rating']}\n\n")
            f.write("Status distribution:\n")
            for status, count in stats['status_counts'].items():
                f.write(f"  {status}: {count}\n")
            f.write(f"\nMost common genre: {stats['most_common_genre']} ({stats['most_common_genre_count']})\n\n")
            f.write("Top-10 genres:\n")
            for genre, count in list(stats['genre_counts'].items())[:10]:
                f.write(f"  {genre}: {count}\n")
            f.write(f"\nTotal duration: {stats['total_duration']} min\n")
            f.write(f"Average duration: {stats['avg_duration']} min\n")
            if stats['items_by_year']:
                f.write("\nYear distribution:\n")
                for year, count in sorted(stats['items_by_year'].items()):
                    f.write(f"  {year}: {count}\n")

        print(f"Report saved to: {txt_file}")
        print("Report generated successfully!")
        return stats