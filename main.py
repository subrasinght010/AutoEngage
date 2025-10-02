# main.py (CLEANED & MERGED)
import asyncio
import os
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

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
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.websockets import WebSocketState


from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

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
from utils.utilities import  AudioValidator, check_silence_loop, handle_audio_chunk, handle_text_message, hash_password, process_audio, verify_password
from database.crud import DBManager

from database.db import get_db, init_db
from database.models import User
from contextlib import asynccontextmanager


# -------------------------
# Load env & constants
# -------------------------
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY", "access_token")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")


# -------------------------
# FastAPI app
# -------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await init_db()
        print("🚀 Database initialized")
        yield
    finally:
        # Optional shutdown logic
        print("🛑 App shutting down")

app = FastAPI(title="Multi-Agent Communication System" ,lifespan=lifespan)
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
    exp = datetime.now(timezone.utc) + timedelta(hours=expires_hours)  # timezone-aware
    payload = {"sub": username, "exp": exp}  # pyjwt accepts datetime with tzinfo
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token


def verify_jwt_token(token: str) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Ensure 'sub' exists
        sub = payload.get("sub")
        if not sub:
            print("❌ Invalid token payload: missing 'sub'")
            raise HTTPException(status_code=401, detail="Invalid token payload")
        
        # Handle expiration safely
        exp = payload.get("exp")
        if exp is None:
            print("❌ Invalid token payload: missing 'exp'")
            raise HTTPException(status_code=401, detail="Invalid token payload")

        # Convert exp to datetime if needed
        if isinstance(exp, int) or isinstance(exp, float):
            exp_datetime = datetime.fromtimestamp(exp, tz=timezone.utc)
        elif isinstance(exp, str):
            # Parse ISO string if your token uses isoformat
            exp_datetime = datetime.fromisoformat(exp)
            if exp_datetime.tzinfo is None:
                exp_datetime = exp_datetime.replace(tzinfo=timezone.utc)
        else:
            exp_datetime = exp  # assume datetime object

        if datetime.now(timezone.utc) > exp_datetime:
            print("❌ Token has expired")
            raise HTTPException(status_code=401, detail="Token has expired")

        return sub

    except jwt.ExpiredSignatureError:
        print("❌ Token has expired (jwt)")
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        print("❌ Invalid token")
        raise HTTPException(status_code=401, detail="Invalid token")


async def require_auth(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        print("❌ No access token found in cookies")
        return RedirectResponse(url="/login", status_code=303)
    try:
        return verify_jwt_token(token)
    except HTTPException:
        return RedirectResponse(url="/login", status_code=303)

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

    user_obj = await DBManager(session=db).get_user_by_username(username=user)
    print(f"🏠 Home page accessed by user: {user_obj.username if user_obj else 'Unknown'}")
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
    async with db.begin():  # Ensures proper session handling
        result = await db.execute(select(User).where(User.username == username))
        db_user = result.scalars().first()

        print(f"🔑 Login attempt for user: {username}")

        if db_user and verify_password(password, db_user.password):
            print(f"✅ User {username} authenticated successfully")
            token = create_jwt_token(username)

            redirect_response = RedirectResponse(url="/", status_code=303)
            redirect_response.set_cookie(
                key="access_token",
                value=token,
                httponly=True,   # safer
                secure=False,
                samesite="Lax"
            )
            return redirect_response

    # If we reach here, login failed
    raise HTTPException(status_code=401, detail="Invalid credentials")


# -------------------------
# Scheduler: auto-followups
# -------------------------
# scheduler = BackgroundScheduler()
# scheduler.start()

def auto_followups():
    print("⏰ Running auto-followups...")
    try:
        leads = get_leads_for_followup()  # synchronous helper per your codebase
    except Exception as e:
        print(f"Failed to fetch leads for followup: {e}")
        return

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

# schedule every 1 minute
# scheduler.add_job(auto_followups, 'interval', minutes=1)

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
            print(f"🎤 Running STT for audio: {voice_file_url}")
            state = stt_node(state, voice_file_url)
        except Exception as e:
            print(f"⚠️ STT error: {e}")

    # LLM intent detection
    try:
        state = intent_detector_llm(state)
    except Exception as e:
        print(f"⚠️ Intent detection error: {e}")

    # Communication agent
    try:
        state = communication_agent(state)
    except Exception as e:
        print(f"⚠️ Communication agent error: {e}")

    # DB logging
    try:
        state = db_update_node(state)
    except Exception as e:
        print(f"⚠️ DB update error: {e}")

    # Schedule next steps
    try:
        state = schedule_call_node(state)
    except Exception as e:
        print(f"⚠️ Scheduling error: {e}")

    # TTS for voice channels
    if channel in ["call", "voice"]:
        try:
            state = tts_node(state)
        except Exception as e:
            print(f"⚠️ TTS error: {e}")

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
SILENCE_TIMEOUT = 1.5  # seconds - adjusted for VAD buffering
MAX_AUDIO_DURATION = 30  # seconds - prevent memory overflow



@app.websocket("/voice_chat")
async def voice_chat(websocket: WebSocket, db: AsyncSession = Depends(get_db)):
    await websocket.accept()
    print("🔗 WebSocket connected")
    print("ℹ️ Client-side VAD handles speech detection, server validates technical quality only")

    # Initialize audio validator
    validator = AudioValidator()
    
    # Use dicts for mutable references
    lead_id_ref = {'value': None}
    audio_data_ref = {'value': b''}
    last_chunk_time_ref = {'value': datetime.now()}
    is_receiving_ref = {'value': False}
    silence_check_task = None

    try:
        # Start silence checker task
        silence_check_task = asyncio.create_task(
            check_silence_loop(audio_data_ref, last_chunk_time_ref, 
                             is_receiving_ref, websocket, validator)
        )
        
        while True:
            # Check connection state
            if websocket.application_state != WebSocketState.CONNECTED:
                print("🚪 WebSocket no longer connected")
                break
            
            try:
                # Receive with timeout
                message = await asyncio.wait_for(
                    websocket.receive(),
                    timeout=60.0
                )
                
            except asyncio.TimeoutError:
                print("⏰ Receive timeout - sending ping")
                if websocket.application_state == WebSocketState.CONNECTED:
                    stats = validator.get_stats()
                    await websocket.send_json({"type": "ping", "stats": stats})
                continue
                
            except WebSocketDisconnect:
                print("🚪 Client disconnected gracefully")
                break

            # Handle text messages
            if "text" in message:
                try:
                    data = json.loads(message["text"])
                    should_break = await handle_text_message(
                        data, lead_id_ref, is_receiving_ref, 
                        last_chunk_time_ref, audio_data_ref, websocket, validator
                    )
                    if should_break:
                        break
                
                except json.JSONDecodeError as e:
                    print(f"❌ JSON decode error: {e}")
                    continue
                except Exception as e:
                    print(f"❌ Error handling text message: {e}")
                    import traceback
                    traceback.print_exc()
                    continue

            # Handle binary audio data
            elif "bytes" in message:
                chunk = message["bytes"]
                await handle_audio_chunk(
                    chunk, audio_data_ref, is_receiving_ref, 
                    last_chunk_time_ref, websocket, validator
                )

    except WebSocketDisconnect:
        print("🚪 Client disconnected during communication")
        
    except Exception as e:
        print(f"❌ Unexpected error in voice_chat: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Cancel silence checker
        if silence_check_task:
            silence_check_task.cancel()
            try:
                await silence_check_task
            except asyncio.CancelledError:
                pass
        
        # Process any remaining audio
        if audio_data_ref.get('value'):
            print("📦 Processing remaining audio buffer...")
            try:
                await process_audio(audio_data_ref['value'], websocket, validator)
            except Exception as e:
                print(f"❌ Failed to process remaining audio: {e}")
        
        # Print final statistics
        final_stats = validator.get_stats()
        print(f"📊 Session Statistics:")
        print(f"   Total Chunks: {final_stats.get('total_received', 0)}")
        print(f"   Valid Chunks: {final_stats.get('total_valid', 0)}")
        print(f"   Total Data: {final_stats.get('total_bytes', 0) / 1024:.2f} KB")
        print(f"   Validation Rate: {final_stats.get('validation_rate', 0)*100:.1f}%")
        print(f"   Avg RMS: {final_stats.get('avg_rms', 0):.3f}")
        print(f"   Avg Clipping: {final_stats.get('avg_clipping_rate', 0)*100:.2f}%")
        
        # Close database session
        if db:
            try:
                await db.close()
            except Exception as e:
                print(f"⚠️ Error closing database: {e}")
        
        # Close WebSocket
        if websocket.application_state == WebSocketState.CONNECTED:
            try:
                await websocket.close()
                print("✅ WebSocket closed cleanly")
            except Exception as e:
                print(f"⚠️ Error closing WebSocket: {e}")

# @app.websocket("/voice_chat")
# async def voice_chat(websocket: WebSocket, db: AsyncSession = Depends(get_db)):
#     await websocket.accept()
#     print("🔗 WebSocket connected")

#     lead_id: Optional[str] = None
#     audio_data = b''
#     last_chunk_time = datetime.now()
#     is_receiving = False
#     silence_check_task = None

#     async def check_silence():
#         """Background task to check for silence timeout"""
#         nonlocal audio_data, last_chunk_time, is_receiving
        
#         while True:
#             await asyncio.sleep(0.5)  # Check every 500ms
            
#             if not is_receiving:
#                 continue
                
#             silence_duration = (datetime.now() - last_chunk_time).total_seconds()
            
#             if silence_duration > SILENCE_TIMEOUT and audio_data:
#                 print(f"🔇 Silence detected ({silence_duration:.2f}s) - Processing audio...")
#                 await process_audio(audio_data)
#                 audio_data = b''
#                 is_receiving = False

#     async def process_audio(audio_bytes: bytes):
#         """Process and transcribe audio data"""
#         if len(audio_bytes) < 3200:  # Less than 100ms at 16kHz
#             print("⚠️ Audio too short, skipping")
#             return

#         try:
#             base_filename = f"audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
#             print(f"💾 Processing audio: {len(audio_bytes)} bytes ({len(audio_bytes) / 32000:.2f}s)")
            
#             # Save PCM to WAV
#             save_pcm_to_wav(audio_bytes, filename=base_filename)
            
#             # Transcribe
#             transcription = await transcribe_with_faster_whisper(audio_bytes)
            
#             if transcription and transcription.strip():
#                 print(f"📝 Transcription: {transcription}")
                
#                 # Send transcription back to client
#                 if websocket.application_state == WebSocketState.CONNECTED:
#                     await websocket.send_json({
#                         "type": "transcription",
#                         "text": transcription,
#                         "timestamp": datetime.now().isoformat()
#                     })
                    
#                     # TODO: Generate AI response and send audio back
#                     # response_audio = await generate_ai_response(transcription)
#                     # await websocket.send_bytes(response_audio)
#             else:
#                 print("⚠️ Empty transcription")
                
#         except Exception as e:
#             print(f"❌ Audio processing failed: {e}")
#             import traceback
#             traceback.print_exc()

#     try:
#         # Start silence checker task
#         silence_check_task = asyncio.create_task(check_silence())
        
#         while True:
#             # Check connection state before receiving
#             if websocket.application_state != WebSocketState.CONNECTED:
#                 print("🚪 WebSocket no longer connected")
#                 break
            
#             try:
#                 # Set timeout to prevent hanging
#                 message = await asyncio.wait_for(
#                     websocket.receive(),
#                     timeout=60.0  # 60 second timeout
#                 )
                
#             except asyncio.TimeoutError:
#                 print("⏰ Receive timeout - sending ping")
#                 if websocket.application_state == WebSocketState.CONNECTED:
#                     await websocket.send_json({"type": "ping"})
#                 continue
                
#             except WebSocketDisconnect:
#                 print("🚪 Client disconnected gracefully")
#                 break

#             # Handle text messages (JSON control messages)
#             if "text" in message:
#                 try:
#                     data = json.loads(message["text"])
#                     msg_type = data.get("type")
                    
#                     if msg_type == "start_conversation":
#                         lead_id = data.get("user_id")
#                         if not lead_id:
#                             print("⚠️ Missing user_id in start_conversation")
#                             await websocket.send_json({
#                                 "type": "error",
#                                 "message": "user_id is required"
#                             })
#                             continue
                        
#                         print(f"🟢 Conversation started with lead: {lead_id}")
#                         is_receiving = True
#                         last_chunk_time = datetime.now()
                        
#                         await websocket.send_json({
#                             "type": "status",
#                             "message": "ready"
#                         })
                    
#                     elif msg_type == "end_conversation":
#                         print("🔴 End conversation requested")
                        
#                         # Process any remaining audio
#                         if audio_data:
#                             await process_audio(audio_data)
#                             audio_data = b''
                        
#                         await websocket.send_json({
#                             "type": "status",
#                             "message": "conversation_ended"
#                         })
#                         break
                    
#                     elif msg_type == "ping":
#                         # Respond to ping
#                         if websocket.application_state == WebSocketState.CONNECTED:
#                             await websocket.send_json({"type": "pong"})
                
#                 except json.JSONDecodeError as e:
#                     print(f"❌ JSON decode error: {e}")
#                     continue
#                 except Exception as e:
#                     print(f"❌ Error handling text message: {e}")
#                     continue

#             # Handle binary audio data
#             elif "bytes" in message:
#                 chunk = message["bytes"]
                
#                 # Validate chunk
#                 if len(chunk) == 0:
#                     continue
                    
#                 if len(chunk) % 2 != 0:
#                     print(f"⚠️ Invalid chunk size: {len(chunk)} bytes (not 16-bit aligned)")
#                     continue
                
#                 # Update state
#                 is_receiving = True
#                 last_chunk_time = datetime.now()
#                 audio_data += chunk
                
#                 # Prevent memory overflow
#                 duration = len(audio_data) / 32000  # 16kHz * 2 bytes
#                 if duration > MAX_AUDIO_DURATION:
#                     print(f"⚠️ Max audio duration reached ({duration:.1f}s), processing...")
#                     await process_audio(audio_data)
#                     audio_data = b''
#                     is_receiving = False
                
#                 # Log progress (every ~1 second of audio)
#                 if len(audio_data) % 32000 < len(chunk):
#                     print(f"🎙️ Buffered: {len(audio_data)} bytes ({duration:.2f}s)")

#     except WebSocketDisconnect:
#         print("🚪 Client disconnected during communication")
        
#     except Exception as e:
#         print(f"❌ Unexpected error in voice_chat: {e}")
#         import traceback
#         traceback.print_exc()
        
#     finally:
#         # Cancel silence checker
#         if silence_check_task:
#             silence_check_task.cancel()
#             try:
#                 await silence_check_task
#             except asyncio.CancelledError:
#                 pass
        
#         # Process any remaining audio
#         if audio_data:
#             print("📦 Processing remaining audio buffer...")
#             try:
#                 await process_audio(audio_data)
#             except Exception as e:
#                 print(f"❌ Failed to process remaining audio: {e}")
        
#         # Close database session
#         if db:
#             try:
#                 await db.close()
#             except Exception as e:
#                 print(f"⚠️ Error closing database: {e}")
        
#         # Close WebSocket if still connected
#         if websocket.application_state == WebSocketState.CONNECTED:
#             try:
#                 await websocket.close()
#                 print("✅ WebSocket closed cleanly")
#             except Exception as e:
#                 print(f"⚠️ Error closing WebSocket: {e}")



# -------------------------
# Main entry (single uvicorn invocation)
# -------------------------
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
