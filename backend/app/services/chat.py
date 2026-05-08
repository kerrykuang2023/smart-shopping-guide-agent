from __future__ import annotations

import json
import urllib.error
import urllib.request

from app.models import Product, RuntimeSettings


class ChatService:
    def answer(self, product: Product, message: str, settings: RuntimeSettings) -> tuple[str, bool, str]:
        if settings.llm_base_url.strip():
            remote = self._answer_with_remote_llm(product, message, settings)
            if remote:
                return remote, False, "remote_llm"

        return self._answer_with_knowledge(product, message), True, "knowledge_base"

    @staticmethod
    def _answer_with_knowledge(product: Product, message: str) -> str:
        points = "；".join(point.text for point in product.selling_points[:3])
        competitors = "；".join(
            f"{item.name}：我们的优势是{'、'.join(item.our_advantages or [])}"
            for item in product.competitors[:2]
        )
        related = "、".join(item.name for item in product.related_products[:3])
        return (
            f"关于“{message}”，我建议这样看：{product.name} 的核心卖点是{points}。"
            f"如果需要对比，{competitors or '当前知识库暂未配置更详细竞品信息'}。"
            f"搭配推荐可以看：{related or '暂无搭配推荐'}。"
        )

    @staticmethod
    def _answer_with_remote_llm(product: Product, message: str, settings: RuntimeSettings) -> str | None:
        endpoint = settings.llm_base_url.rstrip("/")
        if not endpoint.endswith("/v1/chat/completions"):
            endpoint = f"{endpoint}/v1/chat/completions"

        product_context = product.model_dump()
        payload = {
            "model": settings.llm_model,
            "temperature": 0.2,
            "messages": [
                {
                    "role": "system",
                    "content": "你是门店金牌导购。只能基于给定商品知识库回答，不要虚构库存、价格或促销。",
                },
                {
                    "role": "user",
                    "content": f"商品知识库：{json.dumps(product_context, ensure_ascii=False)}\n顾客问题：{message}",
                },
            ],
        }
        headers = {"Content-Type": "application/json"}
        if settings.llm_api_key:
            headers["Authorization"] = f"Bearer {settings.llm_api_key}"
        req = urllib.request.Request(endpoint, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
        except (urllib.error.URLError, TimeoutError, OSError, KeyError, IndexError, json.JSONDecodeError):
            return None

