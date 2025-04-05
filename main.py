import os
import datetime
import json
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

from dotenv import load_dotenv
from backend.utilities import handle_call, hash_password, verify_password
from database.db_setup import get_db, init_db
from database.models import User

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
async def home_page(request: Request, user=Depends(require_auth)):
    if isinstance(user, RedirectResponse):
        return user


    user_id = user.id
    username = user.username

    return templates.TemplateResponse("index.html", {
        "request": request,
        "user_id": user_id,
        "username": username
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
        response = JSONResponse(
                    content={"username": db_user.username, "user_id": db_user.id},
                    status_code=200
                ) 
        response.set_cookie(key="access_token", value=token, httponly=False, secure=False, samesite="Lax")
        return response
    raise HTTPException(status_code=401, detail="Invalid credentials")

# ───── WebSocket Endpoint ──────────────────────────────────
@app.websocket("/voice_chat")
async def voice_chat(websocket: WebSocket, db: Session = Depends(get_db)):
    await websocket.accept()
    logger.info("🔗 WebSocket connected")

    audio_data = b""
    recording = False

    try:
        while True:
            try:
                message = await websocket.receive()

                if "text" in message:
                    try:
                        data = json.loads(message["text"])
                        if data.get("type") == "start_conversation":
                            logger.info("🟢 Conversation started")
                            recording = True
                            audio_data = b""
                        elif data.get("type") == "end_conversation":
                            logger.info("🔴 Conversation ended")
                            recording = False
                            if audio_data:
                                save_pcm_to_wav(audio_data, filename='final_audio.wav', sample_rate=44100)
                                logger.info("✅ Final audio saved")
                                audio_data = b""
                    except json.JSONDecodeError:
                        logger.warning("⚠️ Invalid JSON message")

                elif "bytes" in message:
                    data = message["bytes"]
                    logger.info(f"📥 Received {len(data)} bytes, first 10 bytes: {data[:10]}")
                    if recording:
                        if len(data) % 2 != 0:
                            logger.warning("⚠️ Skipping invalid chunk due to odd byte count")
                            continue
                        audio_data += data

            except WebSocketDisconnect:
                logger.info("🚪 Client disconnected")
                break
            except Exception as e:
                logger.error(f"❌ WebSocket error: {e}")
                break

    finally:
        if recording and audio_data:
            save_pcm_to_wav(audio_data, filename='final_audio.wav', sample_rate=44100)
            logger.info("✅ Final audio saved on disconnect")

        await db.close()

        if websocket.application_state != WebSocketState.DISCONNECTED:
            await websocket.close()

# ───── Audio Saving Utility ─────────────────────────────────
def save_pcm_to_wav(pcm_data, filename="received_audio.wav", sample_rate=44100):
    audio_array = np.frombuffer(pcm_data, dtype=np.int16)
    sf.write(filename, audio_array, sample_rate, subtype='PCM_16')

# ───── App Startup ──────────────────────────────────────────
@app.on_event("startup")
async def startup():
    try:
        await init_db()
        logger.info("🚀 Database initialized")
    except Exception as e:
        logger.error(f"❌ DB startup failed: {e}")

# ───── Entry Point ──────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
