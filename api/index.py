from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, HttpUrl
import yt_dlp
import os
import uuid
import asyncio
from typing import Optional, Dict, Any
import tempfile
import io
from urllib.parse import urlparse
import json
import time

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

class VideoInfo(BaseModel):
    title: str
    duration: Optional[int]
    thumbnail: Optional[str]
    uploader: Optional[str]
    view_count: Optional[int]
    description: Optional[str]
    formats: list
    download_url: Optional[str] = None

class DownloadResponse(BaseModel):
    status: str
    message: str
    video_info: Optional[VideoInfo] = None
    download_url: Optional[str] = None

def get_video_info(url: str) -> Dict[str, Any]:
    """Extract video information without downloading"""
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
        
        # Get direct download URL for immediate download
        download_url = get_best_format_url(info, request.quality, request.audio_only)
        
        return VideoInfo(
            title=info.get("title", "Unknown"),
            duration=info.get("duration"),
            thumbnail=info.get("thumbnail"),
            uploader=info.get("uploader") or info.get("channel", "Unknown"),
            view_count=info.get("view_count"),
            description=info.get("description", "")[:500] + "..." if info.get("description", "") else "",
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
        
        # Get direct download URL
        download_url = get_best_format_url(info, request.quality, request.audio_only)
        
        if not download_url:
            raise HTTPException(status_code=400, detail="Could not extract download URL")
        
        video_info = VideoInfo(
            title=info.get("title", "Unknown"),
            duration=info.get("duration"),
            thumbnail=info.get("thumbnail"),
            uploader=info.get("uploader") or info.get("channel", "Unknown"),
            view_count=info.get("view_count"),
            description=info.get("description", "")[:200] + "..." if info.get("description", "") else "",
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