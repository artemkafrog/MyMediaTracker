"""
Flask web server for MediaTracker
"""

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

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.catalog import MediaCatalog
from src.database import DatabaseManager
from src.media import MediaItem
from src.enums import Status, MediaType
from src.exceptions import NotFoundError, DuplicateError, ValidationError
from src.file_io import export_to_csv
from src.reminder import Reminder

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
                # Добавляем в каталог с ID из БД
                db_id = db.get_item_id_by_title(item.title)
                if db_id:
                    # Сохраняем ID в объекте
                    item._db_id = db_id
                catalog.add_item(item)
            except DuplicateError:
                pass
        print(f"Loaded {len(items)} items from database")
    except Exception as e:
        print(f"Error loading catalog: {e}")

load_catalog()

BASE_DIR = Path(__file__).parent.parent
UPLOAD_FOLDER = BASE_DIR / 'uploads'
THUMBNAIL_FOLDER = BASE_DIR / 'thumbnails'
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
    # Получаем ID из базы данных по названию
    db_id = db.get_item_id_by_title(item.title)
    if db_id:
        item_id = db_id
    elif hasattr(item, '_db_id') and item._db_id:
        item_id = item._db_id
    else:
        # Если ID нет, генерируем временный
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
        
        # Добавляем в БД сначала, чтобы получить ID
        db_id = db.add_item(item)
        if db_id:
            item._db_id = db_id
        
        # Затем добавляем в каталог
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
        
        # Ищем item по ID из БД
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
        # Ищем item по ID из БД
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
        
        # Удаляем из каталога
        catalog.remove_item(cat_id)
        
        # Удаляем из БД
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
        export_dir = Path('exports')
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
        backup_dir = Path('backups')
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

if __name__ == '__main__':
    print("=" * 60)
    print("MediaTracker Server")
    print("=" * 60)
    print(f"Upload folder: {UPLOAD_FOLDER.absolute()}")
    print(f"Thumbnail folder: {THUMBNAIL_FOLDER.absolute()}")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5000)