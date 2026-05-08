from __future__ import annotations

import ssl
import urllib.request
from pathlib import Path


TARGET_DIR = Path(__file__).resolve().parents[1] / "knowledge" / "images"

IMAGE_SOURCES = {
    # 晨光 K35
    "chenguang-k35-hero.jpg": "https://imgservice.suning.cn/uimg1/b2c/image/kCuKMuuJyNwOwTq6x4fOnQ.png",
    "chenguang-k35-front.jpg": "https://imgservice.suning.cn/uimg1/b2c/image/FW7l90V6UMD8FItwF6AVkQ.png",
    "chenguang-k35-tip.jpg": "https://imgservice.suning.cn/uimg1/b2c/image/_Pdd7KXesY32pDu6sN9U1g.png",
    "chenguang-k35-clip.jpg": "https://imgservice.suning.cn/uimg1/b2c/image/ujYT08yp4W6vd2KHIEt1ow.png",
    "chenguang-k35-writing.jpg": "https://imgservice.suning.cn/uimg1/b2c/image/YaCn1ZCsTUcZW3ovMom50g.png",

    # 得力 S01
    "deli-s01-hero.jpg": "https://imgservice.suning.cn/uimg1/b2c/image/FSS0bvbF7lqZyyMNam4Fwg.jpg_800w_800h_4e",
    "deli-s01-front.jpg": "https://imgservice.suning.cn/uimg1/b2c/image/-nkwrT97b4Qe20vCJGf_yg.jpg_800w_800h_4e",
    "deli-s01-tip.jpg": "https://imgservice.suning.cn/uimg1/b2c/image/savuWnzgV0WGVAf1FItn-A.jpg_800w_800h_4e",
    "deli-s01-clip.jpg": "https://imgservice.suning.cn/uimg1/b2c/image/NNUxwLl-gM-QdattXgDQFA.jpg_800w_800h_4e",
    "deli-s01-writing.jpg": "https://imgservice.suning.cn/uimg1/b2c/image/1ccNOzci_UwFCGfqMIa5zQ.jpg_800w_800h_4e",

    # PILOT G2
    "pilot-g2-hero.jpg": "https://uimgproxy.suning.cn/uimg1/sop/commodity/zomqBf0vj-toUZwJp1SdPg.jpg",
    "pilot-g2-front.jpg": "https://uimgproxy.suning.cn/uimg1/sop/commodity/HwZxqev6Jh_Icjnmkw6ELA.jpg",
    "pilot-g2-tip.jpg": "https://uimgproxy.suning.cn/uimg1/sop/commodity/SM6NKtUCkaM2z4uBTr3mXA.jpg",
    "pilot-g2-grip.jpg": "https://uimgproxy.suning.cn/uimg1/sop/commodity/PyBB77HSZ0Q8rrsfrcHF4w.jpg",
    "pilot-g2-writing.jpg": "https://uimgproxy.suning.cn/uimg1/sop/commodity/27jENGdK_LflgHSHswjemA.jpg",
    "pilot-g2-package.jpg": "https://uimgproxy.suning.cn/uimg1/sop/commodity/qXUE9GBx8GP4w8sXjzVbAA.jpg",

    # 英雄 359
    "hero-359-hero.jpg": "https://imgservice.suning.cn/uimg1/b2c/image/IBKjjLsHSQBXirsmmaCaZQ.jpg_800w_800h_4e",
    "hero-359-front.jpg": "https://imgservice.suning.cn/uimg1/b2c/image/myYosjQjCUQZLmy0B4zAJA.jpg_800w_800h_4e",
    "hero-359-nib.jpg": "https://imgservice.suning.cn/uimg1/b2c/image/LlPho0NGQ8b6djPOlGG7Cg.jpg_800w_800h_4e",
    "hero-359-cap.jpg": "https://imgservice.suning.cn/uimg1/b2c/image/TWyBbL5kAEvWbqAvF_ajGw.jpg_800w_800h_4e",
    "hero-359-writing.jpg": "https://imgservice.suning.cn/uimg1/b2c/image/inNKjUyOSrkUW1gStbYS4w.jpg_800w_800h_4e",

    # STABILO Boss
    "stabilo-boss-hero.jpg": "https://upload.wikimedia.org/wikipedia/commons/c/ca/STABILO_BOSS_Original1.jpg",
    "stabilo-boss-front.jpg": "https://upload.wikimedia.org/wikipedia/commons/9/95/Stabilo_Sortiment.jpeg",
    "stabilo-boss-colors.jpg": "https://upload.wikimedia.org/wikipedia/commons/c/ca/STABILO_BOSS_Original1.jpg",
}


def download_file(name: str, url: str) -> bool:
    target = TARGET_DIR / name
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            },
        )
        with urllib.request.urlopen(req, timeout=25, context=ssl.create_default_context()) as resp:
            data = resp.read()
        target.write_bytes(data)
        print(f"[OK] {name} ({len(data)} bytes)")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] {name}: {exc}")
        return False


def main() -> None:
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    ok = 0
    for name, url in IMAGE_SOURCES.items():
        if download_file(name, url):
            ok += 1
    print(f"Downloaded {ok}/{len(IMAGE_SOURCES)} images into {TARGET_DIR}")


if __name__ == "__main__":
    main()

