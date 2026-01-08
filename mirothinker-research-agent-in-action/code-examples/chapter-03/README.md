# 第 3 章：深度研究的認知框架 - 程式碼範例

> 本目錄包含《深度研究代理人實戰》第 3 章的完整可運行程式碼。

---

## 快速開始

### 1. 建立虛擬環境

```bash
cd code-examples/chapter-03
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
python cognitive_research_agent.py

# 指定研究問題
python cognitive_research_agent.py -q "量子計算對金融業的影響"

# 互動模式
python cognitive_research_agent.py -i

# 輸出報告到檔案
python cognitive_research_agent.py -q "AI 對就業市場的影響" -o report.md
```

---

## 檔案說明

| 檔案 | 說明 |
|------|------|
| `cognitive_research_agent.py` | 完整的認知研究代理人實現（~450 行） |
| `requirements.txt` | Python 依賴清單 |
| `.env.example` | 環境變數範例 |
| `README.md` | 本文件 |

---

## 核心概念

### ISP 模型（資訊搜尋過程）

本代理人實現了 Carol Kuhlthau 的六階段資訊搜尋模型：

```
初始化 → 問題分解 → 探索 → 聚焦驗證 → 知識綜合 → 報告生成
 INIT    DECOMPOSE   EXPLORE   FOCUS    SYNTHESIZE   REPORT
```

### 研究階段

| 階段 | 目標 | 主要活動 |
|------|------|----------|
| **DECOMPOSE** | 問題拆分 | 識別核心概念、分解子問題 |
| **EXPLORE** | 廣泛蒐集 | 多源搜尋、記錄所有發現 |
| **FOCUS** | 深入驗證 | 交叉比對、評估可信度 |
| **SYNTHESIZE** | 知識整合 | 提煉結論、識別不確定性 |
| **REPORT** | 產出報告 | 結構化撰寫、引用來源 |

---

## 使用範例

### 基本用法

```python
from cognitive_research_agent import CognitiveResearchAgent

# 建立代理人
agent = CognitiveResearchAgent(
    model="gpt-4o-mini",
    verbose=True
)

# 執行研究
report = agent.research("區塊鏈技術在供應鏈管理中的應用前景")

# 報告會包含：摘要、背景、發現、討論、結論
print(report)
```

### 自訂配置

```python
from cognitive_research_agent import (
    CognitiveResearchAgent,
    PhaseConfig,
    PHASE_CONFIGS,
    ResearchPhase
)

# 自訂探索階段配置
PHASE_CONFIGS[ResearchPhase.EXPLORE] = PhaseConfig(
    max_iterations=15,    # 增加迭代次數
    min_sources=5,        # 要求更多來源
    confidence_threshold=0.4,  # 降低閾值以獲取更多資訊
    allowed_tools=["search", "browse", "academic_search"]
)

agent = CognitiveResearchAgent(model="gpt-4o")
report = agent.research("深度學習在醫療診斷的最新進展")
```

---

## 執行範例

```
============================================================
🔬 開始研究：人工智慧對軟體工程師就業市場的影響是什麼？
============================================================

📍 問題分解
   將複雜問題拆分為可管理的子問題
   ────────────────────────────────────────
   📋 核心概念：['人工智慧', 'AI', '軟體工程師', '就業市場', '自動化']
   📋 子問題數量：4
      Q1: AI 目前在軟體開發中的應用現狀如何？
      Q2: AI 工具對程式設計師生產力的影響？
      Q3: 哪些軟體工程工作可能被 AI 取代？
      Q4: 軟體工程師如何適應 AI 時代？

📍 探索階段
   廣泛蒐集相關資訊
   ────────────────────────────────────────

   🔍 探索子問題：AI 目前在軟體開發中的應用現狀如何？
      ✅ 發現 4 項

   🔍 探索子問題：AI 工具對程式設計師生產力的影響？
      ✅ 發現 3 項

📍 聚焦驗證
   交叉驗證關鍵發現
   ────────────────────────────────────────

   🔎 驗證：GitHub Copilot 等 AI 程式碼助手可提高開發效...
      ✅ 已驗證（置信度：85%）

   🔎 驗證：AI 更可能輔助而非取代軟體工程師...
      ✅ 已驗證（置信度：78%）

   📊 驗證通過：4 項

📍 知識綜合
   整合研究成果形成結論
   ────────────────────────────────────────
   📝 形成 3 個核心結論
      1. AI 工具正在改變軟體開發流程，但短期內不會... (置信度：82%)
      2. 軟體工程師的角色將從「編碼者」轉變為「AI... (置信度：75%)
      3. 對 AI 工具的掌握程度將成為軟體工程師的核心... (置信度：80%)

📍 生成報告
   撰寫結構化研究報告
   ────────────────────────────────────────

============================================================
✅ 研究完成
⏱️  總耗時：45.3 秒
🔄 總交互次數：18
============================================================
```

---

## 證據評估系統

### 來源類型權重

| 來源類型 | 權重 | 說明 |
|----------|------|------|
| ACADEMIC | 1.0 | 學術論文、期刊 |
| OFFICIAL | 0.9 | 政府、官方機構 |
| INDUSTRY | 0.7 | 產業報告、企業白皮書 |
| NEWS | 0.5 | 新聞報導 |
| SOCIAL | 0.2 | 社群媒體、部落格 |

### 證據強度乘數

| 強度 | 乘數 | 說明 |
|------|------|------|
| STRONG | 1.5x | 直接證據、一手資料 |
| MODERATE | 1.0x | 間接證據、專家分析 |
| WEAK | 0.5x | 推測、意見 |

---

## 進階功能

### 自訂搜尋工具

```python
from cognitive_research_agent import SearchTool

class AcademicSearchTool(SearchTool):
    """學術搜尋工具"""

    def search(self, query: str, num_results: int = 5) -> list[dict]:
        # 使用 Semantic Scholar API 或其他學術搜尋
        # 實作你的學術搜尋邏輯
        pass

# 替換預設搜尋工具
agent.search_tool = AcademicSearchTool()
```

### 自訂驗證規則

```python
def custom_verifier(claim: str, evidence: list) -> float:
    """自訂驗證邏輯"""
    # 實作你的驗證規則
    # 返回 0-1 的置信度
    return confidence

# 在驗證階段使用自訂驗證器
```

---

## 常見問題

### Q: 研究結果不夠深入怎麼辦？

1. 增加 `EXPLORE` 階段的 `max_iterations`
2. 使用更強大的模型（如 `gpt-4o`）
3. 提供更具體的研究問題

### Q: 如何處理敏感或爭議性話題？

代理人會：
1. 蒐集多方觀點
2. 標註置信度
3. 明確說明不確定性

建議：對於爭議性話題，設定較高的 `confidence_threshold`

### Q: 如何減少 API 成本？

1. 使用 `gpt-4o-mini` 而非 `gpt-4o`
2. 減少子問題數量（修改 `sub_questions[:3]`）
3. 降低驗證階段的迭代次數

---

## 認知框架對照表

| 人類認知 | 代理人實現 |
|----------|-----------|
| 問題意識 | `_phase_decompose()` |
| 資訊蒐集 | `_phase_explore()` |
| 批判思考 | `_phase_focus()` |
| 知識整合 | `_phase_synthesize()` |
| 表達呈現 | `_phase_report()` |

---

## 延伸閱讀

- [第 1 章程式碼](../chapter-01/) - ReAct 代理人基礎
- [第 2 章程式碼](../chapter-02/) - 交互式縮放實驗
- [Kuhlthau ISP 模型](https://en.wikipedia.org/wiki/Information_Search_Process)
- [批判性思維框架](https://www.criticalthinking.org/)

---

**本章程式碼授權**：MIT License
