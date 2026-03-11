#routes/preview.py
import cv2
import time
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter()

CAMERA_DEVICE = "/dev/video10"


def generate_frames():
    cap = cv2.VideoCapture(CAMERA_DEVICE)

    if not cap.isOpened():
        raise RuntimeError(f"Could not open camera device: {CAMERA_DEVICE}")

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                time.sleep(0.03)
                continue

            ok, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            if not ok:
                time.sleep(0.03)
                continue

            jpg = buffer.tobytes()

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + jpg + b"\r\n"
            )

            time.sleep(0.03)
    finally:
        cap.release()


@router.get("/preview")
def preview_stream():
    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )