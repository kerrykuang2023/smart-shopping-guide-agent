from __future__ import annotations

import base64
import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from io import BytesIO
from random import choice

from PIL import Image


@dataclass
class RecognitionResult:
    sku: str | None
    confidence: float
    reason: str


class RecognizerService:
    """
    Phase-1 recognizer:
    - provider=mock: deterministic/random fallback for demo stability
    - provider=qwen: placeholder hook for future Qwen2.5-VL runtime integration
    """

    def __init__(self, provider: str = "mock") -> None:
        self.provider = provider

    def recognize(
        self,
        image_bytes: bytes,
        allowed_skus: list[str],
        vlm_base_url: str = "",
        vlm_api_key: str = "",
        vlm_model: str = "Qwen/Qwen2.5-VL-7B-Instruct",
    ) -> RecognitionResult:
        if not allowed_skus:
            return RecognitionResult(sku=None, confidence=0.0, reason="no_sku_configured")

        # Minimal image validation to satisfy upload constraints in PRD.
        image = Image.open(BytesIO(image_bytes))
        image.verify()

        if vlm_base_url.strip():
            result = self._recognize_via_http(
                image_bytes=image_bytes,
                vlm_base_url=vlm_base_url.strip(),
                vlm_api_key=vlm_api_key.strip(),
                allowed_skus=allowed_skus,
                vlm_model=vlm_model,
            )
            if result:
                return result
            return RecognitionResult(sku=None, confidence=0.0, reason="remote_vlm_unreachable_or_invalid")

        if self.provider == "qwen":
            # TODO: Integrate Qwen2.5-VL-7B inference pipeline here.
            # For now this returns low confidence to trigger demo-mode fallback if enabled.
            return RecognitionResult(sku=None, confidence=0.2, reason="qwen_stub_not_ready")

        # Mock mode: stable demo path.
        return RecognitionResult(sku=choice(allowed_skus), confidence=0.88, reason="mock_provider")

    def _recognize_via_http(
        self,
        image_bytes: bytes,
        vlm_base_url: str,
        vlm_api_key: str,
        allowed_skus: list[str],
        vlm_model: str,
    ) -> RecognitionResult | None:
        """
        Tries OpenAI-compatible VLM endpoint:
        POST {base}/v1/chat/completions
        Response content should contain one of allowed SKUs.
        """
        endpoint = vlm_base_url.rstrip("/")
        if not endpoint.endswith("/v1/chat/completions"):
            endpoint = f"{endpoint}/v1/chat/completions"

        b64_image = base64.b64encode(image_bytes).decode("utf-8")
        prompt = (
            "你是商品识别助手。仅从下面 SKU 中选择最可能的一个，并输出 JSON："
            '{"sku":"...", "confidence":0.0-1.0}。'
            f"可选 SKU: {', '.join(allowed_skus)}。"
            "如果不确定，confidence 小于 0.5。"
        )
        payload = {
            "model": vlm_model,
            "temperature": 0,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{b64_image}"},
                        },
                    ],
                }
            ],
        }
        headers = {"Content-Type": "application/json"}
        if vlm_api_key:
            headers["Authorization"] = f"Bearer {vlm_api_key}"
        request = urllib.request.Request(
            url=endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                body = response.read().decode("utf-8")
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
            return None

        try:
            data = json.loads(body)
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, json.JSONDecodeError):
            return None

        parsed = self._parse_recognition_content(content, allowed_skus)
        if parsed is None:
            return None
        return RecognitionResult(sku=parsed[0], confidence=parsed[1], reason="remote_vlm")

    @staticmethod
    def _parse_recognition_content(content: str, allowed_skus: list[str]) -> tuple[str, float] | None:
        # Prefer strict JSON format.
        try:
            payload = json.loads(content)
            sku = payload.get("sku")
            confidence = float(payload.get("confidence", 0.5))
            if sku in allowed_skus:
                return sku, max(0.0, min(confidence, 1.0))
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

        # Relaxed parsing fallback.
        for sku in allowed_skus:
            if sku in content:
                match = re.search(r"(0(?:\.\d+)?|1(?:\.0+)?)", content)
                confidence = float(match.group(1)) if match else 0.7
                return sku, max(0.0, min(confidence, 1.0))
        return None

