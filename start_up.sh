cd "$BASE_DIR/backend"
source venv/bin/activate
# Start backend using the active venv python
uvicorn main:app --host 0.0.0.0 --port 8000 &

BACKEND_PID=$!

# Give the backend 3 seconds to fully initialize
sleep 3

if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo "❌ Backend failed to start!"
    exit 1
fi

# Start Camera Engine & UI
echo "📷 Starting Camera Engine and UI..."
cd "$BASE_DIR/hardware/camera"
python3 camera_engine.py

# Cleanup on exit
kill $BACKEND_PID 2>/dev/null