# Roadmap

## Phase 1: MVP H5 Demo (Week 1)

**Goal**: Prove the concept with a working H5 demo that any phone can use via QR code scan.

### Backend
- [ ] FastAPI scaffolding with proper project structure
- [ ] Static file mounts for Console (`/`) and H5 (`/m`)
- [ ] Image hosting at `/images/*` with dynamic resize + WebP support
- [ ] Qwen2.5-VL-7B integration for visual recognition
- [ ] YAML-based knowledge base loader
- [ ] Qdrant embedded mode for related products
- [ ] LLM-based guide generation with image references
- [ ] QR code generation API (auto-detect LAN IP)
- [ ] Demo mode (graceful degradation on errors)
- [ ] Activity logging
- [ ] Health check endpoint

### Frontend Console (frontend-console/)
- [ ] Vue 3 + Vite project scaffolding
- [ ] Element Plus or Naive UI integration
- [ ] Dashboard page (service status + stats)
- [ ] **QR Code page (full-screen, demo-critical)**
- [ ] Product management (list/edit + image upload)
- [ ] Activity logs viewer
- [ ] Settings page (demo mode toggle)

### Frontend H5 (frontend-h5/)
- [ ] Vue 3 + Vite + Vant scaffolding
- [ ] Camera capture page with WebRTC `getUserMedia`
- [ ] Image upload to backend
- [ ] **Image-rich product result page (hero + gallery + selling points with images)**
- [ ] Related products grid (image cards)
- [ ] Competitor comparison view
- [ ] Mobile-optimized navigation

### Knowledge Base
- [x] **Choose demo SKUs: 5 signing pens (locked)** — 晨光 K35 / 得力 S01 / PILOT G2 / 英雄 359 / Stabilo Boss
- [x] Write product YAML files following schema (5 files in `knowledge/products/`)
- [ ] Take 25 self-shot photos (5 pens × 5 angles: hero / front / tip / clip / writing)
- [ ] Source ~30 brand/related/competitor images from official websites
- [ ] Optimize all images (compress to <300KB, WebP conversion)
- [ ] Verify image references in YAML files all resolve

### Deployment (Direct Docker on FusionXpark GB10)
- [ ] Multi-stage Dockerfile (frontend build + backend runtime)
- [ ] docker-compose.yml with GPU support, volumes, healthcheck
- [ ] `.env.example` with all configurable parameters
- [ ] Convenience scripts: `start.sh`, `stop.sh`, `logs.sh`, `preload-models.sh`
- [ ] Deployment guide for FusionXpark GB10
- [ ] **NOT building .kwapp or 1Panel app for Phase 1** (deferred)

### Internal Demo
- [ ] End-to-end test on real phones (iOS + Android)
- [ ] Stakeholder demo rehearsal
- [ ] Polish based on feedback

**Success Criteria**: Stakeholder demo where they scan QR with their own phone, point at a product, and see image-rich AI guide in <5s.

---

## Phase 2: Native App + Production Polish (Week 2-3)

**Goal**: Production-ready Android app + hardened Docker deployment.

- [ ] Flutter project scaffolding
- [ ] Camera + photo capture (native)
- [ ] Product detail page with image carousel
- [ ] Real-time chat WebSocket
- [ ] Offline knowledge base cache (Hive/Drift)
- [ ] Local image cache
- [ ] TTS for voice playback
- [ ] Backend: Performance optimization (vLLM if needed)
- [ ] Backend: Multi-image angle support for recognition
- [ ] Docker Compose: split services (backend + Qdrant + future Nginx)
- [ ] Production hardening: HTTPS, JWT auth for Console, rate limiting
- [ ] Test on FusionXpark GB10 with real customer SKUs
- [ ] Evaluate (and decide) whether to package as 1Panel app for Phase 3
- [ ] Internal training video for sales team

**Success Criteria**: Customer-facing demo on Android tablet, installed via single docker compose command in <10min.

---

## Phase 3: Knowledge Expansion + Enterprise Integration (Week 4-6)

**Goal**: Scale to 100+ SKUs and integrate with enterprise systems.

- [ ] Console: Knowledge base bulk import (CSV/Excel)
- [ ] Console: ERP integration adapter (one major Chinese ERP)
- [ ] Real-time price/inventory sync
- [ ] Console: Admin role management
- [ ] Console: Multi-language support (Chinese + English)
- [ ] Console: ROI dashboard
- [ ] Backend: Per-tenant knowledge isolation
- [ ] Backend: A/B testing framework for guide scripts
- [ ] First paying customer pilot

**Success Criteria**: First paying customer pilot with their own SKU catalog (50+ SKUs).

---

## Phase 4: Advanced Features (Quarter 2)

**Goal**: Differentiation through advanced AI capabilities.

- [ ] Voice wake word ("Hi K") + ASR
- [ ] Conversational checkout flow
- [ ] Personalized recommendations (anonymized profiling)
- [ ] AR product info overlay
- [ ] Multi-modal: voice + image + text simultaneously
- [ ] Conversion analytics (recognition → purchase tracking)
- [ ] A/B testing of guide scripts (live)
- [ ] Edge fine-tuning (small adapter models per store)

---

## Phase 5: KWeaver Box Integration (Quarter 2-3)

**Goal**: Package as the flagship `.kwapp` for KWeaver Box AppHub.

- [ ] Refactor to `.kwapp` packaging spec
- [ ] Helm chart conversion (compatible with K3s)
- [ ] manifest.kweaver.yaml definition
- [ ] Multi-tenant support (one box, multiple stores)
- [ ] OTA updates via KWeaver Box Fleet Manager
- [ ] Cross-store insights via KWeaver DIP
- [ ] Submit to KWeaver AppHub marketplace as featured app
- [ ] Marketing case study + ROI whitepaper
