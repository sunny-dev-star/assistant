"""
WeChat Official Account adapter
Handles: signature verification, XML parsing, message building, voice transcription
"""
import hashlib
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Optional, Any
import logging

from .....domain.ports.channel_port import IChannelAdapter, InboundMessage, OutboundMessage

logger = logging.getLogger(__name__)


@dataclass
class WechatMessage:
    """Parsed WeChat message"""
    msg_type: str  # text / image / voice / video / event
    msg_id: str
    from_user: str  # OpenID of sender
    to_user: str    # Our app ID
    content: str = ""
    media_id: str = ""
    recognize: str = ""  # Voice recognition result (if enabled)
    event: str = ""      # For event messages (subscribe, unsubscribe, etc)
    event_key: str = ""
    pic_url: str = ""
    format: str = ""


class WechatAdapter(IChannelAdapter):
    """WeChat Official Account message adapter"""

    def __init__(self, token: str, app_id: str = "", app_secret: str = "", encoding_aes_key: str = ""):
        self.token = token
        self.app_id = app_id
        self.app_secret = app_secret
        self.encoding_aes_key = encoding_aes_key
        self._access_token: Optional[str] = None
        self._token_expires: float = 0

    @classmethod
    def for_tenant(cls, tenant_config: dict) -> "WechatAdapter":
        """Create adapter from tenant config"""
        wechat_cfg = tenant_config.get("wechat", {})
        return cls(
            token=wechat_cfg.get("token", ""),
            app_id=wechat_cfg.get("app_id", ""),
            app_secret=wechat_cfg.get("app_secret", ""),
            encoding_aes_key=wechat_cfg.get("encoding_aes_key", ""),
        )


    # ==========================================
    # IChannelAdapter interface implementation
    # ==========================================

    async def verify(self, request) -> bool:
        """IChannelAdapter.verify — verify WeChat signature"""
        from fastapi import Request
        if isinstance(request, Request):
            sig = request.query_params.get("signature", "")
            ts = request.query_params.get("timestamp", "")
            nonce = request.query_params.get("nonce", "")
            return self.verify_signature(sig, ts, nonce)
        return False

    async def parse(self, request) -> InboundMessage:
        """IChannelAdapter.parse — parse WeChat XML to InboundMessage"""
        from fastapi import Request
        if isinstance(request, Request):
            body = await request.body()
            msg = self.parse_message(body)
            tenant_id = request.path_params.get("tenant_id", "")
            return InboundMessage(
                message_id=msg.msg_id,
                channel="wechat",
                tenant_id=tenant_id,
                user_id=msg.from_user,
                session_id=f"wx_{msg.from_user}_{tenant_id}",
                content=msg.content or msg.recognize or "",
                content_type=msg.msg_type,
                raw=msg,
            )
        raise ValueError("Expected FastAPI Request")

    async def render(self, msg: OutboundMessage, context: dict) -> str:
        """IChannelAdapter.render — render OutboundMessage to WeChat XML"""
        from_user = context.get("from_user", "")
        to_user = context.get("to_user", "")
        if msg.content_type == "rich" and msg.rich_content:
            articles = msg.rich_content.get("articles", [])
            return self.build_news_reply(from_user, to_user, articles)
        return self.build_text_reply(from_user, to_user, msg.content)

    def verify_signature(self, signature: str, timestamp: str, nonce: str) -> bool:
        """Verify WeChat server signature"""
        params = sorted([self.token, timestamp, nonce])
        raw = "".join(params).encode("utf-8")
        digest = hashlib.sha1(raw).hexdigest()
        return digest == signature

    def parse_message(self, body_bytes: bytes) -> WechatMessage:
        """Parse WeChat XML message body"""
        root = ET.fromstring(body_bytes)

        msg_type = root.findtext("MsgType", "text")
        from_user = root.findtext("FromUserName", "")
        to_user = root.findtext("ToUserName", "")
        msg_id = root.findtext("MsgId", "")
        content = root.findtext("Content", "")
        media_id = root.findtext("MediaId", "")
        recognize = root.findtext("Recognition", "")
        event = root.findtext("Event", "")
        event_key = root.findtext("EventKey", "")
        pic_url = root.findtext("PicUrl", "")
        fmt = root.findtext("Format", "")

        return WechatMessage(
            msg_type=msg_type,
            msg_id=msg_id,
            from_user=from_user,
            to_user=to_user,
            content=content,
            media_id=media_id,
            recognize=recognize,
            event=event,
            event_key=event_key,
            pic_url=pic_url,
            format=fmt,
        )

    def build_text_reply(self, from_user: str, to_user: str, content: str) -> str:
        """Build XML text reply"""
        # Note: WeChat expects from/to swapped in reply
        return f"""<xml>
<ToUserName><![CDATA[{from_user}]]></ToUserName>
<FromUserName><![CDATA[{to_user}]]></FromUserName>
<CreateTime>{int(time.time())}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[{content}]]></Content>
</xml>"""

    def build_news_reply(self, from_user: str, to_user: str, articles: list) -> str:
        """Build XML news (rich media) reply"""
        items = ""
        for art in articles:
            items += f"""<item>
<Title><![CDATA[{art.get('title', '')}]]></Title>
<Description><![CDATA[{art.get('description', '')}]]></Description>
<PicUrl><![CDATA[{art.get('pic_url', '')}]]></PicUrl>
<Url><![CDATA[{art.get('url', '')}]]></Url>
</item>"""
        return f"""<xml>
<ToUserName><![CDATA[{from_user}]]></ToUserName>
<FromUserName><![CDATA[{to_user}]]></FromUserName>
<CreateTime>{int(time.time())}</CreateTime>
<MsgType><![CDATA[news]]></MsgType>
<ArticleCount>{len(articles)}</ArticleCount>
<Articles>{items}</Articles>
</xml>"""

    async def get_access_token(self) -> str:
        """Get or refresh WeChat access token"""
        if self._access_token and time.time() < self._token_expires:
            return self._access_token

        if not self.app_id or not self.app_secret:
            raise ValueError("WeChat app_id and app_secret are required")

        import httpx
        url = "https://api.weixin.qq.com/cgi-bin/token"
        params = {
            "grant_type": "client_credential",
            "appid": self.app_id,
            "secret": self.app_secret,
        }
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params)
            data = resp.json()

        if "access_token" not in data:
            raise RuntimeError(f"WeChat token error: {data.get('errmsg', 'unknown')}")

        self._access_token = data["access_token"]
        self._token_expires = time.time() + data.get("expires_in", 7200) - 300
        logger.info(f"WeChat access token refreshed, expires in {data.get('expires_in', 7200)}s")
        return self._access_token

    async def download_media(self, media_id: str) -> bytes:
        """Download media file from WeChat"""
        token = await self.get_access_token()
        import httpx
        url = f"https://api.weixin.qq.com/cgi-bin/media/get?access_token={token}&media_id={media_id}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
            return resp.content

    async def transcribe_voice(self, media_id: str) -> str:
        """
        Transcribe voice message.
        WeChat may provide Recognition field if voice recognition is enabled.
        Otherwise, download .amr and use ASR service.
        """
        # First try the built-in recognition result
        # This is already populated if the WeChat account has voice recognition enabled
        # For now, return a placeholder - actual ASR integration (iFlytek/Aliyun) can be added later
        logger.info(f"Voice transcription requested for media_id: {media_id}")
        # TODO: Integrate with actual ASR service
        return "[语音消息]"
