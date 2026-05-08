# Product Knowledge Base

YAML-based product knowledge for the Smart Shopping Guide Agent.

## Structure

```
knowledge/
├── schema.yaml            # Schema definition (v0.2 - image-first)
├── products/              # Individual product YAML files (one per SKU)
│   ├── chenguang-k35.yaml
│   ├── deli-s01.yaml
│   ├── pilot-g2.yaml
│   ├── hero-359.yaml
│   └── stabilo-boss.yaml
└── images/                # All product images (see images/README.md)
```

Each product file follows [`schema.yaml`](schema.yaml) — refer to that file for the full field list.

## Phase 1 Demo SKUs — Locked

> **Theme: 文具签字笔（"signing pens" everywhere）**
> Easy to obtain, hard to break, rich product stories, real B2B scenario alignment.

| # | SKU | 品牌 | 类型 | 价位 | YAML |
|---|-----|------|------|------|------|
| 1 | 晨光优品 K35 中性笔 | 晨光（中国） | 中性笔 0.5mm | ¥2.5 | [chenguang-k35.yaml](products/chenguang-k35.yaml) |
| 2 | 得力 S01 中性笔 | 得力（中国） | 中性笔 0.5mm | ¥3 | [deli-s01.yaml](products/deli-s01.yaml) |
| 3 | PILOT 百乐 G2 中性笔 | PILOT（日本） | 中性笔 0.7mm | ¥18 | [pilot-g2.yaml](products/pilot-g2.yaml) |
| 4 | 英雄 359 钢笔 | 英雄（中国） | 钢笔 / 铱金笔尖 | ¥45 | [hero-359.yaml](products/hero-359.yaml) |
| 5 | Stabilo Boss 荧光笔 | Stabilo（德国） | 荧光笔 | ¥12 | [stabilo-boss.yaml](products/stabilo-boss.yaml) |

### Why these 5

| Dimension | Coverage |
|----------|----------|
| **Price gradient** | ¥2.5 → ¥45 (18× difference, demonstrates AI's price-agnostic recognition) |
| **Category diversity** | 3 gel pens + 1 fountain pen + 1 highlighter |
| **Country of origin** | 3 China + 1 Japan + 1 Germany (international brand recognition) |
| **Story richness** | Each pen has historical / technical / cultural narratives |
| **Cross-recommendations** | Notebooks, refills, ink, pouches — natural bundle opportunities |
| **Customer scenario fit** | 晨光生活馆 / 九木杂物社 / 大学书店 / 高端礼品店 / 校园书店 all covered |

## Loading Process

1. Place YAML files in `products/` directory
2. Backend service auto-loads on startup (file watcher reloads in dev mode)
3. Embeddings are generated for `name`, `selling_points`, and `use_cases` and stored in Qdrant for semantic search
4. SKU index built for fast direct lookup
5. Image references are validated; missing images logged as warnings

## Image Strategy

See [`images/README.md`](images/README.md) for the full image plan including:
- Naming conventions
- Per-SKU image checklist (~10–15 images per pen)
- DIY photo setup guide
- Official brand image sources

**Day 1 critical deliverable**: Take 25 self-shot photos (5 pens × 5 angles).

## Adding a New Product

1. Create `products/<sku>.yaml` following the schema
2. Add corresponding images to `images/` directory
3. Restart backend (or wait for hot reload)
4. Verify the SKU appears in the Console product list
5. Test recognition by photographing the actual product

## Production Considerations

- Integrate with ERP/PIM for real-time price and inventory
- Multi-language (Chinese, English at minimum) via i18n keys
- Versioning of knowledge base for A/B testing of guide scripts
- Admin UI for non-technical content editors (planned for Phase 2)
- Content moderation pipeline before publishing to production AppHub
