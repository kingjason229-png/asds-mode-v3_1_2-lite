#!/bin/bash
#============================================
# ASDS Lite 一键安装脚本
# 支持 macOS / Linux
# 用法: bash -c "$(curl -fsSL https://raw.githubusercontent.com/kingjason229-png/asds-mode/main/install.sh)"
# 或下载后: chmod +x install.sh && ./install.sh
#============================================

set -e

VERSION="3.1.0"
REPO="kingjason229-png/asds-mode"
INSTALL_DIR="$HOME/.openclaw"
ORCH_DIR="$INSTALL_DIR/workspace-orchestrator"
WORKSPACE_DIR="$INSTALL_DIR/workspace"
SKILL_DIR="$INSTALL_DIR/workspace/skills/asds-mode"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()    { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
error()   { echo -e "${RED}[ERROR]${NC} $1"; }
done()    { echo -e "${GREEN}[DONE]${NC} $1"; }

echo ""
echo "========================================"
echo "  ASDS Lite v${VERSION} 一键安装脚本"
echo "========================================"
echo ""

# 检测系统
OS="$(uname -s)"
if [[ "$OS" != "Darwin" && "$OS" != "Linux" ]]; then
    error "不支持的操作系统: $OS"
    exit 1
fi
info "检测到系统: $OS"

# 检查 Python 版本
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    error "未找到 python3，请先安装 Python 3.10+"
    exit 1
fi
PYTHON_VERSION=$($PYTHON_CMD --version | cut -d' ' -f2 | cut -d'.' -f1,2)
info "Python 版本: $PYTHON_VERSION"

# 检查 Git
if ! command -v git &> /dev/null; then
    error "未找到 git，请先安装 Git"
    exit 1
fi
info "Git: $(git --version | cut -d' ' -f1-3)"

# 创建目录
info "创建目录结构..."
mkdir -p "$ORCH_DIR"
mkdir -p "$WORKSPACE_DIR"
mkdir -p "$SKILL_DIR"
mkdir -p "$WORKSPACE_DIR/skills"
done "目录创建完成"

# 克隆/更新 asds-mode 仓库
info "拉取 asds-mode 源码..."
if [[ -d "$HOME/asds-mode/.git" ]]; then
    cd "$HOME/asds-mode"
    git pull origin master
else
    git clone --depth=1 https://github.com/${REPO}.git "$HOME/asds-mode"
    cd "$HOME/asds-mode"
fi
done "源码更新完成"

# 安装 orchestrator 文件
info "安装 workspace-orchestrator..."
cp -f "$HOME/asds-mode/AGENTS.md" "$ORCH_DIR/"
cp -f "$HOME/asds-mode/SOUL.md" "$ORCH_DIR/"
cp -f "$HOME/asds-mode/IDENTITY.md" "$ORCH_DIR/"
cp -f "$HOME/asds-mode/TOOLS.md" "$ORCH_DIR/"
cp -f "$HOME/asds-mode/USER.md" "$ORCH_DIR/"
cp -f "$HOME/asds-mode/HEARTBEAT.md" "$ORCH_DIR/"
cp -f "$HOME/asds-mode/scripts/orchestrator_run.py" "$ORCH_DIR/"
cp -f "$HOME/asds-mode/scripts/asds_run.py" "$ORCH_DIR/"
done "orchestrator 安装完成"

# 安装 skill 文件
info "安装 asds-mode skill..."
cp -rf "$HOME/asds-mode/"* "$SKILL_DIR/"
done "skill 安装完成"

# 初始化 workspace 必要文件
info "初始化 workspace..."
if [[ ! -f "$WORKSPACE_DIR/tasks.json" ]]; then
    cat > "$WORKSPACE_DIR/tasks.json" <<'EOF'
{
  "tasks": [],
  "active_task_id": null
}
EOF
fi
if [[ ! -f "$WORKSPACE_DIR/PROGRESS.md" ]]; then
    echo "# PROGRESS.md\n\n## Initialized $(date -u +%Y-%m-%dT%H:%MZ)\n" > "$WORKSPACE_DIR/PROGRESS.md"
fi
if [[ ! -f "$WORKSPACE_DIR/DEMAND.md" ]]; then
    echo "# DEMAND.md\n\n<!-- 等待 intake -->" > "$WORKSPACE_DIR/DEMAND.md"
fi
done "workspace 初始化完成"

# 创建 scripts 软链接（方便命令行使用）
info "创建命令行快捷方式..."
mkdir -p "$HOME/bin"
if [[ ! -f "$HOME/bin/asds" ]]; then
    cat > "$HOME/bin/asds" << 'SCRIPT'
#!/bin/bash
# ASDS Lite 命令行工具
case "$1" in
    fresh)  python3 "$HOME/.openclaw/workspace-orchestrator/orchestrator_run.py" fresh "$2" ;;
    resume) python3 "$HOME/.openclaw/workspace-orchestrator/orchestrator_run.py" resume "$2" ;;
    status) cat "$HOME/.openclaw/workspace/tasks.json" | python3 -c "import json,sys; t=json.load(sys.stdin); p=[x for x in t['tasks'] if x['status'] not in ('DONE','BLOCKED')]; print(f'待处理: {len(p)}'); [print(f'  {x[\"id\"]} {x[\"status\"]} {x.get(\"title\",\"\")[:40]}') for x in p]" ;;
    *)      echo "用法: asds fresh|resume|status" ;;
esac
SCRIPT
    chmod +x "$HOME/bin/asds"
fi
done "命令行工具安装完成"

# 添加 PATH 提示
SHELL_RC="$HOME/.zshrc"
if [[ -f "$SHELL_RC" ]]; then
    if ! grep -q 'PATH="$HOME/bin:$PATH"' "$SHELL_RC"; then
        echo 'export PATH="$HOME/bin:$PATH"' >> "$SHELL_RC"
        info "已添加 ~/bin 到 PATH（请运行: source ~/.zshrc）"
    fi
fi

echo ""
echo "========================================"
done "ASDS Lite 安装完成！"
echo ""
echo "  下一步："
echo "  1. 重启终端 或 运行: source ~/.zshrc"
echo "  2. 使用命令:"
echo "       asds fresh \"你的需求\"   # 新项目"
echo "       asds resume \"继续做xx\"  # 继续当前项目"
echo "       asds status             # 查看状态"
echo ""
echo "  或直接告诉我: '用 ASDS 做一个 xxx'"
echo "========================================"
