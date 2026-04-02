"""
main.py
========
FastAPI application entry point — with session lifecycle management.

Session logging strategy:
  - global_logger (session_logger.py) owns ONE CSV for the Pi's entire runtime.
  - shared_mic is wired into global_logger so dBFS is auto-read on every
    log_tts() and log_stt() call.
  - global_logger.start() is called once at startup.
  - global_logger.close() is called once at shutdown (also fires via atexit).
"""

from contextlib import asynccontextmanager
from datetime import datetime
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.camera.shared_camera import shared_camera
from src.audio.shared_mic import shared_mic

from src.gesture.ws_fsl_server import router as fsl_router
from src.gesture.ws_fsl_dynamic_server import router as fsl_dynamic_router
from src.stt.stt_http import router as stt_router
from src.routes.preview import router as preview_router
from src.stt.ws_stt_live import router as stt_live_router
from src.stt.ws_stt_live import get_model

from session_logger import global_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    startup_ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # ── Wire SharedMic into the logger so dBFS is auto-read ───────────────
    # Must be done BEFORE global_logger.start() so the BOOT row already
    # knows whether mic is available.
    global_logger.shared_mic = shared_mic

    # ── Open the ONE CSV for this Pi boot ─────────────────────────────────
    global_logger.start()

    print("=" * 60)
    print("🚀 FSL Communication System — Server Started")
    print(f"   Session ID : {startup_ts}")
    print(f"   CSV log    : {global_logger._csv_path}")
    print("=" * 60)

    # ── Start hardware ─────────────────────────────────────────────────────
    shared_camera.start()
    shared_mic.start()
    get_model()

    yield

    # ── Shutdown ───────────────────────────────────────────────────────────
    print("\n🛑 Server shutting down...")

    shared_camera.stop()
    shared_mic.stop()

    # Finalize CSV + write summary JSON
    global_logger.close()

    print("✅ Shutdown complete.")


app = FastAPI(
    title="FSL Bidirectional Communication System",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(fsl_router)
app.include_router(stt_router)
app.include_router(fsl_dynamic_router)
app.include_router(stt_live_router)
app.include_router(preview_router)


# ── SOS endpoint ──────────────────────────────────────────────────────────────

@app.post("/sos/trigger")
async def sos_trigger(request: Request):
    t8    = time.monotonic()
    t8_dt = datetime.now().strftime("%H:%M:%S.%f")[:-3]

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})

    state            = body.get("state", "unknown")
    response_time_ms = float(body.get("response_time_ms", 0.0))
    success          = bool(body.get("success", True))
    client_id        = body.get("client_id", "unknown")

    server_receive_ms = (time.monotonic() - t8) * 1000

    print(f"\n  [SOS T8] Received @ {t8_dt}")
    print(f"  {'─'*50}")
    print("  🆘 SOS EVENT")
    print(f"     State            : {state}")
    print(f"     Frontend response: {response_time_ms:.1f} ms  (button → audio)")
    print(f"     Server receive   : {server_receive_ms:.1f} ms")
    print(f"     Client           : {client_id}")
    print(f"     Result           : {'✅ PASS' if success else '❌ FAIL'}")
    print(f"  {'─'*50}\n")

    global_logger.log_sos(
        response_time_ms=response_time_ms,
        state=state,
        success=success,
        notes=f"client_id={client_id}|server_receive_ms={server_receive_ms:.2f}"
    )

    return JSONResponse(content={
        "logged":            True,
        "state":             state,
        "response_time_ms":  response_time_ms,
        "success":           success,
    })


# ── Live summary endpoint ─────────────────────────────────────────────────────

@app.get("/session/summary")
async def session_summary():
    g_events = global_logger._gesture_events
    t_events = global_logger._tts_events
    s_events = global_logger._stt_events
    o_events = global_logger._sos_events

    def avg(lst):
        return round(sum(lst) / len(lst), 2) if lst else 0

    return JSONResponse(content={
        "csv_path":     str(global_logger._csv_path),
        "summary_path": str(global_logger._summary_path),
        "total_events": global_logger._event_counter,
        "gesture": {
            "total":        len(g_events),
            "avg_conf":     avg([e["confidence"]   for e in g_events]),
            "avg_infer_ms": avg([e["inference_ms"] for e in g_events]),
        },
        "tts": {
            "total":       len(t_events),
            "avg_latency": avg([e["latency_ms"] for e in t_events]),
        },
        "stt": {
            "total":       len(s_events),
            "quiet_count": len([e for e in s_events if e["environment"] == "quiet"]),
            "noisy_count": len([e for e in s_events if e["environment"] == "noisy"]),
        },
        "sos": {
            "total":        len(o_events),
            "passed":       len([e for e in o_events if e["success"]]),
            "avg_response": avg([e["response_ms"] for e in o_events]),
        },
    })