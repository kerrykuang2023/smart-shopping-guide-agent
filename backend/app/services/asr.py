"""
Sherpa-ONNX ASR Service
基于 Paraformer 的中文流式语音识别
"""

from __future__ import annotations

import io
import wave
import numpy as np
from pathlib import Path
from typing import Optional

try:
    import sherpa_onnx
    SHERPA_AVAILABLE = True
except ImportError:
    SHERPA_AVAILABLE = False

from app.config import get_settings


class ASRService:
    """
    语音识别服务
    使用 Sherpa-ONNX 的 Paraformer 模型进行中文语音识别
    """

    def __init__(self, models_dir: Optional[Path] = None) -> None:
        self.settings = get_settings()
        self.models_dir = models_dir or self.settings.workspace_dir / "backend" / "models"
        self.recognizer = None
        self._initialized = False

    def is_available(self) -> bool:
        """检查 ASR 服务是否可用"""
        if not SHERPA_AVAILABLE:
            return False
        return self._initialized or self._check_models_exist()

    def _check_models_exist(self) -> bool:
        """检查模型文件是否存在"""
        model_dir = self.models_dir / "sherpa-onnx-streaming-paraformer-bilingual-zh-en"
        model_file = model_dir / "encoder.int8.onnx"
        tokens_file = model_dir / "tokens.txt"
        return model_file.exists() and tokens_file.exists()

    def initialize(self) -> bool:
        """初始化识别器"""
        if not SHERPA_AVAILABLE:
            print("[ASR] sherpa_onnx 未安装，ASR 功能不可用")
            return False

        if self._initialized:
            return True

        if not self._check_models_exist():
            print(f"[ASR] 模型文件不存在: {self.models_dir}")
            print("[ASR] 请先运行: python scripts/download_sherpa_models.py --asr")
            return False

        try:
            model_dir = self.models_dir / "sherpa-onnx-streaming-paraformer-bilingual-zh-en"
            model_file = str(model_dir / "encoder.int8.onnx")
            decoder_file = str(model_dir / "decoder.int8.onnx")
            tokens_file = str(model_dir / "tokens.txt")

            # 创建识别器配置
            recognizer_config = sherpa_onnx.OnlineRecognizerConfig(
                feat_config=sherpa_onnx.FeatureExtractorConfig(
                    sampling_rate=16000,
                    feature_dim=80,
                ),
                model_config=sherpa_onnx.OnlineModelConfig(
                    paraformer=sherpa_onnx.OnlineParaformerModelConfig(
                        encoder=model_file,
                        decoder=decoder_file,
                    ),
                    tokens=tokens_file,
                    num_threads=4,
                    provider="cpu",
                    debug=False,
                ),
                decoding_method="greedy_search",
                max_active_paths=4,
                enable_endpoint_detection=True,
                rule1_min_trailing_silence=2.4,
                rule2_min_trailing_silence=1.2,
                rule3_min_utterance_length=300,
            )

            self.recognizer = sherpa_onnx.OnlineRecognizer(recognizer_config)
            self._initialized = True
            print(f"[ASR] 初始化成功，模型: {model_file}")
            return True

        except Exception as e:
            print(f"[ASR] 初始化失败: {e}")
            return False

    def recognize(self, audio_bytes: bytes, sample_rate: int = 16000) -> dict:
        """
        识别音频数据

        Args:
            audio_bytes: WAV 或原始 PCM 音频数据
            sample_rate: 采样率，默认 16000

        Returns:
            dict: {"text": "识别的文字", "success": True/False, "error": "错误信息"}
        """
        if not self._initialized:
            if not self.initialize():
                return {"text": "", "success": False, "error": "ASR 服务未初始化"}

        try:
            # 解析 WAV 文件
            samples = self._parse_audio(audio_bytes, sample_rate)
            if samples is None:
                return {"text": "", "success": False, "error": "音频解析失败"}

            # 创建流式识别流
            stream = self.recognizer.create_stream()
            stream.accept_waveform(sample_rate, samples)

            # 识别
            self.recognizer.decode_stream(stream)
            text = stream.result.text.strip()

            return {
                "text": text,
                "success": True,
                "error": None,
            }

        except Exception as e:
            return {
                "text": "",
                "success": False,
                "error": f"识别失败: {str(e)}",
            }

    def _parse_audio(self, audio_bytes: bytes, target_sample_rate: int) -> Optional[np.ndarray]:
        """解析音频数据为 numpy 数组"""
        try:
            # 尝试作为 WAV 解析
            with io.BytesIO(audio_bytes) as wav_io:
                with wave.open(wav_io, 'rb') as wav_file:
                    # 获取音频参数
                    n_channels = wav_file.getnchannels()
                    sample_width = wav_file.getsampwidth()
                    sample_rate = wav_file.getframerate()
                    n_frames = wav_file.getnframes()

                    # 读取数据
                    raw_data = wav_file.readframes(n_frames)

                    # 转换为 numpy
                    if sample_width == 2:
                        samples = np.frombuffer(raw_data, dtype=np.int16)
                    elif sample_width == 4:
                        samples = np.frombuffer(raw_data, dtype=np.int32)
                    else:
                        return None

                    # 转换为 float32 并归一化
                    samples = samples.astype(np.float32) / 32768.0

                    # 如果是双声道，转为单声道
                    if n_channels == 2:
                        samples = samples[0::2]

                    # 重采样（如果需要）
                    if sample_rate != target_sample_rate:
                        samples = self._resample(samples, sample_rate, target_sample_rate)

                    return samples

        except Exception as e:
            print(f"[ASR] 音频解析失败: {e}")
            return None

    def _resample(
        self,
        samples: np.ndarray,
        orig_sr: int,
        target_sr: int
    ) -> np.ndarray:
        """简单的线性重采样"""
        if orig_sr == target_sr:
            return samples

        # 计算新长度
        new_length = int(len(samples) * target_sr / orig_sr)

        # 线性插值
        indices = np.linspace(0, len(samples) - 1, new_length)
        indices = indices.astype(np.int32)

        return samples[indices]


# 全局 ASR 服务实例
_asr_service: Optional[ASRService] = None


def get_asr_service() -> ASRService:
    """获取 ASR 服务单例"""
    global _asr_service
    if _asr_service is None:
        _asr_service = ASRService()
    return _asr_service
