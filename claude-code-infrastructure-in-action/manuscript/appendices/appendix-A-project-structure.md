# 附錄 A：完整範例專案架構

> 本附錄提供一個完整的 Claude Code 基礎設施範例專案結構

---

## A.1 專案結構總覽

```
my-project/
├── .claude/                           # Claude Code 配置根目錄
│   ├── hooks/                         # Hook 腳本
│   │   ├── post-tool-use-tracker.sh
│   │   ├── skill-activation-prompt.sh
│   │   ├── check-skills.ts
│   │   ├── skill-activation-prompt.ts
│   │   ├── rule-engine.ts
│   │   └── activity.log
│   │
│   ├── skills/                        # 技能庫
│   │   ├── foundation/                # 基礎層
│   │   │   ├── testing-best-practices/
│   │   │   ├── security-guidelines/
│   │   │   ├── error-handling/
│   │   │   └── typescript-advanced/
│   │   ├── domain/                    # 領域層
│   │   │   ├── backend-dev-guidelines/
│   │   │   ├── frontend-dev-guidelines/
│   │   │   └── api-design-patterns/
│   │   └── advanced/                  # 進階層
│   │       ├── microservices-patterns/
│   │       └── performance-tuning/
│   │
│   ├── agents/                        # Agent 定義
│   │   ├── architecture-reviewer/
│   │   │   ├── agent.json
│   │   │   ├── prompt.md
│   │   │   ├── permissions.yaml
│   │   │   └── runner.sh
│   │   ├── error-detector/
│   │   ├── error-fixer/
│   │   ├── doc-generator/
│   │   └── microservices-coordinator/
│   │
│   ├── knowledge-base/                # 知識庫
│   │   ├── errors.json
│   │   └── skill-registry.json
│   │
│   ├── dev-docs/                      # 開發文件（三檔案模式）
│   │   ├── microservices-refactor/
│   │   │   ├── refactor-plan.md
│   │   │   ├── refactor-context.md
│   │   │   └── refactor-tasks.md
│   │   └── testing-improvement/
│   │
│   ├── cache/                         # 緩存
│   │   └── skill-cache.ts
│   │
│   ├── scripts/                       # 工具腳本
│   │   ├── init-skill.sh
│   │   ├── publish-skill.sh
│   │   ├── update-skills.sh
│   │   └── benchmark.sh
│   │
│   └── config/                        # 配置
│       ├── skill-rules.json
│       ├── team-config.json
│       └── settings.json
│
├── src/                               # 應用代碼
├── tests/                             # 測試
├── docs/                              # 文件
├── package.json
├── tsconfig.json
└── README.md
```

---

## A.2 關鍵檔案範例

### settings.json

```json
{
  "claude": {
    "hooks": {
      "postToolUse": ".claude/hooks/post-tool-use-tracker.sh",
      "userPromptSubmit": ".claude/hooks/skill-activation-prompt.sh"
    },
    "skills": {
      "autoActivation": true,
      "rulesPath": ".claude/config/skill-rules.json"
    },
    "agents": {
      "enabled": true,
      "configPath": ".claude/agents"
    }
  }
}
```

### skill-rules.json

```json
{
  "version": "1.0.0",
  "skills": {
    "backend-dev-guidelines": {
      "type": "domain",
      "enforcement": "suggest",
      "priority": "high",
      "pathPatterns": [
        "src/controllers/**/*.ts",
        "src/services/**/*.ts"
      ],
      "promptTriggers": {
        "keywords": ["API", "controller", "service"],
        "intents": ["create.*controller", "implement.*service"]
      },
      "exclusions": ["**/*.test.ts", "**/*.spec.ts"]
    }
  }
}
```

### 技能結構（backend-dev-guidelines）

```
.claude/skills/domain/backend-dev-guidelines/
├── SKILL.md                    # 主文件（< 500 lines）
├── CHANGELOG.md                # 變更記錄
├── resources/                  # 資源文件
│   ├── controller-patterns.md
│   ├── service-layer.md
│   ├── data-access-layer.md
│   ├── error-handling.md
│   ├── testing.md
│   └── api-versioning.md
└── examples/                   # 範例代碼
    ├── user-controller.ts
    ├── user-service.ts
    └── user-repository.ts
```

---

## A.3 快速開始腳本

### init-project.sh

```bash
#!/bin/bash
# 初始化 Claude Code 基礎設施

set -euo pipefail

echo "🚀 Initializing Claude Code Infrastructure..."

# 1. 創建目錄結構
mkdir -p .claude/{hooks,skills/{foundation,domain,advanced},agents,knowledge-base,dev-docs,cache,scripts,config}

# 2. 複製模板文件
cp templates/settings.json .claude/config/
cp templates/skill-rules.json .claude/config/
cp templates/post-tool-use-tracker.sh .claude/hooks/
cp templates/skill-activation-prompt.sh .claude/hooks/

# 3. 設置權限
chmod +x .claude/hooks/*.sh
chmod +x .claude/scripts/*.sh

# 4. 安裝依賴
npm install --save-dev ts-node typescript @types/node

# 5. 初始化 git
if [ ! -d .git ]; then
    git init
fi

# 添加 .gitignore
cat >> .gitignore <<EOF
.claude/hooks/activity.log
.claude/cache/
node_modules/
EOF

echo "✅ Initialization complete!"
echo ""
echo "Next steps:"
echo "1. Review .claude/config/settings.json"
echo "2. Create your first skill: ./.claude/scripts/init-skill.sh"
echo "3. Test hooks: edit a file and check .claude/hooks/activity.log"
```

---

## A.4 完整範例：backend-dev-guidelines 技能

### SKILL.md（主文件，482 行）

```markdown
# 後端開發指南

**Version**: 2.1.0
**Layer**: Domain
**Maintainer**: backend-team@company.com

## 快速導航

- [控制器設計](#controller-design)
- [服務層架構](#service-layer)
- [資料存取層](#data-access-layer)
- [錯誤處理](#error-handling)
- [測試策略](#testing-strategy)

---

## 控制器設計 {#controller-design}

### 單一職責原則

每個控制器方法應該只處理一個業務操作。

**✅ 好的做法**：

\`\`\`typescript
class UserController {
  async getUser(req: Request, res: Response) {
    const user = await this.userService.findById(req.params.id);
    if (!user) throw new NotFoundError('User not found');
    res.json({ data: user });
  }
}
\`\`\`

**詳細說明**：參見 [resources/controller-patterns.md](resources/controller-patterns.md)

---

## 服務層架構 {#service-layer}

服務層負責業務邏輯，不應包含 HTTP 相關代碼。

**核心原則**：
- 依賴注入
- 單一職責
- 可測試性

**詳細說明**：參見 [resources/service-layer.md](resources/service-layer.md)

---

## 資料存取層 {#data-access-layer}

使用 Repository 模式隔離資料庫邏輯。

**詳細說明**：參見 [resources/data-access-layer.md](resources/data-access-layer.md)

---

## 錯誤處理 {#error-handling}

統一的錯誤處理中介層。

**詳細說明**：參見 [resources/error-handling.md](resources/error-handling.md)

---

## 測試策略 {#testing-strategy}

單元測試、整合測試和 E2E 測試的最佳實踐。

**詳細說明**：參見 [resources/testing.md](resources/testing.md)

---

## 快速檢查清單

開始開發前，確保：
- [ ] 了解單一職責原則
- [ ] 使用依賴注入
- [ ] 實作統一錯誤處理
- [ ] 編寫測試（覆蓋率 > 80%）

---

## 更新日誌

查看 [CHANGELOG.md](CHANGELOG.md) 了解版本更新。
```

---

## A.5 Agent 範例：error-detector

### agent.json

```json
{
  "name": "error-detector",
  "version": "1.0.0",
  "description": "檢測和分類生產環境錯誤",
  "trigger": {
    "manual": false,
    "events": ["log.error", "ci.failed"],
    "schedule": "*/5 * * * *"
  },
  "execution": {
    "model": "claude-sonnet-4-5-20250929",
    "timeout": 300,
    "max_tokens": 100000
  },
  "permissions": {
    "read": ["src/**/*", "logs/**/*"],
    "write": [".claude/error-reports/*.json"],
    "tools": ["Read", "Glob", "Grep", "Write"]
  }
}
```

---

## A.6 dev-docs 範例

### refactor-plan.md

```markdown
# 微服務重構計畫

## 目標
將單體應用拆分為 8 個微服務

## 階段

### Phase 1: 準備（Week 1-4）
- [x] 建立 Hook 系統
- [x] 創建技能庫
- [ ] 分析依賴關係

### Phase 2: 服務提取（Week 5-12）
- [ ] UserService
- [ ] OrderService
- [ ] PaymentService

## 里程碑
- 2024-07-31: 基礎設施完成
- 2024-08-31: 首批服務上線
```

---

## A.7 完整程式碼範例庫

所有範例代碼可在 GitHub 獲取：

```
https://github.com/your-org/claude-code-infrastructure-showcase
```

包含：
- 完整可運行的專案
- 所有技能的完整實作
- 所有 Agents 的完整配置
- 測試與文件

---

**附錄 A 結束**
