import numpy as np
import soundfile as sf
import matplotlib.pyplot as plt

# Load the audio file
audio_path = "/Users/subrat/Desktop/Agent/AutoEngage/vad_audio_on_disconnect.wav"
y, sr = sf.read(audio_path)

# Compute basic statistics
duration = len(y) / sr
mean_amplitude = np.mean(np.abs(y))
max_amplitude = np.max(np.abs(y))
energy = np.sum(y**2) / len(y)

# Plot waveform
plt.figure(figsize=(12, 4))
plt.plot(np.linspace(0, duration, num=len(y)), y, alpha=0.6)
plt.title("Waveform of Received Audio")
plt.xlabel("Time (s)")
plt.ylabel("Amplitude")
plt.show()

print(f"Duration: {duration:.2f} sec")
print(f"Mean Amplitude: {mean_amplitude:.5f}")
print(f"Max Amplitude: {max_amplitude:.5f}")
print(f"Energy: {energy:.5f}")
