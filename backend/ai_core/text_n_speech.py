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

# Set device
device = "cuda" if torch.cuda.is_available() else "cpu"

# Load Whisper model
model = whisper.load_model("tiny").to("cpu")  # Use "base" if "tiny" is too small

# Function to generate TTS and send it as a byte stream
async def text_to_speech(text):
    try:
        # Generate speech using gTTS (Google TTS)
        tts = gTTS(text=text, lang="en")  # You can change 'en' to any language code.
        audio_stream = io.BytesIO()  # Create a buffer to hold the audio
        tts.write_to_fp(audio_stream)  # Write the TTS audio to the buffer
        audio_stream.seek(0)  # Rewind the buffer to the start

        # Initialize Pygame for real-time audio playback
        pygame.mixer.init()
        pygame.mixer.music.load(audio_stream, "mp3")
        pygame.mixer.music.play()

        # Wait for playback to finish before returning
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)

        # Return the audio byte data to send through the WebSocket
        audio_stream.seek(0)  # Rewind the buffer to the start again before sending
        return audio_stream.read()

    except Exception as e:
        print(f"Error occurred during text-to-speech conversion: {e}")
        return None



def process_audio_stream(audio_bytes):
    """Process audio stream, convert to text using Whisper."""
    audio_buffer = io.BytesIO(audio_bytes)
    sample_rate, audio_data = read(audio_buffer)

    # Convert to float32 and normalize
    audio_tensor = torch.tensor(audio_data, dtype=torch.float32).to(device) / 32768.0  
    audio_tensor = whisper.pad_or_trim(audio_tensor)

    mel = whisper.log_mel_spectrogram(audio_tensor).to(device)
    result = model.transcribe(mel, language="hi")

    return result.get("text", "")



async def denoise_audio(audio_bytes: bytes) -> bytes:
    """
    Reduces noise in an audio byte stream using noisereduce.
    Includes checks for silent or invalid data to prevent runtime errors.
    """
    try:
        if not audio_bytes or len(audio_bytes) < 2048:
            logger.warning("⚠️ Skipping denoise due to small or empty chunk")
            return audio_bytes

        audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)

        # Avoid processing silent or invalid audio
        if np.all(audio_np == 0) or np.max(np.abs(audio_np)) < 100:
            logger.info("🔇 Skipping denoise for silent/low-energy audio")
            return audio_bytes

        reduced_noise = nr.reduce_noise(y=audio_np, sr=16000)
        return reduced_noise.astype(np.int16).tobytes()

    except Exception as e:
        logger.error(f"❌ Error during noise reduction: {e}")
        return audio_bytes  # Return original audio in case of error


# Example usage
if __name__ == "__main__":
    text_to_speech("Hello, I am speaking in real-time!")
