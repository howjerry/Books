#!/usr/bin/env python3
"""
深度研究代理人實戰 - 第 10 章：多代理人協作系統
衝突解決器

這個模組實現了專家意見衝突的檢測與解決：
1. 衝突檢測（數值、類別、信心）
2. 解決策略（仲裁、共識、呈現）
3. 結果整合

使用方式：
    python conflict_resolver.py --demo
"""

import asyncio
import argparse
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from collections import Counter
import statistics


# =============================================================================
# 資料結構
# =============================================================================

class ConflictType(Enum):
    """衝突類型"""
    NUMERICAL = "numerical"           # 數值分歧
    CATEGORICAL = "categorical"       # 類別分歧
    CONFIDENCE = "confidence"         # 信心分歧
    CONCLUSION = "conclusion"         # 結論矛盾
    TEMPORAL = "temporal"            # 時間敏感分歧


class ConflictSeverity(Enum):
    """衝突嚴重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ResolutionMethod(Enum):
    """解決方法"""
    ARBITRATION = "arbitration"       # 仲裁
    CONSENSUS = "consensus"           # 共識
    WEIGHTED_AVERAGE = "weighted_avg" # 加權平均
    MAJORITY_VOTE = "majority_vote"   # 多數決
    PRESENTATION = "presentation"     # 呈現（不解決）


@dataclass
class Conflict:
    """
    衝突記錄

    ‹1› 記錄衝突的詳細資訊
    ‹2› 追蹤解決狀態
    """
    conflict_id: str
    conflict_type: ConflictType
    severity: ConflictSeverity
    description: str
    involved_agents: List[str]
    conflicting_values: Dict[str, Any]
    context: Dict[str, Any] = field(default_factory=dict)
    resolution: Optional[Dict[str, Any]] = None
    resolved: bool = False
    detected_at: datetime = field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "conflict_id": self.conflict_id,
            "type": self.conflict_type.value,
            "severity": self.severity.value,
            "description": self.description,
            "involved_agents": self.involved_agents,
            "conflicting_values": self.conflicting_values,
            "context": self.context,
            "resolution": self.resolution,
            "resolved": self.resolved,
            "detected_at": self.detected_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None
        }


@dataclass
class ResolutionResult:
    """
    解決結果

    記錄衝突解決的過程與結論
    """
    conflict: Conflict
    method: ResolutionMethod
    final_value: Any
    confidence: float
    reasoning: str
    supporting_evidence: List[str] = field(default_factory=list)
    dissenting_views: List[Dict] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "conflict_id": self.conflict.conflict_id,
            "method": self.method.value,
            "final_value": self.final_value,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "supporting_evidence": self.supporting_evidence,
            "dissenting_views": self.dissenting_views
        }


# =============================================================================
# 衝突檢測器
# =============================================================================

class ConflictDetector:
    """
    衝突檢測器

    ‹1› 識別專家分析中的矛盾
    ‹2› 評估衝突嚴重程度
    ‹3› 分類衝突類型
    """

    def __init__(self):
        self._conflict_counter = 0
        self.thresholds = {
            "numerical_deviation": 0.25,      # 數值偏差閾值
            "confidence_spread": 0.20,        # 信心差異閾值
            "agreement_ratio": 0.6            # 一致性比率閾值
        }

    def detect_all(
        self,
        expert_reports: Dict[str, Dict[str, Any]]
    ) -> List[Conflict]:
        """
        檢測所有類型的衝突

        整合所有檢測方法，返回完整衝突列表
        """
        conflicts = []

        # 數值衝突
        conflicts.extend(self.detect_numerical_conflicts(expert_reports))

        # 類別衝突
        conflicts.extend(self.detect_categorical_conflicts(expert_reports))

        # 信心衝突
        conflicts.extend(self.detect_confidence_conflicts(expert_reports))

        # 結論衝突
        conflicts.extend(self.detect_conclusion_conflicts(expert_reports))

        return conflicts

    def detect_numerical_conflicts(
        self,
        reports: Dict[str, Dict[str, Any]]
    ) -> List[Conflict]:
        """
        檢測數值衝突

        當專家對同一數值的估計差異超過閾值時標記
        """
        conflicts = []

        # 收集所有數值估計
        numerical_values = {}
        for agent_id, report in reports.items():
            findings = report.get("findings", {})
            self._extract_numerical(agent_id, findings, numerical_values)

        # 比較各指標
        for metric, values in numerical_values.items():
            if len(values) < 2:
                continue

            nums = [v["value"] for v in values if isinstance(v["value"], (int, float))]
            if len(nums) < 2:
                continue

            mean = statistics.mean(nums)
            if mean == 0:
                continue

            # 計算變異係數
            stdev = statistics.stdev(nums) if len(nums) > 1 else 0
            cv = stdev / abs(mean)

            if cv > self.thresholds["numerical_deviation"]:
                self._conflict_counter += 1
                conflicts.append(Conflict(
                    conflict_id=f"conflict_{self._conflict_counter:04d}",
                    conflict_type=ConflictType.NUMERICAL,
                    severity=self._assess_severity(cv),
                    description=f"指標「{metric}」的數值估計存在分歧 (CV={cv:.2%})",
                    involved_agents=[v["agent"] for v in values],
                    conflicting_values={v["agent"]: v["value"] for v in values},
                    context={"metric": metric, "mean": mean, "cv": cv}
                ))

        return conflicts

    def _extract_numerical(
        self,
        agent_id: str,
        data: Dict,
        result: Dict,
        prefix: str = ""
    ):
        """遞歸提取數值"""
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key

            if isinstance(value, (int, float)):
                if full_key not in result:
                    result[full_key] = []
                result[full_key].append({"agent": agent_id, "value": value})
            elif isinstance(value, dict):
                self._extract_numerical(agent_id, value, result, full_key)

    def detect_categorical_conflicts(
        self,
        reports: Dict[str, Dict[str, Any]]
    ) -> List[Conflict]:
        """
        檢測類別衝突

        當專家對同一類別問題的回答不一致時標記
        """
        conflicts = []

        # 提取類別判斷
        categorical_values = {}
        for agent_id, report in reports.items():
            findings = report.get("findings", {})
            self._extract_categorical(agent_id, findings, categorical_values)

        # 檢查一致性
        for category, values in categorical_values.items():
            if len(values) < 2:
                continue

            unique_values = set(v["value"] for v in values)
            if len(unique_values) > 1:
                # 計算一致性比率
                counter = Counter(v["value"] for v in values)
                most_common_count = counter.most_common(1)[0][1]
                agreement_ratio = most_common_count / len(values)

                if agreement_ratio < self.thresholds["agreement_ratio"]:
                    self._conflict_counter += 1
                    conflicts.append(Conflict(
                        conflict_id=f"conflict_{self._conflict_counter:04d}",
                        conflict_type=ConflictType.CATEGORICAL,
                        severity=self._assess_severity(1 - agreement_ratio),
                        description=f"類別「{category}」的判斷存在分歧",
                        involved_agents=[v["agent"] for v in values],
                        conflicting_values={v["agent"]: v["value"] for v in values},
                        context={
                            "category": category,
                            "unique_values": list(unique_values),
                            "agreement_ratio": agreement_ratio
                        }
                    ))

        return conflicts

    def _extract_categorical(
        self,
        agent_id: str,
        data: Dict,
        result: Dict,
        prefix: str = ""
    ):
        """遞歸提取類別值"""
        categorical_keys = ["trend", "status", "assessment", "risk_level", "outlook"]

        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key

            if key in categorical_keys and isinstance(value, str):
                if full_key not in result:
                    result[full_key] = []
                result[full_key].append({"agent": agent_id, "value": value})
            elif isinstance(value, dict):
                self._extract_categorical(agent_id, value, result, full_key)

    def detect_confidence_conflicts(
        self,
        reports: Dict[str, Dict[str, Any]]
    ) -> List[Conflict]:
        """
        檢測信心衝突

        當專家的信心分數差異過大時標記
        """
        conflicts = []

        confidences = []
        for agent_id, report in reports.items():
            conf = report.get("confidence", 0.5)
            confidences.append({"agent": agent_id, "value": conf})

        if len(confidences) < 2:
            return conflicts

        values = [c["value"] for c in confidences]
        spread = max(values) - min(values)

        if spread > self.thresholds["confidence_spread"]:
            self._conflict_counter += 1
            conflicts.append(Conflict(
                conflict_id=f"conflict_{self._conflict_counter:04d}",
                conflict_type=ConflictType.CONFIDENCE,
                severity=self._assess_severity(spread),
                description=f"專家信心分數差異較大 ({min(values):.0%} - {max(values):.0%})",
                involved_agents=[c["agent"] for c in confidences],
                conflicting_values={c["agent"]: c["value"] for c in confidences},
                context={"spread": spread, "min": min(values), "max": max(values)}
            ))

        return conflicts

    def detect_conclusion_conflicts(
        self,
        reports: Dict[str, Dict[str, Any]]
    ) -> List[Conflict]:
        """
        檢測結論衝突

        當專家的核心結論互相矛盾時標記
        """
        conflicts = []

        # 簡化實現：檢測明顯的正負面結論對立
        positive_keywords = ["成長", "上升", "看好", "強勁", "樂觀"]
        negative_keywords = ["下降", "萎縮", "悲觀", "衰退", "風險"]

        agent_sentiments = {}
        for agent_id, report in reports.items():
            findings_str = str(report.get("findings", {}))

            pos_count = sum(1 for kw in positive_keywords if kw in findings_str)
            neg_count = sum(1 for kw in negative_keywords if kw in findings_str)

            if pos_count > neg_count + 2:
                agent_sentiments[agent_id] = "positive"
            elif neg_count > pos_count + 2:
                agent_sentiments[agent_id] = "negative"
            else:
                agent_sentiments[agent_id] = "neutral"

        # 檢查是否存在對立
        sentiments = list(agent_sentiments.values())
        if "positive" in sentiments and "negative" in sentiments:
            positive_agents = [a for a, s in agent_sentiments.items() if s == "positive"]
            negative_agents = [a for a, s in agent_sentiments.items() if s == "negative"]

            self._conflict_counter += 1
            conflicts.append(Conflict(
                conflict_id=f"conflict_{self._conflict_counter:04d}",
                conflict_type=ConflictType.CONCLUSION,
                severity=ConflictSeverity.HIGH,
                description="專家對整體結論存在正負面分歧",
                involved_agents=positive_agents + negative_agents,
                conflicting_values=agent_sentiments,
                context={
                    "positive_agents": positive_agents,
                    "negative_agents": negative_agents
                }
            ))

        return conflicts

    def _assess_severity(self, deviation: float) -> ConflictSeverity:
        """評估衝突嚴重程度"""
        if deviation < 0.15:
            return ConflictSeverity.LOW
        elif deviation < 0.30:
            return ConflictSeverity.MEDIUM
        elif deviation < 0.50:
            return ConflictSeverity.HIGH
        else:
            return ConflictSeverity.CRITICAL


# =============================================================================
# 衝突解決器
# =============================================================================

class ConflictResolver:
    """
    衝突解決器基類

    ‹1› 定義解決介面
    ‹2› 提供通用工具方法
    """

    async def resolve(
        self,
        conflict: Conflict,
        reports: Dict[str, Dict[str, Any]]
    ) -> ResolutionResult:
        """解決衝突（子類實現）"""
        raise NotImplementedError


class WeightedAverageResolver(ConflictResolver):
    """
    加權平均解決器

    適用於數值型衝突
    """

    def __init__(self):
        self.weights = {
            "財務分析師": 1.0,
            "產業分析師": 0.9,
            "技術專家": 0.8,
            "地緣政治顧問": 0.7
        }

    async def resolve(
        self,
        conflict: Conflict,
        reports: Dict[str, Dict[str, Any]]
    ) -> ResolutionResult:
        """使用加權平均解決數值衝突"""
        values = conflict.conflicting_values
        weighted_sum = 0
        total_weight = 0

        for agent, value in values.items():
            if not isinstance(value, (int, float)):
                continue

            # 從 reports 獲取信心分數作為額外權重
            agent_report = next(
                (r for r in reports.values() if r.get("analyst") == agent),
                {}
            )
            confidence = agent_report.get("confidence", 0.5)

            base_weight = self.weights.get(agent, 0.5)
            final_weight = base_weight * confidence

            weighted_sum += value * final_weight
            total_weight += final_weight

        final_value = weighted_sum / total_weight if total_weight > 0 else 0

        # 標記衝突為已解決
        conflict.resolved = True
        conflict.resolved_at = datetime.now()
        conflict.resolution = {"method": "weighted_average", "value": final_value}

        return ResolutionResult(
            conflict=conflict,
            method=ResolutionMethod.WEIGHTED_AVERAGE,
            final_value=final_value,
            confidence=0.75,
            reasoning=f"使用加權平均整合 {len(values)} 位專家的估計",
            supporting_evidence=[f"{a}: {v}" for a, v in values.items()]
        )


class MajorityVoteResolver(ConflictResolver):
    """
    多數決解決器

    適用於類別型衝突
    """

    async def resolve(
        self,
        conflict: Conflict,
        reports: Dict[str, Dict[str, Any]]
    ) -> ResolutionResult:
        """使用多數決解決類別衝突"""
        values = conflict.conflicting_values
        counter = Counter(values.values())

        # 獲取最多支持的選項
        most_common = counter.most_common(1)[0]
        final_value = most_common[0]
        support_count = most_common[1]

        # 計算支持率作為信心
        confidence = support_count / len(values)

        # 找出持不同意見的專家
        dissenters = [
            {"agent": a, "value": v}
            for a, v in values.items()
            if v != final_value
        ]

        conflict.resolved = True
        conflict.resolved_at = datetime.now()
        conflict.resolution = {"method": "majority_vote", "value": final_value}

        return ResolutionResult(
            conflict=conflict,
            method=ResolutionMethod.MAJORITY_VOTE,
            final_value=final_value,
            confidence=confidence,
            reasoning=f"{support_count}/{len(values)} 位專家支持「{final_value}」",
            supporting_evidence=[f"{a} 選擇 {v}" for a, v in values.items() if v == final_value],
            dissenting_views=dissenters
        )


class PresentationResolver(ConflictResolver):
    """
    呈現解決器

    不解決衝突，而是如實呈現各方觀點
    """

    async def resolve(
        self,
        conflict: Conflict,
        reports: Dict[str, Dict[str, Any]]
    ) -> ResolutionResult:
        """呈現各方觀點"""
        values = conflict.conflicting_values

        # 收集各方論據
        viewpoints = []
        for agent, value in values.items():
            agent_report = next(
                (r for r in reports.values() if r.get("analyst") == agent),
                {}
            )
            viewpoints.append({
                "agent": agent,
                "value": value,
                "confidence": agent_report.get("confidence", 0.5),
                "sources": agent_report.get("sources", [])
            })

        conflict.resolved = True
        conflict.resolved_at = datetime.now()
        conflict.resolution = {"method": "presentation", "viewpoints": viewpoints}

        return ResolutionResult(
            conflict=conflict,
            method=ResolutionMethod.PRESENTATION,
            final_value=viewpoints,
            confidence=0.5,
            reasoning="專家意見存在分歧，以下呈現各方觀點供參考",
            supporting_evidence=[f"{v['agent']}: {v['value']}" for v in viewpoints]
        )


# =============================================================================
# 整合解決器
# =============================================================================

class IntegratedResolver:
    """
    整合解決器

    ‹1› 根據衝突類型選擇適當的解決策略
    ‹2› 管理整個解決流程
    ‹3› 生成解決報告
    """

    def __init__(self):
        self.resolvers = {
            ConflictType.NUMERICAL: WeightedAverageResolver(),
            ConflictType.CATEGORICAL: MajorityVoteResolver(),
            ConflictType.CONFIDENCE: PresentationResolver(),
            ConflictType.CONCLUSION: PresentationResolver()
        }

    def set_resolver(self, conflict_type: ConflictType, resolver: ConflictResolver):
        """設置特定類型的解決器"""
        self.resolvers[conflict_type] = resolver

    async def resolve_all(
        self,
        conflicts: List[Conflict],
        reports: Dict[str, Dict[str, Any]]
    ) -> List[ResolutionResult]:
        """解決所有衝突"""
        results = []

        for conflict in conflicts:
            resolver = self.resolvers.get(
                conflict.conflict_type,
                PresentationResolver()
            )
            result = await resolver.resolve(conflict, reports)
            results.append(result)

        return results

    def generate_report(self, results: List[ResolutionResult]) -> str:
        """生成衝突解決報告"""
        lines = [
            "# 衝突解決報告",
            "",
            f"共檢測到 {len(results)} 個衝突",
            "",
            "---",
            ""
        ]

        for i, result in enumerate(results, 1):
            lines.extend([
                f"## 衝突 {i}: {result.conflict.description}",
                "",
                f"- **類型**: {result.conflict.conflict_type.value}",
                f"- **嚴重程度**: {result.conflict.severity.value}",
                f"- **涉及專家**: {', '.join(result.conflict.involved_agents)}",
                f"- **解決方法**: {result.method.value}",
                f"- **最終結論**: {result.final_value}",
                f"- **信心度**: {result.confidence:.0%}",
                f"- **理由**: {result.reasoning}",
                ""
            ])

            if result.dissenting_views:
                lines.append("**不同意見**:")
                for dv in result.dissenting_views:
                    lines.append(f"  - {dv['agent']}: {dv['value']}")
                lines.append("")

            lines.append("---")
            lines.append("")

        return "\n".join(lines)


# =============================================================================
# 示範
# =============================================================================

async def demo():
    """示範衝突檢測與解決"""
    print("=" * 60)
    print("  衝突解決器示範")
    print("=" * 60)

    # 模擬專家報告（包含衝突）
    expert_reports = {
        "industry": {
            "analyst": "產業分析師",
            "analysis_type": "industry_analysis",
            "confidence": 0.82,
            "findings": {
                "market_size": {"current": 500, "growth_rate": 0.15},
                "competitive_landscape": {
                    "concentration": "高度集中",
                    "trend": "上升"
                }
            },
            "sources": ["IDC 報告", "Gartner 分析"]
        },
        "tech": {
            "analyst": "技術專家",
            "analysis_type": "technology_analysis",
            "confidence": 0.75,
            "findings": {
                "market_size": {"current": 480, "growth_rate": 0.18},
                "technology_maturity": "成熟",
                "trend": "穩定"
            },
            "sources": ["技術白皮書", "專利分析"]
        },
        "finance": {
            "analyst": "財務分析師",
            "analysis_type": "financial_analysis",
            "confidence": 0.88,
            "findings": {
                "market_size": {"current": 520, "growth_rate": 0.12},
                "valuation": {"pe_ratio": 65, "assessment": "偏高"},
                "trend": "上升"
            },
            "sources": ["財報", "分析師報告"]
        },
        "geopolitical": {
            "analyst": "地緣政治顧問",
            "analysis_type": "geopolitical_analysis",
            "confidence": 0.65,
            "findings": {
                "risk_level": "高",
                "trend": "下降",
                "outlook": "悲觀"
            },
            "sources": ["智庫報告", "政策分析"]
        }
    }

    # 衝突檢測
    print("\n步驟 1: 衝突檢測")
    print("-" * 40)

    detector = ConflictDetector()
    conflicts = detector.detect_all(expert_reports)

    print(f"檢測到 {len(conflicts)} 個衝突:")
    for conflict in conflicts:
        print(f"\n  [{conflict.conflict_type.value}] {conflict.description}")
        print(f"    嚴重程度: {conflict.severity.value}")
        print(f"    涉及專家: {', '.join(conflict.involved_agents)}")

    # 衝突解決
    print("\n\n步驟 2: 衝突解決")
    print("-" * 40)

    resolver = IntegratedResolver()
    results = await resolver.resolve_all(conflicts, expert_reports)

    for result in results:
        print(f"\n  解決方案: {result.method.value}")
        print(f"    結論: {result.final_value}")
        print(f"    信心度: {result.confidence:.0%}")
        print(f"    理由: {result.reasoning}")

    # 生成報告
    print("\n\n步驟 3: 生成報告")
    print("-" * 40)

    report = resolver.generate_report(results)
    print(report[:1000] + "..." if len(report) > 1000 else report)


def main():
    parser = argparse.ArgumentParser(description="衝突解決器")
    parser.add_argument("--demo", action="store_true", help="執行示範")

    args = parser.parse_args()
    asyncio.run(demo())


if __name__ == "__main__":
    main()
