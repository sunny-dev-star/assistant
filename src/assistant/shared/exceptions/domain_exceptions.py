"""
领域异常
"""


class DomainException(Exception):
    """领域异常基类"""
    pass


class TenantNotFoundException(DomainException):
    """租户不存在"""
    pass


class TenantInactiveException(DomainException):
    """租户未激活"""
    pass


class QuotaExceededException(DomainException):
    """配额超限"""
    pass


class ConversationNotFoundException(DomainException):
    """会话不存在"""
    pass


class MessageNotFoundException(DomainException):
    """消息不存在"""
    pass


class SkillNotFoundException(DomainException):
    """技能不存在"""
    pass


class AuthenticationException(DomainException):
    """认证失败"""
    pass


class AuthorizationException(DomainException):
    """授权失败"""
    pass


class NotFoundError(DomainException):
    """资源不存在"""
    pass


class ValidationError(DomainException):
    """验证错误"""
    pass
