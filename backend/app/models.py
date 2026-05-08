from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ProductRef(BaseModel):
    sku: str
    name: str
    image: str
    price: float | None = None
    bundle_discount: float | None = None
    reason: str | None = None
    our_advantages: list[str] | None = None
    their_advantages: list[str] | None = None


class GalleryImage(BaseModel):
    url: str
    angle: str | None = None
    caption: str | None = None


class SellingPoint(BaseModel):
    text: str
    image: str | None = None


class Product(BaseModel):
    sku: str
    name: str
    category: str
    brand: str
    price: float | None = None
    primary_image: str
    gallery: list[GalleryImage] = Field(default_factory=list)
    selling_points: list[SellingPoint] = Field(default_factory=list)
    specs: list[str] = Field(default_factory=list)
    target_users: list[str] = Field(default_factory=list)
    use_cases: list[str] = Field(default_factory=list)
    related_products: list[ProductRef] = Field(default_factory=list)
    competitors: list[ProductRef] = Field(default_factory=list)
    promotions: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GuideSegment(BaseModel):
    title: str
    text: str
    image: str | None = None


class RecognitionResponse(BaseModel):
    sku: str | None = None
    confidence: float = 0.0
    recognized: bool = True  # 是否成功识别商品库中的商品
    message: str = ""  # 未识别时的提示消息
    mocked: bool = False
    product: Product | None = None
    guide_segments: list[GuideSegment] = Field(default_factory=list)
    related_products: list[ProductRef] = Field(default_factory=list)
    competitors: list[ProductRef] = Field(default_factory=list)


class ProductListResponse(BaseModel):
    count: int
    items: list[Product]


class HealthResponse(BaseModel):
    status: str
    version: str
    demo_mode: bool
    loaded_products: int
    vlm_provider: str
    timestamp: datetime


class ActivityLogEntry(BaseModel):
    timestamp: datetime
    action: str
    sku: str | None = None
    confidence: float | None = None
    mocked: bool = False
    client_ip: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class RuntimeSettings(BaseModel):
    public_base_url: str = ""
    vlm_base_url: str = ""
    vlm_api_key: str = ""
    vlm_model: str = "GLM-4.5V"
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = "qwen-plus"
    qdrant_url: str = ""
    qdrant_api_key: str = ""
    apphub_url: str = ""
    tts_base_url: str = ""
    tts_api_key: str = ""
    tts_model: str = "cosyvoice"
    asr_base_url: str = ""
    asr_api_key: str = ""
    asr_model: str = "sensevoice"
    updated_at: datetime | None = None


class RuntimeSettingsUpdate(BaseModel):
    public_base_url: str | None = None
    vlm_base_url: str | None = None
    vlm_api_key: str | None = None
    vlm_model: str | None = None
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None
    qdrant_url: str | None = None
    qdrant_api_key: str | None = None
    apphub_url: str | None = None
    tts_base_url: str | None = None
    tts_api_key: str | None = None
    tts_model: str | None = None
    asr_base_url: str | None = None
    asr_api_key: str | None = None
    asr_model: str | None = None


class ChatMessage(BaseModel):
    role: str  # 'user' | 'assistant'
    content: str


class ChatRequest(BaseModel):
    sku: str | None = None  # 可选，不指定时使用通用对话模式
    message: str
    history: list[ChatMessage] = Field(default_factory=list)  # 对话历史


class ChatResponse(BaseModel):
    sku: str | None = None
    answer: str
    mocked: bool = False
    source: str = "knowledge_base"  # knowledge_base, remote_llm, general_knowledge


class TestConnectionRequest(BaseModel):
    service_type: str  # vlm, llm, tts, asr


class TestConnectionResponse(BaseModel):
    success: bool
    message: str
    latency_ms: int


class VoiceChatRequest(BaseModel):
    sku: str
    audio_base64: str  # WAV 音频数据的 base64 编码


class VoiceChatResponse(BaseModel):
    sku: str
    recognized_text: str  # ASR 识别的用户语音
    answer_text: str  # LLM 的文本回复
    audio_base64: str  # TTS 合成的回复语音 (base64 WAV)
    success: bool
    mocked: bool = False
    source: str = "knowledge_base"
    error: str | None = None


class ASRResponse(BaseModel):
    text: str
    success: bool
    error: str | None = None


class TTSRequest(BaseModel):
    text: str
    speed: float = 1.0


class TTSResponse(BaseModel):
    audio_base64: str
    sample_rate: int
    success: bool
    error: str | None = None

