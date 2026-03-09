#!/bin/bash

BASE_DIR="/home/sms/Echify-App"
MODEL_PATH="$BASE_DIR/backend/model"

echo "🔄 Updating project from GitHub..."
cd "$BASE_DIR"
git fetch origin
git reset --hard origin/main

echo "🔍 Checking project integrity..."

if [ ! -d "$MODEL_PATH" ]; then
    echo "❌ ERROR: Model directory NOT found at $MODEL_PATH"
    exit 1
fi

if [ -z "$(ls -A "$MODEL_PATH")" ]; then
    echo "⚠️ WARNING: Model folder is empty!"
else
    echo "✅ Model folder found."
fi


# ---------------------------
# Build Web UI
# ---------------------------

echo "🔨 Building Web UI..."

cd "$BASE_DIR"

npx expo export -p web

if [ $? -ne 0 ]; then
    echo "❌ Web build failed"
    exit 1
fi

echo "✅ Web UI built successfully"


# ---------------------------
# Start Backend
# ---------------------------

echo "🚀 Starting Backend..."

cd "$BASE_DIR/backend"

source venv/bin/activate

uvicorn main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

sleep 4

if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo "❌ Backend failed to start"
    exit 1
fi

echo "✅ Backend running"


# ---------------------------
# Start Camera Engine
# ---------------------------

echo "📷 Starting Camera Engine..."

cd "$BASE_DIR/hardware/camera"

"$BASE_DIR/backend/venv/bin/python" camera_engine.py &
CAMERA_PID=$!

sleep 5


# ---------------------------
# Open Chromium
# ---------------------------

echo "🖥 Opening Chromium..."

chromium --app=http://localhost:3000 \
--use-fake-ui-for-media-stream \
--no-sandbox \
--kiosk &


# ---------------------------
# Keep script alive
# ---------------------------

wait