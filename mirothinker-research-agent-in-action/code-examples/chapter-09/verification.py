#!/usr/bin/env python3
"""
深度研究代理人實戰 - 第 9 章：建構你的第一個研究代理人
高級驗證模組

這個模組實現了事實查證功能：
1. 多來源交叉驗證
2. 矛盾識別
3. 可信度評估

使用方式：
    python verification.py --demo
"""

import asyncio
import argparse
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()


# =============================================================================
# 資料結構
# =============================================================================

@dataclass
class VerificationResult:
    """驗證結果"""
    claim: str
    verified: bool
    confidence: float
    supporting_sources: int
    contradicting_sources: int
    status: str  # "verified", "likely", "conflict", "unverified"
    notes: str = ""


@dataclass
class ReportVerification:
    """報告驗證結果"""
    overall_confidence: float
    verified_count: int
    total_claims: int
    conflicts: List[Dict[str, Any]]
    details: List[VerificationResult]


# =============================================================================
# 模擬資料
# =============================================================================

@dataclass
class MockFinding:
    """模擬的研究發現"""
    content: str
    source_url: str
    relevance_score: float = 0.5


# =============================================================================
# 高級驗證模組
# =============================================================================

class AdvancedVerificationModule:
    """
    高級驗證模組

    ‹1› 多來源交叉驗證
    ‹2› 時效性檢查
    ‹3› 可信度評分
    """

    def __init__(self, llm_client=None, search_module=None):
        self.llm = llm_client
        self.search = search_module

    async def verify_claim(
        self,
        claim: str,
        existing_sources: List[Any]
    ) -> VerificationResult:
        """
        驗證單一陳述

        ‹1› 檢查現有來源
        ‹2› 搜尋額外證據
        ‹3› 評估可信度
        """
        supporting_sources = []
        contradicting_sources = []

        # ‹1› 檢查現有來源中的支持證據
        for source in existing_sources:
            content = getattr(source, 'content', str(source))
            relevance = await self._check_relevance(claim, content)
            if relevance > 0.7:
                supporting_sources.append(source)
            elif relevance < 0.3:
                contradicting_sources.append(source)

        # ‹2› 計算可信度
        confidence = self._calculate_confidence(
            supporting_count=len(supporting_sources),
            contradicting_count=len(contradicting_sources),
            total_sources=len(existing_sources)
        )

        # ‹3› 確定狀態
        status = self._determine_status(confidence, len(contradicting_sources))

        return VerificationResult(
            claim=claim,
            verified=confidence > 0.7,
            confidence=confidence,
            supporting_sources=len(supporting_sources),
            contradicting_sources=len(contradicting_sources),
            status=status,
            notes=f"基於 {len(existing_sources)} 個來源驗證"
        )

    async def _check_relevance(self, claim: str, content: str) -> float:
        """檢查內容與陳述的相關性"""
        # 簡化實現：基於關鍵詞重疊度
        claim_words = set(claim.lower().split())
        content_words = set(content.lower().split())
        overlap = len(claim_words & content_words)
        return min(1.0, overlap / max(len(claim_words), 1) * 1.5)

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

        return max(0.0, min(1.0, base_score - penalty + 0.3))

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

    async def verify_claims(
        self,
        claims: List[str],
        existing_sources: List[Any]
    ) -> List[VerificationResult]:
        """批量驗證多個陳述"""
        results = []
        for claim in claims:
            result = await self.verify_claim(claim, existing_sources)
            results.append(result)
        return results

    async def verify_report(
        self,
        summary: str,
        key_findings: List[str],
        existing_sources: List[Any]
    ) -> ReportVerification:
        """驗證整份報告"""
        claims = key_findings + [summary]
        verification_results = await self.verify_claims(claims, existing_sources)

        overall_confidence = sum(
            r.confidence for r in verification_results
        ) / max(len(verification_results), 1)

        verified_count = sum(1 for r in verification_results if r.verified)

        conflicts = [
            {"claim": r.claim, "confidence": r.confidence, "notes": r.notes}
            for r in verification_results if r.status == "conflict"
        ]

        return ReportVerification(
            overall_confidence=overall_confidence,
            verified_count=verified_count,
            total_claims=len(claims),
            conflicts=conflicts,
            details=verification_results
        )


# =============================================================================
# 可信度計算器
# =============================================================================

class CredibilityCalculator:
    """
    可信度計算器

    ‹1› 來源評估
    ‹2› 時效性評估
    ‹3› 一致性評估
    """

    # 已知可信來源域名
    TRUSTED_DOMAINS = [
        "reuters.com", "bloomberg.com", "wsj.com", "ft.com",
        "nature.com", "science.org", "ieee.org",
        "arxiv.org", "github.com"
    ]

    def evaluate_source(self, url: str) -> float:
        """評估來源可信度"""
        from urllib.parse import urlparse

        try:
            domain = urlparse(url).netloc.lower()
        except:
            return 0.3

        # 檢查是否為已知可信來源
        for trusted in self.TRUSTED_DOMAINS:
            if trusted in domain:
                return 0.9

        # 檢查是否為政府或教育機構
        if domain.endswith(".gov") or domain.endswith(".edu"):
            return 0.85

        # 默認可信度
        return 0.5

    def evaluate_consistency(
        self,
        claim: str,
        sources: List[str]
    ) -> float:
        """評估多來源一致性"""
        if len(sources) < 2:
            return 0.5

        # 簡化實現：假設來源越多，一致性越高
        return min(1.0, 0.5 + len(sources) * 0.1)

    def calculate_overall(
        self,
        source_score: float,
        consistency_score: float,
        recency_score: float = 0.7
    ) -> float:
        """計算整體可信度"""
        weights = {
            "source": 0.4,
            "consistency": 0.4,
            "recency": 0.2
        }

        return (
            source_score * weights["source"] +
            consistency_score * weights["consistency"] +
            recency_score * weights["recency"]
        )


# =============================================================================
# 矛盾檢測器
# =============================================================================

class ContradictionDetector:
    """
    矛盾檢測器

    識別來源間的矛盾資訊
    """

    def __init__(self, llm_client=None):
        self.llm = llm_client

    async def detect(
        self,
        statements: List[str]
    ) -> List[Dict[str, Any]]:
        """
        檢測陳述間的矛盾

        返回矛盾對列表
        """
        contradictions = []

        # 簡化實現：檢測明顯的否定關係
        negative_words = ["不", "沒有", "否", "並非", "無法"]

        for i, s1 in enumerate(statements):
            for j, s2 in enumerate(statements[i+1:], i+1):
                # 檢查是否存在否定關係
                has_negation = any(
                    w in s1 and w not in s2 or w in s2 and w not in s1
                    for w in negative_words
                )

                if has_negation:
                    # 檢查主題是否相關
                    s1_words = set(s1.split())
                    s2_words = set(s2.split())
                    overlap = len(s1_words & s2_words)

                    if overlap > 2:  # 有足夠的共同詞彙
                        contradictions.append({
                            "statement1": s1,
                            "statement2": s2,
                            "type": "potential_negation",
                            "confidence": 0.6
                        })

        return contradictions


# =============================================================================
# 示範
# =============================================================================

async def demo():
    """示範驗證功能"""
    print("=" * 60)
    print("✓ 高級驗證模組示範")
    print("=" * 60)

    # 創建驗證模組
    verifier = AdvancedVerificationModule()

    # 模擬來源
    sources = [
        MockFinding(
            content="NVIDIA 在 AI 晶片市場佔據主導地位，市場份額約 80%",
            source_url="https://reuters.com/nvidia-market"
        ),
        MockFinding(
            content="NVIDIA GPU 是訓練大型語言模型的首選，CUDA 生態系統成熟",
            source_url="https://techcrunch.com/nvidia-cuda"
        ),
        MockFinding(
            content="AMD MI300 系列開始獲得市場認可，正在追趕 NVIDIA",
            source_url="https://amd.com/mi300"
        ),
    ]

    # 驗證陳述
    claims = [
        "NVIDIA 在 AI 晶片市場佔據領先地位",
        "AMD 正在追趕 NVIDIA 的市場份額",
        "Intel 放棄了 AI 晶片業務"
    ]

    print("\n📋 待驗證陳述:")
    for i, claim in enumerate(claims, 1):
        print(f"  {i}. {claim}")

    print("\n🔍 驗證結果:")
    print("-" * 40)

    results = await verifier.verify_claims(claims, sources)

    for result in results:
        status_icon = {
            "verified": "✅",
            "likely": "🔶",
            "conflict": "⚠️",
            "unverified": "❓"
        }.get(result.status, "❓")

        print(f"\n{status_icon} {result.claim}")
        print(f"   狀態: {result.status}")
        print(f"   可信度: {result.confidence:.0%}")
        print(f"   支持來源: {result.supporting_sources}")
        print(f"   矛盾來源: {result.contradicting_sources}")

    # 可信度計算示範
    print("\n" + "-" * 40)
    print("📊 來源可信度評估:")
    print("-" * 40)

    calculator = CredibilityCalculator()

    test_urls = [
        "https://reuters.com/article",
        "https://nature.com/paper",
        "https://random-blog.com/post",
        "https://edu.tw/research"
    ]

    for url in test_urls:
        score = calculator.evaluate_source(url)
        print(f"  {url}: {score:.0%}")


def main():
    parser = argparse.ArgumentParser(description="驗證模組")
    parser.add_argument("--demo", action="store_true", help="執行示範")

    args = parser.parse_args()
    asyncio.run(demo())


if __name__ == "__main__":
    main()
