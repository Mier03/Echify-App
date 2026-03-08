#!/bin/bash

# --- Configuration ---
# Define the absolute path to the project root to avoid pathing errors
BASE_DIR="/home/sms/Echify-App"

# --- Backend Startup ---
echo "🚀 Starting FastAPI Backend..."

# Navigate to the backend directory
cd "$BASE_DIR/backend" || { echo "❌ Could not find backend folder"; exit 1; }

# Activate the virtual environment to ensure dependencies (Uvicorn/FastAPI) are available
source venv/bin/activate

# Start the backend server in the background (&) 
# --host 0.0.0.0 makes it accessible from other devices on the network
uvicorn main:app --host 0.0.0.0 --port 8000 &

# Capture the Process ID (PID) of the backend so we can manage/kill it later
BACKEND_PID=$!

# Wait for 3 seconds to let the server bind to the port and initialize
sleep 3

# Check if the process is still running (kill -0 checks for the process without killing it)
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo "❌ Backend failed to start! Check your main.py or venv."
    exit 1
fi

# --- Hardware/UI Startup ---
echo "📷 Starting Camera Engine and UI..."

# Navigate to the camera hardware directory
cd "$BASE_DIR/hardware/camera" || { echo "❌ Could not find camera folder"; exit 1; }

# Run the camera engine (this usually keeps the script running in the foreground)
python3 camera_engine.py

# --- Cleanup ---
# Once the camera engine is closed (Ctrl+C), kill the background backend process
echo "Shutting down..."
kill $BACKEND_PID 2>/dev/null