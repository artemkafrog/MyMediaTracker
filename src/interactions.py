from src.media import MediaItem
from src.enums import MediaType, Status
from src.catalog import MediaCatalog
from datetime import datetime, date
from src.reminder import Reminder

def describe_item(item: MediaItem) -> str:
    item_type = item.get_media_type()
    item_status = item.status
    title, release_date, item_rating, *others, genres_str = item.get_summary()

    handlers = {
        (MediaType.BOOK, Status.WATCHED): lambda i: f"Finished reading '{i.title}'",
        (MediaType.BOOK, Status.WATCHING): lambda i: f"Currently reading '{i.title}'",
        (MediaType.BOOK, Status.ON_HOLD): lambda i: f"'{i.title}' is on hold",
        (MediaType.BOOK, Status.PLANNED): lambda i: f"'{i.title}' is in reading list",
        
        (MediaType.MOVIE, Status.WATCHED): lambda i: f"Watched '{i.title}' in {i.get_duration()} min",
        (MediaType.MOVIE, Status.WATCHING): lambda i: f"Watching '{i.title}'",
        (MediaType.MOVIE, Status.ON_HOLD): lambda i: f"'{i.title}' is paused",
        (MediaType.MOVIE, Status.PLANNED): lambda i: f"'{i.title}' is in watchlist",
        
        (MediaType.TV_SERIES, Status.WATCHED): lambda i: f"Finished '{i.title}' ({i.get_total_episodes()} episodes)",
        (MediaType.TV_SERIES, Status.WATCHING): lambda i: f"Watching '{i.title}'",
        (MediaType.TV_SERIES, Status.ON_HOLD): lambda i: f"'{i.title}' is on hold",
        (MediaType.TV_SERIES, Status.PLANNED): lambda i: f"'{i.title}' is in watchlist",
    }

    handler = handlers.get((item_type, item_status))
    item_status_msg = handler(item)

    description = (
        f"\t{item_status_msg}\n"
        f"\n\tAbout:\n"
        f"\tTitle: {title}\n"
        f"\tRelease date: {release_date}\n"
        f"\tRating: {item_rating}/10\n"
    )

    match item_type:
        case MediaType.BOOK:
            description = description + f"\tPages: {others[0]}\n"
        case MediaType.MOVIE:
            description = description + f"\tMinutes: {others[0]}\n"
        case MediaType.TV_SERIES:
            description = description + f"\tSeasons: {others[0]}\n" + \
            f"\tEpisodes: {others[1]}\n" + f"\tSummary time: {others[2]} min\n"
    description = description + f"\tGenres: {genres_str}"
    if item_rating >= 8.5:
        return "\tMasterpiece!\n\n" + description
    return description

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
