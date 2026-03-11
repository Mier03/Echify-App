from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.camera.shared_camera import shared_camera
from src.audio.shared_mic import shared_mic

from src.gesture.ws_fsl_server import router as fsl_router
from src.stt.stt_http import router as stt_router
from src.stt.ws_stt_live import router as stt_live_router
from src.routes.preview import router as preview_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    shared_camera.start()
    shared_mic.start()


@app.on_event("shutdown")
def shutdown_event():
    shared_camera.stop()
    shared_mic.stop()


app.include_router(fsl_router)
app.include_router(stt_router)
app.include_router(stt_live_router)
app.include_router(preview_router)