from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel, HttpUrl
import yt_dlp
import os
import uuid
import asyncio
from typing import Optional, Dict, Any, List
import tempfile
import shutil
from urllib.parse import urlparse
import re

app = FastAPI(
    title="Social Media Video Downloader API",
    description="Download videos from various social media platforms",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create downloads directory if it doesn't exist
DOWNLOADS_DIR = "/workspace/downloads"
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

# Mount static files for serving downloaded videos
app.mount("/downloads", StaticFiles(directory=DOWNLOADS_DIR), name="downloads")
app.mount("/static", StaticFiles(directory="/workspace/static"), name="static")

class VideoDownloadRequest(BaseModel):
    url: HttpUrl
    quality: Optional[str] = "best"
    audio_only: Optional[bool] = False

class MediaItem(BaseModel):
    type: str  # "video", "audio", "image"
    url: str
    title: str
    filename: str
    format: str
    quality: Optional[str] = None
    size: Optional[int] = None

class VideoInfo(BaseModel):
    title: str
    duration: Optional[int]
    duration_string: Optional[str]
    thumbnail: Optional[str]
    thumbnails: Optional[List[str]] = []
    uploader: Optional[str]
    upload_date: Optional[str]
    view_count: Optional[int]
    like_count: Optional[int]
    description: Optional[str]
    website: Optional[str]
    original_url: str
    media_type: str  # "video", "playlist", "images", "mixed"
    media_items: List[MediaItem] = []
    formats: list

class DownloadResponse(BaseModel):
    status: str
    download_id: str
    message: str
    file_path: Optional[str] = None
    video_info: Optional[VideoInfo] = None

# Store download status
download_status: Dict[str, Dict[str, Any]] = {}

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file system usage"""
    # Remove or replace invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove extra whitespace and dots
    filename = re.sub(r'\s+', ' ', filename).strip()
    filename = filename.replace('..', '_')
    # Limit length
    if len(filename) > 200:
        filename = filename[:200]
    return filename

def format_duration(seconds: Optional[int]) -> Optional[str]:
    """Format duration in seconds to human readable format"""
    if not seconds:
        return None
    
    try:
        # Convert to int if it's a float
        if isinstance(seconds, float):
            seconds = int(seconds)
        elif isinstance(seconds, str):
            seconds = int(float(seconds))
        
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"
    except (ValueError, TypeError):
        return "Unknown"

def extract_thumbnails(info: Dict[str, Any]) -> List[str]:
    """Extract all available thumbnails"""
    thumbnails = []
    
    # Main thumbnail
    if info.get('thumbnail'):
        thumbnails.append(info['thumbnail'])
    
    # All thumbnails from info
    if info.get('thumbnails'):
        for thumb in info['thumbnails']:
            if isinstance(thumb, dict) and thumb.get('url'):
                if thumb['url'] not in thumbnails:
                    thumbnails.append(thumb['url'])
            elif isinstance(thumb, str) and thumb not in thumbnails:
                thumbnails.append(thumb)
    
    return thumbnails

def get_media_type(info: Dict[str, Any]) -> str:
    """Determine the type of media"""
    if info.get('_type') == 'playlist':
        return 'playlist'
    
    formats = info.get('formats', [])
    has_video = any(f.get('vcodec') != 'none' for f in formats if f.get('vcodec'))
    has_audio = any(f.get('acodec') != 'none' for f in formats if f.get('acodec'))
    has_images = any('image' in f.get('format', '').lower() for f in formats)
    
    if has_images and not has_video:
        return 'images'
    elif has_video or has_audio:
        return 'video'
    else:
        return 'unknown'

def generate_filename(title: str, ext: str, quality: str = None) -> str:
    """Generate a safe filename from title"""
    safe_title = sanitize_filename(title or 'download')
    
    # Add quality suffix if specified
    if quality and quality not in ['best', 'worst']:
        safe_title += f"_{quality}"
    
    return f"{safe_title}.{ext}"

def get_video_info(url: str) -> Dict[str, Any]:
    """Extract video information without downloading"""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        # YouTube anti-bot measures
        'extractor_args': {
            'youtube': {
                'skip': ['hls', 'dash'],
                'player_skip': ['configs', 'webpage']
            }
        },
        # Additional headers to avoid bot detection
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        },
        # Retry and timeout settings
        'retries': 3,
        'fragment_retries': 3,
        'socket_timeout': 30,
        'no_check_certificate': True,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            return info
        except yt_dlp.utils.ExtractorError as e:
            error_msg = str(e)
            if "Sign in to confirm you're not a bot" in error_msg:
                # Try alternative extraction for YouTube
                return try_alternative_extraction(url, ydl_opts)
            else:
                raise HTTPException(status_code=400, detail=f"Failed to extract video info: {error_msg}")
        except Exception as e:
            error_msg = str(e)
            if "format code" in error_msg and "float" in error_msg:
                raise HTTPException(status_code=400, detail="Video metadata format error. This video may have incomplete information.")
            raise HTTPException(status_code=400, detail=f"Failed to extract video info: {error_msg}")

def try_alternative_extraction(url: str, base_opts: Dict) -> Dict[str, Any]:
    """Try alternative extraction methods when bot detection occurs"""
    alternative_opts = base_opts.copy()
    alternative_opts.update({
        'extractor_args': {
            'youtube': {
                'skip': ['dash'],
                'player_client': ['web', 'android'],
            }
        },
        'format': 'best[height<=720]',
    })
    
    with yt_dlp.YoutubeDL(alternative_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            return info
        except:
            # Return basic info if all else fails
            from urllib.parse import urlparse, parse_qs
            parsed_url = urlparse(url)
            
            if 'youtube.com' in parsed_url.netloc or 'youtu.be' in parsed_url.netloc:
                video_id = 'unknown'
                if 'v=' in parsed_url.query:
                    video_id = parse_qs(parsed_url.query)['v'][0]
                elif 'youtu.be' in parsed_url.netloc:
                    video_id = parsed_url.path.lstrip('/')
                
                return {
                    'title': f'YouTube Video {video_id}',
                    'id': video_id,
                    'webpage_url': url,
                    'extractor': 'youtube',
                    'duration': None,
                    'thumbnail': f'https://img.youtube.com/vi/{video_id}/maxresdefault.jpg',
                    'description': 'Video information limited due to access restrictions.',
                    'formats': [],
                    '_error': 'Limited access'
                }
            else:
                return {
                    'title': 'Video',
                    'webpage_url': url,
                    'description': 'Video information could not be extracted.',
                    'formats': [],
                    '_error': 'Extraction failed'
                }

def is_supported_platform(url: str) -> bool:
    """Check if the URL is from a supported platform"""
    supported_domains = [
        'youtube.com', 'youtu.be', 'tiktok.com', 'instagram.com', 
        'twitter.com', 'x.com', 'facebook.com', 'twitch.tv',
        'vimeo.com', 'dailymotion.com', 'reddit.com'
    ]
    
    parsed_url = urlparse(str(url))
    domain = parsed_url.netloc.lower()
    
    return any(supported_domain in domain for supported_domain in supported_domains)

async def download_video_task(download_id: str, url: str, quality: str, audio_only: bool):
    """Background task to download video"""
    try:
        download_status[download_id]["status"] = "downloading"
        
        # First get video info to determine filename
        info = get_video_info(url)
        title = info.get('title', 'download')
        safe_filename = sanitize_filename(title)
        
        # Set up download options with proper filename
        ydl_opts = {
            'outtmpl': os.path.join(DOWNLOADS_DIR, f'{safe_filename}.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
        }
        
        if audio_only:
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        else:
            if quality == "worst":
                ydl_opts['format'] = 'worst'
            elif quality == "best":
                ydl_opts['format'] = 'best'
            else:
                ydl_opts['format'] = f'best[height<={quality}]'
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            # Find the downloaded file
            downloaded_files = [f for f in os.listdir(DOWNLOADS_DIR) if f.startswith(download_id)]
            if downloaded_files:
                file_path = os.path.join(DOWNLOADS_DIR, downloaded_files[0])
                download_status[download_id].update({
                    "status": "completed",
                    "file_path": f"/downloads/{downloaded_files[0]}",
                    "title": info.get("title", "Unknown"),
                    "duration": info.get("duration"),
                    "file_size": os.path.getsize(file_path)
                })
            else:
                download_status[download_id]["status"] = "failed"
                download_status[download_id]["error"] = "Downloaded file not found"
                
    except Exception as e:
        download_status[download_id]["status"] = "failed"
        download_status[download_id]["error"] = str(e)

@app.get("/", response_class=HTMLResponse)
async def home():
    """Serve the main page"""
    return FileResponse("/workspace/static/index.html")

@app.post("/api/video/info", response_model=VideoInfo)
async def get_video_information(request: VideoDownloadRequest):
    """Get video information without downloading"""
    url = str(request.url)
    
    if not is_supported_platform(url):
        raise HTTPException(status_code=400, detail="Unsupported platform")
    
    try:
        info = get_video_info(url)
        
        # Get thumbnails
        thumbnails = extract_thumbnails(info)
        
        # Get media type
        media_type = get_media_type(info)
        
        # Format upload date
        upload_date = info.get("upload_date")
        if upload_date:
            try:
                # Convert YYYYMMDD to YYYY-MM-DD
                upload_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
            except:
                pass
        
        return VideoInfo(
            title=info.get("title", "Unknown"),
            duration=info.get("duration"),
            duration_string=format_duration(info.get("duration")),
            thumbnail=thumbnails[0] if thumbnails else None,
            thumbnails=thumbnails,
            uploader=info.get("uploader") or info.get("channel") or info.get("creator", "Unknown"),
            upload_date=upload_date,
            view_count=info.get("view_count"),
            like_count=info.get("like_count"),
            description=info.get("description", "")[:500] + "..." if info.get("description", "") else "",
            website=info.get("extractor_key", "Unknown"),
            original_url=url,
            media_type=media_type,
            media_items=[],
            formats=[{
                "format_id": f.get("format_id"),
                "ext": f.get("ext"),
                "quality": f.get("quality"),
                "height": f.get("height"),
                "width": f.get("width"),
                "filesize": f.get("filesize")
            } for f in info.get("formats", [])[:10]]  # Limit to first 10 formats
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to get video info: {str(e)}")

@app.post("/api/video/download", response_model=DownloadResponse)
async def download_video(request: VideoDownloadRequest, background_tasks: BackgroundTasks):
    """Start video download"""
    url = str(request.url)
    
    if not is_supported_platform(url):
        raise HTTPException(status_code=400, detail="Unsupported platform")
    
    # Generate unique download ID
    download_id = str(uuid.uuid4())
    
    # Initialize download status
    download_status[download_id] = {
        "status": "queued",
        "url": url,
        "quality": request.quality,
        "audio_only": request.audio_only
    }
    
    # Start background download task
    background_tasks.add_task(
        download_video_task, 
        download_id, 
        url, 
        request.quality, 
        request.audio_only
    )
    
    return DownloadResponse(
        status="queued",
        download_id=download_id,
        message="Download started successfully"
    )

@app.get("/api/video/status/{download_id}")
async def get_download_status(download_id: str):
    """Get download status"""
    if download_id not in download_status:
        raise HTTPException(status_code=404, detail="Download not found")
    
    return download_status[download_id]

@app.get("/api/platforms")
async def get_supported_platforms():
    """Get list of supported platforms"""
    return {
        "platforms": [
            {"name": "YouTube", "domain": "youtube.com", "supports_audio": True},
            {"name": "TikTok", "domain": "tiktok.com", "supports_audio": True},
            {"name": "Instagram", "domain": "instagram.com", "supports_audio": True},
            {"name": "Twitter/X", "domain": "twitter.com", "supports_audio": True},
            {"name": "Facebook", "domain": "facebook.com", "supports_audio": True},
            {"name": "Twitch", "domain": "twitch.tv", "supports_audio": True},
            {"name": "Vimeo", "domain": "vimeo.com", "supports_audio": True},
            {"name": "Dailymotion", "domain": "dailymotion.com", "supports_audio": True},
            {"name": "Reddit", "domain": "reddit.com", "supports_audio": True},
        ]
    }

@app.delete("/api/video/{download_id}")
async def delete_downloaded_file(download_id: str):
    """Delete a downloaded file"""
    if download_id not in download_status:
        raise HTTPException(status_code=404, detail="Download not found")
    
    status = download_status[download_id]
    if status["status"] == "completed" and "file_path" in status:
        file_path = status["file_path"].replace("/downloads/", "")
        full_path = os.path.join(DOWNLOADS_DIR, file_path)
        
        if os.path.exists(full_path):
            os.remove(full_path)
            del download_status[download_id]
            return {"message": "File deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="File not found")
    else:
        raise HTTPException(status_code=400, detail="No file to delete")

# For Vercel deployment
handler = app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)