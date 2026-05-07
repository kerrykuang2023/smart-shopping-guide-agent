# Backend Service

FastAPI-based backend service running on the edge compute box (FusionXpark GB10 / DGX Spark / etc.).

## Responsibilities

- **Vision Recognition**: Use Qwen2.5-VL to identify product SKU from uploaded images
- **Knowledge Base Query**: Look up product info from local knowledge base
- **Sales Guide Generation**: Use LLM to generate professional product narration
- **Conversational Q&A**: WebSocket-based real-time chat about products
- **Text-to-Speech**: Stream audio guide for hands-free experience

## Tech Stack

- Python 3.11+
- FastAPI (HTTP + WebSocket)
- Transformers + Qwen2.5-VL (vision-language model)
- Qdrant (vector DB for knowledge base)
- vLLM (optimized inference, optional)

## API Endpoints (Planned)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/recognize` | Upload image → return product info + guide |
| WS | `/chat/{sku}` | Real-time Q&A about a specific product |
| GET | `/products` | List all products in knowledge base |
| GET | `/products/{sku}` | Get specific product details |
| POST | `/products` | Add new product to knowledge base (admin) |
| GET | `/tts?text=...` | Text-to-speech streaming |
| GET | `/health` | Health check for monitoring |

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run service
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

## Docker Deployment

```bash
docker build -t smart-guide-agent:0.1.0 .
docker run --gpus all -p 8080:8080 \
  -v $(pwd)/data/models:/app/models \
  -v $(pwd)/data/knowledge:/app/knowledge \
  smart-guide-agent:0.1.0
```

## Status

> Phase 1 - MVP under development
