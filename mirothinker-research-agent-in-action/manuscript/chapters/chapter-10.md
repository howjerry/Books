# 第 10 章：多代理人協作系統

> **本章目標**：建構一套多代理人協作系統，讓多個專業代理人各司其職、協同完成複雜研究任務。

---

## 引言：當一個代理人不夠用時

在第 9 章，我們成功建構了一個功能完整的深度研究代理人。它能夠理解問題、規劃搜尋策略、收集資訊、分析整合，最終產出高品質的研究報告。但當你開始處理更複雜的研究任務時，你會發現一個問題：

**單一代理人的能力終究有限。**

想像這樣一個場景：你的客戶是一家投資公司，他們想要深入分析「全球半導體產業在 AI 時代的競爭格局」。這個研究需要：

- **產業分析師**：分析市場規模、成長趨勢、競爭態勢
- **技術專家**：評估各家公司的技術實力與專利布局
- **財務分析師**：解讀財報數據、估值模型、投資風險
- **地緣政治顧問**：分析政策影響、供應鏈風險、國際關係

讓一個代理人同時扮演這四種角色？那就像要求一個人同時是產業分析師、半導體工程師、會計師和國際關係專家——理論上可能，但實際上很難做到頂尖水準。

**解決方案：多代理人協作系統。**

```
                    ┌──────────────────┐
                    │   協調器代理人    │
                    │   (Coordinator)   │
                    └────────┬─────────┘
                             │
           ┌─────────────────┼─────────────────┐
           │                 │                 │
           ▼                 ▼                 ▼
    ┌────────────┐    ┌────────────┐    ┌────────────┐
    │ 產業分析師  │    │  技術專家   │    │ 財務分析師  │
    │   Agent    │    │   Agent    │    │   Agent    │
    └────────────┘    └────────────┘    └────────────┘
           │                 │                 │
           └─────────────────┴─────────────────┘
                             │
                    ┌────────▼────────┐
                    │   整合與報告     │
                    └─────────────────┘
```

本章將帶你建構這樣一套系統。完成本章後，你將擁有：

1. **協調器代理人**：負責任務分解、分配、監控與整合
2. **專家代理人模板**：可快速建立各類專業代理人
3. **通訊協議**：代理人間高效傳遞資訊的機制
4. **衝突解決策略**：當專家意見相左時的處理方法
5. **完整的多專家研究系統**：端到端可運行的範例

讓我們開始吧。

---

## 10.1 多代理人架構的設計哲學

在深入程式碼之前，我們需要先理解多代理人系統的核心設計理念。

### 10.1.1 為何需要多代理人？

**單一代理人的局限性：**

| 局限性 | 說明 |
|--------|------|
| **上下文限制** | 即使有 256K context window，處理多領域深度研究仍會捉襟見肘 |
| **專業深度不足** | 一個代理人難以同時精通多個專業領域 |
| **推理負擔過重** | 複雜任務導致推理鏈過長，容易出錯 |
| **難以平行化** | 單一代理人只能順序執行，效率低下 |

**多代理人的優勢：**

| 優勢 | 說明 |
|------|------|
| **專業分工** | 每個代理人專注於一個領域，深度更佳 |
| **上下文隔離** | 每個代理人有獨立上下文，互不干擾 |
| **平行執行** | 多個代理人可同時工作，效率倍增 |
| **模組化擴展** | 需要新專業？加一個代理人即可 |

### 10.1.2 經典的多代理人模式

在實務中，多代理人系統主要有三種經典模式：

**模式一：層級式（Hierarchical）**

```
                    ┌─────────────┐
                    │  Coordinator │
                    └──────┬──────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
    ┌────▼────┐      ┌────▼────┐      ┌────▼────┐
    │ Worker A │      │ Worker B │      │ Worker C │
    └─────────┘      └─────────┘      └─────────┘
```

- **特點**：明確的層級關係，協調器指揮工作者
- **優點**：控制流清晰，易於追蹤
- **缺點**：協調器可能成為瓶頸
- **適用場景**：結構化研究任務

**模式二：對等式（Peer-to-Peer）**

```
    ┌─────────┐         ┌─────────┐
    │ Agent A │ ◀─────▶ │ Agent B │
    └────┬────┘         └────┬────┘
         │                   │
         │    ┌─────────┐    │
         └───▶│ Agent C │◀───┘
              └─────────┘
```

- **特點**：代理人間直接通訊，無中央協調
- **優點**：靈活性高，無單點故障
- **缺點**：通訊複雜度高，難以追蹤
- **適用場景**：開放式探索、辯論式研究

**模式三：混合式（Hybrid）**

```
                    ┌─────────────┐
                    │  Coordinator │
                    └──────┬──────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
    ┌────▼────┐      ┌────▼────┐      ┌────▼────┐
    │ Team A  │      │ Team B  │      │ Team C  │
    └────┬────┘      └─────────┘      └─────────┘
         │
    ┌────┴────┐
    │Sub Agent│
    └─────────┘
```

- **特點**：結合層級式與對等式，團隊內部可自主協作
- **優點**：兼顧控制與靈活
- **缺點**：設計複雜度較高
- **適用場景**：大型複雜研究專案

**本章選擇：層級式模式**

對於深度研究任務，層級式模式是最佳選擇：

1. 研究任務通常有明確的分解結構
2. 需要統一的品質控制與結果整合
3. 易於監控進度與處理錯誤
4. 便於擴展新的專家代理人

### 10.1.3 設計原則

建構多代理人系統時，請牢記以下原則：

**原則 1：單一職責**

每個代理人只負責一件事，做到極致。

```python
# ✅ 好的設計
class FinancialAnalystAgent:
    """專注於財務分析"""
    def analyze_financials(self, company: str) -> FinancialReport:
        ...

# ❌ 不好的設計
class SuperAgent:
    """什麼都做"""
    def do_everything(self, task: str) -> str:
        ...
```

**原則 2：最小知識**

代理人只需知道完成任務所需的最少資訊。

```python
# ✅ 好的設計：只傳遞必要資訊
await analyst.analyze(
    company="NVIDIA",
    focus_areas=["GPU revenue", "Data center growth"]
)

# ❌ 不好的設計：傳遞整個研究上下文
await analyst.analyze(entire_research_context)
```

**原則 3：清晰介面**

代理人間通訊使用結構化的資料格式。

```python
@dataclass
class AgentMessage:
    sender: str
    receiver: str
    message_type: MessageType
    content: Dict[str, Any]
    timestamp: datetime
```

**原則 4：失敗隔離**

一個代理人的失敗不應拖垮整個系統。

```python
try:
    result = await agent.execute(task)
except AgentError as e:
    result = FallbackResult(
        status="partial",
        message=f"Agent {agent.name} failed: {e}"
    )
```

---

## 10.2 協調器代理人：指揮中心

協調器（Coordinator）是多代理人系統的核心，負責：

1. **任務分解**：將複雜研究任務分解為子任務
2. **代理人分配**：決定由哪個專家處理哪個子任務
3. **進度監控**：追蹤各代理人的執行狀態
4. **結果整合**：彙總各專家的分析結果
5. **品質控制**：確保最終報告的品質

### 10.2.1 協調器的核心結構

```python
#!/usr/bin/env python3
"""
深度研究代理人實戰 - 第 10 章：多代理人協作系統
協調器代理人

這個模組實現了多代理人系統的核心協調器：
1. 任務分解與規劃
2. 專家代理人管理
3. 平行執行與結果整合
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
import json

from dotenv import load_dotenv

load_dotenv()


# =============================================================================
# 資料結構
# =============================================================================

class TaskStatus(Enum):
    """任務狀態"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MessageType(Enum):
    """訊息類型"""
    TASK_ASSIGNMENT = "task_assignment"
    STATUS_UPDATE = "status_update"
    RESULT_REPORT = "result_report"
    ERROR_REPORT = "error_report"
    COORDINATION = "coordination"


@dataclass
class SubTask:
    """
    子任務

    ‹1› 表示一個可分配給專家代理人的工作單元
    ‹2› 包含任務描述、所需專業、依賴關係
    """
    task_id: str                          # ‹1› 唯一識別符
    description: str                      # ‹2› 任務描述
    required_expertise: str               # ‹3› 所需專業領域
    dependencies: List[str] = field(default_factory=list)  # ‹4› 依賴的任務 ID
    priority: int = 1                     # ‹5› 優先級（1-5，5 最高）
    status: TaskStatus = TaskStatus.PENDING
    assigned_agent: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


@dataclass
class AgentMessage:
    """
    代理人間訊息

    統一的通訊格式，確保代理人間資訊傳遞的一致性
    """
    message_id: str
    sender: str
    receiver: str
    message_type: MessageType
    content: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: Optional[str] = None  # 用於追蹤相關訊息


@dataclass
class CoordinationResult:
    """
    協調結果

    協調器的最終輸出，包含所有專家分析的整合結果
    """
    research_question: str
    subtasks: List[SubTask]
    expert_reports: Dict[str, Dict[str, Any]]
    integrated_summary: str
    key_insights: List[str]
    conflicts: List[Dict[str, Any]]
    confidence_score: float
    total_duration: float
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# 專家代理人基類
# =============================================================================

class ExpertAgent:
    """
    專家代理人基類

    ‹1› 定義專家代理人的標準介面
    ‹2› 子類需實現 analyze() 方法
    """

    def __init__(
        self,
        name: str,
        expertise: str,
        description: str,
        llm_client=None
    ):
        self.name = name                  # ‹1› 代理人名稱
        self.expertise = expertise        # ‹2› 專業領域
        self.description = description    # ‹3› 代理人描述
        self.llm = llm_client            # ‹4› LLM 客戶端
        self.is_busy = False
        self.current_task: Optional[str] = None

    async def analyze(self, task: SubTask, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        執行分析任務

        ‹1› 子類必須實現此方法
        ‹2› 返回結構化的分析結果
        """
        raise NotImplementedError("Subclasses must implement analyze()")

    def get_system_prompt(self) -> str:
        """獲取代理人的系統提示"""
        return f"""你是一位專業的{self.expertise}專家，名為「{self.name}」。

{self.description}

你的職責是：
1. 針對指派的任務進行深入分析
2. 基於專業知識提供洞察
3. 明確標註資訊來源與可信度
4. 指出分析中的不確定性

請以結構化的方式呈現你的分析結果。"""

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "name": self.name,
            "expertise": self.expertise,
            "description": self.description,
            "is_busy": self.is_busy,
            "current_task": self.current_task
        }


# =============================================================================
# 專業代理人實現
# =============================================================================

class IndustryAnalystAgent(ExpertAgent):
    """
    產業分析師代理人

    專注於市場規模、成長趨勢、競爭格局分析
    """

    def __init__(self, llm_client=None):
        super().__init__(
            name="產業分析師",
            expertise="產業分析",
            description="""專注於分析產業動態：
- 市場規模與成長率
- 競爭格局與市佔率
- 產業趨勢與驅動力
- 進入障礙與風險因素""",
            llm_client=llm_client
        )

    async def analyze(self, task: SubTask, context: Dict[str, Any]) -> Dict[str, Any]:
        """執行產業分析"""
        self.is_busy = True
        self.current_task = task.task_id

        try:
            # 模擬產業分析過程
            await asyncio.sleep(0.5)  # 模擬思考時間

            # 在實際應用中，這裡會：
            # 1. 呼叫 LLM 進行分析
            # 2. 搜尋產業報告
            # 3. 整合市場數據

            result = {
                "analysis_type": "industry_analysis",
                "task_id": task.task_id,
                "findings": {
                    "market_overview": f"針對「{task.description}」的產業分析...",
                    "market_size": "全球市場規模預估...",
                    "growth_trends": ["趨勢1", "趨勢2", "趨勢3"],
                    "competitive_landscape": {
                        "major_players": ["公司A", "公司B", "公司C"],
                        "market_shares": {"公司A": 0.35, "公司B": 0.25, "公司C": 0.15}
                    }
                },
                "confidence": 0.8,
                "sources": ["產業報告", "市場研究"],
                "limitations": ["數據可能有 6 個月滯後"]
            }

            return result

        finally:
            self.is_busy = False
            self.current_task = None


class TechExpertAgent(ExpertAgent):
    """
    技術專家代理人

    專注於技術評估、專利分析、研發能力評估
    """

    def __init__(self, llm_client=None):
        super().__init__(
            name="技術專家",
            expertise="技術分析",
            description="""專注於評估技術實力：
- 核心技術與創新能力
- 專利布局與知識產權
- 研發投入與產出
- 技術路線圖分析""",
            llm_client=llm_client
        )

    async def analyze(self, task: SubTask, context: Dict[str, Any]) -> Dict[str, Any]:
        """執行技術分析"""
        self.is_busy = True
        self.current_task = task.task_id

        try:
            await asyncio.sleep(0.5)

            result = {
                "analysis_type": "technology_analysis",
                "task_id": task.task_id,
                "findings": {
                    "tech_overview": f"針對「{task.description}」的技術分析...",
                    "core_technologies": ["技術A", "技術B"],
                    "patent_analysis": {
                        "total_patents": 1500,
                        "key_areas": ["AI晶片", "製程技術"]
                    },
                    "r_and_d": {
                        "investment": "研發投入佔營收 20%",
                        "key_projects": ["專案1", "專案2"]
                    }
                },
                "confidence": 0.75,
                "sources": ["專利資料庫", "技術白皮書"],
                "limitations": ["部分專利資訊可能不完整"]
            }

            return result

        finally:
            self.is_busy = False
            self.current_task = None


class FinancialAnalystAgent(ExpertAgent):
    """
    財務分析師代理人

    專注於財報分析、估值評估、投資風險
    """

    def __init__(self, llm_client=None):
        super().__init__(
            name="財務分析師",
            expertise="財務分析",
            description="""專注於財務評估：
- 財務報表分析
- 獲利能力與成長性
- 估值模型與目標價
- 財務風險與流動性""",
            llm_client=llm_client
        )

    async def analyze(self, task: SubTask, context: Dict[str, Any]) -> Dict[str, Any]:
        """執行財務分析"""
        self.is_busy = True
        self.current_task = task.task_id

        try:
            await asyncio.sleep(0.5)

            result = {
                "analysis_type": "financial_analysis",
                "task_id": task.task_id,
                "findings": {
                    "financial_overview": f"針對「{task.description}」的財務分析...",
                    "revenue": {
                        "latest": "$26.0B",
                        "yoy_growth": "122%"
                    },
                    "profitability": {
                        "gross_margin": "72.7%",
                        "net_margin": "48.8%"
                    },
                    "valuation": {
                        "pe_ratio": 65.2,
                        "ps_ratio": 30.5
                    }
                },
                "confidence": 0.85,
                "sources": ["SEC 財報", "分析師報告"],
                "limitations": ["使用最近一季數據"]
            }

            return result

        finally:
            self.is_busy = False
            self.current_task = None


class GeopoliticalAdvisorAgent(ExpertAgent):
    """
    地緣政治顧問代理人

    專注於政策影響、供應鏈風險、國際關係
    """

    def __init__(self, llm_client=None):
        super().__init__(
            name="地緣政治顧問",
            expertise="地緣政治分析",
            description="""專注於地緣政治風險：
- 貿易政策與關稅影響
- 供應鏈地緣風險
- 國際關係與制裁
- 區域穩定性評估""",
            llm_client=llm_client
        )

    async def analyze(self, task: SubTask, context: Dict[str, Any]) -> Dict[str, Any]:
        """執行地緣政治分析"""
        self.is_busy = True
        self.current_task = task.task_id

        try:
            await asyncio.sleep(0.5)

            result = {
                "analysis_type": "geopolitical_analysis",
                "task_id": task.task_id,
                "findings": {
                    "geopolitical_overview": f"針對「{task.description}」的地緣政治分析...",
                    "policy_risks": [
                        "美國出口管制加嚴",
                        "中國技術自主政策"
                    ],
                    "supply_chain_risks": {
                        "taiwan_concentration": "高風險",
                        "rare_earth_dependency": "中等風險"
                    },
                    "international_dynamics": {
                        "us_china_relations": "緊張",
                        "trade_barriers": "上升中"
                    }
                },
                "confidence": 0.7,
                "sources": ["政策分析", "智庫報告"],
                "limitations": ["地緣政治情勢變化快速"]
            }

            return result

        finally:
            self.is_busy = False
            self.current_task = None


# =============================================================================
# 協調器
# =============================================================================

class ResearchCoordinator:
    """
    研究協調器

    ‹1› 管理多個專家代理人
    ‹2› 分解任務並分配執行
    ‹3› 整合結果並生成報告
    """

    def __init__(self, llm_client=None):
        self.llm = llm_client
        self.agents: Dict[str, ExpertAgent] = {}
        self.tasks: Dict[str, SubTask] = {}
        self.messages: List[AgentMessage] = []
        self._message_counter = 0

        # ‹1› 註冊預設專家代理人
        self._register_default_agents()

    def _register_default_agents(self):
        """註冊預設的專家代理人"""
        self.register_agent(IndustryAnalystAgent(self.llm))
        self.register_agent(TechExpertAgent(self.llm))
        self.register_agent(FinancialAnalystAgent(self.llm))
        self.register_agent(GeopoliticalAdvisorAgent(self.llm))

    def register_agent(self, agent: ExpertAgent):
        """
        註冊專家代理人

        ‹1› 將代理人加入可用池
        ‹2› 使用專業領域作為鍵值
        """
        self.agents[agent.expertise] = agent
        print(f"✓ 已註冊代理人: {agent.name} ({agent.expertise})")

    def unregister_agent(self, expertise: str) -> bool:
        """移除代理人"""
        if expertise in self.agents:
            del self.agents[expertise]
            return True
        return False

    def list_agents(self) -> List[Dict[str, Any]]:
        """列出所有代理人"""
        return [agent.to_dict() for agent in self.agents.values()]

    async def decompose_task(self, research_question: str) -> List[SubTask]:
        """
        任務分解

        ‹1› 分析研究問題
        ‹2› 識別所需專業領域
        ‹3› 建立子任務清單
        """
        # 在實際應用中，這裡會使用 LLM 進行智能分解
        # 這裡使用規則為基礎的分解作為示範

        subtasks = []
        task_id_counter = 0

        # ‹1› 產業分析任務
        subtasks.append(SubTask(
            task_id=f"task_{task_id_counter:03d}",
            description=f"分析「{research_question}」相關的產業動態與競爭格局",
            required_expertise="產業分析",
            priority=5
        ))
        task_id_counter += 1

        # ‹2› 技術分析任務
        subtasks.append(SubTask(
            task_id=f"task_{task_id_counter:03d}",
            description=f"評估「{research_question}」涉及的核心技術與創新能力",
            required_expertise="技術分析",
            priority=4
        ))
        task_id_counter += 1

        # ‹3› 財務分析任務（依賴產業分析）
        subtasks.append(SubTask(
            task_id=f"task_{task_id_counter:03d}",
            description=f"分析「{research_question}」相關公司的財務狀況與估值",
            required_expertise="財務分析",
            dependencies=["task_000"],  # 依賴產業分析的結果
            priority=4
        ))
        task_id_counter += 1

        # ‹4› 地緣政治分析任務
        subtasks.append(SubTask(
            task_id=f"task_{task_id_counter:03d}",
            description=f"評估「{research_question}」的地緣政治風險與政策影響",
            required_expertise="地緣政治分析",
            priority=3
        ))

        return subtasks

    def _find_agent_for_task(self, task: SubTask) -> Optional[ExpertAgent]:
        """根據任務找到合適的代理人"""
        return self.agents.get(task.required_expertise)

    def _check_dependencies(self, task: SubTask) -> bool:
        """檢查任務依賴是否滿足"""
        for dep_id in task.dependencies:
            dep_task = self.tasks.get(dep_id)
            if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                return False
        return True

    def _get_dependency_results(self, task: SubTask) -> Dict[str, Any]:
        """獲取依賴任務的結果"""
        results = {}
        for dep_id in task.dependencies:
            dep_task = self.tasks.get(dep_id)
            if dep_task and dep_task.result:
                results[dep_id] = dep_task.result
        return results

    async def execute_task(self, task: SubTask) -> SubTask:
        """
        執行單一任務

        ‹1› 找到合適的代理人
        ‹2› 檢查依賴
        ‹3› 分配並執行
        """
        # ‹1› 更新任務狀態
        task.status = TaskStatus.RUNNING
        self.tasks[task.task_id] = task

        # ‹2› 找到合適的代理人
        agent = self._find_agent_for_task(task)
        if not agent:
            task.status = TaskStatus.FAILED
            task.error = f"找不到具備「{task.required_expertise}」專業的代理人"
            return task

        # ‹3› 檢查依賴
        if not self._check_dependencies(task):
            task.status = TaskStatus.PENDING
            task.error = "依賴任務尚未完成"
            return task

        # ‹4› 準備上下文
        context = {
            "research_context": "多代理人協作研究",
            "dependencies": self._get_dependency_results(task)
        }

        # ‹5› 執行分析
        try:
            task.assigned_agent = agent.name
            result = await agent.analyze(task, context)
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()

            # 發送完成訊息
            self._send_message(
                sender="coordinator",
                receiver=agent.name,
                message_type=MessageType.STATUS_UPDATE,
                content={"task_id": task.task_id, "status": "completed"}
            )

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)

        return task

    async def coordinate(self, research_question: str) -> CoordinationResult:
        """
        執行完整的協調流程

        ‹1› 分解任務
        ‹2› 分配代理人
        ‹3› 平行執行（考慮依賴）
        ‹4› 整合結果
        """
        start_time = datetime.now()

        print(f"\n{'='*60}")
        print(f"🔬 開始多代理人協作研究")
        print(f"{'='*60}")
        print(f"研究問題: {research_question}\n")

        # ‹1› 任務分解
        print("📋 步驟 1: 任務分解")
        subtasks = await self.decompose_task(research_question)
        for task in subtasks:
            self.tasks[task.task_id] = task
            print(f"  - {task.task_id}: {task.required_expertise}")

        # ‹2› 執行策略：先執行無依賴任務，再執行有依賴任務
        print("\n⚡ 步驟 2: 平行執行任務")

        # 分離無依賴與有依賴任務
        independent_tasks = [t for t in subtasks if not t.dependencies]
        dependent_tasks = [t for t in subtasks if t.dependencies]

        # 平行執行無依賴任務
        print("  執行無依賴任務...")
        independent_results = await asyncio.gather(
            *[self.execute_task(task) for task in independent_tasks],
            return_exceptions=True
        )

        # 順序執行有依賴任務
        print("  執行有依賴任務...")
        for task in dependent_tasks:
            await self.execute_task(task)

        # ‹3› 收集結果
        print("\n📊 步驟 3: 整合結果")
        expert_reports = {}
        for task_id, task in self.tasks.items():
            if task.result:
                expert_reports[task_id] = task.result

        # ‹4› 生成整合摘要
        integrated_summary, key_insights = await self._integrate_results(
            research_question, expert_reports
        )

        # ‹5› 檢測衝突
        conflicts = self._detect_conflicts(expert_reports)

        # ‹6› 計算整體信心分數
        confidence_scores = [
            r.get("confidence", 0.5)
            for r in expert_reports.values()
        ]
        overall_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0

        # 計算總時長
        duration = (datetime.now() - start_time).total_seconds()

        print(f"\n✅ 協調完成，耗時 {duration:.2f} 秒")

        return CoordinationResult(
            research_question=research_question,
            subtasks=list(self.tasks.values()),
            expert_reports=expert_reports,
            integrated_summary=integrated_summary,
            key_insights=key_insights,
            conflicts=conflicts,
            confidence_score=overall_confidence,
            total_duration=duration,
            metadata={
                "agents_used": len(expert_reports),
                "tasks_completed": sum(1 for t in self.tasks.values() if t.status == TaskStatus.COMPLETED),
                "tasks_failed": sum(1 for t in self.tasks.values() if t.status == TaskStatus.FAILED)
            }
        )

    async def _integrate_results(
        self,
        question: str,
        reports: Dict[str, Dict[str, Any]]
    ) -> tuple:
        """
        整合各專家的分析結果

        ‹1› 提取關鍵發現
        ‹2› 綜合各方觀點
        ‹3› 生成統一結論
        """
        # 在實際應用中，這裡會使用 LLM 進行智能整合
        # 這裡使用簡化的模板為基礎的整合

        # 提取各專家的關鍵發現
        all_findings = []
        for task_id, report in reports.items():
            findings = report.get("findings", {})
            analysis_type = report.get("analysis_type", "unknown")
            all_findings.append({
                "type": analysis_type,
                "findings": findings
            })

        # 生成整合摘要
        summary = f"""## 研究摘要：{question}

本研究整合了 {len(reports)} 位專家的分析，涵蓋產業、技術、財務與地緣政治等多個維度。

### 主要發現

"""
        for finding in all_findings:
            summary += f"**{finding['type']}**：提供了相關領域的深入分析。\n\n"

        # 提取關鍵洞察
        key_insights = [
            "市場持續成長，但競爭加劇",
            "技術創新是維持競爭優勢的關鍵",
            "財務表現強勁，但估值偏高",
            "地緣政治風險需持續關注"
        ]

        return summary, key_insights

    def _detect_conflicts(self, reports: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        檢測專家意見間的衝突

        ‹1› 比較相似主題的結論
        ‹2› 識別矛盾陳述
        ‹3› 記錄衝突詳情
        """
        conflicts = []

        # 簡化實現：檢查信心分數差異
        confidence_values = []
        for task_id, report in reports.items():
            confidence_values.append({
                "task_id": task_id,
                "confidence": report.get("confidence", 0.5)
            })

        # 如果信心分數差異過大，標記為潛在衝突
        if len(confidence_values) >= 2:
            max_conf = max(c["confidence"] for c in confidence_values)
            min_conf = min(c["confidence"] for c in confidence_values)

            if max_conf - min_conf > 0.3:
                conflicts.append({
                    "type": "confidence_discrepancy",
                    "description": f"專家信心分數差異較大（{min_conf:.0%} - {max_conf:.0%}）",
                    "severity": "low"
                })

        return conflicts

    def _send_message(
        self,
        sender: str,
        receiver: str,
        message_type: MessageType,
        content: Dict[str, Any]
    ):
        """發送代理人間訊息"""
        self._message_counter += 1
        message = AgentMessage(
            message_id=f"msg_{self._message_counter:06d}",
            sender=sender,
            receiver=receiver,
            message_type=message_type,
            content=content
        )
        self.messages.append(message)

    def get_message_log(self) -> List[Dict[str, Any]]:
        """獲取訊息日誌"""
        return [
            {
                "message_id": m.message_id,
                "sender": m.sender,
                "receiver": m.receiver,
                "type": m.message_type.value,
                "timestamp": m.timestamp.isoformat()
            }
            for m in self.messages
        ]


# =============================================================================
# 結果報告器
# =============================================================================

class ReportGenerator:
    """
    報告生成器

    將協調結果轉換為可讀的研究報告
    """

    def generate_markdown(self, result: CoordinationResult) -> str:
        """生成 Markdown 格式報告"""
        lines = [
            f"# 研究報告",
            f"",
            f"**研究問題**: {result.research_question}",
            f"",
            f"**執行時間**: {result.total_duration:.2f} 秒",
            f"",
            f"**整體信心分數**: {result.confidence_score:.0%}",
            f"",
            "---",
            "",
            "## 執行摘要",
            "",
            result.integrated_summary,
            "",
            "## 關鍵洞察",
            ""
        ]

        for i, insight in enumerate(result.key_insights, 1):
            lines.append(f"{i}. {insight}")

        lines.extend([
            "",
            "## 專家分析詳情",
            ""
        ])

        for task_id, report in result.expert_reports.items():
            analysis_type = report.get("analysis_type", "未知")
            confidence = report.get("confidence", 0)
            lines.extend([
                f"### {analysis_type}",
                f"",
                f"**信心分數**: {confidence:.0%}",
                f"",
                f"```json",
                json.dumps(report.get("findings", {}), ensure_ascii=False, indent=2),
                f"```",
                ""
            ])

        if result.conflicts:
            lines.extend([
                "## 衝突與不確定性",
                ""
            ])
            for conflict in result.conflicts:
                lines.append(f"- **{conflict['type']}**: {conflict['description']}")

        lines.extend([
            "",
            "---",
            "",
            f"*報告生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
        ])

        return "\n".join(lines)

    def generate_json(self, result: CoordinationResult) -> str:
        """生成 JSON 格式報告"""
        data = {
            "research_question": result.research_question,
            "summary": result.integrated_summary,
            "key_insights": result.key_insights,
            "confidence_score": result.confidence_score,
            "duration": result.total_duration,
            "expert_reports": result.expert_reports,
            "conflicts": result.conflicts,
            "metadata": result.metadata
        }
        return json.dumps(data, ensure_ascii=False, indent=2)
```

### 10.2.2 協調器的工作流程

讓我們透過流程圖理解協調器的完整工作流程：

```
                        研究問題
                            │
                            ▼
            ┌───────────────────────────────┐
            │        1. 任務分解             │
            │   分析問題 → 識別專業需求 →    │
            │   建立子任務清單                │
            └───────────────┬───────────────┘
                            │
                            ▼
            ┌───────────────────────────────┐
            │        2. 依賴分析             │
            │   識別任務間依賴關係            │
            │   建立執行順序                 │
            └───────────────┬───────────────┘
                            │
          ┌─────────────────┴─────────────────┐
          │                                    │
          ▼                                    ▼
┌─────────────────┐              ┌─────────────────┐
│  無依賴任務     │              │  有依賴任務      │
│  （平行執行）   │              │  （等待依賴）    │
└────────┬────────┘              └────────┬────────┘
         │                                 │
         │      ┌────────────────────┐     │
         └─────▶│    3. 平行執行     │◀────┘
                │  分配給專家代理人   │
                └─────────┬──────────┘
                          │
                          ▼
            ┌───────────────────────────────┐
            │        4. 結果收集             │
            │   收集各專家分析結果            │
            │   檢查執行狀態                 │
            └───────────────┬───────────────┘
                            │
                            ▼
            ┌───────────────────────────────┐
            │        5. 衝突檢測             │
            │   比較各專家結論               │
            │   識別矛盾與不一致              │
            └───────────────┬───────────────┘
                            │
                            ▼
            ┌───────────────────────────────┐
            │        6. 結果整合             │
            │   綜合各方觀點                 │
            │   生成統一結論                 │
            └───────────────┬───────────────┘
                            │
                            ▼
                      研究報告
```

### 10.2.3 任務分解策略

任務分解是協調器最關鍵的能力。好的分解能讓專家代理人發揮最大效用。

**策略 1：按專業領域分解**

```python
def decompose_by_expertise(question: str, available_experts: List[str]) -> List[SubTask]:
    """
    根據可用專家領域進行分解

    每個專家負責其專業領域的分析
    """
    subtasks = []
    for expertise in available_experts:
        subtasks.append(SubTask(
            task_id=f"task_{expertise}",
            description=f"從{expertise}角度分析: {question}",
            required_expertise=expertise
        ))
    return subtasks
```

**策略 2：按研究階段分解**

```python
def decompose_by_phase(question: str) -> List[SubTask]:
    """
    根據研究階段進行分解

    階段 1: 資料收集
    階段 2: 分析評估
    階段 3: 綜合結論
    """
    return [
        SubTask(
            task_id="phase_1_collect",
            description=f"收集「{question}」相關資料",
            required_expertise="資料收集",
            priority=5
        ),
        SubTask(
            task_id="phase_2_analyze",
            description=f"分析收集到的資料",
            required_expertise="資料分析",
            dependencies=["phase_1_collect"],
            priority=4
        ),
        SubTask(
            task_id="phase_3_conclude",
            description=f"綜合分析結果，形成結論",
            required_expertise="報告撰寫",
            dependencies=["phase_2_analyze"],
            priority=3
        )
    ]
```

**策略 3：按問題維度分解（本章採用）**

```python
def decompose_by_dimension(question: str) -> List[SubTask]:
    """
    根據問題涉及的維度進行分解

    適用於需要多角度分析的複雜問題
    """
    dimensions = [
        ("產業分析", "市場規模、競爭格局、成長趨勢"),
        ("技術分析", "核心技術、創新能力、專利布局"),
        ("財務分析", "財報數據、估值評估、投資風險"),
        ("地緣政治分析", "政策影響、供應鏈風險、國際關係")
    ]

    subtasks = []
    for i, (expertise, focus) in enumerate(dimensions):
        subtasks.append(SubTask(
            task_id=f"dim_{i:02d}",
            description=f"從{focus}角度分析「{question}」",
            required_expertise=expertise,
            priority=5 - i  # 產業分析優先
        ))

    return subtasks
```

---

## 10.3 專家代理人：各司其職

專家代理人是多代理人系統的工作主力。每個專家專注於特定領域，提供深度分析。

### 10.3.1 設計高效的專家代理人

建立專家代理人時，需要注意以下要點：

**要點 1：明確的專業定位**

```python
class IndustryAnalystAgent(ExpertAgent):
    """
    產業分析師

    專業領域明確界定，避免與其他代理人重疊
    """

    CORE_CAPABILITIES = [
        "市場規模估算",
        "成長趨勢預測",
        "競爭格局分析",
        "進入障礙評估"
    ]

    # ❌ 避免：財務數據分析（應由財務分析師負責）
    # ❌ 避免：技術評估（應由技術專家負責）
```

**要點 2：結構化的輸出格式**

```python
@dataclass
class IndustryAnalysisOutput:
    """產業分析輸出格式"""
    market_size: MarketSize
    growth_trends: List[Trend]
    competitive_landscape: CompetitiveLandscape
    key_players: List[KeyPlayer]
    barriers_to_entry: List[Barrier]
    risks: List[Risk]
    confidence: float
    sources: List[Source]
    limitations: List[str]
```

**要點 3：自我評估能力**

```python
async def analyze(self, task: SubTask, context: Dict) -> Dict:
    result = await self._do_analysis(task, context)

    # 自我評估可信度
    confidence = self._assess_confidence(result)

    # 標註不確定性
    uncertainties = self._identify_uncertainties(result)

    return {
        **result,
        "confidence": confidence,
        "uncertainties": uncertainties
    }
```

### 10.3.2 專家代理人的通訊協議

專家代理人間的通訊需要標準化的協議。

**訊息結構：**

```python
@dataclass
class AgentMessage:
    """代理人間訊息"""
    message_id: str           # 唯一識別符
    sender: str               # 發送者
    receiver: str             # 接收者
    message_type: MessageType # 訊息類型
    content: Dict[str, Any]   # 訊息內容
    timestamp: datetime       # 時間戳
    correlation_id: str       # 關聯 ID（用於追蹤對話）
```

**訊息類型：**

| 類型 | 用途 | 範例 |
|------|------|------|
| `TASK_ASSIGNMENT` | 分配任務 | 協調器 → 專家 |
| `STATUS_UPDATE` | 更新狀態 | 專家 → 協調器 |
| `RESULT_REPORT` | 報告結果 | 專家 → 協調器 |
| `ERROR_REPORT` | 報告錯誤 | 專家 → 協調器 |
| `COORDINATION` | 協調訊息 | 協調器 → 所有專家 |

**通訊範例：**

```
┌─────────────┐         ┌─────────────┐
│  Coordinator │         │  Analyst    │
└──────┬──────┘         └──────┬──────┘
       │                       │
       │  TASK_ASSIGNMENT      │
       │──────────────────────▶│
       │                       │
       │  STATUS_UPDATE        │
       │◀──────────────────────│
       │  (status: running)    │
       │                       │
       │  RESULT_REPORT        │
       │◀──────────────────────│
       │  (analysis results)   │
       │                       │
```

---

## 10.4 平行執行與依賴管理

多代理人系統的一大優勢是平行執行。但當任務間存在依賴關係時，我們需要謹慎處理。

### 10.4.1 依賴關係類型

```
任務 A ──────▶ 任務 B ──────▶ 任務 C
（獨立）      （依賴 A）     （依賴 B）

任務 D ─┐
        ├────▶ 任務 F（依賴 D 和 E）
任務 E ─┘
```

**類型 1：線性依賴**

```python
subtasks = [
    SubTask(task_id="A", dependencies=[]),
    SubTask(task_id="B", dependencies=["A"]),
    SubTask(task_id="C", dependencies=["B"])
]
# 執行順序：A → B → C
```

**類型 2：扇出（Fan-out）**

```python
subtasks = [
    SubTask(task_id="A", dependencies=[]),
    SubTask(task_id="B", dependencies=["A"]),
    SubTask(task_id="C", dependencies=["A"]),
    SubTask(task_id="D", dependencies=["A"])
]
# 執行順序：A → (B, C, D 平行)
```

**類型 3：扇入（Fan-in）**

```python
subtasks = [
    SubTask(task_id="A", dependencies=[]),
    SubTask(task_id="B", dependencies=[]),
    SubTask(task_id="C", dependencies=["A", "B"])
]
# 執行順序：(A, B 平行) → C
```

### 10.4.2 智能調度演算法

```python
class TaskScheduler:
    """
    任務調度器

    ‹1› 拓撲排序確定執行順序
    ‹2› 最大化平行度
    ‹3› 處理動態依賴
    """

    def __init__(self, tasks: List[SubTask]):
        self.tasks = {t.task_id: t for t in tasks}
        self.completed: Set[str] = set()

    def get_ready_tasks(self) -> List[SubTask]:
        """
        獲取可執行的任務

        返回所有依賴已滿足的待執行任務
        """
        ready = []
        for task in self.tasks.values():
            if task.status != TaskStatus.PENDING:
                continue

            # 檢查所有依賴是否已完成
            deps_satisfied = all(
                dep_id in self.completed
                for dep_id in task.dependencies
            )

            if deps_satisfied:
                ready.append(task)

        # 按優先級排序
        ready.sort(key=lambda t: t.priority, reverse=True)
        return ready

    def mark_completed(self, task_id: str):
        """標記任務完成"""
        self.completed.add(task_id)
        self.tasks[task_id].status = TaskStatus.COMPLETED

    async def execute_all(
        self,
        executor: Callable[[SubTask], Awaitable[SubTask]]
    ) -> List[SubTask]:
        """
        執行所有任務

        ‹1› 持續檢查可執行任務
        ‹2› 平行執行就緒任務
        ‹3› 等待完成後更新狀態
        """
        while len(self.completed) < len(self.tasks):
            ready = self.get_ready_tasks()

            if not ready:
                # 檢查是否有循環依賴
                pending = [t for t in self.tasks.values()
                          if t.status == TaskStatus.PENDING]
                if pending:
                    raise RuntimeError("檢測到循環依賴或無法滿足的依賴")
                break

            # 平行執行就緒任務
            results = await asyncio.gather(
                *[executor(task) for task in ready],
                return_exceptions=True
            )

            # 更新完成狀態
            for task in ready:
                if task.status == TaskStatus.COMPLETED:
                    self.mark_completed(task.task_id)

        return list(self.tasks.values())
```

### 10.4.3 執行效率對比

讓我們用實際數據說明平行執行的優勢：

**場景：4 個獨立任務，每個耗時 2 秒**

| 執行方式 | 總耗時 | 效率提升 |
|----------|--------|----------|
| 順序執行 | 8 秒 | - |
| 2 路平行 | 4 秒 | 2x |
| 4 路平行 | 2 秒 | 4x |

**場景：有依賴的 4 個任務**

```
A(2s) ─┐
       ├──▶ C(2s) ──▶ D(2s)
B(2s) ─┘
```

| 執行方式 | 總耗時 | 說明 |
|----------|--------|------|
| 順序執行 | 8 秒 | A→B→C→D |
| 智能調度 | 6 秒 | (A,B 平行)→C→D |

---

## 10.5 結果整合與衝突解決

當多個專家提供分析結果後，協調器需要將這些結果整合成統一的報告。這個過程並不簡單——專家們可能有不同甚至矛盾的觀點。

### 10.5.1 整合策略

**策略 1：加權平均**

適用於數值型結論。

```python
def integrate_numerical(
    results: List[Dict],
    weights: Dict[str, float]
) -> float:
    """
    加權平均整合

    權重可基於：專家可信度、歷史準確率、來源品質
    """
    weighted_sum = 0
    total_weight = 0

    for result in results:
        agent = result["agent"]
        value = result["value"]
        weight = weights.get(agent, 1.0)

        weighted_sum += value * weight
        total_weight += weight

    return weighted_sum / total_weight if total_weight > 0 else 0
```

**策略 2：多數決**

適用於類別型結論。

```python
def integrate_categorical(
    results: List[Dict]
) -> str:
    """
    多數決整合

    選擇最多專家支持的結論
    """
    from collections import Counter

    conclusions = [r["conclusion"] for r in results]
    counter = Counter(conclusions)

    return counter.most_common(1)[0][0]
```

**策略 3：條件整合**

適用於複雜情境。

```python
def integrate_conditional(
    results: List[Dict],
    question_type: str
) -> Dict:
    """
    條件整合

    根據問題類型選擇不同的整合策略
    """
    if question_type == "quantitative":
        return {"method": "weighted_average", "result": ...}
    elif question_type == "qualitative":
        return {"method": "synthesis", "result": ...}
    elif question_type == "predictive":
        return {"method": "scenario_analysis", "result": ...}
    else:
        return {"method": "comprehensive", "result": ...}
```

### 10.5.2 衝突檢測

專家意見相左是常見情況。系統需要能夠識別這些衝突。

```python
class ConflictDetector:
    """
    衝突檢測器

    識別專家分析中的矛盾點
    """

    def detect_numerical_conflict(
        self,
        results: List[Dict],
        threshold: float = 0.3
    ) -> List[Dict]:
        """
        檢測數值衝突

        當數值差異超過閾值時標記為衝突
        """
        conflicts = []
        values = [r["value"] for r in results]

        if len(values) < 2:
            return conflicts

        mean_val = sum(values) / len(values)

        for r in results:
            deviation = abs(r["value"] - mean_val) / mean_val
            if deviation > threshold:
                conflicts.append({
                    "type": "numerical_deviation",
                    "agent": r["agent"],
                    "value": r["value"],
                    "deviation": deviation,
                    "mean": mean_val
                })

        return conflicts

    def detect_categorical_conflict(
        self,
        results: List[Dict]
    ) -> List[Dict]:
        """
        檢測類別衝突

        當專家結論不一致時標記為衝突
        """
        conclusions = [r["conclusion"] for r in results]
        unique = set(conclusions)

        if len(unique) <= 1:
            return []

        return [{
            "type": "categorical_disagreement",
            "conclusions": list(unique),
            "agents": {r["agent"]: r["conclusion"] for r in results}
        }]

    def detect_confidence_conflict(
        self,
        results: List[Dict],
        threshold: float = 0.3
    ) -> List[Dict]:
        """
        檢測信心衝突

        當專家對同一問題的信心差異過大時標記
        """
        confidences = [r.get("confidence", 0.5) for r in results]

        if len(confidences) < 2:
            return []

        max_conf = max(confidences)
        min_conf = min(confidences)

        if max_conf - min_conf > threshold:
            return [{
                "type": "confidence_discrepancy",
                "range": [min_conf, max_conf],
                "spread": max_conf - min_conf
            }]

        return []
```

### 10.5.3 衝突解決策略

檢測到衝突後，我們需要解決它。

**策略 1：仲裁模式**

引入仲裁代理人做出最終判斷。

```python
class ArbitrationResolver:
    """
    仲裁解決

    引入仲裁代理人評估衝突雙方的論點
    """

    def __init__(self, arbitrator: ExpertAgent):
        self.arbitrator = arbitrator

    async def resolve(
        self,
        conflict: Dict,
        agent_reports: List[Dict]
    ) -> Dict:
        """
        仲裁解決衝突

        ‹1› 收集衝突雙方的論據
        ‹2› 提交仲裁代理人評估
        ‹3› 返回仲裁結論
        """
        context = {
            "conflict": conflict,
            "reports": agent_reports,
            "instruction": "請評估各方論點，做出最終判斷"
        }

        arbitration = await self.arbitrator.analyze(
            SubTask(
                task_id="arbitration",
                description="評估專家意見衝突",
                required_expertise="仲裁"
            ),
            context
        )

        return {
            "resolution_method": "arbitration",
            "original_conflict": conflict,
            "arbitration_result": arbitration,
            "final_conclusion": arbitration.get("conclusion")
        }
```

**策略 2：共識模式**

讓衝突雙方進行對話，尋求共識。

```python
class ConsensusResolver:
    """
    共識解決

    促進專家間對話，尋求共識
    """

    async def resolve(
        self,
        conflict: Dict,
        agents: Dict[str, ExpertAgent],
        max_rounds: int = 3
    ) -> Dict:
        """
        對話式解決

        ‹1› 輪流呈現各方觀點
        ‹2› 請對方回應
        ‹3› 尋找共同點
        """
        conversation = []
        involved_agents = list(conflict.get("agents", {}).keys())

        for round in range(max_rounds):
            for agent_name in involved_agents:
                agent = agents.get(agent_name)
                if not agent:
                    continue

                response = await agent.analyze(
                    SubTask(
                        task_id=f"consensus_r{round}_{agent_name}",
                        description="回應其他專家的觀點",
                        required_expertise=agent.expertise
                    ),
                    {"conversation": conversation, "conflict": conflict}
                )

                conversation.append({
                    "round": round,
                    "agent": agent_name,
                    "response": response
                })

            # 檢查是否達成共識
            if self._check_consensus(conversation):
                break

        return {
            "resolution_method": "consensus",
            "rounds": len(conversation) // len(involved_agents),
            "conversation": conversation,
            "consensus_reached": self._check_consensus(conversation)
        }

    def _check_consensus(self, conversation: List[Dict]) -> bool:
        """檢查是否達成共識"""
        if len(conversation) < 2:
            return False

        # 簡化實現：檢查最後兩個回應是否趨同
        # 實際應用中需要更複雜的語義分析
        return False
```

**策略 3：呈現模式**

不解決衝突，而是如實呈現各方觀點。

```python
class PresentationResolver:
    """
    呈現解決

    不強求一致，如實呈現各方觀點
    """

    def resolve(
        self,
        conflict: Dict,
        agent_reports: List[Dict]
    ) -> Dict:
        """
        呈現各方觀點

        適用於：
        - 沒有絕對正確答案的問題
        - 預測性問題
        - 主觀判斷問題
        """
        return {
            "resolution_method": "presentation",
            "message": "專家意見存在分歧，以下呈現各方觀點：",
            "viewpoints": [
                {
                    "agent": r["agent"],
                    "conclusion": r.get("conclusion"),
                    "confidence": r.get("confidence"),
                    "reasoning": r.get("reasoning", "")
                }
                for r in agent_reports
            ],
            "recommendation": "建議讀者根據自身判斷做出決定"
        }
```

---

## 10.6 完整範例：多專家研究系統

現在，讓我們將所有元件整合起來，建構一個完整的多專家研究系統。

### 10.6.1 系統架構

```
┌─────────────────────────────────────────────────────────────────┐
│                     多專家研究系統                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────┐                                              │
│   │  使用者介面  │                                              │
│   └──────┬──────┘                                              │
│          │                                                      │
│          ▼                                                      │
│   ┌─────────────┐                                              │
│   │   研究協調器 │◀─────────────────────────────────┐          │
│   │ Coordinator │                                   │          │
│   └──────┬──────┘                                   │          │
│          │                                          │          │
│          │    任務分配                    結果回報   │          │
│          ▼                                          │          │
│   ┌──────────────────────────────────────────────┐ │          │
│   │              專家代理人池                     │ │          │
│   │                                              │ │          │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  │ │          │
│   │  │ 產業分析師│  │  技術專家 │  │ 財務分析師│  │ │          │
│   │  └──────────┘  └──────────┘  └──────────┘  │ │          │
│   │                                              │ │          │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  │ │          │
│   │  │ 地緣顧問 │  │  法規專家 │  │ 市場專家  │  │ │          │
│   │  └──────────┘  └──────────┘  └──────────┘  │ │          │
│   │                                              │ │          │
│   └──────────────────────────────────────────────┘ │          │
│                                                    │          │
│   ┌──────────────────────────────────────────────┐ │          │
│   │              支援模組                         │ │          │
│   │                                              │ │          │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  │ │          │
│   │  │ 任務調度器│  │ 衝突解決器│  │ 報告生成器│──┘          │
│   │  └──────────┘  └──────────┘  └──────────┘              │
│   │                                              │          │
│   └──────────────────────────────────────────────┘          │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 10.6.2 使用範例

```python
#!/usr/bin/env python3
"""
多專家研究系統 - 使用範例
"""

import asyncio


async def main():
    """示範多專家研究系統"""

    # ‹1› 建立協調器
    coordinator = ResearchCoordinator()

    # ‹2› 執行研究
    research_question = "全球半導體產業在 AI 時代的競爭格局與投資機會"

    result = await coordinator.coordinate(research_question)

    # ‹3› 生成報告
    generator = ReportGenerator()
    report = generator.generate_markdown(result)

    # ‹4› 輸出結果
    print("\n" + "=" * 60)
    print("📄 研究報告")
    print("=" * 60)
    print(report)

    # ‹5› 顯示統計
    print("\n" + "-" * 40)
    print("📊 執行統計")
    print("-" * 40)
    print(f"  總任務數: {len(result.subtasks)}")
    print(f"  完成數: {result.metadata.get('tasks_completed', 0)}")
    print(f"  失敗數: {result.metadata.get('tasks_failed', 0)}")
    print(f"  總耗時: {result.total_duration:.2f} 秒")
    print(f"  整體信心: {result.confidence_score:.0%}")

    if result.conflicts:
        print(f"\n⚠️ 檢測到 {len(result.conflicts)} 個衝突:")
        for c in result.conflicts:
            print(f"  - {c['description']}")


if __name__ == "__main__":
    asyncio.run(main())
```

### 10.6.3 執行結果

```
============================================================
🔬 開始多代理人協作研究
============================================================
研究問題: 全球半導體產業在 AI 時代的競爭格局與投資機會

📋 步驟 1: 任務分解
  - task_000: 產業分析
  - task_001: 技術分析
  - task_002: 財務分析
  - task_003: 地緣政治分析

⚡ 步驟 2: 平行執行任務
  執行無依賴任務...
  執行有依賴任務...

📊 步驟 3: 整合結果

✅ 協調完成，耗時 2.15 秒

============================================================
📄 研究報告
============================================================

# 研究報告

**研究問題**: 全球半導體產業在 AI 時代的競爭格局與投資機會

**執行時間**: 2.15 秒

**整體信心分數**: 78%

---

## 執行摘要

本研究整合了 4 位專家的分析，涵蓋產業、技術、財務與地緣政治等多個維度。

### 主要發現

**industry_analysis**：提供了相關領域的深入分析。

**technology_analysis**：提供了相關領域的深入分析。

**financial_analysis**：提供了相關領域的深入分析。

**geopolitical_analysis**：提供了相關領域的深入分析。

## 關鍵洞察

1. 市場持續成長，但競爭加劇
2. 技術創新是維持競爭優勢的關鍵
3. 財務表現強勁，但估值偏高
4. 地緣政治風險需持續關注

...

----------------------------------------
📊 執行統計
----------------------------------------
  總任務數: 4
  完成數: 4
  失敗數: 0
  總耗時: 2.15 秒
  整體信心: 78%
```

---

## 10.7 進階主題：動態代理人管理

在實際應用中，你可能需要動態新增或移除專家代理人。

### 10.7.1 動態註冊

```python
class DynamicAgentRegistry:
    """
    動態代理人註冊表

    ‹1› 執行時新增/移除代理人
    ‹2› 代理人能力發現
    ‹3› 負載均衡
    """

    def __init__(self):
        self._agents: Dict[str, List[ExpertAgent]] = {}
        self._agent_stats: Dict[str, Dict] = {}

    def register(self, agent: ExpertAgent):
        """註冊新代理人"""
        expertise = agent.expertise

        if expertise not in self._agents:
            self._agents[expertise] = []

        self._agents[expertise].append(agent)
        self._agent_stats[agent.name] = {
            "tasks_completed": 0,
            "avg_duration": 0,
            "success_rate": 1.0
        }

        print(f"✓ 動態註冊: {agent.name} ({expertise})")

    def unregister(self, agent_name: str) -> bool:
        """移除代理人"""
        for expertise, agents in self._agents.items():
            for agent in agents:
                if agent.name == agent_name:
                    agents.remove(agent)
                    del self._agent_stats[agent_name]
                    print(f"✗ 已移除: {agent_name}")
                    return True
        return False

    def get_best_agent(self, expertise: str) -> Optional[ExpertAgent]:
        """
        獲取最佳代理人

        基於：可用性、成功率、平均耗時
        """
        candidates = self._agents.get(expertise, [])

        if not candidates:
            return None

        # 過濾忙碌的代理人
        available = [a for a in candidates if not a.is_busy]

        if not available:
            return None

        # 按成功率和平均耗時排序
        def score(agent):
            stats = self._agent_stats.get(agent.name, {})
            success_rate = stats.get("success_rate", 1.0)
            avg_duration = stats.get("avg_duration", 1.0)
            return success_rate / (avg_duration + 0.1)

        available.sort(key=score, reverse=True)
        return available[0]

    def update_stats(
        self,
        agent_name: str,
        duration: float,
        success: bool
    ):
        """更新代理人統計"""
        if agent_name not in self._agent_stats:
            return

        stats = self._agent_stats[agent_name]
        stats["tasks_completed"] += 1

        # 更新平均耗時（移動平均）
        alpha = 0.3
        stats["avg_duration"] = (
            alpha * duration + (1 - alpha) * stats["avg_duration"]
        )

        # 更新成功率（移動平均）
        stats["success_rate"] = (
            alpha * (1.0 if success else 0.0) +
            (1 - alpha) * stats["success_rate"]
        )
```

### 10.7.2 代理人工廠

```python
class AgentFactory:
    """
    代理人工廠

    根據配置動態建立代理人
    """

    @staticmethod
    def create_from_config(config: Dict) -> ExpertAgent:
        """
        從配置建立代理人

        配置範例：
        {
            "name": "ESG 分析師",
            "expertise": "ESG 分析",
            "description": "專注於環境、社會、治理分析",
            "capabilities": ["碳排放評估", "社會責任評估"]
        }
        """
        class ConfiguredAgent(ExpertAgent):
            def __init__(self, cfg):
                super().__init__(
                    name=cfg["name"],
                    expertise=cfg["expertise"],
                    description=cfg["description"]
                )
                self.capabilities = cfg.get("capabilities", [])

            async def analyze(self, task, context):
                # 通用分析邏輯
                return {
                    "analysis_type": self.expertise,
                    "task_id": task.task_id,
                    "findings": f"針對「{task.description}」的分析結果",
                    "confidence": 0.75
                }

        return ConfiguredAgent(config)

    @staticmethod
    def create_specialist(
        specialty: str,
        llm_client=None
    ) -> ExpertAgent:
        """
        建立專業代理人

        根據專業領域自動配置
        """
        specialties = {
            "ESG": {
                "name": "ESG 分析師",
                "description": "專注於 ESG 評估與永續發展分析"
            },
            "法規": {
                "name": "法規專家",
                "description": "專注於法規遵循與合規風險評估"
            },
            "供應鏈": {
                "name": "供應鏈分析師",
                "description": "專注於供應鏈結構與風險分析"
            }
        }

        config = specialties.get(specialty, {
            "name": f"{specialty}專家",
            "description": f"專注於{specialty}領域的分析"
        })
        config["expertise"] = f"{specialty}分析"

        return AgentFactory.create_from_config(config)
```

---

## 10.8 效能優化與最佳實踐

### 10.8.1 效能優化技巧

**技巧 1：快取共享資訊**

```python
class SharedCache:
    """
    共享快取

    避免重複獲取相同資訊
    """

    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._hits = 0
        self._misses = 0

    async def get_or_fetch(
        self,
        key: str,
        fetcher: Callable[[], Awaitable[Any]],
        ttl: int = 300
    ) -> Any:
        """獲取或拉取資料"""
        if key in self._cache:
            self._hits += 1
            return self._cache[key]

        self._misses += 1
        value = await fetcher()
        self._cache[key] = value
        return value

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0
```

**技巧 2：批次處理**

```python
async def batch_analyze(
    coordinator: ResearchCoordinator,
    questions: List[str],
    batch_size: int = 5
) -> List[CoordinationResult]:
    """
    批次處理多個研究問題

    ‹1› 分批執行避免過載
    ‹2› 共享資源減少重複工作
    """
    results = []

    for i in range(0, len(questions), batch_size):
        batch = questions[i:i + batch_size]

        batch_results = await asyncio.gather(
            *[coordinator.coordinate(q) for q in batch],
            return_exceptions=True
        )

        for r in batch_results:
            if isinstance(r, Exception):
                results.append(None)
            else:
                results.append(r)

    return results
```

**技巧 3：超時控制**

```python
async def execute_with_timeout(
    task: SubTask,
    agent: ExpertAgent,
    timeout: float = 30.0
) -> Dict:
    """
    帶超時的任務執行

    避免單一代理人阻塞整個系統
    """
    try:
        result = await asyncio.wait_for(
            agent.analyze(task, {}),
            timeout=timeout
        )
        return {"status": "success", "result": result}

    except asyncio.TimeoutError:
        return {
            "status": "timeout",
            "error": f"代理人 {agent.name} 執行超時"
        }
```

### 10.8.2 最佳實踐清單

| 類別 | 最佳實踐 | 說明 |
|------|----------|------|
| **設計** | 保持代理人職責單一 | 避免建立「萬能」代理人 |
| **設計** | 定義清晰的介面 | 使用結構化的輸入輸出格式 |
| **設計** | 實現優雅降級 | 單一代理人失敗不影響整體 |
| **執行** | 最大化平行度 | 無依賴任務應平行執行 |
| **執行** | 設定合理超時 | 避免無限等待 |
| **執行** | 使用共享快取 | 減少重複資料獲取 |
| **整合** | 檢測衝突 | 主動識別專家意見分歧 |
| **整合** | 保留原始結論 | 整合時保留各方觀點 |
| **監控** | 記錄訊息日誌 | 便於追蹤與除錯 |
| **監控** | 追蹤代理人效能 | 識別瓶頸與問題 |

---

## 10.9 章節總結

恭喜！你已經掌握了多代理人協作系統的核心概念與實作技巧。讓我們回顧一下：

### 核心概念

1. **為何需要多代理人**：單一代理人難以同時精通多個領域，多代理人系統透過專業分工提升深度與效率

2. **協調器模式**：層級式架構中，協調器負責任務分解、分配、監控與整合

3. **專家代理人**：每個專家專注於特定領域，提供高品質的深度分析

4. **平行執行**：無依賴的任務可平行執行，大幅提升效率

5. **衝突解決**：專家意見相左時，可採用仲裁、共識或呈現等策略

### 關鍵產出物

- `coordinator.py` - 完整的協調器實現（600+ 行）
- 4 個專業代理人類別
- 任務調度器
- 衝突檢測與解決器
- 報告生成器

### 實際效益

| 指標 | 單一代理人 | 多代理人系統 |
|------|-----------|-------------|
| 分析深度 | 一般 | 深入 |
| 專業覆蓋 | 有限 | 多維度 |
| 執行效率 | 順序 | 平行 |
| 可擴展性 | 困難 | 容易 |
| 錯誤隔離 | 全局影響 | 局部影響 |

---

## 10.10 下一章預告

在下一章「**生產環境部署**」中，我們將學習如何將研究代理人系統部署到生產環境：

- **容器化部署**：Docker + Kubernetes 最佳實踐
- **監控與告警**：Prometheus + Grafana 監控體系
- **日誌管理**：結構化日誌與集中式管理
- **擴展策略**：水平擴展與負載均衡
- **安全性**：API 認證、速率限制、資料加密

讓我們繼續前進！

---

## 附錄 A：完整程式碼清單

本章的完整程式碼範例請參考：

```
code-examples/chapter-10/
├── coordinator.py           # 協調器代理人
├── experts.py              # 專家代理人集合
├── scheduler.py            # 任務調度器
├── conflict_resolver.py    # 衝突解決器
├── report_generator.py     # 報告生成器
├── requirements.txt        # 依賴套件
├── .env.example            # 環境變數範例
└── README.md               # 說明文件
```

## 附錄 B：專家代理人模板

建立新專家代理人時，可使用以下模板：

```python
class NewExpertAgent(ExpertAgent):
    """
    [專家名稱] 代理人

    專注於 [專業領域]
    """

    def __init__(self, llm_client=None):
        super().__init__(
            name="[專家名稱]",
            expertise="[專業領域]",
            description="""專注於分析：
- [能力 1]
- [能力 2]
- [能力 3]""",
            llm_client=llm_client
        )

    async def analyze(
        self,
        task: SubTask,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """執行專業分析"""
        self.is_busy = True
        self.current_task = task.task_id

        try:
            # 1. 理解任務
            # 2. 收集資訊
            # 3. 進行分析
            # 4. 評估可信度

            result = {
                "analysis_type": self.expertise,
                "task_id": task.task_id,
                "findings": {...},
                "confidence": 0.8,
                "sources": [...],
                "limitations": [...]
            }

            return result

        finally:
            self.is_busy = False
            self.current_task = None
```
