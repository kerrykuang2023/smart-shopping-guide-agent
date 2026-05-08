# Frontend H5 (Mobile Web App)

Mobile-optimized Vue 3 web app accessed by **scanning the QR code** displayed on the Console. End-users (customers, sales staff) interact with this app on their phones.

## Why H5 First (Phase 1)

- **Zero install**: scan QR → instant access (the demo "wow moment")
- **Cross-platform**: works on iPhone, Android, tablets
- **Fast iteration**: code changes deploy instantly
- **Lower demo barrier**: any audience phone can experience the product

## Entry Point

**The Console displays a QR code** (route `/qr`) pointing to this H5 app. End-users scan to access:

```
Console QR Code  →  http://<server-ip>:8080/m
                          │
                          ▼
                 Mobile H5 (this app)
```

## Tech Stack

- Vue 3 + Vite
- Vant (mobile-optimized component library)
- WebRTC `getUserMedia` for camera access
- Axios for HTTP, native WebSocket for chat
- TypeScript

## Pages (Phase 1)

| Page | Path | Priority | Description |
|------|------|---------|-------------|
| Camera | `/m/` | P0 | Live camera preview + capture button |
| Result | `/m/result/:sku` | P0 | Image-rich product card + AI guide + recommendations |
| Chat | `/m/chat/:sku` | P1 | Follow-up Q&A with streaming responses |

## Image-First Design Principles

This app is **image-heavy by design**. Every screen prioritizes images over text:

- **Product hero image**: full-width, 16:9 or 4:3
- **Gallery**: horizontal scrollable thumbnails
- **Selling points**: each can have an associated image
- **Related products**: grid of image cards (not text list)
- **Competitor comparison**: side-by-side images

### Image Loading Strategy

- **Lazy loading**: `<img loading="lazy">` + IntersectionObserver
- **Responsive sizes**: request `?w=200` for thumbnails, `?w=800` for full
- **WebP first**: send `Accept: image/webp` header
- **Placeholder**: blurred LQIP while loading
- **Cache aggressively**: leverage browser cache for repeated views

## Camera Considerations

### Required Permissions

```javascript
navigator.mediaDevices.getUserMedia({
  video: { facingMode: 'environment' }  // Prefer rear camera
})
```

### HTTPS Requirement

Camera access requires HTTPS on real devices (Chrome/Safari). For dev:

- Use `mkcert` for local trusted certificates
- Or use `vite-plugin-mkcert` for one-step setup
- Or test via `localhost` (HTTPS not required)

### Permission Denied Fallback

If camera permission is denied, show:
- Friendly explanation
- "Upload from photo album" button as backup
- Link to permission settings

## Development

```bash
npm install
npm run dev
# H5 served at http://localhost:5174 (configured in vite.config.ts)
```

For real-device testing:
1. Find your dev machine's LAN IP (e.g. `192.168.1.50`)
2. Configure Vite to bind `0.0.0.0` (already in vite.config.ts)
3. On phone, open `http://192.168.1.50:5174` (must be on same WiFi)

## Build & Deploy

```bash
npm run build
# Output to dist/
# In production, FastAPI serves dist/ at /m path
```

The backend is configured to serve this app at `/m`. Make sure:
- Vite `base` is set to `/m/` in `vite.config.ts`
- Vue Router uses `createWebHistory('/m/')`
- All asset URLs are relative

## Browser Compatibility

| Browser | Status |
|---------|--------|
| iOS Safari 14+ | ✅ Full support |
| Android Chrome 90+ | ✅ Full support |
| Wechat in-app browser | ⚠️ Camera permission may require workaround |
| Older Android browsers | ⚠️ Test individually |

## Status

> Phase 1 - Vue 3 + Vite scaffolding implemented (`src/`, `vite.config.ts`, `package.json`).
