# Deployment

Deployment configurations for various target environments.

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `1panel/` | 1Panel / FusionXplay app package (recommended for FusionXpark GB10) |
| `docker/` | Standalone docker-compose for local testing |
| `helm/` | Helm chart for K3s/Kubernetes (future, for KWeaver Box production) |
| `kwapp/` | Final `.kwapp` packaging spec (future) |

## Deployment Targets (Priority Order)

### 1. FusionXpark GB10 (via 1Panel/FusionXplay)

The primary validation environment. See [`1panel/README.md`](1panel/README.md).

```bash
sudo cp -r 1panel/smart-guide-agent /opt/1panel/resource/apps/local/
# Refresh app store in 1Panel web UI, then click install
```

### 2. Local Development (Docker Compose)

For developers without GB10 access:

```bash
cd docker
docker compose up
```

### 3. KWeaver Box Production (Future)

Will be packaged as a `.kwapp` (Helm chart + KWeaver manifest extension) for one-click install via KWeaver AppHub.

## Hardware Requirements

| Tier | GPU | Memory | Use Case |
|------|-----|--------|----------|
| Minimum | 8GB VRAM (Jetson Orin Nano) | 8GB | Single-user demo |
| Recommended | 16GB VRAM (RTX 4080 / Jetson AGX) | 16GB | 5-10 concurrent users |
| Optimal | DGX Spark (FusionXpark GB10) | 128GB unified | 50+ concurrent users |
