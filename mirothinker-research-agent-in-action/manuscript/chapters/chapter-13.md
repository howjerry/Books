# 第 13 章：幻覺處理與事實查核

> **本章目標**：深入理解 LLM 幻覺的成因與類型，掌握時序敏感訓練、因果律約束等進階技術，建構自動化的事實查核系統。

---

## 13.1 認識 LLM 幻覺

「你確定這是真的嗎？」

這可能是使用 LLM 進行深度研究時最常問的問題。LLM 幻覺（Hallucination）是指模型生成看起來合理但實際上不正確或虛構的資訊。對於深度研究代理人來說，這是最大的挑戰之一。

### 13.1.1 幻覺的類型

```
┌─────────────────────────────────────────────────────────────────┐
│                    LLM 幻覺分類                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  1. 事實性幻覺 (Factual Hallucination)                    │  │
│  │     └── 生成與現實不符的事實陳述                          │  │
│  │     例：「愛因斯坦在 1921 年獲得諾貝爾化學獎」            │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  2. 虛構性幻覺 (Fabrication Hallucination)                │  │
│  │     └── 完全虛構不存在的實體或事件                        │  │
│  │     例：引用不存在的論文或專家                            │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  3. 時序性幻覺 (Temporal Hallucination)                   │  │
│  │     └── 混淆事件的時間順序或時效性                        │  │
│  │     例：將過時資訊當作最新資訊                            │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  4. 推理性幻覺 (Reasoning Hallucination)                  │  │
│  │     └── 推理過程中的邏輯錯誤                              │  │
│  │     例：錯誤的因果推斷或數學計算                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  5. 來源性幻覺 (Source Hallucination)                     │  │
│  │     └── 錯誤歸因或捏造引用來源                            │  │
│  │     例：「根據《自然》期刊 2023 年的研究...」（不存在）   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 13.1.2 幻覺的成因分析

```python
#!/usr/bin/env python3
"""
幻覺成因分析框架

分析和分類 LLM 幻覺的成因
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum


class HallucinationType(Enum):
    """幻覺類型"""
    FACTUAL = "factual"           # 事實性幻覺
    FABRICATION = "fabrication"   # 虛構性幻覺
    TEMPORAL = "temporal"         # 時序性幻覺
    REASONING = "reasoning"       # 推理性幻覺
    SOURCE = "source"             # 來源性幻覺


class HallucinationCause(Enum):
    """幻覺成因"""
    TRAINING_DATA_OUTDATED = "training_data_outdated"    # 訓練資料過時
    TRAINING_DATA_ERROR = "training_data_error"          # 訓練資料錯誤
    KNOWLEDGE_CUTOFF = "knowledge_cutoff"                # 知識截止日期
    PATTERN_OVERFITTING = "pattern_overfitting"          # 模式過擬合
    CONTEXT_CONFUSION = "context_confusion"              # 上下文混淆
    PROBABILITY_SAMPLING = "probability_sampling"        # 機率採樣誤差
    INSTRUCTION_MISUNDERSTANDING = "instruction_misunderstanding"  # 指令誤解


@dataclass
class HallucinationInstance:
    """
    幻覺實例

    記錄單個幻覺的詳細資訊
    """
    hallucination_id: str
    content: str                           # 幻覺內容
    hallucination_type: HallucinationType
    possible_causes: List[HallucinationCause]
    correct_information: Optional[str]     # 正確資訊（如果已知）
    confidence: float                      # 判定信心度
    context: str                           # 發生的上下文
    metadata: Dict[str, Any] = None

    def to_dict(self) -> dict:
        return {
            "id": self.hallucination_id,
            "content": self.content,
            "type": self.hallucination_type.value,
            "causes": [c.value for c in self.possible_causes],
            "correct_info": self.correct_information,
            "confidence": self.confidence,
            "context": self.context[:200] + "..." if len(self.context) > 200 else self.context
        }


class HallucinationAnalyzer:
    """
    幻覺分析器

    ‹1› 檢測潛在的幻覺
    ‹2› 分類幻覺類型
    ‹3› 推斷可能成因
    """

    # 常見的幻覺指標
    HALLUCINATION_INDICATORS = {
        "temporal": [
            "最新", "目前", "現在", "今年", "recently", "currently",
            "as of", "latest", "now"
        ],
        "fabrication": [
            "根據研究", "專家表示", "據報導", "according to",
            "study shows", "research indicates"
        ],
        "factual": [
            "是", "為", "有", "達到", "超過",
            "is", "was", "has", "reached", "exceeded"
        ]
    }

    def __init__(self, llm_client=None, knowledge_cutoff: str = "2024-01"):
        """
        初始化分析器

        Args:
            llm_client: LLM 客戶端（用於輔助分析）
            knowledge_cutoff: 模型知識截止日期
        """
        self.llm_client = llm_client
        self.knowledge_cutoff = knowledge_cutoff

    def detect_potential_hallucinations(
        self,
        text: str,
        context: str = ""
    ) -> List[Dict[str, Any]]:
        """
        檢測潛在的幻覺

        ‹2› 基於規則的初步篩選
        """
        potential_hallucinations = []

        # 檢查時序性問題
        for indicator in self.HALLUCINATION_INDICATORS["temporal"]:
            if indicator in text.lower():
                potential_hallucinations.append({
                    "type": HallucinationType.TEMPORAL,
                    "indicator": indicator,
                    "reason": "包含時效性敏感詞彙，可能涉及過時資訊"
                })
                break

        # 檢查虛構引用
        for indicator in self.HALLUCINATION_INDICATORS["fabrication"]:
            if indicator in text.lower():
                # 進一步檢查是否有具體來源
                if not self._has_verifiable_source(text):
                    potential_hallucinations.append({
                        "type": HallucinationType.SOURCE,
                        "indicator": indicator,
                        "reason": "引用來源但無法驗證"
                    })
                break

        # 檢查數字和統計
        numbers = self._extract_numbers(text)
        if numbers:
            potential_hallucinations.append({
                "type": HallucinationType.FACTUAL,
                "indicator": str(numbers),
                "reason": "包含具體數字，需要驗證"
            })

        return potential_hallucinations

    def _has_verifiable_source(self, text: str) -> bool:
        """檢查是否有可驗證的來源"""
        import re

        # 檢查 URL
        url_pattern = r'https?://[^\s]+'
        if re.search(url_pattern, text):
            return True

        # 檢查標準引用格式
        citation_patterns = [
            r'\[\d+\]',                    # [1], [2] 等
            r'\([A-Z][a-z]+,?\s*\d{4}\)',  # (Author, 2023)
            r'doi:\s*\d+\.\d+',            # DOI
        ]
        for pattern in citation_patterns:
            if re.search(pattern, text):
                return True

        return False

    def _extract_numbers(self, text: str) -> List[str]:
        """提取文本中的數字"""
        import re
        # 匹配各種數字格式
        patterns = [
            r'\d+\.?\d*%',           # 百分比
            r'\$\d+(?:,\d{3})*(?:\.\d+)?(?:\s*(?:billion|million))?',  # 金額
            r'\d{4}年',              # 年份
            r'\d+(?:,\d{3})*',       # 一般數字
        ]
        numbers = []
        for pattern in patterns:
            numbers.extend(re.findall(pattern, text))
        return numbers[:5]  # 限制數量

    async def analyze_with_llm(
        self,
        text: str,
        context: str = ""
    ) -> List[HallucinationInstance]:
        """
        使用 LLM 進行深度分析

        ‹3› 更準確的幻覺檢測
        """
        if not self.llm_client:
            return []

        prompt = f"""分析以下文本中可能存在的幻覺或不準確資訊。

文本內容：
{text}

背景資訊：
{context}

模型知識截止日期：{self.knowledge_cutoff}

請識別：
1. 可能過時的資訊
2. 可能虛構的事實
3. 無法驗證的引用
4. 邏輯推理錯誤

以 JSON 格式回覆，每個問題包含：
- content: 問題內容
- type: 類型（factual/fabrication/temporal/reasoning/source）
- confidence: 信心度（0-1）
- reason: 判斷原因
"""

        response = await self.llm_client.generate(prompt)
        return self._parse_llm_analysis(response, text)

    def _parse_llm_analysis(
        self,
        response: str,
        original_text: str
    ) -> List[HallucinationInstance]:
        """解析 LLM 分析結果"""
        import json
        import uuid

        instances = []

        try:
            # 提取 JSON
            json_start = response.find("[")
            json_end = response.rfind("]") + 1
            if json_start >= 0 and json_end > json_start:
                data = json.loads(response[json_start:json_end])

                for item in data:
                    instances.append(HallucinationInstance(
                        hallucination_id=str(uuid.uuid4())[:8],
                        content=item.get("content", ""),
                        hallucination_type=HallucinationType(
                            item.get("type", "factual")
                        ),
                        possible_causes=[HallucinationCause.TRAINING_DATA_OUTDATED],
                        correct_information=None,
                        confidence=item.get("confidence", 0.5),
                        context=original_text
                    ))
        except Exception:
            pass

        return instances
```

---

## 13.2 事實查核系統設計

事實查核（Fact Checking）是對抗幻覺的核心機制。一個完善的事實查核系統需要多層次的驗證策略。

### 13.2.1 多層次查核架構

```
┌─────────────────────────────────────────────────────────────────┐
│                  多層次事實查核架構                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  輸入文本 ────────────────────────────────────────────────────▶│
│       │                                                         │
│       ▼                                                         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Layer 1: 語法層查核                                       │  │
│  │  - 識別可驗證聲明                                          │  │
│  │  - 提取實體和關係                                          │  │
│  │  - 標記需要驗證的內容                                      │  │
│  └────────────────────────┬─────────────────────────────────┘  │
│                           │                                     │
│                           ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Layer 2: 語義層查核                                       │  │
│  │  - 交叉驗證多個來源                                        │  │
│  │  - 檢查邏輯一致性                                          │  │
│  │  - 評估來源可信度                                          │  │
│  └────────────────────────┬─────────────────────────────────┘  │
│                           │                                     │
│                           ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Layer 3: 知識層查核                                       │  │
│  │  - 知識圖譜比對                                            │  │
│  │  - 時間線驗證                                              │  │
│  │  - 專業領域驗證                                            │  │
│  └────────────────────────┬─────────────────────────────────┘  │
│                           │                                     │
│                           ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Layer 4: 人工審核（可選）                                 │  │
│  │  - 高風險聲明人工確認                                      │  │
│  │  - 爭議性內容標記                                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           │                                     │
│                           ▼                                     │
│  輸出：查核報告 + 信心分數 + 修正建議                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 13.2.2 事實查核引擎實作

```python
#!/usr/bin/env python3
"""
事實查核引擎

多層次事實驗證系統
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import asyncio
from datetime import datetime
import re


class VerificationStatus(Enum):
    """驗證狀態"""
    VERIFIED = "verified"           # 已驗證正確
    REFUTED = "refuted"             # 已驗證錯誤
    UNCERTAIN = "uncertain"         # 無法確定
    OUTDATED = "outdated"           # 資訊過時
    UNVERIFIABLE = "unverifiable"   # 無法驗證


@dataclass
class Claim:
    """
    可驗證聲明

    從文本中提取的需要驗證的聲明
    """
    claim_id: str
    text: str
    claim_type: str  # factual, numerical, temporal, attribution
    entities: List[str] = field(default_factory=list)
    source_context: str = ""


@dataclass
class Evidence:
    """
    證據

    用於支持或反駁聲明的證據
    """
    source: str                    # 來源名稱
    url: Optional[str]             # 來源 URL
    content: str                   # 相關內容
    credibility_score: float       # 可信度分數 0-1
    publication_date: Optional[str] # 發布日期
    supports_claim: Optional[bool]  # 支持/反駁/中立


@dataclass
class VerificationResult:
    """
    驗證結果
    """
    claim: Claim
    status: VerificationStatus
    confidence: float              # 信心度 0-1
    evidences: List[Evidence] = field(default_factory=list)
    explanation: str = ""
    correction: Optional[str] = None  # 如果錯誤，提供正確資訊


class ClaimExtractor:
    """
    聲明提取器

    ‹1› 從文本中提取可驗證的聲明
    """

    # 聲明類型的模式
    CLAIM_PATTERNS = {
        "numerical": [
            r"(\d+(?:\.\d+)?%)",                    # 百分比
            r"(\$\d+(?:,\d{3})*(?:\.\d+)?[MB]?)",   # 金額
            r"(\d+(?:,\d{3})*\s*(?:人|個|家|次))",  # 數量
        ],
        "temporal": [
            r"((?:19|20)\d{2}年)",                  # 年份
            r"((?:上|本|去|今)年)",                 # 相對時間
            r"(\d+月\d+日)",                        # 日期
        ],
        "attribution": [
            r"((?:據|根據).*?(?:表示|指出|報導))",   # 引用
            r"(.*?說：「.*?」)",                    # 直接引用
        ]
    }

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    def extract_claims(self, text: str) -> List[Claim]:
        """
        提取聲明

        ‹2› 結合規則和 NLP 提取
        """
        claims = []
        claim_id = 0

        # 將文本分割成句子
        sentences = self._split_sentences(text)

        for sentence in sentences:
            # 檢查是否包含可驗證內容
            claim_type = self._identify_claim_type(sentence)
            if claim_type:
                claim_id += 1
                entities = self._extract_entities(sentence)
                claims.append(Claim(
                    claim_id=f"CLM-{claim_id:03d}",
                    text=sentence.strip(),
                    claim_type=claim_type,
                    entities=entities,
                    source_context=text[:500]
                ))

        return claims

    def _split_sentences(self, text: str) -> List[str]:
        """分割句子"""
        # 簡單的句子分割
        separators = r'[。！？\.!?]'
        sentences = re.split(separators, text)
        return [s.strip() for s in sentences if s.strip()]

    def _identify_claim_type(self, sentence: str) -> Optional[str]:
        """識別聲明類型"""
        for claim_type, patterns in self.CLAIM_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, sentence):
                    return claim_type

        # 包含特定動詞的陳述句
        fact_verbs = ["是", "為", "有", "達到", "超過", "增長", "下降"]
        for verb in fact_verbs:
            if verb in sentence and len(sentence) > 10:
                return "factual"

        return None

    def _extract_entities(self, sentence: str) -> List[str]:
        """提取實體"""
        entities = []

        # 簡單的實體識別（實際應用中可用 NER 模型）
        # 公司名稱
        company_pattern = r'([A-Z][a-z]*(?:\s[A-Z][a-z]*)*(?:\s(?:Inc|Corp|Ltd)\.?)?)'
        entities.extend(re.findall(company_pattern, sentence))

        # 人名（中文）
        name_pattern = r'([王李張劉陳楊黃趙周吳][^\s]{1,3})'
        entities.extend(re.findall(name_pattern, sentence))

        return list(set(entities))[:5]


class SourceVerifier:
    """
    來源驗證器

    ‹3› 交叉驗證多個來源
    """

    # 可信來源等級
    SOURCE_CREDIBILITY = {
        "academic": 0.95,      # 學術來源
        "government": 0.90,    # 政府官方
        "major_news": 0.85,    # 主流媒體
        "tech_news": 0.80,     # 科技媒體
        "general": 0.60,       # 一般來源
        "social": 0.30,        # 社交媒體
        "unknown": 0.10,       # 未知來源
    }

    TRUSTED_DOMAINS = {
        "academic": [
            "arxiv.org", "nature.com", "science.org", "ieee.org",
            "acm.org", "springer.com", "sciencedirect.com"
        ],
        "government": [
            "gov", "edu", "gov.tw", "gov.cn", "whitehouse.gov"
        ],
        "major_news": [
            "reuters.com", "apnews.com", "bbc.com", "nytimes.com",
            "wsj.com", "economist.com"
        ],
        "tech_news": [
            "techcrunch.com", "wired.com", "arstechnica.com",
            "theverge.com", "venturebeat.com"
        ]
    }

    def __init__(self, search_engine=None):
        self.search_engine = search_engine

    async def verify_claim(
        self,
        claim: Claim,
        max_sources: int = 5
    ) -> Tuple[VerificationStatus, List[Evidence], float]:
        """
        驗證聲明

        Returns:
            (狀態, 證據列表, 信心度)
        """
        # 搜尋相關資訊
        evidences = await self._search_evidences(claim, max_sources)

        if not evidences:
            return VerificationStatus.UNVERIFIABLE, [], 0.0

        # 分析證據
        support_count = sum(1 for e in evidences if e.supports_claim)
        refute_count = sum(1 for e in evidences if e.supports_claim is False)
        neutral_count = len(evidences) - support_count - refute_count

        # 計算加權信心度
        weighted_support = sum(
            e.credibility_score for e in evidences
            if e.supports_claim
        )
        weighted_refute = sum(
            e.credibility_score for e in evidences
            if e.supports_claim is False
        )

        total_weight = weighted_support + weighted_refute
        if total_weight == 0:
            return VerificationStatus.UNCERTAIN, evidences, 0.3

        # 判定狀態
        if weighted_support > weighted_refute * 2:
            status = VerificationStatus.VERIFIED
            confidence = min(weighted_support / (total_weight + 0.5), 0.95)
        elif weighted_refute > weighted_support * 2:
            status = VerificationStatus.REFUTED
            confidence = min(weighted_refute / (total_weight + 0.5), 0.95)
        else:
            status = VerificationStatus.UNCERTAIN
            confidence = 0.5 - abs(weighted_support - weighted_refute) / total_weight * 0.3

        return status, evidences, confidence

    async def _search_evidences(
        self,
        claim: Claim,
        max_sources: int
    ) -> List[Evidence]:
        """搜尋證據"""
        if not self.search_engine:
            return []

        # 構建搜尋查詢
        query = self._build_search_query(claim)

        # 搜尋
        results = await self.search_engine.search(query, max_sources)

        evidences = []
        for result in results:
            credibility = self._assess_source_credibility(result.get("url", ""))
            supports = await self._check_support(claim.text, result.get("content", ""))

            evidences.append(Evidence(
                source=result.get("title", "Unknown"),
                url=result.get("url"),
                content=result.get("snippet", "")[:500],
                credibility_score=credibility,
                publication_date=result.get("date"),
                supports_claim=supports
            ))

        return evidences

    def _build_search_query(self, claim: Claim) -> str:
        """構建搜尋查詢"""
        # 提取關鍵詞
        keywords = claim.entities[:3] if claim.entities else []

        # 添加聲明中的關鍵內容
        claim_words = [
            w for w in claim.text.split()
            if len(w) > 2 and not w.isdigit()
        ][:5]

        query_parts = keywords + claim_words
        return " ".join(query_parts)

    def _assess_source_credibility(self, url: str) -> float:
        """評估來源可信度"""
        if not url:
            return self.SOURCE_CREDIBILITY["unknown"]

        url_lower = url.lower()

        for category, domains in self.TRUSTED_DOMAINS.items():
            for domain in domains:
                if domain in url_lower:
                    return self.SOURCE_CREDIBILITY[category]

        return self.SOURCE_CREDIBILITY["general"]

    async def _check_support(
        self,
        claim_text: str,
        evidence_content: str
    ) -> Optional[bool]:
        """檢查證據是否支持聲明"""
        if not evidence_content:
            return None

        # 簡單的關鍵詞匹配
        claim_words = set(claim_text.lower().split())
        evidence_words = set(evidence_content.lower().split())

        overlap = len(claim_words & evidence_words)
        if overlap < 3:
            return None  # 相關性不足

        # 檢查否定詞
        negation_words = ["不", "沒", "無", "錯", "假", "否", "not", "no", "false", "wrong"]
        has_negation = any(w in evidence_content.lower() for w in negation_words)

        # 簡化判斷：有較多重疊且無否定 = 支持
        if overlap > 5 and not has_negation:
            return True
        elif has_negation and overlap > 3:
            return False
        else:
            return None


class FactCheckEngine:
    """
    事實查核引擎

    整合所有查核功能
    """

    def __init__(
        self,
        llm_client=None,
        search_engine=None
    ):
        self.extractor = ClaimExtractor(llm_client)
        self.verifier = SourceVerifier(search_engine)
        self.llm_client = llm_client

    async def check(self, text: str) -> Dict[str, Any]:
        """
        執行完整的事實查核

        Returns:
            查核報告
        """
        start_time = datetime.now()

        # Step 1: 提取聲明
        claims = self.extractor.extract_claims(text)

        # Step 2: 驗證每個聲明
        results = []
        for claim in claims:
            status, evidences, confidence = await self.verifier.verify_claim(claim)

            result = VerificationResult(
                claim=claim,
                status=status,
                confidence=confidence,
                evidences=evidences,
                explanation=self._generate_explanation(status, evidences)
            )

            # 如果被反駁，嘗試找到正確資訊
            if status == VerificationStatus.REFUTED:
                result.correction = await self._find_correction(claim, evidences)

            results.append(result)

        # Step 3: 生成報告
        end_time = datetime.now()

        return {
            "summary": self._generate_summary(results),
            "claims_count": len(claims),
            "verified_count": sum(
                1 for r in results
                if r.status == VerificationStatus.VERIFIED
            ),
            "refuted_count": sum(
                1 for r in results
                if r.status == VerificationStatus.REFUTED
            ),
            "uncertain_count": sum(
                1 for r in results
                if r.status in [
                    VerificationStatus.UNCERTAIN,
                    VerificationStatus.UNVERIFIABLE
                ]
            ),
            "overall_credibility": self._calculate_credibility(results),
            "duration_seconds": (end_time - start_time).total_seconds(),
            "detailed_results": [
                {
                    "claim": r.claim.text,
                    "status": r.status.value,
                    "confidence": r.confidence,
                    "explanation": r.explanation,
                    "correction": r.correction
                }
                for r in results
            ]
        }

    def _generate_explanation(
        self,
        status: VerificationStatus,
        evidences: List[Evidence]
    ) -> str:
        """生成解釋"""
        if status == VerificationStatus.VERIFIED:
            sources = [e.source for e in evidences if e.supports_claim][:3]
            return f"此聲明得到以下來源的驗證：{', '.join(sources)}"
        elif status == VerificationStatus.REFUTED:
            sources = [e.source for e in evidences if not e.supports_claim][:3]
            return f"此聲明與以下來源的資訊不符：{', '.join(sources)}"
        elif status == VerificationStatus.OUTDATED:
            return "此資訊可能已過時，建議查閱最新資料"
        elif status == VerificationStatus.UNCERTAIN:
            return "無法確定此聲明的準確性，建議進一步驗證"
        else:
            return "無法找到足夠的證據來驗證此聲明"

    async def _find_correction(
        self,
        claim: Claim,
        evidences: List[Evidence]
    ) -> Optional[str]:
        """尋找正確資訊"""
        # 從反駁證據中提取可能的正確資訊
        refuting_evidences = [
            e for e in evidences
            if e.supports_claim is False
        ]

        if refuting_evidences and self.llm_client:
            evidence_texts = "\n".join([
                f"- {e.content}" for e in refuting_evidences[:3]
            ])

            prompt = f"""根據以下證據，提供正確的資訊：

原始聲明：{claim.text}

反駁證據：
{evidence_texts}

請簡潔地說明正確的資訊是什麼。"""

            correction = await self.llm_client.generate(prompt)
            return correction.strip()

        return None

    def _generate_summary(self, results: List[VerificationResult]) -> str:
        """生成摘要"""
        if not results:
            return "未發現需要驗證的聲明"

        verified = sum(1 for r in results if r.status == VerificationStatus.VERIFIED)
        refuted = sum(1 for r in results if r.status == VerificationStatus.REFUTED)
        total = len(results)

        if refuted == 0:
            return f"共檢查 {total} 個聲明，所有可驗證的聲明均準確"
        elif refuted < total / 3:
            return f"共檢查 {total} 個聲明，發現 {refuted} 個不準確的內容"
        else:
            return f"警告：共檢查 {total} 個聲明，{refuted} 個不準確，建議謹慎使用"

    def _calculate_credibility(self, results: List[VerificationResult]) -> float:
        """計算整體可信度"""
        if not results:
            return 1.0

        verified_weight = sum(
            r.confidence for r in results
            if r.status == VerificationStatus.VERIFIED
        )
        refuted_weight = sum(
            r.confidence for r in results
            if r.status == VerificationStatus.REFUTED
        )
        uncertain_weight = sum(
            0.5 for r in results
            if r.status in [
                VerificationStatus.UNCERTAIN,
                VerificationStatus.UNVERIFIABLE
            ]
        )

        total = verified_weight + refuted_weight + uncertain_weight
        if total == 0:
            return 0.5

        return verified_weight / total
```

---

## 13.3 時序敏感訓練

時序性幻覺是深度研究代理人面臨的特殊挑戰。模型的知識有截止日期，但研究問題往往需要最新資訊。

### 13.3.1 時序感知機制

```python
#!/usr/bin/env python3
"""
時序敏感訓練與推理

處理時間相關的資訊和幻覺
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from enum import Enum
import re


class TemporalCategory(Enum):
    """時間類別"""
    STATIC = "static"              # 靜態事實（不隨時間變化）
    DYNAMIC = "dynamic"            # 動態資訊（經常變化）
    PERIODIC = "periodic"          # 周期性資訊
    EVENT = "event"                # 一次性事件
    PREDICTION = "prediction"      # 預測性資訊


@dataclass
class TemporalContext:
    """
    時序上下文

    記錄資訊的時間相關屬性
    """
    reference_time: datetime       # 參考時間
    validity_period: timedelta     # 有效期
    category: TemporalCategory
    confidence_decay: float        # 信心衰減率（每天）


class TemporalAwareProcessor:
    """
    時序感知處理器

    ‹1› 識別時間敏感資訊
    ‹2› 評估資訊時效性
    ‹3› 標記需要更新的內容
    """

    # 時間敏感詞彙
    TEMPORAL_INDICATORS = {
        "current": ["目前", "現在", "當前", "現今", "current", "currently", "now"],
        "recent": ["最近", "近期", "最新", "剛剛", "recent", "recently", "latest"],
        "future": ["將", "預計", "即將", "未來", "will", "expected", "upcoming"],
        "past": ["曾", "過去", "以前", "歷史", "was", "were", "previously"],
    }

    # 資訊類型的預設有效期（天）
    VALIDITY_PERIODS = {
        "stock_price": 0,           # 股價：即時
        "exchange_rate": 0,         # 匯率：即時
        "news": 1,                  # 新聞：1 天
        "market_data": 7,           # 市場數據：1 週
        "company_info": 30,         # 公司資訊：1 個月
        "research_data": 90,        # 研究數據：3 個月
        "historical_fact": 36500,   # 歷史事實：100 年
    }

    def __init__(self, model_cutoff: str = "2024-01-01"):
        """
        初始化處理器

        Args:
            model_cutoff: 模型知識截止日期
        """
        self.model_cutoff = datetime.fromisoformat(model_cutoff)
        self.current_time = datetime.now()

    def analyze_temporal_sensitivity(
        self,
        text: str
    ) -> Dict[str, Any]:
        """
        分析文本的時序敏感性

        ‹2› 識別需要時序驗證的內容
        """
        analysis = {
            "has_temporal_references": False,
            "temporal_markers": [],
            "requires_update": False,
            "sensitive_phrases": [],
            "recommended_actions": []
        }

        # 檢查時間指示詞
        for category, indicators in self.TEMPORAL_INDICATORS.items():
            for indicator in indicators:
                if indicator in text.lower():
                    analysis["has_temporal_references"] = True
                    analysis["temporal_markers"].append({
                        "marker": indicator,
                        "category": category
                    })

        # 檢查日期引用
        date_patterns = [
            r"((?:19|20)\d{2})年",
            r"(\d{1,2})月(\d{1,2})日",
            r"(Q[1-4])\s*((?:19|20)\d{2})",
        ]

        for pattern in date_patterns:
            matches = re.findall(pattern, text)
            if matches:
                analysis["has_temporal_references"] = True
                for match in matches:
                    if isinstance(match, tuple):
                        match = "".join(match)
                    analysis["sensitive_phrases"].append(match)

        # 判斷是否需要更新
        if analysis["has_temporal_references"]:
            # 檢查是否引用了模型知識截止後的日期
            for phrase in analysis["sensitive_phrases"]:
                try:
                    year_match = re.search(r"((?:19|20)\d{2})", phrase)
                    if year_match:
                        year = int(year_match.group(1))
                        if year >= self.model_cutoff.year:
                            analysis["requires_update"] = True
                            analysis["recommended_actions"].append(
                                f"驗證 {year} 年的資訊是否最新"
                            )
                except ValueError:
                    pass

        return analysis

    def estimate_information_age(
        self,
        text: str,
        source_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        估計資訊年齡

        ‹3› 評估資訊的新鮮度
        """
        if source_date:
            age_days = (self.current_time - source_date).days
        else:
            # 從文本中提取日期
            source_date = self._extract_date(text)
            if source_date:
                age_days = (self.current_time - source_date).days
            else:
                # 假設來自模型知識
                age_days = (self.current_time - self.model_cutoff).days

        # 根據資訊類型評估
        info_type = self._classify_information_type(text)
        validity_days = self.VALIDITY_PERIODS.get(info_type, 30)

        is_stale = age_days > validity_days
        freshness_score = max(0, 1 - age_days / validity_days) if validity_days else 0

        return {
            "age_days": age_days,
            "information_type": info_type,
            "validity_period_days": validity_days,
            "is_stale": is_stale,
            "freshness_score": freshness_score,
            "recommendation": self._get_freshness_recommendation(
                is_stale, age_days, info_type
            )
        }

    def _extract_date(self, text: str) -> Optional[datetime]:
        """從文本提取日期"""
        # 嘗試多種日期格式
        patterns = [
            (r"(20\d{2})年(\d{1,2})月(\d{1,2})日", "%Y-%m-%d"),
            (r"(20\d{2})-(\d{2})-(\d{2})", "%Y-%m-%d"),
            (r"(\d{1,2})/(\d{1,2})/(20\d{2})", "%m/%d/%Y"),
        ]

        for pattern, fmt in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    groups = match.groups()
                    if fmt == "%Y-%m-%d":
                        return datetime(int(groups[0]), int(groups[1]), int(groups[2]))
                    elif fmt == "%m/%d/%Y":
                        return datetime(int(groups[2]), int(groups[0]), int(groups[1]))
                except ValueError:
                    continue

        return None

    def _classify_information_type(self, text: str) -> str:
        """分類資訊類型"""
        text_lower = text.lower()

        if any(w in text_lower for w in ["股價", "stock", "price", "trading"]):
            return "stock_price"
        elif any(w in text_lower for w in ["匯率", "exchange", "currency"]):
            return "exchange_rate"
        elif any(w in text_lower for w in ["新聞", "報導", "news", "reported"]):
            return "news"
        elif any(w in text_lower for w in ["市場", "market", "industry"]):
            return "market_data"
        elif any(w in text_lower for w in ["公司", "企業", "company", "corporation"]):
            return "company_info"
        elif any(w in text_lower for w in ["研究", "論文", "study", "research"]):
            return "research_data"
        elif any(w in text_lower for w in ["歷史", "歷史上", "history", "historical"]):
            return "historical_fact"
        else:
            return "general"

    def _get_freshness_recommendation(
        self,
        is_stale: bool,
        age_days: int,
        info_type: str
    ) -> str:
        """獲取新鮮度建議"""
        if not is_stale:
            return "資訊在有效期內，可直接使用"

        if info_type in ["stock_price", "exchange_rate"]:
            return "此類資訊變化極快，請獲取即時數據"
        elif info_type == "news":
            return "新聞資訊已過期，請查閱最新報導"
        elif age_days > 365:
            return f"資訊已超過 {age_days // 365} 年，建議重新驗證"
        else:
            return f"資訊已有 {age_days} 天，建議確認是否有更新"

    def generate_temporal_disclaimer(
        self,
        text: str,
        source_date: Optional[datetime] = None
    ) -> str:
        """
        生成時序免責聲明

        ‹4› 為輸出添加時間相關警告
        """
        analysis = self.analyze_temporal_sensitivity(text)
        age_info = self.estimate_information_age(text, source_date)

        disclaimers = []

        if age_info["is_stale"]:
            disclaimers.append(
                f"⚠️ 此資訊已有 {age_info['age_days']} 天，"
                f"可能已過時。{age_info['recommendation']}"
            )

        if analysis["requires_update"]:
            for action in analysis["recommended_actions"][:3]:
                disclaimers.append(f"📌 {action}")

        if not disclaimers:
            return ""

        return "\n\n---\n**時效性提醒**：\n" + "\n".join(disclaimers)
```

---

## 13.4 因果律約束

因果律約束是防止推理性幻覺的重要機制。它確保模型的推理遵循邏輯因果關係。

### 13.4.1 因果推理驗證器

```python
#!/usr/bin/env python3
"""
因果律約束系統

驗證推理過程的邏輯正確性
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum


class CausalRelationType(Enum):
    """因果關係類型"""
    CAUSES = "causes"              # A 導致 B
    ENABLES = "enables"            # A 使 B 成為可能
    PREVENTS = "prevents"          # A 阻止 B
    CORRELATES = "correlates"      # A 與 B 相關（非因果）
    CONTRADICTS = "contradicts"    # A 與 B 矛盾


@dataclass
class CausalClaim:
    """
    因果聲明

    表示一個因果關係主張
    """
    cause: str                     # 原因
    effect: str                    # 結果
    relation_type: CausalRelationType
    confidence: float              # 信心度
    evidence: Optional[str] = None # 支持證據


@dataclass
class CausalValidation:
    """
    因果驗證結果
    """
    claim: CausalClaim
    is_valid: bool
    issues: List[str]
    suggestions: List[str]


class CausalReasoningValidator:
    """
    因果推理驗證器

    ‹1› 識別文本中的因果主張
    ‹2› 驗證因果關係的合理性
    ‹3› 檢測常見的邏輯謬誤
    """

    # 因果指示詞
    CAUSAL_INDICATORS = {
        "causes": [
            "導致", "造成", "引起", "使", "讓",
            "因為", "由於", "所以", "因此",
            "causes", "leads to", "results in", "because"
        ],
        "enables": [
            "促進", "推動", "有助於", "幫助",
            "enables", "allows", "facilitates"
        ],
        "prevents": [
            "阻止", "防止", "避免", "抑制",
            "prevents", "blocks", "inhibits"
        ],
    }

    # 常見邏輯謬誤模式
    FALLACY_PATTERNS = {
        "post_hoc": {
            "description": "後此謬誤：僅因時序先後推斷因果",
            "indicators": ["之後", "接著", "然後", "after", "then", "subsequently"]
        },
        "correlation_causation": {
            "description": "相關性謬誤：將相關性等同於因果性",
            "indicators": ["相關", "伴隨", "同時", "correlates", "associated"]
        },
        "single_cause": {
            "description": "單一原因謬誤：複雜現象歸因於單一原因",
            "indicators": ["唯一", "只是因為", "純粹是", "solely", "only because"]
        },
        "reverse_causation": {
            "description": "因果倒置：混淆原因和結果的方向",
            "indicators": []  # 需要語義分析
        }
    }

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    def extract_causal_claims(self, text: str) -> List[CausalClaim]:
        """
        提取因果主張

        ‹2› 從文本中識別因果關係
        """
        claims = []
        sentences = self._split_into_sentences(text)

        for sentence in sentences:
            relation_type = self._identify_causal_relation(sentence)
            if relation_type:
                cause, effect = self._extract_cause_effect(
                    sentence, relation_type
                )
                if cause and effect:
                    claims.append(CausalClaim(
                        cause=cause,
                        effect=effect,
                        relation_type=relation_type,
                        confidence=0.7,
                        evidence=sentence
                    ))

        return claims

    def _split_into_sentences(self, text: str) -> List[str]:
        """分割句子"""
        import re
        return [s.strip() for s in re.split(r'[。！？\.!?]', text) if s.strip()]

    def _identify_causal_relation(
        self,
        sentence: str
    ) -> Optional[CausalRelationType]:
        """識別因果關係類型"""
        sentence_lower = sentence.lower()

        for relation_type, indicators in self.CAUSAL_INDICATORS.items():
            for indicator in indicators:
                if indicator in sentence_lower:
                    return CausalRelationType(relation_type)

        return None

    def _extract_cause_effect(
        self,
        sentence: str,
        relation_type: CausalRelationType
    ) -> Tuple[Optional[str], Optional[str]]:
        """提取原因和結果"""
        # 簡化版：根據指示詞分割
        for indicator in self.CAUSAL_INDICATORS.get(relation_type.value, []):
            if indicator in sentence:
                parts = sentence.split(indicator, 1)
                if len(parts) == 2:
                    return parts[0].strip(), parts[1].strip()

        return None, None

    def validate_causal_claim(
        self,
        claim: CausalClaim
    ) -> CausalValidation:
        """
        驗證因果主張

        ‹3› 檢查邏輯合理性
        """
        issues = []
        suggestions = []

        # 檢查常見謬誤
        for fallacy_name, fallacy_info in self.FALLACY_PATTERNS.items():
            if self._check_fallacy(claim, fallacy_info):
                issues.append(f"可能存在{fallacy_info['description']}")
                suggestions.append(self._get_fallacy_suggestion(fallacy_name))

        # 檢查因果方向合理性
        if self._check_reverse_causation_risk(claim):
            issues.append("因果方向可能需要驗證")
            suggestions.append("建議檢查是否存在反向因果關係")

        # 檢查過度簡化
        if self._check_oversimplification(claim):
            issues.append("可能過度簡化了因果關係")
            suggestions.append("建議考慮其他可能的影響因素")

        is_valid = len(issues) == 0

        return CausalValidation(
            claim=claim,
            is_valid=is_valid,
            issues=issues,
            suggestions=suggestions
        )

    def _check_fallacy(
        self,
        claim: CausalClaim,
        fallacy_info: Dict[str, Any]
    ) -> bool:
        """檢查是否存在特定謬誤"""
        if not claim.evidence:
            return False

        for indicator in fallacy_info.get("indicators", []):
            if indicator in claim.evidence.lower():
                return True

        return False

    def _check_reverse_causation_risk(self, claim: CausalClaim) -> bool:
        """檢查反向因果風險"""
        # 簡化實現：檢查常見的可逆因果對
        reversible_pairs = [
            ("收入", "教育"),
            ("健康", "運動"),
            ("成功", "信心"),
            ("income", "education"),
            ("health", "exercise"),
        ]

        for pair in reversible_pairs:
            if (pair[0] in claim.cause.lower() and pair[1] in claim.effect.lower()) or \
               (pair[1] in claim.cause.lower() and pair[0] in claim.effect.lower()):
                return True

        return False

    def _check_oversimplification(self, claim: CausalClaim) -> bool:
        """檢查過度簡化"""
        # 複雜現象的簡單標誌
        complex_phenomena = [
            "經濟增長", "氣候變化", "社會問題", "健康",
            "economic growth", "climate change", "social issues", "health"
        ]

        for phenomenon in complex_phenomena:
            if phenomenon in claim.effect.lower():
                # 複雜現象不太可能有單一原因
                return True

        return False

    def _get_fallacy_suggestion(self, fallacy_name: str) -> str:
        """獲取謬誤建議"""
        suggestions = {
            "post_hoc": "時間先後不等於因果關係，建議尋找機制解釋",
            "correlation_causation": "相關性需要進一步驗證才能確定因果關係",
            "single_cause": "考慮是否存在其他共同影響因素",
            "reverse_causation": "確認因果方向，考慮是否存在反向關係"
        }
        return suggestions.get(fallacy_name, "請進一步驗證因果關係")

    async def validate_with_llm(
        self,
        claim: CausalClaim
    ) -> CausalValidation:
        """
        使用 LLM 進行深度驗證

        ‹4› 更準確的因果分析
        """
        if not self.llm_client:
            return self.validate_causal_claim(claim)

        prompt = f"""分析以下因果主張的邏輯合理性：

原因：{claim.cause}
關係：{claim.relation_type.value}
結果：{claim.effect}

請評估：
1. 這個因果關係是否合理？
2. 是否存在邏輯謬誤？
3. 是否需要額外條件或前提？
4. 是否可能存在反向因果？

請以 JSON 格式回覆，包含：
- is_valid: 是否有效（true/false）
- issues: 問題列表
- suggestions: 建議列表
- confidence: 評估信心度（0-1）
"""

        response = await self.llm_client.generate(prompt)
        return self._parse_llm_validation(response, claim)

    def _parse_llm_validation(
        self,
        response: str,
        claim: CausalClaim
    ) -> CausalValidation:
        """解析 LLM 驗證結果"""
        import json

        try:
            # 提取 JSON
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                data = json.loads(response[json_start:json_end])

                return CausalValidation(
                    claim=claim,
                    is_valid=data.get("is_valid", True),
                    issues=data.get("issues", []),
                    suggestions=data.get("suggestions", [])
                )
        except Exception:
            pass

        # 解析失敗，使用規則驗證
        return self.validate_causal_claim(claim)
```

---

## 13.5 整合：自動事實查核管道

將以上所有組件整合成一個完整的事實查核管道。

### 13.5.1 完整管道實作

```python
#!/usr/bin/env python3
"""
自動事實查核管道

整合所有查核功能
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio


@dataclass
class FactCheckReport:
    """
    事實查核報告
    """
    input_text: str
    check_time: datetime
    duration_seconds: float

    # 幻覺分析
    hallucination_analysis: Dict[str, Any] = field(default_factory=dict)

    # 事實驗證
    fact_verification: Dict[str, Any] = field(default_factory=dict)

    # 時序分析
    temporal_analysis: Dict[str, Any] = field(default_factory=dict)

    # 因果驗證
    causal_validation: Dict[str, Any] = field(default_factory=dict)

    # 總體評估
    overall_credibility: float = 0.0
    risk_level: str = "low"
    summary: str = ""
    recommendations: List[str] = field(default_factory=list)


class FactCheckPipeline:
    """
    自動事實查核管道

    整合所有查核功能
    """

    def __init__(
        self,
        llm_client=None,
        search_engine=None,
        model_cutoff: str = "2024-01-01"
    ):
        """
        初始化管道

        Args:
            llm_client: LLM 客戶端
            search_engine: 搜尋引擎
            model_cutoff: 模型知識截止日期
        """
        self.llm_client = llm_client
        self.search_engine = search_engine
        self.model_cutoff = model_cutoff

        # 初始化各組件
        from hle_evaluator import HallucinationAnalyzer  # 假設存在
        self.hallucination_analyzer = HallucinationAnalyzer(
            llm_client, model_cutoff
        )

        self.fact_checker = FactCheckEngine(llm_client, search_engine)
        self.temporal_processor = TemporalAwareProcessor(model_cutoff)
        self.causal_validator = CausalReasoningValidator(llm_client)

    async def check(self, text: str) -> FactCheckReport:
        """
        執行完整的事實查核

        Args:
            text: 待查核的文本

        Returns:
            完整的查核報告
        """
        start_time = datetime.now()

        # 並行執行各項檢查
        tasks = [
            self._analyze_hallucinations(text),
            self._verify_facts(text),
            self._analyze_temporal(text),
            self._validate_causal(text),
        ]

        results = await asyncio.gather(*tasks)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # 整合結果
        report = FactCheckReport(
            input_text=text[:1000] + "..." if len(text) > 1000 else text,
            check_time=start_time,
            duration_seconds=duration,
            hallucination_analysis=results[0],
            fact_verification=results[1],
            temporal_analysis=results[2],
            causal_validation=results[3]
        )

        # 計算總體評估
        self._compute_overall_assessment(report)

        return report

    async def _analyze_hallucinations(self, text: str) -> Dict[str, Any]:
        """幻覺分析"""
        potential = self.hallucination_analyzer.detect_potential_hallucinations(
            text
        )
        detailed = await self.hallucination_analyzer.analyze_with_llm(text)

        return {
            "potential_issues": len(potential),
            "detected_hallucinations": len(detailed),
            "details": [h.to_dict() for h in detailed]
        }

    async def _verify_facts(self, text: str) -> Dict[str, Any]:
        """事實驗證"""
        result = await self.fact_checker.check(text)
        return result

    async def _analyze_temporal(self, text: str) -> Dict[str, Any]:
        """時序分析"""
        sensitivity = self.temporal_processor.analyze_temporal_sensitivity(text)
        age_info = self.temporal_processor.estimate_information_age(text)
        disclaimer = self.temporal_processor.generate_temporal_disclaimer(text)

        return {
            "sensitivity": sensitivity,
            "age_info": age_info,
            "disclaimer": disclaimer
        }

    async def _validate_causal(self, text: str) -> Dict[str, Any]:
        """因果驗證"""
        claims = self.causal_validator.extract_causal_claims(text)
        validations = []

        for claim in claims:
            if self.llm_client:
                validation = await self.causal_validator.validate_with_llm(claim)
            else:
                validation = self.causal_validator.validate_causal_claim(claim)
            validations.append({
                "claim": f"{claim.cause} → {claim.effect}",
                "is_valid": validation.is_valid,
                "issues": validation.issues
            })

        return {
            "claims_found": len(claims),
            "valid_claims": sum(1 for v in validations if v["is_valid"]),
            "validations": validations
        }

    def _compute_overall_assessment(self, report: FactCheckReport):
        """計算總體評估"""
        scores = []

        # 幻覺分析評分
        hallucination_count = report.hallucination_analysis.get(
            "detected_hallucinations", 0
        )
        hallucination_score = max(0, 1 - hallucination_count * 0.2)
        scores.append(hallucination_score)

        # 事實驗證評分
        fact_credibility = report.fact_verification.get("overall_credibility", 0.5)
        scores.append(fact_credibility)

        # 時序評分
        freshness = report.temporal_analysis.get("age_info", {}).get(
            "freshness_score", 0.5
        )
        scores.append(freshness)

        # 因果評分
        causal_data = report.causal_validation
        if causal_data.get("claims_found", 0) > 0:
            causal_score = (
                causal_data.get("valid_claims", 0) /
                causal_data.get("claims_found", 1)
            )
        else:
            causal_score = 1.0
        scores.append(causal_score)

        # 計算加權平均
        weights = [0.3, 0.4, 0.15, 0.15]
        report.overall_credibility = sum(
            s * w for s, w in zip(scores, weights)
        )

        # 確定風險等級
        if report.overall_credibility >= 0.8:
            report.risk_level = "low"
        elif report.overall_credibility >= 0.6:
            report.risk_level = "medium"
        else:
            report.risk_level = "high"

        # 生成摘要
        report.summary = self._generate_summary(report)

        # 生成建議
        report.recommendations = self._generate_recommendations(report)

    def _generate_summary(self, report: FactCheckReport) -> str:
        """生成摘要"""
        credibility_pct = report.overall_credibility * 100
        risk_labels = {"low": "低", "medium": "中", "high": "高"}

        return (
            f"整體可信度評估：{credibility_pct:.1f}%，"
            f"風險等級：{risk_labels[report.risk_level]}。"
            f"檢查耗時：{report.duration_seconds:.2f} 秒。"
        )

    def _generate_recommendations(self, report: FactCheckReport) -> List[str]:
        """生成建議"""
        recommendations = []

        # 基於幻覺分析
        if report.hallucination_analysis.get("detected_hallucinations", 0) > 0:
            recommendations.append("建議對標記的潛在幻覺進行人工驗證")

        # 基於事實驗證
        refuted = report.fact_verification.get("refuted_count", 0)
        if refuted > 0:
            recommendations.append(f"發現 {refuted} 個不準確的聲明，請修正")

        # 基於時序分析
        if report.temporal_analysis.get("age_info", {}).get("is_stale", False):
            recommendations.append("部分資訊可能過時，建議更新")

        # 基於因果分析
        invalid_causal = (
            report.causal_validation.get("claims_found", 0) -
            report.causal_validation.get("valid_claims", 0)
        )
        if invalid_causal > 0:
            recommendations.append(f"{invalid_causal} 個因果推理需要重新審視")

        if not recommendations:
            recommendations.append("查核通過，內容可信度較高")

        return recommendations


# ===== 使用示例 =====

async def demo_fact_check():
    """示範事實查核"""
    text = """
    根據最新研究，蘋果公司在 2024 年的營收達到 4000 億美元，
    這主要是因為 iPhone 15 的成功。由於 AI 技術的發展，
    智慧型手機市場增長了 50%。專家預測，到 2025 年，
    全球 AI 晶片市場將達到 1000 億美元規模。
    """

    # 注意：實際使用需要配置 LLM 和搜尋引擎
    pipeline = FactCheckPipeline(
        llm_client=None,
        search_engine=None,
        model_cutoff="2024-01-01"
    )

    report = await pipeline.check(text)

    print("=" * 60)
    print("事實查核報告")
    print("=" * 60)
    print(f"\n摘要：{report.summary}")
    print(f"\n可信度：{report.overall_credibility:.2%}")
    print(f"風險等級：{report.risk_level}")
    print("\n建議：")
    for rec in report.recommendations:
        print(f"  - {rec}")


if __name__ == "__main__":
    asyncio.run(demo_fact_check())
```

---

## 13.6 章節總結

本章深入探討了 LLM 幻覺處理與事實查核：

### 核心概念

1. **幻覺類型**
   - 事實性幻覺：事實錯誤
   - 虛構性幻覺：完全虛構
   - 時序性幻覺：時間混淆
   - 推理性幻覺：邏輯錯誤
   - 來源性幻覺：引用捏造

2. **事實查核系統**
   - 多層次查核架構
   - 聲明提取與驗證
   - 來源可信度評估

3. **時序敏感處理**
   - 識別時效性敏感資訊
   - 評估資訊新鮮度
   - 生成時序免責聲明

4. **因果律約束**
   - 識別因果主張
   - 檢測邏輯謬誤
   - 驗證因果合理性

### 檢查清單

- [ ] 理解五種主要幻覺類型
- [ ] 能夠建構多層次事實查核系統
- [ ] 掌握時序敏感性處理方法
- [ ] 了解常見邏輯謬誤及檢測方法

---

## 13.7 下一章預告

在下一章「效能優化與成本控制」中，我們將探討：

- Token 效率優化策略
- 智能快取機制
- 批次處理與並行化
- 成本監控與預算控制
- 模型選擇與降級策略

這些技術將幫助你在保持研究品質的同時，大幅降低運營成本。
