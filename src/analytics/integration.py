from src.functionality.decorators import timing
from src.analytics.data_loader import AnalyticsDataLoader
from src.analytics.eda import ExploratoryAnalyzer
from src.analytics.recommender import ContentRecommender
from src.analytics.report_generator import ReportGenerator
from src.analytics.dash_router import DashRouter

class AnalyticsIntegration:
    """Integrates all analytics modules into a single interface."""

    def __init__(self, db_path: str = "data/media_tracker.db"):
        self.loader = AnalyticsDataLoader(db_path)
        self.df = None
        self.analyzer = None
        self.recommender = None
        self.report_gen = None
        self.router = None

    @timing
    def initialize(self) -> bool:
        """Initialize all analytics components."""
        try:
            self.df = self.loader.load_all_data()

            if self.df is None or len(self.df) == 0:
                print("No data loaded from database")
                return False

            self.analyzer = ExploratoryAnalyzer(self.df)
            self.recommender = ContentRecommender(self.df)
            self.report_gen = ReportGenerator(self.df)
            self.router = DashRouter(self.loader, self.recommender, self.report_gen)
            return True
        except FileNotFoundError as e:
            print(f"Database not found: {e}")
            return False
        except Exception as e:
            print(f"Analytics initialization failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def show_stats_text(self) -> str:
        """Return statistics as formatted text."""
        if self.report_gen is None:
            if not self.initialize():
                return "Analytics module not initialized"
        stats = self.report_gen._calculate_stats()
        return self.report_gen.generate_text_report(stats)

    def generate_full_report(self) -> dict:
        """Generate full analytics report with plots."""
        if self.analyzer is None:
            if not self.initialize():
                return {}
        stats = self.analyzer.generate_full_report()
        if self.report_gen:
            self.report_gen.generate_markdown_report(stats)
            self.report_gen.export_excel_report(stats)
        return stats

    def get_recommendations(self, item_id: int, top_n: int = 5) -> list:
        """Get content-based recommendations for an item."""
        if self.recommender is None:
            if not self.initialize():
                return []
        try:
            return self.recommender.recommend_similar(item_id, top_n)
        except Exception as e:
            print(f"Error getting recommendations: {e}")
            return []

    def get_recommendations_from_planned(self, top_n: int = 5) -> list:
        """Get recommendations from PLANNED items."""
        if self.recommender is None:
            if not self.initialize():
                return []
        try:
            return self.recommender.recommend_by_status('PLANNED', top_n)
        except Exception as e:
            print(f"Error getting planned recommendations: {e}")
            return []