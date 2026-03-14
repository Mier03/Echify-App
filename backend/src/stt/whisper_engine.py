# whisper_engine.py
import torch
from typing import Optional
import os
import subprocess
from faster_whisper import WhisperModel


class WhisperEngine:
    def __init__(self, model_size="small.en"):
        self.device = "cpu"  # Change to "cuda" if using GPU
        print(f"🔊 Loading faster-whisper {model_size} on {self.device}")

        self.model = WhisperModel(
            model_size,
            device=self.device,
            compute_type="int8"  # Fast + efficient
        )

        torch.set_num_threads(1)

    def transcribe_file(self, audio_path: str):
        try:
            # NEW: Pre-process the file just like your mic_test.sh
            processed_path = audio_path.replace(".wav", "_clean.wav")
            
            # This command does the remix 1 and gain 5 automatically
            subprocess.run([
                "sox", audio_path, processed_path, 
                "remix", "1", "gain", "5"
            ], check=True)

            segments, _ = self.model.transcribe(processed_path, language="en")
            text = " ".join(seg.text.strip() for seg in segments)
            
            # Clean up the temp file
            if os.path.exists(processed_path):
                os.remove(processed_path)
                
            return text if text else None
        except Exception as e:
            print(f"Transcription error: {e}")
            return None
