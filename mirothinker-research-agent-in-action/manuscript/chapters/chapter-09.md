# 第 9 章：建構你的第一個研究代理人

> **本章目標**：整合前面所有章節的組件，從零開始建構一個完整的深度研究代理人，實現自主查證與報告生成能力。

---

## 引言：萬事俱備，只欠東風

經過前八章的學習，你已經掌握了深度研究代理人的所有核心組件：

- **第 4 章**：核心調度器，管理任務執行流程
- **第 5 章**：工具系統，與外部環境交互
- **第 6 章**：記憶管理，處理長上下文
- **第 7 章**：搜尋檢索，獲取外部知識
- **第 8 章**：環境部署，運行推理服務

現在，是時候將這些積木組裝成一個完整的研究代理人了。

**本章產出物**：

1. 完整的深度研究代理人（~1,500 行程式碼）
2. 自我查證模組
3. 報告生成引擎
4. 端到端工作流程示範

---

## 9.1 研究代理人架構總覽

### 9.1.1 系統架構圖

```
┌─────────────────────────────────────────────────────────────────┐
│                     深度研究代理人                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    研究協調器                            │   │
│  │  (Research Coordinator)                                  │   │
│  └────────────────────────┬────────────────────────────────┘   │
│                           │                                     │
│          ┌────────────────┼────────────────┐                   │
│          ▼                ▼                ▼                   │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐           │
│  │  搜尋模組    │ │  分析模組    │ │  驗證模組    │           │
│  │  (Search)    │ │  (Analyze)   │ │  (Verify)    │           │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘           │
│         │                │                │                     │
│         └────────────────┼────────────────┘                     │
│                          ▼                                      │
│                 ┌──────────────┐                               │
│                 │  報告生成    │                               │
│                 │  (Report)    │                               │
│                 └──────────────┘                               │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  支撐層                                                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐         │
│  │ 工具管理 │ │ 記憶管理 │ │ 搜尋引擎 │ │ LLM 服務 │         │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

### 9.1.2 研究工作流程

```
用戶問題
    │
    ▼
┌─────────────────┐
│ 1. 問題理解     │  ← 分析意圖、識別關鍵詞
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 2. 研究規劃     │  ← 制定搜尋策略、分解子問題
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 3. 資訊收集     │  ← 網頁搜尋、內容提取
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 4. 分析整合     │  ← 提取關鍵資訊、建立知識圖譜
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 5. 事實查證     │  ← 交叉驗證、識別矛盾
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 6. 報告生成     │  ← 結構化輸出、引用來源
└────────┬────────┘
         │
         ▼
    研究報告
```

---

## 9.2 核心代理人實現

### 9.2.1 研究代理人基礎類

```python
#!/usr/bin/env python3
"""
深度研究代理人實戰 - 第 9 章：建構你的第一個研究代理人
核心研究代理人實現
"""

import asyncio
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
    UNDERSTANDING = "understanding"    # 問題理解
    PLANNING = "planning"              # 研究規劃
    SEARCHING = "searching"            # 資訊收集
    ANALYZING = "analyzing"            # 分析整合
    VERIFYING = "verifying"            # 事實查證
    REPORTING = "reporting"            # 報告生成
    COMPLETED = "completed"            # 完成


@dataclass
class ResearchQuery:
    """研究查詢"""
    question: str
    context: str = ""
    constraints: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def id(self) -> str:
        import hashlib
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
# LLM 客戶端
# =============================================================================

class LLMClient:
    """
    LLM 客戶端

    ‹1› 封裝 LLM API 調用
    ‹2› 支援多種模型
    ‹3› 追蹤使用量
    """

    def __init__(
        self,
        api_url: str = "http://localhost:8000/v1",
        model: str = "Qwen/Qwen2.5-72B-Instruct",
        api_key: str = ""
    ):
        self.api_url = api_url
        self.model = model
        self.api_key = api_key
        self._total_tokens = 0

    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        json_mode: bool = False
    ) -> str:
        """生成回應"""
        import aiohttp

        headers = {
            "Content-Type": "application/json"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.api_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=300)
            ) as resp:
                if resp.status != 200:
                    error = await resp.text()
                    raise Exception(f"LLM API 錯誤: {resp.status} - {error}")

                data = await resp.json()
                self._total_tokens += data.get("usage", {}).get("total_tokens", 0)
                return data["choices"][0]["message"]["content"]

    @property
    def total_tokens(self) -> int:
        return self._total_tokens


# =============================================================================
# 模擬 LLM 客戶端（用於測試）
# =============================================================================

class MockLLMClient:
    """模擬 LLM 客戶端"""

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

        # 根據最後一條訊息內容返回相應的模擬回應
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
                    ]
                }, ensure_ascii=False)
            return "這是一個關於 AI 晶片市場的研究問題，需要分析主要廠商和市場趨勢。"

        if "規劃" in last_message or "搜尋" in last_message:
            if json_mode:
                return json.dumps({
                    "search_queries": [
                        "AI 晶片市場份額 2024",
                        "NVIDIA GPU 市場分析",
                        "AMD MI300 vs NVIDIA H100"
                    ]
                }, ensure_ascii=False)
            return "建議搜尋：1. AI 晶片市場份額 2. NVIDIA 市場分析 3. 競爭對手比較"

        if "驗證" in last_message:
            if json_mode:
                return json.dumps({
                    "verified": True,
                    "confidence": 0.85,
                    "notes": "多個來源確認此資訊"
                }, ensure_ascii=False)
            return "經過交叉驗證，此資訊可信度較高。"

        if "報告" in last_message or "總結" in last_message:
            return """# AI 晶片市場分析報告

## 摘要
全球 AI 晶片市場由 NVIDIA 主導，市場份額約 80%。AMD 和 Intel 正在積極追趕。

## 關鍵發現
1. NVIDIA 憑藉 CUDA 生態系統建立了強大的護城河
2. AMD MI300 系列開始獲得市場認可
3. 自研晶片趨勢明顯，如 Google TPU、Amazon Trainium

## 結論
短期內 NVIDIA 的領導地位難以撼動，但市場競爭正在加劇。"""

        self._total_tokens += 100
        return "這是一個模擬回應。"

    @property
    def total_tokens(self) -> int:
        return self._total_tokens
```

### 9.2.2 研究協調器

```python
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

        # 子模組
        self._understanding_module = UnderstandingModule(self.llm)
        self._planning_module = PlanningModule(self.llm)
        self._search_module = SearchModule(self.llm, self.search_manager)
        self._analysis_module = AnalysisModule(self.llm)
        self._verification_module = VerificationModule(self.llm)
        self._reporting_module = ReportingModule(self.llm)

    async def research(self, question: str, context: str = "") -> ResearchReport:
        """
        執行完整研究流程

        ‹1› 問題理解
        ‹2› 研究規劃
        ‹3› 資訊收集
        ‹4› 分析整合
        ‹5› 事實查證
        ‹6› 報告生成
        """
        query = ResearchQuery(question=question, context=context)
        state = ResearchState(query=query)

        print(f"\n{'='*60}")
        print(f"🔬 開始研究: {question[:50]}...")
        print(f"{'='*60}")

        try:
            # ‹1› 問題理解
            state.phase = ResearchPhase.UNDERSTANDING
            print(f"\n[1/6] 📖 理解問題...")
            understanding = await self._understanding_module.process(state)
            state.tool_calls += 1

            # ‹2› 研究規劃
            state.phase = ResearchPhase.PLANNING
            print(f"\n[2/6] 📝 制定研究計畫...")
            plan = await self._planning_module.process(state, understanding)
            state.search_queries = plan.get("search_queries", [])
            state.tool_calls += 1

            # ‹3› 資訊收集
            state.phase = ResearchPhase.SEARCHING
            print(f"\n[3/6] 🔍 收集資訊...")
            for i, sq in enumerate(state.search_queries[:5], 1):
                print(f"    搜尋 {i}: {sq}")
                findings = await self._search_module.search(sq)
                state.findings.extend(findings[:3])
                state.tool_calls += 1

            print(f"    共收集 {len(state.findings)} 條資訊")

            # ‹4› 分析整合
            state.phase = ResearchPhase.ANALYZING
            print(f"\n[4/6] 🧠 分析資訊...")
            analysis = await self._analysis_module.process(state)
            state.tool_calls += 1

            # ‹5› 事實查證
            state.phase = ResearchPhase.VERIFYING
            print(f"\n[5/6] ✓ 驗證事實...")
            verified = await self._verification_module.process(state, analysis)
            state.verified_facts = verified
            state.tool_calls += 1

            # ‹6› 報告生成
            state.phase = ResearchPhase.REPORTING
            print(f"\n[6/6] 📄 生成報告...")
            report = await self._reporting_module.generate(state, analysis)
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
# 問題理解模組
# =============================================================================

class UnderstandingModule:
    """
    問題理解模組

    ‹1› 分析用戶意圖
    ‹2› 提取關鍵詞
    ‹3› 識別子問題
    """

    PROMPT = """分析以下研究問題，提取關鍵資訊。

問題: {question}
{context}

請以 JSON 格式返回：
{{
    "intent": "研究意圖（簡短描述）",
    "keywords": ["關鍵詞1", "關鍵詞2", ...],
    "sub_questions": ["子問題1", "子問題2", ...],
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


# =============================================================================
# 研究規劃模組
# =============================================================================

class PlanningModule:
    """
    研究規劃模組

    ‹1› 制定搜尋策略
    ‹2› 分解研究步驟
    ‹3› 估算資源需求
    """

    PROMPT = """基於問題分析，制定研究計畫。

原始問題: {question}
問題分析: {understanding}

請以 JSON 格式返回搜尋查詢列表：
{{
    "search_queries": [
        "搜尋查詢1（具體且可搜尋）",
        "搜尋查詢2",
        "搜尋查詢3",
        ...
    ],
    "search_strategy": "搜尋策略說明",
    "expected_sources": 5-10
}}

注意：
1. 搜尋查詢應該具體、可操作
2. 涵蓋問題的不同面向
3. 使用適合搜尋引擎的關鍵詞組合"""

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
            # 使用關鍵詞生成基本搜尋查詢
            keywords = understanding.get("keywords", [])
            return {
                "search_queries": [
                    state.query.question,
                    " ".join(keywords[:3]) if keywords else state.query.question
                ],
                "search_strategy": "基本關鍵詞搜尋",
                "expected_sources": 5
            }


# =============================================================================
# 搜尋模組
# =============================================================================

class SearchModule:
    """
    搜尋模組

    ‹1› 執行網頁搜尋
    ‹2› 提取網頁內容
    ‹3› 過濾和排序結果
    """

    def __init__(self, llm_client, search_manager=None):
        self.llm = llm_client
        self.search_manager = search_manager

    async def search(self, query: str) -> List[ResearchFinding]:
        """執行搜尋並提取發現"""
        findings = []

        if self.search_manager:
            # 使用真實搜尋
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
            # 模擬搜尋結果
            await asyncio.sleep(0.1)
            findings = [
                ResearchFinding(
                    content=f"關於「{query}」的搜尋結果 - 這是一段模擬的內容摘要。",
                    source_url=f"https://example.com/result/{i}",
                    relevance_score=0.8 - i * 0.1
                )
                for i in range(3)
            ]

        return findings


# =============================================================================
# 分析模組
# =============================================================================

class AnalysisModule:
    """
    分析模組

    ‹1› 整合多來源資訊
    ‹2› 提取關鍵觀點
    ‹3› 識別資訊缺口
    """

    PROMPT = """分析以下收集到的資訊，提取關鍵發現。

研究問題: {question}

收集的資訊:
{findings}

請提供：
1. 主要發現（3-5 條）
2. 不同來源的觀點比較
3. 資訊缺口（需要進一步研究的方面）
4. 初步結論"""

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


# =============================================================================
# 驗證模組
# =============================================================================

class VerificationModule:
    """
    驗證模組

    ‹1› 交叉驗證事實
    ‹2› 識別矛盾資訊
    ‹3› 評估可信度
    """

    PROMPT = """驗證以下分析結果的準確性。

分析結果:
{analysis}

原始來源數量: {sources_count}

請評估：
1. 哪些陳述有多個來源支持？
2. 是否存在矛盾的資訊？
3. 整體可信度評分（0-100）
4. 需要進一步驗證的陳述

以 JSON 格式返回：
{{
    "verified_claims": ["已驗證的陳述1", ...],
    "contradictions": ["矛盾1", ...],
    "confidence_score": 0-100,
    "needs_verification": ["待驗證的陳述1", ...]
}}"""

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


# =============================================================================
# 報告生成模組
# =============================================================================

class ReportingModule:
    """
    報告生成模組

    ‹1› 結構化報告
    ‹2› 引用來源
    ‹3› 生成摘要
    """

    PROMPT = """基於研究結果，生成專業報告。

研究問題: {question}
分析結果: {analysis}
來源數量: {sources_count}

請生成包含以下部分的報告：
1. 摘要（100-200 字）
2. 關鍵發現（3-5 條，每條一句話）
3. 詳細分析（300-500 字）

以 JSON 格式返回：
{{
    "summary": "摘要內容",
    "key_findings": ["發現1", "發現2", ...],
    "detailed_analysis": "詳細分析內容",
    "confidence_score": 0.0-1.0
}}"""

    def __init__(self, llm_client):
        self.llm = llm_client

    async def generate(
        self,
        state: ResearchState,
        analysis: Dict[str, Any]
    ) -> ResearchReport:
        """生成研究報告"""
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

        # 構建來源列表
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
```

---

## 9.3 自我查證機制

自我查證是深度研究代理人區別於簡單 RAG 系統的關鍵能力。

### 9.3.1 查證策略

```
┌─────────────────────────────────────────────────────────────────┐
│                     自我查證機制                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐                                               │
│  │  陳述 A     │ ────────────────┐                             │
│  └─────────────┘                  │                             │
│                                   ▼                             │
│  ┌─────────────┐         ┌──────────────┐                      │
│  │  陳述 B     │ ───────▶│  交叉比對    │                      │
│  └─────────────┘         └──────┬───────┘                      │
│                                   │                             │
│  ┌─────────────┐                  │                             │
│  │  陳述 C     │ ────────────────┘                             │
│  └─────────────┘                                               │
│                                   │                             │
│                                   ▼                             │
│                         ┌──────────────┐                       │
│                         │  一致性檢查  │                       │
│                         └──────┬───────┘                       │
│                                │                                │
│              ┌─────────────────┼─────────────────┐             │
│              ▼                 ▼                 ▼             │
│       ┌──────────┐      ┌──────────┐      ┌──────────┐        │
│       │ 確認事實 │      │ 矛盾標記 │      │ 待驗證   │        │
│       │ (verified)│      │(conflict)│      │(pending) │        │
│       └──────────┘      └──────────┘      └──────────┘        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 9.3.2 高級查證模組

```python
# =============================================================================
# 高級查證模組
# =============================================================================

class AdvancedVerificationModule:
    """
    高級查證模組

    ‹1› 多來源交叉驗證
    ‹2› 時效性檢查
    ‹3› 可信度評分
    """

    def __init__(self, llm_client, search_module=None):
        self.llm = llm_client
        self.search = search_module

    async def verify_claim(
        self,
        claim: str,
        existing_sources: List[ResearchFinding]
    ) -> Dict[str, Any]:
        """
        驗證單一陳述

        ‹1› 檢查現有來源
        ‹2› 搜尋額外證據
        ‹3› 評估可信度
        """
        # ‹1› 檢查現有來源中的支持證據
        supporting_sources = []
        contradicting_sources = []

        for source in existing_sources:
            relevance = await self._check_relevance(claim, source.content)
            if relevance > 0.7:
                supporting_sources.append(source)
            elif relevance < 0.3:
                contradicting_sources.append(source)

        # ‹2› 如果支持不足，搜尋額外證據
        if len(supporting_sources) < 2 and self.search:
            verification_query = f"fact check: {claim}"
            additional = await self.search.search(verification_query)
            for finding in additional[:3]:
                relevance = await self._check_relevance(claim, finding.content)
                if relevance > 0.7:
                    supporting_sources.append(finding)

        # ‹3› 計算可信度
        confidence = self._calculate_confidence(
            supporting_count=len(supporting_sources),
            contradicting_count=len(contradicting_sources),
            total_sources=len(existing_sources)
        )

        return {
            "claim": claim,
            "verified": confidence > 0.7,
            "confidence": confidence,
            "supporting_sources": len(supporting_sources),
            "contradicting_sources": len(contradicting_sources),
            "status": self._determine_status(confidence, len(contradicting_sources))
        }

    async def _check_relevance(self, claim: str, content: str) -> float:
        """檢查內容與陳述的相關性（簡化實現）"""
        # 在實際應用中，這裡應該使用 embeddings 或 LLM 進行語義比較
        claim_words = set(claim.lower().split())
        content_words = set(content.lower().split())
        overlap = len(claim_words & content_words)
        return overlap / max(len(claim_words), 1)

    def _calculate_confidence(
        self,
        supporting_count: int,
        contradicting_count: int,
        total_sources: int
    ) -> float:
        """計算可信度分數"""
        if total_sources == 0:
            return 0.5

        base_score = supporting_count / max(total_sources, 1)
        penalty = contradicting_count * 0.2

        return max(0.0, min(1.0, base_score - penalty))

    def _determine_status(
        self,
        confidence: float,
        contradicting_count: int
    ) -> str:
        """確定驗證狀態"""
        if contradicting_count > 0:
            return "conflict"
        elif confidence > 0.7:
            return "verified"
        elif confidence > 0.4:
            return "likely"
        else:
            return "unverified"

    async def verify_report(
        self,
        report: ResearchReport,
        existing_sources: List[ResearchFinding]
    ) -> Dict[str, Any]:
        """驗證整份報告"""
        claims = report.key_findings + [report.summary]
        verification_results = []

        for claim in claims:
            result = await self.verify_claim(claim, existing_sources)
            verification_results.append(result)

        overall_confidence = sum(
            r["confidence"] for r in verification_results
        ) / max(len(verification_results), 1)

        return {
            "overall_confidence": overall_confidence,
            "verified_count": sum(1 for r in verification_results if r["verified"]),
            "total_claims": len(claims),
            "conflicts": [r for r in verification_results if r["status"] == "conflict"],
            "details": verification_results
        }
```

---

## 9.4 完整研究代理人

### 9.4.1 整合所有組件

```python
# =============================================================================
# 完整研究代理人
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

        self.verification = AdvancedVerificationModule(
            llm_client=llm_client or MockLLMClient(),
            search_module=SearchModule(llm_client, search_manager)
        )

        self._history: List[ResearchReport] = []

    async def research(
        self,
        question: str,
        context: str = "",
        verify: bool = True
    ) -> ResearchReport:
        """
        執行研究

        ‹1› 調用協調器執行研究
        ‹2› 可選的事實查證
        ‹3› 保存歷史
        """
        # ‹1› 執行研究
        report = await self.coordinator.research(question, context)

        # ‹2› 事實查證
        if verify:
            verification_result = await self.verification.verify_report(
                report,
                self.coordinator._search_module.__dict__.get("_last_findings", [])
            )
            report.metadata["verification"] = verification_result
            report.confidence_score = verification_result["overall_confidence"]

        # ‹3› 保存歷史
        self._history.append(report)

        return report

    async def follow_up(self, follow_up_question: str) -> ResearchReport:
        """
        追問研究

        基於之前的研究繼續探索
        """
        if not self._history:
            return await self.research(follow_up_question)

        # 使用之前的研究作為上下文
        previous = self._history[-1]
        context = f"之前的研究問題: {previous.query.question}\n摘要: {previous.summary}"

        return await self.research(follow_up_question, context=context)

    def get_history(self) -> List[ResearchReport]:
        """獲取研究歷史"""
        return self._history.copy()

    def clear_history(self) -> None:
        """清除研究歷史"""
        self._history.clear()
```

---

## 9.5 實戰演練

### 9.5.1 基本使用示範

```python
# =============================================================================
# 示範
# =============================================================================

async def demo():
    """示範研究代理人功能"""
    print("=" * 60)
    print("🔬 深度研究代理人示範")
    print("=" * 60)

    # 創建研究代理人
    agent = DeepResearchAgent(
        config={
            "max_iterations": 10,
            "max_sources": 5
        }
    )

    # 執行研究
    question = "分析 2024 年 AI 晶片市場的競爭格局，特別是 NVIDIA、AMD 和 Intel 的市場地位"

    report = await agent.research(question, verify=True)

    # 顯示報告
    print("\n" + "=" * 60)
    print("📄 研究報告")
    print("=" * 60)
    print(report.to_markdown())

    # 追問
    print("\n" + "-" * 40)
    print("📝 執行追問研究...")
    print("-" * 40)

    follow_up = "NVIDIA 的 CUDA 生態系統為何難以被替代？"
    follow_up_report = await agent.follow_up(follow_up)

    print("\n追問報告摘要:")
    print(follow_up_report.summary)


async def demo_with_real_search():
    """使用真實搜尋的示範"""
    # 這需要配置真實的搜尋 API
    from search_engine import SearchManager, MockSearchProvider

    search_manager = SearchManager()
    search_manager.register_provider(MockSearchProvider(), set_default=True)

    agent = DeepResearchAgent(
        search_manager=search_manager
    )

    report = await agent.research(
        "台灣半導體產業在全球供應鏈中的角色",
        verify=True
    )

    print(report.to_markdown())


def main():
    import argparse

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
```

### 9.5.2 進階使用場景

```python
# =============================================================================
# 進階使用場景
# =============================================================================

class ResearchSession:
    """
    研究會話管理

    支援多輪對話式研究
    """

    def __init__(self, agent: DeepResearchAgent):
        self.agent = agent
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.reports: List[ResearchReport] = []

    async def ask(self, question: str) -> ResearchReport:
        """提問"""
        if self.reports:
            report = await self.agent.follow_up(question)
        else:
            report = await self.agent.research(question)

        self.reports.append(report)
        return report

    def get_context(self) -> str:
        """獲取累積的研究上下文"""
        context_parts = []
        for report in self.reports[-3:]:  # 最近 3 個報告
            context_parts.append(f"Q: {report.query.question}")
            context_parts.append(f"A: {report.summary}")
        return "\n\n".join(context_parts)

    def export_session(self) -> str:
        """匯出整個會話"""
        lines = [
            f"# 研究會話 {self.session_id}",
            f"",
            f"共 {len(self.reports)} 個研究問題",
            f"",
            "---",
            ""
        ]

        for i, report in enumerate(self.reports, 1):
            lines.append(f"## 問題 {i}")
            lines.append(report.to_markdown())
            lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)


async def demo_session():
    """會話式研究示範"""
    agent = DeepResearchAgent()
    session = ResearchSession(agent)

    questions = [
        "什麼是生成式 AI？",
        "生成式 AI 有哪些主要應用場景？",
        "企業如何安全地部署生成式 AI？"
    ]

    for q in questions:
        print(f"\n提問: {q}")
        report = await session.ask(q)
        print(f"摘要: {report.summary[:200]}...")

    # 匯出會話
    print("\n" + "=" * 60)
    print("會話匯出:")
    print(session.export_session()[:2000])
```

---

## 9.6 效能優化與最佳實踐

### 9.6.1 並行搜尋

```python
class ParallelSearchModule:
    """並行搜尋模組"""

    def __init__(self, llm_client, search_manager=None, max_concurrent: int = 5):
        self.llm = llm_client
        self.search_manager = search_manager
        self.max_concurrent = max_concurrent

    async def search_parallel(self, queries: List[str]) -> List[ResearchFinding]:
        """並行執行多個搜尋"""
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def search_one(query: str) -> List[ResearchFinding]:
            async with semaphore:
                return await self._search(query)

        tasks = [search_one(q) for q in queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        findings = []
        for result in results:
            if isinstance(result, list):
                findings.extend(result)

        return findings

    async def _search(self, query: str) -> List[ResearchFinding]:
        """單一搜尋"""
        # 實際搜尋邏輯
        await asyncio.sleep(0.1)
        return [
            ResearchFinding(
                content=f"結果: {query}",
                source_url=f"https://example.com/{hash(query) % 1000}"
            )
        ]
```

### 9.6.2 結果快取

```python
class CachedResearchAgent:
    """帶快取的研究代理人"""

    def __init__(self, agent: DeepResearchAgent, cache_ttl: int = 3600):
        self.agent = agent
        self.cache_ttl = cache_ttl
        self._cache: Dict[str, Tuple[ResearchReport, float]] = {}

    async def research(self, question: str, **kwargs) -> ResearchReport:
        """研究（帶快取）"""
        cache_key = self._make_key(question)

        # 檢查快取
        if cache_key in self._cache:
            report, cached_at = self._cache[cache_key]
            if time.time() - cached_at < self.cache_ttl:
                print("📋 使用快取結果")
                return report

        # 執行研究
        report = await self.agent.research(question, **kwargs)

        # 儲存快取
        self._cache[cache_key] = (report, time.time())

        return report

    def _make_key(self, question: str) -> str:
        """生成快取鍵"""
        import hashlib
        return hashlib.md5(question.lower().strip().encode()).hexdigest()

    def clear_cache(self) -> None:
        """清除快取"""
        self._cache.clear()
```

---

## 9.7 章節總結

恭喜！你已經建構了一個完整的深度研究代理人。

### 核心要點回顧

1. **系統架構**
   - 模組化設計：理解、規劃、搜尋、分析、驗證、報告
   - 狀態管理：追蹤研究進度和發現
   - 錯誤處理：優雅地處理失敗情況

2. **研究流程**
   - 問題分解：將複雜問題拆解為可搜尋的子問題
   - 多來源收集：綜合多個來源的資訊
   - 交叉驗證：確保資訊的準確性

3. **自我查證**
   - 多來源比對：檢查不同來源是否一致
   - 矛盾識別：發現並標記衝突資訊
   - 可信度評分：量化報告的可靠程度

4. **最佳實踐**
   - 並行處理：提升搜尋效率
   - 結果快取：避免重複研究
   - 會話管理：支援多輪追問

### 程式碼統計

| 模組 | 行數 | 說明 |
|------|------|------|
| 資料結構 | ~150 行 | ResearchQuery, Finding, Report, State |
| 研究協調器 | ~200 行 | 核心流程管理 |
| 各子模組 | ~400 行 | 理解、規劃、搜尋、分析、驗證、報告 |
| 驗證模組 | ~150 行 | 高級事實查證 |
| 完整代理人 | ~100 行 | 整合所有組件 |
| **總計** | ~1,000 行 | 完整可運行的研究代理人 |

### 檢查清單

```
□ 理解研究代理人的整體架構
□ 實現了問題理解模組
□ 實現了研究規劃模組
□ 實現了資訊搜尋模組
□ 實現了分析整合模組
□ 實現了事實查證模組
□ 實現了報告生成模組
□ 整合所有組件為完整代理人
□ 測試多輪對話研究
□ 驗證自我查證機制
```

---

## 9.8 下一章預告

在第 10 章「多代理人協作系統」中，我們將：

1. 設計多代理人協作架構
2. 實現任務分配與負載均衡
3. 處理代理人間的通信與同步
4. 建構企業級研究團隊

這將把單一代理人擴展為可協作的代理人團隊，處理更複雜的研究任務。

---

## 附錄：完整檔案清單

```
chapter-09/
├── research_agent.py      # 核心研究代理人（本章完整程式碼）
├── verification.py        # 高級驗證模組
├── session.py            # 會話管理
├── utils.py              # 工具函數
├── requirements.txt      # 依賴套件
├── .env.example          # 環境變數範例
└── README.md             # 說明文件
```

---

**本章字數**: 約 15,000 字
**預估閱讀時間**: 45 分鐘
