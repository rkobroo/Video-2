# Social Media Video Downloader API

A powerful web application that allows users to download videos from various social media platforms including YouTube, TikTok, Instagram, Twitter, Facebook, and more.

## Features

- **Multi-platform Support**: Download from YouTube, TikTok, Instagram, Twitter/X, Facebook, Twitch, Vimeo, Dailymotion, and Reddit
- **Quality Selection**: Choose from multiple video quality options (best, 720p, 480p, 360p, worst)
- **Audio-only Downloads**: Extract audio as MP3 files
- **Enhanced Metadata**: Display thumbnails, duration, uploader, views, likes, upload date
- **Multiple Media Support**: Download multiple photos/images from social media posts
- **Smart Filenames**: Automatically use video titles as filenames (sanitized for file systems)
- **Rich Video Info**: Preview comprehensive video details before downloading
- **Real-time Status**: Track download progress with live status updates
- **Modern UI**: Beautiful, responsive web interface with enhanced media display
- **RESTful API**: Full API endpoints for integration

## Quick Start

### Local Development

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Application**:
   ```bash
   python main.py
   # Or use the startup script
   ./start.sh
   ```

3. **Access the Web Interface**:
   Open your browser and go to `http://localhost:8000`

### Deploy to Vercel

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/your-username/video-downloader)

1. **Test Deployment Readiness**:
   ```bash
   python test_vercel.py
   ```

2. **Deploy via GitHub** (Recommended):
   - Push your code to GitHub
   - Go to [vercel.com/new](https://vercel.com/new)
   - Import your repository
   - Deploy automatically

3. **Deploy via CLI**:
   ```bash
   npm install -g vercel
   ./deploy-vercel.sh
   ```

📖 **Detailed Deployment Guide**: See [VERCEL_DEPLOYMENT.md](VERCEL_DEPLOYMENT.md)

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

## Deployment Options

### 🏠 Local Development
- Full featured version with background processing
- File storage on local filesystem
- Real-time download status tracking
- Perfect for personal use and development

### ☁️ Vercel (Serverless)
- Optimized for serverless deployment
- Direct download URLs (no server storage)
- Instant scaling and global CDN
- Perfect for production web apps

### 🔄 Key Differences

| Feature | Local | Vercel |
|---------|-------|--------|
| Background Processing | ✅ AsyncIO tasks | ❌ Direct URLs |
| File Storage | ✅ Local filesystem | ❌ Stateless |
| Download Method | Server processes files | Client downloads directly |
| Scalability | Single server | Auto-scaling |
| Setup Complexity | Simple | Requires Vercel account |

## Technical Details

- **Backend**: FastAPI with Python 3.7+
- **Video Processing**: yt-dlp (youtube-dl fork)
- **Frontend**: Vanilla HTML/CSS/JavaScript
- **Local Storage**: Local filesystem with configurable directory
- **Vercel Storage**: Direct URLs (no server storage)
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

## Project Structure

```
video-downloader/
├── 📁 api/
│   └── index.py              # Vercel serverless API
├── 📁 static/
│   └── index.html            # Modern web interface
├── 📁 downloads/             # Local downloads (auto-created)
├── main.py                   # Local development server
├── requirements.txt          # Local dependencies
├── requirements-vercel.txt   # Vercel dependencies
├── vercel.json               # Vercel configuration
├── start.sh                  # Local startup script
├── deploy-vercel.sh          # Vercel deployment script
├── test_api.py               # API testing script
├── test_vercel.py            # Vercel readiness test
├── README.md                 # Main documentation
├── VERCEL_DEPLOYMENT.md      # Vercel deployment guide
└── .git/                     # Git repository
```

## Contributing

This is a self-contained video downloader application. Feel free to extend it with additional features like:
- User authentication
- Download history
- Batch downloads
- Cloud storage integration
- Additional platform support

## License

This project is for educational and personal use only. Respect the terms of service of the platforms you're downloading from.