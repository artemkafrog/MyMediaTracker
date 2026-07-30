import sqlite3
import json
from datetime import date
from contextlib import contextmanager
from pathlib import Path
from src.functionality.media import MediaItem
from src.functionality.enums import MediaType, Status
from src.functionality.exceptions import NotFoundError, DuplicateError, ValidationError


class DatabaseManager:
    def __init__(self, db_path: str = "data/media_tracker.db"):
        self._db_path = db_path
        self._init_db()

    @property
    def db_path(self):
        return self._db_path
    
    @contextmanager
    def _get_connection(self):
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.executescript("""
                CREATE TABLE IF NOT EXISTS media_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    media_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    rating REAL CHECK(rating >= 0 AND rating <= 10),
                    release_date TEXT,
                    genres TEXT,
                    description TEXT,
                    authors TEXT,
                    video_path TEXT,
                    duration INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id INTEGER NOT NULL,
                    reminder_date TEXT NOT NULL,
                    message TEXT,
                    is_done BOOLEAN DEFAULT 0,
                    FOREIGN KEY (item_id) REFERENCES media_items(id) ON DELETE CASCADE
                );
                
                CREATE INDEX IF NOT EXISTS idx_status ON media_items(status);
                CREATE INDEX IF NOT EXISTS idx_rating ON media_items(rating);
                CREATE INDEX IF NOT EXISTS idx_reminder_date ON reminders(reminder_date);
            """)
        
    def _item_to_db_data(self, item: MediaItem) -> dict:
        data = {
            'title': item.title,
            'media_type': item.get_media_type().value,
            'status': item.status.value,
            'rating': item.rating,
            'release_date': item.release_date.isoformat() if item.release_date else None,
            'genres': json.dumps(item.genres),
            'description': item.description,
            'authors': json.dumps(item.authors),
            'video_path': item.video_path,
            'duration': item.duration
        }
        return data
    
    def _db_row_to_item(self, row: dict) -> MediaItem | None:
        if not row:
            return None
        
        media_type = MediaType(row['media_type'])
        status = Status(row['status'])
        release_date = date.fromisoformat(row['release_date']) if row['release_date'] else date.today()
        genres = json.loads(row['genres']) if row['genres'] else []
        authors = json.loads(row['authors']) if row['authors'] else []
        
        item = MediaItem(
            title=row['title'],
            release_date=release_date,
            rating=row['rating'],
            status=status,
            genres=genres,
            description=row.get('description', ''),
            authors=authors,
            video_path=row.get('video_path', ''),
            duration=row.get('duration', 0)
        )
        # Сохраняем ID из БД
        item._db_id = row['id']
        return item
        
    def add_item(self, item: MediaItem) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT id FROM media_items WHERE title = ? AND media_type = ?",
                (item.title, item.get_media_type().value)
            )
            existing = cursor.fetchone()
            if existing:
                return existing['id']
            
            data = self._item_to_db_data(item)
            
            cursor.execute("""
                INSERT INTO media_items (title, media_type, status, rating, release_date, genres, description, authors, video_path, duration)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data['title'],
                data['media_type'],
                data['status'],
                data['rating'],
                data['release_date'],
                data['genres'],
                data['description'],
                data['authors'],
                data['video_path'],
                data['duration']
            ))
            
            return cursor.lastrowid
    
    def get_item(self, item_id: int) -> MediaItem | None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM media_items WHERE id = ?", (item_id,))
            row = cursor.fetchone()
            if not row:
                return None
            
            return self._db_row_to_item(dict(row))
    
    def get_item_id_by_title(self, title: str) -> int | None:
        """Get database ID by title"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM media_items WHERE title = ?", (title,))
            row = cursor.fetchone()
            return row['id'] if row else None
    
    def get_item_by_title(self, title: str) -> dict | None:
        """Get item by title"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM media_items WHERE title = ?", (title,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def update_item(self, item_id: int, item: MediaItem) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT media_type FROM media_items WHERE id = ?", (item_id,))
            row = cursor.fetchone()
            if not row:
                return False
            
            data = self._item_to_db_data(item)
            
            cursor.execute("""
                UPDATE media_items 
                SET title = ?, status = ?, rating = ?, release_date = ?, genres = ?, 
                    description = ?, authors = ?, video_path = ?, duration = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                data['title'],
                data['status'],
                data['rating'],
                data['release_date'],
                data['genres'],
                data['description'],
                data['authors'],
                data['video_path'],
                data['duration'],
                item_id
            ))
            
            return True
    
    def delete_item(self, item_id: int) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM media_items WHERE id = ?", (item_id,))
            return cursor.rowcount > 0
    
    def delete_item_by_title(self, title: str) -> bool:
        """Delete item by title"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM media_items WHERE title = ?", (title,))
            return cursor.rowcount > 0
    
    def get_all_items(self) -> list[MediaItem]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM media_items ORDER BY title")
            ids = [row['id'] for row in cursor.fetchall()]
            
            items = []
            for item_id in ids:
                item = self.get_item(item_id)
                if item:
                    items.append(item)
            return items
        
    def search_items(self, 
                     title: str = None,
                     status: Status = None,
                     media_type: MediaType = None,
                     min_rating: float = None,
                     genre: str = None,
                     author: str = None) -> list[MediaItem]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            conditions = []
            params = []
            
            if title:
                conditions.append("title LIKE ?")
                params.append(f"%{title}%")
            
            if status:
                conditions.append("status = ?")
                params.append(status.value)
            
            if media_type:
                conditions.append("media_type = ?")
                params.append(media_type.value)
            
            if min_rating is not None:
                conditions.append("rating >= ?")
                params.append(min_rating)
            
            if genre:
                conditions.append("genres LIKE ?")
                params.append(f"%{genre}%")
            
            if author:
                conditions.append("authors LIKE ?")
                params.append(f"%{author}%")
            
            where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
            query = f"SELECT id FROM media_items{where_clause} ORDER BY rating DESC"
            
            cursor.execute(query, params)
            ids = [row['id'] for row in cursor.fetchall()]
            
            items = []
            for item_id in ids:
                item = self.get_item(item_id)
                if item:
                    items.append(item)
            return items
    
    def get_by_status(self, status: Status) -> list[MediaItem]:
        return self.search_items(status=status)
    
    def get_by_type(self, media_type: MediaType) -> list[MediaItem]:
        return self.search_items(media_type=media_type)
    
    def get_by_genre(self, genre: str) -> list[MediaItem]:
        return self.search_items(genre=genre)
    
    def get_by_author(self, author: str) -> list[MediaItem]:
        return self.search_items(author=author)
    
    def get_top_rated(self, n: int, media_type: MediaType = None) -> list[MediaItem]:
        items = self.search_items(media_type=media_type) if media_type else self.get_all_items()
        if len(items) < n:
            raise ValidationError(f"Not enough items. Need {n}, have {len(items)}")
        return sorted(items, key=lambda x: x.rating, reverse=True)[:n]
        
    def add_reminder(self, item_id: int, reminder_date: date, message: str = "") -> int:
        if not self.get_item(item_id):
            raise NotFoundError(f"Item with ID {item_id} not found")
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO reminders (item_id, reminder_date, message)
                VALUES (?, ?, ?)
            """, (item_id, reminder_date.isoformat(), message))
            return cursor.lastrowid
    
    def get_reminders(self, before_date: date = None) -> list[dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = """
                SELECT r.*, m.title 
                FROM reminders r
                JOIN media_items m ON r.item_id = m.id
                WHERE r.is_done = 0
            """
            params = []
            if before_date:
                query += " AND r.reminder_date <= ?"
                params.append(before_date.isoformat())
            query += " ORDER BY r.reminder_date"
            
            cursor.execute(query, params)
            result = []
            for row in cursor.fetchall():
                reminder = dict(row)
                reminder['reminder_date'] = date.fromisoformat(reminder['reminder_date'])
                result.append(reminder)
            return result
    
    def mark_reminder_done(self, reminder_id: int) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE reminders SET is_done = 1 WHERE id = ?", (reminder_id,))
            return cursor.rowcount > 0
        
    def get_stats(self) -> dict:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) as total FROM media_items")
            total = cursor.fetchone()['total']
            
            cursor.execute("""
                SELECT status, COUNT(*) as count 
                FROM media_items 
                GROUP BY status
            """)
            by_status = {Status(row['status']): row['count'] for row in cursor.fetchall()}
            
            cursor.execute("SELECT AVG(rating) as avg_rating FROM media_items")
            avg_rating = cursor.fetchone()['avg_rating'] or 0
            
            cursor.execute("""
                SELECT media_type, COUNT(*) as count 
                FROM media_items 
                GROUP BY media_type
            """)
            by_type = {MediaType(row['media_type']): row['count'] for row in cursor.fetchall()}
            
            cursor.execute("SELECT SUM(duration) as total_duration FROM media_items")
            total_duration = cursor.fetchone()['total_duration'] or 0
            
            return {
                'total': total,
                'by_status': by_status,
                'by_type': by_type,
                'avg_rating': round(avg_rating, 2),
                'total_duration': total_duration
            }
        
    def __len__(self) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as total FROM media_items")
            return cursor.fetchone()['total']
    
    def __iter__(self):
        return iter(self.get_all_items())
    
    def __contains__(self, item_id: int) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM media_items WHERE id = ?", (item_id,))
            return cursor.fetchone() is not None