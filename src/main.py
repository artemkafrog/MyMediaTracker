import sys
import os
from pathlib import Path
from datetime import date
from src.functionality.catalog import MediaCatalog
from src.functionality.database import DatabaseManager
from src.functionality.media import MediaItem
from src.functionality.enums import Status, MediaType
from src.functionality.exceptions import NotFoundError, DuplicateError, ValidationError
from src.functionality.interactions import describe_item, change_status, get_upcoming_releases
from src.functionality.reminder import Reminder
from src.functionality.file_io import export_to_csv

from src.analytics.data_loader import AnalyticsDataLoader
from src.analytics.eda import ExploratoryAnalyzer
from src.analytics.recommender import ContentRecommender, StatusPredictor
from src.analytics.report_generator import ReportGenerator
from src.analytics.integration import AnalyticsIntegration


class MediaTrackerApp:
    def __init__(self):
        self.catalog = MediaCatalog()
        self.db = DatabaseManager()
        self.reminder = Reminder(self.catalog)
        
        self._load_from_db()
        self._init_analytics()
    
    def _load_from_db(self) -> None:
        items = self.db.get_all_items()
        for item in items:
            self.catalog.add_item(item)
        print(f"Loaded {len(items)} items from database")
    
    def _init_analytics(self) -> None:
        try:
            self.analytics = AnalyticsIntegration(self.db._db_path)
            if self.analytics.initialize():
                print("Analytics module initialized successfully")
            else:
                print("Analytics module initialization failed")
                self.analytics = None
        except Exception as e:
            print(f"Analytics not available: {e}")
            self.analytics = None
    
    def run(self) -> None:
        while True:
            self._show_menu()
            choice = input("\nSelect action: ").strip()
            
            if choice == "1":
                self._add_item()
            elif choice == "2":
                self._show_collection()
            elif choice == "3":
                self._search_items()
            elif choice == "4":
                self._change_status()
            elif choice == "5":
                self._show_stats()
            elif choice == "6":
                self._show_reminders()
            elif choice == "7":
                self._export_csv()
            elif choice == "8":
                self._create_backup()
            elif choice == "9":
                self._analytics_menu()
            elif choice == "0":
                print("Goodbye!")
                sys.exit(0)
            else:
                print("Invalid choice. Please try again.")
    
    def _show_menu(self) -> None:
        print("\n" + "=" * 50)
        print("           MediaTracker")
        print("=" * 50)
        print("1. Add new video")
        print("2. Show all collection")
        print("3. Search by title/genre/year/author")
        print("4. Change item status")
        print("5. Show statistics")
        print("6. Show reminders")
        print("7. Export to CSV")
        print("8. Create backup")
        print("9. Analytics & Recommendations")
        print("0. Exit")
        print("=" * 50)
        print(f"In collection: {len(self.catalog)} items")
    
    def _add_item(self) -> None:
        print("\n--- Add new video ---")
        
        title = input("Title: ").strip()
        if not title:
            print("Title cannot be empty")
            return
        
        year = input("Release year (YYYY): ").strip()
        try:
            release_date = date(int(year), 1, 1) if year else date.today()
        except ValueError:
            print("Invalid year format")
            return
        
        rating = input("Rating (0-10): ").strip()
        try:
            rating = float(rating) if rating else 0.0
        except ValueError:
            rating = 0.0
        
        print("\nSelect status:")
        print("1. Watched")
        print("2. Watching")
        print("3. Planned")
        print("4. On Hold")
        status_choice = input("Your choice: ").strip()
        status_map = {
            "1": Status.WATCHED,
            "2": Status.WATCHING,
            "3": Status.PLANNED,
            "4": Status.ON_HOLD
        }
        status = status_map.get(status_choice, Status.PLANNED)
        
        genres_input = input("Genres (comma separated): ").strip()
        genres = [g.strip() for g in genres_input.split(",") if g.strip()]
        
        authors_input = input("Authors (comma separated): ").strip()
        authors = [a.strip() for a in authors_input.split(",") if a.strip()]
        
        description = input("Description: ").strip()
        
        video_path = input("Video file path (or leave empty): ").strip()
        
        duration = input("Duration (minutes): ").strip()
        try:
            duration = int(duration) if duration else 0
        except ValueError:
            duration = 0
        
        try:
            item = MediaItem(
                title=title,
                release_date=release_date,
                rating=rating,
                status=status,
                genres=genres,
                description=description,
                authors=authors,
                video_path=video_path,
                duration=duration
            )
            
            item_id = self.catalog.add_item(item)
            self.db.add_item(item)
            
            print(f"\nItem added successfully! ID: {item_id}")
            print("\n" + describe_item(item))
            
        except DuplicateError as e:
            print(f"{e}")
        except ValidationError as e:
            print(f"Validation error: {e}")
        except Exception as e:
            print(f"Error: {e}")
    
    def _show_collection(self) -> None:
        print("\n--- All collection ---")
        
        print("\nFilter by status?")
        print("1. All")
        print("2. Watched")
        print("3. Watching")
        print("4. Planned")
        print("5. On Hold")
        filter_choice = input("Your choice: ").strip()
        
        status_map = {
            "2": Status.WATCHED,
            "3": Status.WATCHING,
            "4": Status.PLANNED,
            "5": Status.ON_HOLD
        }
        
        if filter_choice in status_map:
            items = self.catalog.get_by_status(status_map[filter_choice])
        else:
            items = list(self.catalog)
        
        if not items:
            print("No items in collection")
            return
        
        print(f"\nFound: {len(items)} items\n")
        
        for i, item in enumerate(items, 1):
            print(f"{i}. {describe_item(item)}\n")
            print("-" * 40)
    
    def _search_items(self) -> None:
        print("\n--- Search ---")
        print("Enter search query (can include genre, year, author):")
        print("Example: 'comedy 2020' or 'author: Smith' or 'Lord of the Rings'")
        query = input("Query: ").strip()
        
        if not query:
            print("Query cannot be empty")
            return
        
        try:
            try:
                item = self.catalog.search_item(query)
                print("\nFound:")
                print(describe_item(item))
            except NotFoundError:
                items = self.catalog.search_all(query)
                if items:
                    print(f"\nFound {len(items)} items:")
                    for i, item in enumerate(items, 1):
                        print(f"\n{i}. {describe_item(item)}")
                else:
                    print(f"No items found for: {query}")
                    
        except Exception as e:
            print(f"Search error: {e}")
    
    def _change_status(self) -> None:
        print("\n--- Change status ---")
        
        items = list(self.catalog)
        if not items:
            print("No items in collection")
            return
        
        print("\nAvailable items:")
        for item in items:
            db_id = getattr(item, '_db_id', id(item))
            print(f"  ID: {db_id} - {item.title} ({item.status.value})")
        
        try:
            item_id = int(input("\nEnter item ID: ").strip())
            item = self.catalog.get_item(item_id)
            
            print(f"\nCurrent status: {item.status.value}")
            print("\nSelect new status:")
            print("1. Watched")
            print("2. Watching")
            print("3. Planned")
            print("4. On Hold")
            
            status_choice = input("Your choice: ").strip()
            status_map = {
                "1": Status.WATCHED,
                "2": Status.WATCHING,
                "3": Status.PLANNED,
                "4": Status.ON_HOLD
            }
            
            new_status = status_map.get(status_choice)
            if not new_status:
                print("Invalid choice")
                return
            
            change_status(self.catalog, item_id, new_status)
            self.db.update_item(item_id, item)
            
            print(f"\nStatus changed to: {new_status.value}")
            print(describe_item(item))
            
        except NotFoundError:
            print("Item not found")
        except ValueError:
            print("Invalid ID")
        except Exception as e:
            print(f"Error: {e}")
    
    def _show_stats(self) -> None:
        print("\n--- Statistics ---")
        
        try:
            stats = self.db.get_stats()
            
            print("\nGeneral statistics:")
            print(f"  Total items: {stats['total']}")
            print(f"  Average rating: {stats['avg_rating']}")
            print(f"  Total duration: {stats['total_duration']} min")
            
            print("\nBy status:")
            for status, count in stats['by_status'].items():
                print(f"  {status.value}: {count}")
            
            print("\nBy type:")
            for media_type, count in stats['by_type'].items():
                print(f"  {media_type.value}: {count}")
                
        except Exception as e:
            print(f"Error getting statistics: {e}")
    
    def _show_reminders(self) -> None:
        print("\n--- Reminders ---")
        
        print("\n1. Upcoming releases (30 days)")
        print("2. All scheduled reminders")
        choice = input("Your choice: ").strip()
        
        try:
            if choice == "1":
                releases = get_upcoming_releases(self.reminder, 30)
                if releases:
                    print("\nUpcoming releases:")
                    print(releases)
                else:
                    print("No upcoming releases")
            else:
                reminders = self.reminder.get_all_reminders()
                if reminders:
                    print("\nAll reminders:")
                    for title, days in reminders:
                        status = "PAST" if days < 0 else f"{days} days left"
                        print(f"  {title}: {status}")
                else:
                    print("No scheduled reminders")
                    
        except Exception as e:
            print(f"Error: {e}")
    
    def _export_csv(self) -> None:
        print("\n--- Export to CSV ---")
        
        try:
            files = export_to_csv(self.catalog)
            print("\nExport completed:")
            for media_type, filepath in files.items():
                print(f"  {media_type}: {filepath}")
                
        except Exception as e:
            print(f"Export error: {e}")
    
    def _create_backup(self) -> None:
        print("\n--- Create backup ---")
        
        try:
            backup_dir = "backups"
            os.makedirs(backup_dir, exist_ok=True)
            
            timestamp = date.today().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(backup_dir, f"media_tracker_backup_{timestamp}.db")
            
            import shutil
            shutil.copy2(self.db._db_path, backup_path)
            
            print(f"Backup created: {backup_path}")
            
            csv_dir = os.path.join(backup_dir, f"csv_backup_{timestamp}")
            export_to_csv(self.catalog, csv_dir)
            print(f"CSV backup created: {csv_dir}")
            
        except Exception as e:
            print(f"Backup error: {e}")
    
    def _clear_reports(self) -> None:
        print("\n--- Clear Reports ---")
        
        reports_path = Path("reports")
        
        if not reports_path.exists():
            print("Reports folder does not exist")
            return
        
        files_count = 0
        for file in reports_path.rglob("*"):
            if file.is_file():
                files_count += 1
        
        if files_count == 0:
            print("Reports folder is already empty")
            return
        
        print(f"Found {files_count} files in reports folder")
        confirm = input("Are you sure you want to delete all reports? (y/N): ").strip().lower()
        
        if confirm != 'y':
            print("Operation cancelled")
            return
        
        try:
            for file in reports_path.rglob("*"):
                if file.is_file():
                    file.unlink()
                    print(f"  Deleted: {file}")
            
            for folder in sorted(reports_path.rglob("*"), reverse=True):
                if folder.is_dir() and not any(folder.iterdir()):
                    folder.rmdir()
                    print(f"  Removed empty folder: {folder}")
            
            reports_path.mkdir(exist_ok=True)
            figures_path = reports_path / "figures"
            figures_path.mkdir(exist_ok=True)
            
            print(f"\nReports folder cleared successfully!")
            print(f"All {files_count} files have been deleted")
            
        except Exception as e:
            print(f"Error clearing reports: {e}")
    
    def _analytics_menu(self) -> None:
        if self.analytics is None:
            print("\nAnalytics module is not available. Please check your data.")
            input("\nPress Enter to continue...")
            return
        
        while True:
            print("\n" + "=" * 50)
            print("        ANALYTICS & RECOMMENDATIONS")
            print("=" * 50)
            print("1. Show detailed statistics")
            print("2. Generate all plots (saves to reports/figures/)")
            print("3. Get recommendations for an item")
            print("4. Get recommendations from PLANNED items")
            print("5. Train status predictor (ML)")
            print("6. Generate full report (Markdown + Excel)")
            print("7. Show correlation analysis")
            print("8. Clear reports folder")
            print("9. Back to main menu")
            print("=" * 50)
            
            choice = input("Select action: ").strip()
            
            if choice == "1":
                self._analytics_stats()
            elif choice == "2":
                self._analytics_plots()
            elif choice == "3":
                self._analytics_recommendations()
            elif choice == "4":
                self._analytics_recommend_planned()
            elif choice == "5":
                self._analytics_train_predictor()
            elif choice == "6":
                self._analytics_report()
            elif choice == "7":
                self._analytics_correlation()
            elif choice == "8":
                self._clear_reports()
            elif choice == "9":
                break
            else:
                print("Invalid choice")
            
            input("\nPress Enter to continue...")
    
    def _analytics_stats(self) -> None:
        try:
            print("\n" + "=" * 50)
            print("DETAILED STATISTICS")
            print("=" * 50)
            
            df = self.analytics.loader.load_all_data()
            stats_df = self.analytics.loader.get_stats_dataframe()
            
            print("\nSummary:")
            for _, row in stats_df['summary'].iterrows():
                print(f"  {row['metric']}: {row['value']}")
            
            print("\nBy Status:")
            print(stats_df['by_status'].to_string(index=False))
            
            print("\nTop Genres:")
            print(stats_df['by_genre'].head(10).to_string(index=False))
            
            print("\nTop Rated:")
            print(stats_df['top_rated'][['title', 'rating', 'status']].to_string(index=False))
            
        except Exception as e:
            print(f"Error showing statistics: {e}")
    
    def _analytics_plots(self) -> None:
        if self.analytics.analyzer is None:
            print("Analyzer not initialized")
            return
        
        try:
            print("\nGenerating plots...")
            self.analytics.analyzer.generate_full_report()
            print("\nPlots saved to reports/figures/")
            
            import glob
            plots = glob.glob("reports/figures/*.png")
            if plots:
                print(f"\nGenerated {len(plots)} plots:")
                for p in plots[-5:]:
                    print(f"  - {os.path.basename(p)}")
        except Exception as e:
            print(f"Error generating plots: {e}")
    
    def _analytics_recommendations(self) -> None:
        try:
            items = list(self.catalog)
            if not items:
                print("No items in collection")
                return
            
            print("\nAvailable items (first 20):")
            for item in items[:20]:
                db_id = getattr(item, '_db_id', None)
                if db_id:
                    print(f"  ID: {db_id} - {item.title} ({item.status.value})")
                else:
                    print(f"  ID: {id(item)} - {item.title} ({item.status.value}) [no DB ID]")
            
            if len(items) > 20:
                print(f"  ... and {len(items) - 20} more")
            
            item_id = input("\nEnter item ID: ").strip()
            if not item_id:
                return
            
            item_id = int(item_id)
            
            found_item = None
            for item in items:
                if getattr(item, '_db_id', None) == item_id:
                    found_item = item
                    break
            
            if not found_item:
                try:
                    found_item = self.catalog.get_item(item_id)
                except NotFoundError:
                    print(f"Item with ID {item_id} not found")
                    return
            
            db_id = getattr(found_item, '_db_id', None)
            if not db_id:
                print("Item doesn't have a database ID")
                return
            
            recs = self.analytics.get_recommendations(db_id, top_n=5)
            
            if not recs:
                print("\nNo recommendations found")
                return
            
            print(f"\nRecommendations for '{found_item.title}' (ID: {db_id}):")
            for i, (rec_id, title, score) in enumerate(recs, 1):
                print(f"  {i}. {title} (ID: {rec_id}) - similarity: {score:.2%}")
            
        except ValueError:
            print("Invalid ID format")
        except NotFoundError as e:
            print(f"Error: {e}")
        except Exception as e:
            print(f"Error getting recommendations: {e}")
    
    def _analytics_recommend_planned(self) -> None:
        try:
            recs = self.analytics.get_recommendations_from_planned(top_n=5)
            
            if not recs:
                print("\nNo recommendations from PLANNED items")
                return
            
            print("\nTop recommendations from PLANNED:")
            for i, (rec_id, title, score) in enumerate(recs, 1):
                print(f"  {i}. {title} (ID: {rec_id}) - match: {score:.2%}")
            
        except Exception as e:
            print(f"Error getting recommendations: {e}")
    
    def _analytics_train_predictor(self) -> None:
        try:
            df = self.analytics.loader.load_all_data()
            predictor = StatusPredictor(df)
            
            print("\nTraining status predictor...")
            metrics = predictor.train_model()
            
            print("\nModel Performance:")
            print(f"  Accuracy:  {metrics['accuracy']:.2%}")
            print(f"  Precision: {metrics['precision']:.2%}")
            print(f"  Recall:    {metrics['recall']:.2%}")
            print(f"  F1 Score:  {metrics['f1_score']:.2%}")
            
            importance = predictor.get_feature_importance()
            print("\nFeature Importance:")
            for feature, imp in sorted(importance.items(), key=lambda x: x[1], reverse=True):
                print(f"  {feature}: {imp:.2%}")
            
        except Exception as e:
            print(f"Error training predictor: {e}")
    
    def _analytics_report(self) -> None:
        try:
            print("\nGenerating full report...")
            stats = self.analytics.generate_full_report()
            
            print("\nReport generated successfully:")
            print(f"  - Statistics: reports/statistics.txt")
            print(f"  - Markdown: reports/report.md")
            print(f"  - Excel: reports/report_*.xlsx")
            print(f"  - Figures: reports/figures/")
            
        except Exception as e:
            print(f"Error generating report: {e}")
    
    def _analytics_correlation(self) -> None:
        try:
            df = self.analytics.loader.load_all_data()
            corr = df[['rating', 'duration', 'release_year']].corr()
            
            print("\nCorrelation Matrix:")
            print(corr.round(3).to_string())
            
            print("\nInsights:")
            rating_duration = corr.loc['rating', 'duration']
            rating_year = corr.loc['rating', 'release_year']
            
            if abs(rating_duration) > 0.3:
                direction = "positive" if rating_duration > 0 else "negative"
                print(f"  - Rating and duration have a {direction} correlation ({rating_duration:.2f})")
            else:
                print(f"  - Rating and duration show weak correlation ({rating_duration:.2f})")
            
            if abs(rating_year) > 0.3:
                direction = "positive" if rating_year > 0 else "negative"
                print(f"  - Rating and release year have a {direction} correlation ({rating_year:.2f})")
            else:
                print(f"  - Rating and release year show weak correlation ({rating_year:.2f})")
            
        except Exception as e:
            print(f"Error analyzing correlations: {e}")


def main():
    try:
        app = MediaTrackerApp()
        app.run()
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"Critical error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()