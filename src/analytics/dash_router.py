from pathlib import Path
from typing import Any
from datetime import datetime

class DashRouter:
    """Routes analytics data for dashboard consumption."""

    def __init__(self, data_loader, recommender, report_generator):
        self.data_loader = data_loader
        self.recommender = recommender
        self.report_generator = report_generator
        self._df = None

    def get_stats_json(self) -> dict[str, Any]:
        """Return statistics as JSON for API endpoints."""
        if self._df is None:
            self._df = self.data_loader.load_all_data()

        stats = self.report_generator._calculate_stats()
        return {
            'timestamp': datetime.now().isoformat(),
            'stats': stats,
            'metadata': {
                'total_items': stats.get('total_items', 0),
                'avg_rating': stats.get('avg_rating', 0),
                'status_counts': stats.get('status_counts', {})
            }
        }

    def get_recommendations_json(self, item_id: int, top_n: int = 5) -> dict[str, Any]:
        """Return recommendations for an item as JSON."""
        try:
            item_metadata = self.recommender.get_item_metadata(item_id)
            similar = self.recommender.recommend_similar(item_id, top_n)

            recommendations = []
            for rec_id, title, score in similar:
                rec_meta = self.recommender.get_item_metadata(rec_id)
                recommendations.append({
                    'id': rec_id,
                    'title': title,
                    'similarity_score': round(float(score), 4),
                    'rating': rec_meta.get('rating', 0),
                    'genres': rec_meta.get('genres', []),
                    'status': rec_meta.get('status', 'Unknown')
                })

            return {
                'source_item': item_metadata,
                'recommendations': recommendations,
                'count': len(recommendations)
            }
        except Exception as e:
            return {'error': str(e), 'recommendations': []}

    def get_plots_list(self) -> list[dict[str, str]]:
        """List available plot images from reports/figures."""
        figures_dir = Path("reports/figures")
        plots = []
        if figures_dir.exists():
            for img in sorted(figures_dir.glob("*.png"),
                              key=lambda x: x.stat().st_mtime, reverse=True):
                plots.append({
                    'name': img.stem,
                    'path': str(img),
                    'url': f"/static/plots/{img.name}",
                    'created': datetime.fromtimestamp(img.stat().st_mtime).isoformat()
                })
        return plots

    def get_dashboard_context(self) -> dict[str, Any]:
        """Build full context for dashboard rendering."""
        if self._df is None:
            self._df = self.data_loader.load_all_data()

        stats = self.report_generator._calculate_stats()

        context = {
            'total_items': stats.get('total_items', 0),
            'avg_rating': stats.get('avg_rating', 0),
            'status_counts': stats.get('status_counts', {}),
            'top_genres': list(stats.get('genre_counts', {}).items())[:5],
            'top_rated': self._df.nlargest(5, 'rating')[['id', 'title', 'rating']].to_dict('records'),
            'plots': self.get_plots_list()[:6]
        }

        return context