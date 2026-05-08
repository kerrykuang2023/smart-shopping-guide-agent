#!/usr/bin/env python3
"""
下载 Sherpa-ONNX 语音模型脚本
支持 ASR (Paraformer) 和 TTS (Matcha) 模型自动下载
"""

import os
import sys
import hashlib
import requests
from pathlib import Path
from urllib.parse import urlparse

# 模型配置
MODELS = {
    "asr": {
        "name": "Paraformer 中文流式双语 ASR",
        "files": [
            {
                "url": "https://huggingface.co/csukuangfj/sherpa-onnx-streaming-paraformer-bilingual-zh-en/resolve/main/model.int8.onnx",
                "filename": "paraformer-zh-en.int8.onnx",
                "size_mb": 75,
            },
            {
                "url": "https://huggingface.co/csukuangfj/sherpa-onnx-streaming-paraformer-bilingual-zh-en/resolve/main/tokens.txt",
                "filename": "paraformer-zh-en-tokens.txt",
                "size_mb": 0.1,
            },
        ],
    },
    "tts": {
        "name": "Matcha 中文 TTS",
        "files": [
            {
                "url": "https://huggingface.co/csukuangfj/matcha-icefall-zh-baker/resolve/main/model-steps-112000.onnx",
                "filename": "matcha-zh.onnx",
                "size_mb": 50,
            },
            {
                "url": "https://huggingface.co/csukuangfj/matcha-icefall-zh-baker/resolve/main/lexicon.txt",
                "filename": "matcha-zh-lexicon.txt",
                "size_mb": 2,
            },
            {
                "url": "https://huggingface.co/csukuangfj/matcha-icefall-zh-baker/resolve/main/tokens.txt",
                "filename": "matcha-zh-tokens.txt",
                "size_mb": 0.1,
            },
            {
                "url": "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vocos-22khz-univ.onnx",
                "filename": "vocos-22khz.onnx",
                "size_mb": 20,
            },
        ],
    },
}


def get_models_dir():
    """获取模型存储目录"""
    # 优先使用环境变量，否则使用默认路径
    models_dir = os.environ.get("SHERPA_MODELS_DIR")
    if not models_dir:
        # 默认放在 backend/models 目录
        script_dir = Path(__file__).resolve().parent
        models_dir = script_dir.parent / "backend" / "models"
    return Path(models_dir)


def download_file(url: str, dest_path: Path, expected_size_mb: float = None):
    """下载文件并显示进度"""
    print(f"  下载: {url}")
    print(f"  目标: {dest_path}")

    if dest_path.exists():
        local_size = dest_path.stat().st_size / (1024 * 1024)
        if expected_size_mb and abs(local_size - expected_size_mb) < 1:
            print(f"  ✓ 文件已存在 ({local_size:.1f} MB)，跳过下载")
            return True
        else:
            print(f"  文件存在但大小不符，重新下载...")

    try:
        response = requests.get(url, stream=True, timeout=300)
        response.raise_for_status()

        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        chunk_size = 8192

        dest_path.parent.mkdir(parents=True, exist_ok=True)

        with open(dest_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        print(f"  进度: {percent:.1f}% ({downloaded / (1024*1024):.1f} MB)", end='\r')

        print(f"\n  ✓ 下载完成 ({dest_path.stat().st_size / (1024*1024):.1f} MB)")
        return True

    except Exception as e:
        print(f"\n  ✗ 下载失败: {e}")
        if dest_path.exists():
            dest_path.unlink()
        return False


def download_model(model_type: str):
    """下载指定类型的模型"""
    if model_type not in MODELS:
        print(f"未知的模型类型: {model_type}")
        print(f"可用类型: {', '.join(MODELS.keys())}")
        return False

    model_info = MODELS[model_type]
    models_dir = get_models_dir()

    print(f"\n{'='*60}")
    print(f"下载模型: {model_info['name']}")
    print(f"存储目录: {models_dir}")
    print(f"{'='*60}")

    all_success = True
    for file_info in model_info["files"]:
        dest_path = models_dir / file_info["filename"]
        success = download_file(
            file_info["url"],
            dest_path,
            file_info.get("size_mb")
        )
        if not success:
            all_success = False

    return all_success


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(
        description="下载 Sherpa-ONNX 语音模型",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python download_sherpa_models.py --all          # 下载所有模型
  python download_sherpa_models.py --asr          # 仅下载 ASR 模型
  python download_sherpa_models.py --tts          # 仅下载 TTS 模型
  SHERPA_MODELS_DIR=/path/to/models python download_sherpa_models.py --all
        """
    )
    parser.add_argument("--all", action="store_true", help="下载所有模型")
    parser.add_argument("--asr", action="store_true", help="下载 ASR 模型")
    parser.add_argument("--tts", action="store_true", help="下载 TTS 模型")
    parser.add_argument("--list", action="store_true", help="列出可用模型")

    args = parser.parse_args()

    if args.list:
        print("\n可用模型:")
        for model_type, info in MODELS.items():
            print(f"\n  [{model_type}] {info['name']}")
            total_size = sum(f.get("size_mb", 0) for f in info["files"])
            print(f"       总大小: ~{total_size:.1f} MB")
            for f in info["files"]:
                print(f"       - {f['filename']} (~{f.get('size_mb', '?')} MB)")
        print()
        return

    if not any([args.all, args.asr, args.tts]):
        parser.print_help()
        return

    success = True

    if args.all or args.asr:
        if not download_model("asr"):
            success = False

    if args.all or args.tts:
        if not download_model("tts"):
            success = False

    print(f"\n{'='*60}")
    if success:
        print("✓ 所有模型下载完成")
        models_dir = get_models_dir()
        print(f"  模型目录: {models_dir}")
    else:
        print("✗ 部分模型下载失败，请检查网络连接")
        sys.exit(1)
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
