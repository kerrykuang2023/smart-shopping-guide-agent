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
    - provider=mock: 无 VLM 时可「随机命中」用于纯本地演示（由 mock_always_pick_sku 控制）
    - provider=qwen: placeholder hook for future Qwen2.5-VL runtime integration
    """

    def __init__(self, provider: str = "mock", *, mock_always_pick_sku: bool = False) -> None:
        self.provider = provider
        self.mock_always_pick_sku = mock_always_pick_sku

    @staticmethod
    def openai_chat_completions_url(base_url: str) -> str:
        """OpenAI 兼容接口：POST {root}/v1/chat/completions（vLLM 常用）。"""
        endpoint = base_url.strip().rstrip("/")
        if not endpoint.endswith("/v1/chat/completions"):
            endpoint = f"{endpoint}/v1/chat/completions"
        return endpoint

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

        if self.mock_always_pick_sku:
            return RecognitionResult(sku=choice(allowed_skus), confidence=0.88, reason="mock_provider_random_sku")
        return RecognitionResult(sku=None, confidence=0.0, reason="mock_no_vlm_url")

    @staticmethod
    def build_recognition_prompt(allowed_skus: list[str]) -> str:
        """与 _recognize_via_http 发往 VLM 的文本完全一致，供前端 / 运维调试展示。"""
        return (
            "你是展区「签字笔/中性笔」识别助手。仅当画面里能较清晰看出与下列某一款陈列笔对应时，输出 JSON："
            '{"sku":"<列表中的 SKU 或 null>","confidence":0.0-1.0}。\n'
            f"可选 SKU（只能从中选或填 null）: {', '.join(allowed_skus)}。\n"
            "规则：若画面不是笔、无法确认是下列某一款、或主体与笔无关，必须输出 \"sku\": null，confidence 建议 ≤0.35；"
            "严禁在不确定时从列表里猜一个 SKU。"
        )

    @staticmethod
    def build_recognition_api_trace(
        *,
        vlm_base_url: str,
        vlm_model: str,
        allowed_skus: list[str],
        image_bytes: bytes,
        recognizer_reason: str,
    ) -> dict:
        """H5 「雷达页」展示的调用说明：含完整 user 文本 prompt、messages 结构与图片占位（不落盘 base64）。"""
        prompt = RecognizerService.build_recognition_prompt(allowed_skus)
        b64_len = len(base64.b64encode(image_bytes))
        img_note = (
            f"data:image/png;base64,<omitted — {b64_len} encoded chars "
            f"from {len(image_bytes)} bytes upload>"
        )
        msg_structure = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": img_note}},
                ],
            }
        ]
        if not (vlm_base_url or "").strip():
            return {
                "phase": "local_fallback",
                "note": "vlm_base_url 为空，未发起远端 HTTP；以下为若启用 VLM 时等同的请求体语义。",
                "http": None,
                "vlm_model": vlm_model,
                "temperature": 0,
                "messages": msg_structure,
                "user_text_prompt": prompt,
                "allowed_skus": list(allowed_skus),
                "upload": {"bytes": len(image_bytes)},
                "recognizer_reason": recognizer_reason,
            }
        endpoint = RecognizerService.openai_chat_completions_url(vlm_base_url)
        return {
            "phase": "openai_compatible_vlm",
            "note": "POST 体与 RecognizerService 真实调用一致（图片仅以占位表示，避免 JSON 臃肿）。",
            "http": {"method": "POST", "url": endpoint},
            "headers_shape": {
                "Content-Type": "application/json",
                "Authorization": "Bearer <runtime vlm_api_key or omitted>",
            },
            "vlm_model": vlm_model,
            "temperature": 0,
            "messages": msg_structure,
            "user_text_prompt": prompt,
            "allowed_skus": list(allowed_skus),
            "upload": {"bytes": len(image_bytes)},
            "recognizer_reason": recognizer_reason,
        }

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
        endpoint = RecognizerService.openai_chat_completions_url(vlm_base_url)

        b64_image = base64.b64encode(image_bytes).decode("utf-8")
        prompt = RecognizerService.build_recognition_prompt(allowed_skus)
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
        sku, confidence = parsed
        if sku is None:
            return RecognitionResult(sku=None, confidence=confidence, reason="remote_vlm_no_catalog_match")
        return RecognitionResult(sku=sku, confidence=confidence, reason="remote_vlm")

    @staticmethod
    def _parse_recognition_content(content: str, allowed_skus: list[str]) -> tuple[str | None, float] | None:
        """返回 (sku, conf)；sku 为 None 表示模型明确判定未命中库内款。无法解析时返回 None。"""

        def _norm_sku(raw: object) -> str | None:
            if raw is None:
                return None
            if isinstance(raw, str):
                s = raw.strip()
                if s.lower() in ("", "null", "none", "无", "undefined"):
                    return None
                return s
            return str(raw).strip() or None

        # Prefer strict JSON format.
        try:
            payload = json.loads(content)
            sku = _norm_sku(payload.get("sku"))
            confidence = float(payload.get("confidence", 0.5))
            confidence = max(0.0, min(confidence, 1.0))
            if sku is None:
                return None, confidence
            if sku in allowed_skus:
                return sku, confidence
            return None, min(confidence, 0.35)
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

        # Relaxed parsing fallback.
        for sku in allowed_skus:
            if sku in content:
                match = re.search(r"(0(?:\.\d+)?|1(?:\.0+)?)", content)
                confidence = float(match.group(1)) if match else 0.7
                return sku, max(0.0, min(confidence, 1.0))
        return None

