#!/usr/bin/env python3
"""
深度研究代理人實戰 - 第 9 章：建構你的第一個研究代理人
核心研究代理人實現

這個模組實現了完整的深度研究代理人：
1. 問題理解與規劃
2. 資訊搜尋與收集
3. 分析與驗證
4. 報告生成

使用方式：
    python research_agent.py --demo
    python research_agent.py -q "AI 晶片市場分析"
"""

import asyncio
import argparse
import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

load_dotenv()


# =============================================================================
# 資料結構
# =============================================================================

class ResearchPhase(Enum):
    """研究階段"""
    UNDERSTANDING = "understanding"
    PLANNING = "planning"
    SEARCHING = "searching"
    ANALYZING = "analyzing"
    VERIFYING = "verifying"
    REPORTING = "reporting"
    COMPLETED = "completed"


@dataclass
class ResearchQuery:
    """研究查詢"""
    question: str
    context: str = ""
    constraints: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def id(self) -> str:
        return hashlib.md5(
            f"{self.question}:{self.created_at.isoformat()}".encode()
        ).hexdigest()[:12]


@dataclass
class ResearchFinding:
    """研究發現"""
    content: str
    source_url: str
    relevance_score: float = 0.0
    verified: bool = False
    verification_notes: str = ""
    extracted_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "source": self.source_url,
            "relevance": self.relevance_score,
            "verified": self.verified
        }


@dataclass
class ResearchReport:
    """研究報告"""
    query: ResearchQuery
    summary: str
    key_findings: List[str]
    detailed_analysis: str
    sources: List[Dict[str, str]]
    confidence_score: float
    generated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_markdown(self) -> str:
        """轉換為 Markdown 格式"""
        lines = [
            f"# 研究報告",
            f"",
            f"**研究問題**: {self.query.question}",
            f"**生成時間**: {self.generated_at.strftime('%Y-%m-%d %H:%M')}",
            f"**信心分數**: {self.confidence_score:.0%}",
            f"",
            f"---",
            f"",
            f"## 摘要",
            f"",
            self.summary,
            f"",
            f"## 關鍵發現",
            f""
        ]

        for i, finding in enumerate(self.key_findings, 1):
            lines.append(f"{i}. {finding}")

        lines.extend([
            f"",
            f"## 詳細分析",
            f"",
            self.detailed_analysis,
            f"",
            f"## 參考來源",
            f""
        ])

        for source in self.sources:
            lines.append(f"- [{source.get('title', '來源')}]({source.get('url', '')})")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "query": self.query.question,
            "summary": self.summary,
            "key_findings": self.key_findings,
            "confidence_score": self.confidence_score,
            "sources_count": len(self.sources),
            "generated_at": self.generated_at.isoformat()
        }


@dataclass
class ResearchState:
    """研究狀態"""
    query: ResearchQuery
    phase: ResearchPhase = ResearchPhase.UNDERSTANDING
    findings: List[ResearchFinding] = field(default_factory=list)
    search_queries: List[str] = field(default_factory=list)
    verified_facts: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    tool_calls: int = 0
    tokens_used: int = 0


# =============================================================================
# 模擬 LLM 客戶端
# =============================================================================

class MockLLMClient:
    """模擬 LLM 客戶端（用於示範）"""

    def __init__(self):
        self._total_tokens = 0

    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        json_mode: bool = False
    ) -> str:
        """模擬生成"""
        await asyncio.sleep(0.1)

        last_message = messages[-1]["content"] if messages else ""

        if "分析" in last_message or "理解" in last_message:
            if json_mode:
                return json.dumps({
                    "intent": "research",
                    "keywords": ["AI", "晶片", "市場"],
                    "sub_questions": [
                        "AI 晶片的主要廠商有哪些？",
                        "各廠商的市場份額如何？",
                        "未來發展趨勢是什麼？"
                    ],
                    "domain": "科技",
                    "complexity": "medium"
                }, ensure_ascii=False)

        if "規劃" in last_message or "搜尋" in last_message:
            if json_mode:
                return json.dumps({
                    "search_queries": [
                        "AI 晶片市場份額 2024",
                        "NVIDIA GPU 市場分析",
                        "AMD Intel AI 晶片競爭"
                    ],
                    "search_strategy": "多角度搜尋",
                    "expected_sources": 5
                }, ensure_ascii=False)

        if "驗證" in last_message:
            if json_mode:
                return json.dumps({
                    "verified_claims": ["NVIDIA 市場領先", "AMD 追趕中"],
                    "contradictions": [],
                    "confidence_score": 85,
                    "needs_verification": []
                }, ensure_ascii=False)

        if "報告" in last_message or "總結" in last_message:
            if json_mode:
                return json.dumps({
                    "summary": "全球 AI 晶片市場由 NVIDIA 主導，市場份額約 80%。AMD 和 Intel 正在積極追趕，但短期內難以撼動 NVIDIA 的地位。",
                    "key_findings": [
                        "NVIDIA 憑藉 CUDA 生態系統建立護城河",
                        "AMD MI300 系列開始獲得市場認可",
                        "自研晶片趨勢明顯（Google TPU、Amazon Trainium）"
                    ],
                    "detailed_analysis": "AI 晶片市場正在快速成長，預計到 2028 年將達到 1000 億美元規模。NVIDIA 的優勢主要來自其完整的軟體生態系統和先發優勢。然而，隨著競爭加劇，市場格局可能會逐漸改變。",
                    "confidence_score": 0.85
                }, ensure_ascii=False)

        self._total_tokens += 100
        return "這是一個模擬回應。"

    @property
    def total_tokens(self) -> int:
        return self._total_tokens


# =============================================================================
# 研究模組
# =============================================================================

class UnderstandingModule:
    """問題理解模組"""

    PROMPT = """分析以下研究問題，提取關鍵資訊。

問題: {question}
{context}

請以 JSON 格式返回：
{{
    "intent": "研究意圖",
    "keywords": ["關鍵詞1", "關鍵詞2"],
    "sub_questions": ["子問題1", "子問題2"],
    "domain": "所屬領域",
    "complexity": "low/medium/high"
}}"""

    def __init__(self, llm_client):
        self.llm = llm_client

    async def process(self, state: ResearchState) -> Dict[str, Any]:
        """處理問題理解"""
        context = f"\n背景: {state.query.context}" if state.query.context else ""

        response = await self.llm.generate(
            messages=[{
                "role": "user",
                "content": self.PROMPT.format(
                    question=state.query.question,
                    context=context
                )
            }],
            json_mode=True,
            temperature=0.3
        )

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {
                "intent": "一般研究",
                "keywords": state.query.question.split()[:5],
                "sub_questions": [state.query.question],
                "domain": "未知",
                "complexity": "medium"
            }


class PlanningModule:
    """研究規劃模組"""

    PROMPT = """基於問題分析，制定研究計畫。

原始問題: {question}
問題分析: {understanding}

請以 JSON 格式返回：
{{
    "search_queries": ["搜尋查詢1", "搜尋查詢2"],
    "search_strategy": "搜尋策略說明",
    "expected_sources": 5
}}"""

    def __init__(self, llm_client):
        self.llm = llm_client

    async def process(
        self,
        state: ResearchState,
        understanding: Dict[str, Any]
    ) -> Dict[str, Any]:
        """制定研究計畫"""
        response = await self.llm.generate(
            messages=[{
                "role": "user",
                "content": self.PROMPT.format(
                    question=state.query.question,
                    understanding=json.dumps(understanding, ensure_ascii=False)
                )
            }],
            json_mode=True,
            temperature=0.5
        )

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            keywords = understanding.get("keywords", [])
            return {
                "search_queries": [
                    state.query.question,
                    " ".join(keywords[:3]) if keywords else state.query.question
                ],
                "search_strategy": "基本關鍵詞搜尋",
                "expected_sources": 5
            }


class SearchModule:
    """搜尋模組"""

    def __init__(self, llm_client, search_manager=None):
        self.llm = llm_client
        self.search_manager = search_manager
        self._last_findings: List[ResearchFinding] = []

    async def search(self, query: str) -> List[ResearchFinding]:
        """執行搜尋"""
        findings = []

        if self.search_manager:
            try:
                results = await self.search_manager.search(query, num_results=5)
                for result in results:
                    findings.append(ResearchFinding(
                        content=result.snippet,
                        source_url=result.url,
                        relevance_score=getattr(result, 'relevance_score', 0.5)
                    ))
            except Exception as e:
                print(f"    搜尋錯誤: {e}")
        else:
            # 模擬搜尋
            await asyncio.sleep(0.1)
            findings = [
                ResearchFinding(
                    content=f"關於「{query}」的搜尋結果 {i+1} - 這是一段模擬的內容摘要，包含相關的研究資訊。",
                    source_url=f"https://example.com/result/{hash(query) % 1000}/{i}",
                    relevance_score=0.9 - i * 0.1
                )
                for i in range(3)
            ]

        self._last_findings = findings
        return findings


class AnalysisModule:
    """分析模組"""

    PROMPT = """分析以下收集到的資訊，提取關鍵發現。

研究問題: {question}

收集的資訊:
{findings}

請提供詳細分析。"""

    def __init__(self, llm_client):
        self.llm = llm_client

    async def process(self, state: ResearchState) -> Dict[str, Any]:
        """分析收集的資訊"""
        findings_text = "\n\n".join([
            f"來源 {i+1} ({f.source_url}):\n{f.content}"
            for i, f in enumerate(state.findings[:10])
        ])

        response = await self.llm.generate(
            messages=[{
                "role": "user",
                "content": self.PROMPT.format(
                    question=state.query.question,
                    findings=findings_text
                )
            }],
            temperature=0.5
        )

        return {
            "analysis": response,
            "findings_count": len(state.findings),
            "sources_used": len(set(f.source_url for f in state.findings))
        }


class VerificationModule:
    """驗證模組"""

    PROMPT = """驗證分析結果的準確性。

分析結果: {analysis}
來源數量: {sources_count}

以 JSON 格式返回驗證結果。"""

    def __init__(self, llm_client):
        self.llm = llm_client

    async def process(
        self,
        state: ResearchState,
        analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """驗證分析結果"""
        response = await self.llm.generate(
            messages=[{
                "role": "user",
                "content": self.PROMPT.format(
                    analysis=analysis.get("analysis", ""),
                    sources_count=analysis.get("sources_used", 0)
                )
            }],
            json_mode=True,
            temperature=0.3
        )

        try:
            result = json.loads(response)
            return result.get("verified_claims", [])
        except json.JSONDecodeError:
            return []


class ReportingModule:
    """報告生成模組"""

    PROMPT = """基於研究結果，生成報告。

研究問題: {question}
分析結果: {analysis}
來源數量: {sources_count}

以 JSON 格式返回：
{{
    "summary": "摘要",
    "key_findings": ["發現1", "發現2"],
    "detailed_analysis": "詳細分析",
    "confidence_score": 0.0-1.0
}}"""

    def __init__(self, llm_client):
        self.llm = llm_client

    async def generate(
        self,
        state: ResearchState,
        analysis: Dict[str, Any]
    ) -> ResearchReport:
        """生成報告"""
        response = await self.llm.generate(
            messages=[{
                "role": "user",
                "content": self.PROMPT.format(
                    question=state.query.question,
                    analysis=analysis.get("analysis", ""),
                    sources_count=len(state.findings)
                )
            }],
            json_mode=True,
            temperature=0.5
        )

        try:
            data = json.loads(response)
        except json.JSONDecodeError:
            data = {
                "summary": analysis.get("analysis", "")[:200],
                "key_findings": ["研究完成"],
                "detailed_analysis": analysis.get("analysis", ""),
                "confidence_score": 0.7
            }

        sources = [
            {"title": f"來源 {i+1}", "url": f.source_url}
            for i, f in enumerate(state.findings[:10])
        ]

        return ResearchReport(
            query=state.query,
            summary=data.get("summary", ""),
            key_findings=data.get("key_findings", []),
            detailed_analysis=data.get("detailed_analysis", ""),
            sources=sources,
            confidence_score=data.get("confidence_score", 0.7),
            metadata={
                "tool_calls": state.tool_calls,
                "findings_count": len(state.findings),
                "elapsed_seconds": (datetime.now() - state.start_time).total_seconds()
            }
        )


# =============================================================================
# 研究協調器
# =============================================================================

class ResearchCoordinator:
    """
    研究協調器

    ‹1› 管理研究流程
    ‹2› 協調各模組工作
    ‹3› 維護研究狀態
    """

    def __init__(
        self,
        llm_client=None,
        search_manager=None,
        memory_manager=None,
        max_iterations: int = 20,
        max_sources: int = 10
    ):
        self.llm = llm_client or MockLLMClient()
        self.search_manager = search_manager
        self.memory_manager = memory_manager
        self.max_iterations = max_iterations
        self.max_sources = max_sources

        self._understanding = UnderstandingModule(self.llm)
        self._planning = PlanningModule(self.llm)
        self._search = SearchModule(self.llm, self.search_manager)
        self._analysis = AnalysisModule(self.llm)
        self._verification = VerificationModule(self.llm)
        self._reporting = ReportingModule(self.llm)

    async def research(self, question: str, context: str = "") -> ResearchReport:
        """執行完整研究流程"""
        query = ResearchQuery(question=question, context=context)
        state = ResearchState(query=query)

        print(f"\n{'='*60}")
        print(f"🔬 開始研究: {question[:50]}...")
        print(f"{'='*60}")

        try:
            # 問題理解
            state.phase = ResearchPhase.UNDERSTANDING
            print(f"\n[1/6] 📖 理解問題...")
            understanding = await self._understanding.process(state)
            state.tool_calls += 1

            # 研究規劃
            state.phase = ResearchPhase.PLANNING
            print(f"\n[2/6] 📝 制定研究計畫...")
            plan = await self._planning.process(state, understanding)
            state.search_queries = plan.get("search_queries", [])
            state.tool_calls += 1

            # 資訊收集
            state.phase = ResearchPhase.SEARCHING
            print(f"\n[3/6] 🔍 收集資訊...")
            for i, sq in enumerate(state.search_queries[:5], 1):
                print(f"    搜尋 {i}: {sq}")
                findings = await self._search.search(sq)
                state.findings.extend(findings[:3])
                state.tool_calls += 1

            print(f"    共收集 {len(state.findings)} 條資訊")

            # 分析整合
            state.phase = ResearchPhase.ANALYZING
            print(f"\n[4/6] 🧠 分析資訊...")
            analysis = await self._analysis.process(state)
            state.tool_calls += 1

            # 事實查證
            state.phase = ResearchPhase.VERIFYING
            print(f"\n[5/6] ✓ 驗證事實...")
            verified = await self._verification.process(state, analysis)
            state.verified_facts = verified
            state.tool_calls += 1

            # 報告生成
            state.phase = ResearchPhase.REPORTING
            print(f"\n[6/6] 📄 生成報告...")
            report = await self._reporting.generate(state, analysis)
            state.phase = ResearchPhase.COMPLETED
            state.tool_calls += 1

            # 統計
            elapsed = (datetime.now() - state.start_time).total_seconds()
            print(f"\n{'='*60}")
            print(f"✅ 研究完成！")
            print(f"   耗時: {elapsed:.1f} 秒")
            print(f"   工具調用: {state.tool_calls} 次")
            print(f"   來源數量: {len(state.findings)}")
            print(f"   信心分數: {report.confidence_score:.0%}")
            print(f"{'='*60}")

            return report

        except Exception as e:
            state.errors.append(str(e))
            print(f"\n❌ 研究失敗: {e}")
            raise


# =============================================================================
# 深度研究代理人
# =============================================================================

class DeepResearchAgent:
    """
    深度研究代理人

    ‹1› 整合所有研究能力
    ‹2› 支援多輪研究
    ‹3› 提供完整的研究報告
    """

    def __init__(
        self,
        llm_client=None,
        search_manager=None,
        memory_manager=None,
        config: Dict[str, Any] = None
    ):
        config = config or {}

        self.coordinator = ResearchCoordinator(
            llm_client=llm_client,
            search_manager=search_manager,
            memory_manager=memory_manager,
            max_iterations=config.get("max_iterations", 20),
            max_sources=config.get("max_sources", 10)
        )

        self._history: List[ResearchReport] = []

    async def research(
        self,
        question: str,
        context: str = "",
        verify: bool = True
    ) -> ResearchReport:
        """執行研究"""
        report = await self.coordinator.research(question, context)
        self._history.append(report)
        return report

    async def follow_up(self, follow_up_question: str) -> ResearchReport:
        """追問研究"""
        if not self._history:
            return await self.research(follow_up_question)

        previous = self._history[-1]
        context = f"之前的研究問題: {previous.query.question}\n摘要: {previous.summary}"

        return await self.research(follow_up_question, context=context)

    def get_history(self) -> List[ResearchReport]:
        """獲取研究歷史"""
        return self._history.copy()

    def clear_history(self) -> None:
        """清除研究歷史"""
        self._history.clear()


# =============================================================================
# 示範
# =============================================================================

async def demo():
    """示範研究代理人功能"""
    print("=" * 60)
    print("🔬 深度研究代理人示範")
    print("=" * 60)

    agent = DeepResearchAgent(
        config={
            "max_iterations": 10,
            "max_sources": 5
        }
    )

    question = "分析 2024 年 AI 晶片市場的競爭格局"

    report = await agent.research(question, verify=True)

    print("\n" + "=" * 60)
    print("📄 研究報告")
    print("=" * 60)
    print(report.to_markdown())

    # 追問
    print("\n" + "-" * 40)
    print("📝 執行追問研究...")
    print("-" * 40)

    follow_up = "NVIDIA 的競爭優勢是什麼？"
    follow_up_report = await agent.follow_up(follow_up)

    print("\n追問報告摘要:")
    print(follow_up_report.summary)


def main():
    parser = argparse.ArgumentParser(description="深度研究代理人")
    parser.add_argument("--demo", action="store_true", help="執行示範")
    parser.add_argument("-q", "--question", type=str, help="研究問題")

    args = parser.parse_args()

    if args.question:
        async def research_question():
            agent = DeepResearchAgent()
            report = await agent.research(args.question)
            print(report.to_markdown())

        asyncio.run(research_question())
    else:
        asyncio.run(demo())


if __name__ == "__main__":
    main()
