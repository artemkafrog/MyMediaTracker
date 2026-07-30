import sys
import os
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

class MediaTrackerApp:
    def __init__(self):
        self.catalog = MediaCatalog()
        self.db = DatabaseManager()
        self.reminder = Reminder(self.catalog)

        self.analytics = AnalyticsDataLoader(self.db.db_path)
        self.recommender = None  
        self.analyzer = None

        self._load_from_db()
    
    def _load_from_db(self) -> None:
        items = self.db.get_all_items()
        for item in items:
            self.catalog.add_item(item)
        print(f"Loaded {len(items)} items from database")
    
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
        print("9. Exit")
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
            print(f"  ID: {id(item)} - {item.title} ({item.status.value})")
        
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