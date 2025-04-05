import os
import datetime
import wave
import jwt
import uvicorn
import ffmpeg
import numpy as np
import soundfile as sf
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Form, Request, Response, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.websockets import WebSocketState
from sqlalchemy.future import select
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from backend.utilities import handle_call, hash_password, verify_password
from database.db_setup import get_db, init_db
from database.models import User

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

@app.get("/home")
async def home_page(request: Request, user=Depends(require_auth)):
    if isinstance(user, RedirectResponse):
        return user
    return templates.TemplateResponse("index.html", {"request": request, "user": user})

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
        response = RedirectResponse(url="/home", status_code=303)
        response.set_cookie(key="access_token", value=token, httponly=False, secure=False, samesite="Lax")
        return response
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.websocket("/voice_chat")
async def voice_chat(websocket: WebSocket, db: Session = Depends(get_db)):
    await websocket.accept()
    audio_data = b""
    try:
        while True:
            try:
                data = await websocket.receive_bytes()
                print(f"Received {len(data)} bytes, first 10 bytes: {data[:10]}")

                if len(data) % 2 != 0:
                    print("❌ Skipping invalid chunk due to odd byte count")
                    continue

                audio_data += data
                # Optional: process audio_data real-time here

            except WebSocketDisconnect:
                print("🚪 Client disconnected")
                break
            except Exception as e:
                print(f"❌ WebSocket error: {e}")
                break
    finally:
        if audio_data:
            save_pcm_to_wav(audio_data, filename='final_audio.wav', sample_rate=44100)
            print("✅ Final audio saved")

        await db.close()

        if websocket.application_state != WebSocketState.DISCONNECTED:
            await websocket.close()


def save_pcm_to_wav(pcm_data, filename="received_audio_16bitpcm.wav", sample_rate=44100):
    audio_array = np.frombuffer(pcm_data, dtype=np.int16)
    sf.write(filename, audio_array, sample_rate, subtype='PCM_16')

@app.on_event("startup")
async def startup():
    try:
        await init_db()
    except Exception as e:
        print("DB startup failed:", e)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)