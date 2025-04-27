import torch
import numpy as np
import time
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)

class AudioBuffer:
    def __init__(self, chunk_size: int = 512):
        """
        Buffer to accumulate and split audio data into fixed-size numpy chunks.
        Default 512 samples (~32ms at 16kHz).
        """
        self.chunk_size = chunk_size
        self.buffer = np.array([], dtype=np.int16)

    def add_data(self, data: np.ndarray):
        """Append new audio data to the buffer."""
        if not isinstance(data, np.ndarray):
            raise ValueError("Data must be a numpy ndarray")
        self.buffer = np.concatenate((self.buffer, data))

    def get_chunks(self) -> List[np.ndarray]:
        """Yield fixed-size numpy chunks from the buffer."""
        chunks = []
        while len(self.buffer) >= self.chunk_size:
            chunk = self.buffer[:self.chunk_size]
            chunks.append(chunk)
            self.buffer = self.buffer[self.chunk_size:]
        return chunks

    def flush(self) -> Optional[np.ndarray]:
        """Flush any remaining data."""
        if self.buffer.size > 0:
            data = self.buffer
            self.buffer = np.array([], dtype=np.int16)
            return data
        return None


class RealTimeSileroVAD:
    def __init__(self, model_path: str, sample_rate: int = 16000, silence_timeout: float = 3.0):
        self.sample_rate = sample_rate
        self.silence_timeout = silence_timeout
        self.model = torch.jit.load(model_path).eval()

        # Adjusted to use 512 samples (32ms) for 16kHz audio
        self.required_samples = 512 if self.sample_rate == 16000 else 256  # 256 for 8kHz

        self.reset()

    def reset(self):
        """Reset VAD state."""
        self.state = torch.zeros(2, 1, 128, dtype=torch.float32)
        self.sr_tensor = torch.tensor([self.sample_rate], dtype=torch.int64)
        self.speech_started = False
        self.last_voice_time = None
        self.voice_buffer = []
        self.pending_audio = np.array([], dtype=np.int16)

    def _prepare_audio_chunk(self, audio_chunk: np.ndarray) -> Optional[torch.Tensor]:
        """Buffer incoming audio until enough samples are collected."""
        self.pending_audio = np.concatenate((self.pending_audio, audio_chunk))

        if len(self.pending_audio) < self.required_samples:
            return None  # Not enough data yet

        # Take only needed samples
        chunk_samples = self.pending_audio[:self.required_samples]
        self.pending_audio = self.pending_audio[self.required_samples:]  # Keep leftovers

        # Convert to float32 and normalize
        audio_float = chunk_samples.astype(np.float32) / 32768.0
        audio_tensor = torch.from_numpy(audio_float).unsqueeze(0)

        return audio_tensor

    def process_chunk(self, audio_chunk: np.ndarray) -> Optional[np.ndarray]:
        """Process small incoming numpy chunks; return full speech buffer when finished."""
        try:
            audio_tensor = self._prepare_audio_chunk(audio_chunk)
            if audio_tensor is None:
                return None  # Still collecting enough data

            with torch.no_grad():
                is_speech = self.model(audio_tensor, self.sr_tensor).item() > 0.5

        except Exception as e:
            logger.error(f"❌ VAD processing error: {e}")
            return None

        now = time.time()

        if is_speech:
            if not self.speech_started:
                self.speech_started = True
                logger.info("🟢 Speech started")
            self.last_voice_time = now
            self.voice_buffer.append(audio_chunk)
        elif self.speech_started:
            if self.last_voice_time and (now - self.last_voice_time) > self.silence_timeout:
                logger.info("🔴 Speech ended (timeout reached)")
                full_audio = np.concatenate(self.voice_buffer) if self.voice_buffer else None
                self.reset()
                return full_audio

        return None
