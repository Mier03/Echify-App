#shared_mic.py
import queue
import threading

import numpy as np
import sounddevice as sd


class SharedMic:
    def __init__(
        self,
        samplerate=48000,
        channels=2,
        blocksize=4800,
        device_name_hint="Google voiceHAT SoundCard",
    ):
        self.samplerate = samplerate
        self.channels = channels
        self.blocksize = blocksize
        self.device_name_hint = device_name_hint

        self.stream = None
        self.running = False
        self.level = 0.0
        self.lock = threading.Lock()
        self.chunk_queue = queue.Queue()
        self.device_index = None

    def _resolve_device_index(self):
        devices = sd.query_devices()
        print("🎤 Available audio devices:")
        for i, dev in enumerate(devices):
            print(f"[{i}] {dev}")

        for i, dev in enumerate(devices):
            name = str(dev["name"])
            max_input_channels = int(dev["max_input_channels"])
            if self.device_name_hint.lower() in name.lower() and max_input_channels > 0:
                return i

        raise RuntimeError(
            f"Could not find input device containing '{self.device_name_hint}'"
        )

    def start(self):
        if self.running:
            return

        try:
            self.device_index = self._resolve_device_index()
            print(f"✅ Using microphone device index: {self.device_index}")

            self.stream = sd.InputStream(
                samplerate=self.samplerate,
                channels=self.channels,
                blocksize=self.blocksize,
                dtype="float32",
                device=self.device_index,
                callback=self._audio_callback,
            )
            self.stream.start()
            self.running = True
            print("✅ Shared microphone started")
        except Exception as e:
            print(f"❌ Failed to start shared microphone: {e}")
            raise

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            print(f"⚠️ Mic status: {status}")

        # Use LEFT channel only, similar to your manual `sox remix 1`
        mono = indata[:, 0].copy()

        rms = float(np.sqrt(np.mean(np.square(mono)))) if len(mono) > 0 else 0.0

        with self.lock:
            self.level = rms

        self.chunk_queue.put(mono)

    def get_level(self):
        with self.lock:
            return self.level

    def drain_chunks(self):
        chunks = []
        while not self.chunk_queue.empty():
            try:
                chunks.append(self.chunk_queue.get_nowait())
            except queue.Empty:
                break
        return chunks

    def stop(self):
        self.running = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        print("🛑 Shared microphone stopped")


shared_mic = SharedMic()