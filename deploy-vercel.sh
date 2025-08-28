#!/bin/bash

# Vercel Deployment Script for Social Media Video Downloader

echo "🚀 Preparing for Vercel deployment..."

# Check if we're in the right directory
if [ ! -f "vercel.json" ]; then
    echo "❌ vercel.json not found. Are you in the right directory?"
    exit 1
fi

# Test deployment readiness
echo "🧪 Testing deployment readiness..."
python test_vercel.py

if [ $? -ne 0 ]; then
    echo "❌ Deployment readiness test failed!"
    exit 1
fi

echo "✅ All tests passed!"

# Check if vercel CLI is installed
if ! command -v vercel &> /dev/null; then
    echo "📦 Vercel CLI not found. Installing..."
    echo "Please install Vercel CLI first:"
    echo "  npm install -g vercel"
    echo ""
    echo "Or deploy via GitHub:"
    echo "  1. Push to GitHub: git push origin main"
    echo "  2. Go to vercel.com/new"
    echo "  3. Import your repository"
    exit 1
fi

# Deploy with Vercel CLI
echo "🚀 Deploying to Vercel..."
vercel --prod

echo "✅ Deployment initiated!"
echo ""
echo "📝 Post-deployment checklist:"
echo "   - Test the deployed application"
echo "   - Check all API endpoints work"
echo "   - Verify video download functionality"
echo "   - Monitor function logs for any issues"