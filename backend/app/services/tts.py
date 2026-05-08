"""
Sherpa-ONNX TTS Service
基于 VITS 的中文语音合成
"""

from __future__ import annotations

import io
import wave
from pathlib import Path
from typing import Optional

try:
    import sherpa_onnx
    SHERPA_AVAILABLE = True
except ImportError:
    SHERPA_AVAILABLE = False

from app.config import get_settings


class TTSService:
    """
    语音合成服务
    使用 Sherpa-ONNX 的 VITS 模型进行中文语音合成
    """

    def __init__(self, models_dir: Optional[Path] = None) -> None:
        self.settings = get_settings()
        self.models_dir = models_dir or self.settings.workspace_dir / "backend" / "models"
        self.tts_engine = None
        self._initialized = False

    def is_available(self) -> bool:
        """检查 TTS 服务是否可用"""
        if not SHERPA_AVAILABLE:
            return False
        return self._initialized or self._check_models_exist()

    def _check_models_exist(self) -> bool:
        """检查模型文件是否存在"""
        model_dir = self.models_dir / "vits-zh-hf-fanchen-c"
        required_files = [
            model_dir / "vits-zh-hf-fanchen-C.onnx",
            model_dir / "tokens.txt",
            model_dir / "lexicon.txt",
            model_dir / "dict",
        ]
        return all(f.exists() for f in required_files)

    def initialize(self) -> bool:
        """初始化 TTS 引擎"""
        if not SHERPA_AVAILABLE:
            print("[TTS] sherpa_onnx 未安装，TTS 功能不可用")
            return False

        if self._initialized:
            return True

        if not self._check_models_exist():
            print(f"[TTS] 模型文件不存在: {self.models_dir}")
            print("[TTS] 请先运行: python scripts/download_sherpa_models.py --tts")
            return False

        try:
            model_dir = self.models_dir / "vits-zh-hf-fanchen-c"
            model_file = str(model_dir / "vits-zh-hf-fanchen-C.onnx")
            tokens_file = str(model_dir / "tokens.txt")
            lexicon_file = str(model_dir / "lexicon.txt")
            dict_dir = str(model_dir / "dict")

            # 创建 TTS 配置
            tts_config = sherpa_onnx.OfflineTtsConfig(
                model=sherpa_onnx.OfflineTtsModelConfig(
                    vits=sherpa_onnx.OfflineTtsVitsModelConfig(
                        model=model_file,
                        lexicon=lexicon_file,
                        tokens=tokens_file,
                        data_dir=dict_dir,
                    ),
                    provider="cpu",
                    debug=False,
                    num_threads=4,
                ),
                rule_fsts="",
                rule_fars="",
                max_num_sentences=1,
            )

            self.tts_engine = sherpa_onnx.OfflineTts(tts_config)
            self._initialized = True
            print(f"[TTS] 初始化成功，模型: {model_file}")
            return True

        except Exception as e:
            print(f"[TTS] 初始化失败: {e}")
            return False

    def synthesize(
        self,
        text: str,
        sid: int = 0,
        speed: float = 1.0,
    ) -> dict:
        """
        合成语音

        Args:
            text: 要合成的文本（中文）
            sid: 说话人 ID（默认为 0）
            speed: 语速，1.0 为正常语速

        Returns:
            dict: {
                "audio_bytes": WAV 音频数据,
                "sample_rate": 采样率,
                "success": True/False,
                "error": "错误信息"
            }
        """
        if not self._initialized:
            if not self.initialize():
                return {
                    "audio_bytes": None,
                    "sample_rate": 0,
                    "success": False,
                    "error": "TTS 服务未初始化",
                }

        try:
            # 合成音频
            audio = self.tts_engine.generate(
                text=text,
                sid=sid,
                speed=speed,
            )

            if audio.samples is None or len(audio.samples) == 0:
                return {
                    "audio_bytes": None,
                    "sample_rate": 0,
                    "success": False,
                    "error": "合成失败，无音频数据",
                }

            # 转换为 WAV 格式
            wav_bytes = self._samples_to_wav(
                samples=audio.samples,
                sample_rate=audio.sample_rate,
            )

            return {
                "audio_bytes": wav_bytes,
                "sample_rate": audio.sample_rate,
                "success": True,
                "error": None,
            }

        except Exception as e:
            return {
                "audio_bytes": None,
                "sample_rate": 0,
                "success": False,
                "error": f"合成失败: {str(e)}",
            }

    def _samples_to_wav(self, samples, sample_rate: int) -> bytes:
        """将音频样本转换为 WAV 字节"""
        # 归一化到 int16 范围
        samples_int16 = (samples * 32767).astype("int16")

        # 创建 WAV 文件
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # 单声道
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(samples_int16.tobytes())

        return wav_buffer.getvalue()


# 全局 TTS 服务实例
_tts_service: Optional[TTSService] = None


def get_tts_service() -> TTSService:
    """获取 TTS 服务单例"""
    global _tts_service
    if _tts_service is None:
        _tts_service = TTSService()
    return _tts_service
