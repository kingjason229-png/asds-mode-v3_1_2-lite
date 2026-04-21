---
name: asds-mode
version: 3.1.2
description: ASDS Lite 全自动开发工作流。当用户提到「全自动开发」「ASDS」「autonomous devops」「无人值守」「持续集成」时激活。
---

# ASDS Lite - 瘦身后的全自动开发工作流

ASDS Lite 的目标不是“功能最多”，而是“最小可靠闭环”。

人类只做三件事：
1. 提需求
2. 回答必要澄清
3. 验收结果

其余流程由系统自动推进，但只保留最小内核。

## 核心原则（不可违反）

1. `tasks.json` 是唯一事实源
2. 只保留三个角色：`orchestrator` / `coder` / `qa`
3. `orchestrator` 兼任 PM 拆解，不再单独设置 PM Agent
4. 串行执行：同一项目同一时间只允许一个活跃任务
5. `coder` 负责实现 + 跑项目定义的验证链
6. `qa` 只做静态业务复核，不改代码、不重复跑一套新测试
7. `PROGRESS.md` 只允许 `orchestrator` 写
8. 所有状态变更必须原子写入 `tasks.json`
9. 自动化只保留主闭环，不保留外围运营层自动化
10. 每个 task 优先保留 `affected_files / verification_summary / verification_artifacts`
11. `BLOCKED` 不扩子状态；如需说明阻塞原因，用 `blocker_type`
12. `RETRY` 必须累计 `retry_count`，达到阈值后升级为 `BLOCKED`
13. 复杂或歧义需求先产轻量 `design.md` / `clarified-demand.md`，再拆 `tasks.json`
14. task 允许增强字段，但只能做增量约束，不能破坏 Lite 5 态和唯一真相源
15. `bugfix` 任务必须记录 `reproduce / root_cause / minimal_fix / regression_verify`
16. QA 输出必须结构化：`result / issue_level / findings / evidence / next_action`
17. DONE 前必须完成轻量 closeout：版本号、变更摘要、验证证据收口

---

## 系统架构

```text
用户
  ↓
DEMAND.md
  ↓
orchestrator
  ├─ 读取需求并拆成 tasks.json
  ├─ 派发 coder
  ├─ 派发 qa
  ├─ 写 PROGRESS.md
  └─ 处理 RETRY / BLOCKED
        ↓
     tasks.json
```

---

## 三角色

### orchestrator
职责：
- 读取 `DEMAND.md`
- 需求不清时向用户澄清
- 复杂/歧义需求先产轻量 `design.md` / `clarified-demand.md`
- 生成/维护 `tasks.json`
- 串行派发 `coder`
- 在 `coder` 完成后派发 `qa`
- QA PASS 后执行轻量 closeout（版本号 / 变更摘要 / 交付证据收口）
- 更新 `PROGRESS.md`
- 处理 `BLOCKED`

禁止：
- 不写业务代码
- 不从对话历史推断任务状态

### coder
职责：
- 读取当前任务
- 修改代码
- `bugfix` 任务先做 `reproduce / root_cause / minimal_fix / regression_verify`
- 执行项目定义的验证链
- 更新 `tasks.json`

禁止：
- 不自行扩展需求
- 不跳过验证直接标记 `DONE`

### qa
职责：
- 对照 `acceptance_criteria` 做静态复核
- 基于代码、diff、验证结果判断 `DONE / RETRY / BLOCKED`
- 按结构化模板输出 `result / issue_level / findings / evidence / next_action`
- 更新 `tasks.json`

禁止：
- 不改代码
- 不重复跑一整套动态测试体系
- 不自行新增需求

---

## 状态机（只保留 5 个状态）

```text
PENDING
  ↓
IN_PROGRESS
  ├─ 验证通过 → DONE
  ├─ 需要修改 → RETRY
  └─ 需人工介入 → BLOCKED

RETRY
  ↓
PENDING
```

说明：
- 不再单独使用 `FAILED`
- 只要系统还能自动继续，就走 `RETRY`
- 只有确实需要人介入时才进入 `BLOCKED`
- `BLOCKED` 的原因写在 `blocker_type`，不新增子状态
- `RETRY` 必须累计 `retry_count`；达到阈值自动升级为 `BLOCKED`
- 用户补齐 blocker 后，直接走现有 `resume` 入口恢复，由 orchestrator 决定是否重新打开任务

---

## 项目结构标准

每个 ASDS Lite 项目必须有：

```text
项目目录/
├── DEMAND.md
├── tasks.json
├── AGENTS.md
└── PROGRESS.md
```

按最小侵入原则，可按需新增两个轻量文件：

```text
项目目录/
├── design.md                # 复杂/歧义需求时先产出
└── delivery-note.md         # closeout 时补变更摘要（可选）
```

### 文件职责
- `DEMAND.md`：原始需求
- `design.md`：复杂/歧义需求的轻量澄清稿；只写 `goal / non_goals / acceptance_criteria / risks_assumptions`
- `tasks.json`：唯一事实源
- `AGENTS.md`：本项目验证命令定义
- `PROGRESS.md`：由 orchestrator 写的摘要日志
- `delivery-note.md`：轻量交付摘要，可选

---

## tasks.json 建议结构

```json
{
  "project": "example-project",
  "active_task_id": null,
  "tasks": [
    {
      "id": "TASK-001",
      "title": "实现登录表单",
      "task_type": "feature",
      "target_files": ["src/pages/Login.tsx", "src/components/LoginForm.tsx"],
      "acceptance_criteria": [
        "用户可输入手机号",
        "提交后有成功/失败反馈"
      ],
      "verification_commands": [
        "npm run test -- login",
        "npm run build"
      ],
      "depends_on": [],
      "risk_level": "medium",
      "status": "PENDING",
      "retry_count": 0,
      "affected_files": [],
      "verification_summary": "",
      "verification_artifacts": [],
      "notes": ""
    }
  ]
}
```

建议字段：
- `id`
- `title`
- `task_type`（如 `feature / bugfix / refactor / docs`）
- `target_files`
- `acceptance_criteria`
- `verification_commands`
- `depends_on`
- `risk_level`
- `status`
- `retry_count`
- `affected_files`
- `verification_summary`
- `verification_artifacts`
- `notes`

兼容规则：
- 这些字段是增量增强，不新增主状态
- 老任务缺少增强字段时允许兼容读取，但 orchestrator 新建任务时应尽量写全
- `bugfix` 任务建议在 `notes` 或任务对象中写出 `reproduce / root_cause / minimal_fix / regression_verify`

暂不引入：
- 并发派发字段
- 多项目调度字段
- 复杂依赖图字段
- 运营层巡检字段

---

## tasks.json 原子写入（强制）

必须使用：
1. 读取当前 JSON
2. 修改内存对象
3. 先写入 `tasks.json.tmp`
4. 回读校验 JSON
5. `rename` 原子替换 `tasks.json`

禁止：
- `echo > tasks.json`
- 手写字符串拼 JSON
- `truncate` 后直接覆盖但无回滚

---

## AGENTS.md 验证链（项目定义）

不要把验证链写死为 `lint -> typecheck -> test -> build`。

改为：每个项目在 `AGENTS.md` 里定义自己的验证命令，例如：

```text
Validation:
1. npm run lint
2. npm run test
3. npm run build
```

规则：
- 有什么就跑什么
- 没有的项标记 `N/A`
- 至少要有一个可代表交付质量的验证步骤

---

## PROGRESS.md 格式（只有 orchestrator 写）

```markdown
## [任务ID] - [时间]
- status: IN_PROGRESS | DONE | RETRY | BLOCKED
- summary: [本次动作]
- validation: [通过 / 失败 / N/A]
- next: [下一步]
```

用途：
- 方便 `tail PROGRESS.md` 巡检
- 但不作为状态真相源

---

## 调度规则

1. orchestrator 读取 `DEMAND.md`；若需求复杂或歧义明显，先产 `design.md` / `clarified-demand.md`
2. orchestrator 读取 `tasks.json`
3. 若 `active_task_id` 非空，则不再派发新任务
4. 找到第一个 `PENDING` 任务，设为 `IN_PROGRESS`
5. 派发 `coder`
6. `coder` 完成后，若通过验证则交给 `qa`
7. `qa` 根据结果写回：
   - `DONE`
   - `RETRY`（并增加 `retry_count`）
   - `BLOCKED`
8. orchestrator 在最终收口前执行轻量 closeout：同步版本号、更新交付摘要、补齐验证证据
9. orchestrator 记录 `PROGRESS.md`
10. 若为 `RETRY`，重置为 `PENDING` 后进入下一轮
11. 若全部 `DONE`，通知用户

---

## Coder bugfix 纪律（新增）

当 `task_type = bugfix` 时，coder 必须按以下顺序执行，并把结果写回 `tasks.json` 的 `notes` 或专门字段：

1. `reproduce`：写清稳定复现方式
2. `root_cause`：写清根因落点（文件 / 逻辑 / 条件）
3. `minimal_fix`：只做最小必要改动
4. `regression_verify`：列出修复后重新验证的命令或场景

规则：
- 没有 `root_cause` 说明，不应直接交 QA
- 不允许只做表面绕过而没有根因解释
- 仍然必须保留 `affected_files / verification_summary / verification_artifacts`

---

## QA 输出模板（新增）

QA 应尽量结构化写回，最少包含：

```json
{
  "result": "PASS | FAIL",
  "issue_level": "critical | major | minor",
  "findings": ["..."],
  "mapped_acceptance_criteria": {
    "AC-1": "PASS",
    "AC-2": "FAIL"
  },
  "evidence": ["..."],
  "next_action": "return_to_coder | request_user_input | done"
}
```

规则：
- `PASS` 才允许 orchestrator 最终收口为 `DONE`
- `FAIL` 时必须明确是哪条 `acceptance_criteria` 未满足
- `BLOCKED` 时必须补 `blocker_type` 和解封条件

---

## Closeout（新增）

QA PASS 后、任务最终收口前，orchestrator 追加一个轻量 closeout 动作，但不新增状态：

1. 同步版本号
2. 更新变更摘要（可写 `delivery-note.md`）
3. 收口 `affected_files / verification_summary / verification_artifacts`
4. 清理 `active_task_id` 并写 `PROGRESS.md`

规则：
- closeout 是 DONE 前的固定动作，不引入 `CLOSING` 等新状态
- 若项目有明确版本文件，必须同步更新，满足“每次修改后都能辨认版本差异”

---

## 自动化范围（瘦身）

保留：
- 一个 orchestrator
- 一个 coder
- 一个 qa
- 一个 cron 定时唤醒 orchestrator
- 一个最小阻塞通知

删除/冻结：
- 独立 PM Agent
- 并发 coder
- 7 层触发器
- 晨间站会
- 夜间回归自动写任务
- 工作区同步
- 愿景核准
- 记忆修剪自动化
- 多项目自动巡检

---

## 什么时候可以升级回完整版

只有满足以下条件时，才考虑恢复更复杂能力：
- 串行闭环长期稳定
- 状态机定义无冲突
- `tasks.json` 原子写已验证稳定
- `BLOCKED` / `RETRY` 流程已验证可靠
- 至少连续多次真实项目运行无重复派发/无状态损坏

在此之前，不要恢复并发、多项目、外围治理自动化。

---

## 主对话触发规则（新增）

当用户在 OpenClaw 主对话里说“启动 ASDS Lite / 新建 ASDS 项目 / 用 ASDS 做这个需求 / 这条消息本身就是需求”时：

1. 不要先做多项目巡检
2. 不要回复“ASDS Lite 触发器已就绪，等待需求输入”
3. 直接把用户原话落到 canonical workspace：`~/.openclaw/workspace`
4. 如需 fresh intake，调用：`python3 ~/.openclaw/workspace/scripts/asds-dialogue-intake.py fresh --message "<用户原话>" --run`
5. 如属继续当前项目，调用：`python3 ~/.openclaw/workspace/scripts/asds-dialogue-intake.py resume --message "<用户原话>" --run`
6. 只允许读写 canonical workspace 下的 `DEMAND.md` / `tasks.json` / `PROGRESS.md`
7. 禁止把任务写到任何旧路径，例如 `~/asds-workspace/projects/*`
8. 禁止为了“补闭环”再临时创建第二套项目目录或第二份 `tasks.json`

这条规则优先级高于历史巡检习惯。ASDS Lite 的默认入口是 canonical workspace intake，不是多项目扫描。

## 一句话判断标准

如果一个规则不能直接提升 “PENDING → DONE/BLOCKED” 主闭环的可靠性，就先不要加。
