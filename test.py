import soundfile as sf
import numpy as np
file_path ='/Users/subrat/Desktop/Agent/audio_data/audio_20251004_201421.wav'
# Read audio file into bytes
with open(file_path, 'rb') as f:
    audio_bytes = f.read()

# After saving a stretched file
info = sf.info(file_path)
print(f"Sample rate: {info.samplerate}")
print(f"Duration: {info.duration}")
print(f"Frames: {info.frames}")
print(f"Subtype: {info.subtype}")

# Calculate expected duration
audio_array = np.frombuffer(audio_bytes, dtype=np.float32)
expected_duration = len(audio_array) / 16000
print(f"Expected duration: {expected_duration}")



import soundfile as sf
import numpy as np
# file_path ='/Users/subrat/Desktop/Agent/audio_data/audio_20251004_133652.wav'
# Read audio file into bytes
with open(file_path, 'rb') as f:
    audio_bytes = f.read()

# After saving a stretched file
info = sf.info(file_path)
print(f"Sample rate: {info.samplerate}")
print(f"Duration: {info.duration}")
print(f"Frames: {info.frames}")
print(f"Subtype: {info.subtype}")

# Calculate expected duration
audio_array = np.frombuffer(audio_bytes, dtype=np.float32)
expected_duration = len(audio_array) / 16000
print(f"Expected duration: {expected_duration}")


from silero_vad import load_silero_vad, read_audio, get_speech_timestamps
model = load_silero_vad()
wav = read_audio(file_path)
speech_timestamps = get_speech_timestamps(wav, model, return_seconds=True)
print(speech_timestamps)
