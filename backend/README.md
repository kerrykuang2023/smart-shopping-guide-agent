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

## API Endpoints (Phase 1 Implemented)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/health` | Health check for monitoring |
| GET | `/api/v1/products` | List all products in knowledge base |
| GET | `/api/v1/products/{sku}` | Get specific product details |
| POST | `/api/v1/recognize` | Upload image → return SKU + guide + recommendations |
| GET | `/api/v1/qrcode` | Generate PNG QR code for mobile H5 entry (`/m`) |
| GET | `/api/v1/logs` | Recent activity logs for Console |
| GET | `/api/v1/settings` | Read runtime URL placeholders |
| PUT | `/api/v1/settings` | Update runtime URL placeholders |
| GET | `/images/{filename}` | Static image hosting with optional resize (`w`, `q`) |

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run service (from backend/)
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

### Environment Variables

| Key | Default | Description |
|-----|---------|-------------|
| `DEMO_MODE` | `true` | Recognition failures are gracefully mocked for stable demos |
| `RECOGNITION_CONFIDENCE_THRESHOLD` | `0.6` | Confidence gate before fallback |
| `VLM_PROVIDER` | `mock` | `mock` or `qwen` (placeholder hook) |
| `WORKSPACE_DIR` | auto-detected | Project root |
| `KNOWLEDGE_PRODUCTS_DIR` | `knowledge/products` | YAML product directory |
| `IMAGE_DIR` | `knowledge/images` | Image directory |

### Runtime URL Placeholders (Console)

The Console provides UI fields for:
- `vlm_base_url`
- `llm_base_url`
- `qdrant_url`
- `apphub_url`

Current behavior:
- If `vlm_base_url` is configured, recognition will try OpenAI-compatible endpoint  
  `POST {vlm_base_url}/v1/chat/completions` (unless URL already ends with that path).
- If remote VLM call fails, service falls back according to `DEMO_MODE`.

## Docker Deployment

```bash
docker build -t smart-guide-agent:0.1.0 .
docker run --gpus all -p 8080:8080 \
  -v $(pwd)/data/models:/app/models \
  -v $(pwd)/data/knowledge:/app/knowledge \
  smart-guide-agent:0.1.0
```

## Status

> Phase 1 backend scaffold is running with PRD-aligned APIs.  
> Next: Qwen2.5-VL real inference integration + Qdrant retrieval + frontend scaffolds.
