"""
语音转文字 (STT) 服务端口定义
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class STTResult:
    """语音转文字结果"""
    text: str
    language: Optional[str] = None
    duration: float = 0.0  # 音频时长(秒)
    confidence: float = 0.0


class ISTTPort(ABC):
    """语音转文字服务端口"""

    @abstractmethod
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
        将音频转为文字

        Args:
            audio_url: 可访问的音频 URL（优先）
            audio_base64: base64 编码的音频数据
            audio_format: 音频格式 (wav/mp3/ogg/webm 等)
            language: 语言代码
            api_key: API 密钥（覆盖默认）
            api_base: API 端点（覆盖默认）
            model: 模型名（覆盖默认）
        """
        ...
