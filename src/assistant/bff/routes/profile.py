"""BFF user profile route"""
from fastapi import APIRouter, Request, Path

router = APIRouter()


@router.get("/profile")
async def get_profile(tenant_id: str = Path(...), request: Request = None):
    user_id = request.state.user_id
    user_repo = request.app.state.user_repo
    user = await user_repo.get_by_id(user_id)
    if not user:
        return {"code": 4040, "message": "User not found", "data": None}
    return {
        "user_id": user["id"],
        "display_name": user.get("display_name"),
        "avatar_url": user.get("avatar_url"),
        "phone": user.get("phone"),
        "email": user.get("email"),
        "last_login_channel": user.get("last_login_channel"),
    }
