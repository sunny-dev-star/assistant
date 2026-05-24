"""
技能加载器 - Claude Skill 规范

SKILL.md 是唯一的技能定义文件。
工具定义在 frontmatter 的 tools 字段（JSON Schema）。
工具实现在 scripts/ 目录（可执行脚本）。
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class SkillLoader:
    """技能加载器（Claude Skill 规范）"""

    def __init__(self, skills_dir: str = "skills"):
        self.skills_dir = Path(skills_dir)
        self.skills: Dict[str, Any] = {}
        self._tool_to_skill: Dict[str, str] = {}

    def load_all(self) -> Dict[str, Any]:
        if not self.skills_dir.exists():
            return {}
        for d in sorted(self.skills_dir.iterdir()):
            if d.is_dir() and not d.name.startswith(("_", ".")):
                try:
                    self._load(d)
                except Exception as e:
                    logger.error(f"Failed: {d}: {e}")
        logger.info(f"Loaded {len(self.skills)} skills, {len(self._tool_to_skill)} tools")
        return self.skills

    def _load(self, d: Path):
        md = d / "SKILL.md"
        if not md.exists():
            return
        metadata, body, tools = self._parse_md(md)
        name = metadata.get("name")
        if not name:
            return

        refs = self._scan(d / "references", (".md",))
        scripts = self._scan(d / "scripts", (".py", ".sh"))
        assets = self._scan_assets(d / "assets")

        self.skills[name] = {
            "metadata": metadata, "body": body, "tools": tools,
            "dir": str(d), "skill_md": str(md),
            "references": refs, "scripts": scripts, "assets": assets,
        }
        for t in tools:
            self._tool_to_skill[t["function"]["name"]] = name

        logger.info(f"✅ {name} ({len(tools)} tools, {len(refs)} refs, {len(scripts)} scripts)")

    def _parse_md(self, md: Path):
        content = md.read_text(encoding="utf-8")
        m = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)', content, re.DOTALL)
        if not m:
            return {}, content, []
        metadata = self._yaml(m.group(1))
        body = m.group(2).strip()
        tools = self._parse_tools(metadata.pop("tools", None))
        return metadata, body, tools

    def _parse_tools(self, data) -> list:
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

    def _yaml(self, text: str) -> dict:
        """Parse YAML frontmatter with full nested structure support"""
        try:
            import yaml
            return yaml.safe_load(text) or {}
        except Exception:
            # Fallback to simple parser
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
                    except:
                        result[k] = v
                elif v.startswith('"') and v.endswith('"'):
                    result[k] = v[1:-1]
                elif v.startswith("'") and v.endswith("'"):
                    result[k] = v[1:-1]
                elif v:
                    result[k] = int(v) if v.isdigit() else v
            return result

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

    # ===== 公共 API =====

    def get_all_tools(self) -> list:
        return [t for s in self.skills.values() for t in s["tools"]]

    async def execute_tool(self, tool_name: str, args: dict) -> str:
        """执行工具：在技能目录下找同名脚本并运行"""
        skill_id = self._tool_to_skill.get(tool_name)
        if not skill_id:
            return json.dumps({"error": f"Unknown: {tool_name}"}, ensure_ascii=False)
        skill = self.skills.get(skill_id, {})

        # 查找脚本: tools/<tool_name>.py 或 scripts/<tool_name>.py
        skill_dir = Path(skill["dir"])
        script = skill_dir / "scripts" / f"{tool_name}.py"
        if not script.exists():
            # fallback: 查找 SKILL.md body 中提到的脚本映射
            script = self._find_script_for_tool(skill, tool_name)

        if script and script.exists():
            import asyncio
            cmd = ["python3", str(script)]
            for k, v in args.items():
                cmd.extend([f"--{k.replace('_', '-')}", str(v)])
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            stdout, stderr = await proc.communicate()
            if proc.returncode == 0:
                return stdout.decode().strip()
            return json.dumps({"error": stderr.decode().strip()[:200]}, ensure_ascii=False)

        return json.dumps({"error": f"No script for: {tool_name}"}, ensure_ascii=False)

    def _find_script_for_tool(self, skill: dict, tool_name: str) -> Optional[Path]:
        """从 SKILL.md body 中查找工具对应的脚本"""
        body = skill.get("body", "")
        skill_dir = Path(skill["dir"])
        # 查找所有脚本
        for s in skill.get("scripts", []):
            sp = Path(s["path"])
            if tool_name.replace("_", "-") in sp.stem or tool_name in sp.stem:
                return sp
        # 默认: scripts/<tool_name>.py
        return skill_dir / "scripts" / f"{tool_name}.py"

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

    def get_skill_info(self) -> list:
        return [{
            "id": sid,
            "description": s["metadata"].get("description", ""),
            "tools": [t["function"]["name"] for t in s["tools"]],
            "has_references": bool(s["references"]),
            "has_scripts": bool(s["scripts"]),
        } for sid, s in self.skills.items()]

    @property
    def tool_count(self): return len(self._tool_to_skill)
    @property
    def skill_count(self): return len(self.skills)
