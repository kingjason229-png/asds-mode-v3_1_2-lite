# ASDS Lite 一键安装包

> 跨境电商 + 软件开发 全自动 AI 开发工作流

## 特性

- 🤖 **全自动**：人类只需提需求，其余全部自动推进
- 🔄 **持续集成**：按项目 `AGENTS.md` 定义验证链自动门控
- 👥 **三角色分工**：Orchestrator / Coder / QA 各司其职
- 🧭 **轻量前置澄清**：复杂/歧义需求先产 `design.md` 再拆任务
- 🩺 **Bugfix 纪律**：`bugfix` 任务强制 `reproduce → root_cause → minimal_fix → regression_verify`
- ✅ **结构化 QA**：`result / issue_level / findings / evidence / next_action`
- 📦 **轻量收口**：DONE 前补版本号、变更摘要、验证证据
- ⏰ **无人值守**：cron 驱动，凌晨也能跑
- 📦 **开箱即用**：一条命令装好整个环境

## 安装

### macOS / Linux 一键安装

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/kingjason229-png/asds-mode/main/install.sh)"
```

或手动下载后：

```bash
chmod +x install.sh
./install.sh
```

### 完成后验证

```bash
asds status
```

## 使用方法

### 方法一：对话触发（推荐）

直接告诉我：
> "用 ASDS 做一个 xxx" / "启动 ASDS 新项目 xxx" / "继续 ASDS 当前项目"

### 方法二：命令行

```bash
# 新项目
asds fresh "做一个用户登录系统"

# 继续当前项目
asds resume "继续做支付模块"

# 查看状态
asds status
```

## 系统要求

- macOS 或 Linux
- Python 3.10+
- Git
- OpenClaw（已安装 Gateway）

## 工作流架构

```
用户需求 (对话/intake)
    ↓
[PM] 拆解 tasks.json
    ↓
[Coder] 领 PENDING 任务 → lint → typecheck → test → build
    ↓
[QA] 静态验收 → PASS/FAIL
    ↓
PM 分配下一个任务 → 循环直到全部 DONE
```

## 文件结构

```
~/.openclaw/
├── workspace/              # 项目根目录（唯一事实源）
│   ├── tasks.json          # 任务状态
│   ├── PROGRESS.md         # 进度记录
│   └── skills/             # skills
│       └── asds-mode/
├── workspace-orchestrator/ # 工作流引擎
│   ├── orchestrator_run.py
│   └── AGENTS.md
```

## License

MIT
