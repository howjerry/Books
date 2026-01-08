# 第 9 章：建構你的第一個研究代理人 - 程式碼範例

本目錄包含第 9 章「建構你的第一個研究代理人」的完整程式碼範例。

## 檔案結構

```
chapter-09/
├── research_agent.py     # 核心研究代理人
├── verification.py       # 高級驗證模組
├── session.py           # 會話管理
├── requirements.txt      # Python 依賴套件
├── .env.example          # 環境變數範例
└── README.md             # 本文件
```

## 快速開始

### 1. 安裝依賴

```bash
cd chapter-09
pip install -r requirements.txt
```

### 2. 設定環境變數

```bash
cp .env.example .env
# 編輯 .env 填入你的配置
```

### 3. 執行示範

```bash
# 研究代理人示範
python research_agent.py --demo

# 執行研究
python research_agent.py -q "AI 晶片市場分析"

# 驗證模組示範
python verification.py --demo

# 會話管理示範
python session.py --demo

# 互動式研究
python session.py --interactive
```

## 模組說明

### 研究代理人 (research_agent.py)

完整的深度研究代理人實現：

```python
from research_agent import DeepResearchAgent

# 創建代理人
agent = DeepResearchAgent(
    config={
        "max_iterations": 20,
        "max_sources": 10
    }
)

# 執行研究
report = await agent.research("AI 晶片市場競爭格局")

# 輸出報告
print(report.to_markdown())

# 追問研究
follow_up = await agent.follow_up("NVIDIA 的競爭優勢是什麼？")
```

### 驗證模組 (verification.py)

事實查證與可信度評估：

```python
from verification import AdvancedVerificationModule, CredibilityCalculator

# 驗證陳述
verifier = AdvancedVerificationModule()
result = await verifier.verify_claim(
    "NVIDIA 市場份額約 80%",
    existing_sources
)

print(f"驗證狀態: {result.status}")
print(f"可信度: {result.confidence:.0%}")

# 計算來源可信度
calculator = CredibilityCalculator()
score = calculator.evaluate_source("https://reuters.com/article")
```

### 會話管理 (session.py)

多輪對話式研究：

```python
from session import ResearchSession, SessionManager
from research_agent import DeepResearchAgent

# 創建會話
agent = DeepResearchAgent()
session = ResearchSession(agent=agent)

# 多輪提問
await session.ask("什麼是深度學習？")
await session.ask("有哪些主要架構？")

# 匯出會話
export = session.export_session()

# 查看統計
stats = session.get_statistics()
```

## 研究流程

```
用戶問題
    │
    ▼
┌─────────────────┐
│ 1. 問題理解     │  ← 分析意圖、識別關鍵詞
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 2. 研究規劃     │  ← 制定搜尋策略
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 3. 資訊收集     │  ← 網頁搜尋、內容提取
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 4. 分析整合     │  ← 提取關鍵資訊
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 5. 事實查證     │  ← 交叉驗證
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 6. 報告生成     │  ← 結構化輸出
└────────┬────────┘
         │
         ▼
    研究報告
```

## 核心類別

### ResearchQuery

研究查詢資料結構：

```python
@dataclass
class ResearchQuery:
    question: str       # 研究問題
    context: str        # 背景資訊
    constraints: Dict   # 約束條件
```

### ResearchReport

研究報告資料結構：

```python
@dataclass
class ResearchReport:
    query: ResearchQuery
    summary: str              # 摘要
    key_findings: List[str]   # 關鍵發現
    detailed_analysis: str    # 詳細分析
    sources: List[Dict]       # 來源列表
    confidence_score: float   # 信心分數
```

### VerificationResult

驗證結果資料結構：

```python
@dataclass
class VerificationResult:
    claim: str              # 待驗證陳述
    verified: bool          # 是否驗證通過
    confidence: float       # 可信度
    status: str             # verified/likely/conflict/unverified
```

## 配置選項

### 代理人配置

| 參數 | 預設值 | 說明 |
|------|--------|------|
| max_iterations | 20 | 最大迭代次數 |
| max_sources | 10 | 最大來源數量 |
| verify | True | 是否執行事實查證 |

### LLM 配置

| 參數 | 預設值 | 說明 |
|------|--------|------|
| temperature | 0.7 | 生成溫度 |
| max_tokens | 4096 | 最大生成長度 |
| json_mode | False | JSON 模式 |

## 學習要點

完成本章後，你將掌握：

1. **研究代理人架構**
   - 模組化設計原則
   - 狀態管理模式
   - 錯誤處理策略

2. **研究流程編排**
   - 問題分解方法
   - 多來源資訊整合
   - 報告生成模板

3. **事實查證機制**
   - 多來源交叉驗證
   - 可信度評估方法
   - 矛盾識別技術

4. **會話管理**
   - 多輪對話追問
   - 上下文累積
   - 會話持久化

## 擴展建議

1. **整合真實搜尋**：連接第 7 章的搜尋模組
2. **添加記憶管理**：連接第 6 章的記憶模組
3. **部署服務**：使用第 8 章的部署配置

## 相關章節

- **第 6 章**：長短時記憶管理
- **第 7 章**：搜尋與檢索引擎
- **第 8 章**：環境搭建與部署
- **第 10 章**：多代理人協作系統
