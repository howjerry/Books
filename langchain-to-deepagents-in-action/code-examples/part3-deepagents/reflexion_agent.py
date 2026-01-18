"""
Chapter 9: 自我修正模式 (The Reflexion Pattern) - 獨立範例

Generator-Evaluator-Refiner 架構實現
"""

import os
import re
from typing import TypedDict, Annotated, Literal
from pydantic import BaseModel, Field
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages


# ============================================================
# 1. 評估結果結構
# ============================================================

class QualityDimension(BaseModel):
    """品質維度評分"""
    name: str
    score: float = Field(ge=0, le=1)
    feedback: str


class EvaluationResult(BaseModel):
    """評估結果"""
    overall_score: float = Field(ge=0, le=1, description="綜合評分 0-1")
    dimensions: list[QualityDimension] = Field(description="各維度評分")
    issues: list[str] = Field(default_factory=list, description="發現的問題")
    suggestions: list[str] = Field(default_factory=list, description="改進建議")
    passed: bool = Field(description="是否通過品質門檻")


class Reflection(BaseModel):
    """反思結果"""
    what_went_wrong: str = Field(description="問題分析")
    root_cause: str = Field(description="根本原因")
    improvement_strategy: str = Field(description="改進策略")


# ============================================================
# 2. 狀態定義
# ============================================================

class ReflexionState(TypedDict):
    messages: Annotated[list, add_messages]
    task: str
    task_type: str  # "code", "text", "analysis"
    current_output: str | None
    output_history: list[str]
    evaluation: EvaluationResult | None
    evaluation_history: list[dict]
    reflections: list[str]
    iteration: int
    max_iterations: int
    quality_threshold: float


# ============================================================
# 3. 評估器實現
# ============================================================

class CodeEvaluator:
    """‹1› 程式碼品質評估器"""

    def __init__(self, llm):
        self.llm = llm

    def evaluate(self, code: str, task: str) -> EvaluationResult:
        """評估程式碼品質"""
        dimensions = []

        # ‹2› 語法正確性檢查
        syntax_score, syntax_feedback = self._check_syntax(code)
        dimensions.append(QualityDimension(
            name="語法正確性",
            score=syntax_score,
            feedback=syntax_feedback
        ))

        # ‹3› 功能完整性檢查（使用 LLM）
        completeness = self._check_completeness(code, task)
        dimensions.append(completeness)

        # ‹4› 程式碼風格檢查
        style = self._check_style(code)
        dimensions.append(style)

        # ‹5› 錯誤處理檢查
        error_handling = self._check_error_handling(code)
        dimensions.append(error_handling)

        # 計算綜合評分
        weights = [0.3, 0.4, 0.15, 0.15]
        overall_score = sum(
            d.score * w for d, w in zip(dimensions, weights)
        )

        # 收集問題和建議
        issues = []
        suggestions = []
        for dim in dimensions:
            if dim.score < 0.7:
                issues.append(f"{dim.name}: {dim.feedback}")
            if dim.score < 0.9:
                suggestions.append(f"改進 {dim.name}")

        return EvaluationResult(
            overall_score=overall_score,
            dimensions=dimensions,
            issues=issues,
            suggestions=suggestions,
            passed=overall_score >= 0.8
        )

    def _check_syntax(self, code: str) -> tuple[float, str]:
        """檢查 Python 語法"""
        try:
            compile(code, "<string>", "exec")
            return 1.0, "語法正確"
        except SyntaxError as e:
            return 0.0, f"語法錯誤：{e.msg} (行 {e.lineno})"

    def _check_completeness(self, code: str, task: str) -> QualityDimension:
        """使用 LLM 檢查功能完整性"""
        prompt = f"""評估以下程式碼是否完整實現了任務要求。

任務：{task}

程式碼：
```python
{code}
```

請評估：
1. 是否實現了所有要求的功能
2. 是否有遺漏的邊界情況
3. 返回格式：分數(0-1)|評語

例如：0.8|基本功能完整，但缺少空值處理"""

        response = self.llm.invoke([HumanMessage(content=prompt)])
        try:
            parts = response.content.strip().split("|")
            score = float(parts[0])
            feedback = parts[1] if len(parts) > 1 else "評估完成"
        except (ValueError, IndexError):
            score = 0.7
            feedback = response.content[:100]

        return QualityDimension(
            name="功能完整性",
            score=min(max(score, 0), 1),
            feedback=feedback
        )

    def _check_style(self, code: str) -> QualityDimension:
        """檢查程式碼風格"""
        issues = []

        # 檢查行長度
        long_lines = [i for i, line in enumerate(code.split("\n"), 1)
                      if len(line) > 100]
        if long_lines:
            issues.append(f"行過長：{long_lines[:3]}")

        # 檢查命名規範
        if re.search(r'\b[a-z][A-Z]', code):  # 混合命名
            issues.append("建議使用一致的命名規範")

        # 檢查文檔字串
        if 'def ' in code and '"""' not in code and "'''" not in code:
            issues.append("缺少文檔字串")

        score = max(0, 1 - len(issues) * 0.2)
        feedback = "；".join(issues) if issues else "風格良好"

        return QualityDimension(
            name="程式碼風格",
            score=score,
            feedback=feedback
        )

    def _check_error_handling(self, code: str) -> QualityDimension:
        """檢查錯誤處理"""
        has_try = "try:" in code
        has_except = "except" in code
        has_validation = any(kw in code for kw in ["if not", "raise", "assert"])

        if has_try and has_except and has_validation:
            return QualityDimension(
                name="錯誤處理",
                score=1.0,
                feedback="有完整的錯誤處理"
            )
        elif has_try or has_validation:
            return QualityDimension(
                name="錯誤處理",
                score=0.6,
                feedback="有基本錯誤處理，可加強"
            )
        else:
            return QualityDimension(
                name="錯誤處理",
                score=0.3,
                feedback="缺少錯誤處理機制"
            )


# ============================================================
# 4. 節點實現
# ============================================================

llm = ChatAnthropic(model="claude-sonnet-4-20250514", temperature=0.7)
evaluator = CodeEvaluator(ChatAnthropic(model="claude-sonnet-4-20250514", temperature=0))


def generator_node(state: ReflexionState) -> dict:
    """‹6› Generator 節點：生成或改進輸出"""
    task = state["task"]
    iteration = state["iteration"]
    reflections = state["reflections"]
    current_output = state["current_output"]

    print(f"\n🔄 迭代 {iteration + 1}")

    if iteration == 0:
        # 首次生成
        system_prompt = """你是一位專業的 Python 開發者。
請根據任務要求生成高品質的程式碼。

要求：
1. 程式碼要完整可運行
2. 包含適當的錯誤處理
3. 添加清晰的文檔字串
4. 遵循 PEP8 風格指南"""

        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"任務：{task}\n\n請生成程式碼：")
        ])
    else:
        # 基於反思改進
        system_prompt = """你是一位專業的 Python 開發者。
請根據之前的反思和建議改進程式碼。

重點關注之前識別出的問題，確保這次解決它們。"""

        reflection_context = "\n".join([
            f"反思 {i+1}: {r}"
            for i, r in enumerate(reflections[-3:])  # 最近 3 次反思
        ])

        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"""
任務：{task}

之前的程式碼：
```python
{current_output}
```

反思與改進建議：
{reflection_context}

請生成改進後的程式碼：
""")
        ])

    # 提取程式碼
    output = response.content
    code_match = re.search(r'```python\n(.*?)\n```', output, re.DOTALL)
    if code_match:
        output = code_match.group(1)

    print(f"  📝 生成程式碼：{len(output)} 字符")

    return {
        "current_output": output,
        "output_history": [output]
    }


def evaluator_node(state: ReflexionState) -> dict:
    """‹7› Evaluator 節點：評估輸出品質"""
    current_output = state["current_output"]
    task = state["task"]

    print("  🔍 評估品質...")

    evaluation = evaluator.evaluate(current_output, task)

    print(f"  📊 綜合評分：{evaluation.overall_score:.2f}")
    for dim in evaluation.dimensions:
        status = "✅" if dim.score >= 0.8 else "⚠️" if dim.score >= 0.5 else "❌"
        print(f"    {status} {dim.name}: {dim.score:.2f} - {dim.feedback}")

    if evaluation.issues:
        print(f"  ⚠️ 問題：{', '.join(evaluation.issues[:3])}")

    return {
        "evaluation": evaluation,
        "evaluation_history": [evaluation.model_dump()]
    }


def refiner_node(state: ReflexionState) -> dict:
    """‹8› Refiner 節點：反思並生成改進策略"""
    evaluation = state["evaluation"]
    current_output = state["current_output"]
    task = state["task"]

    print("  💭 進行反思...")

    # 使用 LLM 進行深度反思
    reflection_prompt = f"""作為一位資深開發者，請反思以下程式碼的問題並提出改進策略。

任務：{task}

程式碼：
```python
{current_output}
```

評估結果：
- 綜合評分：{evaluation.overall_score:.2f}
- 問題：{', '.join(evaluation.issues)}
- 建議：{', '.join(evaluation.suggestions)}

請進行反思，格式：
1. 問題分析：具體哪裡出了問題
2. 根本原因：為什麼會出現這個問題
3. 改進策略：下一次迭代應該如何改進"""

    structured_llm = llm.with_structured_output(Reflection)
    reflection = structured_llm.invoke([HumanMessage(content=reflection_prompt)])

    reflection_text = f"""
問題：{reflection.what_went_wrong}
原因：{reflection.root_cause}
策略：{reflection.improvement_strategy}
""".strip()

    print(f"  📋 反思：{reflection.improvement_strategy[:80]}...")

    return {
        "reflections": [reflection_text],
        "iteration": state["iteration"] + 1
    }


# ============================================================
# 5. 路由函數
# ============================================================

def should_continue(state: ReflexionState) -> Literal["refiner", "end"]:
    """‹9› 決定是否繼續迭代"""
    evaluation = state["evaluation"]
    iteration = state["iteration"]
    max_iterations = state["max_iterations"]
    quality_threshold = state["quality_threshold"]

    # 達到品質門檻
    if evaluation.passed and evaluation.overall_score >= quality_threshold:
        print(f"\n✅ 品質達標！評分：{evaluation.overall_score:.2f}")
        return "end"

    # 達到最大迭代次數
    if iteration >= max_iterations:
        print(f"\n⚠️ 達到最大迭代次數 ({max_iterations})")
        return "end"

    # 繼續改進
    print(f"  ➡️ 需要改進，進入反思...")
    return "refiner"


# ============================================================
# 6. 構建圖
# ============================================================

def build_reflexion_graph() -> StateGraph:
    """構建自我修正模式圖"""
    graph = StateGraph(ReflexionState)

    # 添加節點
    graph.add_node("generator", generator_node)
    graph.add_node("evaluator", evaluator_node)
    graph.add_node("refiner", refiner_node)

    # 添加邊
    graph.add_edge(START, "generator")
    graph.add_edge("generator", "evaluator")
    graph.add_conditional_edges(
        "evaluator",
        should_continue,
        {
            "refiner": "refiner",
            "end": END
        }
    )
    graph.add_edge("refiner", "generator")

    return graph.compile()


# ============================================================
# 7. 主程式
# ============================================================

def main():
    """執行自我修正模式範例"""
    print("=" * 60)
    print("Chapter 9: 自我修正模式 (The Reflexion Pattern)")
    print("=" * 60)

    # 構建圖
    app = build_reflexion_graph()

    # 測試任務
    tasks = [
        "寫一個 Python 函數 `parse_date`，可以解析多種日期格式（如 '2024-01-15', 'Jan 15, 2024', '15/01/2024'），返回 datetime 對象",
        "實現一個 `RateLimiter` 類，使用令牌桶算法控制 API 請求頻率，支持每秒最大請求數配置",
    ]

    for i, task in enumerate(tasks, 1):
        print(f"\n{'='*60}")
        print(f"任務 {i}: {task}")
        print("=" * 60)

        initial_state = {
            "messages": [],
            "task": task,
            "task_type": "code",
            "current_output": None,
            "output_history": [],
            "evaluation": None,
            "evaluation_history": [],
            "reflections": [],
            "iteration": 0,
            "max_iterations": 3,
            "quality_threshold": 0.8
        }

        # 執行圖
        result = app.invoke(initial_state)

        print(f"\n{'='*60}")
        print("最終程式碼：")
        print("=" * 60)
        print(result["current_output"])

        print(f"\n📊 迭代統計：")
        print(f"  - 總迭代次數：{result['iteration']}")
        print(f"  - 最終評分：{result['evaluation'].overall_score:.2f}")
        print(f"  - 反思次數：{len(result['reflections'])}")

        if i < len(tasks):
            input("\n按 Enter 繼續下一個任務...")


if __name__ == "__main__":
    main()
