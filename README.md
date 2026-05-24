# Assistant - 智能体框架

基于 Dify 二次开发的面向中小企业的智能体框架。

## 技术栈

- **后端**: Python 3.11 + FastAPI
- **前端**: Vue 3 + Element Plus
- **引擎**: Dify Self-Hosted
- **数据库**: PostgreSQL 15 + Redis 7
- **容器**: Docker + Docker Compose

## 项目结构

`
.
├── src/                    # 源代码
│   ├── assistant/          # 核心应用
│   │   ├── domain/         # 领域层
│   │   ├── application/    # 应用层 (TODO: rename to app)
│   │   ├── infrastructure/ # 基础设施层
│   │   ├── interfaces/     # 接口层 (TODO: rename to ui)
│   │   └── shared/         # 共享层
│   ├── requirements.txt    # Python 依赖
│   └── Dockerfile          # 容器镜像
├── skills/                 # 行业技能包
├── docs/                   # 文档
├── nginx/                  # Nginx 配置
├── monitoring/             # 监控配置
├── docker-compose.yml      # 容器编排
└── .env                    # 环境变量
`

## 快速开始

`ash
# 1. 安装依赖
cd src
pip install -r requirements.txt

# 2. 启动服务
cd ..
docker-compose up -d

# 3. 运行应用
cd src
uvicorn assistant.main:app --reload
`

## 文档

- [PRD](docs/PRD.md) - 产品需求文档
- [DESIGN](docs/DESIGN.md) - 技术设计文档
- [API_SPEC](docs/API_SPEC.md) - API 接口规范
- [SKILL_SDK](docs/SKILL_SDK.md) - 技能开发 SDK

## 许可证

MIT
