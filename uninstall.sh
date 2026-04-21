#!/bin/bash
# ASDS Lite 卸载脚本
set -e

INSTALL_DIR="$HOME/.openclaw"
ORCH_DIR="$INSTALL_DIR/workspace-orchestrator"
WORKSPACE_DIR="$INSTALL_DIR/workspace"
SKILL_DIR="$INSTALL_DIR/workspace/skills/asds-mode"

echo "⚠️  即将卸载 ASDS Lite..."
read -p "确认删除? (y/N): " confirm
[[ "$confirm" != "y" ]] && echo "取消" && exit 0

rm -rf "$SKILL_DIR"
rm -rf "$HOME/asds-mode"
rm -f "$HOME/bin/asds"
sed -i '/PATH="\$HOME\/bin:\$PATH"/d' "$HOME/.zshrc" 2>/dev/null || true
sed -i '/asds-mode/d' "$HOME/.zshrc" 2>/dev/null || true

echo "✅ ASDS Lite 已卸载"
