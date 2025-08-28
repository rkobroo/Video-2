# Social Media Video Downloader API

A powerful web application that allows users to download videos from various social media platforms including YouTube, TikTok, Instagram, Twitter, Facebook, and more.

## Features

- **Multi-platform Support**: Download from YouTube, TikTok, Instagram, Twitter/X, Facebook, Twitch, Vimeo, Dailymotion, and Reddit
- **Quality Selection**: Choose from multiple video quality options (best, 720p, 480p, 360p, worst)
- **Audio-only Downloads**: Extract audio as MP3 files
- **Real-time Status**: Track download progress with live status updates
- **Video Information**: Preview video details before downloading
- **Modern UI**: Beautiful, responsive web interface
- **RESTful API**: Full API endpoints for integration

## Quick Start

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Application**:
   ```bash
   python main.py
   ```

3. **Access the Web Interface**:
   Open your browser and go to `http://localhost:8000`

## API Endpoints

### Get Video Information
```http
POST /api/video/info
Content-Type: application/json

{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "quality": "best",
  "audio_only": false
}
```

### Download Video
```http
POST /api/video/download
Content-Type: application/json

{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "quality": "720",
  "audio_only": false
}
```

### Check Download Status
```http
GET /api/video/status/{download_id}
```

### Get Supported Platforms
```http
GET /api/platforms
```

### Delete Downloaded File
```http
DELETE /api/video/{download_id}
```

## Supported Platforms

- YouTube (youtube.com, youtu.be)
- TikTok (tiktok.com)
- Instagram (instagram.com)
- Twitter/X (twitter.com, x.com)
- Facebook (facebook.com)
- Twitch (twitch.tv)
- Vimeo (vimeo.com)
- Dailymotion (dailymotion.com)
- Reddit (reddit.com)

## Usage

1. **Web Interface**:
   - Enter a video URL from any supported platform
   - Select desired quality and download type
   - Click "Get Info" to preview video details
   - Click "Download" to start the download process
   - Monitor download progress in real-time

2. **API Integration**:
   - Use the RESTful API endpoints for programmatic access
   - All endpoints return JSON responses
   - Background processing with status tracking

## Technical Details

- **Backend**: FastAPI with Python 3.7+
- **Video Processing**: yt-dlp (youtube-dl fork)
- **Frontend**: Vanilla HTML/CSS/JavaScript
- **File Storage**: Local filesystem with configurable directory
- **CORS**: Enabled for cross-origin requests

## Requirements

- Python 3.7 or higher
- FFmpeg (for audio conversion)
- Internet connection for downloading videos

## Installation Notes

Make sure to install FFmpeg on your system:

- **Ubuntu/Debian**: `sudo apt install ffmpeg`
- **macOS**: `brew install ffmpeg`
- **Windows**: Download from https://ffmpeg.org/

## Security Considerations

- Downloaded files are stored locally in the `/downloads` directory
- No user authentication implemented (suitable for personal use)
- Consider implementing rate limiting for production use
- Be aware of copyright restrictions when downloading content

## Contributing

This is a self-contained video downloader application. Feel free to extend it with additional features like:
- User authentication
- Download history
- Batch downloads
- Cloud storage integration
- Additional platform support

## License

This project is for educational and personal use only. Respect the terms of service of the platforms you're downloading from.