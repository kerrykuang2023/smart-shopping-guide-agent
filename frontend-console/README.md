# Frontend Console (Server-Side Management UI)

The web-based management console for the Smart Shopping Guide Agent. This is what the **demonstrator/admin** sees on a laptop or desktop.

## Purpose

- **Demo Hub**: Display the QR code for audiences to scan and access the mobile H5
- **Knowledge Base Management**: Add/edit/delete product entries and upload images
- **Model Configuration**: View and tune AI model parameters
- **Activity Monitoring**: View recent recognition logs and statistics
- **System Settings**: Configure ports, paths, demo mode, etc.

## Why a Separate Console

The mobile H5 is for end-users (customers/sales), but during demos and daily operations, the admin needs a desktop-grade interface. Separating the two ensures:

- Mobile UI stays focused and fast
- Desktop UI can handle complex CRUD operations
- Clear access control boundary (future: Console requires login, mobile doesn't)

## Tech Stack

- Vue 3 + Vite
- Element Plus or Naive UI (desktop-grade component library)
- Pinia for state management
- Vue Router for SPA routing
- Axios for API calls

## Pages (Phase 1)

| Page | Path | Priority | Description |
|------|------|---------|-------------|
| Dashboard | `/` | P0 | Service status, today's stats, quick links |
| QR Code Display | `/qr` | **P0** | **Demo核心**: Full-screen QR code for mobile entry |
| Product Management | `/products` | P0 | List, add, edit, delete products + image management |
| Model Settings | `/models` | P1 | View current model, adjust parameters |
| Activity Logs | `/logs` | P1 | Recent recognition logs with thumbnails |
| System Settings | `/settings` | P2 | Port, paths, demo mode toggle, etc. |

## Design Style

- **Modern enterprise dashboard** (think Coolify, Vercel Dashboard, 1Panel V2)
- Dark mode + blue/purple gradient accents
- Clean spacing, large typography
- Animated transitions

## QR Code Page (Most Important for Demo)

This is the page that sells the product. Requirements:

- QR code must be at least **350×350 px**
- Auto-detect server LAN IP, regenerate QR on IP change
- Show backup URL text below QR (in case scan fails)
- Show contextual tips: "Connect to same WiFi", "Allow camera access"
- Live counter of scans (positive feedback during demo)
- Full-screen mode (hide sidebar) for projection

## Quick Start

```bash
npm install
npm run dev
# Console will be available at http://localhost:5173
# It will proxy API calls to backend at http://localhost:8080
```

## Build for Production

```bash
npm run build
# Output goes to dist/
# In production, FastAPI serves dist/ at root path /
```

## Status

> Phase 1 - To be implemented
