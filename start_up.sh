#!/bin/bash

BASE_DIR="/home/sms/Echify-App"
MODEL_PATH="$BASE_DIR/backend/model"

echo "🔄 Updating project from GitHub..."
cd "$BASE_DIR"
git fetch origin
git reset --hard origin/main

# ---------------------------
# Build Web UI (Optional)
# ---------------------------
# Tip: If you haven't changed the UI code, you can comment the next 2 lines 
# with a '#' to make the Pi start much faster.
echo "🔨 Building Web UI..."
npx expo export -p web

# ---------------------------
# Start Web Server (Port 3000)
# ---------------------------
echo "🌐 Starting Web Server..."
cd "$BASE_DIR/dist"
# Running in background
python3 -m http.server 3000 &
SERVER_PID=$!

# ---------------------------
# Start Backend (Port 8000)
# ---------------------------
echo "🚀 Starting Backend..."
cd "$BASE_DIR/backend"
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
sleep 4

# ---------------------------
# Start Camera Engine (FIXED PATH)
# ---------------------------
echo "📷 Starting Camera Engine..."
cd "$BASE_DIR/hardware/camera" 
# Using the venv python to ensure all libraries are found
"$BASE_DIR/backend/venv/bin/python" camera_engine.py &
CAMERA_PID=$!
sleep 6 # Giving the Pi 5 extra time to initialize the IMX708

# ---------------------------
# Open Chromium
# ---------------------------
echo "🖥 Opening Chromium..."
# --test-type hides the "unsupported flag" warning
chromium --app=http://localhost:3000 \
--use-fake-ui-for-media-stream \
--no-sandbox \
--test-type \
--kiosk &

echo "✅ All systems active. Press Ctrl+C to stop all processes."

# ---------------------------
# Cleanup on Exit
# ---------------------------
# This function kills all background tasks when you stop the script
cleanup() {
    echo "🛑 Stopping all processes..."
    kill $SERVER_PID $BACKEND_PID $CAMERA_PID
    exit
}

trap cleanup SIGINT SIGTERM

wait