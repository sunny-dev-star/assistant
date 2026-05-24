"""
技能管理路由 - 对齐 Claude Skill 规范
提供三级加载的 API 端点
"""
from fastapi import APIRouter, Request, HTTPException
from typing import Optional


router = APIRouter()


@router.get("/skills")
async def list_skills(request: Request):
    """
    列出所有技能（Level 1: 元数据）
    只有 name + description，用于触发匹配
    """
    loader = request.app.state.skill_loader
    return {
        "skills": loader.get_skill_info(),
        "total": loader.skill_count,
        "tools_total": loader.tool_count,
    }


@router.get("/skills/{skill_id}")
async def get_skill_detail(request: Request, skill_id: str):
    """
    获取技能详情（Level 2: SKILL.md body）
    """
    loader = request.app.state.skill_loader
    skill_data = loader.skills.get(skill_id)

    if not skill_data:
        raise HTTPException(status_code=404, detail=f"Skill not found: {skill_id}")

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
