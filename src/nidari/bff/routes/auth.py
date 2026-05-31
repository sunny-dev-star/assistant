"""BFF authentication routes"""
from fastapi import APIRouter, Request, Path, Response
from pydantic import BaseModel

router = APIRouter()


class WechatLoginBody(BaseModel):
    code: str
    channel: str = "miniprogram"


class PhoneSendCodeBody(BaseModel):
    phone: str


class PhoneLoginBody(BaseModel):
    phone: str
    code: str
    channel: str = "app"


class EmailRegisterBody(BaseModel):
    email: str
    password: str
    display_name: str = ""


class EmailLoginBody(BaseModel):
    email: str
    password: str
    channel: str = "web"


class SSOLoginBody(BaseModel):
    provider: str
    code: str
    channel: str = "web"


class RefreshBody(BaseModel):
    refresh_token: str


class LogoutBody(BaseModel):
    refresh_token: str


@router.post("/auth/wechat")
async def login_wechat(body: WechatLoginBody, tenant_id: str = Path(...)):
    from ..services.auth_service import AuthService
    # Will be resolved via dependency injection in main
    raise NotImplementedError("Use BFF main app with DI")


@router.post("/auth/phone/send-code")
async def send_sms_code(body: PhoneSendCodeBody, tenant_id: str = Path(...)):
    raise NotImplementedError("Use BFF main app with DI")


@router.post("/auth/phone")
async def login_phone(body: PhoneLoginBody, tenant_id: str = Path(...)):
    raise NotImplementedError("Use BFF main app with DI")


@router.post("/auth/email/register")
async def register_email(body: EmailRegisterBody, tenant_id: str = Path(...)):
    raise NotImplementedError("Use BFF main app with DI")


@router.post("/auth/email")
async def login_email(body: EmailLoginBody, tenant_id: str = Path(...), response: Response = None):
    raise NotImplementedError("Use BFF main app with DI")


@router.post("/auth/sso")
async def login_sso(body: SSOLoginBody, tenant_id: str = Path(...)):
    raise NotImplementedError("Use BFF main app with DI")


@router.post("/auth/refresh")
async def refresh_token(body: RefreshBody, tenant_id: str = Path(...)):
    raise NotImplementedError("Use BFF main app with DI")


@router.post("/auth/logout")
async def logout(body: LogoutBody, tenant_id: str = Path(...)):
    raise NotImplementedError("Use BFF main app with DI")
