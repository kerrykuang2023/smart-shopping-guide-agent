from fastapi.testclient import TestClient

from app.main import app
from app.models import RuntimeSettingsUpdate
from app.services.qr import build_qr_png, build_mobile_url


def test_runtime_settings_accept_model_urls_keys_and_models():
    payload = RuntimeSettingsUpdate(
        vlm_base_url="http://gb10:9000",
        public_base_url="http://192.168.1.8:8080",
        vlm_api_key="vlm-key",
        vlm_model="Qwen/Qwen2.5-VL-7B-Instruct",
        llm_base_url="http://gb10:9001",
        llm_api_key="llm-key",
        llm_model="qwen-plus",
        tts_base_url="http://gb10:9002",
        tts_api_key="tts-key",
        tts_model="cosyvoice",
        asr_base_url="http://gb10:9003",
        asr_api_key="asr-key",
        asr_model="sensevoice",
    )

    assert payload.llm_api_key == "llm-key"
    assert payload.public_base_url == "http://192.168.1.8:8080"
    assert payload.tts_model == "cosyvoice"
    assert payload.asr_base_url == "http://gb10:9003"


def test_mobile_url_uses_lan_ip_when_request_host_is_localhost():
    url = build_mobile_url(request_host="localhost", request_port=8080, detected_lan_ip="192.168.1.8")

    assert url == "http://192.168.1.8:8080/m/"


def test_qr_png_is_large_enough_to_be_a_real_qr_code():
    png = build_qr_png("http://192.168.1.8:8080/m/", size=320)

    assert png.startswith(b"\x89PNG")
    assert len(png) > 1000


def test_chat_endpoint_returns_knowledge_based_fallback_answer():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/chat",
            json={"sku": "pilot-g2-black-0.7", "message": "和晨光 K35 比怎么样？"},
        )

    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert data["mocked"] is True

