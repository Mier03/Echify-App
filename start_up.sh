#!/bin/bash

BASE_DIR="/home/sms/Echify-App"
MODEL_PATH="$BASE_DIR/backend/model"

echo "🔄 Updating project from GitHub..."
cd "$BASE_DIR" || exit 1
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

# ---------------------------
# Start Web Server (Port 3000)
# ---------------------------
echo "🌐 Starting Web Server..."
cd "$BASE_DIR/dist" || exit 1
python3 -m http.server 3000 &
SERVER_PID=$!

sleep 2

# ---------------------------
# Start Backend (Port 8000)
# ---------------------------
echo "🚀 Starting Backend..."
cd "$BASE_DIR/backend" || exit 1
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

sleep 4

if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo "❌ Backend failed to start"
    kill $SERVER_PID 2>/dev/null
    exit 1
fi

echo "✅ Backend running"

# ---------------------------
# Start Camera Engine
# ---------------------------
echo "📷 Starting Camera Engine..."
cd "$BASE_DIR/hardware/camera" || exit 1
"$BASE_DIR/backend/venv/bin/python" camera_engine.py &
CAMERA_PID=$!

sleep 6

# ---------------------------
# Open Chromium
# ---------------------------
echo "🖥 Opening Chromium..."
chromium --app=http://localhost:3000 \
  --use-fake-ui-for-media-stream \
  --no-sandbox \
  --test-type \
  --kiosk &

CHROMIUM_PID=$!

echo "✅ All systems active. Press Ctrl+C to stop all processes."

# ---------------------------
# Cleanup on Exit
# ---------------------------
cleanup() {
    echo "🛑 Stopping all processes..."
    kill $CHROMIUM_PID $CAMERA_PID $BACKEND_PID $SERVER_PID 2>/dev/null
    exit
}

trap cleanup SIGINT SIGTERM

wait