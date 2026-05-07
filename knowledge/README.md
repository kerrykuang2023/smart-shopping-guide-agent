# Product Knowledge Base

Templates and example data for the product knowledge base.

## Structure

Each product is described in YAML following [`schema.yaml`](schema.yaml):

```yaml
sku: "iPhone-15-Pro-256GB-Black"
name: "iPhone 15 Pro 256GB Black Titanium"
category: "Smartphone"
brand: "Apple"
price: 8999.00
images:
  - url: "/images/iphone-15-pro-front.jpg"
  - url: "/images/iphone-15-pro-back.jpg"
specs:
  - "A17 Pro chip"
  - "48MP main camera"
  - "Titanium design"
selling_points:
  - "Pro-grade photography with spatial video"
  - "Lightweight titanium build"
  - "Customizable Action Button"
target_users:
  - "Photography enthusiasts"
  - "Business professionals"
  - "iOS ecosystem users"
related_products:
  - "AirPods Pro 2"
  - "MagSafe Charger"
competitors:
  - sku: "Huawei-Mate-60-Pro"
    our_advantages: ["Video recording quality", "iOS ecosystem"]
    their_advantages: ["Satellite calling", "Faster charging"]
```

## Loading Process

1. Place YAML files in `products/` directory
2. Backend service auto-loads on startup
3. Embeddings generated and stored in Qdrant for semantic search
4. SKU index built for fast direct lookup

## MVP Demo Products (3-5 SKUs)

For initial demo, prepare:
- 3-5 well-known products that are easy to obtain visually
- High-quality reference images (3-5 angles each)
- Comprehensive selling points (5-10 per product)
- 1-2 competitor comparisons each

## Production Considerations

- Integrate with ERP for real-time price/inventory
- Support multi-language (Chinese, English at minimum)
- Versioning of knowledge base for A/B testing of guide scripts
- Admin UI for non-technical content editors
