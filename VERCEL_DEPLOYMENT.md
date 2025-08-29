# Deploying Social Media Video Downloader to Vercel

This guide explains how to deploy the Social Media Video Downloader API to Vercel's serverless platform.

## 🚀 Quick Deploy

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/your-username/video-downloader)

## 📋 Prerequisites

1. **Vercel Account**: Sign up at [vercel.com](https://vercel.com)
2. **GitHub Repository**: Push your code to GitHub
3. **Vercel CLI** (optional): `npm install -g vercel`

## 🔧 Vercel Configuration

The project includes these Vercel-specific files:

### `vercel.json`
```json
{
  "version": 2,
  "builds": [
    { "src": "api/index.py", "use": "@vercel/python", "config": { "includeFiles": "static/**" } }
  ],
  "routes": [
    { "src": "/api/(.*)", "dest": "/api/index.py" },
    { "src": "/(.*)", "dest": "/api/index.py" }
  ]
}
```

**Note**: This configuration pins the Python builder implicitly to Vercel's latest supported version and bundles the `static/` directory into the function output.

### `api/requirements.txt`
Dependencies installed for the Python Function:
- `fastapi==0.115.6`
- `yt-dlp==2024.12.23`
- `pydantic==2.10.5`
- `httpx==0.28.1`

## 📁 Project Structure for Vercel

```
your-project/
├── api/
│   └── index.py          # Serverless API handler
├── static/
│   └── index.html        # Frontend
├── vercel.json           # Vercel configuration (builds + routes)
├── api/requirements.txt  # Python function dependencies
├── main.py              # Local development server
└── README.md
```

## 🚀 Deployment Steps

### Method 1: GitHub Integration (Recommended)

1. **Push to GitHub**:
   ```bash
   git add .
   git commit -m "Add Vercel configuration"
   git push origin main
   ```

2. **Connect to Vercel**:
   - Go to [vercel.com/dashboard](https://vercel.com/dashboard)
   - Click "New Project"
   - Import your GitHub repository
   - Vercel will auto-detect the configuration

3. **Configure Build Settings**:
   - Framework Preset: `Other`
   - Build Command: (leave empty)
   - Output Directory: (leave empty)
   - Install Command: (leave empty; Vercel installs `api/requirements.txt`)

4. **Deploy**:
   - Click "Deploy"
   - Wait for deployment to complete
   - Access your app at the provided URL

### Method 2: Vercel CLI

1. **Install Vercel CLI**:
   ```bash
   npm install -g vercel
   ```

2. **Login to Vercel**:
   ```bash
   vercel login
   ```

3. **Deploy**:
   ```bash
   vercel
   ```

4. **Follow the prompts**:
   - Set up and deploy? `Y`
   - Which scope? Choose your scope
   - Link to existing project? `N` (for new project)
   - Project name: Enter your project name
   - In which directory is your code located? `./`

## ⚙️ Environment Variables

For production deployment, you may want to set these environment variables in Vercel:

1. Go to your project in Vercel Dashboard
2. Navigate to Settings → Environment Variables
3. Add any required variables:
   - `PYTHONPATH=/var/task` (automatically set)
   - Custom variables as needed

## 🔄 Serverless Adaptations

The Vercel version includes these key changes from the local version:

### 1. Direct Download URLs
Instead of background processing, the API now returns direct download URLs that users can use immediately.

### 2. Stateless Operation
No file storage on the server - all downloads are handled client-side via direct URLs.

### 3. Optimized Dependencies
Reduced dependency list for faster cold starts:
- Removed `uvicorn` (not needed for serverless)
- Removed `aiofiles` (no file storage)
- Added `httpx` for HTTP requests

### 4. Handler Export
```python
# For Vercel
handler = app
```

## 🌐 Custom Domain

To use a custom domain:

1. **Add Domain in Vercel**:
   - Go to Project Settings → Domains
   - Add your custom domain

2. **Configure DNS**:
   - Add CNAME record pointing to `cname.vercel-dns.com`
   - Or add A record pointing to Vercel's IP

## 📊 Monitoring

Vercel provides built-in monitoring:
- **Analytics**: Traffic and performance metrics
- **Logs**: Real-time function logs
- **Errors**: Error tracking and debugging

Access these in your Vercel project dashboard.

## 🚨 Limitations

Be aware of Vercel's limits:

1. **Function Timeout**: 60 seconds max (configured in vercel.json)
2. **Memory**: 1024MB max for Hobby plan
3. **File Size**: No persistent file storage
4. **Concurrent Executions**: Limited based on plan

## 🔧 Troubleshooting

### Common Issues:

1. **"functions property cannot be used with builds" Error**:
   - ✅ **Fixed**: Use modern `functions` configuration only
   - Remove `builds` and `version` properties from `vercel.json`
   - Use `rewrites` instead of `routes` for URL routing

2. **Build Failures**:
   - Check `requirements-vercel.txt` dependencies
   - Ensure Python 3.9+ compatibility
   - Verify API structure: files must be in `api/` directory

3. **Import Errors**:
   - Verify all imports are available in the serverless environment
   - Check for local-only dependencies
   - Ensure `handler = app` export in `api/index.py`

4. **Timeout Issues**:
   - Optimize video processing
   - Consider using direct URLs instead of processing
   - Current limit: 60 seconds (configured in vercel.json)

5. **CORS Issues**:
   - CORS is pre-configured in the API
   - Check browser developer tools for specific errors

6. **404 Errors**:
   - Ensure API file is at `api/index.py`
   - Check `rewrites` configuration in `vercel.json`
   - Verify FastAPI app is properly exported as `handler`

### Debug Logs:
```bash
vercel logs [deployment-url]
```

## 🆚 Local vs Vercel Differences

| Feature | Local Version | Vercel Version |
|---------|---------------|----------------|
| File Storage | Local filesystem | Direct URLs only |
| Background Tasks | AsyncIO background tasks | Stateless processing |
| Download Method | Server-side processing | Client-side direct download |
| Persistence | File-based status tracking | Stateless operation |

## 📝 Next Steps

After deployment:

1. **Test All Endpoints**: Verify API functionality
2. **Monitor Performance**: Check function execution times
3. **Update Documentation**: Update any hardcoded URLs
4. **Set Up Analytics**: Enable Vercel Analytics if needed

## 🔗 Useful Links

- [Vercel Python Runtime](https://vercel.com/docs/runtimes/python)
- [Vercel Configuration](https://vercel.com/docs/project-configuration)
- [FastAPI Deployment Guide](https://fastapi.tiangolo.com/deployment/vercel/)
- [yt-dlp Documentation](https://github.com/yt-dlp/yt-dlp)

---

Your social media video downloader is now ready for production deployment on Vercel! 🎉