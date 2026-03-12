import asyncio
import os
import tempfile
import wave

import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from faster_whisper import WhisperModel

from src.audio.shared_mic import shared_mic

router = APIRouter()

SAMPLE_RATE = 16000
LEVEL_THRESHOLD = 0.015
SILENCE_SECONDS_TO_STOP = 1.0
MIN_SPEECH_SECONDS = 0.3

_model = None


def get_model():
    global _model
    if _model is None:
        print("🔊 Loading faster-whisper small.en on cpu")
        _model = WhisperModel("small.en", device="cpu", compute_type="int8")
    return _model


def save_wav(samples: np.ndarray, path: str):
    samples = np.clip(samples, -1.0, 1.0)
    pcm16 = (samples * 32767).astype(np.int16)

    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm16.tobytes())


def transcribe_samples(samples: np.ndarray) -> str:
    model = get_model()

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        save_wav(samples, tmp_path)
        segments, _ = model.transcribe(tmp_path, language="en")
        text = " ".join(seg.text.strip() for seg in segments).strip()
        return text
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@router.websocket("/ws/stt-live")
async def stt_live_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("🎤 Client connected to /ws/stt-live")

    try:
        get_model()
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": f"Failed to load STT model: {str(e)}"
        })
        await websocket.close()
        return

    speech_chunks = []
    speaking = False
    silence_duration = 0.0
    speech_duration = 0.0
    chunk_duration = 0.1

    try:
        while True:
            level = shared_mic.get_level()
            chunks = shared_mic.drain_chunks()

            for chunk in chunks:
                chunk_rms = float(np.sqrt(np.mean(np.square(chunk)))) if len(chunk) > 0 else 0.0

                if chunk_rms > LEVEL_THRESHOLD:
                    speaking = True
                    silence_duration = 0.0
                    speech_duration += chunk_duration
                    speech_chunks.append(chunk)
                elif speaking:
                    silence_duration += chunk_duration
                    speech_chunks.append(chunk)

            await websocket.send_json({
                "type": "level",
                "level": level,
                "isRecording": speaking,
            })

            if (
                speaking
                and speech_duration >= MIN_SPEECH_SECONDS
                and silence_duration >= SILENCE_SECONDS_TO_STOP
            ):
                audio = np.concatenate(speech_chunks) if speech_chunks else np.array([], dtype=np.float32)
                text = ""

                if len(audio) > 0:
                    try:
                        text = transcribe_samples(audio)
                    except Exception as e:
                        print(f"❌ STT transcription error: {e}")

                await websocket.send_json({
                    "type": "transcript",
                    "text": text if text else "…",
                })

                speech_chunks = []
                speaking = False
                silence_duration = 0.0
                speech_duration = 0.0

            await asyncio.sleep(0.1)

    except WebSocketDisconnect:
        print("🔌 Client disconnected from /ws/stt-live")
    except Exception as e:
        print(f"❌ STT websocket error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e),
            })
        except Exception:
            pass