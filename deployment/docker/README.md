# Docker Deployment

The **primary deployment method for Demo Phase**. Single docker-compose command to run the full stack on FusionXpark GB10 or any GPU machine.

## Files

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Main orchestration |
| `Dockerfile` | Multi-stage build (frontend + backend) |
| `.env.example` | Environment variable template |
| `nginx.conf` | (Optional) reverse proxy config for HTTPS |

## Quick Start

```bash
# From project root
docker compose -f deployment/docker/docker-compose.yml up -d
```

Or use the convenience script:

```bash
./scripts/start.sh
```

## What Gets Deployed

A single container running:

- FastAPI backend on port 8080
- Qwen2.5-VL-7B model (loaded into GPU memory)
- Embedded Qdrant for vector search
- Console SPA at `/`
- Mobile H5 SPA at `/m`
- Image hosting at `/images/*`

## Environment Variables

See `.env.example` for the full list. Key variables:

| Variable | Default | Purpose |
|----------|---------|---------|
| `DEMO_MODE` | `true` | Enable graceful fallback on errors |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `MODEL_NAME` | `Qwen/Qwen2.5-VL-7B-Instruct` | Vision-language model to load |
| `HF_ENDPOINT` | `https://huggingface.co` | Set to `https://hf-mirror.com` for China |
| `HOST` | `0.0.0.0` | Bind address |
| `PORT` | `8080` | Service port |

## Volumes

| Mount | Purpose |
|-------|---------|
| `./knowledge` → `/app/knowledge` | Product YAML + images (read-only by default) |
| `./models` → `/app/models` | Model cache (persisted to avoid re-download) |
| `./logs` → `/app/logs` | Runtime logs |

## GPU Requirements

The container requires **NVIDIA Container Toolkit** to be installed on the host:

```bash
# Verify
docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi
```

If this fails, install nvidia-container-toolkit:
https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html

## Status

> Phase 1 - Skeleton in place; full implementation in progress.
