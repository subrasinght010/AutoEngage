# 1. Install dependencies
pip install -r requirements.txt

# 2. Setup Ollama (recommended for testing)
curl -fsSL https://ollama.com/install.sh | sh
ollama pull mistral

# 3. Initialize RAG knowledge base
python scripts/setup_rag.py

# 4. Test RAG queries
python scripts/test_rag.py

# 5. Setup database
alembic upgrade head

# 6. Start Ollama server (in separate terminal)
ollama serve

# 7. Run FastAPI server
python main.py

# Or with uvicorn:
uvicorn main:app --host 0.0.0.0 --port 8080 --reload