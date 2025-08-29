from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, HttpUrl, Field
import os
import uuid
import asyncio
from typing import Optional, Dict, Any, List
import tempfile
import io
from urllib.parse import urlparse
import json
import time
import re
from pathlib import Path
import sys

app = FastAPI(
    title="Social Media Video Downloader API",
    description="Download videos from various social media platforms (Vercel Edition)",
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
    thumbnails: List[str] = Field(default_factory=list)
    uploader: Optional[str]
    upload_date: Optional[str]
    view_count: Optional[int]
    like_count: Optional[int]
    description: Optional[str]
    website: Optional[str]
    original_url: str
    media_type: str  # "video", "playlist", "images", "mixed"
    media_items: List[MediaItem] = Field(default_factory=list)
    formats: List[dict] = Field(default_factory=list)
    download_url: Optional[str] = None

class DownloadResponse(BaseModel):
    status: str
    message: str
    video_info: Optional[VideoInfo] = None
    download_url: Optional[str] = None

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
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"

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
    # Lazy import to avoid cold-start failures if yt_dlp fails to import
    try:
        import yt_dlp  # type: ignore
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Dependency error: yt-dlp failed to import: {exc}")

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'writeinfojson': False,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            return info
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to extract video info: {str(e)}")

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

def extract_media_items(info: Dict[str, Any], quality: str, audio_only: bool) -> List[MediaItem]:
    """Extract all available media items (videos, images, audio)"""
    media_items = []
    title = info.get('title', 'Unknown')
    formats = info.get('formats', [])
    
    if audio_only:
        # Find audio formats
        audio_formats = [f for f in formats if f.get('acodec') != 'none' and f.get('vcodec') == 'none']
        if audio_formats:
            best_audio = max(audio_formats, key=lambda x: x.get('abr', 0) or 0)
            if best_audio.get('url'):
                filename = generate_filename(title, 'mp3', quality)
                media_items.append(MediaItem(
                    type="audio",
                    url=best_audio['url'],
                    title=title,
                    filename=filename,
                    format='mp3',
                    quality=f"{best_audio.get('abr', 'unknown')}kbps",
                    size=best_audio.get('filesize')
                ))
    else:
        # Video formats
        video_formats = [f for f in formats if f.get('vcodec') != 'none']
        
        # Find best video format based on quality
        if quality == "worst":
            suitable_formats = sorted(video_formats, key=lambda x: x.get('height', 0) or 0)
        elif quality == "best":
            suitable_formats = sorted(video_formats, key=lambda x: x.get('height', 0) or 0, reverse=True)
        else:
            try:
                max_height = int(quality)
                suitable_formats = [f for f in video_formats if (f.get('height') or 0) <= max_height]
                suitable_formats = sorted(suitable_formats, key=lambda x: x.get('height', 0) or 0, reverse=True)
            except ValueError:
                suitable_formats = video_formats
        
        if suitable_formats:
            best_format = suitable_formats[0]
            if best_format.get('url'):
                ext = best_format.get('ext', 'mp4')
                filename = generate_filename(title, ext, quality)
                quality_str = f"{best_format.get('height', 'unknown')}p" if best_format.get('height') else 'unknown'
                
                media_items.append(MediaItem(
                    type="video",
                    url=best_format['url'],
                    title=title,
                    filename=filename,
                    format=ext,
                    quality=quality_str,
                    size=best_format.get('filesize')
                ))
        
        # Also include images if available (for Instagram posts, etc.)
        image_formats = [f for f in formats if 'image' in f.get('format', '').lower() or f.get('ext') in ['jpg', 'jpeg', 'png', 'webp']]
        for i, img_format in enumerate(image_formats[:10]):  # Limit to 10 images
            if img_format.get('url'):
                ext = img_format.get('ext', 'jpg')
                filename = generate_filename(f"{title}_image_{i+1}", ext)
                
                media_items.append(MediaItem(
                    type="image",
                    url=img_format['url'],
                    title=f"{title} - Image {i+1}",
                    filename=filename,
                    format=ext,
                    quality=f"{img_format.get('width', 'unknown')}x{img_format.get('height', 'unknown')}",
                    size=img_format.get('filesize')
                ))
    
    return media_items

def get_best_format_url(info: Dict[str, Any], quality: str, audio_only: bool) -> Optional[str]:
    """Get the best format URL based on quality preference"""
    formats = info.get('formats', [])
    
    if not formats:
        return info.get('url')
    
    if audio_only:
        # Find best audio format
        audio_formats = [f for f in formats if f.get('acodec') != 'none' and f.get('vcodec') == 'none']
        if audio_formats:
            best_audio = max(audio_formats, key=lambda x: x.get('abr', 0) or 0)
            return best_audio.get('url')
    
    # Video formats
    video_formats = [f for f in formats if f.get('vcodec') != 'none']
    
    if quality == "worst":
        suitable_formats = sorted(video_formats, key=lambda x: x.get('height', 0) or 0)
    elif quality == "best":
        suitable_formats = sorted(video_formats, key=lambda x: x.get('height', 0) or 0, reverse=True)
    else:
        try:
            max_height = int(quality)
            suitable_formats = [f for f in video_formats if (f.get('height') or 0) <= max_height]
            suitable_formats = sorted(suitable_formats, key=lambda x: x.get('height', 0) or 0, reverse=True)
        except ValueError:
            suitable_formats = video_formats
    
    if suitable_formats:
        return suitable_formats[0].get('url')
    
    return info.get('url')

@app.get("/")
async def home():
    """Serve the main page"""
    candidate_paths = [
        Path('/var/task/static/index.html'),
        Path(__file__).resolve().parent.parent / 'static' / 'index.html',
        Path.cwd() / 'static' / 'index.html'
    ]
    for path in candidate_paths:
        try:
            if path.exists():
                content = path.read_text(encoding='utf-8')
                return Response(content=content, media_type="text/html; charset=utf-8")
        except Exception:
            # Try next path
            continue
    return JSONResponse(
        content={
            "message": "Welcome to Social Media Video Downloader API",
            "docs": "/docs",
            "platforms": "/api/platforms"
        },
        status_code=200
    )

@app.post("/api/video/info", response_model=VideoInfo)
async def get_video_information(request: VideoDownloadRequest):
    """Get video information without downloading"""
    url = str(request.url)
    
    if not is_supported_platform(url):
        raise HTTPException(status_code=400, detail="Unsupported platform")
    
    try:
        info = get_video_info(url)
        
        # Extract all available media items
        media_items = extract_media_items(info, request.quality, request.audio_only)
        
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
        
        # Get direct download URL for backward compatibility
        download_url = get_best_format_url(info, request.quality, request.audio_only)
        
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
            media_items=media_items,
            formats=[{
                "format_id": f.get("format_id"),
                "ext": f.get("ext"),
                "quality": f.get("quality"),
                "height": f.get("height"),
                "width": f.get("width"),
                "filesize": f.get("filesize")
            } for f in info.get("formats", [])[:10]],  # Limit to first 10 formats
            download_url=download_url
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to get video info: {str(e)}")

@app.post("/api/video/download", response_model=DownloadResponse)
async def download_video(request: VideoDownloadRequest):
    """Get video download information and direct URL"""
    url = str(request.url)
    
    if not is_supported_platform(url):
        raise HTTPException(status_code=400, detail="Unsupported platform")
    
    try:
        # Ensure yt_dlp import works before proceeding
        try:
            import yt_dlp  # type: ignore  # noqa: F401
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Dependency error: yt-dlp failed to import: {exc}")
        info = get_video_info(url)
        
        # Extract all available media items
        media_items = extract_media_items(info, request.quality, request.audio_only)
        
        # Get thumbnails
        thumbnails = extract_thumbnails(info)
        
        # Get media type
        media_type = get_media_type(info)
        
        # Format upload date
        upload_date = info.get("upload_date")
        if upload_date:
            try:
                upload_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
            except:
                pass
        
        # Get direct download URL for backward compatibility
        download_url = get_best_format_url(info, request.quality, request.audio_only)
        
        if not download_url and not media_items:
            raise HTTPException(status_code=400, detail="Could not extract download URL")
        
        video_info = VideoInfo(
            title=info.get("title", "Unknown"),
            duration=info.get("duration"),
            duration_string=format_duration(info.get("duration")),
            thumbnail=thumbnails[0] if thumbnails else None,
            thumbnails=thumbnails,
            uploader=info.get("uploader") or info.get("channel") or info.get("creator", "Unknown"),
            upload_date=upload_date,
            view_count=info.get("view_count"),
            like_count=info.get("like_count"),
            description=info.get("description", "")[:200] + "..." if info.get("description", "") else "",
            website=info.get("extractor_key", "Unknown"),
            original_url=url,
            media_type=media_type,
            media_items=media_items,
            formats=[],
            download_url=download_url
        )
        
        return DownloadResponse(
            status="ready",
            message="Download URL ready",
            video_info=video_info,
            download_url=download_url
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process video: {str(e)}")

@app.get("/api/video/proxy/{video_id}")
async def proxy_download(video_id: str, url: str):
    """Proxy video download to avoid CORS issues"""
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(url, follow_redirects=True)
            return StreamingResponse(
                io.BytesIO(response.content),
                media_type=response.headers.get("content-type", "video/mp4"),
                headers={
                    "Content-Disposition": f"attachment; filename={video_id}.mp4"
                }
            )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Download failed: {str(e)}")

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

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "Social Media Video Downloader API is running"}

# For Vercel
handler = app

@app.get("/api/debug")
async def debug_info():
    """Return basic debug info to diagnose runtime issues"""
    data: Dict[str, Any] = {
        "python_version": sys.version,
        "fastapi_version": getattr(FastAPI, "__version__", None),
        "cwd": str(Path.cwd()),
    }
    try:
        try:
            import yt_dlp  # type: ignore
            data["yt_dlp"] = {"imported": True, "version": getattr(yt_dlp, "version", None)}
        except Exception as exc:
            data["yt_dlp"] = {"imported": False, "error": str(exc)}
    except Exception as exc:
        data["error"] = str(exc)
    return data