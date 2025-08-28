#!/bin/bash

# Social Media Video Downloader - Startup Script

echo "🎥 Starting Social Media Video Downloader API..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Install dependencies if needed
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Create downloads directory
mkdir -p downloads

# Start the application
echo "🚀 Starting the application on http://localhost:8000"
echo "   Web Interface: http://localhost:8000"
echo "   API Documentation: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python main.py