# TechAssist - Part 1 程式碼範例

本目錄包含《LangChain 到 DeepAgents 實戰》Part 1（Chapter 1-3）的完整可運行程式碼。

## 專案結構

```
part1-langchain-basics/
├── main.py                 # 主程式入口
├── requirements.txt        # 依賴套件
├── .env.example           # 環境變數範本
└── techassist/
    ├── __init__.py
    ├── config.py          # 配置管理
    ├── prompts.py         # Prompt 模板
    ├── intents.py         # 意圖定義
    ├── chains.py          # Chain 定義
    ├── cli.py             # CLI 介面
    └── tools/             # 工具模組
        ├── __init__.py
        ├── doc_search.py  # 文件搜尋
        ├── calculator.py  # 計算器
        ├── api_client.py  # API 調用
        └── code_runner.py # 程式碼執行
```

## 快速開始

### 1. 建立虛擬環境

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

### 2. 安裝依賴

```bash
pip install -r requirements.txt
```

### 3. 設定環境變數

```bash
cp .env.example .env
# 編輯 .env 填入您的 API Key
```

### 4. 執行

```bash
# 執行最新版本 (v0.3)
python main.py

# 執行特定版本
python main.py --v1  # 基礎問答
python main.py --v2  # 意圖分類
python main.py --v3  # 工具增強
```

## 版本說明

### v0.1 - 基礎問答 (Chapter 1)

- 使用 LCEL 組合 Prompt + LLM + Parser
- 串流輸出支援
- 簡單的 CLI 介面

### v0.2 - 意圖分類 (Chapter 2)

- 意圖分類器 (IntentClassifier)
- 結構化輸出 (Pydantic)
- 動態路由到不同處理器

### v0.3 - 工具增強 (Chapter 3)

- 文件搜尋工具
- 計算器工具
- API 調用工具
- 程式碼執行工具 (沙箱)

## 測試工具

### 計算器

```python
from techassist.tools import calculator

result = calculator.invoke({"expression": "sqrt(16) + pi"})
print(result)  # 計算結果：7.141592653589793
```

### 文件搜尋

```python
from techassist.tools import search_documentation

result = search_documentation.invoke({
    "query": "async await",
    "source": "python"
})
print(result)
```

### 程式碼執行

```python
from techassist.tools import run_python_code

result = run_python_code.invoke({
    "code": "print([x**2 for x in range(5)])",
    "timeout": 5
})
print(result)  # ✅ 執行成功：[0, 1, 4, 9, 16]
```

## 注意事項

1. **API Key**: 請確保設定了有效的 `ANTHROPIC_API_KEY`
2. **網路**: 部分工具需要網路連接（API 調用）
3. **安全**: 程式碼執行工具有安全限制，禁止危險操作

## 相關章節

- Chapter 1: 啟程——從 Chain 到 LCEL
- Chapter 2: Prompt 工程與結構化輸出
- Chapter 3: Tool Use——賦予 AI 手腳
