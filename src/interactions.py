from src.media import MediaItem
from src.enums import MediaType, Status
from src.catalog import MediaCatalog
from datetime import datetime, date
from src.reminder import Reminder

def describe_item(item: MediaItem) -> str:
    item_type = item.get_media_type()
    item_status = item.status
    title, release_date, item_rating, duration, genres_str, authors_str, description, video_path = item.get_summary()

    handlers = {
        (MediaType.VIDEO, Status.WATCHED): lambda i: f"Watched '{i.title}' ({i.duration} min)",
        (MediaType.VIDEO, Status.WATCHING): lambda i: f"Currently watching '{i.title}'",
        (MediaType.VIDEO, Status.ON_HOLD): lambda i: f"'{i.title}' is on hold",
        (MediaType.VIDEO, Status.PLANNED): lambda i: f"'{i.title}' is in watchlist",
    }

    handler = handlers.get((item_type, item_status))
    item_status_msg = handler(item) if handler else f"'{item.title}' (status: {item_status})"

    description_text = (
        f"\t{item_status_msg}\n"
        f"\n\tAbout:\n"
        f"\tTitle: {title}\n"
        f"\tRelease date: {release_date}\n"
        f"\tRating: {item_rating}/10\n"
        f"\tDuration: {duration} min\n"
    )
    
    if authors_str:
        description_text += f"\tAuthors: {authors_str}\n"
    
    if description:
        description_text += f"\tDescription: {description}\n"
    
    if video_path:
        description_text += f"\tVideo path: {video_path}\n"
    
    description_text += f"\tGenres: {genres_str}"
    
    if item_rating >= 8.5:
        return "\tMasterpiece!\n\n" + description_text
    return description_text

def change_status(catalog: MediaCatalog, item_id: int, new_status: Status):
    item = catalog.get_item(item_id)    
    item.status = new_status

def get_upcoming_releases(reminder: Reminder, days_ahead=30) -> str:
    reminders = reminder.get_all_reminders()
    upcoming_releases = ""
    for title, days in reminders:
        if 0 <= days <= days_ahead:
            upcoming_releases += f"\tTitle: {title}\n\tDays until reminder: {days}\n\n"
    return upcoming_releases