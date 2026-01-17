"""
chapter-08/hallucination_detector.py

幻覺檢測模組

本模組實作 LLM 幻覺（Hallucination）檢測功能，
判斷 LLM 的回答是否忠於提供的上下文。

使用方式：
    from hallucination_detector import HallucinationDetector
    detector = HallucinationDetector()
    result = detector.detect(answer, contexts)

依賴安裝：
    pip install anthropic numpy
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import re
import os

from anthropic import Anthropic


class HallucinationType(Enum):
    """幻覺類型"""
    FABRICATION = "fabrication"       # 完全編造的資訊
    DISTORTION = "distortion"         # 扭曲原意
    EXTRAPOLATION = "extrapolation"   # 過度推斷
    CONTRADICTION = "contradiction"   # 與上下文矛盾


@dataclass
class HallucinationResult:
    """幻覺檢測結果"""
    has_hallucination: bool
    confidence: float
    hallucination_type: Optional[HallucinationType]
    problematic_segments: List[str]
    explanation: str
    grounded_segments: List[str]


class HallucinationDetector:
    """
    幻覺檢測器

    使用 NLI（Natural Language Inference）風格的方法，
    檢測 LLM 回答是否忠於提供的上下文。
    """

    def __init__(self, api_key: str = None):
        """
        初始化檢測器

        Args:
            api_key: Anthropic API Key
        """
        self.client = Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))

    def detect(
        self,
        answer: str,
        contexts: List[str],
        query: str = None
    ) -> HallucinationResult:
        """
        檢測回答中的幻覺

        Args:
            answer: LLM 的回答
            contexts: 提供給 LLM 的上下文列表
            query: 原始查詢（可選）

        Returns:
            HallucinationResult 檢測結果
        """
        # 建立檢測 Prompt
        context_text = "\n\n".join(f"[上下文 {i+1}]\n{ctx}" for i, ctx in enumerate(contexts))

        detection_prompt = f"""你是一個專業的事實核查專家。你的任務是判斷「回答」中的內容是否完全基於「上下文」。

## 上下文（LLM 可用的資訊）

{context_text}

## LLM 的回答

{answer}

## 檢測任務

請分析回答中的每一個陳述，判斷它是否可以從上下文中找到支持。

輸出格式：
```
整體判斷：[有幻覺/無幻覺]
信心度：[0.0-1.0]
幻覺類型：[fabrication/distortion/extrapolation/contradiction/無]

有問題的內容：
- "具體句子 1"：原因
- "具體句子 2"：原因

有根據的內容：
- "具體句子 1"：來自上下文 X
- "具體句子 2"：來自上下文 Y

詳細說明：
[解釋為什麼判斷為有/無幻覺]
```

請開始檢測："""

        # 呼叫 LLM 進行檢測
        response = self.client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1024,
            messages=[{"role": "user", "content": detection_prompt}]
        )

        detection_text = response.content[0].text

        # 解析檢測結果
        return self._parse_detection_result(detection_text)            # ‹1›

    def _parse_detection_result(self, detection_text: str) -> HallucinationResult:
        """解析 LLM 的檢測結果"""
        # 解析整體判斷
        has_hallucination = "有幻覺" in detection_text

        # 解析信心度
        confidence_match = re.search(r'信心度[：:]\s*([0-9.]+)', detection_text)
        confidence = float(confidence_match.group(1)) if confidence_match else 0.5

        # 解析幻覺類型
        hallucination_type = None
        for h_type in HallucinationType:
            if h_type.value in detection_text.lower():
                hallucination_type = h_type
                break

        # 解析有問題的內容
        problematic_segments = []
        problem_section = re.search(
            r'有問題的內容[：:](.+?)(?=有根據的內容|詳細說明|$)',
            detection_text,
            re.DOTALL
        )
        if problem_section:
            problematic_segments = re.findall(r'"([^"]+)"', problem_section.group(1))

        # 解析有根據的內容
        grounded_segments = []
        grounded_section = re.search(
            r'有根據的內容[：:](.+?)(?=詳細說明|$)',
            detection_text,
            re.DOTALL
        )
        if grounded_section:
            grounded_segments = re.findall(r'"([^"]+)"', grounded_section.group(1))

        # 解析詳細說明
        explanation_match = re.search(r'詳細說明[：:](.+?)$', detection_text, re.DOTALL)
        explanation = explanation_match.group(1).strip() if explanation_match else ""

        return HallucinationResult(
            has_hallucination=has_hallucination,
            confidence=confidence,
            hallucination_type=hallucination_type,
            problematic_segments=problematic_segments,
            explanation=explanation,
            grounded_segments=grounded_segments
        )


class SimpleHallucinationChecker:
    """
    簡單幻覺檢查器

    使用規則式方法進行快速檢查，不需要額外的 LLM 呼叫。
    """

    # 幻覺指標詞彙
    SPECULATION_INDICATORS = [
        "可能", "也許", "大概", "應該是", "我猜", "我認為",
        "通常來說", "一般而言", "據我所知"
    ]

    FABRICATION_INDICATORS = [
        "根據官方資料", "根據最新消息", "研究顯示",
        "專家表示", "數據顯示"
    ]

    def check(
        self,
        answer: str,
        contexts: List[str]
    ) -> Dict:
        """
        快速檢查幻覺風險

        Args:
            answer: LLM 回答
            contexts: 上下文列表

        Returns:
            檢查結果字典
        """
        # 合併上下文
        context_text = " ".join(contexts).lower()
        answer_lower = answer.lower()

        # 檢查推測性詞彙
        speculation_found = [
            word for word in self.SPECULATION_INDICATORS
            if word in answer_lower
        ]

        # 檢查編造指標
        fabrication_found = [
            phrase for phrase in self.FABRICATION_INDICATORS
            if phrase in answer_lower and phrase not in context_text
        ]                                                              # ‹2›

        # 計算風險分數
        risk_score = (
            len(speculation_found) * 0.1 +
            len(fabrication_found) * 0.3
        )
        risk_score = min(risk_score, 1.0)

        return {
            "risk_score": risk_score,
            "risk_level": self._get_risk_level(risk_score),
            "speculation_indicators": speculation_found,
            "fabrication_indicators": fabrication_found,
            "recommendation": self._get_recommendation(risk_score)
        }

    def _get_risk_level(self, score: float) -> str:
        """根據分數判斷風險等級"""
        if score < 0.2:
            return "low"
        elif score < 0.5:
            return "medium"
        else:
            return "high"

    def _get_recommendation(self, score: float) -> str:
        """根據風險分數給出建議"""
        if score < 0.2:
            return "回答看起來可信，但建議人工抽查"
        elif score < 0.5:
            return "發現一些可疑指標，建議仔細核實"
        else:
            return "高風險回答，強烈建議人工審核"


def demo_hallucination_detection():
    """演示幻覺檢測"""
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    console = Console()

    # 測試案例
    contexts = [
        "如何重設密碼？請點擊登入頁面的「忘記密碼」連結，輸入您的電子郵件地址。",
        "密碼重設連結有效期為 24 小時。如果連結過期，請重新申請。",
    ]

    # 案例 1：無幻覺的回答
    good_answer = "您可以點擊登入頁面的「忘記密碼」連結來重設密碼。系統會發送重設連結到您的電子郵件，請注意這個連結有效期為 24 小時。"

    # 案例 2：有幻覺的回答
    bad_answer = "您可以點擊「忘記密碼」連結來重設密碼。根據官方資料，您也可以撥打客服專線 0800-123-456 來重設密碼。通常來說，處理時間約為 2-3 個工作天。"

    checker = SimpleHallucinationChecker()

    console.print("\n[bold]═══ 幻覺檢測演示 ═══[/bold]\n")

    # 檢測好的回答
    console.print(Panel(good_answer, title="案例 1：無幻覺回答", border_style="green"))
    result1 = checker.check(good_answer, contexts)
    console.print(f"風險分數: {result1['risk_score']:.2f}")
    console.print(f"風險等級: {result1['risk_level']}")
    console.print(f"建議: {result1['recommendation']}\n")

    # 檢測有問題的回答
    console.print(Panel(bad_answer, title="案例 2：有幻覺回答", border_style="red"))
    result2 = checker.check(bad_answer, contexts)
    console.print(f"風險分數: {result2['risk_score']:.2f}")
    console.print(f"風險等級: {result2['risk_level']}")
    console.print(f"編造指標: {result2['fabrication_indicators']}")
    console.print(f"推測指標: {result2['speculation_indicators']}")
    console.print(f"建議: {result2['recommendation']}")


if __name__ == "__main__":
    demo_hallucination_detection()
