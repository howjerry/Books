#!/usr/bin/env python3
"""
深度研究代理人實戰 - 第 13 章：幻覺處理與事實查核
自動事實查核管道

這個模組實現了完整的事實查核管道：
1. 幻覺檢測與分析
2. 事實驗證
3. 時序敏感性處理
4. 因果律驗證

使用方式：
    from fact_check_pipeline import FactCheckPipeline

    pipeline = FactCheckPipeline()
    report = await pipeline.check(text)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from datetime import datetime, timedelta
import asyncio
import re
import json
import uuid


# =============================================================================
# 幻覺類型與成因
# =============================================================================

class HallucinationType(Enum):
    """幻覺類型"""
    FACTUAL = "factual"           # 事實性幻覺
    FABRICATION = "fabrication"   # 虛構性幻覺
    TEMPORAL = "temporal"         # 時序性幻覺
    REASONING = "reasoning"       # 推理性幻覺
    SOURCE = "source"             # 來源性幻覺


class VerificationStatus(Enum):
    """驗證狀態"""
    VERIFIED = "verified"           # 已驗證正確
    REFUTED = "refuted"             # 已驗證錯誤
    UNCERTAIN = "uncertain"         # 無法確定
    OUTDATED = "outdated"           # 資訊過時
    UNVERIFIABLE = "unverifiable"   # 無法驗證


class CausalRelationType(Enum):
    """因果關係類型"""
    CAUSES = "causes"              # A 導致 B
    ENABLES = "enables"            # A 使 B 成為可能
    PREVENTS = "prevents"          # A 阻止 B
    CORRELATES = "correlates"      # A 與 B 相關
    CONTRADICTS = "contradicts"    # A 與 B 矛盾


# =============================================================================
# 資料結構
# =============================================================================

@dataclass
class HallucinationInstance:
    """幻覺實例"""
    hallucination_id: str
    content: str
    hallucination_type: HallucinationType
    confidence: float
    context: str
    correct_information: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.hallucination_id,
            "content": self.content,
            "type": self.hallucination_type.value,
            "confidence": self.confidence,
            "correct_info": self.correct_information
        }


@dataclass
class Claim:
    """可驗證聲明"""
    claim_id: str
    text: str
    claim_type: str
    entities: List[str] = field(default_factory=list)


@dataclass
class Evidence:
    """證據"""
    source: str
    url: Optional[str]
    content: str
    credibility_score: float
    supports_claim: Optional[bool]


@dataclass
class VerificationResult:
    """驗證結果"""
    claim: Claim
    status: VerificationStatus
    confidence: float
    evidences: List[Evidence] = field(default_factory=list)
    explanation: str = ""
    correction: Optional[str] = None


@dataclass
class CausalClaim:
    """因果聲明"""
    cause: str
    effect: str
    relation_type: CausalRelationType
    confidence: float
    evidence: Optional[str] = None


@dataclass
class FactCheckReport:
    """事實查核報告"""
    input_text: str
    check_time: datetime
    duration_seconds: float
    hallucination_analysis: Dict[str, Any] = field(default_factory=dict)
    fact_verification: Dict[str, Any] = field(default_factory=dict)
    temporal_analysis: Dict[str, Any] = field(default_factory=dict)
    causal_validation: Dict[str, Any] = field(default_factory=dict)
    overall_credibility: float = 0.0
    risk_level: str = "low"
    summary: str = ""
    recommendations: List[str] = field(default_factory=list)


# =============================================================================
# 幻覺分析器
# =============================================================================

class HallucinationAnalyzer:
    """
    幻覺分析器

    ‹1› 檢測潛在的幻覺
    ‹2› 分類幻覺類型
    """

    HALLUCINATION_INDICATORS = {
        "temporal": [
            "最新", "目前", "現在", "當前", "今年",
            "current", "currently", "now", "latest", "recent"
        ],
        "fabrication": [
            "根據研究", "專家表示", "據報導", "研究顯示",
            "according to", "study shows", "research indicates"
        ],
        "factual": [
            "是", "為", "有", "達到", "超過",
            "is", "was", "has", "reached", "exceeded"
        ]
    }

    def __init__(self, llm_client=None, knowledge_cutoff: str = "2024-01"):
        self.llm_client = llm_client
        self.knowledge_cutoff = knowledge_cutoff

    def detect_potential_hallucinations(
        self,
        text: str
    ) -> List[Dict[str, Any]]:
        """檢測潛在的幻覺"""
        potential = []

        # 檢查時序性問題
        for indicator in self.HALLUCINATION_INDICATORS["temporal"]:
            if indicator in text.lower():
                potential.append({
                    "type": HallucinationType.TEMPORAL.value,
                    "indicator": indicator,
                    "reason": "包含時效性敏感詞彙"
                })
                break

        # 檢查虛構引用
        for indicator in self.HALLUCINATION_INDICATORS["fabrication"]:
            if indicator in text.lower():
                if not self._has_verifiable_source(text):
                    potential.append({
                        "type": HallucinationType.SOURCE.value,
                        "indicator": indicator,
                        "reason": "引用來源但無法驗證"
                    })
                break

        # 檢查數字和統計
        numbers = self._extract_numbers(text)
        if numbers:
            potential.append({
                "type": HallucinationType.FACTUAL.value,
                "indicator": str(numbers[:3]),
                "reason": "包含具體數字，需要驗證"
            })

        return potential

    def _has_verifiable_source(self, text: str) -> bool:
        """檢查是否有可驗證的來源"""
        url_pattern = r'https?://[^\s]+'
        if re.search(url_pattern, text):
            return True

        citation_patterns = [
            r'\[\d+\]',
            r'\([A-Z][a-z]+,?\s*\d{4}\)',
            r'doi:\s*\d+\.\d+',
        ]
        for pattern in citation_patterns:
            if re.search(pattern, text):
                return True

        return False

    def _extract_numbers(self, text: str) -> List[str]:
        """提取文本中的數字"""
        patterns = [
            r'\d+\.?\d*%',
            r'\$\d+(?:,\d{3})*(?:\.\d+)?',
            r'\d{4}年',
            r'\d+(?:,\d{3})*',
        ]
        numbers = []
        for pattern in patterns:
            numbers.extend(re.findall(pattern, text))
        return numbers[:5]

    async def analyze_with_llm(
        self,
        text: str
    ) -> List[HallucinationInstance]:
        """使用 LLM 進行深度分析"""
        if not self.llm_client:
            # 返回基於規則的分析
            potential = self.detect_potential_hallucinations(text)
            return [
                HallucinationInstance(
                    hallucination_id=str(uuid.uuid4())[:8],
                    content=p["indicator"],
                    hallucination_type=HallucinationType(p["type"]),
                    confidence=0.5,
                    context=text[:200]
                )
                for p in potential
            ]

        prompt = f"""分析以下文本中可能存在的幻覺或不準確資訊。

文本內容：
{text}

模型知識截止日期：{self.knowledge_cutoff}

請識別可能過時、虛構或不準確的資訊。
以 JSON 陣列格式回覆。"""

        response = await self.llm_client.generate(prompt)
        return self._parse_llm_analysis(response, text)

    def _parse_llm_analysis(
        self,
        response: str,
        original_text: str
    ) -> List[HallucinationInstance]:
        """解析 LLM 分析結果"""
        instances = []
        try:
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
                        confidence=item.get("confidence", 0.5),
                        context=original_text[:200]
                    ))
        except Exception:
            pass
        return instances


# =============================================================================
# 事實查核引擎
# =============================================================================

class FactCheckEngine:
    """
    事實查核引擎

    ‹3› 提取可驗證聲明
    ‹4› 驗證事實準確性
    """

    CLAIM_PATTERNS = {
        "numerical": [
            r"(\d+(?:\.\d+)?%)",
            r"(\$\d+(?:,\d{3})*(?:\.\d+)?)",
            r"(\d+(?:,\d{3})*\s*(?:人|個|家|次))",
        ],
        "temporal": [
            r"((?:19|20)\d{2}年)",
            r"((?:上|本|去|今)年)",
        ],
        "attribution": [
            r"((?:據|根據).*?(?:表示|指出|報導))",
        ]
    }

    SOURCE_CREDIBILITY = {
        "academic": 0.95,
        "government": 0.90,
        "major_news": 0.85,
        "tech_news": 0.80,
        "general": 0.60,
        "social": 0.30,
        "unknown": 0.10,
    }

    def __init__(self, llm_client=None, search_engine=None):
        self.llm_client = llm_client
        self.search_engine = search_engine

    def extract_claims(self, text: str) -> List[Claim]:
        """提取可驗證聲明"""
        claims = []
        claim_id = 0
        sentences = self._split_sentences(text)

        for sentence in sentences:
            claim_type = self._identify_claim_type(sentence)
            if claim_type:
                claim_id += 1
                entities = self._extract_entities(sentence)
                claims.append(Claim(
                    claim_id=f"CLM-{claim_id:03d}",
                    text=sentence.strip(),
                    claim_type=claim_type,
                    entities=entities
                ))

        return claims

    def _split_sentences(self, text: str) -> List[str]:
        """分割句子"""
        separators = r'[。！？\.!?]'
        sentences = re.split(separators, text)
        return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 5]

    def _identify_claim_type(self, sentence: str) -> Optional[str]:
        """識別聲明類型"""
        for claim_type, patterns in self.CLAIM_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, sentence):
                    return claim_type

        fact_verbs = ["是", "為", "有", "達到", "超過", "增長"]
        for verb in fact_verbs:
            if verb in sentence and len(sentence) > 10:
                return "factual"

        return None

    def _extract_entities(self, sentence: str) -> List[str]:
        """提取實體"""
        entities = []
        company_pattern = r'([A-Z][a-z]*(?:\s[A-Z][a-z]*)*)'
        entities.extend(re.findall(company_pattern, sentence))
        return list(set(entities))[:5]

    async def verify_claim(
        self,
        claim: Claim,
        max_sources: int = 3
    ) -> VerificationResult:
        """驗證聲明"""
        # 簡化版：不進行實際搜尋
        # 實際使用時應整合搜尋引擎

        return VerificationResult(
            claim=claim,
            status=VerificationStatus.UNCERTAIN,
            confidence=0.5,
            evidences=[],
            explanation="需要外部驗證"
        )

    async def check(self, text: str) -> Dict[str, Any]:
        """執行事實查核"""
        start_time = datetime.now()
        claims = self.extract_claims(text)

        results = []
        for claim in claims:
            result = await self.verify_claim(claim)
            results.append(result)

        end_time = datetime.now()

        verified = sum(1 for r in results if r.status == VerificationStatus.VERIFIED)
        refuted = sum(1 for r in results if r.status == VerificationStatus.REFUTED)

        return {
            "summary": f"共檢查 {len(claims)} 個聲明",
            "claims_count": len(claims),
            "verified_count": verified,
            "refuted_count": refuted,
            "uncertain_count": len(claims) - verified - refuted,
            "overall_credibility": 0.7 if refuted == 0 else 0.5,
            "duration_seconds": (end_time - start_time).total_seconds(),
            "detailed_results": [
                {
                    "claim": r.claim.text,
                    "status": r.status.value,
                    "confidence": r.confidence
                }
                for r in results
            ]
        }


# =============================================================================
# 時序敏感處理器
# =============================================================================

class TemporalAwareProcessor:
    """
    時序感知處理器

    ‹5› 識別時間敏感資訊
    ‹6› 評估資訊時效性
    """

    TEMPORAL_INDICATORS = {
        "current": ["目前", "現在", "當前", "current", "currently", "now"],
        "recent": ["最近", "近期", "最新", "recent", "recently", "latest"],
        "future": ["將", "預計", "即將", "will", "expected", "upcoming"],
        "past": ["曾", "過去", "以前", "was", "were", "previously"],
    }

    VALIDITY_PERIODS = {
        "stock_price": 0,
        "exchange_rate": 0,
        "news": 1,
        "market_data": 7,
        "company_info": 30,
        "research_data": 90,
        "historical_fact": 36500,
    }

    def __init__(self, model_cutoff: str = "2024-01-01"):
        self.model_cutoff = datetime.fromisoformat(model_cutoff)
        self.current_time = datetime.now()

    def analyze_temporal_sensitivity(self, text: str) -> Dict[str, Any]:
        """分析時序敏感性"""
        analysis = {
            "has_temporal_references": False,
            "temporal_markers": [],
            "requires_update": False,
            "sensitive_phrases": [],
            "recommended_actions": []
        }

        for category, indicators in self.TEMPORAL_INDICATORS.items():
            for indicator in indicators:
                if indicator in text.lower():
                    analysis["has_temporal_references"] = True
                    analysis["temporal_markers"].append({
                        "marker": indicator,
                        "category": category
                    })

        # 檢查年份
        year_matches = re.findall(r"((?:19|20)\d{2})", text)
        for year_str in year_matches:
            analysis["sensitive_phrases"].append(f"{year_str}年")
            year = int(year_str)
            if year >= self.model_cutoff.year:
                analysis["requires_update"] = True
                analysis["recommended_actions"].append(
                    f"驗證 {year} 年的資訊"
                )

        return analysis

    def estimate_information_age(
        self,
        text: str,
        source_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """估計資訊年齡"""
        if source_date:
            age_days = (self.current_time - source_date).days
        else:
            age_days = (self.current_time - self.model_cutoff).days

        info_type = self._classify_information_type(text)
        validity_days = self.VALIDITY_PERIODS.get(info_type, 30)

        is_stale = age_days > validity_days
        freshness_score = max(0, 1 - age_days / validity_days) if validity_days else 0

        return {
            "age_days": age_days,
            "information_type": info_type,
            "validity_period_days": validity_days,
            "is_stale": is_stale,
            "freshness_score": freshness_score
        }

    def _classify_information_type(self, text: str) -> str:
        """分類資訊類型"""
        text_lower = text.lower()

        if any(w in text_lower for w in ["股價", "stock", "price"]):
            return "stock_price"
        elif any(w in text_lower for w in ["匯率", "exchange"]):
            return "exchange_rate"
        elif any(w in text_lower for w in ["新聞", "news"]):
            return "news"
        elif any(w in text_lower for w in ["市場", "market"]):
            return "market_data"
        elif any(w in text_lower for w in ["公司", "company"]):
            return "company_info"
        elif any(w in text_lower for w in ["研究", "research"]):
            return "research_data"
        else:
            return "general"

    def generate_temporal_disclaimer(self, text: str) -> str:
        """生成時序免責聲明"""
        analysis = self.analyze_temporal_sensitivity(text)
        age_info = self.estimate_information_age(text)

        if not age_info["is_stale"] and not analysis["requires_update"]:
            return ""

        disclaimers = []
        if age_info["is_stale"]:
            disclaimers.append(
                f"⚠️ 此資訊已有 {age_info['age_days']} 天，可能已過時"
            )

        for action in analysis["recommended_actions"][:2]:
            disclaimers.append(f"📌 {action}")

        return "\n".join(disclaimers)


# =============================================================================
# 因果推理驗證器
# =============================================================================

class CausalReasoningValidator:
    """
    因果推理驗證器

    ‹7› 識別因果主張
    ‹8› 驗證因果關係合理性
    """

    CAUSAL_INDICATORS = {
        "causes": [
            "導致", "造成", "引起", "使", "讓",
            "因為", "由於", "所以", "因此",
            "causes", "leads to", "results in", "because"
        ],
        "enables": [
            "促進", "推動", "有助於",
            "enables", "allows", "facilitates"
        ],
        "prevents": [
            "阻止", "防止", "避免",
            "prevents", "blocks", "inhibits"
        ],
    }

    FALLACY_PATTERNS = {
        "post_hoc": {
            "description": "後此謬誤：僅因時序先後推斷因果",
            "indicators": ["之後", "接著", "然後", "after", "then"]
        },
        "correlation_causation": {
            "description": "相關性謬誤：將相關性等同於因果性",
            "indicators": ["相關", "伴隨", "同時", "correlates"]
        },
        "single_cause": {
            "description": "單一原因謬誤：複雜現象歸因於單一原因",
            "indicators": ["唯一", "只是因為", "solely", "only because"]
        }
    }

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    def extract_causal_claims(self, text: str) -> List[CausalClaim]:
        """提取因果主張"""
        claims = []
        sentences = self._split_sentences(text)

        for sentence in sentences:
            relation_type = self._identify_causal_relation(sentence)
            if relation_type:
                cause, effect = self._extract_cause_effect(sentence, relation_type)
                if cause and effect:
                    claims.append(CausalClaim(
                        cause=cause,
                        effect=effect,
                        relation_type=relation_type,
                        confidence=0.7,
                        evidence=sentence
                    ))

        return claims

    def _split_sentences(self, text: str) -> List[str]:
        """分割句子"""
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
        for indicator in self.CAUSAL_INDICATORS.get(relation_type.value, []):
            if indicator in sentence:
                parts = sentence.split(indicator, 1)
                if len(parts) == 2:
                    return parts[0].strip(), parts[1].strip()
        return None, None

    def validate_causal_claim(self, claim: CausalClaim) -> Dict[str, Any]:
        """驗證因果主張"""
        issues = []
        suggestions = []

        for fallacy_name, fallacy_info in self.FALLACY_PATTERNS.items():
            if claim.evidence:
                for indicator in fallacy_info.get("indicators", []):
                    if indicator in claim.evidence.lower():
                        issues.append(fallacy_info["description"])
                        break

        is_valid = len(issues) == 0

        return {
            "claim": f"{claim.cause} → {claim.effect}",
            "is_valid": is_valid,
            "issues": issues,
            "suggestions": suggestions
        }


# =============================================================================
# 完整事實查核管道
# =============================================================================

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
        self.llm_client = llm_client
        self.search_engine = search_engine

        self.hallucination_analyzer = HallucinationAnalyzer(
            llm_client, model_cutoff
        )
        self.fact_checker = FactCheckEngine(llm_client, search_engine)
        self.temporal_processor = TemporalAwareProcessor(model_cutoff)
        self.causal_validator = CausalReasoningValidator(llm_client)

    async def check(self, text: str) -> FactCheckReport:
        """執行完整的事實查核"""
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

        report = FactCheckReport(
            input_text=text[:1000] if len(text) > 1000 else text,
            check_time=start_time,
            duration_seconds=duration,
            hallucination_analysis=results[0],
            fact_verification=results[1],
            temporal_analysis=results[2],
            causal_validation=results[3]
        )

        self._compute_overall_assessment(report)

        return report

    async def _analyze_hallucinations(self, text: str) -> Dict[str, Any]:
        """幻覺分析"""
        potential = self.hallucination_analyzer.detect_potential_hallucinations(text)
        detailed = await self.hallucination_analyzer.analyze_with_llm(text)

        return {
            "potential_issues": len(potential),
            "detected_hallucinations": len(detailed),
            "details": [h.to_dict() for h in detailed]
        }

    async def _verify_facts(self, text: str) -> Dict[str, Any]:
        """事實驗證"""
        return await self.fact_checker.check(text)

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
            validation = self.causal_validator.validate_causal_claim(claim)
            validations.append(validation)

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

        # 加權平均
        weights = [0.3, 0.4, 0.15, 0.15]
        report.overall_credibility = sum(s * w for s, w in zip(scores, weights))

        # 風險等級
        if report.overall_credibility >= 0.8:
            report.risk_level = "low"
        elif report.overall_credibility >= 0.6:
            report.risk_level = "medium"
        else:
            report.risk_level = "high"

        # 摘要
        report.summary = (
            f"整體可信度：{report.overall_credibility:.1%}，"
            f"風險等級：{report.risk_level}"
        )

        # 建議
        report.recommendations = self._generate_recommendations(report)

    def _generate_recommendations(self, report: FactCheckReport) -> List[str]:
        """生成建議"""
        recommendations = []

        if report.hallucination_analysis.get("detected_hallucinations", 0) > 0:
            recommendations.append("建議對潛在幻覺進行人工驗證")

        if report.fact_verification.get("refuted_count", 0) > 0:
            recommendations.append("發現不準確的聲明，請修正")

        if report.temporal_analysis.get("age_info", {}).get("is_stale", False):
            recommendations.append("部分資訊可能過時，建議更新")

        invalid_causal = (
            report.causal_validation.get("claims_found", 0) -
            report.causal_validation.get("valid_claims", 0)
        )
        if invalid_causal > 0:
            recommendations.append(f"{invalid_causal} 個因果推理需要審視")

        if not recommendations:
            recommendations.append("查核通過，內容可信度較高")

        return recommendations


# =============================================================================
# 示範
# =============================================================================

async def demo():
    """示範事實查核"""
    text = """
    根據最新研究，蘋果公司在 2024 年的營收達到 4000 億美元，
    這主要是因為 iPhone 15 的成功。由於 AI 技術的發展，
    智慧型手機市場增長了 50%。專家預測，到 2025 年，
    全球 AI 晶片市場將達到 1000 億美元規模。
    """

    print("=" * 60)
    print("  事實查核管道示範")
    print("=" * 60)

    pipeline = FactCheckPipeline(
        llm_client=None,
        search_engine=None,
        model_cutoff="2024-01-01"
    )

    report = await pipeline.check(text)

    print(f"\n輸入文本長度：{len(text)} 字符")
    print(f"查核耗時：{report.duration_seconds:.2f} 秒")
    print(f"\n{report.summary}")
    print(f"\n可信度分數：{report.overall_credibility:.2%}")
    print(f"風險等級：{report.risk_level}")

    print("\n幻覺分析：")
    print(f"  - 潛在問題：{report.hallucination_analysis.get('potential_issues', 0)}")
    print(f"  - 檢測到的幻覺：{report.hallucination_analysis.get('detected_hallucinations', 0)}")

    print("\n事實驗證：")
    print(f"  - 聲明數量：{report.fact_verification.get('claims_count', 0)}")
    print(f"  - 待驗證：{report.fact_verification.get('uncertain_count', 0)}")

    print("\n時序分析：")
    sensitivity = report.temporal_analysis.get("sensitivity", {})
    print(f"  - 時間敏感：{sensitivity.get('has_temporal_references', False)}")
    print(f"  - 需要更新：{sensitivity.get('requires_update', False)}")

    print("\n因果驗證：")
    print(f"  - 因果主張數：{report.causal_validation.get('claims_found', 0)}")
    print(f"  - 有效主張數：{report.causal_validation.get('valid_claims', 0)}")

    print("\n建議：")
    for rec in report.recommendations:
        print(f"  - {rec}")


if __name__ == "__main__":
    asyncio.run(demo())
