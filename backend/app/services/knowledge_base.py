from __future__ import annotations

from pathlib import Path
from typing import Iterable

import yaml

from app.models import Product


class KnowledgeBaseService:
    def __init__(self, products_dir: Path) -> None:
        self.products_dir = products_dir
        self._products: dict[str, Product] = {}

    def load(self) -> int:
        self._products.clear()
        for path in sorted(self.products_dir.glob("*.yaml")):
            product = self._load_product(path)
            self._products[product.sku] = product
        return len(self._products)

    def list_products(self) -> list[Product]:
        return list(self._products.values())

    def get_product(self, sku: str) -> Product | None:
        return self._products.get(sku)

    def any_product(self) -> Product | None:
        if not self._products:
            return None
        first_key = next(iter(self._products.keys()))
        return self._products[first_key]

    def all_skus(self) -> Iterable[str]:
        return self._products.keys()

    @staticmethod
    def _load_product(path: Path) -> Product:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return Product.model_validate(data)

