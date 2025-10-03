import asyncio
import io
import tempfile
import torch
import numpy as np
import soundfile as sf
import whisper
import os

# -------------------------------
# Device and Model
# -------------------------------
device = "cuda" if torch.cuda.is_available() else "cpu"
model = whisper.load_model("medium").to('cpu')  # Use 'cpu' or 'cuda'

# -------------------------------
# Utilities
# -------------------------------
async def ensure_pcm_bytes(audio_bytes: bytes, target_rate: int = 16000) -> bytes:
    """Ensure audio bytes are PCM16 at target sample rate."""
    try:
        arr = np.frombuffer(audio_bytes, dtype=np.int16)
        if arr.ndim > 1:
            arr = arr[:, 0]
        return arr.tobytes()
    except Exception:
        pass

    try:
        audio_np, sr = sf.read(io.BytesIO(audio_bytes))
        if audio_np.ndim > 1:
            audio_np = audio_np[:, 0]

        if sr != target_rate:
            import librosa
            audio_np = librosa.resample(audio_np.astype(np.float32), orig_sr=sr, target_sr=target_rate)
            audio_np = (audio_np * 32767).astype(np.int16)
        elif audio_np.dtype != np.int16:
            audio_np = (audio_np * 32767).astype(np.int16)

        return audio_np.tobytes()
    except Exception as e:
        print(f"❌ Failed to convert to PCM16: {e}")
        return audio_bytes


# -------------------------------
# Transcription
# -------------------------------
# async def transcribe_with_faster_whisper(audio_bytes: bytes, sample_rate: int = 16000, save_path: str = None) -> str:
#     """Transcribe audio bytes using Whisper. Optionally save audio."""
#     try:
#         with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp_file:
#             audio_np = np.frombuffer(audio_bytes, dtype=np.int16)
#             sf.write(tmp_file.name, audio_np, sample_rate)
#             result = model.transcribe(tmp_file.name, language="hi")
#             return result.get("text", "")
#     except Exception as e:
#         print(f"❌ Transcription error: {e}")
#         return ""
    
async def transcribe_with_faster_whisper(audio_bytes: bytes, sample_rate: int = 16000) -> str:
    """Transcribe Float32 audio bytes directly using OpenAI Whisper."""
    try:
        # Convert Float32 bytes to numpy array
        audio_np = np.frombuffer(audio_bytes, dtype=np.float32)
        
        # Make array writable (fixes the PyTorch warning)
        audio_np = audio_np.copy()
        
        # OpenAI Whisper returns a dict, not tuple
        result = model.transcribe(audio_np, language="en", fp16=False)
        
        return result.get("text", "").strip()
        
    except Exception as e:
        print(f"❌ Transcription error: {e}")
        import traceback
        traceback.print_exc()
        return ""

# -------------------------------
# Test Speech-to-Text
# -------------------------------
async def test_speech_to_text():
    """Test speech-to-text with a sample WAV file."""
    try:
        sample_file = "/Users/subrat/Desktop/Agent/audio_data/audio_20251003_013131.wav"
        save_file = "/Users/subrat/Desktop/Agent/audio_data/audio_20250930_212355.wav"

        audio_np, sr = sf.read(sample_file, dtype="int16")
        print(f"🎚️ Loaded sample audio: {sample_file}, Sample Rate: {sr}, Shape: {audio_np.shape}")

        pcm_bytes = audio_np.tobytes()
        transcription = await transcribe_with_faster_whisper(pcm_bytes, sample_rate=sr, save_path=save_file)
        print(f"📝 Transcription Result: {transcription}")

    except Exception as e:
        print(f"❌ Error in test_speech_to_text: {e}")

# -------------------------------
# Run Test
# -------------------------------
if __name__ == "__main__":
    asyncio.run(test_speech_to_text())
