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
docker-compose -f deployment/docker/docker-compose.yml up -d
```

Or use the convenience script:

```bash
./scripts/start.sh
```

> `scripts/start.sh`/`stop.sh`/`logs.sh` support both `docker-compose` and `docker compose` automatically.

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
| `./knowledge` → `/app/knowledge` | Product YAML + images |
| `./backend/models` → `/app/backend/models` | **Sherpa ASR/TTS** — persisted so updates skip re-download (see entrypoint below) |
| `./logs` → `/app/logs` | Runtime logs |
| `./data` → `/app/data` | **`runtime-settings.json`**（Console 里配置的 VLM/LLM 地址等）— 更新镜像或拉代码后仍保留 |

环境变量 **`RUNTIME_SETTINGS_FILE=/app/data/runtime-settings.json`**（compose 已默认）将运行时配置写入该文件。

若你过去把配置写在 `backend/logs/runtime-settings.json`，可一次性迁移到宿主机：

`cp backend/logs/runtime-settings.json data/runtime-settings.json`（路径按实际仓库根调整）。

## First deploy vs upgrade (models)

The container **`entrypoint.sh`** runs before Uvicorn:

- **首次启动**（宿主机 `./backend/models` 里还没有 ASR/TTS 目录或为空）：自动执行 `download_sherpa_models.py --all`，把模型写入该卷。
- **之后更新镜像**（卷里已有 `sherpa-onnx-streaming-paraformer-bilingual-zh-en` 与 `vits-zh-hf-fanchen-c`）：**跳过下载**，直接启动。

| Variable | Effect |
|----------|--------|
| `SKIP_SHERPA_DOWNLOAD=1` | 不检查、不下载（离线镜像已内置模型时用） |
| `FORCE_SHERPA_DOWNLOAD=1` | 删除上述两个目录后**强制重新下载**（慎用） |

镜像构建阶段**不再**下载模型，因此 `docker compose build` 不会因 TTS/ASR 体积反复拉网。

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
