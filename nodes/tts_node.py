# nodes/tts_node.py

import pyttsx3
from state.workflow_state import WorkflowState

tts_engine = pyttsx3.init()
tts_engine.setProperty('rate', 150)  # speaking rate

def tts_node(state: WorkflowState) -> WorkflowState:
    if not state.conversation_thread:
        return state

    # Get last agent response
    last_response = state.conversation_thread[-1]
    print("🔊 Agent Response:", last_response)

    # Convert text to speech
    tts_engine.say(last_response)
    tts_engine.runAndWait()

    return state
