#!/bin/bash
# User Prompt Submit Hook - 分析使用者提示
# 當使用者提交提示時觸發，根據提示內容建議相關技能

set -euo pipefail  # 嚴格模式

# 取得腳本目錄
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 將 stdin 傳遞給 TypeScript 腳本
cat | node -r ts-node/register "$SCRIPT_DIR/skill-activation-prompt.ts"

exit 0
