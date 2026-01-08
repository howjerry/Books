# 第 14 章：效能優化與成本控制 - 程式碼範例

## 概覽

本目錄包含第 14 章「效能優化與成本控制」的完整程式碼範例，實現了深度研究代理人的成本優化系統。

## 檔案結構

```
chapter-14/
├── cost_optimizer.py      # 完整成本優化引擎（~500 行）
├── requirements.txt       # Python 依賴
├── .env.example           # 環境變數範例
└── README.md              # 本文件
```

## 核心元件

### 1. 優化配置 (`OptimizationProfile`)

四種預設優化配置：

| 配置 | 成本權重 | 速度權重 | 品質權重 | 適用場景 |
|------|----------|----------|----------|----------|
| `COST_FIRST` | 60% | 20% | 20% | 預算有限 |
| `SPEED_FIRST` | 20% | 60% | 20% | 即時應用 |
| `QUALITY_FIRST` | 20% | 20% | 60% | 專業研究 |
| `BALANCED` | 34% | 33% | 33% | 一般用途 |

### 2. Token 分析與優化

**TokenAnalyzer**：追蹤 Token 使用
```python
analyzer = TokenAnalyzer()
tokens = analyzer.count_tokens("你的文本")
stats = analyzer.get_statistics()
```

**TokenOptimizer**：壓縮提示
```python
optimizer = TokenOptimizer(analyzer)
compressed = optimizer.compress_prompt(long_prompt, max_tokens=4000)
messages = optimizer.optimize_history(messages, max_tokens=8000)
```

### 3. 多層快取系統

**MemoryCache**（L1）：毫秒級響應
```python
cache = MemoryCache(max_size=1000, default_ttl=300)
await cache.set("key", value)
result = await cache.get("key")
```

**MultiLayerCache**：整合多層
```python
cache = MultiLayerCache()
await cache.set(key, value)
result = await cache.get(key)
stats = cache.get_stats()  # 含命中率
```

### 4. 成本追蹤與預算

```python
tracker = CostTracker()

# 設置預算
tracker.set_budget(Budget(
    period=BudgetPeriod.DAILY,
    limit=10.0,
    warning_threshold=0.8
))

# 記錄成本
tracker.record("llm_call", "gpt-4o", 1000, 500)

# 檢查是否可繼續
can_proceed, msg = tracker.check_can_proceed(estimated_cost)
```

### 5. 智能模型路由

```python
router = ModelRouter()

# 根據任務選擇模型
model = router.select_model(
    complexity=TaskComplexity.COMPLEX,
    prefer_quality=True,
    max_cost=0.05
)

# 獲取降級選項
fallback = router.get_fallback("gpt-4o")
```

### 6. 並行處理

```python
executor = ParallelExecutor(max_concurrency=10)
results = await executor.execute_all([task1, task2, task3])

limiter = RateLimiter(requests_per_second=10)
await limiter.acquire()  # 獲取令牌
```

### 7. 整合優化器

```python
from cost_optimizer import CostOptimizer, OptimizationProfile

optimizer = CostOptimizer(profile=OptimizationProfile.BALANCED)

result = await optimizer.optimize_call(
    prompt="你的提示",
    model="gpt-4o",
    use_cache=True,
    allow_fallback=True
)

print(f"成本: ${result['cost']:.6f}")
print(f"快取命中: {result['from_cache']}")
```

## 快速開始

### 1. 安裝依賴

```bash
pip install -r requirements.txt
```

### 2. 運行示範

```bash
python cost_optimizer.py
```

## 模型定價參考

| 模型 | 輸入 ($/1K) | 輸出 ($/1K) |
|------|-------------|-------------|
| gpt-4o | $0.005 | $0.015 |
| gpt-4-turbo | $0.01 | $0.03 |
| gpt-3.5-turbo | $0.0005 | $0.0015 |
| claude-3-opus | $0.015 | $0.075 |
| claude-3-sonnet | $0.003 | $0.015 |
| claude-3-haiku | $0.00025 | $0.00125 |

## 優化效果預期

| 優化策略 | 成本節省 | 說明 |
|----------|----------|------|
| Token 壓縮 | 20-40% | 移除冗餘內容 |
| 智能快取 | 30-60% | 避免重複調用 |
| 模型降級 | 50-80% | 用更便宜的模型 |
| 批次處理 | 10-30% | 減少調用次數 |

## 相關章節

- **第 11 章**：生產環境部署
- **第 12 章**：基準測試全解析
- **第 13 章**：幻覺處理與事實查核

## 授權

本程式碼範例遵循書籍的授權條款，僅供學習和參考使用。
