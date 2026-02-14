#!/bin/bash

# 🚀 Bharat Biz-Agent Docker Quick Start Script

set -e

echo "================================"
echo "Bharat Biz-Agent Docker Setup"
echo "================================"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "📋 Creating .env from .env.docker..."
    cp .env.docker .env
    echo "⚠️  IMPORTANT: Edit .env with your credentials"
    echo "   - SECRET_KEY (generate: python -c \"import secrets; print(secrets.token_urlsafe(32))\")"
    echo "   - TELEGRAM_BOT_TOKEN"
    echo "   - GROQ_API_KEY"
    echo ""
    read -p "Press Enter after editing .env..."
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker Desktop"
    exit 1
fi

echo "✓ Docker found"

# Check docker-compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose not found. Please install Docker Desktop"
    exit 1
fi

echo "✓ docker-compose found"
echo ""

# Build
echo "🔨 Building Docker images..."
docker-compose build

echo ""
echo "🚀 Starting services..."
docker-compose up -d

# Wait for services to be ready
echo ""
echo "⏳ Waiting for services to be ready..."
sleep 5

# Check health
echo ""
echo "✅ Checking service health..."

if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "   ✓ Backend: http://localhost:8000 (healthy)"
else
    echo "   ⚠️  Backend: http://localhost:8000 (not responding yet, check logs)"
fi

if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo "   ✓ Frontend: http://localhost:3000 (ready)"
else
    echo "   ⚠️  Frontend: http://localhost:3000 (not responding yet, check logs)"
fi

echo ""
echo "================================"
echo "✅ DEPLOYMENT COMPLETE"
echo "================================"
echo ""
echo "🌐 Access URLs:"
echo "   Frontend: http://localhost:3000"
echo "   Backend API: http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "📋 Useful Commands:"
echo "   View logs:     docker-compose logs -f"
echo "   Stop services: docker-compose down"
echo "   Restart:       docker-compose restart"
echo ""
echo "📖 Read DOCKER_DEPLOYMENT.md for full documentation"
echo ""
