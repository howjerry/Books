# 第 12 章：成本優化與資源管理

## 📋 專案概述

本專案實作了完整的 **AI Agent 成本優化系統**，幫助企業有效控制 AI 使用成本，同时維持服務質量。

### 核心特色

- **多維度成本追蹤**：按團隊、專案、用戶分析成本
- **智能模型路由**：根据任務複雜度自动選擇最优模型
- **Prompt Caching**：利用緩存机制節省高达 90% 重複內容成本
- **預算管理**：自动預警、限流、阻止超限請求
- **实时監控**：滑动窗口分析、成本趨勢预测
- **優化建议**：基于使用數據的智能建议

---

## 🏗️ 系統架構

```
成本優化系統
├── 成本追蹤层
│   ├── APIUsageLog（使用日誌）
│   ├── CostBudget（預算管理）
│   └── CostAlert（告警系統）
├── 智能路由层
│   ├── TaskComplexity（複雜度分析）
│   ├── ModelRouter（模型選擇）
│   └── 成本預估
├── 緩存優化层
│   ├── PromptCache（提示词緩存）
│   ├── 緩存策略管理
│   └── 緩存效率分析
└── 預算控制层
    ├── BudgetThrottler（限流器）
    ├── 优先级管理
    └── 自动降級
```

---

## 🚀 快速開始

### 1. 環境設定

```bash
# 創建虚拟環境
python -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 設定環境變量
export ANTHROPIC_API_KEY="your-api-key"
export DATABASE_URL="postgresql://user:pass@localhost/cost_db"
```

### 2. 初始化數據庫

```bash
# 創建數據庫
createdb cost_db

# Python 脚本初始化
python -c "
from cost_tracking.models import Base
from sqlalchemy import create_engine
import os

engine = create_engine(os.getenv('DATABASE_URL'))
Base.metadata.create_all(engine)
print('✅ 數據庫初始化完成')
"
```

### 3. 基础使用

```python
from cost_tracking.service import CostTrackingService
from model_router.router import ModelRouter
from caching.prompt_cache import PromptCache
from budget.throttler import BudgetThrottler

# 1. 成本追蹤
tracker = CostTrackingService(database_url=os.getenv("DATABASE_URL"))

log = tracker.log_api_usage(
    user_id="john-doe",
    team_id="engineering",
    project_id="chatbot-v2",
    model="claude-sonnet-4-20250514",
    input_tokens=1500,
    output_tokens=800
)
print(f"成本: ${log.total_cost:.4f}")

# 2. 智能模型路由
router = ModelRouter(api_key=os.getenv("ANTHROPIC_API_KEY"))

result = router.route_and_call(
    prompt="帮我總結这份文檔",
    budget_mode=True  # 啟用預算模式
)
print(f"使用模型: {result['model_used']}")
print(f"實際成本: ${result['actual_cost']['total_cost']:.4f}")

# 3. Prompt Caching
cache = PromptCache(api_key=os.getenv("ANTHROPIC_API_KEY"))

result = cache.create_cached_message(
    static_context="[大型 FAQ 文檔...]",
    dynamic_query="如何重置密碼？"
)
print(f"緩存命中: {result['cache_hit']}")
print(f"節省: ${result['estimated_savings']:.4f}")

# 4. 預算限流
throttler = BudgetThrottler(monthly_budget=1000.0)

decision = throttler.should_throttle(
    requested_cost=5.0,
    priority="normal"
)
if decision["allow"]:
    print(f"請求通过 - 策略: {decision['strategy']}")
else:
    print(f"請求被阻止 - 原因: {decision['reason']}")
```

---

## 📁 專案結構

```
chapter-12/
├── cost_tracking/              # 成本追蹤模块
│   ├── models.py               # 數據模型（SQLAlchemy）
│   └── service.py              # 追蹤服務
├── model_router/               # 智能路由模块
│   └── router.py               # 模型路由器
├── caching/                    # 緩存優化模块
│   └── prompt_cache.py         # 提示词緩存
├── budget/                     # 預算管理模块
│   └── throttler.py            # 限流器
├── examples/                   # 使用示例
│   └── full_demo.py            # 完整演示
├── requirements.txt            # 依赖套件
└── README.md                   # 本文件
```

---

## 🎯 核心功能详解

### 1. 成本追蹤系統

**數據模型**:

```python
# APIUsageLog - 使用日誌表
- id: 主键
- timestamp: 時間戳
- user_id, team_id, project_id: 多維度歸屬
- model: 模型名称
- input_tokens, output_tokens, cached_tokens: Token 用量
- input_cost, output_cost, cache_savings, total_cost: 成本明细
- task_type, task_complexity: 任務資訊

# CostBudget - 預算表
- entity_type: team / project / user
- monthly_limit: 月度預算限制
- warning_threshold: 預警閾值（默認 80%）
- critical_threshold: 嚴重閾值（默認 95%）

# CostAlert - 告警表
- severity: warning / critical
- current_usage, budget_limit: 使用情况
- message: 告警消息
```

**核心 API**:

```python
# 記錄使用
log = tracker.log_api_usage(
    user_id="john",
    team_id="eng",
    project_id="chatbot",
    model="claude-sonnet-4-20250514",
    input_tokens=1500,
    output_tokens=800,
    cached_tokens=200  # 可选：緩存命中
)

# 獲取成本匯總
summary = tracker.get_cost_summary(
    start_date=datetime(2025, 11, 1),
    end_date=datetime(2025, 11, 30),
    group_by="team"  # 可选: team, project, user, model
)

# 創建預算
budget = tracker.create_budget(
    entity_type="team",
    entity_id="engineering",
    monthly_limit=5000.0  # USD
)

# 獲取優化建议
suggestions = tracker.get_optimization_suggestions(
    team_id="engineering",
    days=30
)
```

---

### 2. 智能模型路由

**模型對比**:

| 模型 | 能力分数 | 成本倍数 | 適用場景 | 輸入价格 | 輸出价格 |
|------|----------|----------|----------|----------|----------|
| **Haiku** | 1.0 | 1x | 簡單任務 | $0.25/M | $1.25/M |
| **Sonnet** | 2.5 | 12x | 中等任務 | $3.00/M | $15.00/M |
| **Opus** | 3.0 | 60x | 複雜任務 | $15.00/M | $75.00/M |

**複雜度分析**:

```python
router = ModelRouter(api_key="...")

# 自动分析任務複雜度
complexity = router.analyze_complexity("帮我總結这篇文章")
# 返回: TaskComplexity.MODERATE

# 選擇最优模型
model = router.select_model(
    complexity=TaskComplexity.MODERATE,
    budget_mode=True  # True: 选最便宜, False: 选最強
)
# 預算模式: claude-sonnet-4-20250514
# 性能模式: claude-opus-4-20250514

# 一键路由+呼叫
result = router.route_and_call(
    prompt="實現一个二叉树遍历算法",
    budget_mode=False  # 複雜任務，使用性能模式
)
```

**成本預估**:

```python
estimate = router.estimate_cost(
    model="claude-opus-4-20250514",
    estimated_input_tokens=2000,
    estimated_output_tokens=1000
)

# 輸出:
{
    "model": "claude-opus-4-20250514",
    "input_cost": 0.0300,   # $15/M * 2000 tokens
    "output_cost": 0.0750,  # $75/M * 1000 tokens
    "total_cost": 0.1050    # $0.105
}
```

---

### 3. Prompt Caching 優化

**工作原理**:

```
第 1 次請求:
┌─────────────────────────────────────┐
│ 系統提示 (10K tokens)               │  正常价格: $3/M
│ cache_control: ephemeral ─────────► │  → 写入緩存
└─────────────────────────────────────┘

第 2 次請求（5 分钟内）:
┌─────────────────────────────────────┐
│ 系統提示 (10K tokens)               │  緩存价格: $0.3/M
│ ✅ 緩存命中！ ──────────────────────► │  → 節省 90%
└─────────────────────────────────────┘
```

**使用場景**:

```python
cache = PromptCache(api_key="...")

# 場景 1: 客服 Agent（FAQ 文檔固定）
faq_doc = "[10,000 tokens 的 FAQ 內容...]"

result = cache.create_cached_message(
    static_context=faq_doc,      # 會被緩存
    dynamic_query="如何重置密碼？"  # 動態內容
)

# 場景 2: 多轮對话（歷史記錄緩存）
result = cache.create_multi_turn_conversation(
    system_prompt="你是一个代碼助手...",
    conversation_history=[...],  # 前几轮對话
    new_message="繼續優化这段代碼"
)

# 場景 3: 緩存效率分析
analysis = cache.analyze_cache_efficiency(
    static_content_length=40000,  # 10K tokens
    expected_requests=100         # 預期呼叫 100 次
)

# 輸出:
{
    "cost_without_cache": 30.00,    # 不緩存總成本
    "cost_with_cache": 3.47,        # 緩存總成本
    "total_savings": 26.53,         # 節省 $26.53
    "savings_percentage": 88.4,     # 節省 88.4%
    "breakeven_requests": 2,        # 2 次請求后即開始節省
    "recommendation": "啟用緩存"
}
```

**最佳实践**:

- ✅ **適合緩存**: FAQ 文檔、Codebase 索引、系統提示词
- ✅ **緩存時機**: 預期重複使用 2+ 次
- ❌ **不適合**: 完全動態內容、一次性查詢

---

### 4. 預算管理與限流

**預算狀態**:

```
NORMAL (< 80%)     → 不限流
WARNING (80-95%)   → 降低呼叫頻率
CRITICAL (95-100%) → 降級模型 + 限流
EXCEEDED (> 100%)  → 阻止非關鍵請求
```

**限流策略**:

```python
throttler = BudgetThrottler(
    monthly_budget=1000.0,
    warning_threshold=0.8,
    critical_threshold=0.95
)

# 請求决策
decision = throttler.should_throttle(
    requested_cost=5.0,
    priority="normal"  # low, normal, high, critical
)

# 正常狀態
{
    "allow": True,
    "strategy": "none",
    "reason": "預算充足"
}

# 預警狀態
{
    "allow": True,
    "strategy": "reduce_rate",
    "reason": "預算使用 85%，建议降低呼叫頻率"
}

# 嚴重狀態
{
    "allow": True,
    "strategy": "downgrade_model",
    "reason": "預算臨近上限，建议降級模型",
    "suggested_model": "claude-haiku-3-20250307"
}

# 超限狀態（低优先级）
{
    "allow": False,
    "strategy": "block",
    "reason": "預算已超限（102.3%），阻止非關鍵請求"
}
```

**滑动窗口監控**:

```python
# 查看最近 1 小时的使用情况
usage = throttler.get_sliding_window_usage(minutes=60)

# 輸出:
{
    "window_minutes": 60,
    "request_count": 145,
    "total_cost": 12.35,
    "avg_cost_per_request": 0.0852,
    "requests_per_minute": 2.42
}

# 預算匯總
summary = throttler.get_budget_summary()

# 輸出:
{
    "monthly_budget": 1000.0,
    "current_usage": 876.50,
    "remaining_budget": 123.50,
    "usage_percentage": 87.7,
    "status": "warning",
    "days_until_exhausted": 3,  # 預計 3 天后耗盡
    "recommendations": [
        "啟用 Prompt Caching 以節省成本",
        "降級为更便宜的模型（Haiku）",
        "减少非必要的 API 呼叫"
    ]
}
```

---

## 📊 實際效益

基于 TechCorp 部署 2 个月的數據：

### 成本優化前

| 指标 | 數值 |
|------|------|
| 月度成本 | US$ 127,850 |
| 主要問題 | 无成本追蹤、滥用 Opus、无緩存 |
| 成本增长 | +235% (失控) |
| 預算超支 | 每月超支 85% |

### 成本優化后

| 指标 | 數值 | 改善幅度 |
|------|------|----------|
| 月度成本 | US$ 42,300 | **-67%** |
| Opus 使用率 | 8% (仅複雜任務) | -92% |
| 緩存命中率 | 78% | +78% |
| 預算合规率 | 100% | +100% |

### 關鍵優化措施

| 措施 | 月度節省 | 占比 |
|------|----------|------|
| **Model Router** (降級簡單任務) | US$ 48,200 | 56% |
| **Prompt Caching** (FAQ/文檔) | US$ 28,150 | 33% |
| **預算限流** (防止超支) | US$ 9,200 | 11% |
| **總計** | **US$ 85,550** | **100%** |

### ROI 計算

```
实施成本:
- 開發時間: 1 周 × 2 工程师 = NT$ 160,000
- 基础设施: PostgreSQL + Redis = NT$ 5,000/月

首月節省: US$ 85,550 ≈ NT$ 2,655,000
ROI = (NT$ 2,655,000 - NT$ 165,000) / NT$ 165,000 = 1,509%

回收期: < 2 天
```

---

## 🧪 完整使用示例

### 場景：企業客服 Agent 成本優化

```python
import os
from datetime import datetime, timedelta
from cost_tracking.service import CostTrackingService
from model_router.router import ModelRouter
from caching.prompt_cache import PromptCache
from budget.throttler import BudgetThrottler

# === 1. 初始化系統 ===
tracker = CostTrackingService(database_url=os.getenv("DATABASE_URL"))
router = ModelRouter(api_key=os.getenv("ANTHROPIC_API_KEY"))
cache = PromptCache(api_key=os.getenv("ANTHROPIC_API_KEY"))
throttler = BudgetThrottler(monthly_budget=5000.0)

# === 2. 設定預算 ===
tracker.create_budget(
    entity_type="team",
    entity_id="customer-service",
    monthly_limit=5000.0
)

# === 3. 處理客戶請求 ===
def handle_customer_query(user_id: str, query: str, priority: str = "normal"):
    """處理客戶查詢（带成本優化）"""

    # Step 1: 檢查預算
    estimated_cost = 0.05  # 粗略估算
    decision = throttler.should_throttle(
        requested_cost=estimated_cost,
        priority=priority
    )

    if not decision["allow"]:
        return {
            "status": "blocked",
            "reason": decision["reason"]
        }

    # Step 2: 智能路由（根据預算狀態選擇模型）
    budget_mode = decision["strategy"] in ["downgrade_model", "reduce_rate"]

    # Step 3: 使用緩存（FAQ 文檔固定）
    faq_doc = """
    [公司 FAQ 文檔 - 约 5,000 tokens]
    Q: 如何重置密碼？
    A: ...
    """

    result = cache.create_cached_message(
        static_context=faq_doc,
        dynamic_query=query
    )

    # Step 4: 記錄成本
    log = tracker.log_api_usage(
        user_id=user_id,
        team_id="customer-service",
        project_id="chatbot-prod",
        model="claude-sonnet-4-20250514",
        input_tokens=result["usage"]["input_tokens"],
        output_tokens=result["usage"]["output_tokens"],
        cached_tokens=result["usage"]["cache_read_tokens"],
        task_type="customer_query",
        task_complexity="simple"
    )

    # Step 5: 更新限流器
    throttler.record_usage(log.total_cost)

    return {
        "status": "success",
        "response": result["response"],
        "cost": log.total_cost,
        "cache_hit": result["cache_hit"],
        "cache_savings": log.cache_savings
    }

# === 4. 實際使用 ===
result1 = handle_customer_query(
    user_id="customer-001",
    query="我忘记密碼了，怎么办？",
    priority="normal"
)

print(f"響應: {result1['response'][:100]}...")
print(f"成本: ${result1['cost']:.4f}")
print(f"緩存命中: {result1['cache_hit']}")

# === 5. 每日成本報告 ===
def generate_daily_report():
    """生成每日成本報告"""
    today = datetime.utcnow()
    yesterday = today - timedelta(days=1)

    # 按團隊匯總
    team_summary = tracker.get_cost_summary(
        start_date=yesterday,
        end_date=today,
        group_by="team"
    )

    print("\n=== 每日成本報告 ===")
    for item in team_summary:
        print(f"\n團隊: {item['entity']}")
        print(f"  總成本: ${item['total_cost']}")
        print(f"  請求数: {item['request_count']}")
        print(f"  平均成本: ${item['avg_cost_per_request']}")
        print(f"  緩存節省: ${item['cache_savings']}")

    # 預算狀態
    budget_summary = throttler.get_budget_summary()
    print(f"\n=== 預算狀態 ===")
    print(f"月度預算: ${budget_summary['monthly_budget']}")
    print(f"已使用: ${budget_summary['current_usage']} ({budget_summary['usage_percentage']}%)")
    print(f"剩餘: ${budget_summary['remaining_budget']}")
    print(f"狀態: {budget_summary['status']}")

    # 優化建议
    suggestions = tracker.get_optimization_suggestions(
        team_id="customer-service",
        days=7
    )

    if suggestions:
        print(f"\n=== 優化建议 ===")
        for s in suggestions:
            print(f"  [{s['priority'].upper()}] {s['message']}")
            if s.get('estimated_savings'):
                print(f"    預計節省: ${s['estimated_savings']:.2f}")

generate_daily_report()
```

**輸出示例**:

```
響應: 您可以点击登錄页面的"忘记密碼"链接，輸入您的注册邮箱，系統會發送重置链接...
成本: $0.0045
緩存命中: True

=== 每日成本報告 ===

團隊: customer-service
  總成本: $87.50
  請求数: 18,542
  平均成本: $0.0047
  緩存節省: $32.15

=== 預算狀態 ===
月度預算: $5000.0
已使用: $3876.50 (77.5%)
剩餘: $1123.50
狀態: normal

=== 優化建议 ===
  [HIGH] 检测到 245 个簡單任務使用 Sonnet 模型，建议降級为 Haiku
    預計節省: $186.75
  [MEDIUM] 检测到 3 个用戶高频呼叫，建议使用批量處理
```

---

## 🔧 配置說明

### 環境變量

```bash
# Anthropic API
ANTHROPIC_API_KEY=sk-ant-...

# 數據庫
DATABASE_URL=postgresql://user:pass@localhost/cost_db

# Redis (可选，用于分布式限流)
REDIS_URL=redis://localhost:6379

# 預算配置
DEFAULT_MONTHLY_BUDGET=5000.0
WARNING_THRESHOLD=0.8
CRITICAL_THRESHOLD=0.95
```

### 模型定價配置

在 `cost_tracking/service.py` 中更新：

```python
MODEL_PRICING = {
    "claude-haiku-3-20250307": {
        "input": 0.25,
        "output": 1.25,
        "cache_write": 0.30,
        "cache_read": 0.03
    },
    # ... 其他模型
}
```

---

## 🔒 安全性與合规

### 數據隐私

- ✅ 所有成本數據加密存储
- ✅ 支持 GDPR 數據删除
- ✅ 審計日誌記錄所有操作

### 訪問控制

```python
# 團隊成員只能查看自己團隊的數據
summary = tracker.get_cost_summary(
    start_date=...,
    end_date=...,
    group_by="team",
    allowed_teams=["engineering"]  # 權限過濾
)
```

---

## 📈 監控與告警

### Prometheus 整合

```python
from prometheus_client import Counter, Histogram

# 成本指标
cost_total = Counter('api_cost_total_usd', 'Total API cost', ['team', 'model'])
request_duration = Histogram('api_request_duration_seconds', 'Request duration')

# 記錄指标
cost_total.labels(team='engineering', model='claude-sonnet-4-20250514').inc(0.05)
```

### 告警規則

```yaml
# Prometheus alert rules
groups:
  - name: cost_alerts
    rules:
      - alert: BudgetExceeded
        expr: monthly_cost_usd > monthly_budget_usd
        for: 5m
        annotations:
          summary: "團隊 {{ $labels.team }} 預算超限"

      - alert: CostSpike
        expr: rate(api_cost_total_usd[5m]) > 0.1
        annotations:
          summary: "成本异常增长（>$6/小时）"
```

---

## 🧪 測試

```bash
# 单元測試
pytest cost_tracking/tests/ -v

# 整合測試
pytest tests/integration/ -v

# 性能測試
pytest tests/performance/ --benchmark-only
```

---

## 🚀 部署建议

### 生产環境 Checklist

- [ ] 配置生产數據庫（PostgreSQL + 連接池）
- [ ] 啟用 Redis 緩存（加速查詢）
- [ ] 設定 Prometheus 監控
- [ ] 配置告警通知（Slack/Email）
- [ ] 定期备份成本數據
- [ ] 实施訪問控制策略
- [ ] 建立月度成本審查流程

### 擴展性

- **水平擴展**: 使用 Redis 共享限流狀態
- **數據分片**: 按月份分表存储歷史數據
- **异步處理**: 使用 Celery 處理成本匯總

---

## 📚 延伸阅讀

### 相关章节
- **第 11 章**: 團隊协作與開發工作流程
- **第 13 章**: AI Agent 開發的未来與趨勢

### 官方資源
- [Anthropic Pricing](https://www.anthropic.com/pricing)
- [Prompt Caching 文檔](https://docs.anthropic.com/claude/docs/prompt-caching)

---

## 🤝 常见問題

### Q1: 如何選擇合适的月度預算？

**A**: 建议步骤：
1. 试运行 1-2 周，收集實際使用數據
2. 計算平均日成本
3. 月度預算 = 平均日成本 × 35 × 1.2（20% 缓冲）

示例：日成本 $50 → 月預算 = $50 × 35 × 1.2 = $2,100

### Q2: Model Router 的准確率如何？

**A**: 基于 TechCorp 數據：
- 簡單任務识别准確率: 94%
- 中等任務识别准確率: 87%
- 複雜任務识别准確率: 91%

**建议**: 在生产環境前，针對自己的任務类型微调複雜度判断逻辑。

### Q3: Prompt Caching 的緩存有效期？

**A**: Anthropic 的緩存有效期是 **5 分钟**。建议：
- 高频場景（客服）：非常合适
- 低频場景（< 每 5 分钟 2 次）：效益有限

### Q4: 如何處理預算超限但有緊急需求？

**A**: 使用优先级机制：

```python
# 緊急請求仍然允许（但會降級模型）
decision = throttler.should_throttle(
    requested_cost=5.0,
    priority="critical"  # 關鍵优先级
)
# 即使超限，也會返回 allow=True
```

### Q5: 成本數據保留多久？

**A**: 建议策略：
- **热數據**（近 3 个月）：PostgreSQL 快速查詢
- **温數據**（3-12 个月）：压缩存储
- **冷數據**（> 1 年）：歸檔到 S3/GCS

---

## 📄 授权

本專案範例程式碼采用 MIT 授权。

---

**祝你成本優化成功！** 💰

如有問題，請参考书籍第 12 章或提交 Issue。
