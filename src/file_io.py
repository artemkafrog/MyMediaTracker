import pandas as pd
import os
from pathlib import Path
from src.catalog import MediaCatalog
from src.media import MediaItem
from src.enums import MediaType

def export_to_csv(catalog: MediaCatalog, output_dir: str = "exports") -> dict[str, str]:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    exported_files = {}
    
    videos = catalog.get_by_type(MediaType.VIDEO)
    if videos:
        filepath = os.path.join(output_dir, "videos.csv")
        _export_videos(videos, filepath)
        exported_files["videos"] = filepath
    
    return exported_files

def _export_videos(videos: list[MediaItem], filepath: str) -> None:
    data = []
    for video in videos:
        data.append({
            'title': video.title,
            'release_date': video.release_date,
            'rating': video.rating,
            'status': video.status.value,
            'genres': ';'.join(video.genres),
            'duration': video.duration,
            'authors': ';'.join(video.authors),
            'description': video.description,
            'video_path': video.video_path,
            'media_type': video.get_media_type().value
        })
    
    df = pd.DataFrame(data)
    df.to_csv(filepath, index=False, encoding='utf-8')