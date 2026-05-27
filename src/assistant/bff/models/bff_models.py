"""
BFF ORM models: platform_users, auth_identities, refresh_tokens, push_devices
"""
from datetime import datetime
from sqlalchemy import (
    Column, String, DateTime, Boolean, Integer, BigInteger, Text, JSON, ForeignKey, Index
)
from sqlalchemy.orm import relationship

from ...infrastructure.persistence.database import Base


class PlatformUserModel(Base):
    """统一用户表（多端多登录方式）"""
    __tablename__ = "platform_users"

    id = Column(String(50), primary_key=True)
    tenant_id = Column(String(50), ForeignKey("tenants.id"), nullable=False, index=True)
    display_name = Column(String(100))
    avatar_url = Column(Text)
    phone = Column(String(20), nullable=True)
    email = Column(String(200), nullable=True)
    password_hash = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True)
    last_login_at = Column(DateTime, nullable=True)
    last_login_channel = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("uq_platform_user_phone", "tenant_id", "phone", unique=True),
        Index("uq_platform_user_email", "tenant_id", "email", unique=True),
    )

    identities = relationship("AuthIdentityModel", back_populates="user", lazy="selectin")
    refresh_tokens = relationship("RefreshTokenModel", back_populates="user", lazy="noload")


class AuthIdentityModel(Base):
    """第三方身份绑定表"""
    __tablename__ = "auth_identities"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(String(50), ForeignKey("platform_users.id"), nullable=False, index=True)
    tenant_id = Column(String(50), nullable=False)
    provider = Column(String(30), nullable=False)
    provider_uid = Column(String(200), nullable=False)
    extra = Column(JSON, default=dict)
    bound_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("PlatformUserModel", back_populates="identities")

    __table_args__ = (
        Index("uq_auth_identity", "tenant_id", "provider", "provider_uid", unique=True),
    )


class RefreshTokenModel(Base):
    """Refresh Token 存储（支持主动吊销）"""
    __tablename__ = "refresh_tokens"

    id = Column(String(100), primary_key=True)
    user_id = Column(String(50), ForeignKey("platform_users.id"), nullable=False)
    tenant_id = Column(String(50), nullable=False)
    channel = Column(String(20), nullable=False)
    device_id = Column(String(200), nullable=True)
    issued_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False)
    revoked_at = Column(DateTime, nullable=True)

    user = relationship("PlatformUserModel", back_populates="refresh_tokens")

    __table_args__ = (
        Index("idx_refresh_tokens_user", "user_id", "tenant_id", "revoked"),
    )


class PushDeviceModel(Base):
    """App 推送设备注册表"""
    __tablename__ = "push_devices"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(String(50), nullable=False, index=True)
    tenant_id = Column(String(50), nullable=False)
    platform = Column(String(10), nullable=False)
    device_token = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    registered_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("uq_push_device", "user_id", "device_token", unique=True),
    )


class TenantFrontendConfigModel(Base):
    """租户前端配置（多端）"""
    __tablename__ = "tenant_frontend_configs"

    id = Column(String(50), primary_key=True)
    tenant_id = Column(String(50), ForeignKey("tenants.id"), nullable=False, unique=True)
    app_name = Column(String(100), default="智能助手")
    logo_url = Column(Text, nullable=True)
    primary_color = Column(String(20), default="#1890ff")
    welcome_message = Column(Text, default="你好，有什么可以帮你？")
    features = Column(JSON, default=dict)

    web_domain = Column(String(200), nullable=True)
    web_theme = Column(JSON, default=dict)

    ios_bundle_id = Column(String(200), nullable=True)
    android_pkg = Column(String(200), nullable=True)
    apns_key = Column(Text, nullable=True)
    fcm_server_key = Column(Text, nullable=True)

    auth_methods = Column(JSON, default=lambda: {
        "wechat": True, "phone": True,
        "email": False, "feishu": False, "dingtalk": False,
    })

    streaming_enabled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
