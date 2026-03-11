import queue
import threading

import numpy as np
import sounddevice as sd


class SharedMic:
    def __init__(self, samplerate=16000, channels=1, blocksize=1600, device=None):
        self.samplerate = samplerate
        self.channels = channels
        self.blocksize = blocksize
        self.device = device

        self.stream = None
        self.running = False
        self.level = 0.0
        self.lock = threading.Lock()
        self.chunk_queue = queue.Queue()

    def start(self):
        if self.running:
            return

        self.stream = sd.InputStream(
            samplerate=self.samplerate,
            channels=self.channels,
            blocksize=self.blocksize,
            dtype="float32",
            device=self.device,
            callback=self._audio_callback,
        )
        self.stream.start()
        self.running = True
        print("✅ Shared microphone started")

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            print(f"⚠️ Mic status: {status}")

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