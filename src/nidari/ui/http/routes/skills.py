"""
技能管理路由 - 四层权限感知
提供技能列表、详情、工具列表的 API 端点
"""
from fastapi import APIRouter, Request, HTTPException
from typing import Optional


router = APIRouter()


@router.get("/skills")
async def list_skills(request: Request):
    """
    列出租户可见的技能（不暴露未购买技能）
    """
    tenant = request.state.tenant
    loader = request.app.state.skill_loader

    # 使用新的租户感知方法
    skills = loader.list_skills_for_tenant(tenant)

    return {
        "skills": skills,
        "total": len(skills),
        "tools_total": loader.tool_count,
    }


@router.get("/skills/{skill_id}")
async def get_skill_detail(request: Request, skill_id: str):
    """
    获取技能详情（Level 2: SKILL.md body）
    """
    loader = request.app.state.skill_loader
    tenant = request.state.tenant

    skill_data = loader.skills.get(skill_id)
    if not skill_data:
        raise HTTPException(status_code=404, detail=f"Skill not found: {skill_id}")

    # 权限检查：租户是否可用此技能
    tenant_enabled = set(tenant.config.get("enabled_skills", []))
    if skill_id not in loader._platform and skill_id not in tenant_enabled:
        raise HTTPException(status_code=403, detail=f"Skill not available: {skill_id}")

    meta = skill_data.get("metadata", {})
    body = skill_data.get("body", "")

    return {
        "id": skill_id,
        "name": meta.get("name", ""),
        "description": meta.get("description", ""),
        "body": body,
        "tools": [
            {
                "name": t["function"]["name"],
                "description": t["function"]["description"],
            }
            for t in skill_data.get("tools", [])
        ],
        "references": [
            {"name": r["name"], "filename": r["filename"]}
            for r in skill_data.get("references", [])
        ],
        "scripts": [
            {"name": s["name"], "filename": s["filename"]}
            for s in skill_data.get("scripts", [])
        ],
        "assets": [
            {"name": a["name"], "filename": a["filename"]}
            for a in skill_data.get("assets", [])
        ],
    }


@router.get("/skills/{skill_id}/tools")
async def list_skill_tools(skill_id: str, request: Request):
    """
    返回该用户在该技能下可用的工具（含角色过滤）
    """
    tenant = request.state.tenant
    user_id = request.query_params.get("user_id", "anonymous")
    loader = request.app.state.skill_loader
    role_repo = getattr(request.app.state, 'role_repo', None)

    if role_repo:
        tools = await loader.get_tools_for_user(
            tenant, user_id, role_repo
        )
        skill_tools = [
            t for t in tools
            if loader._tool_to_skill.get(t["function"]["name"]) == skill_id
        ]
    else:
        skill_data = loader.skills.get(skill_id)
        if not skill_data:
            raise HTTPException(status_code=404, detail=f"Skill not found: {skill_id}")
        skill_tools = skill_data.get("tools", [])

    return {"tools": skill_tools}


@router.get("/skills/{skill_id}/references/{ref_name}")
async def get_reference(request: Request, skill_id: str, ref_name: str):
    """
    读取参考文档（Level 3: 按需加载）
    """
    loader = request.app.state.skill_loader
    content = loader.read_reference(skill_id, ref_name)

    if content is None:
        raise HTTPException(
            status_code=404,
            detail=f"Reference not found: {ref_name} in skill {skill_id}"
        )

    return {
        "skill_id": skill_id,
        "reference": ref_name,
        "content": content,
    }


@router.get("/skills/{skill_id}/scripts/{script_name}")
async def get_script(request: Request, skill_id: str, script_name: str):
    """
    读取脚本内容（Level 3: 按需加载）
    """
    loader = request.app.state.skill_loader
    content = loader.read_script(skill_id, script_name)

    if content is None:
        raise HTTPException(
            status_code=404,
            detail=f"Script not found: {script_name} in skill {skill_id}"
        )

    return {
        "skill_id": skill_id,
        "script": script_name,
        "content": content,
    }
