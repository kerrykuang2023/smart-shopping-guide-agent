from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from PIL import Image

from app.config import get_settings
from app.models import (
    ActivityLogEntry,
    ASRResponse,
    ChatRequest,
    ChatResponse,
    HealthResponse,
    ProductListResponse,
    RecognitionResponse,
    RuntimeSettings,
    RuntimeSettingsUpdate,
    TestConnectionRequest,
    TestConnectionResponse,
    TTSRequest,
    TTSResponse,
    VoiceChatRequest,
    VoiceChatResponse,
)
from app.services.activity_log import ActivityLogService
from app.services.asr import get_asr_service
from app.services.chat import ChatService
from app.services.guide import GuideService
from app.services.knowledge_base import KnowledgeBaseService
from app.services.qr import build_mobile_url, build_qr_png
from app.services.recognizer import RecognizerService
from app.services.runtime_settings import RuntimeSettingsService
from app.services.tts import get_tts_service

settings = get_settings()
knowledge_service = KnowledgeBaseService(settings.knowledge_products_dir)
guide_service = GuideService()
recognizer_service = RecognizerService(provider=settings.vlm_provider)
activity_log_service = ActivityLogService()
runtime_settings_service = RuntimeSettingsService(settings.logs_dir / "runtime-settings.json")
chat_service = ChatService()

app = FastAPI(title=settings.app_name, version=settings.app_version)


def _resolve_static_root(candidates: list[Path], fallback_dir_name: str) -> Path:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    fallback = Path(__file__).resolve().parents[1] / "static" / fallback_dir_name
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def _mount_static_apps() -> None:
    project_root = settings.workspace_dir
    console_root = _resolve_static_root(
        [project_root / "frontend-console" / "dist"],
        fallback_dir_name="console",
    )
    mobile_root = _resolve_static_root(
        [project_root / "frontend-h5" / "dist"],
        fallback_dir_name="mobile",
    )

    app.mount("/console", StaticFiles(directory=str(console_root), html=True), name="console")
    app.mount("/m", StaticFiles(directory=str(mobile_root), html=True), name="mobile_h5")


@app.on_event("startup")
def startup_event() -> None:
    loaded = knowledge_service.load()
    runtime_settings_service.load()
    activity_log_service.seed_startup()
    activity_log_service.add(
        ActivityLogEntry(
            timestamp=datetime.utcnow(),
            action="knowledge_loaded",
            details={"count": loaded},
        )
    )
    _mount_static_apps()


@app.get("/")
def root_console_entry() -> RedirectResponse:
    return RedirectResponse(url="/console")


@app.get("/api/v1/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        demo_mode=settings.demo_mode,
        loaded_products=len(knowledge_service.list_products()),
        vlm_provider=settings.vlm_provider,
        timestamp=datetime.utcnow(),
    )


@app.get("/api/v1/products", response_model=ProductListResponse)
def list_products() -> ProductListResponse:
    products = knowledge_service.list_products()
    return ProductListResponse(count=len(products), items=products)


@app.get("/api/v1/products/{sku}")
def get_product(sku: str):
    product = knowledge_service.get_product(sku)
    if product is None:
        raise HTTPException(status_code=404, detail=f"SKU not found: {sku}")
    return product


@app.post("/api/v1/recognize", response_model=RecognitionResponse)
async def recognize(
    request: Request,
    image: UploadFile = File(...),
    style: str = Query(default="professional"),
) -> RecognitionResponse:
    if image.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status_code=400, detail="Only JPG/PNG/WebP uploads are supported.")

    payload = await image.read()
    if len(payload) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Max image size is 10MB.")

    runtime_settings = runtime_settings_service.get()
    result = recognizer_service.recognize(
        payload,
        list(knowledge_service.all_skus()),
        vlm_base_url=runtime_settings.vlm_base_url,
        vlm_api_key=runtime_settings.vlm_api_key,
        vlm_model=runtime_settings.vlm_model or settings.vlm_model_name,
    )
    mocked = False

    # 识别失败或置信度太低
    if not result.sku or result.confidence < settings.recognition_confidence_threshold:
        # 在非 demo 模式下，返回未识别状态，允许通用对话
        if not settings.demo_mode:
            return RecognitionResponse(
                sku=None,
                confidence=result.confidence,
                recognized=False,
                message="在您的产品库中还未收录该商品，但我可以基于我的知识尽力帮您解答问题。请告诉我您想了解什么？",
                mocked=False,
                product=None,
                guide_segments=[],
                related_products=[],
                competitors=[],
            )
        # demo 模式下随机返回一个产品用于演示
        fallback = knowledge_service.any_product()
        if fallback is None:
            raise HTTPException(status_code=500, detail="Knowledge base is empty.")
        product = fallback
        mocked = True
    else:
        product = knowledge_service.get_product(result.sku)
        if product is None:
            raise HTTPException(status_code=500, detail="Recognized SKU is missing from knowledge base.")

    guide_segments = guide_service.generate_segments(product, style=style)
    response = RecognitionResponse(
        sku=product.sku,
        confidence=result.confidence if not mocked else max(result.confidence, 0.75),
        recognized=True,
        message="",
        mocked=mocked,
        product=product,
        guide_segments=guide_segments,
        related_products=product.related_products,
        competitors=product.competitors,
    )

    activity_log_service.add(
        ActivityLogEntry(
            timestamp=datetime.utcnow(),
            action="recognize",
            sku=product.sku,
            confidence=response.confidence,
            mocked=mocked,
            client_ip=request.client.host if request.client else None,
            details={"filename": image.filename, "provider_reason": result.reason},
        )
    )
    return response


@app.get("/api/v1/qrcode")
def qrcode_endpoint(
    request: Request,
    size: int = Query(default=320, ge=160, le=1024),
) -> Response:
    runtime_settings = runtime_settings_service.get()
    url = (
        f"{runtime_settings.public_base_url.rstrip('/')}/m/"
        if runtime_settings.public_base_url.strip()
        else build_mobile_url(
            request_host=request.url.hostname or "127.0.0.1",
            request_port=request.url.port or settings.app_port,
        )
    )
    png = build_qr_png(url=url, size=size)
    return Response(content=png, media_type="image/png")


@app.get("/api/v1/mobile-url")
def mobile_url_endpoint(request: Request):
    runtime_settings = runtime_settings_service.get()
    if runtime_settings.public_base_url.strip():
        return {"url": f"{runtime_settings.public_base_url.rstrip('/')}/m/"}
    return {
        "url": build_mobile_url(
            request_host=request.url.hostname or "127.0.0.1",
            request_port=request.url.port or settings.app_port,
        )
    }


@app.get("/api/v1/logs")
def recent_logs(limit: int = Query(default=50, ge=1, le=200)):
    return {"count": len(activity_log_service), "items": activity_log_service.recent(limit=limit)}


@app.get("/api/v1/settings", response_model=RuntimeSettings)
def get_runtime_settings() -> RuntimeSettings:
    return runtime_settings_service.get()


@app.put("/api/v1/settings", response_model=RuntimeSettings)
def update_runtime_settings(payload: RuntimeSettingsUpdate) -> RuntimeSettings:
    updated = runtime_settings_service.update(payload)
    activity_log_service.add(
        ActivityLogEntry(
            timestamp=datetime.utcnow(),
            action="runtime_settings_updated",
            details=payload.model_dump(exclude_none=True),
        )
    )
    return updated


@app.post("/api/v1/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    runtime_settings = runtime_settings_service.get()
    
    # 通用对话模式（未指定 SKU 或商品未识别）
    if not payload.sku:
        answer, mocked, source, new_summary, new_history = chat_service.general_answer(
            message=payload.message,
            settings=runtime_settings,
            history=payload.history,
            summary=payload.summary,
        )
        activity_log_service.add(
            ActivityLogEntry(
                timestamp=datetime.utcnow(),
                action="chat",
                sku=None,
                mocked=mocked,
                details={"source": source, "message": payload.message, "mode": "general", "history_length": len(payload.history)},
            )
        )
        return ChatResponse(
            sku=None, 
            answer=answer, 
            mocked=mocked, 
            source=source,
            summary=new_summary,
            history=new_history
        )
    
    # 指定了 SKU，使用产品知识库对话
    product = knowledge_service.get_product(payload.sku)
    if product is None:
        raise HTTPException(status_code=404, detail=f"SKU not found: {payload.sku}")

    answer, mocked, source, new_summary, new_history = chat_service.answer(
        product=product,
        message=payload.message,
        settings=runtime_settings,
        history=payload.history,
        summary=payload.summary,
    )
    activity_log_service.add(
        ActivityLogEntry(
            timestamp=datetime.utcnow(),
            action="chat",
            sku=payload.sku,
            mocked=mocked,
            details={"source": source, "message": payload.message, "history_length": len(payload.history)},
        )
    )
    return ChatResponse(
        sku=payload.sku, 
        answer=answer, 
        mocked=mocked, 
        source=source,
        summary=new_summary,
        history=new_history
    )


@app.get("/images/{filename:path}")
def serve_image(
    filename: str,
    w: int | None = Query(default=None, ge=50, le=2400),
    q: int = Query(default=80, ge=30, le=95),
) -> Response:
    image_path = settings.image_dir / filename
    if not image_path.exists():
        raise HTTPException(status_code=404, detail=f"Image not found: {filename}")

    if w is None:
        return FileResponse(image_path)

    with Image.open(image_path) as img:
        ratio = w / img.width
        h = int(img.height * ratio)
        resized = img.resize((w, h))
        output = BytesIO()
        save_format = "WEBP" if image_path.suffix.lower() != ".png" else "PNG"
        resized.save(output, format=save_format, quality=q)
        media_type = "image/webp" if save_format == "WEBP" else "image/png"
        return Response(content=output.getvalue(), media_type=media_type)


@app.post("/api/v1/test-connection", response_model=TestConnectionResponse)
def test_connection(payload: TestConnectionRequest) -> TestConnectionResponse:
    """Test connection to external AI services (VLM/LLM/TTS/ASR)."""
    import time
    import urllib.request
    import json
    from typing import Literal

    s = runtime_settings_service.get()
    start = time.time()

    service_type = payload.service_type
    base_url = ""
    api_key = ""
    model = ""
    endpoint = ""
    test_payload = {}
    method = "POST"

    if service_type == "vlm":
        base_url = s.vlm_base_url.strip()
        api_key = s.vlm_api_key.strip()
        model = s.vlm_model.strip() or "GLM-4.5V"
        if not base_url:
            return TestConnectionResponse(success=False, message="VLM Base URL 未配置", latency_ms=0)
        endpoint = base_url.rstrip("/") + "/v1/chat/completions"
        test_payload = {
            "model": model,
            "temperature": 0,
            "messages": [{"role": "user", "content": "Hello, this is a test. Reply with 'OK' only."}],
            "max_tokens": 10
        }
    elif service_type == "llm":
        base_url = s.llm_base_url.strip()
        api_key = s.llm_api_key.strip()
        model = s.llm_model.strip() or "qwen-plus"
        if not base_url:
            return TestConnectionResponse(success=False, message="LLM Base URL 未配置", latency_ms=0)
        endpoint = base_url.rstrip("/") + "/v1/chat/completions"
        test_payload = {
            "model": model,
            "temperature": 0,
            "messages": [{"role": "user", "content": "Hello, this is a test. Reply with 'OK' only."}],
            "max_tokens": 10
        }
    elif service_type == "tts":
        base_url = s.tts_base_url.strip()
        api_key = s.tts_api_key.strip()
        if not base_url:
            return TestConnectionResponse(success=False, message="TTS Base URL 未配置", latency_ms=0)
        endpoint = base_url.rstrip("/") + "/v1/models"
        method = "GET"
        test_payload = {}
    elif service_type == "asr":
        base_url = s.asr_base_url.strip()
        api_key = s.asr_api_key.strip()
        if not base_url:
            return TestConnectionResponse(success=False, message="ASR Base URL 未配置", latency_ms=0)
        endpoint = base_url.rstrip("/") + "/v1/models"
        method = "GET"
        test_payload = {}
    else:
        return TestConnectionResponse(success=False, message=f"未知服务类型: {service_type}", latency_ms=0)

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        req = urllib.request.Request(
            url=endpoint,
            data=json.dumps(test_payload).encode("utf-8") if test_payload else None,
            headers=headers,
            method=method
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            _ = resp.read()
            latency = int((time.time() - start) * 1000)
            return TestConnectionResponse(
                success=True,
                message=f"连接成功 (HTTP {resp.status})",
                latency_ms=latency
            )
    except urllib.error.HTTPError as e:
        latency = int((time.time() - start) * 1000)
        error_body = e.read().decode("utf-8")[:200]
        return TestConnectionResponse(
            success=False,
            message=f"HTTP {e.code}: {e.reason}. {error_body}",
            latency_ms=latency
        )
    except Exception as e:
        latency = int((time.time() - start) * 1000)
        return TestConnectionResponse(
            success=False,
            message=f"连接失败: {str(e)}",
            latency_ms=latency
        )


# ============== Sherpa-ONNX 语音服务 API ==============

asr_service = get_asr_service()
tts_service = get_tts_service()


@app.get("/api/v1/voice/status")
def voice_status():
    """检查语音服务（ASR/TTS）状态"""
    return {
        "asr_available": asr_service.is_available(),
        "tts_available": tts_service.is_available(),
        "models_dir": str(asr_service.models_dir),
    }


@app.post("/api/v1/asr", response_model=ASRResponse)
async def asr_endpoint(audio: UploadFile = File(...)):
    """
    语音识别端点
    上传音频文件（WAV 格式），返回识别文字
    """
    if not asr_service.is_available():
        raise HTTPException(status_code=503, detail="ASR 服务不可用，模型未下载")

    if audio.content_type not in {"audio/wav", "audio/x-wav", "audio/wave"}:
        raise HTTPException(status_code=400, detail="仅支持 WAV 格式音频")

    audio_bytes = await audio.read()
    result = asr_service.recognize(audio_bytes)

    activity_log_service.add(
        ActivityLogEntry(
            timestamp=datetime.utcnow(),
            action="asr",
            details={"text": result.get("text", ""), "success": result.get("success", False)},
        )
    )

    return ASRResponse(**result)


@app.post("/api/v1/tts", response_model=TTSResponse)
async def tts_endpoint(request: TTSRequest):
    """
    语音合成端点
    输入文字，返回合成的音频（base64 WAV）
    """
    if not tts_service.is_available():
        raise HTTPException(status_code=503, detail="TTS 服务不可用，模型未下载")

    result = tts_service.synthesize(request.text, speed=request.speed)

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "TTS 合成失败"))

    import base64
    audio_base64 = base64.b64encode(result["audio_bytes"]).decode("utf-8")

    activity_log_service.add(
        ActivityLogEntry(
            timestamp=datetime.utcnow(),
            action="tts",
            details={"text": request.text, "speed": request.speed},
        )
    )

    return TTSResponse(
        audio_base64=audio_base64,
        sample_rate=result["sample_rate"],
        success=True,
        error=None,
    )


@app.post("/api/v1/voice-chat", response_model=VoiceChatResponse)
async def voice_chat_endpoint(request: VoiceChatRequest):
    """
    语音对话端点（完整流程）
    1. ASR: 识别用户语音 -> 文字
    2. LLM: 根据文字生成回复
    3. TTS: 将回复合成为语音

    请求: audio_base64 (WAV 音频的 base64 编码)
    响应: recognized_text (识别文字), answer_text (回复文字), audio_base64 (回复语音)
    """
    import base64

    # 检查服务可用性
    if not asr_service.is_available():
        return VoiceChatResponse(
            sku=request.sku,
            recognized_text="",
            answer_text="",
            audio_base64="",
            success=False,
            error="ASR 服务不可用，请下载模型: python scripts/download_sherpa_models.py --asr",
        )

    if not tts_service.is_available():
        return VoiceChatResponse(
            sku=request.sku,
            recognized_text="",
            answer_text="",
            audio_base64="",
            success=False,
            error="TTS 服务不可用，请下载模型: python scripts/download_sherpa_models.py --tts",
        )

    # 1. ASR: 语音识别
    try:
        audio_bytes = base64.b64decode(request.audio_base64)
    except Exception as e:
        return VoiceChatResponse(
            sku=request.sku,
            recognized_text="",
            answer_text="",
            audio_base64="",
            success=False,
            error=f"音频解码失败: {str(e)}",
        )

    asr_result = asr_service.recognize(audio_bytes)
    if not asr_result["success"]:
        return VoiceChatResponse(
            sku=request.sku,
            recognized_text="",
            answer_text="",
            audio_base64="",
            success=False,
            error=f"语音识别失败: {asr_result.get('error', '未知错误')}",
        )

    recognized_text = asr_result["text"]
    if not recognized_text:
        return VoiceChatResponse(
            sku=request.sku,
            recognized_text="",
            answer_text="没有听清，请再说一遍",
            audio_base64="",
            success=False,
            error="未能识别语音内容",
        )

    # 2. LLM: 生成回复
    product = knowledge_service.get_product(request.sku)
    if product is None:
        return VoiceChatResponse(
            sku=request.sku,
            recognized_text=recognized_text,
            answer_text="",
            audio_base64="",
            success=False,
            error=f"产品不存在: {request.sku}",
        )

    answer_text, mocked, source = chat_service.answer(
        product=product,
        message=recognized_text,
        settings=runtime_settings_service.get(),
    )

    # 3. TTS: 合成回复语音
    tts_result = tts_service.synthesize(answer_text, speed=1.0)
    audio_base64_response = ""
    if tts_result["success"]:
        audio_base64_response = base64.b64encode(tts_result["audio_bytes"]).decode("utf-8")

    # 记录日志
    activity_log_service.add(
        ActivityLogEntry(
            timestamp=datetime.utcnow(),
            action="voice_chat",
            sku=request.sku,
            mocked=mocked,
            details={
                "source": source,
                "recognized": recognized_text,
                "answer": answer_text,
            },
        )
    )

    return VoiceChatResponse(
        sku=request.sku,
        recognized_text=recognized_text,
        answer_text=answer_text,
        audio_base64=audio_base64_response,
        success=True,
        mocked=mocked,
        source=source,
        error=None,
    )

