# Frontend H5 (Quick Validation)

Lightweight Vue 3 web app for fast demo and validation. **Use this for the first 1-2 weeks to validate the concept with stakeholders before building native app.**

## Why H5 First

- **Zero install**: scan QR code, instant access
- **Cross-platform**: works on iPhone, Android, tablets, even desktop
- **Fast iteration**: code changes deploy instantly, no app rebuild
- **Lower barrier**: easy to share with non-technical stakeholders for demo

## Tech Stack

- Vue 3 + Vite
- Vant UI (mobile-first component library) or Element Plus
- WebRTC `getUserMedia` for camera access
- Axios for API calls
- WebSocket for real-time chat

## Features (Phase 1)

- [ ] Camera capture (后置摄像头优先)
- [ ] Image upload to backend `/recognize`
- [ ] Display product card (image, name, specs, selling points)
- [ ] Text-to-speech playback (`/tts` streaming)
- [ ] Follow-up Q&A via WebSocket `/chat/{sku}`
- [ ] Competitor comparison view
- [ ] Related product recommendations

## Quick Start

```bash
npm install
npm run dev
# Open http://<your-IP>:5173 from your phone
```

## Important Notes

- HTTPS required for camera access on real devices (use `mkcert` or ngrok for dev)
- For LAN access from phones, ensure dev server binds to `0.0.0.0`
- Test on both iOS Safari and Android Chrome

## Status

> Phase 1 - MVP under development
