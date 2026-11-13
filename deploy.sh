#!/bin/bash
set -e

echo "=========================================================="
echo "🚀 LOOTOZAVR PRODUCTION DEPLOYMENT SCRIPT"
echo "=========================================================="

# 1. Check if docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Installing Docker & Docker Compose..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
fi

# 2. Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Generating from .env.example..."
    cp .env.example .env
    # Generate random admin secret key
    SECRET_KEY=$(openssl rand -hex 24)
    sed -i "s/ADMIN_SECRET_KEY=.*/ADMIN_SECRET_KEY=${SECRET_KEY}/g" .env
    echo "🔑 Generated random ADMIN_SECRET_KEY: ${SECRET_KEY}"
    echo "⚠️  Please edit .env with your TELEGRAM_BOT_TOKEN before continuing!"
fi

# 3. Pull latest git changes if in a git repo
if [ -d .git ]; then
    echo "📥 Pulling latest git updates..."
    git pull origin master || true
fi

# 4. Build and run containers
echo "🐳 Building and starting Docker containers..."
docker compose up -d --build

# 5. Clean up unused images
echo "🧹 Cleaning up dangling images..."
docker image prune -f

echo "=========================================================="
echo "✅ DEPLOYMENT FINISHED SUCCESSFULLY!"
echo "LootoZavr is live at http://127.0.0.1:8080"
echo "Containers status:"
docker compose ps
echo "=========================================================="
