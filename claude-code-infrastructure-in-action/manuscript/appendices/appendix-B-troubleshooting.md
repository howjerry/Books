# 附錄 B：故障排除指南

> 本附錄整理常見問題與解決方法

---

## B.1 Hook 系統問題

### 問題 1：Hook 未執行

**症狀**：
- 編輯文件後無反應
- activity.log 無新記錄

**診斷**：
```bash
# 檢查 Hook 腳本是否存在
ls -la .claude/hooks/post-tool-use-tracker.sh

# 檢查權限
ls -l .claude/hooks/*.sh
# 應顯示 -rwxr-xr-x（可執行）

# 檢查 settings.json
cat .claude/config/settings.json | jq '.claude.hooks'
```

**解決方法**：
```bash
# 賦予執行權限
chmod +x .claude/hooks/*.sh

# 重啟 Claude Code（如果使用 IDE 集成）
```

---

### 問題 2：Hook 執行錯誤

**症狀**：
```
[ERROR] Hook execution failed: /bin/bash: line 5: jq: command not found
```

**解決方法**：
```bash
# 安裝依賴
## macOS
brew install jq

## Ubuntu/Debian
sudo apt-get install jq

## Windows (WSL)
sudo apt-get install jq
```

---

## B.2 技能系統問題

### 問題 3：技能未激活

**症狀**：
- 編輯匹配路徑的文件，但技能未推薦

**診斷**：
```bash
# 檢查規則配置
cat .claude/config/skill-rules.json | jq '.skills["backend-dev-guidelines"]'

# 手動測試規則引擎
node -r ts-node/register .claude/hooks/check-skills.ts "src/controllers/UserController.ts"
```

**常見原因**：
1. **路徑模式錯誤**：`src/controllers/*.ts` vs `src/controllers/**/*.ts`
2. **排除規則匹配**：文件被 exclusions 排除
3. **技能不存在**：skill-rules.json 引用了不存在的技能

**解決方法**：
```json
// 修正路徑模式（使用 ** 匹配子目錄）
{
  "pathPatterns": [
    "src/controllers/**/*.ts",  // ✅ 正確
    "src/services/**/*.ts"
  ]
}
```

---

### 問題 4：技能載入過慢

**症狀**：
- 技能激活需要 10+ 秒

**診斷**：
```bash
# 檢查技能大小
find .claude/skills -name "SKILL.md" -exec wc -l {} +

# 識別過大的技能（> 1000 行）
```

**解決方法**：
1. **模組化大型技能**：拆分資源文件
2. **啟用緩存**：實作 skill-cache.ts
3. **延遲載入**：只載入主文件

---

## B.3 Agent 系統問題

### 問題 5：Agent 執行超時

**症狀**：
```
[ERROR] Agent execution timeout after 600s
```

**解決方法**：
```json
// agent.json
{
  "execution": {
    "timeout": 1200,  // 增加到 20 分鐘
    "max_tokens": 200000
  }
}
```

---

### 問題 6：Agent 權限拒絕

**症狀**：
```
[ERROR] Permission denied: Cannot write to src/controllers/UserController.ts
```

**診斷**：
```bash
# 檢查權限配置
cat .claude/agents/error-fixer/permissions.yaml
```

**解決方法**：
```yaml
# permissions.yaml
write:
  - pattern: "src/**/*.ts"
    allowed: true
    reason: "Allow fixing source files"
```

---

## B.4 效能問題

### 問題 7：API 成本過高

**症狀**：
- 月度成本超過預算
- token 使用量異常高

**診斷**：
```bash
# 生成成本報告
./.claude/scripts/cost-report.sh

# 查看 token 使用分布
```

**解決方法**：
1. **技能模組化**（-75% 成本）
2. **啟用緩存**（-32% 重複載入）
3. **延遲載入資源文件**（-64% 上下文）
4. **設定 Agent 預算**

參見：第 11 章 效能優化與成本控制

---

## B.5 文件同步問題

### 問題 8：文件未自動更新

**症狀**：
- 代碼變更後文件未同步
- doc-detector 未觸發

**診斷**：
```bash
# 檢查 doc-detector 配置
cat .claude/agents/doc-detector/agent.json | jq '.trigger'

# 手動運行檢測
./.claude/agents/doc-detector/runner.sh
```

**解決方法**：
```json
// 確保觸發事件正確配置
{
  "trigger": {
    "events": ["code.changed", "pr.created"],
    "schedule": "0 9 * * *"  // 每天早上 9 點
  }
}
```

---

## B.6 多團隊協作問題

### 問題 9：技能版本衝突

**症狀**：
```
[ERROR] Skill version conflict: team A uses v1.5.0, team B uses v2.0.0
```

**解決方法**：
1. **使用版本範圍**：
```json
{
  "subscriptions": {
    "testing-best-practices": {
      "version": "^2.0.0",  // 自動更新到最新 2.x
      "auto_update": true
    }
  }
}
```

2. **設定遷移期**：
```markdown
## Deprecation Notice

v1.x will be EOL on 2025-06-01.
Please migrate to v2.x before then.
```

---

## B.7 常見錯誤訊息解讀

### 錯誤 1
```
Error: ENOENT: no such file or directory, open '.claude/config/skill-rules.json'
```
**原因**：技能規則文件不存在
**解決**：`cp templates/skill-rules.json .claude/config/`

### 錯誤 2
```
TypeError: Cannot read property 'pathPatterns' of undefined
```
**原因**：skill-rules.json 格式錯誤
**解決**：使用 `jq` 驗證 JSON 格式

### 錯誤 3
```
Agent execution failed: Budget exceeded (205000/200000 tokens)
```
**原因**：上下文超出預算
**解決**：減少 Agent 讀取的文件數量，或增加預算

---

## B.8 診斷工具

### 健康檢查腳本

```bash
#!/bin/bash
# .claude/scripts/health-check.sh

echo "🏥 Claude Code Infrastructure Health Check"
echo ""

# 檢查 Hook
echo "1. Checking Hooks..."
if [ -x .claude/hooks/post-tool-use-tracker.sh ]; then
    echo "   ✅ post-tool-use-tracker.sh"
else
    echo "   ❌ post-tool-use-tracker.sh (not executable)"
fi

# 檢查技能
echo "2. Checking Skills..."
SKILL_COUNT=$(find .claude/skills -name "SKILL.md" | wc -l)
echo "   Found $SKILL_COUNT skills"

# 檢查 Agents
echo "3. Checking Agents..."
AGENT_COUNT=$(find .claude/agents -name "agent.json" | wc -l)
echo "   Found $AGENT_COUNT agents"

# 檢查配置
echo "4. Checking Configuration..."
if [ -f .claude/config/settings.json ]; then
    echo "   ✅ settings.json"
else
    echo "   ❌ settings.json (missing)"
fi

echo ""
echo "Health check complete!"
```

---

## B.9 社群支援

### 獲取幫助

1. **GitHub Issues**: https://github.com/your-org/claude-code-infrastructure-showcase/issues
2. **Discord**: claude-code-community
3. **Stack Overflow**: 標籤 `claude-code`

### 報告 Bug

提供以下資訊：
- Claude Code 版本
- 作業系統與版本
- 錯誤訊息（完整日誌）
- 重現步驟
- 相關配置文件

---

**附錄 B 結束**
