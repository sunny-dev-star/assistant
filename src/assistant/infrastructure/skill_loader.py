"""
技能加载器 - 四层权限感知

Layer 1: 平台技能（platform/）— 所有租户、所有角色自动可用
Layer 2: 租户技能授权（tenants.enabled_skills）— 租户购买/开通
Layer 3: 角色技能权限（role_skill_grants）— 角色能用哪些工具
Layer 4: 内容定制（skills/tenants/{tenant_id}/）— 租户/角色定制 prompt

目录约定：
  skills/platform/{skill}/           平台技能，所有人自动可用
  skills/{skill}/                    行业基础技能
  skills/tenants/{tenant_id}/{skill}/  租户定制覆盖（prompt/rules）
  skills/tenants/{tenant_id}/_roles/{role_name}/{skill}/
                                     角色专属 prompt 补丁
"""
import json
import re
import logging
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class SkillLoader:
    """
    四层权限感知的技能加载器。
    保持原有公共 API 兼容，新增 get_tools_for_user / get_system_prompt_for_user 等权限感知方法。
    """

    PLATFORM_DIR = "platform"
    TENANTS_DIR = "tenants"
    ROLES_DIR = "_roles"

    def __init__(self, skills_dir: str = "skills"):
        self.skills_dir = Path(skills_dir)
        # 兼容旧 API
        self.skills: Dict[str, Any] = {}
        self._tool_to_skill: Dict[str, str] = {}

        # 新四层缓存
        self._platform: Dict[str, dict] = {}   # 平台技能缓存
        self._industry: Dict[str, dict] = {}    # 行业技能缓存
        self._load_all_base_skills()

    # ═══════════════════════════════════════════════════════
    # 启动加载（保持兼容 + 新增四层结构解析）
    # ═══════════════════════════════════════════════════════

    def _load_all_base_skills(self):
        """加载平台技能和行业基础技能（不含租户定制）"""
        if not self.skills_dir.exists():
            return

        for item in sorted(self.skills_dir.iterdir()):
            if not item.is_dir() or item.name.startswith(("_", ".")):
                continue

            if item.name == self.PLATFORM_DIR:
                # 加载平台技能
                for sub in item.iterdir():
                    if sub.is_dir() and (sub / "SKILL.md").exists():
                        skill = self._parse_skill_md(sub)
                        if skill:
                            skill["scope"] = "platform"
                            self._platform[skill["name"]] = skill
                            # 兼容旧结构
                            self.skills[skill["name"]] = self._to_legacy_format(sub, skill)
                            for t in skill["tools"]:
                                self._tool_to_skill[t["function"]["name"]] = skill["name"]
                            logger.info(f"平台技能加载: {skill['name']}")

            elif item.name == self.TENANTS_DIR:
                pass  # 租户定制目录，按需动态加载

            else:
                # 行业基础技能
                if (item / "SKILL.md").exists():
                    skill = self._parse_skill_md(item)
                    if skill:
                        skill["scope"] = "industry"
                        self._industry[skill["name"]] = skill
                        # 兼容旧结构
                        self.skills[skill["name"]] = self._to_legacy_format(item, skill)
                        for t in skill["tools"]:
                            self._tool_to_skill[t["function"]["name"]] = skill["name"]
                        logger.info(f"行业技能加载: {skill['name']}")

    def load_all(self) -> Dict[str, Any]:
        """兼容旧 API：返回 skills dict"""
        return self.skills

    # ═══════════════════════════════════════════════════════
    # 核心公开接口（四层权限感知）
    # ═══════════════════════════════════════════════════════

    async def get_tools_for_user(
        self, tenant, user_id: str, role_repo=None, role_name: str = None
    ) -> list[dict]:
        """
        返回该用户在该租户下可用的工具列表。
        这是唯一应该传给 LLM 的工具入口。
        """
        # Layer 1：platform 技能，无条件加载
        tools = []
        for skill in self._platform.values():
            tools.extend(skill["tools"])

        if not role_repo:
            # 无角色仓储（兼容旧模式）：返回所有工具
            for skill in self._industry.values():
                tools.extend(skill["tools"])
            return tools

        # Layer 2+3：行业技能，走角色权限
        effective_grants = await role_repo.get_effective_grants(
            tenant.id, user_id
        )
        tenant_enabled = set(tenant.config.get("enabled_skills", []))

        # 管理员：租户所有已购技能全开
        if "__admin__" in effective_grants:
            for skill_name in tenant_enabled:
                skill = self._resolve_skill(skill_name, tenant.id, role_name)
                if skill:
                    tools.extend(skill["tools"])
            return tools

        # 普通角色：按授权过滤
        for skill_name, tool_whitelist in effective_grants.items():
            if skill_name not in tenant_enabled:
                continue  # 租户未购买此技能

            skill = self._resolve_skill(skill_name, tenant.id, role_name)
            if not skill:
                continue

            if tool_whitelist is None:
                tools.extend(skill["tools"])
            else:
                tools.extend([
                    t for t in skill["tools"]
                    if t["function"]["name"] in tool_whitelist
                ])

        return tools

    async def get_system_prompt_for_user(
        self, tenant, user_id: str, role_repo=None, role_name: str = None
    ) -> str:
        """
        返回该用户可见的完整 system prompt。
        按角色权限过滤，并合并角色专属 prompt 补丁。
        """
        parts = []

        # platform 技能的 system prompt
        for skill in self._platform.values():
            if skill.get("system_prompt"):
                parts.append(skill["system_prompt"])

        if not role_repo:
            for skill in self._industry.values():
                if skill.get("system_prompt"):
                    parts.append(skill["system_prompt"])
            return "\n\n---\n\n".join(parts)

        # 行业技能的 system prompt（按权限过滤）
        effective_grants = await role_repo.get_effective_grants(
            tenant.id, user_id
        )
        tenant_enabled = set(tenant.config.get("enabled_skills", []))

        if "__admin__" in effective_grants:
            skill_names = tenant_enabled
        else:
            skill_names = {
                s for s in effective_grants if s in tenant_enabled
            }

        for skill_name in skill_names:
            skill = self._resolve_skill(skill_name, tenant.id, role_name)
            if skill and skill.get("system_prompt"):
                parts.append(skill["system_prompt"])

            # 追加角色专属 prompt 补丁（若有）
            addon = self._load_role_addon(
                skill_name, tenant.id, role_name
            )
            if addon:
                parts.append(addon)

        return "\n\n---\n\n".join(parts)

    async def execute_tool(self, tool_name: str, args: dict,
                           tenant=None, user_id: str = None,
                           role_repo=None) -> str:
        """
        执行工具。
        保持旧签名兼容，新增权限校验参数。
        """
        # 权限校验（防绕过）
        if tenant and user_id and role_repo:
            skill_name = self._tool_to_skill.get(tool_name, "")
            await self._assert_tool_access(
                tenant, user_id, role_repo, skill_name, tool_name
            )

        skill_id = self._tool_to_skill.get(tool_name)
        if not skill_id:
            return json.dumps({"error": f"Unknown: {tool_name}"}, ensure_ascii=False)

        # 找到技能目录
        skill_dir = self._get_skill_dir(skill_id)
        if not skill_dir:
            return json.dumps({"error": f"Skill not found: {skill_id}"}, ensure_ascii=False)

        # 查找脚本
        script = skill_dir / "scripts" / f"{tool_name}.py"
        if not script.exists():
            script = self._find_script_legacy(skill_id, tool_name)

        if script and script.exists():
            cmd = ["python3", str(script)]
            for k, v in args.items():
                cmd.extend([f"--{k.replace('_', '-')}", str(v)])
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE)
            stdout, stderr = await proc.communicate()
            if proc.returncode == 0:
                return stdout.decode().strip()
            return json.dumps({"error": stderr.decode().strip()[:200]}, ensure_ascii=False)

        return json.dumps({"error": f"No script for: {tool_name}"}, ensure_ascii=False)

    def list_skills_for_tenant(self, tenant) -> list[dict]:
        """返回租户可见的技能列表（不暴露未购买技能）"""
        enabled = set(tenant.config.get("enabled_skills", []))
        result = []

        for skill in self._platform.values():
            result.append({
                "name": skill["name"],
                "description": skill["description"],
                "scope": "platform",
                "tool_count": len(skill["tools"]),
            })

        for name, skill in self._industry.items():
            if name in enabled:
                result.append({
                    "name": name,
                    "description": skill["description"],
                    "scope": "industry",
                    "tool_count": len(skill["tools"]),
                })

        return result

    # ═══════════════════════════════════════════════════════
    # 内容解析（私有）
    # ═══════════════════════════════════════════════════════

    def _resolve_skill(
        self, skill_name: str, tenant_id: str, role_name: str = None
    ) -> Optional[dict]:
        """
        按优先级解析技能内容：
        1. 租户定制版（若有）
        2. 行业基础版
        合并：基础工具 schema 不变，references 被覆盖
        """
        base = self._industry.get(skill_name)
        if not base:
            return None

        # 查找租户定制目录
        tenant_dir = (
            self.skills_dir / self.TENANTS_DIR
            / tenant_id / skill_name
        )
        if not tenant_dir.exists():
            return base

        # 有租户定制：加载并覆盖 system_prompt，工具 schema 保持基础版
        override = self._parse_skill_md(tenant_dir, base_skill=base)
        return override if override else base

    def _load_role_addon(
        self, skill_name: str, tenant_id: str, role_name: str
    ) -> Optional[str]:
        """加载角色专属 prompt 补丁（仅追加，不覆盖基础 prompt）"""
        if not role_name:
            return None
        addon_path = (
            self.skills_dir / self.TENANTS_DIR / tenant_id
            / self.ROLES_DIR / role_name / skill_name
            / "references" / "role_addon.md"
        )
        if addon_path.exists():
            return addon_path.read_text(encoding="utf-8")
        return None

    def _get_skill_dir(self, skill_name: str) -> Optional[Path]:
        """获取技能目录（兼容 platform 和 industry）"""
        if skill_name in self._platform:
            for d in (self.skills_dir / self.PLATFORM_DIR).iterdir():
                if d.is_dir() and (d / "SKILL.md").exists():
                    skill = self._parse_skill_md(d)
                    if skill and skill["name"] == skill_name:
                        return d
        if skill_name in self._industry:
            d = self.skills_dir / skill_name
            if d.exists():
                return d
        # fallback: 直接搜
        d = self.skills_dir / skill_name
        return d if d.exists() else None

    def _parse_skill_md(
        self, skill_dir: Path, base_skill: dict = None
    ) -> Optional[dict]:
        """
        解析 SKILL.md：
        - Frontmatter → tools schema、元数据
        - references/*.md → 拼接为 system_prompt
        如果传入 base_skill，则工具 schema 继承 base，只覆盖 system_prompt
        """
        md_path = skill_dir / "SKILL.md"
        if not md_path.exists():
            return None

        content = md_path.read_text(encoding="utf-8")
        match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)', content, re.DOTALL)
        if not match:
            return None

        try:
            import yaml
            meta = yaml.safe_load(match.group(1)) or {}
        except Exception:
            meta = self._yaml_fallback(match.group(1))

        # 加载 references/（系统提示词）
        system_prompt = self._load_references(skill_dir)

        # 工具 schema：有 base 时继承，否则从 frontmatter 取
        tools = (base_skill["tools"] if base_skill
                 else self._parse_tools(meta.pop("tools", None)))

        return {
            "name": meta.get("name", skill_dir.name),
            "description": meta.get("description", ""),
            "version": meta.get("version", "1.0.0"),
            "scope": meta.get("scope", "industry"),
            "tools": tools,
            "system_prompt": system_prompt,
            "scripts_dir": str(skill_dir / "scripts"),
        }

    def _load_references(self, skill_dir: Path) -> str:
        refs_dir = skill_dir / "references"
        if not refs_dir.exists():
            return ""
        parts = []
        for f in sorted(refs_dir.glob("*.md")):
            parts.append(f.read_text(encoding="utf-8"))
        return "\n\n".join(parts)

    def _parse_tools(self, data) -> list:
        """解析工具 schema"""
        if not data:
            return []
        tools = []
        for item in data:
            if isinstance(item, dict) and "name" in item:
                tools.append({"type": "function", "function": {
                    "name": item["name"],
                    "description": item.get("description", ""),
                    "parameters": item.get("parameters", {"type": "object", "properties": {}}),
                }})
            elif isinstance(item, str):
                tools.append({"type": "function", "function": {
                    "name": item, "description": item,
                    "parameters": {"type": "object", "properties": {}},
                }})
        return tools

    def _yaml_fallback(self, text: str) -> dict:
        """YAML 解析回退"""
        result = {}
        for line in text.split("\n"):
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            m = re.match(r'^(\w+):\s*(.*)', s)
            if not m:
                continue
            k, v = m.group(1), m.group(2).strip()
            if v.startswith("[") or v.startswith("{"):
                try:
                    result[k] = json.loads(v)
                except Exception:
                    result[k] = v
            elif v.startswith('"') and v.endswith('"'):
                result[k] = v[1:-1]
            elif v.startswith("'") and v.endswith("'"):
                result[k] = v[1:-1]
            elif v:
                result[k] = int(v) if v.isdigit() else v
        return result

    # ═══════════════════════════════════════════════════════
    # 权限校验（私有）
    # ═══════════════════════════════════════════════════════

    async def _assert_tool_access(
        self, tenant, user_id: str, role_repo,
        skill_name: str, tool_name: str
    ):
        """execute_tool 的最后一道防线"""
        # platform 技能始终允许
        if skill_name in self._platform:
            return

        grants = await role_repo.get_effective_grants(
            tenant.id, user_id
        )
        tenant_enabled = set(tenant.config.get("enabled_skills", []))

        if "__admin__" in grants:
            if skill_name not in tenant_enabled:
                raise PermissionError(
                    f"租户 {tenant.id} 未购买技能 {skill_name}"
                )
            return

        if skill_name not in tenant_enabled:
            raise PermissionError(
                f"租户 {tenant.id} 未购买技能 {skill_name}"
            )

        tool_whitelist = grants.get(skill_name)
        if tool_whitelist is not None and tool_name not in tool_whitelist:
            raise PermissionError(
                f"角色无权调用工具 {skill_name}.{tool_name}"
            )

    # ═══════════════════════════════════════════════════════
    # 旧 API 兼容层
    # ═══════════════════════════════════════════════════════

    def _to_legacy_format(self, skill_dir: Path, skill: dict) -> dict:
        """将新的四层结构转为旧格式（兼容旧代码）"""
        md_path = skill_dir / "SKILL.md"
        body = ""
        if md_path.exists():
            content = md_path.read_text(encoding="utf-8")
            m = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)', content, re.DOTALL)
            if m:
                body = m.group(2).strip()

        refs = self._scan(skill_dir / "references", (".md",))
        scripts = self._scan(skill_dir / "scripts", (".py", ".sh"))
        assets = self._scan_assets(skill_dir / "assets")

        return {
            "metadata": {
                "name": skill["name"],
                "description": skill["description"],
                "version": skill.get("version", "1.0.0"),
            },
            "body": body,
            "tools": skill["tools"],
            "dir": str(skill_dir),
            "skill_md": str(md_path),
            "references": refs,
            "scripts": scripts,
            "assets": assets,
        }

    def _scan(self, d: Path, exts: tuple) -> list:
        if not d.exists():
            return []
        return [{"name": f.stem, "filename": f.name, "path": str(f)}
                for f in d.iterdir() if f.suffix in exts and not f.name.startswith("_")]

    def _scan_assets(self, d: Path) -> list:
        if not d.exists():
            return []
        return [{"name": f.stem, "filename": str(f.relative_to(d)), "path": str(f)}
                for f in d.rglob("*") if f.is_file() and not f.name.startswith("_")]

    def _find_script_legacy(self, skill_id: str, tool_name: str) -> Optional[Path]:
        """从旧结构中查找脚本"""
        skill_data = self.skills.get(skill_id, {})
        skill_dir = Path(skill_data.get("dir", ""))
        # 查找所有脚本
        for s in skill_data.get("scripts", []):
            sp = Path(s["path"])
            if tool_name.replace("_", "-") in sp.stem or tool_name in sp.stem:
                return sp
        return skill_dir / "scripts" / f"{tool_name}.py"

    # ═══════════════════════════════════════════════════════
    # 公共兼容 API
    # ═══════════════════════════════════════════════════════

    def get_all_tools_with_skill_tag(self) -> list:
        """Return all tools with _skill_name tag for tenant filtering"""
        result = []
        for skill_name, skill in self.skills.items():
            for t in skill["tools"]:
                tagged = dict(t)
                tagged["_skill_name"] = skill_name
                result.append(tagged)
        return result

    def get_all_tools(self) -> list:
        return [t for s in self.skills.values() for t in s["tools"]]

    def get_skill_descriptions(self) -> str:
        lines = []
        for sid, s in self.skills.items():
            desc = s["metadata"].get("description", "")
            lines.append(f"- **{sid}**: {desc}")
        return "\n".join(lines)

    def get_skill_body(self, skill_id: str) -> Optional[str]:
        return self.skills.get(skill_id, {}).get("body")

    def read_reference(self, skill_id: str, name: str) -> Optional[str]:
        for r in self.skills.get(skill_id, {}).get("references", []):
            if r["name"] == name or r["filename"] == name:
                return Path(r["path"]).read_text(encoding="utf-8")
        return None

    def read_script(self, skill_id: str, name: str) -> Optional[str]:
        for s in self.skills.get(skill_id, {}).get("scripts", []):
            if s["name"] == name or s["filename"] == name:
                return Path(s["path"]).read_text(encoding="utf-8")
        return None

    def get_skill_info(self) -> list:
        return [{
            "id": sid,
            "description": s["metadata"].get("description", ""),
            "tools": [t["function"]["name"] for t in s["tools"]],
            "has_references": bool(s["references"]),
            "has_scripts": bool(s["scripts"]),
        } for sid, s in self.skills.items()]

    @property
    def tool_count(self):
        return len(self._tool_to_skill)

    @property
    def skill_count(self):
        return len(self.skills)
