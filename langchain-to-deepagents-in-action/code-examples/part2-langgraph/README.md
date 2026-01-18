# TechAssist - Part 2 程式碼範例

本目錄包含《LangChain 到 DeepAgents 實戰》Part 2（Chapter 4-6）的程式碼範例。

## 專案結構

```
part2-langgraph/
├── requirements.txt           # 依賴套件
├── react_agent.py            # ReAct Agent 範例 (Ch4)
├── approval_workflow.py      # 審批工作流範例 (Ch5)
├── multi_agent_system.py     # 多 Agent 系統範例 (Ch6)
└── techassist_v5/            # TechAssist v0.5-v0.7
    ├── __init__.py
    ├── state.py              # 狀態定義
    ├── nodes.py              # 節點實現
    ├── graph.py              # Graph 組裝
    └── cli.py                # CLI 介面
```

## 快速開始

### 1. 安裝依賴

```bash
pip install -r requirements.txt
```

### 2. 設定環境變數

```bash
export ANTHROPIC_API_KEY=your-api-key
```

### 3. 執行範例

```bash
# ReAct Agent (Chapter 4)
python react_agent.py

# 審批工作流 (Chapter 5)
python approval_workflow.py

# 多 Agent 系統 (Chapter 6)
python multi_agent_system.py
```

## 版本說明

### v0.5 - LangGraph 基礎 (Chapter 4)

- StateGraph 狀態管理
- 節點與邊的定義
- ReAct Agent 模式

### v0.6 - 人機協作 (Chapter 5)

- Checkpointer 狀態持久化
- 中斷與恢復機制
- Human-in-the-Loop 流程

### v0.7 - 多 Agent 協作 (Chapter 6)

- Supervisor Pattern
- 專業化 Worker Agents
- 任務分配與結果整合

## 核心概念

### State（狀態）

```python
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    phase: str
```

### Node（節點）

```python
def my_node(state: AgentState) -> dict:
    # 處理邏輯
    return {"phase": "next"}
```

### Edge（邊）

```python
graph.add_edge("node_a", "node_b")
graph.add_conditional_edges("node_a", router_func, {...})
```

## 相關章節

- Chapter 4: 狀態機思維——StateGraph 基礎
- Chapter 5: 路由模式與人機協作 (HITL)
- Chapter 6: 多智能體協作——Supervisor 模式
