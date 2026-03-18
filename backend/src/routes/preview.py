#preview.py
import cv2
import time
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from src.camera.shared_camera import shared_camera

router = APIRouter()


def generate_frames():
    import numpy as np

    while True:
        frame = shared_camera.get_frame()

        # ✅ FIX: always send a frame (even if camera not ready)
        if frame is None:
            frame = np.zeros((480, 640, 3), dtype=np.uint8)

            cv2.putText(
                frame,
                "Starting camera...",
                (120, 240),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )

        ok, buffer = cv2.imencode(
            ".jpg",
            frame,
            [int(cv2.IMWRITE_JPEG_QUALITY), 80]
        )

        if not ok:
            time.sleep(0.03)
            continue

        jpg = buffer.tobytes()

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + jpg + b"\r\n"
        )

        time.sleep(0.03)

@router.get("/preview")
def preview_stream():
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "*",
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0",
    }

    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers=headers,
    )