#!/usr/bin/env python3
"""
下载 Sherpa-ONNX 语音模型脚本
支持 ASR (Paraformer) 和 TTS (VITS) 模型自动下载
"""

import os
import sys
import tarfile
import urllib.request
from pathlib import Path

# 模型配置
MODELS = {
    "asr": {
        "name": "Paraformer 中文流式双语 ASR",
        "url": "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-streaming-paraformer-bilingual-zh-en.tar.bz2",
        "dirname": "sherpa-onnx-streaming-paraformer-bilingual-zh-en",
    },
    "tts": {
        "name": "VITS 中文 TTS (fanchen-c)",
        "url": "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-zh-hf-fanchen-c.tar.bz2",
        "dirname": "vits-zh-hf-fanchen-c",
    },
}


def get_models_dir():
    """获取模型存储目录"""
    models_dir = os.environ.get("SHERPA_MODELS_DIR")
    if not models_dir:
        script_dir = Path(__file__).resolve().parent
        models_dir = script_dir.parent / "backend" / "models"
    return Path(models_dir)


def download_and_extract(model_key: str, dest_dir: Path):
    """下载并解压模型"""
    config = MODELS[model_key]
    url = config["url"]
    dirname = config["dirname"]
    tar_path = dest_dir / f"{dirname}.tar.bz2"
    
    # 检查是否已存在解压后的目录
    if (dest_dir / dirname).exists():
        print(f"  ✓ 模型 {config['name']} 已存在，跳过下载")
        return True

    print(f"  下载: {url}")
    dest_dir.mkdir(parents=True, exist_ok=True)

    try:
        # 下载
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=300) as response:
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            chunk_size = 8192
            
            with open(tar_path, 'wb') as f:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        print(f"  进度: {percent:.1f}% ({downloaded / (1024*1024):.1f} MB)", end='\r')
        print("\n  下载完成，正在解压...")
        
        # 解压
        with tarfile.open(tar_path, "r:bz2") as tar:
            tar.extractall(path=dest_dir)
            
        # 清理压缩包
        tar_path.unlink()
        print(f"  ✓ 解压完成")
        return True
        
    except Exception as e:
        print(f"\n  ✗ 下载或解压失败: {e}")
        if tar_path.exists():
            tar_path.unlink()
        return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description="下载 Sherpa-ONNX 模型")
    parser.add_argument("--asr", action="store_true", help="仅下载 ASR 模型")
    parser.add_argument("--tts", action="store_true", help="仅下载 TTS 模型")
    parser.add_argument("--all", action="store_true", help="下载所有模型")
    args = parser.parse_args()

    if not any([args.asr, args.tts, args.all]):
        args.all = True

    models_dir = get_models_dir()
    print(f"存储目录: {models_dir}")

    success = True
    if args.all or args.asr:
        print("\n" + "="*60)
        print(f"下载模型: {MODELS['asr']['name']}")
        print("="*60)
        if not download_and_extract("asr", models_dir):
            success = False

    if args.all or args.tts:
        print("\n" + "="*60)
        print(f"下载模型: {MODELS['tts']['name']}")
        print("="*60)
        if not download_and_extract("tts", models_dir):
            success = False

    if not success:
        print("\n" + "="*60)
        print("✗ 部分模型下载失败，请检查网络连接")
        sys.exit(1)
    else:
        print("\n" + "="*60)
        print("✨ 所有请求的模型均已就绪！")


if __name__ == "__main__":
    main()
