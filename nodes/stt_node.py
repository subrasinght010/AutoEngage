# nodes/stt_node.py

import whisper
import sounddevice as sd
import numpy as np
from state.workflow_state import WorkflowState, lead_reducer

# Load Whisper Medium model (offline)
model = whisper.load_model("medium")

def stt_node(state: WorkflowState) -> WorkflowState:
    print("🎤 Listening for voice input... (chunked)")

    duration = 3  # seconds per audio chunk for near real-time
    samplerate = 16000
    recording = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=1)
    sd.wait()

    audio = np.squeeze(recording).astype(np.float32)
    result = model.transcribe(audio, fp16=False)
    text = result["text"].strip()
    print("STT Result:", text)

    # Update conversation thread
    updates = {
        "conversation_thread": state.conversation_thread + [f"User (voice): {text}"],
        "pending_action": "intent_detector_llm"
    }

    return lead_reducer(state, updates)
