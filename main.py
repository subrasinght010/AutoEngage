# main.py (CLEANED & MERGED)
import os
import sys
import json
import time
import traceback
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

import numpy as np
import soundfile as sf
import librosa  # if used elsewhere
from dotenv import load_dotenv

import jwt
import uvicorn

from fastapi import (
    FastAPI,
    Request,
    Response,
    Form,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.websockets import WebSocketState

from apscheduler.schedulers.background import BackgroundScheduler

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import Session

# Project imports (kept names from your original)
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
from backend.ai_core.text_n_speech import transcribe_with_faster_whisper
from backend.utilities import handle_call, hash_password, verify_password
from backend.curd import get_user_by_username

from database.db_setup import get_db, init_db
from database.models import User

# -------------------------
# Load env & constants
# -------------------------
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY", "default_secret_key")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

# -------------------------
# Logger setup
# -------------------------
logger = logging.getLogger("voice-app")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter("[%(asctime)s] %(message)s", "%Y-%m-%d %H:%M:%S")
handler.setFormatter(formatter)
logger.handlers.clear()
logger.addHandler(handler)
logger.propagate = False

# -------------------------
# FastAPI app
# -------------------------
app = FastAPI(title="Multi-Agent Communication System")
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
templates = Jinja2Templates(directory="frontend/templates")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------
# Auth utilities
# -------------------------
def create_jwt_token(username: str, expires_hours: int = 1) -> str:
    exp = datetime.utcnow() + timedelta(hours=expires_hours)
    payload = {"sub": username, "exp": exp.isoformat()}
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token

def verify_jwt_token(token: str) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # payload might store exp in isoformat string; handle both cases
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        return sub
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def require_auth(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/login", status_code=303)
    try:
        return verify_jwt_token(token)
    except HTTPException:
        return RedirectResponse(url="/login", status_code=303)

# -------------------------
# Audio helpers (kept both; clear names)
# -------------------------
def save_pcm_to_wav_44k(pcm_data: bytes, filename: str = "received_audio.wav", sample_rate: int = 44100) -> None:
    """
    Save 16-bit PCM bytes to a WAV file at 44.1 kHz
    """
    audio_array = np.frombuffer(pcm_data, dtype=np.int16)
    sf.write(filename, audio_array, sample_rate, subtype='PCM_16')

def save_pcm_to_wav_16k(pcm_data: bytes, filename: str = "received_audio_16.wav", sample_rate: int = 16000) -> None:
    """
    Save 16-bit PCM bytes to a WAV file at 16 kHz
    """
    audio_array = np.frombuffer(pcm_data, dtype=np.int16)
    sf.write(filename, audio_array, sample_rate, subtype='PCM_16')

# -------------------------
# Routes (auth + pages)
# -------------------------
@app.get("/")
async def root(request: Request):
    token = request.cookies.get("access_token")
    if token:
        try:
            verify_jwt_token(token)
            return RedirectResponse(url="/home", status_code=303)
        except HTTPException:
            pass
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/signup")
async def signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@app.get("/home", response_class=HTMLResponse)
async def home_page(
    request: Request,
    user=Depends(require_auth),              # returns username or RedirectResponse
    db: AsyncSession = Depends(get_db),
):
    if isinstance(user, RedirectResponse):
        return user

    user_obj = await get_user_by_username(db=db, username=user)
    if not user_obj:
        return HTMLResponse("User not found", status_code=404)

    return templates.TemplateResponse("index.html", {
        "request": request,
        "user_id": user_obj.id,
        "username": user_obj.username
    })

@app.post("/signup")
async def signup(
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    if password != confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    result = await db.execute(select(User).where(User.username == username))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Username already exists")

    new_user = User(username=username, password=hash_password(password))
    db.add(new_user)
    try:
        await db.commit()
        await db.refresh(new_user)
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal Server Error")

    return RedirectResponse(url="/login", status_code=303)

@app.post("/login")
async def login(
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.username == username))
    db_user = result.scalars().first()
    if db_user and verify_password(password, db_user.password):
        token = create_jwt_token(username)
        redirect_response = RedirectResponse(url="/", status_code=303)
        redirect_response.set_cookie(
            key="access_token",
            value=token,
            httponly=False,
            secure=False,
            samesite="Lax"
        )
        return redirect_response
    raise HTTPException(status_code=401, detail="Invalid credentials")

# -------------------------
# Scheduler: auto-followups
# -------------------------
scheduler = BackgroundScheduler()
scheduler.start()

def auto_followups():
    logger.info("⏰ Running auto-followups...")
    try:
        leads = get_leads_for_followup()  # synchronous helper per your codebase
    except Exception as e:
        logger.error(f"Failed to fetch leads for followup: {e}")
        return

    for lead in leads:
        lead_id = lead.get("id")
        if not lead_id:
            continue

        try:
            logger.info(f"➡️ Processing lead {lead_id}")
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
            logger.exception(f"⚠️ Error processing lead {lead_id}: {e}")

# schedule every 1 minute
scheduler.add_job(auto_followups, 'interval', minutes=1)

# -------------------------
# Generic incoming handler
# -------------------------
async def handle_incoming(message_data: Dict[str, Any]) -> WorkflowState:
    channel = message_data.get("channel")
    voice_file_url = message_data.get("voice_file_url")
    state = WorkflowState()  # fresh per-lead state

    # Incoming listener
    state = incoming_listener(state, message_data)

    # STT processing for voice
    if channel in ["call", "voice"] and voice_file_url:
        try:
            logger.info(f"🎤 Running STT for audio: {voice_file_url}")
            state = stt_node(state, voice_file_url)
        except Exception as e:
            logger.exception(f"⚠️ STT error: {e}")

    # LLM intent detection
    try:
        state = intent_detector_llm(state)
    except Exception as e:
        logger.exception(f"⚠️ Intent detection error: {e}")

    # Communication agent
    try:
        state = communication_agent(state)
    except Exception as e:
        logger.exception(f"⚠️ Communication agent error: {e}")

    # DB logging
    try:
        state = db_update_node(state)
    except Exception as e:
        logger.exception(f"⚠️ DB update error: {e}")

    # Schedule next steps
    try:
        state = schedule_call_node(state)
    except Exception as e:
        logger.exception(f"⚠️ Scheduling error: {e}")

    # TTS for voice channels
    if channel in ["call", "voice"]:
        try:
            state = tts_node(state)
        except Exception as e:
            logger.exception(f"⚠️ TTS error: {e}")

    return state

# -------------------------
# Webhook endpoints
# -------------------------
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

# -------------------------
# Manual outgoing trigger
# -------------------------
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

# -------------------------
# WebSocket: voice_chat
# -------------------------
SILENCE_TIMEOUT = 1  # seconds

@app.websocket("/voice_chat")
async def voice_chat(websocket: WebSocket, db: AsyncSession = Depends(get_db)):
    await websocket.accept()
    logger.info("🔗 WebSocket connected")

    lead_id: Optional[str] = None
    audio_data = b''
    last_chunk_time = datetime.utcnow()

    try:
        while True:
            try:
                message = await websocket.receive()

                # Text messages (control messages in JSON)
                if isinstance(message, dict) and "text" in message and message["text"]:
                    try:
                        data = json.loads(message["text"])
                    except json.JSONDecodeError:
                        logger.error(f"❌ JSON decoding failed: {message['text']}")
                        continue

                    msg_type = data.get("type")
                    if msg_type == "start_conversation":
                        lead_id = data.get("user_id")
                        if not lead_id:
                            logger.warning("⚠️ Missing user_id in start_conversation")
                            await websocket.close()
                            return
                        logger.info(f"🟢 Conversation started with {lead_id}")

                    elif msg_type == "end_conversation":
                        logger.info("🔴 Conversation ended by client")
                        break

                # Audio binary frames
                elif isinstance(message, dict) and "bytes" in message:
                    chunk = message["bytes"]
                    if len(chunk) % 2 != 0:
                        logger.warning("⚠️ Skipping invalid chunk due to odd byte count")
                        continue
                    audio_data += chunk
                    logger.info(f"🎙️ Received chunk - Raw: {len(chunk)} bytes")
                    last_chunk_time = datetime.utcnow()

                # Silence timeout handling
                if (datetime.utcnow() - last_chunk_time).total_seconds() > SILENCE_TIMEOUT:
                    if audio_data:
                        base_filename = f"audio_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.wav"
                        logger.info(f"💾 Saving audio with filename: {base_filename}")
                        # Save using 16k (if you prefer 44k, change to save_pcm_to_wav_44k)
                        save_pcm_to_wav_16k(audio_data, filename=base_filename)
                        # Transcribe
                        try:
                            transcription = await transcribe_with_faster_whisper(audio_data)
                            logger.info(f"📝 Transcription: {transcription}")
                            await websocket.send_json({"type": "transcription", "text": transcription})
                        except Exception as e:
                            logger.exception(f"❌ Transcription failed: {e}")

                        # Reset buffer
                        audio_data = b''

                    last_chunk_time = datetime.utcnow()

            except WebSocketDisconnect:
                logger.info("🚪 Client disconnected")
                break

            except Exception as e:
                logger.exception(f"❌ WebSocket error: {e}")
                break

    finally:
        try:
            # if using AsyncSession, close it
            if db:
                try:
                    await db.close()
                except Exception:
                    pass
        except Exception:
            pass

        if websocket.application_state != WebSocketState.DISCONNECTED:
            await websocket.close()

# -------------------------
# Startup event
# -------------------------
@app.on_event("startup")
async def startup_event():
    try:
        await init_db()
        logger.info("🚀 Database initialized")
    except Exception as e:
        logger.exception(f"❌ DB startup failed: {e}")

# -------------------------
# Main entry (single uvicorn invocation)
# -------------------------
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
