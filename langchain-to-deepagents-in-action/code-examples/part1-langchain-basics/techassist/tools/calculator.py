"""計算器工具"""

import math
from langchain_core.tools import tool
from pydantic import BaseModel, Field


class CalculatorInput(BaseModel):
    """計算器參數"""
    expression: str = Field(
        description="數學表達式，支援 +, -, *, /, **, sqrt(), sin(), cos(), log(), pi, e"
    )


# 安全的數學環境
SAFE_MATH_ENV = {
    # 基本函數
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sum": sum,
    "pow": pow,
    # math 模組函數
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "log": math.log,
    "log10": math.log10,
    "log2": math.log2,
    "exp": math.exp,
    "floor": math.floor,
    "ceil": math.ceil,
    "factorial": math.factorial,
    # 常數
    "pi": math.pi,
    "e": math.e,
    "inf": math.inf,
}


@tool(args_schema=CalculatorInput)
def calculator(expression: str) -> str:
    """計算數學表達式。

    用於需要精確數值計算的場景，例如：
    - 複雜的數學運算
    - 單位轉換
    - 統計計算
    - 科學計算

    支援的運算符：+, -, *, /, ** (次方), // (整除), % (取餘)
    支援的函數：sqrt, sin, cos, tan, log, log10, exp, floor, ceil, factorial
    支援的常數：pi, e

    範例：
    - "2 + 3 * 4" -> 14
    - "sqrt(16) + pi" -> 7.14...
    - "log(e)" -> 1.0

    Returns:
        計算結果或錯誤訊息
    """
    try:
        # 移除危險的內建函數，只保留安全的數學環境
        result = eval(expression, {"__builtins__": {}}, SAFE_MATH_ENV)

        # 處理特殊值
        if math.isinf(result):
            return "計算結果：無限大 (∞)"
        if math.isnan(result):
            return "計算結果：非數值 (NaN)"

        # 格式化輸出
        if isinstance(result, float):
            # 如果是整數結果，移除小數點
            if result.is_integer():
                return f"計算結果：{int(result)}"
            # 保留合理的小數位數
            return f"計算結果：{result:.10g}"

        return f"計算結果：{result}"

    except ZeroDivisionError:
        return "錯誤：除以零"
    except ValueError as e:
        return f"錯誤：數值無效 - {e}"
    except SyntaxError:
        return "錯誤：表達式語法錯誤，請檢查括號和運算符"
    except NameError as e:
        return f"錯誤：未知的函數或變數 - {e}"
    except TypeError as e:
        return f"錯誤：類型錯誤 - {e}"
    except Exception as e:
        return f"計算錯誤：{e}"
