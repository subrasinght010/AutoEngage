# Multi-Channel AI Communication System - Setup Guide

## Prerequisites

- Python 3.9+
- 16GB RAM (for running Whisper + Mistral)
- Gmail account (for email monitoring)
- Twilio account (for SMS/WhatsApp)
- SendGrid account (for sending emails)

---

## Step 1: Install Dependencies
```bash
pip install -r requirements.txt
## Step 2: Setup Ollama (LLM)
Step 2: Setup Ollama (LLM)
bash# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull Mistral model
ollama pull mistral

# Start Ollama server (in separate terminal)
ollama serve

Step 3: Configure Environment Variables
Copy .env.example to .env and fill in:
bashcp .env.example .env
nano .env
Required configurations:
Email Monitoring:
envEMAIL_USERNAME=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
For Gmail App Password:

Go to Google Account → Security
Enable 2-Step Verification
Generate App Password
Use that password in .env

Twilio (SMS/WhatsApp):
envTWILIO_ACCOUNT_SID=ACxxxx
TWILIO_AUTH_TOKEN=your_token
TWILIO_PHONE_NUMBER=+1234567890
TWILIO_WHATSAPP_NUMBER=whatsapp:+1234567890
SendGrid (Email sending):
envSENDGRID_API_KEY=SG.xxxx
FROM_EMAIL=support@yourdomain.com

Step 4: Initialize Database
bash# Run migrations
alembic upgrade head

Step 5: Initialize RAG System
bash# Add your company documents to knowledge_base/
mkdir knowledge_base
# Copy your PDFs, text files here

# Initialize RAG
python scripts/setup_rag.py

Step 6: Test Components
Test Email Monitoring:
bashpython scripts/test_email_monitor.py
Test Webhooks:
bash# First, start server:
python main.py

# In another terminal:
python scripts/test_webhooks.py

Step 7: Configure Twilio Webhooks

Go to Twilio Console
For SMS: Set webhook URL to https://yourserver.com/webhook/sms
For WhatsApp: Set webhook URL to https://yourserver.com/webhook/whatsapp

Use ngrok for local testing:
bashngrok http 8080
# Use ngrok URL in Twilio webhooks

Step 8: Start Application
Option A: Run everything together
bashpython main.py
Option B: Run workers separately
bash# Terminal 1: Main server
python main.py

# Terminal 2: Background workers (optional if not using lifespan)
python scripts/start_workers.py

Step 9: Verify System
Check worker status:
bashcurl http://localhost:8080/workers/status
Check webhook status:
bashcurl http://localhost:8080/webhook/status

Troubleshooting
Email monitor not working:

Check EMAIL_USERNAME and EMAIL_PASSWORD
Enable IMAP in Gmail settings
Use App Password, not regular password

Webhooks not receiving:

Check Twilio webhook URLs
Use ngrok for local testing
Check firewall/port settings

Database errors:

Run: alembic upgrade head
Delete mydatabase.db and recreate

LLM not responding:

Check if Ollama is running: ollama list
Restart Ollama: ollama serve


Production Deployment

Use proper domain (not ngrok)
Setup SSL certificate
Use environment-specific .env
Setup systemd service for auto-start
Configure log rotation
Setup monitoring (Sentry, etc.)
