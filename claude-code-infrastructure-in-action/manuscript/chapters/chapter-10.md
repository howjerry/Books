# 第 10 章：團隊協作中的技能共享

> **本章內容**
> - 建立組織級技能庫
> - 技能版本管理與發布
> - 跨團隊技能共享機制
> - 技能品質評估與改進

---

## 10.1 規模化挑戰：從個人到組織

### 場景：多團隊的困擾

6 個月重構成功後，其他團隊也想採用：

> **前端團隊 Lead**：「我們也想用你們的技能系統」
>
> **移動端團隊 Lead**：「可以分享你們的 Agent 配置嗎？」
>
> **測試團隊 Lead**：「我們需要類似的自動化測試 Agent」

**問題**：

- 每個團隊各自複製技能（維護困難）
- 版本不一致（修復 bug 要改 N 次）
- 無法追蹤技能使用情況
- 缺乏品質管控

---

## 10.2 組織級技能庫架構

### 技能分層設計

```
.claude/
├── skills/
│   ├── foundation/          # 基礎層（所有團隊共享）
│   │   ├── testing-best-practices/
│   │   ├── security-guidelines/
│   │   ├── error-handling/
│   │   └── typescript-advanced/
│   │
│   ├── domain/              # 領域層（特定技術棧）
│   │   ├── backend/
│   │   │   ├── nodejs-best-practices/
│   │   │   ├── api-design-patterns/
│   │   │   └── database-optimization/
│   │   ├── frontend/
│   │   │   ├── react-best-practices/
│   │   │   ├── state-management/
│   │   │   └── performance-optimization/
│   │   └── mobile/
│   │       ├── react-native-guidelines/
│   │       └── mobile-ux-patterns/
│   │
│   └── advanced/            # 進階層（特殊場景）
│       ├── microservices-patterns/
│       ├── event-driven-architecture/
│       └── performance-tuning/
│
└── skill-registry.json      # 技能註冊表
```

---

### 技能註冊表

**檔案**: `.claude/skill-registry.json`

```json
{
  "version": "1.0.0",
  "lastUpdated": "2024-12-15T10:00:00Z",

  "skills": {
    "testing-best-practices": {
      "version": "2.1.0",
      "layer": "foundation",
      "owner": "quality-team",
      "maintainers": ["alice@company.com", "bob@company.com"],
      "tags": ["testing", "jest", "unit-test", "integration-test"],
      "dependencies": [],
      "usage_count": 456,
      "rating": 4.8,
      "last_updated": "2024-12-10T08:30:00Z",

      "changelog": [
        {
          "version": "2.1.0",
          "date": "2024-12-10",
          "changes": ["Added React Testing Library examples", "Updated mock patterns"]
        },
        {
          "version": "2.0.0",
          "date": "2024-11-15",
          "changes": ["Major restructure", "Separated unit and integration guides"]
        }
      ]
    },

    "react-best-practices": {
      "version": "1.5.2",
      "layer": "domain",
      "owner": "frontend-team",
      "dependencies": ["testing-best-practices", "typescript-advanced"],
      "usage_count": 234,
      "rating": 4.6
    }
  },

  "teams": {
    "backend-team": {
      "subscribed_skills": [
        "testing-best-practices",
        "nodejs-best-practices",
        "api-design-patterns",
        "database-optimization"
      ]
    },
    "frontend-team": {
      "subscribed_skills": [
        "testing-best-practices",
        "react-best-practices",
        "state-management"
      ]
    }
  }
}
```

---

## 10.3 技能版本管理

### 語義化版本控制

```
版本格式：MAJOR.MINOR.PATCH

- MAJOR：不相容的 API 變更
- MINOR：向後相容的功能新增
- PATCH：向後相容的 bug 修復

範例：
- 1.0.0 → 1.0.1: 修正錯字、範例錯誤
- 1.0.1 → 1.1.0: 新增新的最佳實踐章節
- 1.1.0 → 2.0.0: 重構檔案結構
```

### 技能發布流程

```bash
# 1. 開發新版本
cd .claude/skills/foundation/testing-best-practices

# 2. 更新版本號
# 修改 SKILL.md 頂部的版本宣告
## Version: 2.1.0

# 3. 更新 CHANGELOG.md
## [2.1.0] - 2024-12-10
### Added
- React Testing Library examples
- Custom hook testing patterns

### Fixed
- Mock function examples

# 4. 提交 PR
git checkout -b release/testing-best-practices-v2.1.0
git add .
git commit -m "release: testing-best-practices v2.1.0"
git push

# 5. Code Review + 合併

# 6. 發布（自動更新 registry）
./scripts/publish-skill.sh testing-best-practices 2.1.0

# 7. 通知訂閱團隊
./scripts/notify-skill-update.sh testing-best-practices 2.1.0
```

---

## 10.4 跨團隊共享機制

### 技能訂閱系統

**團隊訂閱配置**：

```json
// .claude/team-config.json
{
  "team": "backend-team",
  "subscriptions": {
    "testing-best-practices": {
      "version": "^2.0.0",  // 自動更新到最新 2.x 版本
      "auto_update": true,
      "notify_on_update": true
    },
    "nodejs-best-practices": {
      "version": "1.5.2",   // 鎖定特定版本
      "auto_update": false
    }
  }
}
```

**自動更新機制**：

```bash
# 每日自動檢查更新
./.claude/scripts/update-skills.sh

# 輸出範例：
[INFO] Checking for skill updates...
[UPDATE] testing-best-practices: 2.0.5 → 2.1.0
[UPDATE] security-guidelines: 1.8.0 → 1.9.0
[INFO] nodejs-best-practices: 1.5.2 (locked)

[PROMPT] Update 2 skills? (y/n): y
[DOWNLOADING] testing-best-practices@2.1.0...
[DOWNLOADING] security-guidelines@1.9.0...
[SUCCESS] Skills updated

[NOTIFY] Sending update notification to #backend-team channel
```

---

## 10.5 技能品質評估

### 品質指標

| 指標 | 權重 | 計算方式 |
|------|------|---------|
| **使用頻率** | 25% | 過去 30 天的激活次數 |
| **用戶評分** | 30% | 開發者評分（1-5 星）|
| **文件完整性** | 20% | 是否包含所有必要章節 |
| **程式碼範例品質** | 15% | 可運行、有註解、覆蓋主要場景 |
| **更新頻率** | 10% | 最近更新時間、維護活躍度 |

### 品質評分系統

```bash
# 生成技能品質報告
./.claude/scripts/skill-quality-report.sh

# 輸出範例：
╔════════════════════════════════════════════════════╗
║           Skill Quality Report                     ║
║           Generated: 2024-12-15                    ║
╚════════════════════════════════════════════════════╝

Foundation Skills:
┌────────────────────────────┬───────┬────────┬─────────┐
│ Skill                      │ Score │ Rating │ Status  │
├────────────────────────────┼───────┼────────┼─────────┤
│ testing-best-practices     │  92   │ ⭐⭐⭐⭐⭐  │ ✅ Great │
│ security-guidelines        │  88   │ ⭐⭐⭐⭐⭐  │ ✅ Great │
│ error-handling             │  76   │ ⭐⭐⭐⭐   │ ⚠️  Good  │
│ typescript-advanced        │  65   │ ⭐⭐⭐    │ ⚠️  Fair  │
└────────────────────────────┴───────┴────────┴─────────┘

Recommendations:
- typescript-advanced: Update examples, add more use cases
- error-handling: Improve documentation structure
```

---

## 10.6 真實案例：跨團隊協作

### 案例：統一測試標準

**背景**：
- 3 個團隊（Backend, Frontend, Mobile）
- 各有自己的測試規範
- 測試品質參差不齊

**解決方案**：建立共享的 `testing-best-practices` 技能

**實施**：

1. **組建技能委員會**
   - 各團隊派出 1 名代表
   - 每兩週會議討論改進

2. **制定統一標準**
   - 統一測試結構（Arrange-Act-Assert）
   - 統一 mock 模式
   - 統一斷言風格

3. **建立範例庫**
   - 收集各團隊的最佳實踐
   - 整理成可重用的範例

4. **發布與推廣**
   - 發布 v1.0.0
   - 工作坊培訓（3 次）
   - 設置採用目標（3 個月內 80%）

**成果**：

```
📊 3 個月成果（2024-09 → 2024-12）

測試覆蓋率：
├── Backend: 78% → 85%
├── Frontend: 62% → 82%
└── Mobile: 55% → 76%

測試品質分數（1-10）：
├── Backend: 7.2 → 8.9
├── Frontend: 6.5 → 8.6
└── Mobile: 6.1 → 8.3

Code Review 效率：
└── 測試相關問題減少 68%
```

---

## 10.7 章節總結

### 關鍵要點

1. **分層架構**：Foundation → Domain → Advanced
2. **版本管理**：語義化版本 + 自動更新
3. **品質保證**：多維度評分 + 持續改進
4. **跨團隊協作**：訂閱機制 + 技能委員會

### 實施檢查清單

- [ ] 建立技能註冊表
- [ ] 設置版本管理流程
- [ ] 實作自動更新機制
- [ ] 建立品質評估體系
- [ ] 組建技能委員會
- [ ] 設置團隊訂閱
- [ ] 定期生成品質報告

---

## 10.8 下一章預告

**第 11 章：效能優化與成本控制**

技能共享後，新問題來了：**如何控制 AI API 成本？**

下一章將深入探討：
- 上下文使用優化
- 智能緩存策略
- API 成本分析與控制
- 效能基準測試

讓我們在第 11 章中探索成本優化策略！
