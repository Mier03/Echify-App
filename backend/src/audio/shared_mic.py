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
        device_index=None,      # auto-detect
    ):
        self.samplerate = samplerate
        self.channels = channels
        self.blocksize = blocksize
        self.device_index = device_index

        self.stream = None
        self.running = False
        self.level = 0.0
        self.lock = threading.Lock()
        self.chunk_queue = queue.Queue()

    def _find_voicehat_device(self) -> int:
        """
        Scan sounddevice list for Google VoiceHAT on card 1 or card 2.
        Returns the device index if found, raises RuntimeError if not.
        """
        devices = sd.query_devices()
        print("🎤 Available audio devices:")
        print(devices)

        # Keywords that identify the VoiceHAT mic
        keywords = ["googlevoicehat", "google voicehat", "voicehat", "googevoicehat"]

        for i, dev in enumerate(devices):
            name = dev["name"].lower().replace(" ", "").replace("-", "")
            has_input = dev["max_input_channels"] > 0
            is_voicehat = any(k.replace(" ", "") in name for k in keywords)

            if has_input and is_voicehat:
                print(f"✅ Found VoiceHAT mic at device index {i}: {dev['name']}")
                return i

        # Fallback: try card 1 and card 2 directly by checking ALSA hw names
        print("⚠️ VoiceHAT not found by name, trying card 1 and card 2...")
        for i, dev in enumerate(devices):
            name = dev["name"].lower()
            has_input = dev["max_input_channels"] > 0
            is_card1_or_2 = "hw:1" in name or "hw:2" in name or \
                            "card 1" in name or "card 2" in name

            if has_input and is_card1_or_2:
                print(f"✅ Found input device at index {i}: {dev['name']}")
                return i

        # Last resort: try index 1 then 2 directly
        print("⚠️ Fallback: probing device index 1 and 2 directly...")
        for idx in [1, 2]:
            try:
                dev = sd.query_devices(idx)
                if dev["max_input_channels"] > 0:
                    print(f"✅ Using device index {idx}: {dev['name']}")
                    return idx
            except Exception:
                continue

        raise RuntimeError(
            "❌ Could not find Google VoiceHAT microphone on card 1 or card 2. "
            "Check physical connection on the 40-pin header."
        )

    def start(self):
        if self.running:
            return

        try:
            # Auto-detect if no device_index was specified
            if self.device_index is None:
                self.device_index = self._find_voicehat_device()

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
            print(f"✅ Shared microphone started on device index {self.device_index}")
        except Exception as e:
            print(f"❌ Failed to start shared microphone: {e}")
            raise

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            print(f"⚠️ Mic status: {status}")

        mono = indata[:, 0].copy() * 5.0
        mono = np.clip(mono, -1.0, 1.0)

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