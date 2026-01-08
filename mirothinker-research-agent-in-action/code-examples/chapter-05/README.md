# 第 5 章：工具調用與軌跡收集 - 程式碼範例

> 本目錄包含《深度研究代理人實戰》第 5 章的完整可運行程式碼。

---

## 快速開始

### 1. 建立虛擬環境

```bash
cd code-examples/chapter-05
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 2. 安裝依賴

```bash
pip install -r requirements.txt
```

### 3. 設定環境變數

```bash
cp .env.example .env
# 編輯 .env 檔案，填入你的 API Key
```

### 4. 執行

```bash
# 工具管理系統示範
python tool_manager.py --demo

# 使用工具處理查詢
python tool_manager.py -q "搜尋 Python 異步編程教程"

# 軌跡收集示範
python trajectory_collector.py --demo

# 匯出訓練資料
python trajectory_collector.py --export training_data.jsonl
```

---

## 檔案說明

| 檔案 | 行數 | 說明 |
|------|------|------|
| `tool_manager.py` | ~450 | 工具管理系統完整實現 |
| `trajectory_collector.py` | ~500 | 軌跡收集與獎勵計算 |
| `requirements.txt` | - | Python 依賴清單 |
| `.env.example` | - | 環境變數範例 |
| `README.md` | - | 本文件 |

---

## 核心概念

### 工具定義結構

```
ToolDefinition
├── name: 工具名稱
├── description: 功能描述（供 LLM 理解）
├── parameters: 參數綱要
│   ├── name: 參數名稱
│   ├── type: 資料類型
│   ├── description: 參數說明
│   └── required: 是否必填
├── examples: 使用範例
└── category: 工具類別
```

### 內建工具

| 工具 | 類別 | 功能 |
|------|------|------|
| `web_search` | search | 網頁搜尋 |
| `web_browser` | browsing | 網頁內容擷取 |
| `python_interpreter` | code_execution | Python 程式碼執行 |
| `file_reader` | file_system | 檔案讀取 |

### 軌跡資料結構

```
Trajectory
├── trajectory_id: 軌跡識別碼
├── task_query: 原始任務
├── steps: [TrajectoryStep, ...]
│   ├── step_type: thought | action | observation
│   ├── content: 步驟內容
│   └── timestamp: 時間戳
├── tool_calls: [ToolCall, ...]
├── final_answer: 最終答案
├── success: 是否成功
└── rewards: 獎勵信號
```

### 獎勵信號設計

| 信號 | 權重 | 說明 |
|------|------|------|
| `task_completion` | 0.30 | 任務完成度 |
| `tool_efficiency` | 0.20 | 工具使用效率 |
| `answer_quality` | 0.25 | 答案品質 |
| `factual_accuracy` | 0.15 | 事實準確度 |
| `token_efficiency` | 0.10 | Token 使用效率 |

---

## 使用範例

### 基本工具調用

```python
import asyncio
from tool_manager import ToolManager

async def main():
    manager = ToolManager()

    # 執行搜尋
    result = await manager.execute_tool(
        "web_search",
        query="Python 異步編程",
        num_results=5
    )

    if result.success:
        print(f"搜尋到 {len(result.content)} 個結果")
        print(f"耗時: {result.execution_time:.2f}s")

asyncio.run(main())
```

### 自訂工具

```python
from tool_manager import BaseTool, ToolDefinition, ParameterSchema

class CustomTool(BaseTool):
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="my_custom_tool",
            description="自訂工具描述",
            parameters=[
                ParameterSchema(
                    name="input",
                    type="string",
                    description="輸入內容"
                )
            ]
        )

    async def _execute(self, input: str) -> dict:
        return {"result": f"處理: {input}"}

# 註冊到管理器
manager.registry.register(CustomTool())
```

### 軌跡收集

```python
from trajectory_collector import TrajectoryCollector

collector = TrajectoryCollector()

# 開始軌跡
trajectory = collector.start_trajectory("分析市場趨勢")

# 記錄步驟
trajectory.add_thought("需要搜尋市場數據...")
tool_call = trajectory.add_action("web_search", {"query": "市場趨勢"})
trajectory.add_observation({"results": [...]}, tool_call)

# 完成軌跡
rewards = collector.complete_trajectory(
    trajectory,
    final_answer="市場呈現上升趨勢...",
    success=True
)

print(f"總獎勵: {rewards['total']:.3f}")
```

### 匯出訓練資料

```python
# 匯出高品質軌跡作為訓練資料
count = collector.export_for_training(
    output_path="training_data.jsonl",
    min_reward=0.5,  # 只匯出獎勵 > 0.5 的軌跡
    format="jsonl"
)
print(f"匯出 {count} 條訓練資料")
```

---

## 執行範例

### 工具管理系統示範

```
============================================================
🔧 工具管理系統示範
============================================================

📋 可用工具：
   • web_search: 搜尋網頁獲取資訊。用於查找最新資訊、研究主題或...
   • web_browser: 瀏覽並獲取網頁內容。用於深入閱讀特定網頁...
   • python_interpreter: 執行 Python 程式碼。用於數據分析...
   • file_reader: 讀取本地檔案內容。用於分析程式碼...

============================================================
📍 測試工具調用
============================================================

1️⃣ 網頁搜尋工具
   結果類型: success
   執行時間: 0.51s
   結果數量: 3

2️⃣ Python 執行器
   結果類型: success
   輸出: Hello from MiroThinker!
         5050

============================================================
📊 使用統計
============================================================
   總調用次數: 2
   成功率: 100.0%
   總執行時間: 0.53s
```

### 軌跡收集示範

```
============================================================
📊 軌跡收集系統示範
============================================================

📝 開始記錄軌跡: 分析 2024 年全球 AI 晶片市場...

🔄 模擬 ReAct 循環...
   💭 添加思考步驟
   🔧 添加行動步驟: web_search
   👁️ 添加觀察步驟
   💭 添加思考步驟
   🔧 添加行動步驟: web_browser
   👁️ 添加觀察步驟

✅ 軌跡完成

============================================================
📈 獎勵信號
============================================================
   task_completion     : 1.000 ████████████████████
   tool_efficiency     : 0.700 ██████████████
   answer_quality      : 0.850 █████████████████
   factual_accuracy    : 0.500 ██████████
   token_efficiency    : 0.800 ████████████████
   total               : 0.790 ███████████████

📤 已匯出 1 條訓練資料到 ./demo_trajectories/training_data.jsonl
```

---

## 進階功能

### 工具調用統計

```python
stats = manager.get_statistics()
print(f"總調用: {stats['total_calls']}")
print(f"成功率: {stats['success_rate']*100:.1f}%")

for tool, data in stats['tools'].items():
    print(f"  {tool}: {data['calls']} 次")
```

### 軌跡過濾

```python
# 過濾高品質軌跡
high_quality = collector.filter_trajectories(
    min_reward=0.7,
    success_only=True,
    min_tools=2
)
print(f"找到 {len(high_quality)} 條高品質軌跡")
```

### 軌跡回放

```python
from trajectory_collector import TrajectoryReplayer

replayer = TrajectoryReplayer()
replayer.replay(trajectory, delay=0.5)
```

---

## RLEF 訓練資料格式

匯出的訓練資料採用 JSONL 格式：

```json
{
  "id": "traj_20260108_123456_abc12345",
  "query": "分析 2024 年全球 AI 晶片市場...",
  "trajectory": [
    {"step_type": "thought", "content": "...", "timestamp": 1704700000},
    {"step_type": "action", "content": {"tool_name": "web_search", ...}},
    {"step_type": "observation", "content": {...}}
  ],
  "answer": "2024 年全球 AI 晶片市場...",
  "reward": 0.79,
  "reward_breakdown": {
    "task_completion": 1.0,
    "tool_efficiency": 0.7,
    "answer_quality": 0.85,
    "factual_accuracy": 0.5,
    "token_efficiency": 0.8
  },
  "metadata": {
    "duration": 12.5,
    "tool_count": 2,
    "step_count": 6,
    "success": true
  }
}
```

---

## 常見問題

### Q: 如何添加真實的搜尋 API？

替換 `WebSearchTool._execute` 方法，使用 Serper 或 Tavily API：

```python
async def _execute(self, query: str, num_results: int = 5, **kwargs):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://api.serper.dev/search",
            headers={"X-API-KEY": os.getenv("SERPER_API_KEY")},
            json={"q": query, "num": num_results}
        ) as resp:
            data = await resp.json()
            return data.get("organic", [])
```

### Q: 軌跡儲存過多怎麼辦？

設定自動清理：

```python
collector = TrajectoryCollector(
    storage_path="./trajectories",
    auto_save=True
)

# 清理 30 天前的軌跡
import glob
import os
import time

for f in glob.glob("./trajectories/*.json"):
    if os.path.getmtime(f) < time.time() - 30*24*3600:
        os.remove(f)
```

### Q: 如何自訂獎勵權重？

```python
from trajectory_collector import RewardCalculator

calculator = RewardCalculator(weights={
    "task_completion": 0.40,  # 提高完成度權重
    "tool_efficiency": 0.15,
    "answer_quality": 0.30,
    "factual_accuracy": 0.10,
    "token_efficiency": 0.05
})

collector.reward_calculator = calculator
```

---

## 延伸閱讀

- [第 4 章程式碼](../chapter-04/) - 核心調度器設計
- [第 6 章程式碼](../chapter-06/) - 長短時記憶管理（待完成）
- [OpenAI Function Calling 文檔](https://platform.openai.com/docs/guides/function-calling)
- [RLHF/RLEF 訓練方法](https://arxiv.org/abs/2203.02155)

---

**本章程式碼授權**：MIT License
