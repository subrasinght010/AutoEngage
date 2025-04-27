import os
import datetime
import json
import time
import traceback
from backend.ai_core.text_n_speech import transcribe_with_faster_whisper
from backend.audio import AudioBuffer, RealTimeSileroVAD
import numpy as np
import soundfile as sf
import logging
import sys
import jwt
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Form, Request, Response
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.websockets import WebSocketState
from sqlalchemy.future import select
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from dotenv import load_dotenv
from backend.utilities import handle_call, hash_password, verify_password
from database.db_setup import get_db, init_db
from database.models import User
from backend.curd import get_user_by_username
# ───── Logger Setup ─────────────────────────────────────────
logger = logging.getLogger("voice-app")
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)

formatter = logging.Formatter("[%(asctime)s] %(message)s", "%Y-%m-%d %H:%M:%S")
handler.setFormatter(formatter)

logger.handlers.clear()
logger.addHandler(handler)
logger.propagate = False

# ───── App Initialization ──────────────────────────────────
load_dotenv()
app = FastAPI()
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
templates = Jinja2Templates(directory="frontend/templates")

SECRET_KEY = os.getenv("SECRET_KEY", "default_secret_key")
ALGORITHM = "HS256"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ───── Auth Utilities ──────────────────────────────────────
def create_jwt_token(username: str):
    expiration = datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    payload = {"sub": username, "exp": expiration}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_jwt_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload["sub"]
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

# ───── Routes ───────────────────────────────────────────────
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
    user=Depends(require_auth),             # returns username
    db: AsyncSession = Depends(get_db)  # put here, not in the decorator
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
async def signup(response: Response, username: str = Form(...), password: str = Form(...), confirm_password: str = Form(...), db: Session = Depends(get_db)):
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
    except:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal Server Error")
    return RedirectResponse(url="/login", status_code=303)

@app.post("/login")
async def login(response: Response, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
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



# ───── App Startup ──────────────────────────────────────────
@app.on_event("startup")
async def startup():
    try:
        await init_db()
        logger.info("🚀 Database initialized")
    except Exception as e:
        logger.error(f"❌ DB startup failed: {e}")


import time
import numpy as np
import soundfile as sf

# ───── Audio Saving Utility ─────────────────────────────────
def save_pcm_to_wav(pcm_data, filename="received_audio.wav", sample_rate=44100):
    audio_array = np.frombuffer(pcm_data, dtype=np.int16)
    sf.write(filename, audio_array, sample_rate, subtype='PCM_16')




import numpy as np
import soundfile as sf
import librosa


def save_pcm_to_wav(pcm_data, filename="received_audio.wav", sample_rate=44100):
    audio_array = np.frombuffer(pcm_data, dtype=np.int16)
    sf.write(filename, audio_array, sample_rate, subtype='PCM_16')

def save_pcm_to_wav_16(pcm_data, filename="received_audio_16.wav", sample_rate=16000):
    audio_array = np.frombuffer(pcm_data, dtype=np.int16)
    sf.write(filename, audio_array, sample_rate, subtype='PCM_16')

import numpy as np
import soundfile as sf
import librosa
import datetime
import json
import traceback


# ==========================
# Audio Handling Functions
# ==========================


def save_pcm_to_wav(pcm_data, filename="received_audio.wav", sample_rate=44100):
    audio_array = np.frombuffer(pcm_data, dtype=np.int16)
    sf.write(filename, audio_array, sample_rate, subtype='PCM_16')

# ==========================
# WebSocket Handler
# ==========================

SILENCE_TIMEOUT = 1  # seconds

@app.websocket("/voice_chat")
async def voice_chat(websocket: WebSocket, db: Session = Depends(get_db)):
    await websocket.accept()
    logger.info("🔗 WebSocket connected")

    lead_id = None
    audio_data = b''
    last_chunk_time = datetime.datetime.now()

    try:
        while True:
            try:
                message = await websocket.receive()

                # Handle text messages
                if "text" in message and message["text"]:
                    try:
                        data = json.loads(message["text"])

                        if data.get("type") == "start_conversation":
                            lead_id = data.get("user_id")
                            if not lead_id:
                                logger.warning("⚠️ Missing user_id in start_conversation")
                                return
                            logger.info(f"🟢 Conversation started with {lead_id}")

                        elif data.get("type") == "end_conversation":
                            logger.info("🔴 Conversation ended by client")
                            # transcription = await transcribe_with_faster_whisper(b"")
                            # await websocket.send_json({"type": "transcription", "text": transcription})
                            break

                    except json.JSONDecodeError as e:
                        logger.error(f"❌ JSON decoding failed: {message['text']}")
                        continue  # Skip malformed message

                # Handle audio chunks
                elif "bytes" in message:
                    chunk = message["bytes"]

                    if len(chunk) % 2 != 0:
                        logger.warning("⚠️ Skipping invalid chunk due to odd byte count")
                        continue

                    audio_data += chunk
                    logger.info(f"🎙️ Received chunk - Raw: {len(chunk)} bytes")

                    last_chunk_time = datetime.datetime.now()

                # Handle silence timeout
                if (datetime.datetime.now() - last_chunk_time) > datetime.timedelta(seconds=SILENCE_TIMEOUT):
                    if audio_data:
                        logger.info("⏳ Silence detected, sending accumulated audio data for final transcription.")

                        # Save audio with timestamped filename
                        base_filename = f"audio_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        logger.info(f"💾 Saving audio with base filename: {base_filename}")
                        save_pcm_to_wav(audio_data)

                        # Transcribe and send result
                        transcription = await transcribe_with_faster_whisper(audio_data)
                        logger.info(f"📝 Transcription: {transcription}")
                        await websocket.send_json({"type": "transcription", "text": transcription})

                        # Reset audio data
                        audio_data = b''
                    
                    last_chunk_time = datetime.datetime.now()

            except WebSocketDisconnect:
                logger.info("🚪 Client disconnected")
                break

            except Exception as e:
                logger.error(f"❌ WebSocket error: {e}\n{traceback.format_exc()}")
                break

    finally:
        await db.close()
        if websocket.application_state != WebSocketState.DISCONNECTED:
            await websocket.close()




# ───── Entry Point ──────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
