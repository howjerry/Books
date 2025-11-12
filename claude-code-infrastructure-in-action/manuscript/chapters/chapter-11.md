# 第 11 章：效能優化與成本控制

> **本章內容**
> - 上下文使用優化
> - 智能緩存策略
> - API 成本分析與控制
> - 效能基準測試

---

## 11.1 成本分析：你的 AI 花費在哪裡？

### 典型專案的成本結構

```
📊 月度 API 成本分析（中型團隊，8 人）

總成本：$2,340/月

成本分解：
├── 技能載入：$980 (41.9%)
│   └── 問題：重複載入相同技能
├── Agent 執行：$720 (30.8%)
│   └── 問題：上下文過大
├── 對話補全：$480 (20.5%)
│   └── 問題：無效率的提示
└── 其他：$160 (6.8%)
```

**優化潛力**：60-70% 成本可被優化

---

## 11.2 上下文優化策略

### 策略 1：技能模組化（已實施）

**Before**：

```
技能文件：2,500 行
每次載入：50,000 tokens
月度成本：$980
```

**After**：

```
主文件：500 行
資源文件：按需載入
每次載入：12,000 tokens
月度成本：$240

節省：-75.5%
```

---

### 策略 2：智能緩存

**實作緩存層**：

```typescript
// .claude/cache/skill-cache.ts
class SkillCache {
  private cache = new Map<string, CachedSkill>();
  private TTL = 3600 * 1000; // 1 hour

  get(skillName: string): string | null {
    const cached = this.cache.get(skillName);

    if (!cached) return null;

    // 檢查過期
    if (Date.now() - cached.timestamp > this.TTL) {
      this.cache.delete(skillName);
      return null;
    }

    return cached.content;
  }

  set(skillName: string, content: string): void {
    this.cache.set(skillName, {
      content,
      timestamp: Date.now()
    });
  }
}
```

**效果**：
- 緩存命中率：0% → 78%
- 重複載入減少：78%
- 成本節省：-32%

---

### 策略 3：延遲載入

```typescript
// 只載入主文件，資源文件按需
const skill = {
  mainContent: readFile('SKILL.md'),  // 立即載入
  resources: {
    'controller-patterns': () => readFile('resources/controller-patterns.md'),  // 延遲
    'service-layer': () => readFile('resources/service-layer.md')
  }
};

// 用戶明確要求時才載入
if (userRequest.includes('controller patterns')) {
  const resource = skill.resources['controller-patterns']();
}
```

**效果**：
- 平均上下文使用：50K → 18K tokens
- 成本節省：-64%

---

## 11.3 Agent 成本控制

### 設定上下文預算

```json
{
  "agent": "microservices-coordinator",
  "execution": {
    "max_tokens": 150000,  // 硬性限制
    "budget_allocation": {
      "coordinator": 40000,  // 27%
      "subagents": {
        "analysis": 60000,   // 40%
        "extraction": 30000, // 20%
        "testing": 15000,    // 10%
        "documentation": 5000 // 3%
      }
    }
  }
}
```

**超出預算處理**：

```typescript
if (tokensUsed > budget) {
  // 1. 警告
  console.warn(`⚠️  Approaching budget limit: ${tokensUsed}/${budget}`);

  // 2. 自動縮減（刪除非必要內容）
  context = trimContext(context, budget);

  // 3. 終止（如果無法縮減）
  if (tokensUsed > budget * 1.1) {
    throw new BudgetExceededError();
  }
}
```

---

## 11.4 效能基準測試

### 建立基準

```bash
# 運行基準測試
./.claude/scripts/benchmark.sh

# 結果
╔════════════════════════════════════════════════════╗
║            Performance Benchmarks                  ║
╚════════════════════════════════════════════════════╝

Skill Loading:
├── testing-best-practices: 2.3s (12K tokens)
├── backend-dev-guidelines: 3.1s (18K tokens)
└── react-best-practices: 2.8s (15K tokens)

Agent Execution:
├── architecture-reviewer: 3m 42s (85K tokens)
├── error-detector: 42s (22K tokens)
└── doc-generator: 8m 15s (142K tokens)

API Cost (per execution):
├── Skill activation: $0.012
├── Agent execution: $0.85 (avg)
└── Multi-agent system: $3.20
```

---

## 11.5 成本優化成果

### 優化前後對比

| 項目 | 優化前 | 優化後 | 節省 |
|------|--------|--------|------|
| **月度總成本** | $2,340 | $890 | -62% |
| **技能載入** | $980 | $240 | -75.5% |
| **Agent 執行** | $720 | $450 | -37.5% |
| **對話補全** | $480 | $180 | -62.5% |
| **年度節省** | - | - | **$17,400** |

---

## 11.6 章節總結

### 優化清單

- [x] 技能模組化（-75.5% 成本）
- [x] 智能緩存（-32% 重複載入）
- [x] 延遲載入（-64% 上下文使用）
- [x] Agent 預算管理（-37.5% Agent 成本）
- [x] 效能基準測試（持續監控）

### 最佳實踐

1. **持續監控**：每週檢視成本報告
2. **設定預算**：為每個 Agent 設定上下文預算
3. **緩存優先**：優先使用緩存
4. **按需載入**：資源文件延遲載入

---

## 11.7 下一章預告

**第 12 章：技能生命週期管理**

成本優化後，新問題：**技能如何持續演進？**

下一章將探討：
- 技能廢棄策略
- 版本遷移路徑
- 技能合併與拆分
- 持續改進機制
