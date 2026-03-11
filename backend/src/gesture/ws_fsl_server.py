from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import cv2
import base64
import time

from src.gesture.fsl_static_inference import (
    initialize_fsl_model,
    predict_fsl_static,
)

router = APIRouter()

CAMERA_DEVICE = "/dev/video10"


def frame_to_base64(frame):
    ok, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
    if not ok:
        return None
    return base64.b64encode(buffer.tobytes()).decode("utf-8")


@router.websocket("/ws/fsl-simple")
async def fsl_simple_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("📱 Client connected to /ws/fsl-simple")

    try:
        initialize_fsl_model()
    except Exception as e:
        await websocket.send_json({"error": str(e), "prediction": "ERROR"})
        await websocket.close()
        return

    cap = cv2.VideoCapture(CAMERA_DEVICE)

    if not cap.isOpened():
        await websocket.send_json({
            "success": False,
            "prediction": "UNKNOWN",
            "confidence": 0.0,
            "message": f"Could not open camera device: {CAMERA_DEVICE}",
            "should_speak": False,
            "letters_to_speak": [],
            "committed_letter": None
        })
        await websocket.close()
        return

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                await websocket.send_json({
                    "success": False,
                    "prediction": "UNKNOWN",
                    "confidence": 0.0,
                    "message": "Failed to read frame",
                    "should_speak": False,
                    "letters_to_speak": [],
                    "committed_letter": None
                })
                time.sleep(0.1)
                continue

            frame_b64 = frame_to_base64(frame)
            if not frame_b64:
                time.sleep(0.05)
                continue

            result = predict_fsl_static(frame_b64, confidence_threshold=0.65)
            await websocket.send_json(result)

            time.sleep(0.15)

    except WebSocketDisconnect:
        print("🔌 Client disconnected from /ws/fsl-simple")
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
    finally:
        cap.release()