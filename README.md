# AI Communication System - Multi-Channel Autonomous Agent

A production-ready, multi-channel AI communication system that handles voice calls, SMS, WhatsApp, and email with autonomous conversation management, RAG-powered responses, and intelligent follow-ups.

## 🌟 Features

- **Multi-Channel Support**: Voice calls, SMS, WhatsApp, Email
- **Real-Time Voice Conversations**: WebSocket-based voice chat with VAD
- **Autonomous Follow-ups**: Smart follow-up scheduling across channels
- **RAG-Powered Responses**: Knowledge base integration with ChromaDB
- **Conversation Threading**: Context-aware conversations across channels
- **Production-Ready**: Security, monitoring, rate limiting, retry logic
- **Scalable Architecture**: Docker deployment, queue system, connection pooling

## 📋 Table of Contents

- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Testing](#testing)
- [Deployment](#deployment)
- [Monitoring](#monitoring)
- [API Documentation](#api-documentation)
- [Contributing](#contributing)

## 🏗️ Architecture
┌─────────────────────────────────────────────────┐
│              User Interfaces                    │
│  Voice Call | SMS | WhatsApp | Email | Web     │
└──────────────────┬──────────────────────────────┘
│
┌──────────────────▼──────────────────────────────┐
│           FastAPI Server (main.py)              │
│  ┌──────────────────────────────────────────┐  │
│  │  Webhook Handlers (Security + Rate Limit)│  │
│  └──────────────┬───────────────────────────┘  │
│                 │                                │
│  ┌──────────────▼───────────────────────────┐  │
│  │     Message Queue (Optional)             │  │
│  └──────────────┬───────────────────────────┘  │
│                 │                                │
│  ┌──────────────▼───────────────────────────┐  │
│  │  Intent Detector + LLM (Mistral 7B)      │  │
│  │  + RAG (ChromaDB)                        │  │
│  └──────────────┬───────────────────────────┘  │
│                 │                                │
│  ┌──────────────▼───────────────────────────┐  │
│  │  Communication Agents                    │  │
│  │  (Email/SMS/WhatsApp/Call)               │  │
│  └──────────────┬───────────────────────────┘  │
└─────────────────┼──────────────────────────────┘
│
┌─────────────────▼──────────────────────────────┐
│        Background Workers                       │
│  ┌──────────┬──────────────┬────────────────┐ │
│  │  Email   │  Follow-up   │  Callback      │ │
│  │  Monitor │  Manager     │  Scheduler     │ │
│  └──────────┴──────────────┴────────────────┘ │
└─────────────────────────────────────────────────┘
│
┌─────────────────▼──────────────────────────────┐
│            Data Layer                           │
│  PostgreSQL | Redis | ChromaDB                  │
└─────────────────────────────────────────────────┘
## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- 16GB RAM
- Docker & Docker Compose (optional)
- Twilio account (for SMS/WhatsApp)
- SendGrid account (for email)
- Gmail account (for email monitoring)

### One-Command Setup (Development)
```bash
# Clone repository
git clone https://github.com/yourusername/ai-communication-system.git
cd ai-communication-system

# Run setup script
./scripts/quick_start.sh

Manual Setup
bash# 1. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Setup Ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama pull mistral

# 4. Configure environment
cp .env.example .env
# Edit .env with your credentials

# 5. Initialize database
alembic upgrade head

# 6. Initialize RAG
python scripts/setup_rag.py

# 7. Start application
python main.py
⚙️ Configuration
Environment Variables
env# Required
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
SENDGRID_API_KEY=your_key
EMAIL_USERNAME=your_email@gmail.com
EMAIL_PASSWORD=your_app_password

# Optional
DATABASE_URL=postgresql://...  # Defaults to SQLite
USE_MESSAGE_QUEUE=false
ENABLE_METRICS=true
Twilio Webhook Configuration

Go to Twilio Console
Configure webhooks:

SMS: https://yourdomain.com/webhook/sms
WhatsApp: https://yourdomain.com/webhook/whatsapp



Use ngrok for local testing:
bashngrok http 8080
# Use ngrok URL in Twilio
📖 Usage
Starting the System
bash# Development
python main.py

# Production (with Docker)
docker-compose up -d

# With monitoring
docker-compose -f docker-compose.yml -f deployment/docker-compose.monitoring.yml up -d
Testing Components
bash# Test email monitoring
python scripts/test_email_monitor.py

# Test webhooks
python scripts/test_webhooks.py

# Run full test suite
./scripts/run_tests.sh
API Endpoints
GET  /health          - Health check
GET  /workers/status  - Worker status
GET  /metrics         - Prometheus metrics
POST /webhook/sms     - SMS webhook
POST /webhook/whatsapp- WhatsApp webhook
WS   /voice_chat      - Voice call WebSocket
🧪 Testing
bash# Run all tests
pytest

# With coverage
pytest --cov=. --cov-report=html

# Specific test file
pytest tests/test_database.py

# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration
🚢 Deployment
Docker Deployment
bash# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
Production Deployment (Ubuntu/Debian)
bash# Run installation script
sudo ./deployment/install.sh

# Start service
sudo systemctl start ai-agent
sudo systemctl enable ai-agent

# Check status
sudo systemctl status ai-agent

# View logs
sudo journalctl -u ai-agent -f
Environment-Specific Configuration
bash# Development
ENVIRONMENT=development python main.py

# Staging
ENVIRONMENT=staging python main.py

# Production
ENVIRONMENT=production python main.py
📊 Monitoring
Metrics
Access Prometheus metrics:
http://localhost:8080/metrics
Available metrics:

messages_processed_total - Total messages by channel
response_time_seconds - Response time histogram
active_conversations - Current active conversations
worker_status - Worker health status
errors_total - Error counter

Dashboards
Access Grafana:
http://localhost:3000  (admin/admin)
Pre-configured dashboards:

System Overview
Message Processing
Worker Status
Error Rates

Health Checks
bash# Full health check
curl http://localhost:8080/health

# Quick health check
curl http://localhost:8080/health/quick

# Worker status
curl http://localhost:8080/workers/status
📚 API Documentation
Auto-generated API docs available at:
http://localhost:8080/docs      # Swagger UI
http://localhost:8080/redoc     # ReDoc
🔧 Troubleshooting
Email monitor not working
bash# Test connection
python scripts/test_email_monitor.py

# Check credentials
- Enable IMAP in Gmail settings
- Use App Password, not regular password
- Check EMAIL_USERNAME and EMAIL_PASSWORD in .env
Webhooks not receiving messages
bash# Verify webhook URLs in Twilio Console
# Test with ngrok for local development
ngrok http 8080

# Check webhook signature verification is working
# View logs: docker-compose logs -f app
LLM not responding
bash# Check Ollama is running
ollama list

# Restart Ollama
ollama serve

# Check model is downloaded
ollama pull mistral
Database errors
bash# Run migrations
alembic upgrade head

# Reset database (WARNING: deletes data)
rm mydatabase.db
alembic upgrade head
🤝 Contributing

Fork the repository
Create feature branch (git checkout -b feature/AmazingFeature)
Commit changes (git commit -m 'Add AmazingFeature')
Push to branch (git push origin feature/AmazingFeature)
Open Pull Request

📄 License
This project is licensed under the MIT License - see LICENSE file for details.
🙏 Acknowledgments

Anthropic Claude for AI capabilities
Twilio for communication APIs
SendGrid for email delivery
Ollama for local LLM hosting
FastAPI for web framework

📞 Support

Documentation: docs/
Issues: GitHub Issues
Email: support@yourdomain.com

🗺️ Roadmap

 Mobile app integration
 Advanced analytics dashboard
 Multi-language support
 Video call support
 CRM integrations
 Machine learning improvements


Built with ❤️ for autonomous customer communication

---

## 🎉 **IMPLEMENTATION COMPLETE!**

All 12 suggestion points have been fully implemented:

✅ **1. Webhook Authentication & Security**
✅ **2. Error Handling & Retry Mechanism**
✅ **3. Health Check & Monitoring**
✅ **4. Structured Logging**
✅ **5. Message Queue System**
✅ **6. Delivery Status Tracking**
✅ **7. Analytics & Metrics**
✅ **8. Database Optimization**
✅ **9. Configuration Management**
✅ **10. Docker Deployment**
✅ **11. Systemd Service**
✅ **12. Prometheus & Grafana Monitoring**

**BONUS: Complete Testing Suite**

The system is now **production-ready** with:
- Enterprise-grade security
- High availability
- Comprehensive monitoring
- Automated testing
- Easy deployment
- Scalable architecture