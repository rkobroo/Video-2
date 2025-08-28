from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel, HttpUrl
import yt_dlp
import os
import uuid
import asyncio
from typing import Optional, Dict, Any
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

class VideoInfo(BaseModel):
    title: str
    duration: Optional[int]
    thumbnail: Optional[str]
    uploader: Optional[str]
    view_count: Optional[int]
    description: Optional[str]
    formats: list

class DownloadResponse(BaseModel):
    status: str
    download_id: str
    message: str
    file_path: Optional[str] = None

# Store download status
download_status: Dict[str, Dict[str, Any]] = {}

def get_video_info(url: str) -> Dict[str, Any]:
    """Extract video information without downloading"""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
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

async def download_video_task(download_id: str, url: str, quality: str, audio_only: bool):
    """Background task to download video"""
    try:
        download_status[download_id]["status"] = "downloading"
        
        # Set up download options
        ydl_opts = {
            'outtmpl': os.path.join(DOWNLOADS_DIR, f'{download_id}_%(title)s.%(ext)s'),
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