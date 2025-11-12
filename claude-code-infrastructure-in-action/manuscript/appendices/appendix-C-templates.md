# 附錄 C：技能與 Agent 模板庫

> 本附錄提供可直接使用的技能與 Agent 模板

---

## C.1 技能模板

### 模板 1：領域技能（Domain Skill）

**適用場景**：特定技術棧的最佳實踐（如 React、Node.js）

**結構**：
```
.claude/skills/domain/[skill-name]/
├── SKILL.md
├── CHANGELOG.md
├── resources/
│   ├── patterns.md
│   ├── anti-patterns.md
│   └── examples.md
└── examples/
    └── example.ts
```

**SKILL.md 模板**：

```markdown
# [Skill Name] Best Practices

**Version**: 1.0.0
**Layer**: Domain
**Maintainer**: team@company.com
**Tags**: [tag1], [tag2], [tag3]

## 快速導航

- [核心概念](#concepts)
- [最佳實踐](#best-practices)
- [常見陷阱](#pitfalls)
- [範例](#examples)

---

## 核心概念 {#concepts}

簡要說明核心概念（3-5 段）

---

## 最佳實踐 {#best-practices}

### 原則 1：[原則名稱]

**✅ 好的做法**：
\`\`\`language
// Code example
\`\`\`

**❌ 避免**：
\`\`\`language
// Anti-pattern example
\`\`\`

**詳細說明**：[resources/patterns.md](resources/patterns.md)

---

## 常見陷阱 {#pitfalls}

列舉常見錯誤及解決方法

---

## 範例 {#examples}

完整的使用範例

**詳細範例**：[resources/examples.md](resources/examples.md)

---

## 檢查清單

- [ ] 理解核心概念
- [ ] 應用最佳實踐
- [ ] 避免常見陷阱
- [ ] 參考範例

---

## 更新日誌

查看 [CHANGELOG.md](CHANGELOG.md)
```

---

### 模板 2：基礎技能（Foundation Skill）

**適用場景**：跨技術棧的通用實踐（如測試、安全）

**SKILL.md 模板**：

```markdown
# [Foundation Skill Name]

**Version**: 1.0.0
**Layer**: Foundation
**Applicable**: All projects
**Priority**: High

## 為何重要

說明此技能的重要性

---

## 核心原則

### 原則 1
### 原則 2
### 原則 3

---

## 實踐指南

### 語言特定實踐

#### TypeScript
\`\`\`typescript
// Example
\`\`\`

#### Python
\`\`\`python
# Example
\`\`\`

---

## 工具與資源

- 工具 1：說明
- 工具 2：說明

---

## 檢查清單

- [ ] 項目 1
- [ ] 項目 2
```

---

## C.2 Agent 模板

### 模板 1：分析型 Agent

**適用場景**：掃描代碼、生成報告（如架構審查、安全掃描）

**agent.json**：

```json
{
  "name": "[agent-name]",
  "version": "1.0.0",
  "description": "[描述]",

  "trigger": {
    "manual": true,
    "schedule": "0 9 * * 1"  // 每週一早上 9 點
  },

  "execution": {
    "model": "claude-sonnet-4-5-20250929",
    "timeout": 600,
    "max_tokens": 150000,
    "temperature": 0.0
  },

  "permissions": {
    "read": ["src/**/*", "tests/**/*"],
    "write": [".claude/reports/*.md"],
    "tools": ["Read", "Glob", "Grep", "Write"],
    "bash": { "allowed": false }
  },

  "output": {
    "format": "markdown",
    "path": ".claude/reports/[report-name]-{{TIMESTAMP}}.md"
  }
}
```

**prompt.md 模板**：

```markdown
# [Agent Name]

你是 [角色描述] 專家。

## 任務

[詳細任務描述]

---

## 執行步驟

### Step 1: 掃描
使用 Glob 掃描目標文件...

### Step 2: 分析
分析每個文件，提取...

### Step 3: 生成報告
按照以下格式生成報告：

\`\`\`markdown
# [Report Title]

## Summary
- Total files: X
- Issues found: Y

## Critical Issues
### 1. [Issue Title]
...
\`\`\`

---

## 輸出

寫入：`.claude/reports/[report-name]-{{TIMESTAMP}}.md`
```

---

### 模板 2：修復型 Agent

**適用場景**：自動修復問題（如錯誤修復、格式化）

**agent.json**：

```json
{
  "name": "[fixer-agent-name]",
  "trigger": {
    "manual": false,
    "events": ["[trigger-event]"]
  },

  "execution": {
    "timeout": 600,
    "max_tokens": 150000
  },

  "permissions": {
    "read": ["src/**/*"],
    "write": ["src/**/*"],  // 允許修改源碼
    "tools": ["Read", "Edit", "Write", "Bash"],
    "bash": {
      "allowed": true,
      "whitelist": [
        "npm test",
        "npm run lint",
        "git diff",
        "git add",
        "git commit"
      ]
    }
  },

  "testing": {
    "required": true,
    "commands": ["npm test", "npm run lint"],
    "rollback_on_failure": true
  },

  "pr_creation": {
    "enabled": true,
    "require_approval": true
  }
}
```

**prompt.md 核心邏輯**：

```markdown
## 執行步驟

### Step 1: 載入問題
從輸入讀取問題報告...

### Step 2: 選擇修復策略
根據問題類型選擇策略...

### Step 3: 應用修復
使用 Edit 工具修改文件...

### Step 4: 測試
\`\`\`bash
npm test
npm run lint
\`\`\`

### Step 5: 創建 PR（如果測試通過）
\`\`\`bash
git add .
git commit -m "fix: [description]"
gh pr create --title "[title]" --body "[body]"
\`\`\`

---

## 約束條件

**必須遵守**：
1. ✅ 修復後必須通過測試
2. ✅ 測試失敗必須回滾
3. ✅ 只修復報告中的問題

**禁止**：
1. ❌ 不要跳過測試
2. ❌ 不要直接 push 到 main
```

---

### 模板 3：生成型 Agent

**適用場景**：生成文件、代碼（如文件生成、測試生成）

**agent.json**：

```json
{
  "name": "[generator-agent-name]",
  "trigger": {
    "events": ["[missing-detected]"]
  },

  "generation_templates": {
    "template_type_1": "templates/template1.md",
    "template_type_2": "templates/template2.md"
  },

  "output_formats": ["markdown", "json", "html"],

  "permissions": {
    "read": ["src/**/*", "templates/**/*"],
    "write": ["docs/**/*", "tests/**/*"],
    "tools": ["Read", "Glob", "Grep", "Write"]
  }
}
```

---

## C.3 配置模板

### skill-rules.json 模板

```json
{
  "version": "1.0.0",
  "lastUpdated": "{{DATE}}",

  "skills": {
    "[skill-name]": {
      "type": "domain|foundation|advanced",
      "enforcement": "suggest|require",
      "priority": "critical|high|medium|low",

      "pathPatterns": [
        "src/[path]/**/*.ts"
      ],

      "promptTriggers": {
        "keywords": ["keyword1", "keyword2"],
        "intents": ["create.*[pattern]", "implement.*[pattern]"]
      },

      "exclusions": [
        "**/*.test.ts",
        "**/*.spec.ts"
      ],

      "dependencies": []
    }
  }
}
```

---

### team-config.json 模板

```json
{
  "team": "[team-name]",

  "subscriptions": {
    "[skill-name]": {
      "version": "^1.0.0",
      "auto_update": true,
      "notify_on_update": true
    }
  },

  "agent_config": {
    "auto_run": ["[agent-name]"],
    "schedule": {
      "[agent-name]": "0 9 * * 1"
    }
  },

  "cost_budget": {
    "monthly_limit": 1000,
    "alert_threshold": 0.8
  }
}
```

---

## C.4 腳本模板

### init-skill.sh

```bash
#!/bin/bash
# 創建新技能

SKILL_NAME=$1
SKILL_LAYER=$2  # foundation|domain|advanced

if [ -z "$SKILL_NAME" ] || [ -z "$SKILL_LAYER" ]; then
    echo "Usage: ./init-skill.sh <skill-name> <layer>"
    exit 1
fi

SKILL_DIR=".claude/skills/$SKILL_LAYER/$SKILL_NAME"

mkdir -p "$SKILL_DIR"/{resources,examples}

# 複製模板
cp templates/SKILL.md "$SKILL_DIR/"
cp templates/CHANGELOG.md "$SKILL_DIR/"

# 替換佔位符
sed -i "s/{{SKILL_NAME}}/$SKILL_NAME/g" "$SKILL_DIR/SKILL.md"

echo "✅ Skill created: $SKILL_DIR"
echo "Next: Edit $SKILL_DIR/SKILL.md"
```

---

### publish-skill.sh

```bash
#!/bin/bash
# 發布技能新版本

SKILL_NAME=$1
VERSION=$2

if [ -z "$SKILL_NAME" ] || [ -z "$VERSION" ]; then
    echo "Usage: ./publish-skill.sh <skill-name> <version>"
    exit 1
fi

# 1. 驗證版本格式
if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Error: Invalid version format (use semver: X.Y.Z)"
    exit 1
fi

# 2. 更新 skill-registry.json
jq ".skills[\"$SKILL_NAME\"].version = \"$VERSION\" | \
    .skills[\"$SKILL_NAME\"].last_updated = \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"" \
    .claude/knowledge-base/skill-registry.json > tmp.json
mv tmp.json .claude/knowledge-base/skill-registry.json

# 3. 創建 Git tag
git add .
git commit -m "release: $SKILL_NAME v$VERSION"
git tag "$SKILL_NAME-v$VERSION"
git push --tags

echo "✅ Published: $SKILL_NAME v$VERSION"
```

---

## C.5 使用範例

### 創建新技能

```bash
# 1. 使用模板創建
./claude/scripts/init-skill.sh react-hooks-guide domain

# 2. 編輯內容
vim .claude/skills/domain/react-hooks-guide/SKILL.md

# 3. 添加到規則
vim .claude/config/skill-rules.json

# 4. 測試
# 編輯匹配路徑的文件，檢查技能是否激活
```

---

### 創建新 Agent

```bash
# 1. 複製模板
cp -r templates/agent-template .claude/agents/my-agent

# 2. 編輯配置
vim .claude/agents/my-agent/agent.json
vim .claude/agents/my-agent/prompt.md

# 3. 測試
./.claude/agents/my-agent/runner.sh
```

---

## C.6 模板庫資源

完整模板庫：
```
https://github.com/your-org/claude-code-templates
```

包含：
- 20+ 技能模板
- 10+ Agent 模板
- 完整的腳本庫
- 詳細使用說明

---

**附錄 C 結束**

---

**全書完**
