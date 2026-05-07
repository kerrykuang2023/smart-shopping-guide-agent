# Roadmap

## Phase 1: MVP H5 Demo (Week 1)

**Goal**: Prove the concept with a working H5 demo that any phone can use.

- [ ] Backend: FastAPI scaffolding with mock data
- [ ] Backend: Integrate Qwen2.5-VL for image recognition
- [ ] Backend: Build 3-5 product knowledge base entries
- [ ] Backend: LLM-based guide generation
- [ ] H5: Camera capture + image upload
- [ ] H5: Product card display
- [ ] H5: Basic chat for follow-up questions
- [ ] Deploy: Run on a single Docker container, accessible from LAN

**Success Criteria**: Stakeholder demo where they pick up a phone, point at a product, and see AI-generated guide in <5s.

## Phase 2: Native App + Production Polish (Week 2-3)

**Goal**: Production-ready Android app + 1Panel deployment.

- [ ] Flutter: Project scaffolding
- [ ] Flutter: Camera + photo capture
- [ ] Flutter: Product detail page with TTS playback
- [ ] Flutter: Real-time chat WebSocket
- [ ] Flutter: Offline knowledge base cache
- [ ] Backend: TTS streaming endpoint
- [ ] Backend: Performance optimization (vLLM if needed)
- [ ] Backend: Multi-image angle support
- [ ] Deploy: 1Panel app package
- [ ] Deploy: Test on FusionXpark GB10

**Success Criteria**: Install via 1Panel in <10min, customer-facing demo on Android tablet.

## Phase 3: Knowledge Expansion (Week 4-6)

**Goal**: Scale to 100+ SKUs and integrate with enterprise systems.

- [ ] Knowledge base admin UI (web)
- [ ] CSV/Excel import for bulk SKU upload
- [ ] ERP integration adapter (one major Chinese ERP)
- [ ] Real-time price/inventory sync
- [ ] Multi-language support (Chinese + English)
- [ ] ROI dashboard (recognitions, conversions, customer feedback)
- [ ] Admin role management

**Success Criteria**: First paying customer pilot with their own SKU catalog.

## Phase 4: Advanced Features (Quarter 2)

**Goal**: Differentiation through advanced AI capabilities.

- [ ] Voice wake word ("Hi K") + ASR
- [ ] Conversational checkout flow
- [ ] Personalized recommendations (anonymized profiling)
- [ ] AR product info overlay
- [ ] Multi-modal: voice + image + text
- [ ] Conversion analytics (recognition → purchase tracking)
- [ ] A/B testing of guide scripts
- [ ] Edge fine-tuning (small adapter models per store)

## Phase 5: KWeaver Box Integration (Quarter 2-3)

**Goal**: Package as the flagship `.kwapp` for KWeaver Box AppHub.

- [ ] Refactor to `.kwapp` packaging spec
- [ ] Helm chart conversion
- [ ] Multi-tenant support (one box, multiple stores)
- [ ] OTA updates via KWeaver Box Fleet Manager
- [ ] Cross-store insights via KWeaver DIP
- [ ] Submit to KWeaver AppHub marketplace
