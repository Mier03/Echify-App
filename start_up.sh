#!/bin/bash

BASE_DIR="/home/sms/Echify-App"
MODEL_PATH="$BASE_DIR/backend/models"

echo "🔄 Updating project from GitHub..."
cd "$BASE_DIR" || exit 1
# git fetch origin
# git reset --hard origin/main

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

echo "🛑 Stopping old processes..."
pkill -f "python3 -m http.server 3000" 2>/dev/null
pkill -f "uvicorn main:app --host 0.0.0.0 --port 8000" 2>/dev/null
pkill -f "camera_engine.py" 2>/dev/null
pkill -f "chromium.*localhost:3000" 2>/dev/null

sleep 2

# ---------------------------
# Build Web UI
# ---------------------------
echo "🔨 Building Web UI..."
rm -rf "$BASE_DIR/dist"
npx expo export -p web --clear

if [ $? -ne 0 ]; then
    echo "❌ Web build failed"
    exit 1
fi

if [ ! -f "$BASE_DIR/dist/index.html" ]; then
    echo "❌ dist/index.html not found after build"
    exit 1
fi

echo "✅ Web UI built successfully"

# ---------------------------
# Start Web Server (Port 3000)
# ---------------------------
echo "🌐 Starting Web Server..."
cd "$BASE_DIR/dist" || exit 1
python3 -m http.server 3000 > "$BASE_DIR/web.log" 2>&1 &
SERVER_PID=$!

sleep 2

if ! kill -0 $SERVER_PID 2>/dev/null; then
    echo "❌ Web server failed to start"
    echo "Check: $BASE_DIR/web.log"
    exit 1
fi

echo "✅ Web server running"

# ---------------------------
# Start Backend (Port 8000)
# ---------------------------
echo "🚀 Starting Backend..."
cd "$BASE_DIR/backend" || exit 1
source "$BASE_DIR/venv/bin/activate"
uvicorn src.main:app --host 0.0.0.0 --port 8000 > "$BASE_DIR/backend.log" 2>&1 &
BACKEND_PID=$!

sleep 5

if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo "❌ Backend failed to start"
    echo "Check: $BASE_DIR/backend.log"
    kill $SERVER_PID 2>/dev/null
    exit 1
fi

echo "✅ Backend running"

# ---------------------------
# Start Camera Engine
# ---------------------------
echo "📷 Starting Camera Engine..."
cd "$BASE_DIR/hardware/camera" || exit 1
"$BASE_DIR/venv/bin/python" camera_engine.py > "$BASE_DIR/camera.log" 2>&1 &
CAMERA_PID=$!

sleep 6

if ! kill -0 $CAMERA_PID 2>/dev/null; then
    echo "❌ Camera engine failed to start"
    echo "Check: $BASE_DIR/camera.log"
    kill $BACKEND_PID $SERVER_PID 2>/dev/null
    exit 1
fi

echo "✅ Camera engine running"

# ---------------------------
# Open Chromium
# ---------------------------
echo "🖥 Opening Chromium..."
rm -rf /tmp/echify-chrome

chromium \
  --user-data-dir=/tmp/echify-chrome \
  --disable-application-cache \
  --disable-cache \
  --disable-service-worker \
  --disk-cache-size=1 \
  --app=http://localhost:3000 \
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