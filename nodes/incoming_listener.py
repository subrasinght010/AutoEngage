# nodes/incoming_listener.py

from state.workflow_state import WorkflowState, lead_reducer
from tools.db_client import get_lead_by_id  # Your DB helper
from datetime import datetime
from nodes.stt_node import stt_node
from nodes.tts_node import tts_node
from nodes.intent_detector import intent_detector_llm

def incoming_listener(state: WorkflowState, message_data: dict) -> WorkflowState:
    """
    Handles incoming messages or calls (voice or text).
    - Detects new or existing client
    - Captures voice if incoming call
    - Updates WorkflowState
    """

    lead_id = message_data.get("lead_id")
    incoming_message = message_data.get("message")  # text or None if voice
    channel = message_data.get("channel")           # "call", "whatsapp", "email", "voice"

    # -----------------------------
    # 1. Check DB for existing client
    # -----------------------------
    lead_record = get_lead_by_id(lead_id)  # Returns None if new client

    if lead_record:
        client_type = "existing"
        conversation_thread = lead_record.get("conversation_thread", [])
        thread_id = lead_record.get("thread_id")
    else:
        client_type = "new"
        conversation_thread = []
        thread_id = f"thread_{lead_id or 'new'}"

    # -----------------------------
    # 2. Handle voice call (STT)
    # -----------------------------
    if channel in ["call", "voice"]:
        print("🎤 Incoming voice call detected, running STT...")
        # stt_node will record and transcribe voice
        temp_state = lead_reducer(state, {
            "lead_id": lead_id,
            "lead_data": lead_record or {"id": lead_id},
            "client_type": client_type,
            "conversation_thread": conversation_thread,
            "thread_id": thread_id,
            "preferred_channel": channel
        })
        temp_state = stt_node(temp_state)
        transcribed_text = temp_state.conversation_thread[-1]  # last added message
        incoming_message = transcribed_text.split(": ", 1)[-1]  # Extract text
        conversation_thread = temp_state.conversation_thread

    # -----------------------------
    # 3. Prepare updates for WorkflowState
    # -----------------------------
    updates = {
        "lead_id": lead_id,
        "lead_data": lead_record or {"id": lead_id},
        "client_type": client_type,
        "pending_action": "intent_detector_llm",
        "conversation_thread": conversation_thread + [f"[{datetime.now().isoformat()}] Incoming via {channel}: {incoming_message}"],
        "thread_id": thread_id,
        "preferred_channel": channel
    }

    updated_state = lead_reducer(state, updates)

    # -----------------------------
    # 4. Run LLM intent detection
    # -----------------------------
    updated_state = intent_detector_llm(updated_state)

    # -----------------------------
    # 5. Optional: Run TTS if response is via voice
    # -----------------------------
    if updated_state.preferred_channel in ["call", "voice"]:
        updated_state = tts_node(updated_state)

    return updated_state
