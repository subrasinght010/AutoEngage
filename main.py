import os
import datetime
import subprocess
import wave
import jwt
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Form, Request, Response, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.future import select
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from backend.utilities import handle_call
from database.db_setup import get_db, init_db
from database.models import User
from backend.utilities import hash_password, verify_password
from starlette.websockets import WebSocketState

import asyncio
import ffmpeg
import numpy as np
import soundfile as sf

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

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        message = await websocket.receive_json()
        if message.get("type") != "auth" or "token" not in message:
            await websocket.close(code=1008, reason="Unauthorized")
            return

        try:
            verify_jwt_token(message["token"])
        except Exception as e:
            await websocket.close(code=1008, reason="Invalid or expired token")
            return

        while True:
            try:
                data = await websocket.receive_bytes()
                if len(data) % 2 != 0:
                    print(f"Invalid buffer size: {len(data)}")
                    continue
                await websocket.send_text(f"Received {len(data)} bytes")
            except WebSocketDisconnect:
                print("Client disconnected")
                break
            except Exception as e:
                print(f"WebSocket error: {e}")
                break

    finally:
        if websocket.application_state == WebSocketState.CONNECTED:
            await websocket.close()

@app.websocket("/audio_stream")
async def audio_stream(websocket: WebSocket, lead_id: int = Query(None), db: Session = Depends(get_db)):
    await websocket.accept()
    try:
        message = await websocket.receive_json()
        if message.get("type") != "auth" or "token" not in message:
            await websocket.close(code=1008, reason="Unauthorized")
            return

        try:
            verify_jwt_token(message["token"])
        except Exception:
            await websocket.close(code=1008, reason="Invalid or expired token")
            return

        await handle_call(websocket, lead_id, db)

    except WebSocketDisconnect:
        print("Client disconnected")

    finally:
        await db.close()
        if websocket.application_state == WebSocketState.CONNECTED:
            await websocket.close()

def decode_opus(opus_data):
    try:
        process = (
            ffmpeg
            .input('pipe:0', format='webm')
            .output('pipe:1', format='wav', acodec='pcm_s16le', ar=16000)
            .global_args('-fflags', '+discardcorrupt')
            .global_args('-loglevel', 'debug')
            .run(capture_stdout=True, input=opus_data)
        )
        return process[0]
    except Exception as e:
        print(f"❌ FFmpeg decoding failed: {e}")
        return None

@app.websocket("/voice_chat")
async def voice_chat(websocket: WebSocket, db: Session = Depends(get_db)):
    await websocket.accept()
    audio_data = b""

    try:
        while True:
            try:
                data = await websocket.receive_bytes()
                audio_data += data
                print(f"Received {len(data)} bytes, first 10 bytes: {data[:10]}")

                if len(data) % 2 != 0:
                    print(f"Invalid buffer size: {len(data)}")
                    continue

                pcm_audio = decode_opus(data)
                if pcm_audio:
                    audio_array = np.frombuffer(pcm_audio, dtype=np.int16)
                    sf.write("received_audio_16bitpcm.wav", audio_array, 16000, subtype='PCM_16')
                    print("✅ Real-time WAV saved")
                else:
                    print("❌ Decoding failed, skipping chunk")
                    continue

                await handle_call(websocket, 2, db)

            except WebSocketDisconnect:
                print("Client disconnected")
                break
            except Exception as e:
                print(f"WebSocket error: {e}")
                break

    finally:
        if audio_data:
            final_pcm_audio = decode_opus(audio_data)
            if final_pcm_audio:
                sf.write('final_audio.wav', np.frombuffer(final_pcm_audio, dtype=np.int16), 16000, subtype='PCM_16')
                print("✅ Final audio saved")
        await db.close()
        if websocket.application_state == WebSocketState.CONNECTED:
            await websocket.close()

@app.on_event("startup")
async def startup():
    try:
        await init_db()
    except:
        pass

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)