# main.py
from fastapi import FastAPI, Request
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from state.workflow_state import WorkflowState, lead_reducer
from nodes.incoming_listener import incoming_listener
from nodes.schedule_call import schedule_call_node, execute_call_node
from nodes.db_update import db_update_node
from nodes.communication_agent import communication_agent
from nodes.intent_detector import intent_detector_llm
from nodes.follow_up import follow_up_node
from nodes.stt_node import stt_node
from nodes.tts_node import tts_node
from tools.db_client import get_lead_by_id, get_leads_for_followup

app = FastAPI(title="Multi-Agent Communication System")

# -----------------------------
# Scheduler (background)
# -----------------------------
scheduler = BackgroundScheduler()
scheduler.start()

# -----------------------------
# Auto Follow-ups Scheduler
# -----------------------------
def auto_followups():
    """
    Periodically triggered task to process leads pending follow-up.
    """
    print("⏰ Running auto-followups...")
    leads = get_leads_for_followup()  # fetch leads from DB

    for lead in leads:
        lead_id = lead.get("id")
        if not lead_id:
            continue

        try:
            print(f"➡️ Processing lead {lead_id}")
            state_updates = {
                "lead_id": lead_id,
                "lead_data": lead,
                "preferred_channel": lead.get("preferred_channel", "call"),
                "follow_up_time": lead.get("next_action_time", datetime.now().isoformat()),
                "conversation_thread": lead.get("conversation_thread", []) + [
                    f"[{datetime.now().isoformat()}] Auto follow-up triggered"
                ],
                "pending_action": lead.get("pending_action", "follow_up_node"),
            }

            state = lead_reducer(WorkflowState(), state_updates)

            # Execute node based on pending_action
            if state.pending_action == "execute_call_node":
                state = execute_call_node(state)
            elif state.pending_action == "follow_up_node":
                state = follow_up_node(state)

            # Update DB
            _ = db_update_node(state)

        except Exception as e:
            print(f"⚠️ Error processing lead {lead_id}: {e}")

# Schedule periodic job every 1 minute
scheduler.add_job(auto_followups, 'interval', minutes=1)

# -----------------------------
# Generic Incoming Handler
# -----------------------------
async def handle_incoming(message_data: dict) -> WorkflowState:
    """
    Unified handler for incoming events (call, email, whatsapp, voice).
    Returns updated per-lead WorkflowState.
    """
    channel = message_data.get("channel")
    voice_file_url = message_data.get("voice_file_url")
    state = WorkflowState()  # fresh per-lead state

    # Incoming listener
    state = incoming_listener(state, message_data)

    # STT processing for voice
    if channel in ["call", "voice"] and voice_file_url:
        try:
            print(f"🎤 Running STT for audio: {voice_file_url}")
            state = stt_node(state, voice_file_url)
        except Exception as e:
            print(f"⚠️ STT error: {e}")

    # LLM intent detection
    state = intent_detector_llm(state)

    # Communication agent
    state = communication_agent(state)

    # DB logging
    state = db_update_node(state)

    # Schedule next steps
    state = schedule_call_node(state)

    # TTS for voice channels
    if channel in ["call", "voice"]:
        try:
            state = tts_node(state)
        except Exception as e:
            print(f"⚠️ TTS error: {e}")

    return state

# -----------------------------
# Webhooks
# -----------------------------
@app.post("/webhook/call")
async def webhook_call(request: Request):
    data = await request.json()
    message_data = {
        "lead_id": data.get("caller"),
        "message": data.get("transcript") or "Incoming call",
        "channel": "call",
        "voice_file_url": data.get("recording_url") or data.get("voice_file_url")
    }
    state = await handle_incoming(message_data)
    return {"status": "call processed", "lead_id": state.lead_id}

@app.post("/webhook/email")
async def webhook_email(request: Request):
    data = await request.json()
    message_data = {
        "lead_id": data.get("from"),
        "message": f"{data.get('subject', '')}: {data.get('body', '')}",
        "channel": "email"
    }
    state = await handle_incoming(message_data)
    return {"status": "email processed", "lead_id": state.lead_id}

@app.post("/webhook/whatsapp")
async def webhook_whatsapp(request: Request):
    data = await request.json()
    message_data = {
        "lead_id": data.get("from"),
        "message": data.get("message"),
        "channel": "whatsapp",
        "voice_file_url": data.get("voice_file_url")
    }
    state = await handle_incoming(message_data)
    return {"status": "whatsapp processed", "lead_id": state.lead_id}

# -----------------------------
# Manual Outgoing Trigger
# -----------------------------
@app.post("/trigger_outgoing")
async def trigger_outgoing(lead_id: str, channel: str = "call"):
    lead_record = get_lead_by_id(lead_id)
    if not lead_record:
        return {"status": "error", "message": "Lead not found"}

    state_updates = {
        "lead_id": lead_id,
        "lead_data": lead_record,
        "preferred_channel": channel,
        "pending_action": "execute_call_node",
        "conversation_thread": lead_record.get("conversation_thread", []) + [
            f"[{datetime.now().isoformat()}] Outgoing via {channel}"
        ]
    }

    state = lead_reducer(WorkflowState(), state_updates)
    state = execute_call_node(state)
    state = db_update_node(state)

    return {"status": "outgoing triggered", "lead_id": lead_id}

# -----------------------------
# Run Server
# -----------------------------
if __name__ == "__main__":
    import uvicorn
    import asyncio
    from database.db import init_db  # your async DB init

    async def main():
        # Initialize database before starting server
        await init_db()
        # Run the FastAPI server
        config = uvicorn.Config(app, host="0.0.0.0", port=8001, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()

    # Run the async main function
    asyncio.run(main())
