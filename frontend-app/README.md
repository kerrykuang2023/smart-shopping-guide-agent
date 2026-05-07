# Frontend Native App (Enterprise Deployment)

Flutter-based native app for production deployment in retail stores, dealerships, etc.

> Begin development in **Phase 2 (Week 2-3)** after H5 validation succeeds.

## Why Flutter

- **One codebase**: Android + iOS + tablet from a single Dart codebase
- **Native performance**: closer to native than React Native
- **Beautiful UI**: Material 3 + Cupertino out of the box
- **Hardware access**: camera, scanner, NFC, BLE all supported

## Features Beyond H5

| Feature | H5 | Native App |
|---------|-----|-----------|
| Offline knowledge base | ❌ | ✅ |
| Local model cache | ❌ | ✅ |
| Barcode scanner integration | ❌ | ✅ |
| Voice wake word ("Hi K") | ❌ | ✅ |
| 24/7 kiosk mode | ❌ | ✅ |
| Receipt printer integration | ❌ | ✅ |
| OTA updates via 1Panel | ❌ | ✅ |

## Tech Stack

- Flutter 3.x
- `camera` plugin for camera access
- `dio` for HTTP, `web_socket_channel` for chat
- `flutter_tts` or local TTS for audio playback
- `hive` or `drift` for offline cache
- `flutter_barcode_scanner` for SKU scanning

## Status

> Phase 2 - Planned, not started yet
