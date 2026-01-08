# 第 10 章：多代理人協作系統 - 程式碼範例

本目錄包含第 10 章「多代理人協作系統」的完整程式碼範例。

## 檔案結構

```
chapter-10/
├── coordinator.py       # 協調器與專家代理人
├── scheduler.py         # 任務調度器
├── conflict_resolver.py # 衝突解決器
├── requirements.txt     # Python 依賴套件
├── .env.example         # 環境變數範例
└── README.md            # 本文件
```

## 快速開始

### 1. 安裝依賴

```bash
cd chapter-10
pip install -r requirements.txt
```

### 2. 設定環境變數

```bash
cp .env.example .env
# 編輯 .env 填入你的配置
```

### 3. 執行示範

```bash
# 協調器示範
python coordinator.py --demo

# 執行自訂研究
python coordinator.py -q "AI 晶片市場競爭分析"

# 任務調度器示範
python scheduler.py --demo

# 衝突解決器示範
python conflict_resolver.py --demo
```

## 模組說明

### 協調器 (coordinator.py)

多代理人系統的核心，負責任務分解、分配與整合：

```python
from coordinator import ResearchCoordinator, ReportGenerator

# 創建協調器
coordinator = ResearchCoordinator()

# 執行多專家研究
result = await coordinator.coordinate(
    "全球半導體產業在 AI 時代的競爭格局"
)

# 生成報告
generator = ReportGenerator()
report = generator.generate_markdown(result)
print(report)
```

**內建專家代理人：**
- `IndustryAnalystAgent` - 產業分析師
- `TechExpertAgent` - 技術專家
- `FinancialAnalystAgent` - 財務分析師
- `GeopoliticalAdvisorAgent` - 地緣政治顧問

### 任務調度器 (scheduler.py)

智能任務調度，最大化平行度：

```python
from scheduler import TaskScheduler, SchedulableTask

# 創建任務
tasks = [
    SchedulableTask(task_id="A", description="任務 A", priority=5),
    SchedulableTask(task_id="B", description="任務 B", dependencies=["A"]),
    SchedulableTask(task_id="C", description="任務 C", dependencies=["A"]),
]

# 調度執行
scheduler = TaskScheduler(max_concurrent=3)
scheduler.add_tasks(tasks)

# 獲取平行執行組
groups = scheduler.get_parallel_groups()
# [["A"], ["B", "C"]]  # A 先執行，B 和 C 可平行

# 執行所有任務
results = await scheduler.execute_all(executor_function)
```

**主要功能：**
- 拓撲排序確定執行順序
- 自動識別可平行執行的任務
- 依賴管理與循環依賴檢測
- 失敗重試機制

### 衝突解決器 (conflict_resolver.py)

檢測並解決專家意見衝突：

```python
from conflict_resolver import ConflictDetector, IntegratedResolver

# 檢測衝突
detector = ConflictDetector()
conflicts = detector.detect_all(expert_reports)

# 解決衝突
resolver = IntegratedResolver()
results = await resolver.resolve_all(conflicts, expert_reports)

# 生成報告
report = resolver.generate_report(results)
```

**衝突類型：**
| 類型 | 說明 | 解決策略 |
|------|------|---------|
| 數值衝突 | 數值估計差異大 | 加權平均 |
| 類別衝突 | 類別判斷不一致 | 多數決 |
| 信心衝突 | 信心分數差異大 | 呈現各方 |
| 結論衝突 | 核心結論矛盾 | 呈現各方 |

## 系統架構

```
┌─────────────────────────────────────────────────────────────┐
│                   多代理人協作系統                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   研究問題                                                  │
│      │                                                      │
│      ▼                                                      │
│   ┌─────────────┐                                          │
│   │   協調器    │◀──────────────────────────────┐          │
│   │ Coordinator │                               │          │
│   └──────┬──────┘                               │          │
│          │                                      │          │
│          │ 任務分解                   結果回報   │          │
│          ▼                                      │          │
│   ┌─────────────┐                               │          │
│   │  調度器     │                               │          │
│   │ Scheduler   │                               │          │
│   └──────┬──────┘                               │          │
│          │                                      │          │
│          │ 平行分配                             │          │
│          ▼                                      │          │
│   ┌──────────────────────────────────────────┐ │          │
│   │            專家代理人池                   │ │          │
│   │  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐ │ │          │
│   │  │產業  │  │ 技術 │  │ 財務 │  │ 地緣 │ │ │          │
│   │  │分析師│  │ 專家 │  │分析師│  │ 顧問 │ │ │          │
│   │  └──────┘  └──────┘  └──────┘  └──────┘ │ │          │
│   └──────────────────────────────────────────┘ │          │
│          │                                      │          │
│          │ 收集結果                             │          │
│          ▼                                      │          │
│   ┌─────────────┐                               │          │
│   │ 衝突解決器  │───────────────────────────────┘          │
│   └──────┬──────┘                                          │
│          │                                                  │
│          ▼                                                  │
│   ┌─────────────┐                                          │
│   │ 報告生成器  │                                          │
│   └──────┬──────┘                                          │
│          │                                                  │
│          ▼                                                  │
│      研究報告                                               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 擴展指南

### 新增專家代理人

```python
from coordinator import ExpertAgent, SubTask

class ESGAnalystAgent(ExpertAgent):
    """ESG 分析師代理人"""

    def __init__(self, llm_client=None):
        super().__init__(
            name="ESG 分析師",
            expertise="ESG 分析",
            description="專注於環境、社會、治理分析",
            llm_client=llm_client
        )

    async def analyze(self, task: SubTask, context: Dict) -> Dict:
        # 實現分析邏輯
        return {
            "analysis_type": "esg_analysis",
            "findings": {...},
            "confidence": 0.8
        }

# 註冊到協調器
coordinator.register_agent(ESGAnalystAgent())
```

### 自訂衝突解決策略

```python
from conflict_resolver import ConflictResolver, ResolutionResult

class ArbitrationResolver(ConflictResolver):
    """仲裁解決器"""

    def __init__(self, arbitrator_agent):
        self.arbitrator = arbitrator_agent

    async def resolve(self, conflict, reports):
        # 請仲裁代理人做出判斷
        judgment = await self.arbitrator.arbitrate(conflict, reports)

        return ResolutionResult(
            conflict=conflict,
            method=ResolutionMethod.ARBITRATION,
            final_value=judgment["conclusion"],
            confidence=judgment["confidence"],
            reasoning=judgment["reasoning"]
        )

# 使用自訂解決器
resolver = IntegratedResolver()
resolver.set_resolver(ConflictType.CONCLUSION, ArbitrationResolver(arbitrator))
```

## 效能優化

### 1. 共享快取

```python
class SharedCache:
    """避免重複獲取相同資訊"""

    def __init__(self):
        self._cache = {}

    async def get_or_fetch(self, key, fetcher):
        if key not in self._cache:
            self._cache[key] = await fetcher()
        return self._cache[key]
```

### 2. 批次處理

```python
async def batch_research(questions: List[str], batch_size=5):
    """批次處理多個研究問題"""
    results = []
    for i in range(0, len(questions), batch_size):
        batch = questions[i:i+batch_size]
        batch_results = await asyncio.gather(
            *[coordinator.coordinate(q) for q in batch]
        )
        results.extend(batch_results)
    return results
```

### 3. 超時控制

```python
async def execute_with_timeout(task, agent, timeout=30):
    """帶超時的任務執行"""
    try:
        return await asyncio.wait_for(
            agent.analyze(task, {}),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        return {"status": "timeout", "error": f"執行超時 ({timeout}s)"}
```

## 學習要點

完成本章後，你將掌握：

1. **多代理人架構設計**
   - 層級式、對等式、混合式模式
   - 協調器設計原則
   - 專家代理人介面標準

2. **任務調度**
   - 依賴圖與拓撲排序
   - 平行執行最大化
   - 失敗重試機制

3. **衝突解決**
   - 衝突類型識別
   - 多種解決策略
   - 結果整合方法

4. **系統整合**
   - 端到端執行流程
   - 報告生成
   - 效能優化

## 相關章節

- **第 9 章**：建構你的第一個研究代理人
- **第 11 章**：生產環境部署
- **第 12 章**：基準測試全解析
