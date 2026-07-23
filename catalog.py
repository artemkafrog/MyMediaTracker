import re
import unicodedata
from media import MediaItem, Movie, TVSeries, Book
from enums import MediaType, Status, Genre
from exceptions import DuplicateError, ValidationError, NotFoundError
from secrets import randbits
from rapidfuzz import process, fuzz # for parsing

NOISE = {
    "фильм", "смотреть", "онлайн", "скачать", "бесплатно", "кино", 
    "сериал", "книга", "читать", "скачать", "купить", "новый", 
    "лучший", "популярный", "топ", "сезон", "серия",

    "movie", "film", "watch", "online", "download", "free", "cinema",
    "series", "tv", "show", "book", "read", "buy", "new", "best",
    "top", "season", "episode", "the", "a", "an"
}

class MediaCatalog:
    def __init__(self):
        self._items: dict[int, MediaItem] = {}
        self._by_status: dict[Status, set[int]] = {
            Status.WATCHED: set(),  
            Status.WATCHING: set(),
            Status.PLANNED: set(),
            Status.ON_HOLD: set()
        }
        self._by_type: dict[MediaType, set[int]] = {
            MediaType.MOVIE: set(),
            MediaType.TV_SERIES: set(),
            MediaType.BOOK: set()
        }
        self._by_genre: dict[str, set[int]] = {}
        self._title_index: dict[str, set[int]] = {}


    def add_item(self, item: MediaItem) -> int:
        duplicates = [existing for existing in self._items.values()
                      if existing.title.lower() == item.title.lower()
                      and isinstance(existing, type(item))]
        if duplicates:
            raise DuplicateError("This item already exists.")

        item_id = randbits(32)

        self._items[item_id] = item
        self._by_status[item.status].add(item_id)

        media_type = self._get_media_type(item)
        self._by_type[media_type].add(item_id)

        for genre in item.genres:
            genre = genre.lower()
            if genre not in self._by_genre:
                self._by_genre[genre] = set()
            self._by_genre[genre].add(item_id)

        self._index_title(item.title, item_id)
        return item_id

    def _index_title(self, title: str, item_id: int):
        clean_title = self._clean_title(title)
        words = clean_title.split()
        
        for word in words:
            if len(word) > 2: 
                if word not in self._title_index:
                    self._title_index[word] = set()
                self._title_index[word].add(item_id)
        
        if clean_title not in self._title_index:
            self._title_index[clean_title] = set()
        self._title_index[clean_title].add(item_id)

    def _get_media_type(self, item: MediaItem) -> Movie | TVSeries | Book | None:
        if isinstance(item, Movie):
            return MediaType.MOVIE
        elif isinstance(item, TVSeries):
            return MediaType.TV_SERIES
        elif isinstance(item, Book):
            return MediaType.BOOK
        return None

    def get_by_status(self, status: Status) -> list[MediaItem]:
        ids = self._by_status.get(status, set())
        return [self._items[id] for id in ids if id in self._items]

    def get_by_type(self, type: MediaType) -> list[MediaItem]:
        ids = self._by_type.get(type, set())
        return [self._items[id] for id in ids if id in self._items]

    def get_by_genres(self, genre: str) -> list[MediaItem]:
        genre = genre.lower()
        ids = self._by_genre.get(genre, set())
        return [self._items[id] for id in ids if id in self._items]

    def get_top_rated(self, n: int, type: MediaType = None) -> list[MediaItem]:
        if type:
            items = self.get_by_type(type)
        else:
            items = list(self._items.values())

        if len(items) < n:
            raise ValidationError("Not enough items in the catalog") 
        sorted_items = sorted([item for item in items], key=lambda x: x._rating, reverse=True)
        return sorted_items[:n]
        
    def search_item(self, query: str = "", **kwargs) -> MediaItem:
        if not query:
            raise ValidationError("Search query cannot be empty")
        
        parsed_query = self._parse_query(query)
        if parsed_query.get("genre") or parsed_query.get("media_type") or parsed_query.get("year"):
            return self._search_with_filters(parsed_query)
        return self._search_by_title(parsed_query["title"])

    def _search_with_filters(self, parsed_query: dict[str, str]) -> MediaItem:
        candidates = set(self._items.keys())
        
        if parsed_query.get("media_type"):
            type_ids = self._by_type.get(parsed_query["media_type"], set())
            candidates &= type_ids
        
        if parsed_query.get("genre"):
            genre_ids = self._by_genre.get(parsed_query["genre"].lower(), set())
            candidates &= genre_ids
        
        if parsed_query.get("year"):
            year = parsed_query["year"]
            candidates = {
                id for id in candidates 
                if self._items[id]._release_date.year == year
            }
        
        if parsed_query.get("title"):
            title = parsed_query["title"]
            title_candidates = self._find_by_title(title, candidates)
            if title_candidates:
                candidates = title_candidates
            else:
                items = [self._items[id] for id in candidates]
                if items:
                    best = process.extractOne(
                        title,
                        items,
                        scorer=fuzz.WRatio,
                        processor=lambda x: x.title
                    )
                    if best:
                        return best[0]
        
        if not candidates:
            raise NotFoundError(f"No items found for query")
        
        return self._items[next(iter(candidates))]
    
    def _search_by_title(self, title: str) -> MediaItem:
        catalog = list(self._items.values())
        
        if not catalog:
            raise NotFoundError("Catalog is empty")
        
        title_lower = title.lower()
        found_ids = set()
        for word in title_lower.split():
            if word in self._title_index:
                found_ids.update(self._title_index[word])
        
        if found_ids:
            best_item = max([self._items[id] for id in found_ids], 
                          key=lambda x: fuzz.WRatio(title_lower, x.title.lower()))
            return best_item
        
        best_matched = process.extractOne(
            title,
            catalog,
            scorer=fuzz.WRatio,
            processor=lambda x: x.title
        )
        
        if not best_matched or best_matched[1] < 60:  
            clean_title = self._clean_title(title)
            best_matched = process.extractOne(
                clean_title,
                catalog,
                scorer=fuzz.partial_ratio,
                processor=lambda x: self._clean_title(x.title)
            )
            
            if not best_matched or best_matched[1] < 50:
                raise NotFoundError(f"No items found for: {title}")
        
        return best_matched[0]

    def _find_by_title(self, title: str, candidate_ids: set) -> set:
        title_lower = title.lower()
        found_ids = set()
        
        for word in title_lower.split():
            if len(word) > 2 and word in self._title_index:
                found_ids.update(self._title_index[word] & candidate_ids)
        
        return found_ids

    def search_all(self, query: str = "") -> list[MediaItem]:
        if not query:
            return list(self._items.values())
        
        parsed_query = self._parse_query(query)
        catalog = list(self._items.values())
        
        matches = process.extract(
            parsed_query["title"],
            catalog,
            scorer=fuzz.WRatio,
            processor=lambda x: x.title,
            limit=10,
            score_cutoff=60
        )
        
        return [match[0] for match in matches]

    def _clean_title(self, title: str) -> str:
        title_clean = re.sub(r'[^\w\s]', '', title)
        title_clean = title_clean.lower()
        tokens = title_clean.split()
        clean_tokens = [t for t in tokens if t not in NOISE]
        return " ".join(clean_tokens)

    def _clean_query(self, query: str) -> list[str]:
        query_normalized = unicodedata.normalize('NFKD', query).encode('ascii', 'ignore').decode('utf-8')
        query_clean = re.sub(r'[^\w\s]', '', query_normalized.lower())
        return query_clean.split()

    def _parse_query(self, query: str) -> dict[str, str]:
        parsed_query = {
            "title": "",
            "year": None,
            "media_type": None,
            "genre": None
        }
        
        query_lower = query.lower()
        original_query = query
        
        year_match = re.search(r'\b(19\d{2}|20\d{2})\b', query)
        if year_match:
            parsed_query["year"] = int(year_match.group(0))
            query = query.replace(year_match.group(0), "")
            query_lower = query_lower.replace(year_match.group(0), "")
        
        type_keywords = {
            MediaType.MOVIE: {"фильм", "movie", "film", "кино", "cinema"},
            MediaType.TV_SERIES: {"сериал", "series", "tv", "show", "телесериал"},
            MediaType.BOOK: {"книга", "book", "читать", "read"}
        }
        
        for media_type, keywords in type_keywords.items():
            for keyword in keywords:
                if keyword in query_lower:
                    parsed_query["media_type"] = media_type
                    query = query.replace(keyword, "")
                    query_lower = query_lower.replace(keyword, "")
                    break
            if parsed_query["media_type"]:
                break
        
        genres = {
            "comedy": "комедия",
            "drama": "драма",
            "action": "боевик",
            "thriller": "триллер",
            "horror": "ужасы",
            "sci-fi": "фантастика",
            "fantasy": "фэнтези",
            "romance": "романтика",
            "adventure": "приключения",
            "mystery": "детектив",
            "biography": "биография",
            "documentary": "документальный",
            "history": "исторический",
            "western": "вестерн",
            "musical": "мюзикл",
            "family": "семейный"
        }
        
        for eng, rus in genres.items():
            if eng in query_lower or rus in query_lower:
                parsed_query["genre"] = rus
                query = query.replace(eng, "").replace(rus, "")
                query_lower = query_lower.replace(eng, "").replace(rus, "")
                break
        
        tokens = self._clean_query(query)
        clean_tokens = [token for token in tokens if token not in NOISE and len(token) > 1]
        
        if clean_tokens:
            parsed_query["title"] = " ".join(clean_tokens)
        
        return parsed_query

    def remove_item(self, item_id: int) -> None:
        if item_id not in self._items:
            raise NotFoundError(f"Item with ID {item_id} not found")
        
        item = self._items[item_id]
        self._by_status[item.status].discard(item_id)
        
        media_type = self._get_media_type(item)
        if media_type:
            self._by_type[media_type].discard(item_id)
        
        for genre in item._genres:
            genre_lower = genre.lower()
            if genre_lower in self._by_genre:
                self._by_genre[genre_lower].discard(item_id)
                if not self._by_genre[genre_lower]:
                    del self._by_genre[genre_lower]
        
        for key in list(self._title_index.keys()):
            self._title_index[key].discard(item_id)
            if not self._title_index[key]:
                del self._title_index[key]
        
        del self._items[item_id]

    def update_status(self, item_id: int, new_status: Status) -> None:
        if item_id not in self._items:
            raise NotFoundError(f"Item with ID {item_id} not found")
        
        item = self._items[item_id]
        old_status = item.status
        
        if old_status != new_status:
            self._by_status[old_status].discard(item_id)
            self._by_status[new_status].add(item_id)
            item.status = new_status

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self):
        return iter(self._items.values())

    def __contains__(self, item_id: int) -> bool:
        return item_id in self._items




        