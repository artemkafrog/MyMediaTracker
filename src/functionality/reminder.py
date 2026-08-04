from datetime import date, timedelta

from src.functionality.catalog import MediaCatalog
from src.functionality.exceptions import NotFoundError

class Reminder:
    """Manages reminders for media items."""

    def __init__(self, catalog: MediaCatalog, reminders: dict[int, date] = None):
        self._catalog = catalog
        self._reminders = reminders.copy() if reminders else {}

    def schedule_reminder(self, item_id: int, days_before: int) -> str:
        """Schedule a reminder for an item."""
        item = self._catalog.get_item(item_id)
        title = item.title
        release_date = item.release_date

        target_date = release_date - timedelta(days=days_before)

        def check_reminder():
            today = date.today()
            if today >= target_date:
                return f"The reminder: time to watch {title}."
            else:
                days = target_date - today
                return f"The reminder: {days} day(s) left. {title}."

        return check_reminder

    def add_reminder(self, item_id: int, date_reminder: date) -> str:
        """Add or update a reminder for an item."""
        if item_id not in self._reminders:
            self._reminders[item_id] = date_reminder
            return "Date added"
        else:
            self._reminders[item_id] = date_reminder
            return "Date changed"

    def get_reminder(self, item_id: int) -> tuple[str, int]:
        """Get reminder details for an item."""
        if item_id not in self._reminders:
            raise NotFoundError("This item doesn't have a reminder")

        today = date.today()
        target_date = self._reminders[item_id]
        days = (target_date - today).days

        item = self._catalog.get_item(item_id)
        title = item.title

        return (title, days)

    def get_all_reminders(self) -> list[tuple[str, int]]:
        """Get all reminders with days remaining."""
        reminders = []
        today = date.today()

        for item_id in self._reminders.keys():
            target_date = self._reminders[item_id]
            days = (target_date - today).days

            item = self._catalog.get_item(item_id)
            title = item.title

            reminders.append((title, days))

        return reminders