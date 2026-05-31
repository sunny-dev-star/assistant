"""
OpenAI Whisper STT 适配器
支持 OpenAI / DeepSeek / 任何兼容 OpenAI Audio API 的服务
"""
import aiohttp
import base64
import logging
from typing import Optional

from ...domain.ports.stt_port import ISTTPort, STTResult

logger = logging.getLogger(__name__)


class WhisperSTTAdapter(ISTTPort):
    """基于 OpenAI Audio API 的 STT 适配器"""

    DEFAULT_MODEL = "whisper-1"
    DEFAULT_API_BASE = "https://api.openai.com/v1"

    def __init__(self, default_api_key: str = None, default_api_base: str = None):
        self.default_api_key = default_api_key
        self.default_api_base = default_api_base or self.DEFAULT_API_BASE

    async def transcribe(
        self,
        audio_url: str = "",
        audio_base64: str = "",
        audio_format: str = "wav",
        language: str = "zh",
        api_key: str = None,
        api_base: str = None,
        model: str = None,
    ) -> STTResult:
        """
        调用 Whisper API 将音频转为文字
        支持两种输入方式：
        1. audio_url: 直接传 URL（需服务商可访问）
        2. audio_base64: base64 编码的音频数据
        """
        key = api_key or self.default_api_key
        base = api_base or self.default_api_base
        model_name = model or self.DEFAULT_MODEL

        if not key:
            return STTResult(text="", language=language, confidence=0.0)

        # 构造 multipart 请求
        url = f"{base}/audio/transcriptions"

        data = aiohttp.FormData()
        data.add_field("model", model_name)
        data.add_field("language", language)
        data.add_field("response_format", "verbose_json")

        if audio_url:
            # 下载音频再上传
            audio_bytes = await self._download_audio(audio_url)
            if audio_bytes:
                data.add_field("file", audio_bytes,
                               filename=f"audio.{audio_format}",
                               content_type=f"audio/{audio_format}")
            else:
                return STTResult(text="[音频下载失败]", confidence=0.0)
        elif audio_base64:
            audio_bytes = base64.b64decode(audio_base64)
            data.add_field("file", audio_bytes,
                           filename=f"audio.{audio_format}",
                           content_type=f"audio/{audio_format}")
        else:
            return STTResult(text="[无音频数据]", confidence=0.0)

        headers = {"Authorization": f"Bearer {key}"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data, headers=headers,
                                        timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        return STTResult(
                            text=result.get("text", ""),
                            language=result.get("language", language),
                            duration=result.get("duration", 0.0),
                            confidence=1.0,
                        )
                    else:
                        error_text = await resp.text()
                        logger.error(f"STT API error {resp.status}: {error_text[:200]}")
                        return STTResult(text=f"[语音识别失败: {resp.status}]", confidence=0.0)
        except Exception as e:
            logger.error(f"STT request failed: {e}")
            return STTResult(text=f"[语音识别异常: {str(e)[:50]}]", confidence=0.0)

    async def _download_audio(self, url: str) -> Optional[bytes]:
        """下载音频文件"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status == 200:
                        return await resp.read()
        except Exception as e:
            logger.error(f"Audio download failed: {e}")
        return None
