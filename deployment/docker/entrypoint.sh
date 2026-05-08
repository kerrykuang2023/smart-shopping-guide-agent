#!/bin/sh
# 首次部署：模型目录为空 → 下载 Sherpa ASR/TTS。
# 后续部署：卷里已有模型 → 跳过下载，仅启动应用。
# 可选环境变量：
#   SHERPA_MODELS_DIR  模型目录（默认 /app/backend/models，须与运行时 MODELS_DIR 一致）
#   FORCE_SHERPA_DOWNLOAD=1  强制重新下载（覆盖已存在目录需先手动清空）
#   SKIP_SHERPA_DOWNLOAD=1   永远不下載（离线镜像已有模型时用）

set -e

MODEL_DIR="${SHERPA_MODELS_DIR:-/app/backend/models}"
# 与 scripts/download_sherpa_models.py 中 MODELS 的 dirname 保持一致
ASR_DIR="$MODEL_DIR/sherpa-onnx-streaming-paraformer-bilingual-zh-en"
TTS_DIR="$MODEL_DIR/vits-zh-hf-fanchen-c"

asr_ready() {
  [ -d "$ASR_DIR" ] && [ -n "$(ls -A "$ASR_DIR" 2>/dev/null | head -1)" ]
}

tts_ready() {
  [ -d "$TTS_DIR" ] && [ -n "$(ls -A "$TTS_DIR" 2>/dev/null | head -1)" ]
}

if [ "${SKIP_SHERPA_DOWNLOAD:-0}" = "1" ]; then
  echo "[entrypoint] SKIP_SHERPA_DOWNLOAD=1 — 跳过模型检查与下载。"
elif [ "${FORCE_SHERPA_DOWNLOAD:-0}" = "1" ]; then
  echo "[entrypoint] FORCE_SHERPA_DOWNLOAD=1 — 将删除已有 ASR/TTS 目录并重新下载..."
  rm -rf "$ASR_DIR" "$TTS_DIR"
  mkdir -p "$MODEL_DIR"
  export SHERPA_MODELS_DIR="$MODEL_DIR"
  python /app/scripts/download_sherpa_models.py --all
elif asr_ready && tts_ready; then
  echo "[entrypoint] 已在 $MODEL_DIR 检测到 ASR/TTS 模型 — 跳过下载（后续部署快速启动）。"
else
  echo "[entrypoint] 首次部署或模型不完整 — 正在下载模型到 $MODEL_DIR ..."
  mkdir -p "$MODEL_DIR"
  export SHERPA_MODELS_DIR="$MODEL_DIR"
  python /app/scripts/download_sherpa_models.py --all
fi

exec "$@"
