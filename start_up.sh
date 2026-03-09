#!/bin/bash

BASE_DIR="/home/sms/Echify-App"
MODEL_FILE="$BASE_DIR/backend/models/lstm_static/best_fsl_lstm_model.pth"

echo "🔄 Updating project from GitHub..."
cd "$BASE_DIR" || exit 1
git fetch origin
git reset --hard origin/main

echo "🔍 Checking project integrity..."

if [ ! -f "$MODEL_FILE" ]; then
    echo "❌ ERROR: Model file NOT found at $MODEL_FILE"
    exit 1
fi

echo "✅ Model file found."

echo "🛑 Stopping old processes..."
pkill -f "python3 -m http.server 3000" 2>/dev/null
pkill -f "uvicorn src.main:app --host 0.0.0.0 --port 8000" 2>/dev/null
pkill -f "camera_engine.py" 2>/dev/null
pkill -f "gst-launch-1.0" 2>/dev/null
pkill -f "chromium.*localhost:3000" 2>/dev/null

sleep 2

echo "🔨 Building Web UI..."
rm -rf "$BASE_DIR/dist"
cd "$BASE_DIR" || exit 1
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

echo "🌐 Starting Web Server..."
cd "$BASE_DIR/dist" || exit 1
python3 -m http.server 3000 > "$BASE_DIR/web.log" 2>&1 &
SERVER_PID=$!

sleep 2

if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "❌ Web server failed to start"
    echo "Check: $BASE_DIR/web.log"
    exit 1
fi

echo "✅ Web server running"

echo "🚀 Starting Backend..."
cd "$BASE_DIR/backend" || exit 1
source "$BASE_DIR/venv/bin/activate"
uvicorn src.main:app --host 0.0.0.0 --port 8000 > "$BASE_DIR/backend.log" 2>&1 &
BACKEND_PID=$!

sleep 5

if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo "❌ Backend failed to start"
    echo "Check: $BASE_DIR/backend.log"
    kill "$SERVER_PID" 2>/dev/null
    exit 1
fi

echo "✅ Backend running"

echo "📷 Starting Camera Engine..."
cd "$BASE_DIR/hardware/camera" || exit 1
"$BASE_DIR/venv/bin/python" camera_engine.py > "$BASE_DIR/camera.log" 2>&1 &
CAMERA_PID=$!

sleep 6

if ! kill -0 "$CAMERA_PID" 2>/dev/null; then
    echo "❌ Camera engine failed to start"
    echo "Check: $BASE_DIR/camera.log"
    kill "$BACKEND_PID" "$SERVER_PID" 2>/dev/null
    exit 1
fi

echo "✅ Camera engine running"

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
  --autoplay-policy=no-user-gesture-required \
  --no-sandbox \
  --test-type \
  --kiosk &

CHROMIUM_PID=$!

echo "✅ All systems active. Press Ctrl+C to stop all processes."

cleanup() {
    echo "🛑 Stopping all processes..."
    kill "$CHROMIUM_PID" "$CAMERA_PID" "$BACKEND_PID" "$SERVER_PID" 2>/dev/null
    pkill -f "gst-launch-1.0" 2>/dev/null
    exit
}

trap cleanup SIGINT SIGTERM

wait