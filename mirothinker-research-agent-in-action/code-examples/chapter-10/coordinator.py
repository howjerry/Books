#!/usr/bin/env python3
"""
深度研究代理人實戰 - 第 10 章：多代理人協作系統
協調器代理人

這個模組實現了多代理人系統的核心協調器：
1. 任務分解與規劃
2. 專家代理人管理
3. 平行執行與結果整合

使用方式：
    python coordinator.py --demo
"""

import asyncio
import argparse
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Awaitable
import os

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

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "task_id": self.task_id,
            "description": self.description,
            "required_expertise": self.required_expertise,
            "dependencies": self.dependencies,
            "priority": self.priority,
            "status": self.status.value,
            "assigned_agent": self.assigned_agent,
            "has_result": self.result is not None,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }


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

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "message_id": self.message_id,
            "sender": self.sender,
            "receiver": self.receiver,
            "message_type": self.message_type.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id
        }


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

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "research_question": self.research_question,
            "subtasks": [t.to_dict() for t in self.subtasks],
            "expert_reports": self.expert_reports,
            "integrated_summary": self.integrated_summary,
            "key_insights": self.key_insights,
            "conflicts": self.conflicts,
            "confidence_score": self.confidence_score,
            "total_duration": self.total_duration,
            "metadata": self.metadata
        }


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
        self._task_history: List[Dict] = []

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

    def record_task(self, task_id: str, duration: float, success: bool):
        """記錄任務執行歷史"""
        self._task_history.append({
            "task_id": task_id,
            "duration": duration,
            "success": success,
            "timestamp": datetime.now().isoformat()
        })

    def get_stats(self) -> Dict[str, Any]:
        """獲取代理人統計"""
        if not self._task_history:
            return {
                "tasks_completed": 0,
                "avg_duration": 0,
                "success_rate": 0
            }

        tasks = len(self._task_history)
        successes = sum(1 for t in self._task_history if t["success"])
        durations = [t["duration"] for t in self._task_history]

        return {
            "tasks_completed": tasks,
            "avg_duration": sum(durations) / len(durations),
            "success_rate": successes / tasks
        }

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "name": self.name,
            "expertise": self.expertise,
            "description": self.description,
            "is_busy": self.is_busy,
            "current_task": self.current_task,
            "stats": self.get_stats()
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
        start_time = datetime.now()

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
                "analyst": self.name,
                "findings": {
                    "market_overview": f"針對「{task.description}」的產業分析完成",
                    "market_size": {
                        "current": "$500B",
                        "projected_2030": "$1.2T",
                        "cagr": "15.2%"
                    },
                    "growth_trends": [
                        "AI 驅動的需求激增",
                        "邊緣計算應用擴展",
                        "電動車市場帶動"
                    ],
                    "competitive_landscape": {
                        "major_players": [
                            {"name": "NVIDIA", "share": 0.80, "trend": "穩定"},
                            {"name": "AMD", "share": 0.12, "trend": "上升"},
                            {"name": "Intel", "share": 0.05, "trend": "下降"}
                        ],
                        "concentration": "高度集中"
                    },
                    "entry_barriers": ["高資本投入", "技術複雜度", "生態系統鎖定"]
                },
                "confidence": 0.82,
                "sources": [
                    "IDC 半導體市場報告 2024",
                    "Gartner AI 晶片預測",
                    "公司財報與法說會"
                ],
                "limitations": [
                    "市場數據可能有 3-6 個月滯後",
                    "新興玩家可能被低估"
                ],
                "timestamp": datetime.now().isoformat()
            }

            duration = (datetime.now() - start_time).total_seconds()
            self.record_task(task.task_id, duration, True)

            return result

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            self.record_task(task.task_id, duration, False)
            raise

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
        start_time = datetime.now()

        try:
            await asyncio.sleep(0.6)

            result = {
                "analysis_type": "technology_analysis",
                "task_id": task.task_id,
                "analyst": self.name,
                "findings": {
                    "tech_overview": f"針對「{task.description}」的技術分析完成",
                    "core_technologies": [
                        {"name": "CUDA 生態系統", "maturity": "成熟", "moat": "高"},
                        {"name": "Tensor Core", "maturity": "成熟", "moat": "高"},
                        {"name": "NVLink 互連", "maturity": "成熟", "moat": "中"}
                    ],
                    "patent_analysis": {
                        "total_patents": 15000,
                        "annual_filings": 2500,
                        "key_areas": ["AI 加速器", "記憶體架構", "軟體框架"],
                        "citation_index": 85
                    },
                    "r_and_d": {
                        "annual_investment": "$7.5B",
                        "rd_ratio": "22%",
                        "key_projects": [
                            "Blackwell 架構",
                            "Grace Hopper 超級晶片",
                            "Omniverse 平台"
                        ]
                    },
                    "technology_roadmap": {
                        "2024": "Blackwell B100/B200",
                        "2025": "Rubin 架構",
                        "2026": "Rubin Ultra"
                    }
                },
                "confidence": 0.78,
                "sources": [
                    "USPTO 專利資料庫",
                    "IEEE 論文庫",
                    "技術白皮書與產品發表"
                ],
                "limitations": [
                    "部分專利資訊可能不完整",
                    "未公開的研發計畫無法評估"
                ],
                "timestamp": datetime.now().isoformat()
            }

            duration = (datetime.now() - start_time).total_seconds()
            self.record_task(task.task_id, duration, True)

            return result

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            self.record_task(task.task_id, duration, False)
            raise

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
        start_time = datetime.now()

        try:
            await asyncio.sleep(0.5)

            result = {
                "analysis_type": "financial_analysis",
                "task_id": task.task_id,
                "analyst": self.name,
                "findings": {
                    "financial_overview": f"針對「{task.description}」的財務分析完成",
                    "revenue": {
                        "latest_quarter": "$26.0B",
                        "yoy_growth": "122%",
                        "guidance": "$28.0B ± 2%"
                    },
                    "profitability": {
                        "gross_margin": "72.7%",
                        "operating_margin": "54.1%",
                        "net_margin": "48.8%",
                        "trend": "持續改善"
                    },
                    "valuation": {
                        "market_cap": "$2.5T",
                        "pe_ratio": 65.2,
                        "ps_ratio": 30.5,
                        "peg_ratio": 1.8,
                        "assessment": "估值偏高但有成長支撐"
                    },
                    "financial_health": {
                        "cash_position": "$26.0B",
                        "debt_equity": 0.41,
                        "current_ratio": 4.2,
                        "assessment": "財務狀況穩健"
                    },
                    "dividend_and_buyback": {
                        "dividend_yield": "0.03%",
                        "buyback_program": "$25B 授權"
                    }
                },
                "confidence": 0.88,
                "sources": [
                    "SEC 10-Q/10-K 報告",
                    "法說會逐字稿",
                    "分析師報告"
                ],
                "limitations": [
                    "使用最近一季數據",
                    "未來展望基於公司指引"
                ],
                "timestamp": datetime.now().isoformat()
            }

            duration = (datetime.now() - start_time).total_seconds()
            self.record_task(task.task_id, duration, True)

            return result

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            self.record_task(task.task_id, duration, False)
            raise

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
        start_time = datetime.now()

        try:
            await asyncio.sleep(0.4)

            result = {
                "analysis_type": "geopolitical_analysis",
                "task_id": task.task_id,
                "analyst": self.name,
                "findings": {
                    "geopolitical_overview": f"針對「{task.description}」的地緣政治分析完成",
                    "policy_risks": [
                        {
                            "policy": "美國出口管制",
                            "impact": "限制對華高端晶片出口",
                            "severity": "高",
                            "trend": "加嚴中"
                        },
                        {
                            "policy": "CHIPS 法案",
                            "impact": "促進美國本土製造",
                            "severity": "中",
                            "trend": "實施中"
                        }
                    ],
                    "supply_chain_risks": {
                        "taiwan_concentration": {
                            "risk_level": "高",
                            "exposure": "先進製程高度依賴台積電",
                            "mitigation": "多元化供應商策略進行中"
                        },
                        "rare_earth_dependency": {
                            "risk_level": "中",
                            "exposure": "部分原材料依賴中國",
                            "mitigation": "替代來源開發中"
                        }
                    },
                    "international_dynamics": {
                        "us_china_relations": {
                            "status": "緊張",
                            "outlook": "短期內難以改善",
                            "key_issues": ["技術競爭", "市場准入"]
                        },
                        "regional_alliances": {
                            "chip4_alliance": "發展中",
                            "eu_chips_act": "實施中"
                        }
                    },
                    "risk_scenarios": [
                        {
                            "scenario": "台海緊張升級",
                            "probability": "低-中",
                            "impact": "嚴重供應中斷"
                        },
                        {
                            "scenario": "出口管制擴大",
                            "probability": "中",
                            "impact": "市場萎縮 10-15%"
                        }
                    ]
                },
                "confidence": 0.72,
                "sources": [
                    "政府政策文件",
                    "智庫報告",
                    "外交關係分析"
                ],
                "limitations": [
                    "地緣政治情勢變化快速",
                    "政策影響難以精確量化"
                ],
                "timestamp": datetime.now().isoformat()
            }

            duration = (datetime.now() - start_time).total_seconds()
            self.record_task(task.task_id, duration, True)

            return result

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            self.record_task(task.task_id, duration, False)
            raise

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
        print(f"  ✓ 已註冊代理人: {agent.name} ({agent.expertise})")

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
            self._send_message(
                sender="coordinator",
                receiver=agent.name,
                message_type=MessageType.TASK_ASSIGNMENT,
                content={"task_id": task.task_id, "description": task.description}
            )

            result = await agent.analyze(task, context)
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()

            self._send_message(
                sender=agent.name,
                receiver="coordinator",
                message_type=MessageType.RESULT_REPORT,
                content={"task_id": task.task_id, "status": "completed"}
            )

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            self._send_message(
                sender=agent.name,
                receiver="coordinator",
                message_type=MessageType.ERROR_REPORT,
                content={"task_id": task.task_id, "error": str(e)}
            )

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
        print(f"  開始多代理人協作研究")
        print(f"{'='*60}")
        print(f"研究問題: {research_question}\n")

        # ‹1› 任務分解
        print("步驟 1: 任務分解")
        subtasks = await self.decompose_task(research_question)
        for task in subtasks:
            self.tasks[task.task_id] = task
            print(f"  - {task.task_id}: {task.required_expertise}")

        # ‹2› 執行策略：先執行無依賴任務，再執行有依賴任務
        print("\n步驟 2: 平行執行任務")

        # 分離無依賴與有依賴任務
        independent_tasks = [t for t in subtasks if not t.dependencies]
        dependent_tasks = [t for t in subtasks if t.dependencies]

        # 平行執行無依賴任務
        print("  執行無依賴任務...")
        await asyncio.gather(
            *[self.execute_task(task) for task in independent_tasks],
            return_exceptions=True
        )

        # 順序執行有依賴任務
        print("  執行有依賴任務...")
        for task in dependent_tasks:
            await self.execute_task(task)

        # ‹3› 收集結果
        print("\n步驟 3: 整合結果")
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

        print(f"\n協調完成，耗時 {duration:.2f} 秒")

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
                "tasks_failed": sum(1 for t in self.tasks.values() if t.status == TaskStatus.FAILED),
                "message_count": len(self.messages)
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
        # 提取各專家的關鍵發現
        findings_by_type = {}
        for task_id, report in reports.items():
            analysis_type = report.get("analysis_type", "unknown")
            findings = report.get("findings", {})
            analyst = report.get("analyst", "未知")
            confidence = report.get("confidence", 0)
            findings_by_type[analysis_type] = {
                "analyst": analyst,
                "findings": findings,
                "confidence": confidence
            }

        # 生成整合摘要
        summary_parts = [
            f"## 研究摘要：{question}",
            "",
            f"本研究整合了 {len(reports)} 位專家的分析，涵蓋產業、技術、財務與地緣政治等多個維度。",
            "",
            "### 各專家分析要點",
            ""
        ]

        for analysis_type, data in findings_by_type.items():
            summary_parts.append(f"**{data['analyst']}** (信心度: {data['confidence']:.0%})")

            # 提取並格式化關鍵發現
            if analysis_type == "industry_analysis":
                market = data["findings"].get("market_size", {})
                summary_parts.append(f"- 市場規模: {market.get('current', 'N/A')} → {market.get('projected_2030', 'N/A')}")
            elif analysis_type == "technology_analysis":
                rd = data["findings"].get("r_and_d", {})
                summary_parts.append(f"- 研發投入: {rd.get('annual_investment', 'N/A')}")
            elif analysis_type == "financial_analysis":
                revenue = data["findings"].get("revenue", {})
                summary_parts.append(f"- 營收成長: {revenue.get('yoy_growth', 'N/A')}")
            elif analysis_type == "geopolitical_analysis":
                risks = data["findings"].get("policy_risks", [])
                if risks:
                    summary_parts.append(f"- 主要風險: {risks[0].get('policy', 'N/A')}")

            summary_parts.append("")

        summary = "\n".join(summary_parts)

        # 提取關鍵洞察
        key_insights = [
            "AI 驅動下半導體市場持續高速成長，預計 2030 年達 $1.2T",
            "NVIDIA 憑藉 CUDA 生態系統維持 80% 市場主導地位",
            "財務表現亮眼（營收 YoY +122%），但估值已反映成長預期",
            "美中科技競爭加劇，供應鏈多元化成為關鍵策略",
            "地緣政治風險需持續關注，尤其是出口管制與台海局勢"
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

        # 檢查信心分數差異
        confidence_values = []
        for task_id, report in reports.items():
            confidence_values.append({
                "task_id": task_id,
                "analyst": report.get("analyst", "未知"),
                "confidence": report.get("confidence", 0.5)
            })

        if len(confidence_values) >= 2:
            max_conf = max(c["confidence"] for c in confidence_values)
            min_conf = min(c["confidence"] for c in confidence_values)

            if max_conf - min_conf > 0.2:
                max_analyst = next(c["analyst"] for c in confidence_values if c["confidence"] == max_conf)
                min_analyst = next(c["analyst"] for c in confidence_values if c["confidence"] == min_conf)
                conflicts.append({
                    "type": "confidence_discrepancy",
                    "description": f"專家信心分數差異：{min_analyst}({min_conf:.0%}) vs {max_analyst}({max_conf:.0%})",
                    "severity": "low",
                    "recommendation": "建議進一步驗證低信心領域的分析"
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
        return [m.to_dict() for m in self.messages]

    def reset(self):
        """重置協調器狀態"""
        self.tasks.clear()
        self.messages.clear()
        self._message_counter = 0


# =============================================================================
# 報告生成器
# =============================================================================

class ReportGenerator:
    """
    報告生成器

    將協調結果轉換為可讀的研究報告
    """

    def generate_markdown(self, result: CoordinationResult) -> str:
        """生成 Markdown 格式報告"""
        lines = [
            f"# 多專家研究報告",
            f"",
            f"**研究問題**: {result.research_question}",
            f"",
            f"**執行時間**: {result.total_duration:.2f} 秒",
            f"",
            f"**整體信心分數**: {result.confidence_score:.0%}",
            f"",
            "---",
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
            analyst = report.get("analyst", "未知")
            analysis_type = report.get("analysis_type", "未知")
            confidence = report.get("confidence", 0)

            lines.extend([
                f"### {analyst}",
                f"",
                f"- **分析類型**: {analysis_type}",
                f"- **信心分數**: {confidence:.0%}",
                f"- **來源**: {', '.join(report.get('sources', []))}",
                f"",
                "**主要發現**:",
                ""
            ])

            findings = report.get("findings", {})
            for key, value in findings.items():
                if isinstance(value, dict):
                    lines.append(f"- **{key}**: {json.dumps(value, ensure_ascii=False)[:100]}...")
                elif isinstance(value, list):
                    lines.append(f"- **{key}**: {len(value)} 項")
                else:
                    lines.append(f"- **{key}**: {str(value)[:100]}")

            lines.append("")

        if result.conflicts:
            lines.extend([
                "## 衝突與不確定性",
                ""
            ])
            for conflict in result.conflicts:
                lines.append(f"- **{conflict['type']}**: {conflict['description']}")
                if conflict.get('recommendation'):
                    lines.append(f"  - 建議: {conflict['recommendation']}")
            lines.append("")

        lines.extend([
            "## 執行統計",
            "",
            f"- 使用代理人數: {result.metadata.get('agents_used', 0)}",
            f"- 完成任務數: {result.metadata.get('tasks_completed', 0)}",
            f"- 失敗任務數: {result.metadata.get('tasks_failed', 0)}",
            f"- 訊息交換數: {result.metadata.get('message_count', 0)}",
            "",
            "---",
            "",
            f"*報告生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
        ])

        return "\n".join(lines)

    def generate_json(self, result: CoordinationResult) -> str:
        """生成 JSON 格式報告"""
        return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)


# =============================================================================
# 示範
# =============================================================================

async def demo():
    """示範多代理人協作系統"""
    print("=" * 60)
    print("  多代理人協作系統示範")
    print("=" * 60)

    # 建立協調器
    print("\n初始化協調器...")
    coordinator = ResearchCoordinator()

    # 顯示已註冊的代理人
    print("\n已註冊的專家代理人:")
    for agent in coordinator.list_agents():
        print(f"  - {agent['name']} ({agent['expertise']})")

    # 執行研究
    research_question = "全球半導體產業在 AI 時代的競爭格局與投資機會"

    result = await coordinator.coordinate(research_question)

    # 生成報告
    generator = ReportGenerator()
    report = generator.generate_markdown(result)

    # 輸出報告
    print("\n" + "=" * 60)
    print("  研究報告")
    print("=" * 60)
    print(report)

    # 顯示訊息日誌
    print("\n" + "-" * 40)
    print("  代理人通訊日誌")
    print("-" * 40)
    for msg in coordinator.get_message_log()[:10]:  # 只顯示前 10 條
        print(f"  [{msg['timestamp'][:19]}] {msg['sender']} → {msg['receiver']}: {msg['type']}")


def main():
    parser = argparse.ArgumentParser(description="多代理人協作系統")
    parser.add_argument("--demo", action="store_true", help="執行示範")
    parser.add_argument("-q", "--question", type=str, help="研究問題")

    args = parser.parse_args()

    if args.question:
        async def run_research():
            coordinator = ResearchCoordinator()
            result = await coordinator.coordinate(args.question)
            generator = ReportGenerator()
            print(generator.generate_markdown(result))

        asyncio.run(run_research())
    else:
        asyncio.run(demo())


if __name__ == "__main__":
    main()
