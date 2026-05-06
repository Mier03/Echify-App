"""
ws_stt_live.py
==============
Speech-to-Text live WebSocket — Raspberry Pi 5.

Identical to the original ws_stt_live.py EXCEPT:
  - Imports global_logger from session_logger
  - Calls global_logger.log_reconnect("STT", ...) on each connect
  - Calls global_logger.log_stt(...) after each successful transcript
  - Measures dBFS from SharedMic during the recording window

All STT rows land in the SAME CSV as the Sign→TTS rows.
global_logger is never closed here — main.py owns its lifecycle.
"""

import asyncio
import contextlib
import json
import time

import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from faster_whisper import WhisperModel

from src.audio.shared_mic import shared_mic
from session_logger import global_logger, rms_to_dbfs, get_mic_dbfs

router = APIRouter()

INPUT_SAMPLE_RATE  = 48000
OUTPUT_SAMPLE_RATE = 16000

_model = None


def get_model():
    global _model
    if _model is None:
        print("🔊 Loading faster-whisper tiny.en on cpu")
        _model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
    return _model


from scipy.signal import resample_poly


def downsample_48k_to_16k(samples: np.ndarray) -> np.ndarray:
    return resample_poly(samples, 1, 3).astype(np.float32)


def transcribe_samples(samples: np.ndarray) -> str:
    model = get_model()
    mono_16k = downsample_48k_to_16k(samples)
    segments, _ = model.transcribe(
        mono_16k,
        language="en",
        vad_filter=False,
        condition_on_previous_text=False,
        beam_size=1,
    )
    text = " ".join(seg.text.strip() for seg in segments).strip()
    return text


@router.websocket("/ws/stt-live")
async def stt_live_endpoint(websocket: WebSocket):
    await websocket.accept()

    client_id = f"{websocket.client.host}:{websocket.client.port}"
    print(f"🎤 Client connected to /ws/stt-live | {client_id}")

    global_logger.log_reconnect("STT", client_id)

    try:
        get_model()
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": f"Failed to load STT model: {str(e)}",
        })
        await websocket.close()
        return

    is_listening = False
    recorded_chunks = []
    dbfs_samples = []
    rec_start = 0.0
    stop_event = asyncio.Event()

    async def transcribe_and_send(environment="auto", reference=None, auto_stop=False):
        nonlocal recorded_chunks, dbfs_samples, rec_start

        rec_duration = time.monotonic() - rec_start

        audio = (
            np.concatenate(recorded_chunks)
            if recorded_chunks
            else np.array([], dtype=np.float32)
        )

        avg_dbfs = (
            round(sum(dbfs_samples) / len(dbfs_samples), 2)
            if dbfs_samples
            else None
        )

        text = ""
        stt_latency = 0.0
        success = False

        print(f"🧪 Recorded chunks: {len(recorded_chunks)}")
        print(f"🧪 Audio samples  : {len(audio)}")

        if len(audio) > 0:
            print(f"🧪 Max amplitude  : {float(np.max(np.abs(audio))):.4f}")

        if rec_duration >= 0.5 and len(audio) > 0:
            try:
                t0 = time.monotonic()
                text = await asyncio.to_thread(transcribe_samples, audio)
                stt_latency = (time.monotonic() - t0) * 1000
                success = True

                print(
                    f"🧪 Transcript: \"{text}\" | "
                    f"latency={stt_latency:.1f}ms | dBFS={avg_dbfs}"
                )

            except Exception as e:
                print(f"❌ STT transcription error: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": f"STT transcription error: {str(e)}",
                })
                return

        if success:
            global_logger.log_stt(
                transcript=text,
                stt_latency_ms=stt_latency,
                reference=reference,
                environment=environment,
                dbfs=avg_dbfs,
                notes=(
                    f"client={client_id}|"
                    f"duration={rec_duration:.2f}s|"
                    f"chunks={len(recorded_chunks)}|"
                    f"auto_stop={auto_stop}"
                ),
            )

        await websocket.send_json({
            "type": "transcript",
            "text": text if text else "…",
            "dbfs": avg_dbfs,
            "latency_ms": round(stt_latency, 2),
        })

        recorded_chunks = []
        dbfs_samples = []

    async def receiver():
        nonlocal is_listening, recorded_chunks, dbfs_samples, rec_start

        while not stop_event.is_set():
            raw = await websocket.receive_text()
            data = json.loads(raw)

            action = data.get("action")
            environment = data.get("environment", "quiet")
            reference = data.get("reference", None)

            if action == "start":
                print(f"🎙 STT start | env={environment} | client={client_id}")

                is_listening = True
                recorded_chunks = []
                dbfs_samples = []
                rec_start = time.monotonic()

                shared_mic.drain_chunks()

                await websocket.send_json({
                    "type": "status",
                    "message": "Listening started",
                })

            elif action == "stop":
                print(f"🛑 STT stop | client={client_id}")
                is_listening = False
                
                await transcribe_and_send(
                    environment=environment,
                    reference=reference,
                    auto_stop=False,
                )

    async def sender():
        nonlocal is_listening, recorded_chunks, dbfs_samples, rec_start

        # IMPORTANT:
        # Check your terminal silent level.
        # If silence prints around 0.0120, set threshold around 0.018–0.020.
        LOUD_THRESHOLD = 0.0004
        # Auto-transcribe after this many seconds of silence.
        SILENCE_SECONDS = 1.5

        CHUNK_INTERVAL = 0.1

        speech_started = False
        last_loud_time = 0.0

        while not stop_event.is_set():
            level = shared_mic.get_level()
            chunks = shared_mic.drain_chunks()
            now = time.monotonic()

            print(f"Silence Level: {level:.4f}")

            if is_listening and chunks:
                is_loud = level >= LOUD_THRESHOLD

                if is_loud:
                    if not speech_started:
                        print("🗣 Speech started")
                        speech_started = True

                    last_loud_time = now

                # Once speech starts, record everything:
                # loud speech + quiet speech + silence tail.
                if speech_started:
                    recorded_chunks.extend(chunks)

                    db = get_mic_dbfs(shared_mic)
                    if db is not None:
                        dbfs_samples.append(db)

                    silence_duration = now - last_loud_time

                    if silence_duration >= SILENCE_SECONDS:
                        print("🤫 Silence detected, auto-transcribing STT")

                        is_listening = False
                        speech_started = False

                        await websocket.send_json({
                            "type": "status",
                            "message": "Transcribing..."
                        })
                        await transcribe_and_send(
                            environment="auto",
                            reference=None,
                            auto_stop=True,
                        )

            await websocket.send_json({
                "type": "level",
                "level": level,
                "isRecording": is_listening,
            })

            await asyncio.sleep(CHUNK_INTERVAL)

    receiver_task = asyncio.create_task(receiver())
    sender_task = asyncio.create_task(sender())

    try:
        done, pending = await asyncio.wait(
            [receiver_task, sender_task],
            return_when=asyncio.FIRST_EXCEPTION,
        )

        for task in done:
            exc = task.exception()
            if exc:
                raise exc

    except WebSocketDisconnect:
        print(f"🔌 Client disconnected from /ws/stt-live | {client_id}")

    except Exception as e:
        print(f"❌ STT websocket error: {e}")
        with contextlib.suppress(Exception):
            await websocket.send_json({
                "type": "error",
                "message": str(e),
            })

    finally:
        stop_event.set()

        for task in (receiver_task, sender_task):
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await task