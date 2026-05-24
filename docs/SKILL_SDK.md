# Agent Framework - 技能开发 SDK 文档 (Claude Skill 规范)

## 概述

技能（Skill）是 Agent Framework 的核心扩展单元。本框架全面采用 **Claude Skill 规范 (Progressive Disclosure)**，不再使用旧版的 `skill.json` 和 Python 面向对象类封装。
每个技能封装了特定行业或场景的能力，通过声明式的 Markdown 和原生脚本组成，支持热加载。

## 目录结构

符合 Claude Skill 规范的技能包结构如下：

```text
skills/my_skill/
├── SKILL.md            # 核心定义（必填）：包含 Frontmatter 工具 Schema 和技能说明
├── references/         # 参考知识（可选）：Markdown 格式的业务规则、系统提示词片段
│   └── rules.md
├── scripts/            # 可执行工具（可选）：具体的 Python 或 Bash 脚本
│   └── query_data.py
└── assets/             # 媒体资源（可选）：图片、多媒体文件
    └── logo.png
```

## 快速开始

### 1. 创建技能目录

```bash
mkdir -p skills/catering_service/{references,scripts,assets}
cd skills/catering_service
```

### 2. 编写 SKILL.md

`SKILL.md` 是技能的唯一核心入口，采用 YAML Frontmatter 定义元数据与工具 Schema。

```markdown
---
name: catering_service
description: 餐饮行业的智能客服和订座服务
version: 1.0.0
author: your_name
tools:
  - type: function
    function:
      name: query_menu
      description: 查询菜单信息和价格
      parameters:
        type: object
        properties:
          dish_type:
            type: string
            description: 菜品类别，如“招牌菜”、“主食”
        required: []
  - type: function
    function:
      name: make_reservation
      description: 帮助客户预约订座
      parameters:
        type: object
        properties:
          date:
            type: string
            description: 预约日期，如 "2026-05-18"
          time:
            type: string
            description: 预约时间，如 "18:30"
          people:
            type: integer
            description: 就餐人数
          name:
            type: string
            description: 客户姓名
          phone:
            type: string
            description: 客户电话
        required: [date, time, people, name, phone]
---

# 餐饮服务技能

这是餐饮客服的专属能力包，它提供了菜单查询、预约订座等核心能力。系统会自动将 `references/` 下的 Markdown 知识拼接进 System Prompt 中。
```

### 3. 编写参考知识 (references)

在 `references/rules.md` 中编写该技能的业务规则或背景知识：

```markdown
# 餐饮服务规则
你是一位专业的餐饮客服助手。

你的职责：
1. 回答客户关于菜单、价格、营业时间的问题
2. 帮助客户预约订座
3. 礼貌回复客户评价

规则：
- 语气亲切、热情
- 回答简洁，不超过 100 字
- 涉及退款/投诉时，请安抚客户情绪并记录
```

### 4. 编写工具执行脚本 (scripts)

在 `scripts/query_menu.py` 中编写原生工具实现。框架会自动将大模型的 tool_calls 映射执行：

```python
import sys
import json

def query_menu(dish_type=None):
    menu = {
        "招牌菜": [
            {"name": "红烧肉", "price": 68, "description": "秘制酱料，肥而不腻"},
            {"name": "清蒸鲈鱼", "price": 88, "description": "新鲜活鱼，现点现做"}
        ],
        "主食": [
            {"name": "扬州炒饭", "price": 28},
            {"name": "牛肉面", "price": 32}
        ]
    }
    
    if dish_type and dish_type in menu:
        return json.dumps(menu[dish_type], ensure_ascii=False)
    return json.dumps(menu, ensure_ascii=False)

if __name__ == "__main__":
    # 解析来自框架的参数
    args = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
    result = query_menu(args.get("dish_type"))
    print(result)
```

## 技能加载机制

系统启动时，`SkillLoader` 会扫描 `skills/` 目录，并按如下三级逐步加载：

1. **Level 1 (元数据)**：解析 `SKILL.md` 的 Frontmatter，提取工具列表与描述。
2. **Level 2 (主体)**：提取 `SKILL.md` 的正文。
3. **Level 3 (按需资源)**：当 LLM 需要执行工具时，动态加载 `scripts/` 中的代码；当构建 Prompt 时，加载 `references/` 的知识片段。

你可以在运行中通过上传新的符合规范的目录，或在后台触发热重载。
