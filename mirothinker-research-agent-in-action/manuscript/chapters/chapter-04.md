# 第 4 章：核心調度器設計

> **本章目標**：完整剖析 MiroThinker 的調度器設計，並實作一個能處理複雜多步任務的調度系統。
>
> **核心產出物**：
> - 調度器職責圖與架構圖
> - 任務分解演算法
> - 執行流程 Mermaid 圖
> - 完整可運行的 `dispatcher.py`（500+ 行）

---

## 開場案例：一個失控的研究任務

讓我們從一個真實場景開始。

你建構了一個研究代理人，給它一個看似簡單的任務：

> 「分析 2024 年全球 AI 晶片市場格局，包括主要玩家、技術趨勢、以及未來三年的投資建議。」

代理人開始工作。第一次搜尋返回了 NVIDIA 的資料，於是它繼續搜尋 AMD。然後是 Intel、Google TPU、AWS Inferentia...每個玩家又牽涉到技術細節、財務數據、競爭對手比較...

30 分鐘後，代理人仍在搜尋。它已經執行了 200 次工具調用，蒐集了大量資料，但沒有任何整合的跡象。更糟的是，它開始重複搜尋之前已經查過的內容。

這就是缺乏「**調度器**」（Dispatcher）的後果。

沒有調度器的代理人就像一個沒有專案經理的開發團隊——每個人都在忙，但沒有人知道整體進度，沒有人確保任務按時完成，也沒有人處理任務之間的依賴關係。

本章將教你如何設計一個強大的調度器，讓你的代理人從「盲目執行」升級為「策略性研究」。

---

## 4.1 調度器的角色與職責

### 4.1.1 什麼是調度器？

在深度研究代理人系統中，**調度器**（Dispatcher）是負責協調整個研究流程的核心組件。它就像一個經驗豐富的研究總監：

- 接收研究任務並理解其範圍
- 將大任務分解為可管理的子任務
- 決定子任務的執行順序和優先級
- 監控執行進度並處理異常
- 整合各個子任務的結果

```
┌──────────────────────────────────────────────────────────────────┐
│                    調度器在系統中的位置                           │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│                         ┌─────────────┐                         │
│                         │  使用者請求  │                         │
│                         └──────┬──────┘                         │
│                                │                                 │
│                                ▼                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                      調 度 器                            │    │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐    │    │
│  │  │任務接收 │→│任務分解 │→│執行編排 │→│結果整合 │    │    │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘    │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                │                                 │
│            ┌───────────────────┼───────────────────┐            │
│            ▼                   ▼                   ▼            │
│     ┌───────────┐       ┌───────────┐       ┌───────────┐      │
│     │  搜尋工具  │       │  瀏覽工具  │       │ 程式碼執行 │      │
│     └───────────┘       └───────────┘       └───────────┘      │
│            │                   │                   │            │
│            └───────────────────┼───────────────────┘            │
│                                ▼                                 │
│                         ┌─────────────┐                         │
│                         │  研究報告   │                         │
│                         └─────────────┘                         │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 4.1.2 調度器的五大職責

一個完整的調度器需要履行以下職責：

| 職責 | 說明 | 關鍵能力 |
|------|------|----------|
| **任務接收** | 接收並解析使用者請求 | 意圖理解、範圍界定 |
| **任務分解** | 將複雜任務拆分為子任務 | 依賴分析、粒度控制 |
| **資源分配** | 為子任務分配工具和計算資源 | 優先級排序、負載平衡 |
| **執行監控** | 追蹤子任務執行狀態 | 進度追蹤、異常處理 |
| **結果整合** | 收集並整合子任務結果 | 衝突解決、質量控制 |

### 4.1.3 調度器與執行器的分離

一個良好的架構會將「**調度**」和「**執行**」分離：

```
┌─────────────────────────────────────────────────────────────┐
│                    職責分離原則                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────┐  ┌─────────────────────────┐  │
│  │       調度器層          │  │       執行器層          │  │
│  │  (Dispatcher Layer)     │  │   (Executor Layer)      │  │
│  ├─────────────────────────┤  ├─────────────────────────┤  │
│  │ • 任務規劃              │  │ • 工具調用              │  │
│  │ • 優先級決策            │  │ • API 請求              │  │
│  │ • 狀態管理              │  │ • 結果解析              │  │
│  │ • 錯誤策略              │  │ • 重試邏輯              │  │
│  │ • 進度追蹤              │  │ • 超時處理              │  │
│  └─────────────────────────┘  └─────────────────────────┘  │
│              │                          ▲                   │
│              │      任務指令            │                   │
│              └──────────────────────────┘                   │
│                      執行結果                               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

這種分離帶來幾個好處：

1. **可測試性**：可以獨立測試調度邏輯
2. **可擴展性**：可以替換不同的執行器實現
3. **可維護性**：職責清晰，代碼易於理解
4. **可觀測性**：更容易監控和調試

---

## 4.2 MiroThinker Dispatcher 原始碼剖析

讓我們深入分析 MiroThinker 項目中調度器的設計。雖然我們無法直接查看其私有代碼，但可以從其公開的架構設計和行為推斷出核心機制。

### 4.2.1 狀態機設計

MiroThinker 的調度器採用**有限狀態機**（Finite State Machine, FSM）模式管理任務生命週期：

```
┌──────────────────────────────────────────────────────────────────┐
│                    任務狀態機                                     │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────┐                                                    │
│  │ PENDING │  任務已創建，等待處理                               │
│  └────┬────┘                                                    │
│       │ start()                                                  │
│       ▼                                                          │
│  ┌─────────┐                                                    │
│  │ PLANNING│  正在分解任務、建立執行計畫                         │
│  └────┬────┘                                                    │
│       │ plan_complete()                                          │
│       ▼                                                          │
│  ┌─────────┐         retry()         ┌─────────┐               │
│  │ RUNNING │◀───────────────────────│ RETRYING│               │
│  └────┬────┘                         └────▲────┘               │
│       │                                   │                      │
│       ├─── success() ───▶ ┌─────────┐    │                      │
│       │                   │COMPLETED│    │                      │
│       │                   └─────────┘    │                      │
│       │                                   │                      │
│       ├─── error() ─────▶ 判斷是否重試 ───┘                      │
│       │                        │                                 │
│       │                        │ max_retries_exceeded()          │
│       │                        ▼                                 │
│       └─── timeout() ──▶ ┌─────────┐                            │
│                          │ FAILED  │                            │
│                          └─────────┘                            │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

狀態定義：

```python
from enum import Enum, auto

class TaskState(Enum):
    """任務狀態枚舉"""
    PENDING = auto()    # 等待處理
    PLANNING = auto()   # 規劃中
    RUNNING = auto()    # 執行中
    RETRYING = auto()   # 重試中
    COMPLETED = auto()  # 已完成
    FAILED = auto()     # 已失敗
    CANCELLED = auto()  # 已取消
```

### 4.2.2 核心類別結構

MiroThinker 調度器的核心類別結構如下：

```python
from dataclasses import dataclass, field
from typing import Optional, Callable
from datetime import datetime
import uuid

@dataclass
class Task:
    """任務資料結構"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    query: str = ""                      # ‹1› 原始查詢
    state: TaskState = TaskState.PENDING # ‹2› 當前狀態
    priority: int = 5                    # ‹3› 優先級 (1-10)
    parent_id: Optional[str] = None      # ‹4› 父任務 ID
    children: list = field(default_factory=list)  # ‹5› 子任務列表
    dependencies: list = field(default_factory=list)  # ‹6› 依賴的任務
    result: Optional[dict] = None        # ‹7› 執行結果
    error: Optional[str] = None          # ‹8› 錯誤訊息
    retry_count: int = 0                 # ‹9› 重試次數
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class ExecutionPlan:
    """執行計畫"""
    root_task: Task
    task_graph: dict  # 任務依賴圖
    execution_order: list  # 執行順序
    estimated_duration: float  # 預估耗時
```

**標記說明**：
- ‹1› 原始的使用者請求或子任務描述
- ‹2› 任務當前的狀態（狀態機的當前位置）
- ‹3› 數字越小優先級越高
- ‹4› 如果是子任務，記錄父任務的 ID
- ‹5› 任務被分解後產生的子任務
- ‹6› 必須在本任務之前完成的其他任務
- ‹7› 任務執行完成後的結果
- ‹8› 如果失敗，記錄錯誤原因
- ‹9› 已經重試的次數

### 4.2.3 調度器主類別

```python
class Dispatcher:
    """
    核心調度器

    負責任務的接收、分解、調度和監控
    """

    def __init__(
        self,
        max_concurrent_tasks: int = 5,
        max_retries: int = 3,
        task_timeout: float = 300.0
    ):
        self.max_concurrent_tasks = max_concurrent_tasks
        self.max_retries = max_retries
        self.task_timeout = task_timeout

        # 任務存儲
        self.tasks: dict[str, Task] = {}
        self.task_queue: list[Task] = []  # 待執行隊列

        # 執行狀態
        self.running_tasks: set[str] = set()

        # 回調函數
        self.on_task_complete: Optional[Callable] = None
        self.on_task_failed: Optional[Callable] = None

    async def submit(self, query: str, priority: int = 5) -> Task:
        """提交新任務"""
        task = Task(query=query, priority=priority)
        self.tasks[task.id] = task
        await self._plan_task(task)
        return task

    async def _plan_task(self, task: Task):
        """規劃任務執行"""
        task.state = TaskState.PLANNING
        # 任務分解邏輯（見下一節）
        subtasks = await self._decompose(task)
        task.children = [st.id for st in subtasks]
        # 加入執行隊列
        self._enqueue(task)
        task.state = TaskState.RUNNING

    def _enqueue(self, task: Task):
        """將任務加入隊列（按優先級排序）"""
        self.task_queue.append(task)
        self.task_queue.sort(key=lambda t: t.priority)
```

### 4.2.4 事件驅動架構

MiroThinker 採用事件驅動模式處理任務狀態變化：

```python
from enum import Enum
from typing import Callable, Any
from collections import defaultdict

class TaskEvent(Enum):
    """任務事件類型"""
    CREATED = "created"
    STARTED = "started"
    PROGRESS = "progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class EventBus:
    """事件總線"""

    def __init__(self):
        self._handlers: dict[TaskEvent, list[Callable]] = defaultdict(list)

    def subscribe(self, event: TaskEvent, handler: Callable):
        """訂閱事件"""
        self._handlers[event].append(handler)

    def publish(self, event: TaskEvent, data: Any):
        """發布事件"""
        for handler in self._handlers[event]:
            try:
                handler(data)
            except Exception as e:
                print(f"Event handler error: {e}")
```

這種設計允許系統的不同部分鬆散耦合地響應任務狀態變化：

- **日誌系統**訂閱所有事件，記錄完整執行軌跡
- **監控系統**訂閱 PROGRESS 事件，更新進度指示器
- **告警系統**訂閱 FAILED 事件，發送通知

---

## 4.3 任務分解策略

任務分解是調度器最關鍵的能力之一。一個好的分解策略能夠：

- 將複雜問題轉化為可並行處理的子問題
- 識別子問題之間的依賴關係
- 保持適當的分解粒度

### 4.3.1 分解原則

**MECE 原則**（Mutually Exclusive, Collectively Exhaustive）：

```
┌──────────────────────────────────────────────────────────────────┐
│                    MECE 分解原則                                  │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  原始任務：分析全球 AI 晶片市場                                   │
│                                                                  │
│  ✅ 正確分解（MECE）：                                           │
│  ┌──────────────────────────────────────────────────────┐       │
│  │                                                      │       │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐│       │
│  │  │ 供應端  │ │ 需求端  │ │ 技術   │ │ 投資   ││       │
│  │  │ 分析   │ │ 分析   │ │ 趨勢   │ │ 建議   ││       │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘│       │
│  │      ↑互斥        ↑互斥        ↑互斥        ↑互斥    │       │
│  │                                                      │       │
│  │  ←─────────────── 完備覆蓋 ───────────────→         │       │
│  └──────────────────────────────────────────────────────┘       │
│                                                                  │
│  ❌ 錯誤分解（非 MECE）：                                        │
│  ┌──────────────────────────────────────────────────────┐       │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐              │       │
│  │  │ NVIDIA  │ │ GPU市場 │ │ 資料中心│   ← 重疊!     │       │
│  │  │ 分析   │ │ 分析   │ │ 晶片   │              │       │
│  │  └──────────┘ └──────────┘ └──────────┘              │       │
│  │                                                      │       │
│  │  缺少：邊緣 AI 晶片、車用晶片、手機 AI 晶片...        │       │
│  └──────────────────────────────────────────────────────┘       │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 4.3.2 分解粒度控制

分解粒度需要權衡：

| 粒度 | 優點 | 缺點 | 適用場景 |
|------|------|------|----------|
| **粗粒度** | 減少協調開銷 | 難以並行化 | 簡單任務 |
| **細粒度** | 高度並行化 | 協調開銷大 | 複雜任務 |
| **適中粒度** | 平衡並行與協調 | 需要經驗判斷 | 一般任務 |

判斷粒度的經驗法則：

```python
def estimate_granularity(task: Task) -> str:
    """估計任務應採用的分解粒度"""

    # 預估任務複雜度
    complexity = estimate_complexity(task.query)

    # 預估可並行度
    parallelism = estimate_parallelism(task.query)

    if complexity < 3 and parallelism < 2:
        return "coarse"  # 粗粒度：不分解或最小分解
    elif complexity > 7 or parallelism > 5:
        return "fine"    # 細粒度：深度分解
    else:
        return "medium"  # 適中粒度：標準分解
```

### 4.3.3 依賴關係識別

子任務之間可能存在依賴關係。我們需要識別並正確處理這些依賴：

```
┌──────────────────────────────────────────────────────────────────┐
│                    任務依賴圖範例                                 │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  研究任務：分析 AI 晶片市場並給出投資建議                         │
│                                                                  │
│                    ┌─────────────┐                              │
│                    │  根任務     │                              │
│                    │  (T0)      │                              │
│                    └──────┬──────┘                              │
│                           │                                      │
│         ┌─────────────────┼─────────────────┐                   │
│         ▼                 ▼                 ▼                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ 市場規模   │  │ 主要玩家   │  │ 技術趨勢   │             │
│  │   (T1)     │  │   (T2)     │  │   (T3)     │             │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
│         │                │                │                      │
│         │                ▼                │                      │
│         │         ┌─────────────┐         │                      │
│         │         │ 競爭分析   │         │                      │
│         └────────▶│   (T4)     │◀────────┘                      │
│                   │ 依賴T1,T2,T3│                                │
│                   └──────┬──────┘                                │
│                          │                                       │
│                          ▼                                       │
│                   ┌─────────────┐                                │
│                   │ 投資建議   │                                │
│                   │   (T5)     │                                │
│                   │ 依賴T4     │                                │
│                   └─────────────┘                                │
│                                                                  │
│  執行順序：{T1, T2, T3} (並行) → T4 → T5                         │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

依賴關係的程式表示：

```python
from dataclasses import dataclass, field

@dataclass
class TaskNode:
    """任務節點（用於依賴圖）"""
    task_id: str
    dependencies: set = field(default_factory=set)  # 前置依賴
    dependents: set = field(default_factory=set)    # 後續依賴


class DependencyGraph:
    """任務依賴圖"""

    def __init__(self):
        self.nodes: dict[str, TaskNode] = {}

    def add_task(self, task_id: str, dependencies: list[str] = None):
        """添加任務節點"""
        deps = set(dependencies or [])
        self.nodes[task_id] = TaskNode(task_id=task_id, dependencies=deps)

        # 更新依賴關係
        for dep_id in deps:
            if dep_id in self.nodes:
                self.nodes[dep_id].dependents.add(task_id)

    def get_ready_tasks(self, completed: set[str]) -> list[str]:
        """獲取可執行的任務（所有依賴已完成）"""
        ready = []
        for task_id, node in self.nodes.items():
            if task_id not in completed:
                if node.dependencies.issubset(completed):
                    ready.append(task_id)
        return ready

    def topological_sort(self) -> list[str]:
        """拓撲排序（獲取執行順序）"""
        in_degree = {tid: len(node.dependencies)
                     for tid, node in self.nodes.items()}
        queue = [tid for tid, deg in in_degree.items() if deg == 0]
        result = []

        while queue:
            current = queue.pop(0)
            result.append(current)
            for dependent in self.nodes[current].dependents:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        if len(result) != len(self.nodes):
            raise ValueError("Circular dependency detected!")

        return result
```

### 4.3.4 動態重規劃

研究過程中可能發現新的子任務需求，或者某些計畫的子任務變得不必要。調度器需要支持動態調整：

```python
class DynamicPlanner:
    """動態規劃器"""

    def __init__(self, dispatcher: 'Dispatcher'):
        self.dispatcher = dispatcher

    async def replan(self, task: Task, reason: str):
        """重新規劃任務"""

        # 1. 暫停當前執行
        await self.dispatcher.pause_task(task.id)

        # 2. 評估是否需要重規劃
        if not self._should_replan(task, reason):
            await self.dispatcher.resume_task(task.id)
            return

        # 3. 取消不再需要的子任務
        obsolete = self._identify_obsolete_subtasks(task)
        for subtask_id in obsolete:
            await self.dispatcher.cancel_task(subtask_id)

        # 4. 添加新的子任務
        new_subtasks = await self._generate_new_subtasks(task, reason)
        for subtask in new_subtasks:
            await self.dispatcher.submit_subtask(task.id, subtask)

        # 5. 重新計算依賴圖
        self.dispatcher.rebuild_dependency_graph(task.id)

        # 6. 恢復執行
        await self.dispatcher.resume_task(task.id)

    def _should_replan(self, task: Task, reason: str) -> bool:
        """判斷是否需要重規劃"""
        # 如果已完成超過 80%，不值得重規劃
        progress = self._calculate_progress(task)
        if progress > 0.8:
            return False

        # 如果原因是發現關鍵新資訊，應該重規劃
        if "critical" in reason.lower() or "important" in reason.lower():
            return True

        return False
```

---

## 4.4 執行流程編排

調度器需要決定子任務的執行方式：同步、異步、還是並行？

### 4.4.1 同步 vs 異步執行

```
┌──────────────────────────────────────────────────────────────────┐
│                    執行模式比較                                   │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  同步執行（Sequential）：                                        │
│  ┌────┐   ┌────┐   ┌────┐   ┌────┐                             │
│  │ T1 │──▶│ T2 │──▶│ T3 │──▶│ T4 │                             │
│  └────┘   └────┘   └────┘   └────┘                             │
│  ──────────────────────────────────▶ 時間                        │
│  總時間 = T1 + T2 + T3 + T4                                      │
│                                                                  │
│  ─────────────────────────────────────────────────────────────  │
│                                                                  │
│  異步並行執行（Parallel）：                                       │
│  ┌────┐                                                         │
│  │ T1 │────────────────────▶                                    │
│  └────┘                                                         │
│  ┌────┐                                                         │
│  │ T2 │──────────────▶                                          │
│  └────┘                                                         │
│  ┌────┐                                                         │
│  │ T3 │────────────────────────────▶                            │
│  └────┘                                                         │
│  ┌────┐                                                         │
│  │ T4 │──────────▶                                              │
│  └────┘                                                         │
│  ──────────────────────────────────▶ 時間                        │
│  總時間 = max(T1, T2, T3, T4)                                    │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

選擇執行模式的決策樹：

```python
def choose_execution_mode(tasks: list[Task]) -> str:
    """選擇執行模式"""

    # 1. 檢查依賴關係
    has_dependencies = any(t.dependencies for t in tasks)
    if has_dependencies:
        return "dependency_aware"  # 需要考慮依賴的混合模式

    # 2. 檢查資源競爭
    uses_same_resources = check_resource_conflict(tasks)
    if uses_same_resources:
        return "sequential"  # 避免資源衝突

    # 3. 檢查任務數量
    if len(tasks) == 1:
        return "sequential"

    # 4. 預設並行執行
    return "parallel"
```

### 4.4.2 並行任務管理

當多個任務並行執行時，需要管理並發度和資源分配：

```python
import asyncio
from typing import TypeVar, Coroutine

T = TypeVar('T')

class ParallelExecutor:
    """並行執行器"""

    def __init__(self, max_concurrency: int = 5):
        self.max_concurrency = max_concurrency
        self.semaphore = asyncio.Semaphore(max_concurrency)

    async def execute_all(
        self,
        tasks: list[Coroutine[any, any, T]]
    ) -> list[T]:
        """並行執行所有任務"""

        async def limited_execute(coro):
            async with self.semaphore:
                return await coro

        return await asyncio.gather(
            *[limited_execute(task) for task in tasks],
            return_exceptions=True
        )

    async def execute_with_progress(
        self,
        tasks: list[Coroutine],
        progress_callback: callable
    ) -> list:
        """帶進度回報的並行執行"""
        total = len(tasks)
        completed = 0
        results = []

        async def track_task(coro, index):
            nonlocal completed
            try:
                result = await coro
                completed += 1
                progress_callback(completed, total, index, "success")
                return result
            except Exception as e:
                completed += 1
                progress_callback(completed, total, index, "failed")
                raise

        async with self.semaphore:
            results = await asyncio.gather(
                *[track_task(t, i) for i, t in enumerate(tasks)],
                return_exceptions=True
            )

        return results
```

### 4.4.3 超時與重試策略

```python
import asyncio
from functools import wraps

class RetryConfig:
    """重試配置"""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0


def with_retry(config: RetryConfig = None):
    """重試裝飾器"""
    if config is None:
        config = RetryConfig()

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(config.max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    if attempt < config.max_retries:
                        # 計算指數退避延遲
                        delay = min(
                            config.base_delay * (config.exponential_base ** attempt),
                            config.max_delay
                        )
                        print(f"Retry {attempt + 1}/{config.max_retries} "
                              f"after {delay:.1f}s: {e}")
                        await asyncio.sleep(delay)

            raise last_exception

        return wrapper
    return decorator


async def execute_with_timeout(
    coro,
    timeout: float,
    timeout_message: str = "Task timed out"
):
    """帶超時的執行"""
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        raise TimeoutError(timeout_message)
```

### 4.4.4 執行流程圖

完整的執行流程如下：

```
┌──────────────────────────────────────────────────────────────────┐
│                    調度器執行流程                                 │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐                                                │
│  │  接收任務   │                                                │
│  └──────┬──────┘                                                │
│         │                                                        │
│         ▼                                                        │
│  ┌─────────────┐     ┌─────────────┐                           │
│  │  任務分解   │────▶│ 建立依賴圖 │                           │
│  └──────┬──────┘     └──────┬──────┘                           │
│         │                   │                                    │
│         └─────────┬─────────┘                                   │
│                   ▼                                              │
│         ┌─────────────────┐                                     │
│         │  計算執行順序   │                                     │
│         │  (拓撲排序)     │                                     │
│         └────────┬────────┘                                     │
│                  │                                               │
│                  ▼                                               │
│  ┌───────────────────────────────────────────┐                  │
│  │              執行循環                      │                  │
│  │  ┌─────────────────────────────────────┐  │                  │
│  │  │ 獲取可執行任務                      │  │                  │
│  │  └──────────────┬──────────────────────┘  │                  │
│  │                 │                         │                  │
│  │                 ▼                         │                  │
│  │  ┌─────────────────────────────────────┐  │                  │
│  │  │ 並行執行（受限於 max_concurrency）  │  │                  │
│  │  └──────────────┬──────────────────────┘  │                  │
│  │                 │                         │                  │
│  │       ┌─────────┼─────────┐              │                  │
│  │       ▼         ▼         ▼              │                  │
│  │   ┌──────┐  ┌──────┐  ┌──────┐          │                  │
│  │   │成功  │  │失敗  │  │超時  │          │                  │
│  │   └──┬───┘  └──┬───┘  └──┬───┘          │                  │
│  │      │         │         │               │                  │
│  │      │    ┌────▼────┐    │               │                  │
│  │      │    │重試判斷 │◀───┘               │                  │
│  │      │    └────┬────┘                    │                  │
│  │      │         │                         │                  │
│  │      │    ┌────┴────┐                    │                  │
│  │      │    ▼         ▼                    │                  │
│  │      │  重試     標記失敗                │                  │
│  │      │    │         │                    │                  │
│  │      └────┴─────────┘                    │                  │
│  │                 │                         │                  │
│  │                 ▼                         │                  │
│  │  ┌─────────────────────────────────────┐  │                  │
│  │  │ 更新依賴狀態、解鎖後續任務          │  │                  │
│  │  └──────────────┬──────────────────────┘  │                  │
│  │                 │                         │                  │
│  │                 ▼                         │                  │
│  │          是否還有任務？ ──── 是 ─────────┘                  │
│  │                 │                                            │
│  │                 │ 否                                         │
│  └─────────────────┼────────────────────────────────────────────┘
│                    ▼                                             │
│           ┌─────────────┐                                       │
│           │  整合結果   │                                       │
│           └──────┬──────┘                                       │
│                  │                                               │
│                  ▼                                               │
│           ┌─────────────┐                                       │
│           │  返回報告   │                                       │
│           └─────────────┘                                       │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 4.5 動手實作：建構你的調度器

現在讓我們把所有概念整合起來，建構一個完整的調度器。

### 4.5.1 完整實作

```python
"""
dispatcher.py

深度研究代理人的核心調度器實現
支援任務分解、依賴管理、並行執行和錯誤恢復

使用方式：
    dispatcher = Dispatcher()
    result = await dispatcher.run("分析 AI 晶片市場格局")
"""

import os
import json
import asyncio
import uuid
from enum import Enum, auto
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Callable, Any
from collections import defaultdict
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()


# =============================================================================
# 狀態與事件定義
# =============================================================================

class TaskState(Enum):
    """任務狀態"""
    PENDING = auto()
    PLANNING = auto()
    READY = auto()
    RUNNING = auto()
    WAITING = auto()  # 等待依賴
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


class TaskEvent(Enum):
    """任務事件"""
    CREATED = "created"
    STARTED = "started"
    PROGRESS = "progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


# =============================================================================
# 資料結構
# =============================================================================

@dataclass
class Task:
    """任務資料結構"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    query: str = ""
    state: TaskState = TaskState.PENDING
    priority: int = 5
    parent_id: Optional[str] = None
    children: list = field(default_factory=list)
    dependencies: list = field(default_factory=list)
    result: Optional[dict] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """轉換為字典"""
        return {
            "id": self.id,
            "query": self.query,
            "state": self.state.name,
            "priority": self.priority,
            "parent_id": self.parent_id,
            "children": self.children,
            "dependencies": self.dependencies,
            "retry_count": self.retry_count,
            "result": self.result,
            "error": self.error
        }


@dataclass
class ExecutionPlan:
    """執行計畫"""
    root_task_id: str
    tasks: dict[str, Task] = field(default_factory=dict)
    execution_order: list[str] = field(default_factory=list)
    dependency_graph: dict = field(default_factory=dict)


# =============================================================================
# 事件總線
# =============================================================================

class EventBus:
    """事件總線"""

    def __init__(self):
        self._handlers: dict[TaskEvent, list[Callable]] = defaultdict(list)

    def subscribe(self, event: TaskEvent, handler: Callable):
        """訂閱事件"""
        self._handlers[event].append(handler)

    def publish(self, event: TaskEvent, data: Any):
        """發布事件"""
        for handler in self._handlers[event]:
            try:
                handler(data)
            except Exception as e:
                print(f"Event handler error: {e}")

    def clear(self):
        """清除所有訂閱"""
        self._handlers.clear()


# =============================================================================
# 依賴圖
# =============================================================================

class DependencyGraph:
    """任務依賴圖"""

    def __init__(self):
        self.nodes: dict[str, set] = {}  # task_id -> set of dependencies
        self.reverse: dict[str, set] = defaultdict(set)  # task_id -> set of dependents

    def add_task(self, task_id: str, dependencies: list[str] = None):
        """添加任務"""
        deps = set(dependencies or [])
        self.nodes[task_id] = deps

        for dep_id in deps:
            self.reverse[dep_id].add(task_id)

    def remove_task(self, task_id: str):
        """移除任務"""
        if task_id in self.nodes:
            for dep_id in self.nodes[task_id]:
                self.reverse[dep_id].discard(task_id)
            del self.nodes[task_id]

        if task_id in self.reverse:
            for dependent_id in self.reverse[task_id]:
                if dependent_id in self.nodes:
                    self.nodes[dependent_id].discard(task_id)
            del self.reverse[task_id]

    def get_ready_tasks(self, completed: set[str]) -> list[str]:
        """獲取可執行的任務"""
        ready = []
        for task_id, deps in self.nodes.items():
            if task_id not in completed and deps.issubset(completed):
                ready.append(task_id)
        return ready

    def get_execution_order(self) -> list[str]:
        """獲取執行順序（拓撲排序）"""
        in_degree = {tid: len(deps) for tid, deps in self.nodes.items()}
        queue = [tid for tid, deg in in_degree.items() if deg == 0]
        result = []

        while queue:
            current = queue.pop(0)
            result.append(current)

            for dependent in self.reverse.get(current, []):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        if len(result) != len(self.nodes):
            raise ValueError("Circular dependency detected!")

        return result


# =============================================================================
# 任務執行器
# =============================================================================

class TaskExecutor:
    """任務執行器"""

    def __init__(self, client: AsyncOpenAI, model: str = "gpt-4o-mini"):
        self.client = client
        self.model = model

    async def execute(self, task: Task) -> dict:
        """執行任務"""
        # 根據任務類型選擇執行策略
        task_type = task.metadata.get("type", "research")

        if task_type == "search":
            return await self._execute_search(task)
        elif task_type == "analyze":
            return await self._execute_analyze(task)
        elif task_type == "synthesize":
            return await self._execute_synthesize(task)
        else:
            return await self._execute_research(task)

    async def _execute_research(self, task: Task) -> dict:
        """執行研究任務"""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{
                "role": "user",
                "content": f"請研究以下問題並提供詳細分析：\n\n{task.query}"
            }],
            temperature=0.3
        )

        return {
            "type": "research",
            "content": response.choices[0].message.content,
            "tokens_used": response.usage.total_tokens if response.usage else 0
        }

    async def _execute_search(self, task: Task) -> dict:
        """執行搜尋任務（模擬）"""
        # 在實際實現中，這裡會調用搜尋 API
        await asyncio.sleep(0.5)  # 模擬網路延遲

        return {
            "type": "search",
            "content": f"搜尋結果：{task.query}",
            "sources": ["https://example.com/1", "https://example.com/2"]
        }

    async def _execute_analyze(self, task: Task) -> dict:
        """執行分析任務"""
        # 獲取依賴任務的結果
        parent_results = task.metadata.get("parent_results", [])

        context = "\n".join([
            f"資料 {i+1}：{r.get('content', '')[:500]}"
            for i, r in enumerate(parent_results)
        ])

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{
                "role": "user",
                "content": f"""基於以下資料進行分析：

{context}

分析任務：{task.query}

請提供結構化的分析結果。"""
            }],
            temperature=0.3
        )

        return {
            "type": "analyze",
            "content": response.choices[0].message.content
        }

    async def _execute_synthesize(self, task: Task) -> dict:
        """執行綜合任務"""
        parent_results = task.metadata.get("parent_results", [])

        context = "\n\n".join([
            f"## 資料 {i+1}\n{r.get('content', '')}"
            for i, r in enumerate(parent_results)
        ])

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{
                "role": "user",
                "content": f"""請綜合以下研究結果，生成一份完整的報告：

{context}

報告主題：{task.query}

請生成一份結構化的研究報告，包含：
1. 摘要
2. 主要發現
3. 分析
4. 結論與建議"""
            }],
            temperature=0.3
        )

        return {
            "type": "synthesize",
            "content": response.choices[0].message.content
        }


# =============================================================================
# 任務分解器
# =============================================================================

class TaskDecomposer:
    """任務分解器"""

    def __init__(self, client: AsyncOpenAI, model: str = "gpt-4o-mini"):
        self.client = client
        self.model = model

    async def decompose(self, task: Task) -> list[Task]:
        """分解任務為子任務"""

        prompt = f"""你是一位任務規劃專家。請將以下研究任務分解為可執行的子任務。

研究任務：{task.query}

請分解為 3-6 個子任務，每個子任務應該：
1. 具體且可獨立執行
2. 涵蓋問題的不同面向
3. 有明確的產出物

請以 JSON 格式輸出：
```json
{{
  "subtasks": [
    {{
      "id": "1",
      "query": "子任務描述",
      "type": "search|analyze|synthesize",
      "priority": 1-10,
      "dependencies": []
    }}
  ],
  "final_task": {{
    "query": "整合所有結果的最終任務描述",
    "dependencies": ["所有子任務的 id"]
  }}
}}
```"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )

        content = response.choices[0].message.content

        # 解析 JSON
        import re
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', content)
        if json_match:
            data = json.loads(json_match.group(1))
        else:
            try:
                data = json.loads(content)
            except:
                # 降級：不分解，直接執行
                return []

        subtasks = []

        for st in data.get("subtasks", []):
            subtask = Task(
                id=f"{task.id}-{st['id']}",
                query=st["query"],
                priority=st.get("priority", 5),
                parent_id=task.id,
                dependencies=[f"{task.id}-{d}" for d in st.get("dependencies", [])],
                metadata={"type": st.get("type", "research")}
            )
            subtasks.append(subtask)

        # 添加最終整合任務
        final = data.get("final_task", {})
        if final:
            final_task = Task(
                id=f"{task.id}-final",
                query=final.get("query", f"整合 {task.query} 的研究結果"),
                priority=1,  # 最高優先級
                parent_id=task.id,
                dependencies=[f"{task.id}-{d}" for d in final.get("dependencies", [])],
                metadata={"type": "synthesize"}
            )
            subtasks.append(final_task)

        return subtasks


# =============================================================================
# 核心調度器
# =============================================================================

class Dispatcher:
    """
    核心調度器

    負責任務的接收、分解、調度和監控
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        max_concurrent: int = 5,
        task_timeout: float = 300.0,
        verbose: bool = True
    ):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model
        self.max_concurrent = max_concurrent
        self.task_timeout = task_timeout
        self.verbose = verbose

        # 組件
        self.executor = TaskExecutor(self.client, model)
        self.decomposer = TaskDecomposer(self.client, model)
        self.event_bus = EventBus()

        # 狀態
        self.tasks: dict[str, Task] = {}
        self.dependency_graph = DependencyGraph()
        self.completed_tasks: set[str] = set()
        self.failed_tasks: set[str] = set()

        # 並發控制
        self.semaphore = asyncio.Semaphore(max_concurrent)

        # 統計
        self.stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "total_retries": 0,
            "start_time": None,
            "end_time": None
        }

        # 設置事件處理
        self._setup_event_handlers()

    def _setup_event_handlers(self):
        """設置事件處理器"""
        self.event_bus.subscribe(
            TaskEvent.COMPLETED,
            lambda data: self._log(f"✅ 任務完成：{data['task_id']}")
        )
        self.event_bus.subscribe(
            TaskEvent.FAILED,
            lambda data: self._log(f"❌ 任務失敗：{data['task_id']} - {data.get('error', 'Unknown')}")
        )
        self.event_bus.subscribe(
            TaskEvent.RETRYING,
            lambda data: self._log(f"🔄 重試任務：{data['task_id']} (第 {data['retry_count']} 次)")
        )

    async def run(self, query: str) -> dict:
        """
        執行研究任務

        Args:
            query: 研究問題

        Returns:
            研究結果字典
        """
        self.stats["start_time"] = datetime.now()

        self._log(f"\n{'='*60}")
        self._log(f"🚀 開始調度：{query}")
        self._log(f"{'='*60}\n")

        try:
            # 1. 創建根任務
            root_task = Task(query=query)
            self.tasks[root_task.id] = root_task
            self.stats["total_tasks"] += 1

            # 2. 任務分解
            await self._plan_task(root_task)

            # 3. 執行任務
            await self._execute_all()

            # 4. 收集結果
            result = self._collect_results(root_task.id)

            self.stats["end_time"] = datetime.now()

            self._log(f"\n{'='*60}")
            self._log(f"✅ 調度完成")
            self._log(self._format_stats())
            self._log(f"{'='*60}\n")

            return result

        except Exception as e:
            self._log(f"❌ 調度失敗：{e}")
            raise

    async def _plan_task(self, task: Task):
        """規劃任務"""
        task.state = TaskState.PLANNING
        self._log(f"📋 規劃任務：{task.query[:50]}...")

        # 分解任務
        subtasks = await self.decomposer.decompose(task)

        if not subtasks:
            # 不需要分解，直接執行
            self.dependency_graph.add_task(task.id, [])
            task.state = TaskState.READY
            return

        # 添加子任務
        for subtask in subtasks:
            self.tasks[subtask.id] = subtask
            self.stats["total_tasks"] += 1
            self.dependency_graph.add_task(subtask.id, subtask.dependencies)
            task.children.append(subtask.id)

        self._log(f"   📊 分解為 {len(subtasks)} 個子任務")

        # 打印執行順序
        order = self.dependency_graph.get_execution_order()
        self._log(f"   📝 執行順序：{' → '.join(order)}")

        task.state = TaskState.WAITING

    async def _execute_all(self):
        """執行所有任務"""
        self._log("\n📍 開始執行任務")

        while True:
            # 獲取可執行的任務
            ready = self.dependency_graph.get_ready_tasks(self.completed_tasks)
            ready = [tid for tid in ready if tid not in self.failed_tasks]

            if not ready:
                # 檢查是否還有未完成的任務
                pending = set(self.dependency_graph.nodes.keys()) - self.completed_tasks - self.failed_tasks
                if not pending:
                    break
                # 有任務但無法執行（可能是依賴失敗）
                self._log("⚠️ 部分任務因依賴失敗而無法執行")
                break

            # 並行執行
            await self._execute_batch(ready)

    async def _execute_batch(self, task_ids: list[str]):
        """批次執行任務"""
        self._log(f"\n   🔄 並行執行 {len(task_ids)} 個任務")

        async def execute_single(task_id: str):
            async with self.semaphore:
                return await self._execute_task(task_id)

        results = await asyncio.gather(
            *[execute_single(tid) for tid in task_ids],
            return_exceptions=True
        )

        for task_id, result in zip(task_ids, results):
            if isinstance(result, Exception):
                self._log(f"      ❌ {task_id}: {result}")
            else:
                self._log(f"      ✅ {task_id}: 完成")

    async def _execute_task(self, task_id: str) -> dict:
        """執行單個任務"""
        task = self.tasks[task_id]
        task.state = TaskState.RUNNING
        task.started_at = datetime.now()

        # 收集依賴任務的結果
        if task.dependencies:
            parent_results = []
            for dep_id in task.dependencies:
                if dep_id in self.tasks:
                    dep_result = self.tasks[dep_id].result
                    if dep_result:
                        parent_results.append(dep_result)
            task.metadata["parent_results"] = parent_results

        try:
            # 執行任務
            result = await asyncio.wait_for(
                self.executor.execute(task),
                timeout=self.task_timeout
            )

            task.result = result
            task.state = TaskState.COMPLETED
            task.completed_at = datetime.now()
            self.completed_tasks.add(task_id)
            self.stats["completed_tasks"] += 1

            self.event_bus.publish(TaskEvent.COMPLETED, {"task_id": task_id})

            return result

        except asyncio.TimeoutError:
            return await self._handle_task_failure(task, "Task timeout")

        except Exception as e:
            return await self._handle_task_failure(task, str(e))

    async def _handle_task_failure(self, task: Task, error: str) -> dict:
        """處理任務失敗"""
        task.error = error
        task.retry_count += 1
        self.stats["total_retries"] += 1

        if task.retry_count <= task.max_retries:
            # 重試
            self.event_bus.publish(TaskEvent.RETRYING, {
                "task_id": task.id,
                "retry_count": task.retry_count,
                "error": error
            })

            # 指數退避
            await asyncio.sleep(2 ** task.retry_count)

            return await self._execute_task(task.id)

        else:
            # 標記失敗
            task.state = TaskState.FAILED
            self.failed_tasks.add(task.id)
            self.stats["failed_tasks"] += 1

            self.event_bus.publish(TaskEvent.FAILED, {
                "task_id": task.id,
                "error": error
            })

            return {"error": error}

    def _collect_results(self, root_task_id: str) -> dict:
        """收集結果"""
        root_task = self.tasks[root_task_id]

        # 找到最終任務
        final_task_id = f"{root_task_id}-final"
        if final_task_id in self.tasks:
            final_task = self.tasks[final_task_id]
            if final_task.result:
                return {
                    "success": True,
                    "content": final_task.result.get("content", ""),
                    "subtask_count": len(root_task.children),
                    "stats": self.stats
                }

        # 如果沒有最終任務，收集所有子任務結果
        contents = []
        for child_id in root_task.children:
            if child_id in self.tasks:
                child = self.tasks[child_id]
                if child.result:
                    contents.append(child.result.get("content", ""))

        return {
            "success": len(self.failed_tasks) == 0,
            "content": "\n\n---\n\n".join(contents) if contents else "No results",
            "subtask_count": len(root_task.children),
            "stats": self.stats
        }

    def _format_stats(self) -> str:
        """格式化統計資訊"""
        duration = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()

        return f"""
   📊 執行統計
   ├── 總任務數：{self.stats['total_tasks']}
   ├── 完成任務：{self.stats['completed_tasks']}
   ├── 失敗任務：{self.stats['failed_tasks']}
   ├── 總重試次數：{self.stats['total_retries']}
   └── 總耗時：{duration:.1f} 秒"""

    def _log(self, message: str):
        """輸出日誌"""
        if self.verbose:
            print(message)


# =============================================================================
# 主程式
# =============================================================================

async def main():
    """主程式"""
    import argparse

    parser = argparse.ArgumentParser(description="深度研究調度器")
    parser.add_argument("-q", "--query", type=str, help="研究問題")
    parser.add_argument("--model", default="gpt-4o-mini", help="使用的模型")
    parser.add_argument("--max-concurrent", type=int, default=5, help="最大並發數")
    parser.add_argument("-o", "--output", type=str, help="輸出檔案")

    args = parser.parse_args()

    if not os.getenv("OPENAI_API_KEY"):
        print("❌ 請設定 OPENAI_API_KEY 環境變數")
        return

    dispatcher = Dispatcher(
        model=args.model,
        max_concurrent=args.max_concurrent,
        verbose=True
    )

    query = args.query or "分析 2024 年全球 AI 晶片市場格局，包括主要玩家和技術趨勢"

    result = await dispatcher.run(query)

    print("\n" + "="*60)
    print("📄 研究報告")
    print("="*60)
    print(result.get("content", "No content"))

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(result.get("content", ""))
        print(f"\n📄 報告已保存至：{args.output}")


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 4.6 進階：分散式調度考量

當研究任務規模擴大，單一調度器可能成為瓶頸。這時需要考慮分散式架構。

### 4.6.1 多節點協調

```
┌──────────────────────────────────────────────────────────────────┐
│                    分散式調度架構                                 │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│                    ┌─────────────────┐                          │
│                    │  協調者節點     │                          │
│                    │  (Coordinator)  │                          │
│                    └────────┬────────┘                          │
│                             │                                    │
│            ┌────────────────┼────────────────┐                  │
│            ▼                ▼                ▼                  │
│     ┌────────────┐  ┌────────────┐  ┌────────────┐             │
│     │ 調度節點 1 │  │ 調度節點 2 │  │ 調度節點 3 │             │
│     │ (搜尋專用) │  │ (分析專用) │  │ (綜合專用) │             │
│     └─────┬──────┘  └─────┬──────┘  └─────┬──────┘             │
│           │               │               │                      │
│     ┌─────┴─────┐   ┌─────┴─────┐   ┌─────┴─────┐              │
│     │ Worker ×N │   │ Worker ×N │   │ Worker ×N │              │
│     └───────────┘   └───────────┘   └───────────┘              │
│                                                                  │
│                    ┌─────────────────┐                          │
│                    │   共享狀態庫    │                          │
│                    │ (Redis/etcd)   │                          │
│                    └─────────────────┘                          │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 4.6.2 負載平衡策略

```python
from enum import Enum

class LoadBalancingStrategy(Enum):
    ROUND_ROBIN = "round_robin"     # 輪詢
    LEAST_LOADED = "least_loaded"   # 最少負載
    TASK_AFFINITY = "task_affinity" # 任務親和性
    RANDOM = "random"               # 隨機


class LoadBalancer:
    """負載平衡器"""

    def __init__(self, strategy: LoadBalancingStrategy = LoadBalancingStrategy.LEAST_LOADED):
        self.strategy = strategy
        self.nodes: list[str] = []
        self.node_loads: dict[str, int] = {}
        self.task_affinity: dict[str, str] = {}  # task_type -> preferred_node
        self._rr_index = 0

    def select_node(self, task: Task) -> str:
        """選擇節點"""
        if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return self._round_robin()
        elif self.strategy == LoadBalancingStrategy.LEAST_LOADED:
            return self._least_loaded()
        elif self.strategy == LoadBalancingStrategy.TASK_AFFINITY:
            return self._task_affinity(task)
        else:
            import random
            return random.choice(self.nodes)

    def _round_robin(self) -> str:
        node = self.nodes[self._rr_index]
        self._rr_index = (self._rr_index + 1) % len(self.nodes)
        return node

    def _least_loaded(self) -> str:
        return min(self.nodes, key=lambda n: self.node_loads.get(n, 0))

    def _task_affinity(self, task: Task) -> str:
        task_type = task.metadata.get("type", "default")
        if task_type in self.task_affinity:
            return self.task_affinity[task_type]
        return self._least_loaded()
```

### 4.6.3 一致性保證

分散式環境中的一致性挑戰：

| 挑戰 | 解決方案 |
|------|----------|
| 任務狀態同步 | 使用分散式鎖（Redis Lock） |
| 重複執行 | 冪等性設計 + 任務 ID 去重 |
| 順序保證 | 分散式事務或事件溯源 |
| 故障恢復 | 心跳檢測 + 任務接管 |

---

## 4.7 章節總結

本章深入探討了調度器的設計與實現。

### 核心概念回顧

1. **調度器職責**：任務接收、分解、資源分配、執行監控、結果整合

2. **狀態機設計**：PENDING → PLANNING → RUNNING → COMPLETED/FAILED

3. **任務分解**：MECE 原則、粒度控制、依賴識別

4. **依賴圖**：拓撲排序、就緒任務識別、動態重規劃

5. **執行策略**：同步/異步、並發控制、超時重試

6. **事件驅動**：鬆散耦合、可觀測性

### 學習檢查清單

- [ ] 理解調度器在代理人系統中的角色
- [ ] 掌握任務狀態機的設計
- [ ] 能夠實現依賴圖和拓撲排序
- [ ] 理解 MECE 分解原則
- [ ] 掌握並發執行和錯誤處理
- [ ] 完成 `dispatcher.py` 的運行

### 下一章預告

在第 5 章「工具調用與軌跡收集」中，我們將深入 MiroThinker 的工具系統，學習：

- 工具描述的設計模式
- 如何建立工具註冊機制
- 執行軌跡的收集與存儲
- 強化學習（RLEF）的基礎

從調度器的高層設計，我們將進入工具調用的實現細節。

---

## 本章程式碼清單

| 檔案 | 行數 | 說明 |
|------|------|------|
| `dispatcher.py` | ~550 | 完整的調度器實現 |
| `requirements.txt` | ~15 | Python 依賴清單 |
| `.env.example` | ~10 | 環境變數範例 |
| `README.md` | ~200 | 使用說明 |

**GitHub 位置**：`code-examples/chapter-04/`
