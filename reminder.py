from datetime import datetime, date, timedelta
from catalog import MediaCatalog
from exceptions import NotFoundError

class Reminder:
    def __init__(self, catalog: MediaCatalog, reminders: dict[int,datetime] = {}):
        self._catalog = catalog
        self._reminders = reminders

    def schedule_reminder(self, item_id: int, days_before: int) -> str:
        item = self._catalog.get_item(item_id)
        title = item.title
        release_date = item.release_date

        target_date = release_date - timedelta(days=days_before)
        def check_reminder():
            today =  date.today()
            if today >= target_date:
                return f"The reminder: time to watch {title}."
            else:
                days = target_date - today
                return f"The reminder: {days} day(s) left. {title}."
        return check_reminder

    def add_reminder(self, item_id: int, date_reminder: datetime) -> str:
        if item_id not in self._reminders:
            self._reminders[item_id] = date_reminder
            return "Date added"
        else:
            self._reminders[item_id] = date_reminder
            return "Date changed"
        
    def get_reminder(self, item_id: int)  -> str:
        if item_id not in self._reminders:
            raise NotFoundError("This item doesn't have a reminder")

        today = date.today()
        target_date = self._reminders[item_id]
        delta = target_date - today
        days = delta.days

        item = self._catalog.get_item(item_id)
        title = item.title

        if days >= 1:
            return f"The reminder: {days} day(s) left. {title}."
        elif days == 0:
            return f"The reminder: today. {title}."
        else:
            return f"The {title} reminder was {days} day(s) ago."

    def get_all_reminders(self) -> str:
        for item_id in self._reminders.keys():

            today = date.today()
            target_date = self._reminders[item_id]
            delta = target_date - today
            days = delta.days

            item = self._catalog.get_item(item_id)
            title = item.title

            if days >= 1:
                return f"The reminder: {days} day(s) left. {title}."
            elif days == 0:
                return f"The reminder: today. {title}."
            else:
                return f"The {title} reminder was {days} day(s) ago."
