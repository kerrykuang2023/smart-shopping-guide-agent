from __future__ import annotations

import socket
from io import BytesIO

import qrcode


def detect_lan_ip() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
    except OSError:
        ip = "127.0.0.1"
    finally:
        sock.close()
    return ip


def build_mobile_url(request_host: str, request_port: int, detected_lan_ip: str | None = None) -> str:
    host = request_host.strip("[]")
    if host in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}:
        host = detected_lan_ip or detect_lan_ip()
    return f"http://{host}:{request_port}/m/"


def build_qr_png(url: str, size: int = 320) -> bytes:
    qr = qrcode.QRCode(version=None, box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    img = img.resize((size, size))
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()

