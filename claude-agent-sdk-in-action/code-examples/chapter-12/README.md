# 第 12 章：成本优化与资源管理

## 📋 专案概述

本专案实作了完整的 **AI Agent 成本优化系统**，帮助企业有效控制 AI 使用成本，同时维持服务质量。

### 核心特色

- **多维度成本追踪**：按团队、专案、用户分析成本
- **智能模型路由**：根据任务复杂度自动选择最优模型
- **Prompt Caching**：利用缓存机制节省高达 90% 重复内容成本
- **预算管理**：自动预警、限流、阻止超限请求
- **实时监控**：滑动窗口分析、成本趋势预测
- **优化建议**：基于使用数据的智能建议

---

## 🏗️ 系统架构

```
成本优化系统
├── 成本追踪层
│   ├── APIUsageLog（使用日志）
│   ├── CostBudget（预算管理）
│   └── CostAlert（告警系统）
├── 智能路由层
│   ├── TaskComplexity（复杂度分析）
│   ├── ModelRouter（模型选择）
│   └── 成本预估
├── 缓存优化层
│   ├── PromptCache（提示词缓存）
│   ├── 缓存策略管理
│   └── 缓存效率分析
└── 预算控制层
    ├── BudgetThrottler（限流器）
    ├── 优先级管理
    └── 自动降级
```

---

## 🚀 快速开始

### 1. 环境设定

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 设定环境变量
export ANTHROPIC_API_KEY="your-api-key"
export DATABASE_URL="postgresql://user:pass@localhost/cost_db"
```

### 2. 初始化数据库

```bash
# 创建数据库
createdb cost_db

# Python 脚本初始化
python -c "
from cost_tracking.models import Base
from sqlalchemy import create_engine
import os

engine = create_engine(os.getenv('DATABASE_URL'))
Base.metadata.create_all(engine)
print('✅ 数据库初始化完成')
"
```

### 3. 基础使用

```python
from cost_tracking.service import CostTrackingService
from model_router.router import ModelRouter
from caching.prompt_cache import PromptCache
from budget.throttler import BudgetThrottler

# 1. 成本追踪
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
    prompt="帮我总结这份文档",
    budget_mode=True  # 启用预算模式
)
print(f"使用模型: {result['model_used']}")
print(f"实际成本: ${result['actual_cost']['total_cost']:.4f}")

# 3. Prompt Caching
cache = PromptCache(api_key=os.getenv("ANTHROPIC_API_KEY"))

result = cache.create_cached_message(
    static_context="[大型 FAQ 文档...]",
    dynamic_query="如何重置密码？"
)
print(f"缓存命中: {result['cache_hit']}")
print(f"节省: ${result['estimated_savings']:.4f}")

# 4. 预算限流
throttler = BudgetThrottler(monthly_budget=1000.0)

decision = throttler.should_throttle(
    requested_cost=5.0,
    priority="normal"
)
if decision["allow"]:
    print(f"请求通过 - 策略: {decision['strategy']}")
else:
    print(f"请求被阻止 - 原因: {decision['reason']}")
```

---

## 📁 专案结构

```
chapter-12/
├── cost_tracking/              # 成本追踪模块
│   ├── models.py               # 数据模型（SQLAlchemy）
│   └── service.py              # 追踪服务
├── model_router/               # 智能路由模块
│   └── router.py               # 模型路由器
├── caching/                    # 缓存优化模块
│   └── prompt_cache.py         # 提示词缓存
├── budget/                     # 预算管理模块
│   └── throttler.py            # 限流器
├── examples/                   # 使用示例
│   └── full_demo.py            # 完整演示
├── requirements.txt            # 依赖套件
└── README.md                   # 本文件
```

---

## 🎯 核心功能详解

### 1. 成本追踪系统

**数据模型**:

```python
# APIUsageLog - 使用日志表
- id: 主键
- timestamp: 时间戳
- user_id, team_id, project_id: 多维度归属
- model: 模型名称
- input_tokens, output_tokens, cached_tokens: Token 用量
- input_cost, output_cost, cache_savings, total_cost: 成本明细
- task_type, task_complexity: 任务信息

# CostBudget - 预算表
- entity_type: team / project / user
- monthly_limit: 月度预算限制
- warning_threshold: 预警阈值（默认 80%）
- critical_threshold: 严重阈值（默认 95%）

# CostAlert - 告警表
- severity: warning / critical
- current_usage, budget_limit: 使用情况
- message: 告警消息
```

**核心 API**:

```python
# 记录使用
log = tracker.log_api_usage(
    user_id="john",
    team_id="eng",
    project_id="chatbot",
    model="claude-sonnet-4-20250514",
    input_tokens=1500,
    output_tokens=800,
    cached_tokens=200  # 可选：缓存命中
)

# 获取成本汇总
summary = tracker.get_cost_summary(
    start_date=datetime(2025, 11, 1),
    end_date=datetime(2025, 11, 30),
    group_by="team"  # 可选: team, project, user, model
)

# 创建预算
budget = tracker.create_budget(
    entity_type="team",
    entity_id="engineering",
    monthly_limit=5000.0  # USD
)

# 获取优化建议
suggestions = tracker.get_optimization_suggestions(
    team_id="engineering",
    days=30
)
```

---

### 2. 智能模型路由

**模型对比**:

| 模型 | 能力分数 | 成本倍数 | 适用场景 | 输入价格 | 输出价格 |
|------|----------|----------|----------|----------|----------|
| **Haiku** | 1.0 | 1x | 简单任务 | $0.25/M | $1.25/M |
| **Sonnet** | 2.5 | 12x | 中等任务 | $3.00/M | $15.00/M |
| **Opus** | 3.0 | 60x | 复杂任务 | $15.00/M | $75.00/M |

**复杂度分析**:

```python
router = ModelRouter(api_key="...")

# 自动分析任务复杂度
complexity = router.analyze_complexity("帮我总结这篇文章")
# 返回: TaskComplexity.MODERATE

# 选择最优模型
model = router.select_model(
    complexity=TaskComplexity.MODERATE,
    budget_mode=True  # True: 选最便宜, False: 选最强
)
# 预算模式: claude-sonnet-4-20250514
# 性能模式: claude-opus-4-20250514

# 一键路由+调用
result = router.route_and_call(
    prompt="实现一个二叉树遍历算法",
    budget_mode=False  # 复杂任务，使用性能模式
)
```

**成本预估**:

```python
estimate = router.estimate_cost(
    model="claude-opus-4-20250514",
    estimated_input_tokens=2000,
    estimated_output_tokens=1000
)

# 输出:
{
    "model": "claude-opus-4-20250514",
    "input_cost": 0.0300,   # $15/M * 2000 tokens
    "output_cost": 0.0750,  # $75/M * 1000 tokens
    "total_cost": 0.1050    # $0.105
}
```

---

### 3. Prompt Caching 优化

**工作原理**:

```
第 1 次请求:
┌─────────────────────────────────────┐
│ 系统提示 (10K tokens)               │  正常价格: $3/M
│ cache_control: ephemeral ─────────► │  → 写入缓存
└─────────────────────────────────────┘

第 2 次请求（5 分钟内）:
┌─────────────────────────────────────┐
│ 系统提示 (10K tokens)               │  缓存价格: $0.3/M
│ ✅ 缓存命中！ ──────────────────────► │  → 节省 90%
└─────────────────────────────────────┘
```

**使用场景**:

```python
cache = PromptCache(api_key="...")

# 场景 1: 客服 Agent（FAQ 文档固定）
faq_doc = "[10,000 tokens 的 FAQ 内容...]"

result = cache.create_cached_message(
    static_context=faq_doc,      # 会被缓存
    dynamic_query="如何重置密码？"  # 动态内容
)

# 场景 2: 多轮对话（历史记录缓存）
result = cache.create_multi_turn_conversation(
    system_prompt="你是一个代码助手...",
    conversation_history=[...],  # 前几轮对话
    new_message="继续优化这段代码"
)

# 场景 3: 缓存效率分析
analysis = cache.analyze_cache_efficiency(
    static_content_length=40000,  # 10K tokens
    expected_requests=100         # 预期调用 100 次
)

# 输出:
{
    "cost_without_cache": 30.00,    # 不缓存总成本
    "cost_with_cache": 3.47,        # 缓存总成本
    "total_savings": 26.53,         # 节省 $26.53
    "savings_percentage": 88.4,     # 节省 88.4%
    "breakeven_requests": 2,        # 2 次请求后即开始节省
    "recommendation": "启用缓存"
}
```

**最佳实践**:

- ✅ **适合缓存**: FAQ 文档、Codebase 索引、系统提示词
- ✅ **缓存时机**: 预期重复使用 2+ 次
- ❌ **不适合**: 完全动态内容、一次性查询

---

### 4. 预算管理与限流

**预算状态**:

```
NORMAL (< 80%)     → 不限流
WARNING (80-95%)   → 降低调用频率
CRITICAL (95-100%) → 降级模型 + 限流
EXCEEDED (> 100%)  → 阻止非关键请求
```

**限流策略**:

```python
throttler = BudgetThrottler(
    monthly_budget=1000.0,
    warning_threshold=0.8,
    critical_threshold=0.95
)

# 请求决策
decision = throttler.should_throttle(
    requested_cost=5.0,
    priority="normal"  # low, normal, high, critical
)

# 正常状态
{
    "allow": True,
    "strategy": "none",
    "reason": "预算充足"
}

# 预警状态
{
    "allow": True,
    "strategy": "reduce_rate",
    "reason": "预算使用 85%，建议降低调用频率"
}

# 严重状态
{
    "allow": True,
    "strategy": "downgrade_model",
    "reason": "预算临近上限，建议降级模型",
    "suggested_model": "claude-haiku-3-20250307"
}

# 超限状态（低优先级）
{
    "allow": False,
    "strategy": "block",
    "reason": "预算已超限（102.3%），阻止非关键请求"
}
```

**滑动窗口监控**:

```python
# 查看最近 1 小时的使用情况
usage = throttler.get_sliding_window_usage(minutes=60)

# 输出:
{
    "window_minutes": 60,
    "request_count": 145,
    "total_cost": 12.35,
    "avg_cost_per_request": 0.0852,
    "requests_per_minute": 2.42
}

# 预算汇总
summary = throttler.get_budget_summary()

# 输出:
{
    "monthly_budget": 1000.0,
    "current_usage": 876.50,
    "remaining_budget": 123.50,
    "usage_percentage": 87.7,
    "status": "warning",
    "days_until_exhausted": 3,  # 预计 3 天后耗尽
    "recommendations": [
        "启用 Prompt Caching 以节省成本",
        "降级为更便宜的模型（Haiku）",
        "减少非必要的 API 调用"
    ]
}
```

---

## 📊 实际效益

基于 TechCorp 部署 2 个月的数据：

### 成本优化前

| 指标 | 数值 |
|------|------|
| 月度成本 | US$ 127,850 |
| 主要问题 | 无成本追踪、滥用 Opus、无缓存 |
| 成本增长 | +235% (失控) |
| 预算超支 | 每月超支 85% |

### 成本优化后

| 指标 | 数值 | 改善幅度 |
|------|------|----------|
| 月度成本 | US$ 42,300 | **-67%** |
| Opus 使用率 | 8% (仅复杂任务) | -92% |
| 缓存命中率 | 78% | +78% |
| 预算合规率 | 100% | +100% |

### 关键优化措施

| 措施 | 月度节省 | 占比 |
|------|----------|------|
| **Model Router** (降级简单任务) | US$ 48,200 | 56% |
| **Prompt Caching** (FAQ/文档) | US$ 28,150 | 33% |
| **预算限流** (防止超支) | US$ 9,200 | 11% |
| **总计** | **US$ 85,550** | **100%** |

### ROI 计算

```
实施成本:
- 开发时间: 1 周 × 2 工程师 = NT$ 160,000
- 基础设施: PostgreSQL + Redis = NT$ 5,000/月

首月节省: US$ 85,550 ≈ NT$ 2,655,000
ROI = (NT$ 2,655,000 - NT$ 165,000) / NT$ 165,000 = 1,509%

回收期: < 2 天
```

---

## 🧪 完整使用示例

### 场景：企业客服 Agent 成本优化

```python
import os
from datetime import datetime, timedelta
from cost_tracking.service import CostTrackingService
from model_router.router import ModelRouter
from caching.prompt_cache import PromptCache
from budget.throttler import BudgetThrottler

# === 1. 初始化系统 ===
tracker = CostTrackingService(database_url=os.getenv("DATABASE_URL"))
router = ModelRouter(api_key=os.getenv("ANTHROPIC_API_KEY"))
cache = PromptCache(api_key=os.getenv("ANTHROPIC_API_KEY"))
throttler = BudgetThrottler(monthly_budget=5000.0)

# === 2. 设定预算 ===
tracker.create_budget(
    entity_type="team",
    entity_id="customer-service",
    monthly_limit=5000.0
)

# === 3. 处理客户请求 ===
def handle_customer_query(user_id: str, query: str, priority: str = "normal"):
    """处理客户查询（带成本优化）"""

    # Step 1: 检查预算
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

    # Step 2: 智能路由（根据预算状态选择模型）
    budget_mode = decision["strategy"] in ["downgrade_model", "reduce_rate"]

    # Step 3: 使用缓存（FAQ 文档固定）
    faq_doc = """
    [公司 FAQ 文档 - 约 5,000 tokens]
    Q: 如何重置密码？
    A: ...
    """

    result = cache.create_cached_message(
        static_context=faq_doc,
        dynamic_query=query
    )

    # Step 4: 记录成本
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

# === 4. 实际使用 ===
result1 = handle_customer_query(
    user_id="customer-001",
    query="我忘记密码了，怎么办？",
    priority="normal"
)

print(f"响应: {result1['response'][:100]}...")
print(f"成本: ${result1['cost']:.4f}")
print(f"缓存命中: {result1['cache_hit']}")

# === 5. 每日成本报告 ===
def generate_daily_report():
    """生成每日成本报告"""
    today = datetime.utcnow()
    yesterday = today - timedelta(days=1)

    # 按团队汇总
    team_summary = tracker.get_cost_summary(
        start_date=yesterday,
        end_date=today,
        group_by="team"
    )

    print("\n=== 每日成本报告 ===")
    for item in team_summary:
        print(f"\n团队: {item['entity']}")
        print(f"  总成本: ${item['total_cost']}")
        print(f"  请求数: {item['request_count']}")
        print(f"  平均成本: ${item['avg_cost_per_request']}")
        print(f"  缓存节省: ${item['cache_savings']}")

    # 预算状态
    budget_summary = throttler.get_budget_summary()
    print(f"\n=== 预算状态 ===")
    print(f"月度预算: ${budget_summary['monthly_budget']}")
    print(f"已使用: ${budget_summary['current_usage']} ({budget_summary['usage_percentage']}%)")
    print(f"剩余: ${budget_summary['remaining_budget']}")
    print(f"状态: {budget_summary['status']}")

    # 优化建议
    suggestions = tracker.get_optimization_suggestions(
        team_id="customer-service",
        days=7
    )

    if suggestions:
        print(f"\n=== 优化建议 ===")
        for s in suggestions:
            print(f"  [{s['priority'].upper()}] {s['message']}")
            if s.get('estimated_savings'):
                print(f"    预计节省: ${s['estimated_savings']:.2f}")

generate_daily_report()
```

**输出示例**:

```
响应: 您可以点击登录页面的"忘记密码"链接，输入您的注册邮箱，系统会发送重置链接...
成本: $0.0045
缓存命中: True

=== 每日成本报告 ===

团队: customer-service
  总成本: $87.50
  请求数: 18,542
  平均成本: $0.0047
  缓存节省: $32.15

=== 预算状态 ===
月度预算: $5000.0
已使用: $3876.50 (77.5%)
剩余: $1123.50
状态: normal

=== 优化建议 ===
  [HIGH] 检测到 245 个简单任务使用 Sonnet 模型，建议降级为 Haiku
    预计节省: $186.75
  [MEDIUM] 检测到 3 个用户高频调用，建议使用批量处理
```

---

## 🔧 配置说明

### 环境变量

```bash
# Anthropic API
ANTHROPIC_API_KEY=sk-ant-...

# 数据库
DATABASE_URL=postgresql://user:pass@localhost/cost_db

# Redis (可选，用于分布式限流)
REDIS_URL=redis://localhost:6379

# 预算配置
DEFAULT_MONTHLY_BUDGET=5000.0
WARNING_THRESHOLD=0.8
CRITICAL_THRESHOLD=0.95
```

### 模型定价配置

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

## 🔒 安全性与合规

### 数据隐私

- ✅ 所有成本数据加密存储
- ✅ 支持 GDPR 数据删除
- ✅ 审计日志记录所有操作

### 访问控制

```python
# 团队成员只能查看自己团队的数据
summary = tracker.get_cost_summary(
    start_date=...,
    end_date=...,
    group_by="team",
    allowed_teams=["engineering"]  # 权限过滤
)
```

---

## 📈 监控与告警

### Prometheus 集成

```python
from prometheus_client import Counter, Histogram

# 成本指标
cost_total = Counter('api_cost_total_usd', 'Total API cost', ['team', 'model'])
request_duration = Histogram('api_request_duration_seconds', 'Request duration')

# 记录指标
cost_total.labels(team='engineering', model='claude-sonnet-4-20250514').inc(0.05)
```

### 告警规则

```yaml
# Prometheus alert rules
groups:
  - name: cost_alerts
    rules:
      - alert: BudgetExceeded
        expr: monthly_cost_usd > monthly_budget_usd
        for: 5m
        annotations:
          summary: "团队 {{ $labels.team }} 预算超限"

      - alert: CostSpike
        expr: rate(api_cost_total_usd[5m]) > 0.1
        annotations:
          summary: "成本异常增长（>$6/小时）"
```

---

## 🧪 测试

```bash
# 单元测试
pytest cost_tracking/tests/ -v

# 集成测试
pytest tests/integration/ -v

# 性能测试
pytest tests/performance/ --benchmark-only
```

---

## 🚀 部署建议

### 生产环境 Checklist

- [ ] 配置生产数据库（PostgreSQL + 连接池）
- [ ] 启用 Redis 缓存（加速查询）
- [ ] 设置 Prometheus 监控
- [ ] 配置告警通知（Slack/Email）
- [ ] 定期备份成本数据
- [ ] 实施访问控制策略
- [ ] 建立月度成本审查流程

### 扩展性

- **水平扩展**: 使用 Redis 共享限流状态
- **数据分片**: 按月份分表存储历史数据
- **异步处理**: 使用 Celery 处理成本汇总

---

## 📚 延伸阅读

### 相关章节
- **第 11 章**: 团队协作与开发工作流程
- **第 13 章**: AI Agent 开发的未来与趋势

### 官方资源
- [Anthropic Pricing](https://www.anthropic.com/pricing)
- [Prompt Caching 文档](https://docs.anthropic.com/claude/docs/prompt-caching)

---

## 🤝 常见问题

### Q1: 如何选择合适的月度预算？

**A**: 建议步骤：
1. 试运行 1-2 周，收集实际使用数据
2. 计算平均日成本
3. 月度预算 = 平均日成本 × 35 × 1.2（20% 缓冲）

示例：日成本 $50 → 月预算 = $50 × 35 × 1.2 = $2,100

### Q2: Model Router 的准确率如何？

**A**: 基于 TechCorp 数据：
- 简单任务识别准确率: 94%
- 中等任务识别准确率: 87%
- 复杂任务识别准确率: 91%

**建议**: 在生产环境前，针对自己的任务类型微调复杂度判断逻辑。

### Q3: Prompt Caching 的缓存有效期？

**A**: Anthropic 的缓存有效期是 **5 分钟**。建议：
- 高频场景（客服）：非常合适
- 低频场景（< 每 5 分钟 2 次）：效益有限

### Q4: 如何处理预算超限但有紧急需求？

**A**: 使用优先级机制：

```python
# 紧急请求仍然允许（但会降级模型）
decision = throttler.should_throttle(
    requested_cost=5.0,
    priority="critical"  # 关键优先级
)
# 即使超限，也会返回 allow=True
```

### Q5: 成本数据保留多久？

**A**: 建议策略：
- **热数据**（近 3 个月）：PostgreSQL 快速查询
- **温数据**（3-12 个月）：压缩存储
- **冷数据**（> 1 年）：归档到 S3/GCS

---

## 📄 授权

本专案范例程式码采用 MIT 授权。

---

**祝你成本优化成功！** 💰

如有问题，请参考书籍第 12 章或提交 Issue。
