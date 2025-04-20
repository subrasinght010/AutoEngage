import whisper

# Load the Whisper model
model = whisper.load_model("base")  # You can choose "base", "small", "medium", "large" based on your hardware

# Function to transcribe audio file
def transcribe_audio(file_path):
    # Transcribe the audio file using Whisper
    result = model.transcribe(file_path, language='en')  # You can try 'hi' if the audio is more in Hindi
    return result['text']

# Example usage
audio_file_path = "/Users/subrat/Desktop/Agent/AutoEngage/final_audio.wav"  # Replace with your audio file path
transcribed_text = transcribe_audio(audio_file_path)

print(f"Transcribed Text: {transcribed_text}")

# from pydub import AudioSegment
# import numpy as np
# import wave
# import struct

# def convert_to_mono(input_filename, output_filename):
#     """Convert stereo audio to mono and save it."""
#     audio = AudioSegment.from_wav(input_filename)
#     mono_audio = audio.set_channels(1).set_sample_width(2)  # Mono and 16-bit
#     mono_audio.export(output_filename, format="wav")

# def read_wave(filename):
#     """Read a .wav file and return audio data."""
#     with wave.open(filename, 'rb') as wf:
#         sample_rate = wf.getframerate()
#         frames = wf.readframes(wf.getnframes())
#     return frames, sample_rate

# def energy_of_frame(frame):
#     """Calculate the energy of a frame."""
#     # Unpack the frame as 16-bit PCM data
#     fmt = "%dh" % (len(frame) // 2)
#     samples = struct.unpack(fmt, frame)
    
#     # Calculate energy as the sum of squared amplitudes
#     energy = np.sum(np.array(samples)**2)
#     return energy

# def process_audio(filename, threshold=10000):
#     """Process the audio and detect speech based on energy threshold."""
#     audio_data, sample_rate = read_wave(filename)
#     frame_duration = 5  # Frame duration in ms
#     frame_size = int(sample_rate * frame_duration / 1000)  # Size of each frame in samples
    
#     # Iterate over the audio data in frames
#     for i in range(0, len(audio_data), frame_size):
#         frame = audio_data[i:i + frame_size]
#         if len(frame) < frame_size:
#             continue  # Skip incomplete frames
        
#         energy = energy_of_frame(frame)
#         if energy > threshold:
#             print("Speech detected!")
#         else:
#             print("Silence detected!")

# # Example usage
# input_audio = "/Users/subrat/Desktop/Agent/AutoEngage/final_audio.wav"
# mono_audio = "/Users/subrat/Desktop/Agent/AutoEngage/output_mono_1.wav"

# # Convert to mono if needed
# convert_to_mono(input_audio, mono_audio)

# # Process the audio to detect speech
# process_audio(mono_audio)
