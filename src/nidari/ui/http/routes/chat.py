"""
Chat router — 支持多模态（文本/图片/语音）
- 图片: 传给 vision 模型理解
- 语音: 先 STT 转文字，再走文本对话
- 纯文本: 直接对话
"""
import uuid
import logging
from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from ....domain.models.context import TenantContext, LLMConfig
from ....domain.entities.message import Attachment
from ....domain.value_objects.channel import Channel
from ....infrastructure.config.settings import settings

logger = logging.getLogger(__name__)
router = APIRouter()


class ImageInput(BaseModel):
    """图片输入"""
    url: Optional[str] = None       # 图片 URL（优先）
    base64: Optional[str] = None    # base64 编码
    mime_type: str = "image/jpeg"


class VoiceInput(BaseModel):
    """语音输入"""
    url: Optional[str] = None       # 音频 URL（优先）
    base64: Optional[str] = None    # base64 编码
    mime_type: str = "audio/wav"    # audio/wav, audio/mp3, audio/ogg 等
    format: str = "wav"             # wav, mp3, ogg, webm


class ChatRequest(BaseModel):
    """Chat request — 支持多模态"""
    message: str = ""
    session_id: Optional[str] = None
    user_id: str = "anonymous"
    user_name: Optional[str] = None
    channel: str = "web"
    metadata: Optional[Dict[str, Any]] = None
    # 多模态附件
    images: Optional[List[ImageInput]] = None   # 图片列表
    voice: Optional[VoiceInput] = None           # 语音（单条）


class ChatResponse(BaseModel):
    """Chat response"""
    session_id: str
    reply: str
    tokens_used: int = 0
    cost_usd: float = 0.0
    stt_text: Optional[str] = None  # 语音转文字结果（如果有语音输入）


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: Request,
    chat_req: ChatRequest
):
    """
    Unified chat endpoint.
    支持纯文本、图片、语音三种输入模式。
    """
    app_service = request.app.state.assistant_chat_app_service
    tenant = request.state.tenant

    session_id = chat_req.session_id or f"sess_{uuid.uuid4().hex[:12]}"
    user_id = chat_req.user_id

    # ── 构建 LLM 配置（租户级覆盖）──
    tcfg = tenant.config or {}
    llm_config = _build_llm_config(tcfg)

    # ── 构建上下文 ──
    context = TenantContext(
        tenant_id=tenant.id,
        user_id=user_id,
        channel=Channel(chat_req.channel),
        session_id=session_id,
        llm_config=llm_config,
        allowed_skills=tcfg.get("enabled_skills", []),
        metadata={
            **(chat_req.metadata or {}),
            "window_size": tcfg.get("window_size", 10),
        }
    )
    context._tenant_entity = tenant

    # ── 处理多模态输入 ──
    user_text = chat_req.message
    attachments: List[Attachment] = []
    stt_text = None

    # 语音：先 STT 转文字
    if chat_req.voice:
        stt_text = await _process_voice(chat_req.voice, tcfg, request)
        if stt_text:
            # STT 结果拼入用户消息
            if user_text:
                user_text = f"{user_text}\n[语音内容]: {stt_text}"
            else:
                user_text = f"[语音内容]: {stt_text}"

    # 图片：构造附件
    if chat_req.images:
        for img in chat_req.images:
            attachments.append(Attachment(
                type="image",
                url=img.url or "",
                base64=img.base64 or "",
                mime_type=img.mime_type,
            ))

        # 如果有图片，需要用 vision 模型
        if llm_config.vision_model:
            llm_config.model = llm_config.vision_model
            if llm_config.vision_api_key:
                llm_config.api_key = llm_config.vision_api_key
            if llm_config.vision_api_base:
                llm_config.api_base = llm_config.vision_api_base

    # ── 执行对话 ──
    result = await app_service.execute(
        context=context,
        user_message_content=user_text,
        user_name=chat_req.user_name,
        attachments=attachments if attachments else None,
    )

    response = ChatResponse(**result)
    if stt_text:
        response.stt_text = stt_text
    return response


@router.get("/chat/history/{session_id}")
async def get_chat_history(
    request: Request,
    session_id: str,
    limit: int = 50
):
    """Get chat history"""
    app_service = request.app.state.assistant_chat_app_service
    messages = await app_service.message_repo.list_by_conversation(session_id, limit=limit)
    return {
        "session_id": session_id,
        "messages": [m.to_dict() for m in messages]
    }


# ═══════════════════════════════════════════════════════
# 内部工具函数
# ═══════════════════════════════════════════════════════

def _build_llm_config(tcfg: dict) -> LLMConfig:
    """从租户配置构建 LLMConfig，含 vision/stt"""
    return LLMConfig(
        provider="openai_compat",
        model=tcfg.get("default_model", settings.DEEPSEEK_MODEL or "deepseek/deepseek-chat"),
        api_key=tcfg.get("llm_api_key") or settings.DEEPSEEK_API_KEY or None,
        api_base=tcfg.get("llm_api_base") or settings.DEEPSEEK_API_URL or None,
        temperature=tcfg.get("llm_temperature", 0.7),
        max_tokens=tcfg.get("llm_max_tokens", 2048),
        # 视觉模型配置
        vision_model=tcfg.get("vision_model"),
        vision_api_key=tcfg.get("vision_api_key"),
        vision_api_base=tcfg.get("vision_api_base"),
        # STT 配置
        stt_provider=tcfg.get("stt_provider"),
        stt_api_key=tcfg.get("stt_api_key"),
        stt_api_base=tcfg.get("stt_api_base"),
        stt_model=tcfg.get("stt_model"),
    )


async def _process_voice(voice: VoiceInput, tcfg: dict, request: Request) -> str | None:
    """
    语音转文字：根据租户配置选择 STT 服务
    """
    stt_provider = tcfg.get("stt_provider")
    if not stt_provider:
        logger.warning("No STT provider configured for tenant")
        return None

    try:
        from ....infrastructure.external_services.whisper_stt_adapter import WhisperSTTAdapter
        stt = WhisperSTTAdapter(
            default_api_key=tcfg.get("stt_api_key"),
            default_api_base=tcfg.get("stt_api_base"),
        )
        result = await stt.transcribe(
            audio_url=voice.url or "",
            audio_base64=voice.base64 or "",
            audio_format=voice.format,
            language="zh",
            api_key=tcfg.get("stt_api_key"),
            api_base=tcfg.get("stt_api_base"),
            model=tcfg.get("stt_model"),
        )
        if result and result.text:
            return result.text
    except Exception as e:
        logger.error(f"STT failed: {e}")
    return None
