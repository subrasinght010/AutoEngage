# nodes/incoming_listener.py
"""
Incoming Listener Node - Handles ALL user inputs with proper type detection
Step 1: Detect input type (Message, Web Call, Twilio Call)
Step 2: Route to appropriate handler
"""

import asyncio
from enum import Enum
from typing import Optional, Dict, Any
from state.workflow_state import WorkflowState, lead_reducer
from tools.db_client import get_lead_by_id
from datetime import datetime
from nodes.intent_detector import intent_detector_llm
from nodes.communication_agent import communication_agent
from tools.language_model import LanguageModel
from nodes.tts_node import generate_audio


class InputType(Enum):
    """Types of incoming inputs"""
    MESSAGE = "message"           # SMS, WhatsApp, Email
    WEB_CALL = "web_call"        # Voice call via WebSocket
    TWILIO_CALL = "twilio_call"  # Voice call via Twilio


# ==================== STEP 1: DETECT INPUT TYPE ====================

def detect_input_type(message_data: dict, websocket=None) -> InputType:
    """
    Step 1: Detect if incoming request is Message, Web Call, or Twilio Call
    
    Args:
        message_data: Request payload
        websocket: WebSocket connection (presence indicates web call)
    
    Returns:
        InputType enum
    """
    channel = message_data.get("channel", "").lower()
    
    # Check for explicit channel type
    if channel in ["sms", "whatsapp", "email"]:
        print(f"✅ Detected: MESSAGE ({channel})")
        return InputType.MESSAGE
    
    # Check for Twilio-specific indicators
    if channel == "twilio_call" or "CallSid" in message_data or "From" in message_data.get("twilio_data", {}):
        print(f"✅ Detected: TWILIO_CALL")
        return InputType.TWILIO_CALL
    
    # Check for web call indicators
    if channel in ["call", "voice", "web_call"] or websocket is not None:
        print(f"✅ Detected: WEB_CALL")
        return InputType.WEB_CALL
    
    # Default: treat as message
    print(f"⚠️ Unknown channel '{channel}', defaulting to MESSAGE")
    return InputType.MESSAGE


# ==================== STEP 2: HANDLE MESSAGES ====================

async def handle_message(state: WorkflowState, message_data: dict) -> WorkflowState:
    """
    Step 2: Handle text messages (SMS, WhatsApp, Email)
    Immediately forwards to Communication Node
    
    Args:
        state: Current workflow state
        message_data: Message content
    
    Returns:
        Updated workflow state
    """
    lead_id = message_data.get("lead_id")
    message_text = message_data.get("message", "")
    channel = message_data.get("channel", "unknown")
    
    print(f"📨 Handling MESSAGE from {lead_id} via {channel}")
    
    # Fetch lead data
    lead_record = get_lead_by_id(lead_id)
    
    if lead_record:
        client_type = "existing"
        conversation_thread = lead_record.get("conversation_thread", [])
    else:
        client_type = "new"
        conversation_thread = []
    
    # Update state
    state = lead_reducer(state, {
        "lead_id": lead_id,
        "lead_data": lead_record or {"id": lead_id},
        "client_type": client_type,
        "conversation_thread": conversation_thread + [
            f"[{datetime.now().isoformat()}] User via {channel}: {message_text}"
        ],
        "preferred_channel": channel
    })
    
    # Run intent detection (includes AI response generation)
    print(f"➡️ Forwarding to Intent Detector...")
    state = intent_detector_llm(state)
    
    # Forward to Communication Node to send response
    print(f"➡️ Forwarding to Communication Agent...")
    state = communication_agent(state)
    
    return state


# ==================== STEP 3 & 4: HANDLE WEB CALLS ====================

async def handle_web_call(state: WorkflowState, message_data: dict, websocket) -> WorkflowState:
    """
    Step 3 & 4: Handle Web Call via WebSocket (Non-Twilio)
    
    Flow:
    1. Audio already captured by WebSocket (done in main.py)
    2. Audio transcribed by STT (done in utils/audio.py)
    3. Generate AI response immediately (FAST PATH)
    4. Run intent detection in parallel (SLOW PATH)
    
    Args:
        state: Current workflow state
        message_data: Contains transcription and audio_bytes
        websocket: Active WebSocket connection
    
    Returns:
        Updated workflow state
    """
    lead_id = message_data.get("lead_id")
    transcription = message_data.get("message")  # Already transcribed text
    
    print(f"📞 Handling WEB_CALL from {lead_id}")
    
    if not transcription or not transcription.strip():
        print("⚠️ No transcription - skipping")
        return state
    
    # Fetch lead data
    lead_record = get_lead_by_id(lead_id)
    
    if lead_record:
        client_type = "existing"
        conversation_thread = lead_record.get("conversation_thread", [])
    else:
        client_type = "new"
        conversation_thread = []
    
    # Update state with user message
    state = lead_reducer(state, {
        "lead_id": lead_id,
        "lead_data": lead_record or {"id": lead_id},
        "client_type": client_type,
        "conversation_thread": conversation_thread + [
            f"[{datetime.now().isoformat()}] User (voice): {transcription}"
        ],
        "preferred_channel": "web_call"
    })
    
    print(f"📝 Transcription: {transcription}")
    
    # **CRITICAL: Run in PARALLEL (Non-Blocking)**
    await asyncio.gather(
        generate_and_send_ai_response(state, transcription, websocket),  # IMMEDIATE
        run_intent_detection_async(state, transcription)                 # ASYNC
    )
    
    return state


# ==================== STEP 5: HANDLE TWILIO CALLS (PLACEHOLDER) ====================

async def handle_twilio_call(state: WorkflowState, message_data: dict) -> WorkflowState:
    """
    Step 5: Handle Twilio Call (Future Implementation)
    
    Twilio Flow (to be implemented):
    1. Receive Twilio webhook with CallSid
    2. Connect to Twilio Media Stream
    3. Capture audio from Twilio
    4. Process through STT → LLM → TTS
    5. Send audio back to Twilio
    
    Args:
        state: Current workflow state
        message_data: Twilio webhook data
    
    Returns:
        Updated workflow state
    """
    print("📞 TWILIO_CALL detected - PLACEHOLDER (Not implemented yet)")
    
    call_sid = message_data.get("CallSid")
    from_number = message_data.get("From")
    to_number = message_data.get("To")
    
    print(f"  CallSid: {call_sid}")
    print(f"  From: {from_number}")
    print(f"  To: {to_number}")
    
    # TODO: Implement Twilio integration
    # 1. Setup Twilio Media Stream
    # 2. Handle audio streaming
    # 3. Process through same STT → LLM → Intent pipeline
    # 4. Return TwiML response
    
    state = lead_reducer(state, {
        "lead_id": from_number,
        "preferred_channel": "twilio_call",
        "twilio_call_sid": call_sid,
        "pending_action": "twilio_call_handler"
    })
    
    return state


# ==================== AI RESPONSE GENERATION (IMMEDIATE) ====================

async def generate_and_send_ai_response(state: WorkflowState, user_input: str, websocket) -> None:
    """
    Generate AI response and send immediately via WebSocket
    This is the FAST PATH - must not block
    """
    try:
        print(f"🤖 Generating immediate AI response...")
        
        # Initialize LLM
        llm = LanguageModel()
        
        # Build conversation context
        recent_history = state.conversation_thread[-5:] if len(state.conversation_thread) > 5 else state.conversation_thread
        conversation_context = "\n".join(recent_history)
        
        # Generate AI text response
        prompt = f"""You are a helpful AI voice assistant. Respond naturally and conversationally.

**Conversation History:**
{conversation_context}

**User:** {user_input}

**Respond naturally in 1-2 sentences:**"""
        
        ai_text = await asyncio.to_thread(llm.generate, prompt, max_tokens=150)
        print(f"💬 AI Response: {ai_text}")
        
        # Convert to audio (TTS)
        audio_response = await asyncio.to_thread(generate_audio, ai_text)
        
        # Send audio to user immediately
        if websocket and websocket.application_state.value == 1:  # CONNECTED
            await websocket.send_bytes(audio_response)
            print("🔊 AI audio response sent to user")
        
        # Update conversation thread
        state.conversation_thread.append(
            f"[{datetime.now().isoformat()}] AI: {ai_text}"
        )
        
    except Exception as e:
        print(f"❌ AI response generation error: {e}")
        import traceback
        traceback.print_exc()


# ==================== INTENT DETECTION (ASYNC) ====================

async def run_intent_detection_async(state: WorkflowState, user_input: str) -> None:
    """
    Run intent detection asynchronously in parallel
    Does NOT block AI response
    """
    try:
        print(f"🔍 Running intent detection (async, non-blocking)...")
        
        # Run intent detector in thread pool
        intent_state = await asyncio.to_thread(intent_detector_llm, state)
        
        # Extract results
        intent = intent_state.get("intent_detected")
        actions = intent_state.get("actions_to_execute", [])
        
        print(f"🎯 Intent detected: {intent}")
        print(f"⚡ Actions to execute: {actions}")
        
        # Execute workflow actions based on intent
        await execute_workflow_actions(intent_state, actions)
        
    except Exception as e:
        print(f"❌ Intent detection error: {e}")
        import traceback
        traceback.print_exc()


# ==================== WORKFLOW ACTION EXECUTOR ====================

async def execute_workflow_actions(state: WorkflowState, actions: list) -> None:
    """
    Execute workflow actions based on detected intent
    Runs in background without blocking user response
    """
    if not actions:
        print("ℹ️ No actions to execute")
        return
    
    print(f"⚡ Executing {len(actions)} workflow actions...")
    
    for action in actions:
        try:
            if action == "schedule_callback":
                from nodes.schedule_call import schedule_call_node
                await asyncio.to_thread(schedule_call_node, state)
                print("✅ Callback scheduled")
                
            elif action == "send_details_email":
                from nodes.communication_agent import send_email_details
                await asyncio.to_thread(send_email_details, state)
                print("✅ Email sent")
                
            elif action == "send_details_whatsapp":
                from nodes.communication_agent import send_whatsapp_details
                await asyncio.to_thread(send_whatsapp_details, state)
                print("✅ WhatsApp message sent")
                
            elif action == "update_database":
                from nodes.db_update import db_update_node
                await asyncio.to_thread(db_update_node, state)
                print("✅ Database updated")
                
            elif action == "escalate_to_human":
                print("🚨 Escalating to human agent...")
                # Add your escalation logic here
                
            else:
                print(f"⚠️ Unknown action: {action}")
                
        except Exception as e:
            print(f"❌ Action '{action}' failed: {e}")
            import traceback
            traceback.print_exc()


# ==================== MAIN ENTRY POINT ====================

async def incoming_listener(
    state: WorkflowState, 
    message_data: dict, 
    websocket=None
) -> WorkflowState:
    """
    Main entry point for Incoming Listener Node
    
    Steps:
    1. Detect input type (Message, Web Call, Twilio Call)
    2. Route to appropriate handler
    
    Args:
        state: Current workflow state
        message_data: Input data
        websocket: WebSocket connection (optional, only for web calls)
    
    Returns:
        Updated workflow state
    """
    print("\n" + "="*60)
    print("🎯 INCOMING LISTENER - Processing input")
    print("="*60)
    
    # STEP 1: Detect Input Type
    input_type = detect_input_type(message_data, websocket)
    
    # STEP 2 & 3: Route to appropriate handler
    if input_type == InputType.MESSAGE:
        # Handle text messages
        state = await handle_message(state, message_data)
    
    elif input_type == InputType.WEB_CALL:
        # Handle web calls via WebSocket
        state = await handle_web_call(state, message_data, websocket)
    
    elif input_type == InputType.TWILIO_CALL:
        # Handle Twilio calls (placeholder)
        state = await handle_twilio_call(state, message_data)
    
    print("="*60)
    print("✅ INCOMING LISTENER - Processing complete")
    print("="*60 + "\n")
    
    return state