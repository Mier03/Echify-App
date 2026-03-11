from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import cv2
import base64
import asyncio

from src.camera.shared_camera import shared_camera
from src.gesture.fsl_static_inference import (
    initialize_fsl_model,
    predict_fsl_static,
)

router = APIRouter()


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

    try:
        while True:
            frame = shared_camera.get_frame()

            if frame is None:
                await websocket.send_json({
                    "success": False,
                    "prediction": "UNKNOWN",
                    "confidence": 0.0,
                    "message": "No frame available",
                    "should_speak": False,
                    "letters_to_speak": [],
                    "committed_letter": None
                })
                await asyncio.sleep(0.1)
                continue

            frame_b64 = frame_to_base64(frame)
            if not frame_b64:
                await asyncio.sleep(0.05)
                continue

            result = predict_fsl_static(frame_b64, confidence_threshold=0.65)
            print("Prediction result:", result)
            await websocket.send_json(result)

            await asyncio.sleep(0.15)

    except WebSocketDisconnect:
        print("🔌 Client disconnected from /ws/fsl-simple")
    except Exception as e:
        print(f"❌ WebSocket error: {e}")