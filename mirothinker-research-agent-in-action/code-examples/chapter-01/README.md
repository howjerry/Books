# 第 1 章：從 LLM 到自主代理人 - 程式碼範例

> 本目錄包含《深度研究代理人實戰》第 1 章的完整可運行程式碼。

---

## 快速開始

### 1. 建立虛擬環境

```bash
cd code-examples/chapter-01
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
# 執行示範
python simple_react_agent.py

# 或啟動互動模式
python simple_react_agent.py -i
```

---

## 檔案說明

| 檔案 | 說明 |
|------|------|
| `simple_react_agent.py` | 完整的 ReAct 代理人實現（~300 行） |
| `requirements.txt` | Python 依賴清單 |
| `.env.example` | 環境變數範例 |
| `README.md` | 本文件 |

---

## 核心功能

### SimpleReActAgent 類別

```python
from simple_react_agent import SimpleReActAgent

# 建立代理人
agent = SimpleReActAgent(
    model="gpt-4o-mini",  # 可選：gpt-4o, gpt-4-turbo
    verbose=True          # 是否輸出執行過程
)

# 單一問題
answer = agent.run("2024 年諾貝爾物理學獎得主是誰？")

# 批次問題
answers = agent.run_batch([
    "今天台北天氣如何？",
    "SpaceX 最近一次發射是什麼時候？"
])
```

### 執行模式

**示範模式**（預設）：
```bash
python simple_react_agent.py
```

**互動模式**：
```bash
python simple_react_agent.py -i
```

---

## API Key 獲取

### OpenAI API Key（必要）

1. 前往 https://platform.openai.com/api-keys
2. 登入或註冊帳號
3. 點擊「Create new secret key」
4. 複製 Key 到 `.env` 檔案

### Serper API Key（選用）

1. 前往 https://serper.dev/
2. 註冊帳號（有免費額度）
3. 在 Dashboard 中找到 API Key
4. 複製 Key 到 `.env` 檔案

> 如果不設定 Serper API Key，代理人將使用模擬搜尋模式，可用於測試基本流程。

---

## 執行範例

```
============================================================
📝 問題: 2024 年諾貝爾物理學獎得主是誰？他們的主要貢獻是什麼？
============================================================

🔄 第 1 輪迭代
   💭 Thought: 這是一個關於 2024 年諾貝爾獎的問題，我需要搜尋最新資訊。
    🔍 執行搜尋: 2024 年諾貝爾物理學獎得主
   👁 Observation: 標題: 2024年諾貝爾物理學獎揭曉...

🔄 第 2 輪迭代
   💭 Thought: 已找到得主資訊，現在需要更多關於他們貢獻的細節。
    🔍 執行搜尋: Hopfield Hinton 神經網路 貢獻
   👁 Observation: ...

🔄 第 3 輪迭代
   💭 Thought: 我現在有足夠的資訊來回答這個問題了。

============================================================
✅ 最終答案:
2024 年諾貝爾物理學獎由 John Hopfield 和 Geoffrey Hinton 共同獲得...
============================================================
⏱️ 總耗時: 12.34 秒
🔄 迭代次數: 3
```

---

## 進階挑戰

完成基本範例後，試著：

1. **添加計算器工具**：讓代理人能做數學運算
2. **改進錯誤處理**：更優雅地處理 API 失敗
3. **增加記憶功能**：讓代理人記住之前的對話
4. **交叉驗證**：搜尋多次並比對結果

---

## 常見問題

### Q: 出現 "OPENAI_API_KEY not set" 錯誤

確保你已經：
1. 複製 `.env.example` 為 `.env`
2. 在 `.env` 中填入有效的 API Key

### Q: 搜尋結果顯示「模擬模式」

這表示你沒有設定 `SERPER_API_KEY`。程式會使用模擬搜尋結果，可用於測試流程，但無法獲取真實資訊。

### Q: 代理人陷入循環

這通常發生在問題過於複雜或模糊時。試著：
- 讓問題更具體
- 增加 `max_iterations` 限制
- 檢查系統提示詞

---

## 延伸閱讀

- [ReAct 原論文](https://arxiv.org/abs/2210.03629)
- [OpenAI API 文件](https://platform.openai.com/docs)
- [Serper API 文件](https://serper.dev/docs)

---

**本章程式碼授權**：MIT License
