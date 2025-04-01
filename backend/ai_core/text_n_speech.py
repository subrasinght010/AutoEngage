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
model = whisper.load_model("small").to(device)

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

async def denoise_audio(audio_bytes):
    """Reduces noise in an audio byte stream."""
    audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
    reduced_noise = nr.reduce_noise(y=audio_np, sr=16000)
    return reduced_noise.astype(np.int16).tobytes()

# Example usage
if __name__ == "__main__":
    text_to_speech("Hello, I am speaking in real-time!")
