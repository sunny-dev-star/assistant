"""
WeChat webhook router
Handles: server verification (GET) + message receiving (POST)
Routes WeChat messages to the unified AppService
"""
import logging

from fastapi import APIRouter, Request, Response, Query, HTTPException

from .adapters.wechat_adapter import WechatAdapter
from ....infrastructure.config.settings import settings
from ....infrastructure.persistence.database import async_session_factory
from ....infrastructure.persistence.sqlalchemy_tenant_repository import SQLAlchemyTenantRepository

logger = logging.getLogger(__name__)

router = APIRouter()


async def _get_tenant_wechat_config(tenant_id: str) -> dict:
    """Load tenant's WeChat config from database"""
    async with async_session_factory() as session:
        repo = SQLAlchemyTenantRepository(session)
        tenant = await repo.get_by_id(tenant_id)
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        return tenant.config


@router.get("/wechat/{tenant_id}")
async def wechat_verify(
    tenant_id: str,
    signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...),
    echostr: str = Query(...),
):
    """WeChat server verification endpoint"""
    config = await _get_tenant_wechat_config(tenant_id)
    adapter = WechatAdapter.for_tenant(config)

    if adapter.verify_signature(signature, timestamp, nonce):
        return Response(content=echostr, media_type="text/plain")

    return Response(status_code=403)


@router.post("/wechat/{tenant_id}")
async def wechat_message(tenant_id: str, request: Request):
    """Receive and process WeChat message"""
    config = await _get_tenant_wechat_config(tenant_id)
    adapter = WechatAdapter.for_tenant(config)

    body = await request.body()
    msg = adapter.parse_message(body)

    logger.info(f"WeChat msg: type={msg.msg_type} from={msg.from_user} tenant={tenant_id}")

    # Handle event messages
    if msg.msg_type == "event":
        if msg.event == "subscribe":
            reply = "欢迎关注！我是您的智能助手，有什么可以帮您的吗？😊"
            return Response(
                content=adapter.build_text_reply(msg.from_user, msg.to_user, reply),
                media_type="application/xml",
            )
        elif msg.event == "unsubscribe":
            logger.info(f"User {msg.from_user} unsubscribed")
            return Response(status_code=200)
        # Other events: ignore silently
        return Response(status_code=200)

    # Handle voice messages
    if msg.msg_type == "voice":
        if msg.recognize:
            msg.content = msg.recognize
        else:
            msg.content = await adapter.transcribe_voice(msg.media_id)

    # Skip if no text content
    if not msg.content:
        reply = "抱歉，暂时只支持文字和语音消息哦～"
        return Response(
            content=adapter.build_text_reply(msg.from_user, msg.to_user, reply),
            media_type="application/xml",
        )

    # Route to AppService
    try:
        # Look up tenant entity for auth context
        async with async_session_factory() as session:
            repo = SQLAlchemyTenantRepository(session)
            tenant = await repo.get_by_id(tenant_id)

        if not tenant or not tenant.is_active():
            reply = "服务暂时不可用，请稍后再试。"
            return Response(
                content=adapter.build_text_reply(msg.from_user, msg.to_user, reply),
                media_type="application/xml",
            )

        # Import here to avoid circular imports
        from ....domain.models.context import TenantContext, LLMConfig
        from ....domain.value_objects.channel import Channel

        default_model = tenant.config.get("default_model", "deepseek/deepseek-chat")
        llm_config = LLMConfig(
            provider="openai_compat",
            model=default_model,
            api_key=settings.DEEPSEEK_API_KEY or None,
            api_base=settings.DEEPSEEK_API_URL if settings.DEEPSEEK_API_URL else None,
        )

        context = TenantContext(
            tenant_id=tenant.id,
            user_id=msg.from_user,  # Use WeChat OpenID as user_id
            channel=Channel("wechat"),
            session_id=f"wx_{msg.from_user}_{tenant_id}",
            llm_config=llm_config,
            allowed_skills=tenant.config.get("enabled_skills", []),
            metadata={"window_size": tenant.config.get("window_size", 10)},
        )

        app_service = request.app.state.assistant_chat_app_service
        result = await app_service.execute(
            context=context,
            user_message_content=msg.content,
        )

        reply = result.get("reply", "抱歉，处理您的消息时出现了问题。")

    except Exception as e:
        logger.error(f"WeChat message processing error: {e}", exc_info=True)
        reply = "抱歉，服务暂时出了点问题，请稍后再试。"

    return Response(
        content=adapter.build_text_reply(msg.from_user, msg.to_user, reply),
        media_type="application/xml",
    )
