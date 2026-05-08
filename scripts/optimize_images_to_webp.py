from __future__ import annotations

from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
IMAGE_DIR = ROOT / "knowledge" / "images"
PRODUCT_DIR = ROOT / "knowledge" / "products"


def convert_images() -> set[str]:
    converted: set[str] = set()
    for path in IMAGE_DIR.iterdir():
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
            continue
        webp_path = path.with_suffix(".webp")
        if webp_path.exists() and path.suffix.lower() == ".webp":
            converted.add(path.stem)
            continue

        with Image.open(path) as img:
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGB")
            img.save(webp_path, format="WEBP", quality=78, method=6)
        converted.add(path.stem)
    return converted


def rewrite_yaml_refs(converted_stems: set[str]) -> int:
    updates = 0
    for yaml_path in PRODUCT_DIR.glob("*.yaml"):
        content = yaml_path.read_text(encoding="utf-8")
        new_content = content
        for stem in converted_stems:
            new_content = new_content.replace(f"/images/{stem}.jpg", f"/images/{stem}.webp")
            new_content = new_content.replace(f"/images/{stem}.jpeg", f"/images/{stem}.webp")
            new_content = new_content.replace(f"/images/{stem}.png", f"/images/{stem}.webp")
        if new_content != content:
            yaml_path.write_text(new_content, encoding="utf-8")
            updates += 1
    return updates


def main() -> None:
    converted = convert_images()
    touched = rewrite_yaml_refs(converted)
    print(f"Converted image stems: {len(converted)}")
    print(f"Updated YAML files: {touched}")


if __name__ == "__main__":
    main()

