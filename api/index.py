from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, HttpUrl
import yt_dlp
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
        'writeinfojson': False,
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
        # Try to use cookies if available (for YouTube)
        'cookiefile': None,
        # Skip unavailable fragments
        'ignoreerrors': False,
        'no_check_certificate': True,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            return info
        except yt_dlp.utils.ExtractorError as e:
            error_msg = str(e)
            if "Sign in to confirm you're not a bot" in error_msg:
                # Try alternative extraction method for YouTube
                return try_alternative_youtube_extraction(url, ydl_opts)
            elif "format code" in error_msg:
                # Handle format string errors
                raise HTTPException(status_code=400, detail="Video format extraction error. Please try a different URL.")
            else:
                raise HTTPException(status_code=400, detail=f"Failed to extract video info: {error_msg}")
        except Exception as e:
            error_msg = str(e)
            if "format code" in error_msg and "float" in error_msg:
                # Handle the specific float format error
                raise HTTPException(status_code=400, detail="Video metadata format error. This video may have incomplete information.")
            raise HTTPException(status_code=400, detail=f"Failed to extract video info: {error_msg}")

def try_alternative_youtube_extraction(url: str, base_opts: Dict) -> Dict[str, Any]:
    """Try alternative extraction methods for YouTube when bot detection occurs"""
    alternative_opts = base_opts.copy()
    
    # Try with different extractor options
    alternative_opts.update({
        'extractor_args': {
            'youtube': {
                'skip': ['dash'],
                'player_client': ['web', 'android'],
            }
        },
        'format': 'best[height<=720]',  # Lower quality to avoid restrictions
    })
    
    with yt_dlp.YoutubeDL(alternative_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            return info
        except:
            # If all else fails, return basic info with error
            parsed_url = urlparse(url)
            video_id = parsed_url.query.split('v=')[1].split('&')[0] if 'v=' in parsed_url.query else 'unknown'
            return {
                'title': f'YouTube Video {video_id}',
                'id': video_id,
                'webpage_url': url,
                'extractor': 'youtube',
                'duration': None,
                'thumbnail': f'https://img.youtube.com/vi/{video_id}/maxresdefault.jpg',
                'description': 'Video information limited due to access restrictions. Download may still work.',
                'formats': [],
                '_error': 'Limited access - some features may not work'
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

def extract_media_items(info: Dict[str, Any], quality: str, audio_only: bool) -> List[MediaItem]:
    """Extract all available media items (videos, images, audio)"""
    media_items = []
    title = info.get('title', 'Unknown')
    formats = info.get('formats', [])
    
    # Handle case where no formats are available but direct URL exists
    if not formats and info.get('url'):
        # Direct URL case (common with TikTok and some other platforms)
        ext = 'mp4' if not audio_only else 'mp3'
        filename = generate_filename(title, ext, quality)
        
        media_items.append(MediaItem(
            type="audio" if audio_only else "video",
            url=info['url'],
            title=title,
            filename=filename,
            format=ext,
            quality="unknown",
            size=info.get('filesize')
        ))
        return media_items
    
    if audio_only:
        # Find audio formats
        audio_formats = [f for f in formats if f.get('acodec') != 'none' and f.get('vcodec') == 'none']
        if not audio_formats:
            # If no pure audio, try video formats for audio extraction
            audio_formats = [f for f in formats if f.get('acodec') != 'none']
        
        if audio_formats:
            best_audio = max(audio_formats, key=lambda x: x.get('abr', 0) or 0)
            if best_audio.get('url'):
                filename = generate_filename(title, 'mp3', quality)
                quality_str = f"{best_audio.get('abr', 'unknown')}kbps" if best_audio.get('abr') else 'unknown'
                
                media_items.append(MediaItem(
                    type="audio",
                    url=best_audio['url'],
                    title=title,
                    filename=filename,
                    format='mp3',
                    quality=quality_str,
                    size=best_audio.get('filesize')
                ))
    else:
        # Video formats
        video_formats = [f for f in formats if f.get('vcodec') != 'none']
        
        # If no video formats, try all formats (some platforms don't mark vcodec properly)
        if not video_formats:
            video_formats = [f for f in formats if f.get('url')]
        
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
                
                # Better quality string handling
                height = best_format.get('height')
                if height:
                    quality_str = f"{height}p"
                elif best_format.get('format_note'):
                    quality_str = best_format['format_note']
                elif best_format.get('format_id'):
                    quality_str = best_format['format_id']
                else:
                    quality_str = 'unknown'
                
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
                
                width = img_format.get('width', 'unknown')
                height = img_format.get('height', 'unknown')
                quality_str = f"{width}x{height}" if width != 'unknown' and height != 'unknown' else 'unknown'
                
                media_items.append(MediaItem(
                    type="image",
                    url=img_format['url'],
                    title=f"{title} - Image {i+1}",
                    filename=filename,
                    format=ext,
                    quality=quality_str,
                    size=img_format.get('filesize')
                ))
    
    return media_items

def get_best_format_url(info: Dict[str, Any], quality: str, audio_only: bool) -> Optional[str]:
    """Get the best format URL based on quality preference"""
    formats = info.get('formats', [])
    
    # If no formats, try direct URL
    if not formats:
        return info.get('url')
    
    if audio_only:
        # Find best audio format
        audio_formats = [f for f in formats if f.get('acodec') != 'none' and f.get('vcodec') == 'none']
        if not audio_formats:
            # Fallback to any format with audio
            audio_formats = [f for f in formats if f.get('acodec') != 'none']
        
        if audio_formats:
            best_audio = max(audio_formats, key=lambda x: x.get('abr', 0) or 0)
            return best_audio.get('url')
    
    # Video formats
    video_formats = [f for f in formats if f.get('vcodec') != 'none']
    
    # If no video formats, try all available formats
    if not video_formats:
        video_formats = [f for f in formats if f.get('url')]
    
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
    
    # Final fallback
    return info.get('url')

@app.get("/")
async def home():
    """Serve the main page"""
    try:
        with open('/var/task/static/index.html', 'r') as f:
            content = f.read()
        return Response(content=content, media_type="text/html")
    except FileNotFoundError:
        # Fallback for local development
        try:
            with open('static/index.html', 'r') as f:
                content = f.read()
            return Response(content=content, media_type="text/html")
        except FileNotFoundError:
            return JSONResponse(
                content={"message": "Welcome to Social Media Video Downloader API", 
                        "docs": "/docs",
                        "platforms": "/api/platforms"}, 
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

# For Vercel deployment
app