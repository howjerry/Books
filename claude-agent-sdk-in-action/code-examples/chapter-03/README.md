# 第 3 章：情境工程 - 建立長期記憶的知識管理 Agent

## 專案說明

這是《Claude Agent SDK 打造企業 Agent》第 3 章的完整可運行程式碼範例。

本專案展示如何建立一個具有「長期記憶」的 AI Agent，能夠記住專案知識、回答新成員的問題、追蹤決策脈絡。

## 功能特色

✅ **CLAUDE.md 解析器**
- 解析 Markdown 結構
- 提取專案概覽、ADRs、FAQ
- 全文搜尋功能

✅ **知識管理 Agent**
- 回答關於專案的問題
- 引用具體文件章節
- 提供架構決策背景

✅ **情境持久化**
- 儲存對話歷史
- 多使用者支援
- 跨 Session 保持情境

✅ **友善的介面**
- Rich 終端介面
- Markdown 格式化輸出
- 來源引用顯示

## 快速開始

### 1. 安裝依賴

```bash
# 建立虛擬環境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安裝套件
pip install -r requirements.txt
```

### 2. 設定環境變數

```bash
# 複製範例檔案
cp .env.example .env

# 編輯 .env 並填入你的 API 金鑰
# ANTHROPIC_API_KEY=your_api_key_here
```

### 3. 建立知識庫

```bash
# 複製範例 CLAUDE.md 並自訂內容
cp CLAUDE.md.example CLAUDE.md

# 編輯 CLAUDE.md，填入你的專案資訊
```

### 4. 執行 Agent

```bash
python main.py
```

## 專案結構

```
chapter-03/
├── main.py                      # 主程式
├── knowledge_agent.py           # 知識管理 Agent
├── requirements.txt             # Python 依賴
├── .env.example                 # 環境變數範例
├── CLAUDE.md.example            # CLAUDE.md 範本
├── tools/                       # 工具模組
│   ├── claude_md_parser.py      # CLAUDE.md 解析器
│   └── context_manager.py       # 情境管理器
└── contexts/                    # 對話歷史儲存（執行後產生）
```

## 使用方式

### 基本對話

```
你: 專案使用什麼資料庫？

Agent: 專案使用 PostgreSQL 14 作為主要資料庫...
```

### 查詢決策背景

```
你: 為什麼選擇 FastAPI？

Agent: 根據 ADR-001（2024-01-15 的架構決策）...
```

### 取得重要提醒

```
你: 有哪些事情千萬不能做？

Agent: ⚠️ 以下是絕對不能做的事情：
1. 不要直接修改 `legacy-auth.py`...
```

### 命令

- **exit**: 離開程式
- **clear**: 清除對話歷史

## 自訂 CLAUDE.md

CLAUDE.md 是 Agent 的「長期記憶」，包含以下區塊：

### 必要區塊

1. **專案概覽**
```markdown
## 📋 專案概覽
- **專案名稱**: [你的專案名稱]
- **專案類型**: [專案類型]
- **技術棧**: [使用的技術]
```

2. **架構決策記錄 (ADRs)**
```markdown
## 🏗️ 架構決策記錄 (ADRs)

### ADR-001: [決策標題]
**日期**: YYYY-MM-DD
**決策**: [簡短描述]
**原因**:
- [原因 1]
- [原因 2]
```

3. **重要提醒**
```markdown
## ⚠️ 重要提醒

### 千萬不要做
- ❌ [禁止的操作]

### 最佳實踐
- ✅ [推薦的做法]
```

### 可選區塊

- 當前工作情境
- 專案結構
- 開發環境設定
- 知識庫
- 變更記錄
- 相關資源

## 進階功能

### 多使用者支援

每個使用者的對話歷史獨立儲存：

```python
# 修改 main.py 中的 user_id
user_id = "alice"  # 或 "bob", "charlie" 等
```

### 情境管理

```python
from knowledge_agent import KnowledgeAgent

agent = KnowledgeAgent()

# 使用持久化情境
result = agent.chat_with_context("user_001", "你的問題")

# 清除特定使用者的情境
agent.context_manager.clear_context("user_001")

# 列出所有使用者
users = agent.context_manager.list_users()
```

## 效能指標

- **新成員上手時間**: 2 週 → 30 分鐘（98% 時間節省）
- **查詢決策原因**: 2 小時 → 30 秒（99% 時間節省）
- **API 成本**: ~$0.023 / 對話
- **每月成本**（50 queries）: ~$1.15

## 學習目標

完成本章後，你將掌握：

✅ 理解三種記憶類型（短期、工作、長期）
✅ 設計並建立 CLAUDE.md 知識庫
✅ 實作 CLAUDE.md 解析器
✅ 建構知識管理 Agent
✅ 實現多 Session 情境管理
✅ 對話歷史的持久化

## 常見問題

### Q: 找不到 CLAUDE.md？
**A**: 複製 `CLAUDE.md.example` 為 `CLAUDE.md` 並自訂內容。

### Q: Agent 回答不準確？
**A**: 檢查 CLAUDE.md 是否包含相關資訊，使用清晰的結構和關鍵字。

### Q: 如何整合到現有專案？
**A**: 在專案根目錄建立 `CLAUDE.md`，記錄專案知識，然後使用 `KnowledgeAgent` 讀取。

### Q: 對話歷史儲存在哪裡？
**A**: `contexts/` 目錄，每個使用者一個 JSON 檔案。

## 相關章節

- 第 1 章：建構你的第一個 Claude Agent - 智慧客服助理
- 第 2 章：賦予 Agent 執行能力 - 自動化報表生成系統
- 第 4 章：你的第一個 Subagent - 大規模程式碼重構系統

## 擴展建議

1. **整合向量資料庫**（Pinecone, Weaviate）實現語義搜尋
2. **自動更新 CLAUDE.md**（Git hook 監聽變更）
3. **Web 介面**（使用 Streamlit 或 Gradio）
4. **多語言支援**（英文、中文知識庫）
5. **權限管理**（不同角色看到不同資訊）

## 授權

本程式碼為教學用途，版權所有。

---

**最後更新**: 2025-11-08
