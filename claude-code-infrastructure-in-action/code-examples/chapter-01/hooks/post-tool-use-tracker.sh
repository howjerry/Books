#!/bin/bash
# Post Tool Use Hook - 監聽檔案編輯事件
# 當 Claude 使用 Edit、Write 或 MultiEdit 工具時觸發

set -euo pipefail  # 嚴格模式

# 從 stdin 讀取 JSON 資料
INPUT=$(cat)

# 提取工具名稱和檔案路徑
TOOL=$(echo "$INPUT" | jq -r '.tool')
FILE_PATH=$(echo "$INPUT" | jq -r '.args.file_path // empty')

# 只處理檔案編輯相關的工具
if [[ "$TOOL" == "Edit" || "$TOOL" == "Write" || "$TOOL" == "MultiEdit" ]]; then
    if [[ -n "$FILE_PATH" ]]; then
        # 記錄到活動日誌
        LOG_DIR="$(dirname "$0")"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Tool: $TOOL, File: $FILE_PATH" >> "$LOG_DIR/activity.log"

        # 調用 TypeScript 規則引擎檢查技能
        SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
        cd "$SCRIPT_DIR"

        # 執行技能匹配
        MATCHED_SKILLS=$(node -r ts-node/register "$SCRIPT_DIR/check-skills.ts" "$FILE_PATH" 2>/dev/null || echo "")

        # 如果有匹配的技能，顯示建議
        if [[ -n "$MATCHED_SKILLS" ]]; then
            echo "📝 檔案已編輯: $(basename "$FILE_PATH")"
            echo ""
            echo "$MATCHED_SKILLS"
        fi
    fi
fi

exit 0
