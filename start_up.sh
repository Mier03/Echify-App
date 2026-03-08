#!/bin/bash

BASE_DIR="/home/sms/Echify-App"

echo "🧹 Step 0: Cleaning up old processes and drivers..."

sudo fuser -k 8000/tcp 2>/dev/null
sudo fuser -k 3000/tcp 2>/dev/null

# Reset virtual camera
sudo modprobe -r v4l2loopback 2>/dev/null
sudo modprobe v4l2loopback video_nr=10 card_label="Echify-Camera" exclusive_caps=1
sleep 1
sudo chmod 777 /dev/video10

echo "🚀 Starting Echify..."

# -------------------------
# 1. Start AI Backend
# -------------------------
echo "🧠 Starting AI Backend..."

cd "$BASE_DIR/backend"

$BASE_DIR/backend/venv/bin/python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 &

BACKEND_PID=$!

sleep 3

if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo "❌ Backend failed to start!"
    exit 1
fi

# -------------------------
# 2. Start Camera Engine
# -------------------------
echo "📷 Starting Camera Engine and UI..."

cd "$BASE_DIR/hardware/camera"
python3 camera_engine.py

# -------------------------
# Cleanup
# -------------------------
kill $BACKEND_PID 2>/dev/null