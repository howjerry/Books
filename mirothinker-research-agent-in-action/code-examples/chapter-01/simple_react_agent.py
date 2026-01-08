"""
simple_react_agent.py

一個簡單但完整的 ReAct 代理人實現。
展示 Thought-Action-Observation 循環的核心機制。

來源：《深度研究代理人實戰》第 1 章
授權：MIT License
"""

import os
import json
import httpx
from openai import OpenAI
from dotenv import load_dotenv
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime

# 載入環境變數
load_dotenv()


# ============================================================
# 資料結構定義
# ============================================================

@dataclass
class Tool:
    """工具定義"""
    name: str
    description: str
    parameters: dict


@dataclass
class ToolCall:
    """工具調用記錄"""
    tool_name: str
    arguments: dict
    result: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class AgentTrace:
    """代理人執行軌跡"""
    question: str
    iterations: list = field(default_factory=list)
    final_answer: Optional[str] = None
    total_time: float = 0.0


# ============================================================
# 搜尋工具實現
# ============================================================

class SearchTool:
    """
    網路搜尋工具
    使用 Serper API 進行 Google 搜尋
    """

    def __init__(self):
        self.api_key = os.getenv("SERPER_API_KEY")
        self.base_url = "https://google.serper.dev/search"

        if not self.api_key:
            print("⚠️ 警告：未設定 SERPER_API_KEY，搜尋功能將使用模擬模式")

    def search(self, query: str, num_results: int = 5) -> str:
        """
        執行搜尋並返回格式化的結果

        Args:
            query: 搜尋關鍵字
            num_results: 返回結果數量

        Returns:
            格式化的搜尋結果字串
        """
        # 如果沒有 API Key，使用模擬模式
        if not self.api_key:
            return self._mock_search(query)

        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "q": query,
            "num": num_results
        }

        try:
            response = httpx.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()

            # 格式化搜尋結果
            results = []
            for item in data.get("organic", [])[:num_results]:
                results.append(
                    f"標題: {item.get('title', 'N/A')}\n"
                    f"連結: {item.get('link', 'N/A')}\n"
                    f"摘要: {item.get('snippet', 'N/A')}\n"
                )

            if results:
                return "\n---\n".join(results)
            else:
                return "未找到相關結果"

        except httpx.TimeoutException:
            return "搜尋逾時，請稍後再試"
        except httpx.HTTPStatusError as e:
            return f"搜尋服務錯誤: HTTP {e.response.status_code}"
        except Exception as e:
            return f"搜尋錯誤: {str(e)}"

    def _mock_search(self, query: str) -> str:
        """模擬搜尋結果（用於測試）"""
        return f"""標題: 模擬搜尋結果 - {query}
連結: https://example.com/search?q={query.replace(' ', '+')}
摘要: 這是一個模擬的搜尋結果。在實際使用中，請設定 SERPER_API_KEY 環境變數來啟用真實搜尋功能。您搜尋的關鍵字是：{query}

---

標題: 相關資訊 - {query}
連結: https://example.com/related
摘要: 這是另一個模擬結果。模擬模式可以用來測試代理人的基本流程，但無法獲取真實的網路資訊。"""


# ============================================================
# ReAct 代理人核心類別
# ============================================================

class SimpleReActAgent:
    """
    簡單的 ReAct 代理人

    實現 Thought-Action-Observation 循環
    """

    def __init__(self, model: str = "gpt-4o-mini", verbose: bool = True):
        """
        初始化代理人

        Args:
            model: 使用的 OpenAI 模型
            verbose: 是否輸出詳細執行過程
        """
        self.client = OpenAI()
        self.model = model
        self.verbose = verbose
        self.search_tool = SearchTool()
        self.max_iterations = 10  # 防止無限循環

        # 系統提示詞：教導模型如何扮演 ReAct 代理人
        self.system_prompt = """你是一個使用 ReAct（Reasoning and Acting）模式的研究助理代理人。

你的工作方式如下：
1. 收到問題後，先思考（Thought）需要什麼資訊
2. 如果需要外部資訊，使用工具（Action）獲取
3. 觀察（Observation）工具返回的結果
4. 重複上述過程，直到能夠回答問題

## 可用工具

### search
- 功能：搜尋網路獲取最新資訊
- 使用方式：Action: search[搜尋關鍵字]
- 範例：Action: search[2024 年諾貝爾物理學獎得主]

## 回應格式

請嚴格按照以下格式回應：

如果需要搜尋：
```
Thought: [你的思考過程，為什麼需要搜尋，搜尋什麼]
Action: search[搜尋關鍵字]
```

如果已經可以回答：
```
Thought: [你的最終思考，為什麼可以回答了]
Answer: [你的最終答案]
```

## 重要原則

1. 每次只執行一個 Action
2. 如果資訊不足，不要猜測，繼續搜尋
3. 如果搜尋結果矛盾，嘗試更多搜尋來交叉驗證
4. 最終答案要基於搜尋結果，並說明資訊來源
5. 如果無法找到可靠資訊，誠實說明
6. 使用繁體中文回答
"""

    def _log(self, message: str):
        """條件性輸出日誌"""
        if self.verbose:
            print(message)

    def _parse_response(self, response: str) -> tuple[str, Optional[str], Optional[str]]:
        """
        解析模型回應，提取 Thought、Action 或 Answer

        Returns:
            (thought, action, answer) 元組
        """
        thought = ""
        action = None
        answer = None

        lines = response.strip().split("\n")

        for line in lines:
            line = line.strip()
            if line.startswith("Thought:"):
                thought = line[8:].strip()
            elif line.startswith("Action:"):
                action = line[7:].strip()
            elif line.startswith("Answer:"):
                # Answer 可能是多行的
                answer_start = response.find("Answer:")
                if answer_start != -1:
                    answer = response[answer_start + 7:].strip()

        return thought, action, answer

    def _execute_action(self, action: str) -> str:
        """
        執行工具調用

        Args:
            action: 工具調用字串，格式如 "search[關鍵字]"

        Returns:
            工具執行結果
        """
        if action.startswith("search[") and action.endswith("]"):
            query = action[7:-1]
            self._log(f"    🔍 執行搜尋: {query}")
            result = self.search_tool.search(query)
            return result
        else:
            return f"未知的工具或格式錯誤: {action}"

    def run(self, question: str) -> str:
        """
        執行 ReAct 循環

        Args:
            question: 使用者問題

        Returns:
            最終答案
        """
        start_time = datetime.now()

        self._log(f"\n{'='*60}")
        self._log(f"📝 問題: {question}")
        self._log(f"{'='*60}\n")

        # 初始化對話歷史
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"問題: {question}"}
        ]

        # 建立執行軌跡
        trace = AgentTrace(question=question)

        iteration = 0

        while iteration < self.max_iterations:
            iteration += 1
            self._log(f"🔄 第 {iteration} 輪迭代")

            # 調用 LLM
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.1,  # 低溫度提高一致性
                    max_tokens=1000
                )
            except Exception as e:
                self._log(f"❌ LLM 調用錯誤: {e}")
                return f"抱歉，發生錯誤: {str(e)}"

            assistant_message = response.choices[0].message.content
            messages.append({"role": "assistant", "content": assistant_message})

            # 解析回應
            thought, action, answer = self._parse_response(assistant_message)

            # 記錄迭代
            trace.iterations.append({
                "iteration": iteration,
                "thought": thought,
                "action": action,
                "answer": answer
            })

            self._log(f"   💭 Thought: {thought}")

            # 如果有最終答案，結束循環
            if answer:
                trace.final_answer = answer
                trace.total_time = (datetime.now() - start_time).total_seconds()

                self._log(f"\n{'='*60}")
                self._log(f"✅ 最終答案:")
                self._log(f"{answer}")
                self._log(f"{'='*60}")
                self._log(f"⏱️ 總耗時: {trace.total_time:.2f} 秒")
                self._log(f"🔄 迭代次數: {iteration}")

                return answer

            # 如果有行動，執行並添加觀察結果
            if action:
                observation = self._execute_action(action)

                # 記錄觀察結果
                trace.iterations[-1]["observation"] = observation

                # 將觀察結果添加到對話歷史
                observation_message = f"Observation: {observation}"
                messages.append({"role": "user", "content": observation_message})

                # 顯示截斷的觀察結果
                display_obs = observation[:200] + "..." if len(observation) > 200 else observation
                self._log(f"   👁 Observation: {display_obs}")
                self._log()
            else:
                # 既沒有答案也沒有行動，可能是格式問題
                self._log(f"   ⚠️ 無法解析行動，原始回應:")
                self._log(f"   {assistant_message[:200]}...")

                # 提示模型重新格式化
                messages.append({
                    "role": "user",
                    "content": "請按照指定格式回應。如果需要搜尋，使用 'Action: search[關鍵字]'；如果可以回答，使用 'Answer: 你的答案'。"
                })

        # 超過最大迭代次數
        trace.total_time = (datetime.now() - start_time).total_seconds()
        self._log(f"\n⚠️ 已達到最大迭代次數 ({self.max_iterations})")

        return "抱歉，經過多次嘗試仍無法找到滿意的答案。請嘗試重新表述問題。"

    def run_batch(self, questions: list[str]) -> list[str]:
        """
        批次執行多個問題

        Args:
            questions: 問題列表

        Returns:
            答案列表
        """
        answers = []
        for i, q in enumerate(questions, 1):
            self._log(f"\n{'#'*60}")
            self._log(f"# 問題 {i}/{len(questions)}")
            self._log(f"{'#'*60}")
            answer = self.run(q)
            answers.append(answer)
        return answers


# ============================================================
# 互動式介面
# ============================================================

def interactive_mode():
    """啟動互動式對話模式"""
    print("\n" + "="*60)
    print("🤖 簡單 ReAct 代理人 - 互動模式")
    print("="*60)
    print("輸入問題讓代理人幫你搜尋答案")
    print("輸入 'quit' 或 'exit' 退出")
    print("="*60 + "\n")

    agent = SimpleReActAgent()

    while True:
        try:
            question = input("\n❓ 你的問題: ").strip()

            if question.lower() in ['quit', 'exit', 'q']:
                print("\n👋 再見！")
                break

            if not question:
                print("請輸入問題")
                continue

            agent.run(question)

        except KeyboardInterrupt:
            print("\n\n👋 再見！")
            break
        except Exception as e:
            print(f"\n❌ 發生錯誤: {e}")


# ============================================================
# 主程式入口
# ============================================================

def main():
    """
    主程式：展示代理人的使用方式
    """
    # 檢查環境變數
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ 錯誤：請設定 OPENAI_API_KEY 環境變數")
        print("可以在 .env 檔案中設定，或直接設定環境變數")
        return

    agent = SimpleReActAgent()

    # 測試問題
    test_question = "2024 年諾貝爾物理學獎得主是誰？他們的主要貢獻是什麼？"

    print("\n" + "="*60)
    print("🤖 簡單 ReAct 代理人示範")
    print("="*60)

    answer = agent.run(test_question)

    print("\n" + "-"*60)
    print("📊 執行完成")
    print("-"*60)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "-i":
        interactive_mode()
    else:
        main()
