#!/bin/bash

BASE_DIR="/home/sms/Echify-App"
MODEL_PATH="$BASE_DIR/backend/model"

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
# Start Backend
# ---------------------------

echo "🚀 Starting FastAPI Backend..."

cd "$BASE_DIR/backend" || exit 1
source venv/bin/activate

uvicorn main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

sleep 4

if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo "❌ Backend failed to start."
    exit 1
fi

echo "✅ Backend running"

# ---------------------------
# Start Expo Web
# ---------------------------

echo "🌐 Starting Expo Web UI..."

cd "$BASE_DIR"

npx expo start --web &
EXPO_PID=$!

sleep 8

# ---------------------------
# Start Camera Engine
# ---------------------------

echo "📷 Starting Camera Engine..."

cd "$BASE_DIR/hardware/camera" || exit 1

"$BASE_DIR/backend/venv/bin/python" camera_engine.py &
CAMERA_PID=$!

# ---------------------------
# Open Chromium
# ---------------------------

echo "🖥 Opening Chromium UI..."

chromium-browser http://localhost:19006 --kiosk &

# ---------------------------
# Wait
# ---------------------------

wait