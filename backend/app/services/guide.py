from __future__ import annotations

from app.models import GuideSegment, Product


class GuideService:
    """Generate deterministic demo-friendly guide segments from product data."""

    def generate_segments(self, product: Product, style: str = "professional") -> list[GuideSegment]:
        style_prefix = {
            "professional": "专业解读",
            "friendly": "亲切推荐",
            "concise": "快速总结",
        }.get(style, "专业解读")

        segments: list[GuideSegment] = [
            GuideSegment(
                title=f"{style_prefix}：产品定位",
                text=f"{product.name} 属于 {product.category}，品牌为 {product.brand}。"
                + (f" 当前参考价约 ¥{product.price:g}。" if product.price else ""),
                image=product.primary_image,
            )
        ]

        for idx, point in enumerate(product.selling_points[:3], start=1):
            segments.append(
                GuideSegment(
                    title=f"核心卖点 {idx}",
                    text=point.text,
                    image=point.image or product.primary_image,
                )
            )

        if product.use_cases:
            segments.append(
                GuideSegment(
                    title="适用场景",
                    text="、".join(product.use_cases[:3]),
                    image=product.gallery[0].url if product.gallery else product.primary_image,
                )
            )

        return segments[:5]

