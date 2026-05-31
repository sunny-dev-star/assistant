#!/usr/bin/env python3
"""
端到端测试 — 四层角色级技能权限控制
使用实际的 SKILL.md 工具名
"""
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

import asyncio
import json
from pathlib import Path
import tempfile

DB_PATH = os.path.join(PROJECT_ROOT, "test_role_permissions.db")
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{DB_PATH}"
os.environ["AUTH_ENABLED"] = "false"
os.environ["DEEPSEEK_API_KEY"] = "test-key"

from nidari.infrastructure.persistence.database import async_session_factory, init_db
from nidari.infrastructure.persistence.sqlalchemy_tenant_repository import SQLAlchemyTenantRepository
from nidari.infrastructure.persistence.repositories.role_repo import RoleRepository
from nidari.infrastructure.skill_loader import SkillLoader
from nidari.domain.services.tenant_service import TenantService
from nidari.domain.entities.tenant import Tenant
from nidari.domain.value_objects.api_key import ApiKey
from nidari.domain.value_objects.quota import Quota

PASS = 0
FAIL = 0

def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name}")
        if detail:
            print(f"     → {detail}")


async def run_tests():
    print("=" * 60)
    print("Day 1: 数据库 & 仓储层")
    print("=" * 60)

    await init_db()
    check("roles / role_skill_grants / user_roles 表自动创建", True)

    async with async_session_factory() as session:
        role_repo = RoleRepository(session)
        tenant_repo = SQLAlchemyTenantRepository(session)

        tenant = Tenant(
            id="tnt_test01", name="测试医养集团", industry="elder_care",
            plan="professional",
            api_key=ApiKey("ak_test_key_001"),
            quota=Quota(limit=1000000, used=0),
            config={
                "enabled_skills": ["elder_care", "weather_query", "express_query"],
                "default_model": "deepseek/deepseek-chat",
                "window_size": 10,
            },
        )
        await tenant_repo.create(tenant)
        await session.commit()
        check("创建测试租户 tnt_test01 (enabled: elder_care, weather_query, express_query)", True)

        # 创建角色
        await role_repo.create({"id": "role_admin_test01", "tenant_id": "tnt_test01",
            "name": "admin", "display_name": "管理员", "is_default": False, "is_admin": True})
        await role_repo.create({"id": "role_default_test01", "tenant_id": "tnt_test01",
            "name": "default", "display_name": "普通用户", "is_default": True, "is_admin": False})
        await role_repo.create({"id": "role_nursing_test01", "tenant_id": "tnt_test01",
            "name": "nursing_staff", "display_name": "护理员", "is_default": False, "is_admin": False})
        await role_repo.create({"id": "role_doctor_test01", "tenant_id": "tnt_test01",
            "name": "doctor", "display_name": "值班医生", "is_default": False, "is_admin": False})
        await role_repo.create({"id": "role_clerk_test01", "tenant_id": "tnt_test01",
            "name": "admin_clerk", "display_name": "行政人员", "is_default": False, "is_admin": False})
        await session.commit()

        roles = await role_repo.get_by_tenant("tnt_test01")
        check("get_by_tenant 返回 5 个角色", len(roles) == 5)

        def_role = await role_repo.get_default_role("tnt_test01")
        check("get_default_role → default 角色", def_role["name"] == "default")

        # 技能授权 — 使用真实工具名
        # 护理员: elder_care 的 3 个工具 (record_checkin, log_health_data, trigger_emergency_alert)
        await role_repo.grant_skill("role_nursing_test01", "elder_care",
            ["record_checkin", "log_health_data", "trigger_emergency_alert"])
        # 值班医生: elder_care 全部工具 + weather_query.get_weather
        await role_repo.grant_skill("role_doctor_test01", "elder_care", None)
        await role_repo.grant_skill("role_doctor_test01", "weather_query", ["get_weather"])
        # 行政: express_query.track_package
        await role_repo.grant_skill("role_clerk_test01", "express_query", ["track_package"])
        await session.commit()

        g = await role_repo.get_grants_by_role("role_nursing_test01")
        check("护理员有 1 个技能授权", len(g) == 1)
        check("护理员 elder_care 白名单 3 个工具",
              g[0]["tool_whitelist"] is not None and len(g[0]["tool_whitelist"]) == 3,
              f"got {g[0]['tool_whitelist']}")

        g = await role_repo.get_grants_by_role("role_doctor_test01")
        check("值班医生有 2 个技能授权", len(g) == 2)
        check("值班医生 elder_care 无工具限制",
              next(x for x in g if x["skill_name"] == "elder_care")["tool_whitelist"] is None)

        g = await role_repo.get_grants_by_role("role_clerk_test01")
        check("行政有 1 个技能授权 (express_query)", len(g) == 1)

        # 用户绑定
        await role_repo.assign_role("tnt_test01", "user_nurse", "role_nursing_test01")
        await role_repo.assign_role("tnt_test01", "user_doctor", "role_doctor_test01")
        await role_repo.assign_role("tnt_test01", "user_clerk", "role_clerk_test01")
        await role_repo.assign_role("tnt_test01", "user_admin", "role_admin_test01")
        await role_repo.assign_role("tnt_test01", "user_multi", "role_nursing_test01")
        await role_repo.assign_role("tnt_test01", "user_multi", "role_clerk_test01")
        await session.commit()

        print("\n--- 权限合并测试 ---")

        # 无角色 → default（无授权）
        g = await role_repo.get_effective_grants("tnt_test01", "user_stranger")
        check("无角色用户 → default 角色, 无技能权限", len(g) == 0, f"got {g}")

        # 管理员
        g = await role_repo.get_effective_grants("tnt_test01", "user_admin")
        check("管理员 → __admin__ 标记", "__admin__" in g)

        # 护理员
        g = await role_repo.get_effective_grants("tnt_test01", "user_nurse")
        check("护理员 → 只有 elder_care", set(g.keys()) == {"elder_care"})
        check("护理员 elder_care 白名单 3 个",
              g["elder_care"] is not None and len(g["elder_care"]) == 3,
              f"got {g.get('elder_care')}")

        # 值班医生
        g = await role_repo.get_effective_grants("tnt_test01", "user_doctor")
        check("医生 → elder_care + weather_query",
              set(g.keys()) == {"elder_care", "weather_query"})
        check("医生 elder_care 无限制 (None)", g["elder_care"] is None)
        check("医生 weather_query 只有 get_weather",
              g["weather_query"] == ["get_weather"])

        # 行政
        g = await role_repo.get_effective_grants("tnt_test01", "user_clerk")
        check("行政 → 只有 express_query", set(g.keys()) == {"express_query"})

        # 多角色（护理员+行政 → 并集）
        g = await role_repo.get_effective_grants("tnt_test01", "user_multi")
        check("多角色 → elder_care + express_query",
              set(g.keys()) == {"elder_care", "express_query"})
        check("多角色 elder_care 保留白名单 3 个",
              g["elder_care"] is not None and len(g["elder_care"]) == 3)

        # 撤销 + 解绑
        await role_repo.revoke_skill("role_clerk_test01", "express_query")
        await session.commit()
        g = await role_repo.get_grants_by_role("role_clerk_test01")
        check("撤销后行政无技能授权", len(g) == 0)

        await role_repo.unassign_role("tnt_test01", "user_nurse", "role_nursing_test01")
        await session.commit()
        r = await role_repo.get_user_roles("tnt_test01", "user_nurse")
        check("解绑后 user_nurse 无角色", len(r) == 0)

    # ================================================================
    print("\n" + "=" * 60)
    print("Day 2: SkillLoader 四层权限")
    print("=" * 60)

    skills_dir = os.path.join(PROJECT_ROOT, "skills")
    loader = SkillLoader(str(skills_dir))

    check("平台技能已加载 (platform)", len(loader._platform) > 0,
          f"{list(loader._platform.keys())}")
    check("行业技能已加载 (industry)", len(loader._industry) >= 3,
          f"{list(loader._industry.keys())}")
    check("旧 API 兼容 skills dict", len(loader.skills) > 0)
    check("旧 API 兼容 tool_count", loader.tool_count > 0)

    # 打印实际工具名
    print(f"  ℹ️  实际工具: {list(loader._tool_to_skill.keys())}")

    async with async_session_factory() as session:
        role_repo = RoleRepository(session)
        tenant_obj = await SQLAlchemyTenantRepository(session).get_by_id("tnt_test01")

        # 管理员 → 所有已购技能工具
        admin_tools = await loader.get_tools_for_user(tenant_obj, "user_admin", role_repo)
        admin_names = {t["function"]["name"] for t in admin_tools}
        check("管理员获得 platform + 所有已购行业技能工具",
              len(admin_tools) > len(loader._platform) * 2,  # 至少比 platform 多
              f"platform tools + {len(admin_tools)} total")

        # 重新绑定护理员
        await role_repo.assign_role("tnt_test01", "user_nurse", "role_nursing_test01")
        await session.commit()

        nurse_tools = await loader.get_tools_for_user(tenant_obj, "user_nurse", role_repo)
        nurse_ec = [t for t in nurse_tools
                    if loader._tool_to_skill.get(t["function"]["name"]) == "elder_care"]
        nurse_wx = [t for t in nurse_tools
                    if loader._tool_to_skill.get(t["function"]["name"]) == "weather_query"]
        nurse_platform = [t for t in nurse_tools
                         if loader._tool_to_skill.get(t["function"]["name"]) in loader._platform]
        check("护理员只有 elder_care 的工具 (白名单过滤)",
              len(nurse_ec) == 3,  # record_checkin, log_health_data, trigger_emergency_alert
              f"got {len(nurse_ec)} elder_care tools: {[t['function']['name'] for t in nurse_ec]}")
        check("护理员无 weather_query 工具", len(nurse_wx) == 0,
              f"got {len(nurse_wx)}")
        check("护理员有 platform 工具", len(nurse_platform) > 0)

        # 无角色用户 → 只有 platform
        stranger_tools = await loader.get_tools_for_user(tenant_obj, "user_stranger", role_repo)
        stranger_non_platform = [t for t in stranger_tools
            if loader._tool_to_skill.get(t["function"]["name"]) not in loader._platform]
        check("无角色用户只有 platform 工具",
              len(stranger_non_platform) == 0,
              f"non-platform: {[t['function']['name'] for t in stranger_non_platform]}")

        # list_skills_for_tenant
        skills_list = loader.list_skills_for_tenant(tenant_obj)
        s_names = {s["name"] for s in skills_list}
        check("list_skills 包含 platform", any(s["scope"] == "platform" for s in skills_list))
        check("list_skills 不暴露未购买技能", "nonexistent" not in s_names)

    # ================================================================
    print("\n" + "=" * 60)
    print("Day 3: API 路由验证")
    print("=" * 60)

    from nidari.main import app
    route_paths = [r.path for r in app.routes if hasattr(r, "path")]
    for expected in [
        "/v1/admin/roles",
        "/v1/admin/roles/{role_id}",
        "/v1/admin/roles/{role_id}/skills",
        "/v1/admin/roles/{role_id}/skills/{skill_name}",
        "/v1/admin/roles/users/assign",
        "/v1/admin/roles/users/{user_id}/roles",
        "/v1/admin/roles/users/{user_id}/permissions",
        "/v1/skills",
        "/v1/skills/{skill_id}/tools",
    ]:
        check(f"路由 {expected} 已注册", expected in route_paths)

    # ================================================================
    print("\n" + "=" * 60)
    print("Day 4: TenantService 创建租户 + 自动角色初始化")
    print("=" * 60)

    async with async_session_factory() as session:
        svc = TenantService(
            SQLAlchemyTenantRepository(session),
            RoleRepository(session)
        )
        result = await svc.create_tenant(name="新测试租户", industry="education", plan="basic")
        await session.commit()

        check("返回 tenant", result["tenant"] is not None)
        check("返回 api_key (ak_...)", result["api_key"].startswith("ak_"))
        check("自动创建 admin 角色 (is_admin=True)",
              result["admin_role"]["is_admin"] == True)
        check("自动创建 default 角色 (is_default=True)",
              result["default_role"]["is_default"] == True)

        r = await RoleRepository(session).get_by_tenant(result["tenant"].id)
        check("新租户有 2 个默认角色", len(r) == 2, f"got {len(r)}")

    # ================================================================
    print("\n" + "=" * 60)
    print("权限矩阵验证 (方案文档中的矩阵)")
    print("=" * 60)

    async with async_session_factory() as session:
        rr = RoleRepository(session)
        # admin → __admin__
        g = await rr.get_effective_grants("tnt_test01", "user_admin")
        check("admin → __admin__", "__admin__" in g)

        # doctor → elder_care:*, weather_query:get_weather
        g = await rr.get_effective_grants("tnt_test01", "user_doctor")
        check("doctor → elder_care 无限制", g.get("elder_care") is None)
        check("doctor → weather_query=get_weather", g.get("weather_query") == ["get_weather"])
        check("doctor → 无 express_query", "express_query" not in g)

        # clerk (已撤销) → 空
        g = await rr.get_effective_grants("tnt_test01", "user_clerk")
        check("admin_clerk(已撤销) → 无技能", len(g) == 0, f"got {g}")

        # stranger → default（空）
        g = await rr.get_effective_grants("tnt_test01", "user_stranger")
        check("未分配用户 → 无技能", len(g) == 0)

    # ================================================================
    print("\n" + "=" * 60)
    print("内容定制路径验证")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        # 基础 elder_care
        ec = base / "elder_care"
        ec.mkdir()
        (ec / "SKILL.md").write_text(
            "---\nname: elder_care\ndescription: 基础\n---\n基础 body")
        (ec / "references").mkdir()
        (ec / "references" / "system.md").write_text("基础版 system prompt")

        # 租户定制
        tnt_ec = base / "tenants" / "tnt_test01" / "elder_care"
        tnt_ec.mkdir(parents=True)
        (tnt_ec / "SKILL.md").write_text(
            "---\nname: elder_care\ndescription: XX定制\n---\n定制 body")
        (tnt_ec / "references").mkdir()
        (tnt_ec / "references" / "system.md").write_text("XX医养集团专属品牌语言")

        # 角色补丁
        addon_dir = (base / "tenants" / "tnt_test01" / "_roles" /
                     "nursing_staff" / "elder_care" / "references")
        addon_dir.mkdir(parents=True)
        (addon_dir / "role_addon.md").write_text("护理人员特别说明：可以使用专业医疗术语")

        cl = SkillLoader(str(base))

        r = cl._resolve_skill("elder_care", "tnt_test01")
        check("租户定制版 system prompt 覆盖",
              r is not None and "XX医养集团" in (r.get("system_prompt") or ""),
              f"got: {(r.get('system_prompt','')[:60]) if r else 'None'}")

        addon = cl._load_role_addon("elder_care", "tnt_test01", "nursing_staff")
        check("role_addon.md 加载成功 (护理员)",
              addon is not None and "专业医疗术语" in addon)

        base_only = cl._resolve_skill("elder_care", "tnt_other")
        check("无定制的租户使用基础版",
              base_only is not None and "基础版" in (base_only.get("system_prompt") or ""))

        no_addon = cl._load_role_addon("elder_care", "tnt_test01", "doctor")
        check("医生角色无 role_addon → None", no_addon is None)

    # ================================================================
    print("\n" + "=" * 60)
    print("execute_tool 权限校验 (防绕过)")
    print("=" * 60)

    async with async_session_factory() as session:
        rr = RoleRepository(session)
        tenant_obj = await SQLAlchemyTenantRepository(session).get_by_id("tnt_test01")

        # 护理员调 weather_query → 拒绝
        try:
            await loader._assert_tool_access(tenant_obj, "user_nurse", rr,
                                              "weather_query", "get_weather")
            check("护理员调 weather_query → PermissionError", False, "未抛异常!")
        except PermissionError:
            check("护理员调 weather_query → PermissionError ✅", True)

        # 护理员调 express_query → 拒绝
        try:
            await loader._assert_tool_access(tenant_obj, "user_nurse", rr,
                                              "express_query", "track_package")
            check("护理员调 express_query → PermissionError", False, "未抛异常!")
        except PermissionError:
            check("护理员调 express_query → PermissionError ✅", True)

        # 护理员调允许的 elder_care 工具 → 通过
        try:
            await loader._assert_tool_access(tenant_obj, "user_nurse", rr,
                                              "elder_care", "record_checkin")
            check("护理员调 record_checkin → 通过 ✅", True)
        except PermissionError as e:
            check("护理员调允许工具 → 不应抛异常", False, str(e))

        # 护理员调未授权的 elder_care 工具 → 拒绝
        try:
            await loader._assert_tool_access(tenant_obj, "user_nurse", rr,
                                              "elder_care", "query_health_history")
            check("护理员调 query_health_history → PermissionError", False, "未抛异常!")
        except PermissionError:
            check("护理员调 query_health_history → PermissionError ✅", True)

        # 管理员调任意已购技能 → 通过
        try:
            await loader._assert_tool_access(tenant_obj, "user_admin", rr,
                                              "elder_care", "any_tool")
            check("管理员调 elder_care 任意工具 → 通过 ✅", True)
        except PermissionError:
            check("管理员 → 不应受限", False)

        # 管理员调未购买技能 → 拒绝
        try:
            await loader._assert_tool_access(tenant_obj, "user_admin", rr,
                                              "nonexistent_skill", "tool")
            check("管理员调未购买技能 → PermissionError", False, "未抛异常!")
        except PermissionError:
            check("管理员调未购买技能 → PermissionError ✅", True)

        # platform 技能始终允许
        try:
            await loader._assert_tool_access(tenant_obj, "user_nurse", rr,
                                              "task_scheduler", "any_tool")
            check("platform 技能 (task_scheduler) 始终允许 ✅", True)
        except PermissionError:
            check("platform 技能不应受限", False)

    # ================================================================
    print("\n" + "=" * 60)
    print("隔离验证 (租户间互不影响)")
    print("=" * 60)

    async with async_session_factory() as session:
        rr = RoleRepository(session)
        # 新租户的用户不应该能看到 tnt_test01 的角色
        g = await rr.get_effective_grants("tnt_new", "user_nurse")
        check("不同租户用户 → 无权限", len(g) == 0, f"got {g}")

    # ================================================================
    print("\n" + "=" * 60)
    total = PASS + FAIL
    print(f"测试结果: {PASS}/{total} 通过, {FAIL} 失败")
    print("=" * 60)

    if FAIL > 0:
        print("\n❌ 有失败项，请检查上方标记。")
        sys.exit(1)
    else:
        print("\n🎉 全部通过！四层权限控制功能符合需求文档预期。")

    # 清理
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)


if __name__ == "__main__":
    asyncio.run(run_tests())
