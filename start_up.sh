#!/bin/bash

# --- Configuration ---
BASE_DIR="/home/sms/Echify-App"
MODEL_PATH="$BASE_DIR/backend/model"

# --- 1. Model & Directory Check ---
echo "🔍 Checking project integrity..."

# Check if the model folder exists
if [ ! -d "$MODEL_PATH" ]; then
    echo "❌ ERROR: Model directory NOT found at $MODEL_PATH"
    exit 1
fi

# Check if the model folder is empty
if [ -z "$(ls -A "$MODEL_PATH")" ]; then
    echo "⚠️  WARNING: Model folder is empty! Your AI features might fail."
else
    echo "✅ Model folder found. Files: $(ls "$MODEL_PATH" | tr '\n' ' ')"
fi

# --- 2. Start Backend ---
echo "🚀 Starting FastAPI Backend..."
cd "$BASE_DIR/backend" || exit 1

# Activate venv and start Uvicorn in background
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait and verify backend is actually running
sleep 4
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo "❌ Backend failed to start. Check your Python code or venv."
    exit 1
fi
echo "✅ Backend is live (PID: $BACKEND_PID)"

# --- 3. Start Frontend / UI ---
echo "🖥️  Starting Frontend / Camera Engine..."

# Navigate to your UI/Camera directory
cd "$BASE_DIR/hardware/camera" || exit 1

# Run the UI/Camera Engine
# Using the venv python ensures it has the right libraries
"$BASE_DIR/backend/venv/bin/python" camera_engine.py

# --- 4. Cleanup ---
echo "Stopping all services..."
kill $BACKEND_PID 2>/dev/null