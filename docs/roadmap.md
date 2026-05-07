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
- [ ] Choose 3-5 demo SKUs (recommend: 1-2 phones + 1-2 appliances or accessories)
- [ ] Prepare 5-8 images per SKU (hero, gallery, selling points)
- [ ] Write product YAML files following schema
- [ ] Optimize all images (compress, WebP)

### Deployment
- [ ] Single Dockerfile with all dependencies
- [ ] Docker Compose for local dev
- [ ] README with one-command run

### Internal Demo
- [ ] End-to-end test on real phones (iOS + Android)
- [ ] Stakeholder demo rehearsal
- [ ] Polish based on feedback

**Success Criteria**: Stakeholder demo where they scan QR with their own phone, point at a product, and see image-rich AI guide in <5s.

---

## Phase 2: Native App + 1Panel Production (Week 2-3)

**Goal**: Production-ready Android app + 1Panel deployment.

- [ ] Flutter project scaffolding
- [ ] Camera + photo capture (native)
- [ ] Product detail page with image carousel
- [ ] Real-time chat WebSocket
- [ ] Offline knowledge base cache (Hive/Drift)
- [ ] Local image cache
- [ ] TTS for voice playback
- [ ] Backend: Performance optimization (vLLM if needed)
- [ ] Backend: Multi-image angle support for recognition
- [ ] 1Panel app package (data.yml + docker-compose.yml + scripts)
- [ ] Test on FusionXpark GB10
- [ ] Internal training video for sales team

**Success Criteria**: Install via 1Panel in <10min, customer-facing demo on Android tablet.

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
