#preview.py
import cv2
import time
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from src.camera.shared_camera import shared_camera

router = APIRouter()


def generate_frames():
    while True:
        frame = shared_camera.get_frame()

        if frame is None:
            time.sleep(0.03)
            continue

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