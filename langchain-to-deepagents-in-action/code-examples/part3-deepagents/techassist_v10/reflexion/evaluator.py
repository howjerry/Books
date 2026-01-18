"""
TechAssist v1.0 - Evaluator 組件

評估輸出品質
"""

import re
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

from ..config import config
from ..state import QualityDimension, EvaluationResult, TechAssistState


class OutputEvaluator:
    """通用輸出評估器"""

    def __init__(self):
        self.llm = ChatAnthropic(
            model=config.primary_model,
            temperature=0
        )

    def evaluate(
        self,
        output: str,
        task: str,
        task_type: str
    ) -> EvaluationResult:
        """評估輸出品質"""
        if task_type == "code":
            return self._evaluate_code(output, task)
        else:
            return self._evaluate_text(output, task)

    def _evaluate_code(self, code: str, task: str) -> EvaluationResult:
        """評估程式碼品質"""
        dimensions = []

        # 語法檢查
        syntax_score, syntax_feedback = self._check_python_syntax(code)
        dimensions.append(QualityDimension(
            name="語法正確性",
            score=syntax_score,
            feedback=syntax_feedback
        ))

        # 功能完整性（LLM 評估）
        completeness = self._llm_evaluate_dimension(
            code, task,
            "功能完整性",
            "評估程式碼是否完整實現了任務要求的所有功能"
        )
        dimensions.append(completeness)

        # 程式碼品質
        quality = self._check_code_quality(code)
        dimensions.append(quality)

        # 計算綜合評分
        weights = [0.3, 0.5, 0.2]
        overall = sum(d.score * w for d, w in zip(dimensions, weights))

        issues = [d.feedback for d in dimensions if d.score < 0.7]
        suggestions = [f"改進 {d.name}" for d in dimensions if d.score < 0.9]

        return EvaluationResult(
            overall_score=overall,
            dimensions=dimensions,
            issues=issues,
            suggestions=suggestions,
            passed=overall >= config.quality_threshold
        )

    def _evaluate_text(self, text: str, task: str) -> EvaluationResult:
        """評估文本品質"""
        dimensions = []

        # 相關性
        relevance = self._llm_evaluate_dimension(
            text, task,
            "相關性",
            "評估回答是否切題並解答了用戶的問題"
        )
        dimensions.append(relevance)

        # 完整性
        completeness = self._llm_evaluate_dimension(
            text, task,
            "完整性",
            "評估回答是否涵蓋了問題的所有方面"
        )
        dimensions.append(completeness)

        # 清晰度
        clarity = self._llm_evaluate_dimension(
            text, task,
            "清晰度",
            "評估回答是否清晰易懂"
        )
        dimensions.append(clarity)

        overall = sum(d.score for d in dimensions) / len(dimensions)

        issues = [d.feedback for d in dimensions if d.score < 0.7]
        suggestions = [f"改進 {d.name}" for d in dimensions if d.score < 0.9]

        return EvaluationResult(
            overall_score=overall,
            dimensions=dimensions,
            issues=issues,
            suggestions=suggestions,
            passed=overall >= config.quality_threshold
        )

    def _check_python_syntax(self, code: str) -> tuple[float, str]:
        """檢查 Python 語法"""
        try:
            compile(code, "<string>", "exec")
            return 1.0, "語法正確"
        except SyntaxError as e:
            return 0.0, f"語法錯誤：{e.msg}"

    def _check_code_quality(self, code: str) -> QualityDimension:
        """檢查程式碼品質"""
        issues = []

        # 行長度
        long_lines = sum(1 for line in code.split("\n") if len(line) > 100)
        if long_lines > 3:
            issues.append("多行過長")

        # 文檔
        if "def " in code and '"""' not in code:
            issues.append("缺少文檔字串")

        # 錯誤處理
        if "def " in code and "try" not in code:
            issues.append("可考慮添加錯誤處理")

        score = max(0, 1 - len(issues) * 0.2)

        return QualityDimension(
            name="程式碼品質",
            score=score,
            feedback="；".join(issues) if issues else "品質良好"
        )

    def _llm_evaluate_dimension(
        self,
        content: str,
        task: str,
        dimension_name: str,
        criteria: str
    ) -> QualityDimension:
        """使用 LLM 評估特定維度"""
        prompt = f"""請評估以下內容的 {dimension_name}。

任務：{task}

內容：
{content[:2000]}

評估標準：{criteria}

請以「分數|評語」格式回答（分數 0-1，如：0.85|內容完整但可以更詳細）"""

        response = self.llm.invoke([HumanMessage(content=prompt)])

        try:
            parts = response.content.strip().split("|")
            score = float(parts[0])
            feedback = parts[1] if len(parts) > 1 else "評估完成"
        except (ValueError, IndexError):
            score = 0.7
            feedback = response.content[:100]

        return QualityDimension(
            name=dimension_name,
            score=min(max(score, 0), 1),
            feedback=feedback
        )


# 全局評估器實例
evaluator = OutputEvaluator()


def evaluate_output(state: TechAssistState) -> dict:
    """評估節點：評估當前輸出的品質"""
    output = state["current_output"]
    task = state["task"]
    task_type = state.get("task_type", "text")

    evaluation = evaluator.evaluate(output, task, task_type)

    return {
        "evaluation": evaluation,
        "phase": "refine" if not evaluation.passed else "respond"
    }
