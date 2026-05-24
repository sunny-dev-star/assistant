---
name: task_scheduler
description: 平台级定时任务工具，所有租户自动可用，无需配置。当用户表达定时、周期性、提醒类需求时调用。
version: 1.0.0
scope: platform
tools:
  - name: create_task
    description: >
      当用户表达任何定时、周期性、提醒类需求时调用。
      识别关键词：每天、每周、明天、定时、提醒、定期、周期、自动。
      调用前将时间转换为标准格式：
      周期任务 -> cron:<表达式> 例：cron:0 8 * * *
      一次性 -> once:<ISO时间> 例：once:2026-06-01T14:00:00
      执行模式选择：
      步骤固定且顺序明确 -> pipeline
      需根据结果决策下一步 -> agent_mission
      单工具 -> skill_invoke
      固定文本 -> message
    parameters:
      type: object
      properties:
        task_type:
          type: string
          description: 任务业务标签，如 medication_reminder / daily_checkin
        display_name:
          type: string
          description: 展示给用户的任务名称
        schedule:
          type: string
          description: "cron:0 8 * * * 或 once:2026-06-01T14:00:00"
        execution_type:
          type: string
          enum: [message, skill_invoke, pipeline, agent_mission]
          description: 执行模式
        message:
          type: string
          description: execution_type=message 时的固定推送文本
        skill_name:
          type: string
          description: skill_invoke 模式的技能名
        tool_name:
          type: string
          description: skill_invoke 模式的工具名
        tool_args:
          type: object
          description: 工具业务参数
        steps:
          type: array
          description: pipeline 模式的步骤列表
          items:
            type: object
            properties:
              step_id: { type: string }
              skill_name: { type: string }
              tool_name: { type: string }
              args: { type: object }
              result_key: { type: string }
              inject_results:
                type: array
                items: { type: string }
        mission_prompt:
          type: string
          description: agent_mission 模式的任务目标
        mission_skills:
          type: array
          description: agent_mission 可调用的技能白名单
          items: { type: string }
        context_as_input:
          type: boolean
          description: 是否将上次结果注入本次 prompt
        skill_disabled_action:
          type: string
          enum: [skip, notify_admin, deactivate_task]
          description: 技能不可用时的处理策略
      required: [task_type, schedule, execution_type]

  - name: list_tasks
    description: 列出用户当前所有活跃的定时任务。用户问"我设了什么提醒"时调用。
    parameters:
      type: object
      properties:
        limit:
          type: integer
          description: 最多返回条数，默认10
      required: []

  - name: cancel_task
    description: 取消一个定时任务。用户说"取消提醒"、"不用叫我了"时调用。
    parameters:
      type: object
      properties:
        task_id:
          type: string
          description: 任务ID，从 list_tasks 结果获取
      required: [task_id]
---

## 平台级定时任务工具

所有租户自动获得本工具，无需在 enabled_skills 中配置。
当用户在对话中表达定时需求时直接调用，无需询问技术细节。
时间解析交由 LLM 负责，脚本只处理标准格式输入。
