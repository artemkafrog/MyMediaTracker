import os
import sys
import json
import shutil
import subprocess
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Any

from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename

PROJECT_ROOT = Path(__file__).parent.parent

sys.path.append(str(PROJECT_ROOT))

from src.functionality.catalog import MediaCatalog
from src.functionality.database import DatabaseManager
from src.functionality.media import MediaItem
from src.functionality.enums import Status, MediaType
from src.functionality.exceptions import NotFoundError, DuplicateError, ValidationError
from src.functionality.file_io import export_to_csv
from src.functionality.reminder import Reminder

app = Flask(__name__)
app.config['SECRET_KEY'] = 'media-tracker-secret-key'
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

app.jinja_env.variable_start_string = '{['
app.jinja_env.variable_end_string = ']}'

CORS(app)

catalog = MediaCatalog()
db = DatabaseManager()
reminder = Reminder(catalog)

def load_catalog():
    try:
        items = db.get_all_items()
        for item in items:
            try:
                db_id = db.get_item_id_by_title(item.title)
                if db_id:
                    item._db_id = db_id
                catalog.add_item(item)
            except DuplicateError:
                pass
        print(f"Loaded {len(items)} items from database")
    except Exception as e:
        print(f"Error loading catalog: {e}")

load_catalog()

UPLOAD_FOLDER = PROJECT_ROOT / 'uploads'
THUMBNAIL_FOLDER = PROJECT_ROOT / 'thumbnails'
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mkv', 'mov', 'webm'}

UPLOAD_FOLDER.mkdir(exist_ok=True)
THUMBNAIL_FOLDER.mkdir(exist_ok=True)

print(f"Upload folder: {UPLOAD_FOLDER.absolute()}")
print(f"Thumbnail folder: {THUMBNAIL_FOLDER.absolute()}")

def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_video_info(filepath: Path) -> Dict[str, Any]:
    info = {
        'duration': 0,
        'width': 0,
        'height': 0,
        'size': 0,
        'codec': 'unknown'
    }
    
    if not filepath.exists():
        return info
    
    try:
        result = subprocess.run(
            ['ffprobe', '-version'],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode != 0:
            return info
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return info
    
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 
             'format=duration,size', '-show_entries', 
             'stream=width,height,codec_name', 
             '-of', 'json', str(filepath)],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0 and result.stdout:
            data = json.loads(result.stdout)
            
            if 'format' in data:
                format_data = data['format']
                if 'duration' in format_data:
                    info['duration'] = int(float(format_data['duration']))
                if 'size' in format_data:
                    info['size'] = int(format_data['size'])
            
            if 'streams' in data:
                for stream in data['streams']:
                    if stream.get('codec_type') == 'video':
                        if 'width' in stream:
                            info['width'] = int(stream['width'])
                        if 'height' in stream:
                            info['height'] = int(stream['height'])
                        if 'codec_name' in stream:
                            info['codec'] = stream['codec_name']
                        break
                        
    except Exception:
        pass
    
    return info

def generate_thumbnail(filepath: Path, thumbnail_path: Path, time_pos: float = 1.0) -> bool:
    if not filepath.exists():
        return False
    
    try:
        result = subprocess.run(
            ['ffmpeg', '-version'],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode != 0:
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
    
    try:
        cmd = [
            'ffmpeg', '-i', str(filepath),
            '-ss', str(time_pos),
            '-vframes', '1',
            '-vf', 'scale=320:-1',
            '-q:v', '2',
            '-y',
            str(thumbnail_path)
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0 and thumbnail_path.exists():
            return True
        return False
            
    except Exception:
        return False

def item_to_dict(item: MediaItem) -> Dict[str, Any]:
    db_id = db.get_item_id_by_title(item.title)
    if db_id:
        item_id = db_id
    elif hasattr(item, '_db_id') and item._db_id:
        item_id = item._db_id
    else:
        import hashlib
        item_id = int(hashlib.md5(item.title.lower().encode()).hexdigest()[:8], 16)
    
    thumbnail_path = THUMBNAIL_FOLDER / f"{item_id}.jpg"
    has_thumbnail = thumbnail_path.exists()
    
    return {
        'id': item_id,
        'title': item.title,
        'release_date': item.release_date.isoformat() if item.release_date else None,
        'rating': item.rating,
        'status': item.status.value,
        'genres': item.genres,
        'description': item.description,
        'authors': item.authors,
        'video_path': item.video_path,
        'duration': item.duration,
        'media_type': item.get_media_type().value,
        'year': item.release_date.year if item.release_date else None,
        'has_thumbnail': has_thumbnail,
        'thumbnail_url': f'/api/thumbnail/{item_id}.jpg' if has_thumbnail else None
    }

def status_from_string(status_str: str) -> Status:
    status_map = {
        'watched': Status.WATCHED,
        'watching': Status.WATCHING,
        'planned': Status.PLANNED,
        'on_hold': Status.ON_HOLD
    }
    return status_map.get(status_str.lower(), Status.PLANNED)

@app.route('/')
def index():
    return render_template('carousel.html')

@app.route('/collection')
def collection():
    return render_template('index.html')

@app.route('/carousel')
def carousel():
    return render_template('carousel.html')

@app.route('/analytics')
def analytics():
    return render_template('analytics.html')

# ==================== СТАТИКА ДЛЯ ОТЧЕТОВ ====================

@app.route('/static/reports/figures/<path:filename>')
def serve_report_figure(filename):
    try:
        # Ищем файл в reports/figures/ относительно корня проекта
        filepath = PROJECT_ROOT / 'reports' / 'figures' / filename
        if not filepath.exists():
            return jsonify({'success': False, 'error': 'File not found: ' + filename}), 404
        
        return send_file(str(filepath), mimetype='image/png')
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/static/reports/<path:filename>')
def serve_report_static(filename):
    try:
        filepath = PROJECT_ROOT / 'reports' / filename
        if not filepath.exists():
            return jsonify({'success': False, 'error': 'File not found'}), 404
        
        return send_file(str(filepath))
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/items', methods=['GET'])
def get_items():
    try:
        status_filter = request.args.get('status')
        
        if status_filter:
            try:
                status = Status(status_filter)
                items = catalog.get_by_status(status)
            except ValueError:
                items = list(catalog)
        else:
            items = list(catalog)
        
        sort_by = request.args.get('sort', 'title')
        reverse = request.args.get('reverse', 'false').lower() == 'true'
        
        sort_map = {
            'title': lambda x: x.title.lower(),
            'rating': lambda x: x.rating,
            'year': lambda x: x.release_date.year if x.release_date else 0,
            'duration': lambda x: x.duration,
            'status': lambda x: x.status.value
        }
        
        if sort_by in sort_map:
            items.sort(key=sort_map[sort_by], reverse=reverse)
        
        return jsonify({
            'success': True,
            'items': [item_to_dict(item) for item in items],
            'total': len(items)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/items', methods=['POST'])
def add_item():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        title = data.get('title', '').strip()
        if not title:
            return jsonify({'success': False, 'error': 'Title is required'}), 400
        
        year = data.get('year')
        release_date = date(year, 1, 1) if year else date.today()
        
        rating = float(data.get('rating', 0))
        rating = max(0, min(10, rating))
        
        status = status_from_string(data.get('status', 'planned'))
        
        genres_str = data.get('genres', '')
        genres = [g.strip() for g in genres_str.split(',') if g.strip()]
        
        authors_str = data.get('authors', '')
        authors = [a.strip() for a in authors_str.split(',') if a.strip()]
        
        duration = int(data.get('duration', 0))
        video_path = data.get('video_path', '')
        
        if video_path and duration == 0:
            try:
                filename = video_path.split('/')[-1]
                filepath = UPLOAD_FOLDER / filename
                if filepath.exists():
                    info = extract_video_info(filepath)
                    if info['duration'] > 0:
                        duration = info['duration'] // 60
            except Exception:
                pass
        
        item = MediaItem(
            title=title,
            release_date=release_date,
            rating=rating,
            status=status,
            genres=genres,
            description=data.get('description', ''),
            authors=authors,
            video_path=video_path,
            duration=duration
        )
        
        db_id = db.add_item(item)
        if db_id:
            item._db_id = db_id
        
        item_id = catalog.add_item(item)
        
        thumbnail_generated = False
        if video_path:
            try:
                filename = video_path.split('/')[-1]
                filepath = UPLOAD_FOLDER / filename
                if filepath.exists():
                    thumbnail_path = THUMBNAIL_FOLDER / f"{db_id or item_id}.jpg"
                    thumbnail_generated = generate_thumbnail(filepath, thumbnail_path, time_pos=1.0)
            except Exception:
                pass
        
        return jsonify({
            'success': True,
            'item': item_to_dict(item),
            'message': f'Item "{title}" added successfully',
            'thumbnail_generated': thumbnail_generated
        })
        
    except DuplicateError as e:
        return jsonify({'success': False, 'error': str(e)}), 409
    except ValidationError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/items/<int:item_id>', methods=['PUT'])
def update_item(item_id: int):
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        item = None
        for cat_item in catalog:
            db_id = db.get_item_id_by_title(cat_item.title)
            if db_id == item_id:
                item = cat_item
                break
        
        if not item:
            return jsonify({'success': False, 'error': 'Item not found'}), 404
        
        if 'title' in data and data['title']:
            item._title = data['title'].strip()
        
        if 'rating' in data:
            item.rating = float(data['rating'])
        
        if 'status' in data:
            item.status = status_from_string(data['status'])
        
        if 'description' in data:
            item._description = data['description']
        
        if 'genres' in data:
            genres_str = data['genres']
            if isinstance(genres_str, str):
                item._genres = [g.strip() for g in genres_str.split(',') if g.strip()]
            else:
                item._genres = genres_str
        
        if 'authors' in data:
            authors_str = data['authors']
            if isinstance(authors_str, str):
                item._authors = [a.strip() for a in authors_str.split(',') if a.strip()]
            else:
                item._authors = authors_str
        
        if 'duration' in data:
            item._duration = int(data['duration'])
        
        if 'video_path' in data:
            old_video_path = item._video_path
            item._video_path = data['video_path']
            
            if old_video_path != item._video_path and item._video_path:
                try:
                    filename = item._video_path.split('/')[-1]
                    filepath = UPLOAD_FOLDER / filename
                    if filepath.exists():
                        thumbnail_path = THUMBNAIL_FOLDER / f"{item_id}.jpg"
                        generate_thumbnail(filepath, thumbnail_path, time_pos=1.0)
                except Exception:
                    pass
        
        db.update_item(item_id, item)
        
        return jsonify({
            'success': True,
            'item': item_to_dict(item),
            'message': 'Item updated successfully'
        })
        
    except NotFoundError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/items/<int:item_id>', methods=['DELETE'])
def delete_item(item_id: int):
    try:
        item = None
        cat_id = None
        for cat_item_id, cat_item in catalog._items.items():
            db_id = db.get_item_id_by_title(cat_item.title)
            if db_id == item_id:
                item = cat_item
                cat_id = cat_item_id
                break
        
        if not item or cat_id is None:
            return jsonify({'success': False, 'error': 'Item not found'}), 404
        
        catalog.remove_item(cat_id)
        db.delete_item(item_id)
        
        thumbnail_path = THUMBNAIL_FOLDER / f"{item_id}.jpg"
        if thumbnail_path.exists():
            thumbnail_path.unlink()
        
        return jsonify({
            'success': True,
            'message': 'Item deleted successfully'
        })
        
    except NotFoundError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/search', methods=['GET'])
def search_items():
    try:
        query = request.args.get('q', '').strip()
        
        if not query:
            return jsonify({
                'success': True,
                'items': [item_to_dict(item) for item in catalog],
                'total': len(catalog)
            })
        
        try:
            item = catalog.search_item(query)
            return jsonify({
                'success': True,
                'items': [item_to_dict(item)],
                'total': 1
            })
        except NotFoundError:
            items = catalog.search_all(query)
            return jsonify({
                'success': True,
                'items': [item_to_dict(item) for item in items],
                'total': len(items)
            })
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    try:
        stats = db.get_stats()
        
        by_status = {}
        for status, count in stats.get('by_status', {}).items():
            by_status[status.value if hasattr(status, 'value') else status] = count
        
        by_type = {}
        for media_type, count in stats.get('by_type', {}).items():
            by_type[media_type.value if hasattr(media_type, 'value') else media_type] = count
        
        return jsonify({
            'success': True,
            'stats': {
                'total': stats.get('total', 0),
                'by_status': by_status,
                'by_type': by_type,
                'avg_rating': stats.get('avg_rating', 0),
                'total_duration': stats.get('total_duration', 0)
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/genres', methods=['GET'])
def get_genres():
    try:
        genres = set()
        for item in catalog:
            genres.update(item.genres)
        return jsonify({
            'success': True,
            'genres': sorted(genres)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/statuses', methods=['GET'])
def get_statuses():
    try:
        return jsonify({
            'success': True,
            'statuses': [
                {'value': 'watched', 'label': 'Watched'},
                {'value': 'watching', 'label': 'Watching'},
                {'value': 'planned', 'label': 'Planned'},
                {'value': 'on_hold', 'label': 'On Hold'}
            ]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/export', methods=['GET'])
def export_data():
    try:
        export_dir = PROJECT_ROOT / 'exports'
        export_dir.mkdir(exist_ok=True)
        
        files = export_to_csv(catalog, str(export_dir))
        
        return jsonify({
            'success': True,
            'files': files,
            'message': 'Export completed successfully'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/import', methods=['POST'])
def import_data():
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        if not file.filename.endswith('.csv'):
            return jsonify({'success': False, 'error': 'Only CSV files are supported'}), 400
        
        import pandas as pd
        df = pd.read_csv(file)
        
        added_count = 0
        for _, row in df.iterrows():
            try:
                genres = row.get('genres', '').split(';') if row.get('genres') else []
                authors = row.get('authors', '').split(';') if row.get('authors') else []
                
                release_date_str = row.get('release_date')
                if release_date_str and isinstance(release_date_str, str):
                    try:
                        release_date = date.fromisoformat(release_date_str[:10])
                    except ValueError:
                        release_date = date.today()
                else:
                    release_date = date.today()
                
                status_str = row.get('status', 'planned')
                status = status_from_string(status_str)
                
                rating = float(row.get('rating', 0))
                duration = int(row.get('duration', 0))
                video_path = row.get('video_path', '')
                
                if video_path and duration == 0:
                    try:
                        filename = video_path.split('/')[-1]
                        filepath = UPLOAD_FOLDER / filename
                        if filepath.exists():
                            info = extract_video_info(filepath)
                            if info['duration'] > 0:
                                duration = info['duration'] // 60
                    except Exception:
                        pass
                
                item = MediaItem(
                    title=row.get('title', 'Untitled'),
                    release_date=release_date,
                    rating=rating,
                    status=status,
                    genres=genres,
                    description=row.get('description', ''),
                    authors=authors,
                    video_path=video_path,
                    duration=duration
                )
                
                catalog.add_item(item)
                db.add_item(item)
                added_count += 1
                
            except DuplicateError:
                continue
            except Exception:
                pass
        
        return jsonify({
            'success': True,
            'added': added_count,
            'message': f'Imported {added_count} items successfully'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/backup', methods=['POST'])
def create_backup():
    try:
        backup_dir = PROJECT_ROOT / 'backups'
        backup_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = backup_dir / f'media_tracker_backup_{timestamp}.db'
        
        shutil.copy2(db._db_path, backup_path)
        
        return jsonify({
            'success': True,
            'backup_path': str(backup_path),
            'message': 'Backup created successfully'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/reminders', methods=['GET'])
def get_reminders():
    try:
        reminders = reminder.get_all_reminders()
        
        result = []
        for title, days in reminders:
            result.append({
                'title': title,
                'days': days,
                'is_past': days < 0
            })
        
        return jsonify({
            'success': True,
            'reminders': result
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/reminders', methods=['POST'])
def add_reminder():
    try:
        data = request.get_json()
        item_id = data.get('item_id')
        reminder_date_str = data.get('reminder_date')
        
        if not item_id or not reminder_date_str:
            return jsonify({'success': False, 'error': 'Item ID and reminder date required'}), 400
        
        reminder_date = date.fromisoformat(reminder_date_str)
        reminder.add_reminder(item_id, reminder_date)
        
        return jsonify({
            'success': True,
            'message': 'Reminder added successfully'
        })
        
    except NotFoundError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/upload', methods=['POST'])
def upload_video():
    try:
        if 'video' not in request.files:
            return jsonify({'success': False, 'error': 'No video file provided'}), 400
        
        file = request.files['video']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'File type not allowed'}), 400
        
        filename = secure_filename(file.filename)
        filepath = UPLOAD_FOLDER / filename
        
        counter = 1
        original_name = filename
        while filepath.exists():
            name, ext = os.path.splitext(original_name)
            new_name = f"{name}_{counter}{ext}"
            filepath = UPLOAD_FOLDER / new_name
            counter += 1
        
        file.save(str(filepath))
        
        video_info = extract_video_info(filepath)
        duration_seconds = video_info.get('duration', 0)
        duration_minutes = int(duration_seconds / 60) if duration_seconds > 0 else 0
        
        return jsonify({
            'success': True,
            'filepath': str(filepath),
            'filename': filepath.name,
            'duration': duration_seconds,
            'duration_minutes': duration_minutes,
            'width': video_info.get('width', 0),
            'height': video_info.get('height', 0),
            'codec': video_info.get('codec', 'unknown'),
            'size': video_info.get('size', 0),
            'message': f'File "{filepath.name}" uploaded successfully'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/thumbnail/<path:filename>')
def serve_thumbnail(filename):
    try:
        filepath = THUMBNAIL_FOLDER / filename
        if not filepath.exists():
            return jsonify({'success': False, 'error': 'Thumbnail not found'}), 404
        
        return send_file(str(filepath), mimetype='image/jpeg')
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/video/<path:filename>')
def serve_video(filename):
    try:
        filepath = UPLOAD_FOLDER / filename
        
        if not filepath.exists():
            return jsonify({'success': False, 'error': 'Video not found'}), 404
        
        ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        mimetypes = {
            'mp4': 'video/mp4',
            'webm': 'video/webm',
            'avi': 'video/x-msvideo',
            'mkv': 'video/x-matroska',
            'mov': 'video/quicktime',
            'm4v': 'video/mp4',
            'mpg': 'video/mpeg',
            'mpeg': 'video/mpeg'
        }
        mimetype = mimetypes.get(ext, 'video/mp4')
        
        response = send_file(
            str(filepath), 
            mimetype=mimetype,
            as_attachment=False,
            download_name=filename
        )
        
        response.headers['Accept-Ranges'] = 'bytes'
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        return response
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analytics/stats', methods=['GET'])
def get_analytics_stats():
    try:
        items = list(catalog)
        
        total_items = len(items)
        avg_rating = sum(i.rating for i in items) / total_items if total_items > 0 else 0
        total_duration = sum(i.duration for i in items)
        
        all_genres = set()
        for item in items:
            all_genres.update(item.genres)
        unique_genres = len(all_genres)
        
        status_counts = {}
        status_labels = {
            'watched': 'Watched',
            'watching': 'Watching',
            'planned': 'Planned',
            'on_hold': 'On Hold'
        }
        status_data = []
        for status in ['watched', 'watching', 'planned', 'on_hold']:
            count = sum(1 for i in items if i.status.value == status)
            status_counts[status] = count
            status_data.append({
                'value': status,
                'label': status_labels.get(status, status),
                'count': count
            })
        
        genre_counts = {}
        for item in items:
            for genre in item.genres:
                genre_counts[genre] = genre_counts.get(genre, 0) + 1
        genre_data = [
            {'label': g, 'count': c} 
            for g, c in sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)
        ]
        
        year_counts = {}
        for item in items:
            if item.release_date:
                year = item.release_date.year
                year_counts[year] = year_counts.get(year, 0) + 1
        year_data = [
            {'label': str(y), 'count': c} 
            for y, c in sorted(year_counts.items())
        ]
        
        rating_buckets = {i: 0 for i in range(0, 11)}
        for item in items:
            rating = int(item.rating)
            rating_buckets[rating] = rating_buckets.get(rating, 0) + 1
        rating_data = [
            {'label': str(r), 'count': c} 
            for r, c in rating_buckets.items() if c > 0
        ]
        
        top_rated = sorted(items, key=lambda x: x.rating, reverse=True)[:10]
        top_rated_data = [
            {
                'id': db.get_item_id_by_title(item.title) or id(item),
                'title': item.title,
                'rating': item.rating,
                'status': item.status.value
            }
            for item in top_rated
        ]
        
        return jsonify({
            'success': True,
            'stats': {
                'total_items': total_items,
                'avg_rating': round(avg_rating, 2),
                'total_duration': total_duration,
                'unique_genres': unique_genres,
                'status_counts': status_counts,
                'genre_counts': genre_counts,
                'year_counts': year_counts
            },
            'status_data': status_data,
            'genre_data': genre_data,
            'year_data': year_data,
            'rating_data': rating_data,
            'top_rated': top_rated_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analytics/favorites', methods=['GET'])
def get_favorites():
    try:
        favorites = json.loads(request.headers.get('X-Favorites', '[]'))
        return jsonify({'success': True, 'favorites': favorites})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analytics/export', methods=['GET'])
def export_analytics_report():
    try:
        from datetime import datetime
        
        items = list(catalog)
        report_data = {
            'generated': datetime.now().isoformat(),
            'total_items': len(items),
            'items': [item_to_dict(item) for item in items]
        }
        
        report_dir = PROJECT_ROOT / 'reports'
        report_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = report_dir / f'analytics_report_{timestamp}.json'
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False, default=str)
        
        return jsonify({
            'success': True,
            'url': f'/api/analytics/download/{filepath.name}',
            'path': str(filepath)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analytics/download/<filename>', methods=['GET'])
def download_analytics_report(filename):
    try:
        filepath = PROJECT_ROOT / 'reports' / filename
        if not filepath.exists():
            return jsonify({'success': False, 'error': 'File not found'}), 404
        
        return send_file(
            str(filepath),
            as_attachment=True,
            download_name=filename,
            mimetype='application/json'
        )
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analytics/generate', methods=['POST'])
def generate_analytics_report():
    try:
        from src.analytics.integration import AnalyticsIntegration
        
        analytics = AnalyticsIntegration(db._db_path)
        if not analytics.initialize():
            return jsonify({'success': False, 'error': 'Analytics initialization failed'}), 500
        
        stats = analytics.generate_full_report()
        
        return jsonify({
            'success': True,
            'path': 'reports/statistics.txt',
            'stats': stats
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/reports/list', methods=['GET'])
def list_reports():
    try:
        reports_dir = PROJECT_ROOT / 'reports'
        if not reports_dir.exists():
            return jsonify({'success': True, 'reports': []})
        
        reports = []
        for file in reports_dir.iterdir():
            if file.is_file():
                reports.append({
                    'name': file.name,
                    'size': file.stat().st_size,
                    'modified': file.stat().st_mtime
                })
        
        reports.sort(key=lambda x: x['modified'], reverse=True)
        return jsonify({'success': True, 'reports': reports})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/reports/view/<filename>', methods=['GET'])
def view_report(filename):
    try:
        filepath = PROJECT_ROOT / 'reports' / filename
        if not filepath.exists():
            return jsonify({'success': False, 'error': 'File not found'}), 404
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return jsonify({'success': True, 'content': content})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/reports/download/<filename>', methods=['GET'])
def download_report(filename):
    try:
        filepath = PROJECT_ROOT / 'reports' / filename
        if not filepath.exists():
            return jsonify({'success': False, 'error': 'File not found'}), 404
        
        return send_file(
            str(filepath),
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/reports/delete/<filename>', methods=['DELETE'])
def delete_report(filename):
    try:
        filepath = PROJECT_ROOT / 'reports' / filename
        if not filepath.exists():
            return jsonify({'success': False, 'error': 'File not found'}), 404
        
        filepath.unlink()
        return jsonify({'success': True, 'message': 'Report deleted'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/reports/delete-all', methods=['DELETE'])
def delete_all_reports():
    try:
        reports_dir = PROJECT_ROOT / 'reports'
        if not reports_dir.exists():
            return jsonify({'success': True, 'message': 'No reports to delete'})
        
        deleted = 0
        for file in reports_dir.iterdir():
            if file.is_file():
                file.unlink()
                deleted += 1
        
        return jsonify({'success': True, 'deleted': deleted})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/charts/list', methods=['GET'])
def list_charts():
    try:
        figures_dir = PROJECT_ROOT / 'reports' / 'figures'
        if not figures_dir.exists():
            return jsonify({'success': True, 'charts': []})
        
        charts = []
        for file in figures_dir.iterdir():
            if file.is_file() and file.suffix.lower() in ['.png', '.jpg', '.jpeg', '.svg']:
                charts.append({
                    'name': file.name,
                    'size': file.stat().st_size,
                    'modified': file.stat().st_mtime
                })
        
        charts.sort(key=lambda x: x['modified'], reverse=True)
        print(f"Found {len(charts)} charts in {figures_dir}")
        return jsonify({'success': True, 'charts': charts})
        
    except Exception as e:
        print(f"Error listing charts: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/charts/view/<filename>', methods=['GET'])
def view_chart(filename):
    try:
        filepath = PROJECT_ROOT / 'reports' / 'figures' / filename
        if not filepath.exists():
            return jsonify({'success': False, 'error': 'File not found: ' + filename}), 404
        
        return send_file(str(filepath), mimetype='image/png')
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/charts/delete/<filename>', methods=['DELETE'])
def delete_chart(filename):
    try:
        filepath = PROJECT_ROOT / 'reports' / 'figures' / filename
        if not filepath.exists():
            return jsonify({'success': False, 'error': 'File not found'}), 404
        
        filepath.unlink()
        return jsonify({'success': True, 'message': 'Chart deleted'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/charts/delete-all', methods=['DELETE'])
def delete_all_charts():
    try:
        figures_dir = PROJECT_ROOT / 'reports' / 'figures'
        if not figures_dir.exists():
            return jsonify({'success': True, 'message': 'No charts to delete'})
        
        deleted = 0
        for file in figures_dir.iterdir():
            if file.is_file():
                file.unlink()
                deleted += 1
        
        return jsonify({'success': True, 'deleted': deleted})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/charts/download/<filename>', methods=['GET'])
def download_chart(filename):
    try:
        filepath = PROJECT_ROOT / 'reports' / 'figures' / filename
        if not filepath.exists():
            return jsonify({'success': False, 'error': 'File not found'}), 404
        
        return send_file(
            str(filepath),
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    print("=" * 60)
    print("MediaTracker Server")
    print("=" * 60)
    print(f"Upload folder: {UPLOAD_FOLDER.absolute()}")
    print(f"Thumbnail folder: {THUMBNAIL_FOLDER.absolute()}")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5000)