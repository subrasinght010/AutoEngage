import asyncio
from asyncio.log import logger
import whisper
import numpy as np
import io
import torch
import tempfile
import pygame
import subprocess
from scipy.io.wavfile import read
import noisereduce as nr
from gtts import gTTS

device = "cuda" if torch.cuda.is_available() else "cpu"

model = whisper.load_model("base").to(device)

async def text_to_speech(text):
    try:
        tts = gTTS(text=text, lang="en")
        audio_stream = io.BytesIO()
        tts.write_to_fp(audio_stream)
        audio_stream.seek(0)

        pygame.mixer.init()
        pygame.mixer.music.load(audio_stream, "mp3")
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)

        audio_stream.seek(0)
        return audio_stream.read()

    except Exception as e:
        print(f"Error occurred during text-to-speech conversion: {e}")
        return None

def process_audio_stream(audio_bytes):
    print("📥 Starting audio stream processing...")

    audio_buffer = io.BytesIO(audio_bytes)
    sample_rate, audio_data = read(audio_buffer)
    print(f"🎚️ Sample Rate: {sample_rate}, Audio Shape: {audio_data.shape}")

    try:
        audio_tensor = torch.tensor(audio_data, dtype=torch.float32).to(device) / 32768.0
        audio_tensor = whisper.pad_or_trim(audio_tensor)
        print(f"🔁 Padded/Trimmed Tensor Shape: {audio_tensor.shape}")

        mel = whisper.log_mel_spectrogram(audio_tensor).to(device)
        print(f"📊 Mel Spectrogram Shape: {mel.shape}")

        result = model.transcribe(mel, language="hi")
        print(f"📝 Transcription Result: {result}")

        return result.get("text", "")
    except Exception as e:
        print(f"❌ Error in process_audio_stream: {e}")
        return ""


async def denoise_audio(audio_bytes: bytes) -> bytes:
    try:
        if not audio_bytes or len(audio_bytes) < 2048:
            logger.warning("⚠️ Skipping denoise due to small or empty chunk")
            return audio_bytes

        audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)

        if np.all(audio_np == 0) or np.max(np.abs(audio_np)) < 100:
            logger.info("🔇 Skipping denoise for silent/low-energy audio")
            return audio_bytes

        reduced_noise = nr.reduce_noise(y=audio_np, sr=16000)
        return reduced_noise.astype(np.int16).tobytes()

    except Exception as e:
        logger.error(f"❌ Error during noise reduction: {e}")
        return audio_bytes

if __name__ == "__main__":
    asyncio.run(text_to_speech("Patani, kuch tts kaam ni kar rai, kyu ki Hindi me akshay kaam ni kar te English language me akshay kaam par rai, dey ar working good in English language, but they are not able to work in Hindi language. So please suggest me some other tts model which work on really well on the Hindi language. Mainly I focus on the English, which is the English and the combination. Thank you"))