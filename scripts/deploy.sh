#!/bin/bash
# PriceForge deployment script
# Usage: ./deploy.sh [server_ip]

set -e

SERVER=${1:-"YOUR_SERVER_IP"}
USER="deploy"
PROJECT_DIR="/opt/priceforge"

echo "=== PriceForge Deploy ==="
echo "Server: $SERVER"

# 1. Pull latest code
echo "[1/5] Pulling latest code..."
ssh $USER@$SERVER "cd $PROJECT_DIR && git pull"

# 2. Build containers
echo "[2/5] Building containers..."
ssh $USER@$SERVER "cd $PROJECT_DIR/docker && docker compose build --no-cache backend"

# 3. Restart services
echo "[3/5] Restarting services..."
ssh $USER@$SERVER "cd $PROJECT_DIR/docker && docker compose up -d --force-recreate backend celery-worker celery-beat"

# 4. Run migrations
echo "[4/5] Running database migrations..."
ssh $USER@$SERVER "cd $PROJECT_DIR/docker && docker compose exec -T backend alembic upgrade head"

# 5. Health check
echo "[5/5] Health check..."
sleep 3
HEALTH=$(ssh $USER@$SERVER "curl -s http://localhost:8000/api/health")
echo "Health: $HEALTH"

echo "=== Deploy complete ==="
