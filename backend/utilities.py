import asyncio
import numpy as np
import datetime
import jwt
from fastapi import HTTPException
from typing import Optional
import webrtcvad
from backend.ai_core.text_n_speech import process_audio_stream, text_to_speech, denoise_audio
from .curd import get_lead, get_last_interaction, insert_lead_interaction
from starlette.websockets import WebSocketState, WebSocketDisconnect

VAD = webrtcvad.Vad(3)  # Aggressive VAD setting
SILENCE_THRESHOLD = 3  # Maximum consecutive silence prompts before ending call

EXPECTED_FRAME_SIZE = 256  # Adjust based on your model's requirements


SECRET_KEY = "your_secret_key"
ALGORITHM = "HS256"

def generate_ai_response(user_text, history):
    """Mock function to generate AI response based on user input and conversation history."""
    return f"I understand that you said: {user_text}. Can you elaborate?"

async def generate_greeting(lead, last_interaction):
    """Generates a personalized greeting based on lead data and last interaction."""
    if last_interaction:
        return f"Hello {lead['name']}, last time we spoke about . How can I assist today?"
    return f"Hello {lead['name']}, how can I help you today?"
    


async def handle_call(audio_queue: asyncio.Queue, websocket, lead_id, db):
    """Handles real-time conversation with speech detection, silence handling, and AI-user interaction."""

    conversation_history = []
    ai_speaking = False
    user_speaking = False
    silence_counter = 0
    greeting_sent = False

    lead = {"name": 'subrat', "topic": 'nothing..'}  # await get_lead(db, lead_id)
    last_interaction = await get_last_interaction(db, lead_id)
    greeting = await generate_greeting(lead, last_interaction)
    print(f"👋 Greeting: {greeting}")

    audio_response = await text_to_speech(greeting)
    if audio_response is None:
        print("❌ text_to_speech() returned None. Skipping audio response.")
    elif not greeting_sent:
        print("📤 Sending greeting audio...")
        await websocket.send_bytes(audio_response)
        greeting_sent = True

    start_time = datetime.datetime.utcnow()

    try:
        while True:
            try:
                print("⏳ Waiting for audio chunk...")
                audio_chunk = await asyncio.wait_for(audio_queue.get(), timeout=10)
                print(f"📥 Received audio chunk of size: {len(audio_chunk)}")

                if len(audio_chunk) % EXPECTED_FRAME_SIZE != 0:
                    print(f"❌ Invalid buffer size ({len(audio_chunk)}), skipping chunk.")
                    continue

                processed_audio = audio_chunk #await denoise_audio(audio_chunk)
                # print(f"🎛️ Processed audio size: {len(processed_audio)}")

                # if len(processed_audio) % EXPECTED_FRAME_SIZE != 0:
                #     print(f"❌ Processed audio has an invalid buffer size, skipping.")
                #     continue

                volume_level = np.max(np.abs(np.frombuffer(processed_audio, dtype=np.int16))) / 32768.0
                print(f"🔊 Volume Level: {volume_level:.2f}")

                vad_result = VAD.is_speech(processed_audio, 16000)
                print(f"🗣️ VAD Result: {vad_result}")

                if ai_speaking and vad_result:
                    ai_speaking = False
                    print("🛑 User interrupted AI")
                    await websocket.send_bytes(await text_to_speech("Oh! You have something to say. Go ahead, I'm listening."))
                    continue

                if volume_level < 0.3 or not vad_result:
                    silence_counter += 1
                    print(f"🤫 Silence counter: {silence_counter}")

                    prompts = [
                        "Could you please repeat that? I couldn't hear you clearly.",
                        "There seems to be some background noise. Could you speak a bit louder?",
                        "I’m having trouble hearing. Maybe we can try again later."
                    ]
                    if silence_counter >= SILENCE_THRESHOLD:
                        print("❌ Ending call due to prolonged silence.")
                        await websocket.send_bytes(await text_to_speech(prompts[-1]))
                        break

                    await websocket.send_bytes(await text_to_speech(prompts[min(silence_counter, 2)]))
                    continue

                silence_counter = 0
                print("🎧 Processing audio to text...")
                user_text = await process_audio_stream(processed_audio)
                print(f"📄 Transcribed Text: '{user_text.strip()}'")

                if not user_text.strip():
                    print("⚠️ Empty transcription. Skipping...")
                    continue

                user_speaking = True

                try:
                    ai_response = user_text  # Replace with actual AI logic later
                    ai_audio = await text_to_speech(ai_response)
                    print(f"🤖 AI Response: '{ai_response}'")
                except Exception as e:
                    print(f"❌ AI Response Error: {e}")
                    ai_response = "I'm sorry, I didn't understand that."
                    ai_audio = await text_to_speech(ai_response)

                conversation_history.append({"user": user_text, "AI": ai_response})
                ai_speaking = True
                print("📤 Sending AI response audio...")
                await websocket.send_bytes(ai_audio)
                ai_speaking = False

            except asyncio.TimeoutError:
                print("⏳ Timeout waiting for audio.")
                if user_speaking:
                    user_speaking = False
                    await websocket.send_bytes(await text_to_speech("I'm listening, please continue."))
                    continue

    except Exception as e:
        print(f"❌ WebSocket Error: {e}")

    finally:
        end_time = datetime.datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        print(f"📅 Conversation duration: {duration:.2f} seconds")
        print(f"💬 Final conversation history: {conversation_history}")
        # await insert_lead_interaction(db, lead_id, conversation_history, duration)

        if websocket.application_state == WebSocketState.CONNECTED:
            print("🔌 Closing WebSocket connection.")
            await websocket.close()




# async def handle_call(data, websocket, lead_id, db):
#     """Handles real-time conversation with speech detection, silence handling, and AI-user interaction."""
    
#     conversation_history = []
#     ai_speaking = False
#     user_speaking = False
#     silence_counter = 0
#     greeting_sent = False

#     lead = {"name":'subrat',"topic":'nothing..'}#await get_lead(db, lead_id)
#     last_interaction = await get_last_interaction(db, lead_id)
#     greeting = await generate_greeting(lead, last_interaction)
#     print(greeting)
#     # await websocket.send_bytes(text_to_speech(greeting))
#     # import ipdb;ipdb.set_trace()
#     audio_response = await text_to_speech(greeting)
#     if audio_response is None:
#         print("❌ text_to_speech() returned None. Skipping audio response.")
#     elif not greeting_sent :
#         await websocket.send_bytes(audio_response)
#         greeting_sent

#     start_time = datetime.datetime.utcnow()
#     try:
#         while True:
#             try:
#                 audio_chunk = await asyncio.wait_for(websocket.receive_bytes(), timeout=2)
#                 if len(audio_chunk) % EXPECTED_FRAME_SIZE != 0:
#                     print(f"❌ Invalid buffer size ({len(audio_chunk)}), skipping chunk.")
#                     continue

#                 processed_audio = await denoise_audio(audio_chunk)
                
#                 # Ensure the processed audio also maintains proper buffer size
#                 if len(processed_audio) % EXPECTED_FRAME_SIZE != 0:
#                     print(f"❌ Processed audio has an invalid buffer size, skipping.")
#                     continue

#                 processed_audio = await denoise_audio(audio_chunk)
                
#                 volume_level = np.max(np.abs(np.frombuffer(processed_audio, dtype=np.int16))) / 32768.0
                
#                 if ai_speaking and VAD.is_speech(processed_audio, 16000):
#                     ai_speaking = False
#                     await websocket.send_bytes(await text_to_speech("Oh! You have something to say. Go ahead, I'm listening."))
#                     continue

#                 if volume_level < 0.3 or not VAD.is_speech(processed_audio, 16000):
#                     silence_counter += 1
#                     prompts = [
#                         "Could you please repeat that? I couldn't hear you clearly.",
#                         "There seems to be some background noise. Could you speak a bit louder?",
#                         "I’m having trouble hearing. Maybe we can try again later."
#                     ]
#                     if silence_counter >= SILENCE_THRESHOLD:
#                         await websocket.send_bytes(await text_to_speech(prompts[-1]))
#                         break
#                     await websocket.send_bytes(await text_to_speech(prompts[min(silence_counter, 2)]))
#                     continue
                
#                 silence_counter = 0
#                 user_text = await process_audio_stream(processed_audio)
#                 if not user_text.strip():
#                     continue
                
#                 user_speaking = True
                
#                 try:
#                     ai_response = generate_ai_response(user_text, conversation_history)
#                     ai_audio = await text_to_speech(ai_response)
#                 except Exception as e:
#                     print(f"AI Response Error: {e}")
#                     ai_response = "I'm sorry, I didn't understand that."
#                     ai_audio = await text_to_speech(ai_response)
                
#                 conversation_history.append({"user": user_text, "AI": ai_response})
#                 ai_speaking = True
#                 await websocket.send_bytes(ai_audio)
#                 ai_speaking = False

#             except asyncio.TimeoutError:
#                 if user_speaking:
#                     user_speaking = False
#                     await websocket.send_bytes(await text_to_speech("I'm listening, please continue."))
#                     continue
    
#     except Exception as e:
#         print(f"WebSocket Error: {e}")
    
#     finally:
#         end_time = datetime.datetime.utcnow()
#         duration = (end_time - start_time).total_seconds()

#         # await insert_lead_interaction(db, lead_id, conversation_history, duration)
#         if websocket.application_state == WebSocketState.CONNECTED:
#             await websocket.close()




def verify_jwt_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTError:
        raise HTTPException(status_code=403, detail="Could not validate credentials")


import bcrypt

def hash_password(password: str) -> str:
    """Hashes a password using bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, stored_password: str) -> bool:
    """Verifies a password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8'))
    except ValueError:
        print("❌ Error: Stored password is not a valid bcrypt hash.")
        return False
