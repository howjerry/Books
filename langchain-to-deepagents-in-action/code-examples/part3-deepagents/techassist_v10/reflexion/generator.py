"""
TechAssist v1.0 - Generator 組件

生成初始輸出或改進後的輸出
"""

import re
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage

from ..config import config
from ..state import TechAssistState


GENERATOR_SYSTEM_PROMPT = """你是 TechAssist，一個專業的企業技術助理。

請根據任務要求生成高品質的輸出。要求：
1. 內容準確且完整
2. 格式清晰易讀
3. 如果是程式碼，確保可運行
4. 考慮邊界情況和錯誤處理"""

REFINEMENT_SYSTEM_PROMPT = """你是 TechAssist，正在改進之前的輸出。

請根據反思和建議改進輸出，重點關注：
1. 解決之前識別的問題
2. 提升整體品質
3. 確保改進後的輸出更加完善"""


def generate_output(state: TechAssistState) -> dict:
    """生成或改進輸出"""
    task = state["task"]
    iteration = state["iteration"]
    reflections = state.get("reflections", [])
    current_output = state.get("current_output")
    context = state.get("injected_context", "")

    llm = ChatAnthropic(
        model=config.primary_model,
        temperature=config.temperature
    )

    if iteration == 0:
        # 首次生成
        messages = [SystemMessage(content=GENERATOR_SYSTEM_PROMPT)]

        if context:
            messages.append(SystemMessage(content=f"相關上下文：\n{context}"))

        messages.append(HumanMessage(content=f"任務：{task}"))

    else:
        # 基於反思改進
        messages = [SystemMessage(content=REFINEMENT_SYSTEM_PROMPT)]

        reflection_text = "\n".join([
            f"反思 {i+1}: {r}"
            for i, r in enumerate(reflections[-3:])
        ])

        messages.append(HumanMessage(content=f"""
任務：{task}

之前的輸出：
{current_output}

反思與改進建議：
{reflection_text}

請生成改進後的輸出：
"""))

    response = llm.invoke(messages)
    output = response.content

    # 如果是程式碼任務，提取程式碼塊
    if state.get("task_type") == "code":
        code_match = re.search(r'```(?:python)?\n(.*?)\n```', output, re.DOTALL)
        if code_match:
            output = code_match.group(1)

    return {
        "current_output": output,
        "phase": "evaluate"
    }
