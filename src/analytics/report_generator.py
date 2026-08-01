import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Any, Optional
from tabulate import tabulate

class ReportGenerator:
    def __init__(self, df: pd.DataFrame, output_dir: str = "reports/"):
        self.df = df.copy()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._figures_dir = self.output_dir / "figures"
        self._figures_dir.mkdir(exist_ok=True)

    def generate_text_report(self, stats: Optional[dict[str, Any]] = None) -> str:
        if stats is None:
            stats = self._calculate_stats()
        
        lines = []
        lines.append("=" * 60)
        lines.append("MEDIA TRACKER - ANALYTICS REPORT")
        lines.append("=" * 60)
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        lines.append("-" * 40)
        lines.append("OVERVIEW")
        lines.append("-" * 40)
        lines.append(f"Total items: {stats.get('total_items', 0)}")
        lines.append(f"Average rating: {stats.get('avg_rating', 0):.2f}")
        lines.append(f"Median rating: {stats.get('median_rating', 0):.2f}")
        lines.append(f"Rating range: {stats.get('min_rating', 0):.1f} - {stats.get('max_rating', 0):.1f}")
        lines.append("")
        
        lines.append("-" * 40)
        lines.append("STATUS DISTRIBUTION")
        lines.append("-" * 40)
        for status, count in stats.get('status_counts', {}).items():
            pct = (count / stats.get('total_items', 1)) * 100
            lines.append(f"  {status}: {count} ({pct:.1f}%)")
        lines.append("")
        
        lines.append("-" * 40)
        lines.append("TOP GENRES")
        lines.append("-" * 40)
        genre_counts = stats.get('genre_counts', {})
        for i, (genre, count) in enumerate(list(genre_counts.items())[:10], 1):
            lines.append(f"  {i}. {genre}: {count}")
        lines.append("")
        
        lines.append("-" * 40)
        lines.append("DURATION STATS")
        lines.append("-" * 40)
        lines.append(f"Total duration: {stats.get('total_duration', 0):,} min")
        lines.append(f"Average duration: {stats.get('avg_duration', 0):.1f} min")
        lines.append("")
        
        if stats.get('items_by_year'):
            lines.append("-" * 40)
            lines.append("RELEASES BY YEAR")
            lines.append("-" * 40)
            for year, count in sorted(stats.get('items_by_year', {}).items()):
                lines.append(f"  {year}: {count}")
        
        return "\n".join(lines)

    def generate_markdown_report(self, stats: Optional[dict[str, Any]] = None) -> Path:
        if stats is None:
            stats = self._calculate_stats()
        
        lines = []
        lines.append("# Media Analytics Report")
        lines.append("")
        lines.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        lines.append("")
        
        lines.append("## Overview")
        lines.append("")
        lines.append(f"- **Total items**: {stats.get('total_items', 0)}")
        lines.append(f"- **Average rating**: {stats.get('avg_rating', 0):.2f}")
        lines.append(f"- **Median rating**: {stats.get('median_rating', 0):.2f}")
        lines.append(f"- **Rating range**: {stats.get('min_rating', 0):.1f} - {stats.get('max_rating', 0):.1f}")
        lines.append("")
        
        lines.append("## Status Distribution")
        lines.append("")
        status_df = pd.DataFrame([
            {'status': s, 'count': c} 
            for s, c in stats.get('status_counts', {}).items()
        ])
        if not status_df.empty:
            lines.append(tabulate(status_df, headers='keys', tablefmt='pipe', showindex=False))
        lines.append("")
        
        lines.append("## Top Genres")
        lines.append("")
        genre_data = [
            {'genre': g, 'count': c} 
            for g, c in list(stats.get('genre_counts', {}).items())[:10]
        ]
        if genre_data:
            lines.append(tabulate(genre_data, headers='keys', tablefmt='pipe', showindex=False))
        lines.append("")
        
        lines.append("## Duration Stats")
        lines.append("")
        lines.append(f"- **Total duration**: {stats.get('total_duration', 0):,} min")
        lines.append(f"- **Average duration**: {stats.get('avg_duration', 0):.1f} min")
        lines.append("")
        
        lines.append("## Figures")
        lines.append("")
        figures_dir = self._figures_dir
        if figures_dir.exists():
            for img in sorted(figures_dir.glob("*.png"))[-10:]:
                rel_path = img.relative_to(self.output_dir.parent)
                lines.append(f"![{img.stem}]({rel_path})")
        lines.append("")
        
        if stats.get('items_by_year'):
            lines.append("## Releases by Year")
            lines.append("")
            year_data = [
                {'year': y, 'count': c} 
                for y, c in sorted(stats.get('items_by_year', {}).items())
            ]
            if year_data:
                lines.append(tabulate(year_data, headers='keys', tablefmt='pipe', showindex=False))
        
        md_path = self.output_dir / "report.md"
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))
        
        return md_path

    def export_excel_report(self, stats: Optional[dict[str, Any]] = None) -> Path:
        if stats is None:
            stats = self._calculate_stats()
        
        excel_path = self.output_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            self.df.to_excel(writer, sheet_name='All Items', index=False)
            
            status_df = pd.DataFrame([
                {'status': s, 'count': c} 
                for s, c in stats.get('status_counts', {}).items()
            ])
            if not status_df.empty:
                status_df.to_excel(writer, sheet_name='Status Distribution', index=False)
            
            genre_data = [
                {'genre': g, 'count': c} 
                for g, c in stats.get('genre_counts', {}).items()
            ]
            if genre_data:
                pd.DataFrame(genre_data).to_excel(writer, sheet_name='Genre Popularity', index=False)
            
            if stats.get('items_by_year'):
                year_data = [
                    {'year': y, 'count': c} 
                    for y, c in sorted(stats.get('items_by_year', {}).items())
                ]
                pd.DataFrame(year_data).to_excel(writer, sheet_name='Releases by Year', index=False)
            
            summary_data = {
                'Metric': [
                    'Total Items', 'Average Rating', 'Median Rating', 
                    'Min Rating', 'Max Rating', 'Total Duration (min)',
                    'Average Duration (min)', 'Most Common Genre'
                ],
                'Value': [
                    stats.get('total_items', 0),
                    stats.get('avg_rating', 0),
                    stats.get('median_rating', 0),
                    stats.get('min_rating', 0),
                    stats.get('max_rating', 0),
                    stats.get('total_duration', 0),
                    stats.get('avg_duration', 0),
                    stats.get('most_common_genre', 'No data')
                ]
            }
            pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
        
        return excel_path

    def _calculate_stats(self) -> dict[str, Any]:
        stats = {}
        stats['total_items'] = len(self.df)
        stats['avg_rating'] = round(self.df['rating'].mean(), 2) if not self.df['rating'].isna().all() else 0
        stats['median_rating'] = round(self.df['rating'].median(), 2) if not self.df['rating'].isna().all() else 0
        stats['min_rating'] = round(self.df['rating'].min(), 2) if not self.df['rating'].isna().all() else 0
        stats['max_rating'] = round(self.df['rating'].max(), 2) if not self.df['rating'].isna().all() else 0
        
        stats['status_counts'] = self.df['status'].value_counts().to_dict()
        
        if 'genres' in self.df.columns:
            genres_exploded = self.df['genres'].explode()
            genre_counts = genres_exploded.value_counts()
            stats['genre_counts'] = genre_counts.to_dict()
            if not genre_counts.empty:
                stats['most_common_genre'] = genre_counts.index[0]
                stats['most_common_genre_count'] = int(genre_counts.iloc[0])
            else:
                stats['most_common_genre'] = 'No data'
                stats['most_common_genre_count'] = 0
        
        stats['total_duration'] = int(self.df['duration'].sum()) if not self.df['duration'].isna().all() else 0
        stats['avg_duration'] = round(self.df['duration'].mean(), 2) if not self.df['duration'].isna().all() else 0
        
        if 'release_date' in self.df.columns:
            df_copy = self.df.copy()
            df_copy['release_year'] = pd.to_datetime(df_copy['release_date']).dt.year
            stats['items_by_year'] = df_copy.groupby('release_year').size().to_dict()
        else:
            stats['items_by_year'] = {}
        
        return stats