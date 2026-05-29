# Contributing to Nidari

感谢你对 Nidari 的关注。本项目采用 **AGPL-3.0 + 商业双授权**，贡献前请先阅读 [LICENSE](./LICENSE) 与 [COMMERCIAL-LICENSE.md](./COMMERCIAL-LICENSE.md)。

## 如何参与

1. **Fork** 本仓库，基于 `main` 创建分支（如 `feat/skill-xxx`、`fix/tenant-auth`）
2. 本地开发与自测（见下方）
3. 提交 **Pull Request**，说明变更动机与测试方式
4. 等待维护者 Review；合并后你的贡献将保留在提交历史中

## 开发环境

```bash
git clone https://github.com/sunny-dev-star/assistant.git
cd assistant

pip install -r requirements.txt
cp .env.example .env
# 编辑 .env，至少填入 DEEPSEEK_API_KEY

cd src
uvicorn assistant.main:app --host 0.0.0.0 --port 8000 --reload
```

健康检查：

```bash
curl http://localhost:8000/health
```

集成测试（可选）：

```bash
python3 tests/test_integration.py http://localhost:8000
```

## 贡献方向（欢迎）

- **技能（Skills）**：在 `skills/` 下新增行业技能包，遵循 [SKILL_SDK](docs/SKILL_SDK.md)
- **渠道适配**：飞书、钉钉、企业微信等 Webhook 适配器
- **文档**：README、API 文档、部署指南的中英文改进
- **Bug 修复**：附带复现步骤与测试
- **测试**：单元测试 / 集成测试补充

## 代码规范

- Python 3.10+，遵循项目现有 DDD 分层（`ui` → `app` → `domain` → `infrastructure`）
- 新增 API 路由请同步更新 `docs/API_SPEC.md`
- 日志使用英文；代码注释使用英文
- 不要提交 `.env`、密钥、真实租户数据

## 技能贡献指南

```bash
mkdir -p skills/my_skill/{references,scripts}
# 编写 skills/my_skill/SKILL.md + scripts/*.py
# 重启服务后 GET /v1/skills 应能看到新技能
```

详细规范见 [docs/SKILL_SDK.md](docs/SKILL_SDK.md)。

## Issue 与讨论

- **Bug**：使用 [Bug Report](.github/ISSUE_TEMPLATE/bug_report.yml) 模板
- **功能建议**：使用 [Feature Request](.github/ISSUE_TEMPLATE/feature_request.yml) 模板
- **安全问题**：请勿公开 Issue，请通过 COMMERCIAL-LICENSE.md 中的联系方式私信报告

## 许可证说明

向本项目提交的代码，默认以与项目相同的 **AGPL-3.0** 许可证发布。若你不同意，请勿提交 PR。
