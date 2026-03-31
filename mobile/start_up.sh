#!/bin/bash
# start_up.sh

BASE_DIR="/home/sms/Echify-App"
MODEL_PATH="$BASE_DIR/backend/models"
CHROME_PROFILE="/home/sms/.echify-profile"

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

echo "🛑 Stopping old processes..."
pkill -f "emergency_button.py" 2>/dev/null
pkill -f "python3 -m http.server 3000" 2>/dev/null
pkill -f "uvicorn src.main:app --host 0.0.0.0 --port 8000" 2>/dev/null
pkill -f "camera_engine.py" 2>/dev/null
pkill -x chromium 2>/dev/null
pkill -f "$CHROME_PROFILE" 2>/dev/null

sleep 3

echo "🧹 Cleaning old Chromium profile..."

##
echo "🎙️ Validating Microphone (Google VoiceHAT)..."

# Check if VoiceHAT is on card 1 OR card 2
MIC_CARD=""
if arecord -l | grep -q "card 2.*voicehat\|voicehat.*card 2" 2>/dev/null; then
    MIC_CARD="2"
elif arecord -l | grep -q "card 1.*voicehat\|voicehat.*card 1" 2>/dev/null; then
    MIC_CARD="1"
elif arecord -l | grep -q "card 2"; then
    MIC_CARD="2"
elif arecord -l | grep -q "card 1"; then
    MIC_CARD="1"
fi

if [ -z "$MIC_CARD" ]; then
    echo "❌ ERROR: Google VoiceHAT NOT detected on card 1 or card 2!"
    echo "Check physical connection on the 40-pin header."
    exit 1
fi

echo "✅ VoiceHAT detected on card $MIC_CARD"

# Wake up the ALSA stream on the detected card
arecord -D plughw:${MIC_CARD},0 -r 44100 -c 2 -f S32_LE -d 2 /tmp/startup_mic_test.wav > /dev/null 2>&1
sox /tmp/startup_mic_test.wav /tmp/startup_mono.wav remix 1 > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo "✅ Microphone hardware initialized on card $MIC_CARD"
else
    echo "⚠️ WARNING: Mic initialization had issues, but continuing..."
fi
##

echo "🎥 Preparing virtual webcam..."
sudo modprobe -r v4l2loopback 2>/dev/null
sudo modprobe v4l2loopback video_nr=10 card_label='Echify-Camera' exclusive_caps=1
sudo chmod 777 /dev/video10
sleep 2

if [ ! -e /dev/video10 ]; then
    echo "❌ /dev/video10 not found after modprobe"
    exit 1
fi

echo "🔨 Building Web UI..."
cd "$BASE_DIR/mobile" || exit 1
rm -rf "$BASE_DIR/mobile/dist"
npx expo export -p web --clear

if [ $? -ne 0 ]; then
    echo "❌ Web build failed"
    exit 1
fi

if [ ! -f "$BASE_DIR/mobile/dist/index.html" ]; then
    echo "❌ dist/index.html not found after build"
    exit 1
fi

echo "✅ Web UI built successfully"

echo "🌐 Starting Web Server..."
cd "$BASE_DIR/mobile/dist" || exit 1
python3 -m http.server 3000 > "$BASE_DIR/web.log" 2>&1 &
SERVER_PID=$!

sleep 2

if ! kill -0 $SERVER_PID 2>/dev/null; then
    echo "❌ Web server failed to start"
    echo "Check: $BASE_DIR/web.log"
    exit 1
fi

echo "✅ Web server running on http://localhost:3000"

echo "📷 Starting Camera Engine..."
cd "$BASE_DIR/hardware/camera" || exit 1
"$BASE_DIR/venv/bin/python" camera_engine.py > "$BASE_DIR/camera.log" 2>&1 &
CAMERA_PID=$!

sleep 12

if ! kill -0 $CAMERA_PID 2>/dev/null; then
    echo "❌ Camera engine failed to start"
    echo "Check: $BASE_DIR/camera.log"
    kill $SERVER_PID 2>/dev/null
    exit 1
fi

echo "✅ Camera engine running"

echo "⏳ Waiting for virtual webcam to stabilize..."
sleep 5

echo "🚀 Starting Backend..."
cd "$BASE_DIR/backend" || exit 1
source "$BASE_DIR/venv/bin/activate"
uvicorn src.main:app --host 0.0.0.0 --port 8000 > "$BASE_DIR/backend.log" 2>&1 &
BACKEND_PID=$!

sleep 5

if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo "❌ Backend failed to start"
    echo "Check: $BASE_DIR/backend.log"
    kill $CAMERA_PID $SERVER_PID 2>/dev/null
    exit 1
fi

echo "✅ Backend running on http://localhost:8000"

echo "🔘 Starting Physical Button Listener..."
cd "$BASE_DIR/hardware/button" || exit 1
"$BASE_DIR/venv/bin/python" emergency_button.py > "$BASE_DIR/button.log" 2>&1 &
BUTTON_PID=$!

sleep 2

if ! kill -0 $BUTTON_PID 2>/dev/null; then
    echo "❌ Button listener failed to start"
    echo "Check: $BASE_DIR/button.log"
    kill $BACKEND_PID $CAMERA_PID $SERVER_PID 2>/dev/null
    exit 1
fi

echo "✅ Button listener running"

echo "🖥 Opening Chromium..."
chromium \
  --user-data-dir="$CHROME_PROFILE" \
  --app=http://localhost:3000 \
  --use-fake-ui-for-media-stream \
  --unsafely-treat-insecure-origin-as-secure=http://localhost:3000 \
  --no-sandbox \
  --test-type \
  --kiosk &

CHROMIUM_PID=$!

echo "✅ All systems active. Press Ctrl+C to stop all processes."

cleanup() {
    echo "🛑 Stopping all processes..."
    kill $CHROMIUM_PID $CAMERA_PID $BACKEND_PID $SERVER_PID $BUTTON_PID 2>/dev/null
    pkill -x chromium 2>/dev/null
    exit
}

trap cleanup SIGINT SIGTERM

wait