# 第 3 章：深度研究的認知框架

> **本章目標**：為代理人設計一套「認知藍圖」，使其能像人類研究員一樣進行系統性的資訊尋求與知識整合。
>
> **核心產出物**：
> - 認知模式流程圖
> - 認知框架 Prompt 模板
> - 研究策略決策樹
> - 完整可運行的 `cognitive_research_agent.py`

---

## 開場案例：一位研究員的思維過程

想像一下，你是一位資深產業分析師，接到了一個研究任務：

> 「評估量子計算對金融業的潛在影響，特別是在風險管理與投資組合優化方面。」

你會怎麼做？

大多數人不會立刻開始「回答問題」。相反，你的大腦會經歷一連串的思考過程：

1. **問題分解**：「量子計算」、「金融業」、「風險管理」、「投資組合優化」——這些詞彙意味著什麼？它們之間有什麼關聯？

2. **資訊規劃**：我需要了解量子計算的現狀、金融業的計算需求、現有的研究文獻、企業案例...

3. **來源評估**：學術論文的可信度高於新聞報導；一手資料優於二手轉述；最新數據比舊數據更有價值...

4. **批判性思考**：這項技術是否被過度炒作？有沒有反面觀點？實際落地的障礙是什麼？

5. **知識整合**：如何將零散的資訊組織成有結構的報告？

這整個過程，就是我們所說的「**認知框架**」（Cognitive Framework）。

如果我們希望 AI 代理人能夠進行真正的「深度研究」，而不只是簡單的問答，我們就必須將這套認知框架「植入」到代理人中。

本章將帶你深入理解這套認知框架，並將其轉化為可執行的程式碼。

---

## 3.1 人類研究員的認知模式

在設計代理人的認知框架之前，我們需要先理解人類研究員是如何思考的。認知科學為我們提供了豐富的理論基礎。

### 3.1.1 資訊尋求行為模型

1970 年代，圖書資訊學家 Carol Kuhlthau 提出了著名的「**資訊搜尋過程模型**」（Information Search Process Model），描述了人們在進行研究時經歷的六個階段：

```
┌──────────────────────────────────────────────────────────────────┐
│                    資訊搜尋過程模型（ISP）                         │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐         │
│  │ 啟動    │──▶│ 選擇    │──▶│ 探索    │──▶│ 聚焦    │         │
│  │ Initiation│  │Selection│   │Exploration│  │Formulation│        │
│  └─────────┘   └─────────┘   └─────────┘   └─────────┘         │
│       │                                          │              │
│       │                                          ▼              │
│       │                                    ┌─────────┐         │
│       │                                    │ 收集    │         │
│       │                                    │Collection│         │
│       │                                    └─────────┘         │
│       │                                          │              │
│       │                                          ▼              │
│       │                                    ┌─────────┐         │
│       └────────────────────────────────────│ 呈現    │         │
│                                            │Presentation│       │
│                                            └─────────┘         │
│                                                                  │
│  情緒變化: 不確定 → 樂觀 → 困惑 → 清晰 → 滿足 → 成就感          │
└──────────────────────────────────────────────────────────────────┘
```

讓我們來理解每個階段：

| 階段 | 認知活動 | 情緒狀態 | Agent 對應行為 |
|------|----------|----------|----------------|
| **啟動** | 意識到資訊缺口 | 不確定 | 接收任務、理解需求 |
| **選擇** | 確定研究主題 | 樂觀 | 分解問題、選擇切入點 |
| **探索** | 廣泛蒐集資訊 | 困惑、懷疑 | 多源搜尋、初步篩選 |
| **聚焦** | 形成明確觀點 | 清晰 | 確定核心論點、收斂方向 |
| **收集** | 深入蒐集證據 | 信心增加 | 深度搜尋、驗證資訊 |
| **呈現** | 組織並表達 | 滿足或失望 | 生成報告、引用來源 |

> **關鍵洞察**：注意到「**探索**」階段的「困惑」情緒嗎？這是正常的！好的研究過程必然會經歷這個階段。如果代理人在早期就過於「確定」，反而可能意味著它沒有真正深入探索。

### 3.1.2 批判性思考的要素

批判性思考（Critical Thinking）是區分「深度研究」與「表面搜尋」的關鍵能力。Richard Paul 和 Linda Elder 提出的批判性思維框架包含以下要素：

```
┌──────────────────────────────────────────────────────────────────┐
│                    批判性思維的八個元素                           │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│                        ┌─────────────┐                          │
│                        │   目的      │                          │
│                        │  Purpose    │                          │
│                        └──────┬──────┘                          │
│                               │                                  │
│        ┌──────────────────────┼──────────────────────┐          │
│        ▼                      ▼                      ▼          │
│  ┌───────────┐         ┌───────────┐         ┌───────────┐      │
│  │  問題     │         │  資訊     │         │  概念     │      │
│  │ Question  │         │Information│         │ Concepts  │      │
│  └─────┬─────┘         └─────┬─────┘         └─────┬─────┘      │
│        │                     │                     │            │
│        └──────────────────────┼──────────────────────┘          │
│                               ▼                                  │
│                        ┌───────────┐                            │
│                        │  假設     │                            │
│                        │Assumptions│                            │
│                        └─────┬─────┘                            │
│                               │                                  │
│        ┌──────────────────────┼──────────────────────┐          │
│        ▼                      ▼                      ▼          │
│  ┌───────────┐         ┌───────────┐         ┌───────────┐      │
│  │  觀點     │         │  推論     │         │  影響     │      │
│  │ Point of  │         │Inferences │         │Implications│     │
│  │   View    │         │           │         │           │      │
│  └───────────┘         └───────────┘         └───────────┘      │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

將這些元素轉化為代理人可以執行的具體行為：

| 思維元素 | 批判性問題 | Agent 實踐 |
|----------|-----------|------------|
| **目的** | 我為什麼要研究這個？ | 明確研究目標與預期產出 |
| **問題** | 核心問題是什麼？ | 問題分解與優先級排序 |
| **資訊** | 我需要什麼資料？ | 來源識別與資訊蒐集 |
| **概念** | 有哪些關鍵概念？ | 術語定義與概念釐清 |
| **假設** | 我有什麼先入為主的假設？ | 假設識別與挑戰 |
| **觀點** | 有沒有不同的觀點？ | 多元視角蒐集 |
| **推論** | 我的推論有什麼依據？ | 證據支撐與邏輯驗證 |
| **影響** | 這個結論有什麼影響？ | 後果分析與風險評估 |

### 3.1.3 知識整合與綜合

研究的最終目的不是蒐集一堆資料，而是**整合**這些資料成為有意義的知識。Benjamin Bloom 的認知分類學（Taxonomy of Learning）為我們提供了一個框架：

```
                        ┌─────────────┐
                        │   創造      │  ← 最高層次
                        │   Create    │
                        └──────┬──────┘
                               │
                        ┌──────▼──────┐
                        │   評估      │
                        │  Evaluate   │
                        └──────┬──────┘
                               │
                        ┌──────▼──────┐
                        │   分析      │
                        │   Analyze   │
                        └──────┬──────┘
                               │
                        ┌──────▼──────┐
                        │   應用      │
                        │    Apply    │
                        └──────┬──────┘
                               │
                        ┌──────▼──────┐
                        │   理解      │
                        │ Understand  │
                        └──────┬──────┘
                               │
                        ┌──────▼──────┐
                        │   記憶      │  ← 最低層次
                        │  Remember   │
                        └─────────────┘
```

傳統的 LLM 主要停留在「記憶」和「理解」層次——它們能回憶訓練資料中的資訊，並展示一定程度的理解。但深度研究代理人需要達到更高層次：

- **分析**：識別模式、比較差異、追溯因果
- **評估**：判斷可信度、評估論證強度
- **創造**：綜合多方資訊產生新的見解

> **MiroThinker 的設計目標**：透過工具調用與多輪交互，讓 8B 模型也能展現「分析」甚至「評估」層次的認知能力。

---

## 3.2 從認知科學到 Agent 設計

現在我們已經理解了人類研究員的認知模式，下一步是將這些理論轉化為代理人可以執行的程式碼。

### 3.2.1 認知模式的程式化表達

我們首先定義一個研究過程的狀態機：

```
┌──────────────────────────────────────────────────────────────────┐
│                    研究代理人狀態機                               │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐                                               │
│  │   INIT       │  接收任務                                      │
│  │   初始化     │──────────────────────────────┐                │
│  └──────────────┘                              │                │
│         │                                      │                │
│         ▼                                      │                │
│  ┌──────────────┐                              │                │
│  │  DECOMPOSE   │  問題分解                    │                │
│  │   分解問題   │◀─────────────────────────────┤                │
│  └──────────────┘       需要重新分解            │                │
│         │                                      │                │
│         ▼                                      │                │
│  ┌──────────────┐                              │                │
│  │   EXPLORE    │  廣泛探索                    │                │
│  │   探索階段   │◀─────────────────────────────┤                │
│  └──────────────┘       發現新方向              │                │
│         │                                      │                │
│         ▼                                      │                │
│  ┌──────────────┐                              │                │
│  │    FOCUS     │  聚焦驗證                    │                │
│  │   聚焦階段   │                              │                │
│  └──────────────┘                              │                │
│         │                                      │                │
│         ├──── 資訊不足 ──────────────────────▶─┘                │
│         │                                                       │
│         ▼                                                       │
│  ┌──────────────┐                                               │
│  │  SYNTHESIZE  │  知識綜合                                      │
│  │   綜合階段   │                                               │
│  └──────────────┘                                               │
│         │                                                       │
│         ▼                                                       │
│  ┌──────────────┐                                               │
│  │   REPORT     │  生成報告                                      │
│  │   報告階段   │                                               │
│  └──────────────┘                                               │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

這個狀態機有幾個關鍵設計：

1. **非線性流程**：狀態可以回退（例如從 FOCUS 回到 EXPLORE）
2. **資訊驅動轉換**：狀態轉換由資訊充足度決定
3. **終止條件明確**：達到 REPORT 階段才算完成

### 3.2.2 分階段研究策略

每個階段都有特定的目標和策略：

```python
# 研究階段定義
from enum import Enum
from dataclasses import dataclass

class ResearchPhase(Enum):
    INIT = "init"           # 初始化
    DECOMPOSE = "decompose" # 問題分解
    EXPLORE = "explore"     # 廣泛探索
    FOCUS = "focus"         # 聚焦驗證
    SYNTHESIZE = "synthesize"  # 知識綜合
    REPORT = "report"       # 生成報告

@dataclass
class PhaseConfig:
    """階段配置"""
    name: str
    max_iterations: int  # ‹1› 每個階段的最大迭代次數
    min_sources: int     # ‹2› 最少需要的來源數量
    confidence_threshold: float  # ‹3› 進入下一階段的信心閾值
    allowed_tools: list[str]  # ‹4› 該階段允許使用的工具
```

**標記說明**：
- ‹1› 防止代理人在某一階段陷入無限循環
- ‹2› 確保資訊的多樣性
- ‹3› 決定何時可以進入下一階段
- ‹4› 不同階段使用不同工具，提高效率

每個階段的詳細策略：

| 階段 | 目標 | 策略 | 工具優先級 |
|------|------|------|------------|
| **DECOMPOSE** | 將複雜問題拆分為可管理的子問題 | 識別關鍵術語、確定研究邊界、建立問題層次 | 無需工具（純推理） |
| **EXPLORE** | 廣泛蒐集相關資訊 | 多元搜尋、不過早過濾、記錄所有發現 | 搜尋引擎、知識庫 |
| **FOCUS** | 深入驗證關鍵資訊 | 交叉比對、追溯原始來源、評估可信度 | 網頁瀏覽、學術搜尋 |
| **SYNTHESIZE** | 整合資訊形成見解 | 識別模式、建立連結、提煉核心論點 | 無需工具（純推理） |
| **REPORT** | 產出結構化報告 | 組織結構、引用來源、視覺化呈現 | 無需工具（純生成） |

### 3.2.3 自我質疑與驗證機制

批判性思考的核心是「自我質疑」。我們設計一套機制讓代理人能夠質疑自己的發現：

```python
# 自我質疑 Prompt 模板
SELF_QUESTIONING_PROMPT = """
你剛才得出了以下結論：
{conclusion}

請從以下角度進行自我質疑：

1. **證據充足性**：支持這個結論的證據是否足夠？有沒有關鍵證據缺失？

2. **來源可信度**：這些證據來自哪裡？來源是否可靠？是否有利益衝突？

3. **邏輯一致性**：從證據到結論的推理過程是否有邏輯漏洞？

4. **反面論證**：有沒有反對這個結論的證據或觀點？這些反對意見是否有道理？

5. **時效性**：這些資訊是否過時？領域是否有新的發展可能推翻這個結論？

6. **假設識別**：這個結論建立在什麼假設之上？這些假設是否合理？

請根據質疑結果，決定下一步行動：
- 如果發現重大問題，返回 EXPLORE 階段蒐集更多資訊
- 如果發現小問題，在 FOCUS 階段進行補充驗證
- 如果結論穩固，進入 SYNTHESIZE 階段
"""
```

這個機制確保代理人不會過早「收斂」到一個可能有問題的結論。

---

## 3.3 MiroThinker 的研究策略

MiroThinker 項目實現了一套精心設計的研究策略。讓我們深入分析其核心機制。

### 3.3.1 問題分解（Query Decomposition）

複雜問題通常無法用單一搜尋來回答。MiroThinker 使用階層式問題分解：

```
原始問題：「量子計算對金融業的潛在影響？」
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
   ┌─────────┐ ┌─────────┐ ┌─────────┐
   │子問題 1 │ │子問題 2 │ │子問題 3 │
   │量子計算 │ │金融業的 │ │現有應用 │
   │技術現狀 │ │計算需求 │ │案例     │
   └────┬────┘ └────┬────┘ └────┬────┘
        │           │           │
   ┌────▼────┐ ┌────▼────┐ ┌────▼────┐
   │ • 量子  │ │ • 風險  │ │ • IBM   │
   │   比特  │ │   計算  │ │   量子  │
   │ • 糾錯  │ │ • 蒙特  │ │ • 摩根  │
   │   技術  │ │   卡羅  │ │   大通  │
   │ • 時程  │ │ • 組合  │ │ • 高盛  │
   │   預測  │ │   優化  │ │   實驗  │
   └─────────┘ └─────────┘ └─────────┘
```

分解策略的關鍵原則：

1. **MECE 原則**：Mutually Exclusive, Collectively Exhaustive（互斥且完備）
2. **依賴識別**：某些子問題可能依賴其他子問題的答案
3. **優先排序**：先處理基礎問題，再處理進階問題
4. **動態調整**：根據發現動態添加或移除子問題

```python
# 問題分解的 Prompt 模板
QUERY_DECOMPOSITION_PROMPT = """
你的任務是將一個複雜的研究問題分解為可管理的子問題。

原始問題：{original_query}

請遵循以下步驟：

1. **識別核心概念**：找出問題中的關鍵術語和概念

2. **建立問題層次**：
   - 第一層：核心問題（1-3 個）
   - 第二層：支持問題（每個核心問題 2-4 個）

3. **確定依賴關係**：標註哪些問題需要先回答

4. **設定優先級**：基於重要性和依賴關係排序

輸出格式：
```json
{
  "core_concepts": ["概念1", "概念2", ...],
  "questions": [
    {
      "id": "Q1",
      "question": "子問題描述",
      "level": 1,
      "dependencies": [],
      "priority": 1
    },
    ...
  ]
}
```
"""
```

### 3.3.2 多來源交叉驗證

單一來源的資訊不可靠。MiroThinker 實施嚴格的多來源驗證策略：

```
┌──────────────────────────────────────────────────────────────────┐
│                    多來源交叉驗證流程                             │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  聲明：「量子計算將在 2030 年達到商業化水平」                      │
│                    │                                             │
│    ┌───────────────┼───────────────┬───────────────┐            │
│    ▼               ▼               ▼               ▼            │
│ ┌──────┐      ┌──────┐       ┌──────┐       ┌──────┐           │
│ │來源 A│      │來源 B│       │來源 C│       │來源 D│           │
│ │學術  │      │企業  │       │政府  │       │新聞  │           │
│ │論文  │      │報告  │       │白皮書│       │報導  │           │
│ └──┬───┘      └──┬───┘       └──┬───┘       └──┬───┘           │
│    │             │              │              │               │
│    ▼             ▼              ▼              ▼               │
│ 「2028-      「2030 年      「2035 年      「2025 年           │
│  2032」       可能」         保守估計」      樂觀預測」          │
│    │             │              │              │               │
│    └─────────────┴──────────────┴──────────────┘               │
│                    │                                             │
│                    ▼                                             │
│    ┌─────────────────────────────────────────┐                  │
│    │         交叉驗證分析                     │                  │
│    │ • 一致性：中等（2028-2035 範圍）         │                  │
│    │ • 偏差：新聞來源傾向樂觀                 │                  │
│    │ • 建議：採用 2030±2 年作為合理估計       │                  │
│    └─────────────────────────────────────────┘                  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

驗證規則：

| 規則 | 說明 | 閾值 |
|------|------|------|
| **最少來源** | 關鍵事實至少需要 N 個獨立來源 | N ≥ 2 |
| **來源多樣性** | 來源類型不能單一（如全是新聞） | ≥ 2 種類型 |
| **時效性** | 優先採用較新的資訊 | < 2 年 |
| **一致性檢查** | 多來源說法的一致程度 | 60%+ 一致 |
| **權威優先** | 學術 > 官方 > 企業 > 新聞 | 依序權重 |

### 3.3.3 證據權重評估

並非所有證據都有相同的說服力。MiroThinker 使用一套證據評分系統：

```python
# 證據權重評估
from dataclasses import dataclass
from enum import Enum

class SourceType(Enum):
    ACADEMIC = "academic"     # 學術論文、期刊
    OFFICIAL = "official"     # 政府、官方機構
    INDUSTRY = "industry"     # 產業報告、企業白皮書
    NEWS = "news"            # 新聞報導
    SOCIAL = "social"        # 社群媒體、部落格

class EvidenceStrength(Enum):
    STRONG = 3     # 直接證據、一手資料
    MODERATE = 2   # 間接證據、專家分析
    WEAK = 1       # 推測、意見

@dataclass
class Evidence:
    """證據資料結構"""
    claim: str              # 聲明內容
    source_url: str         # 來源網址
    source_type: SourceType # 來源類型
    strength: EvidenceStrength  # 證據強度
    timestamp: str          # 資料時間
    author_credibility: float   # 作者可信度 (0-1)

    def calculate_weight(self) -> float:
        """計算證據權重"""
        # ‹1› 基礎權重：來源類型
        type_weights = {
            SourceType.ACADEMIC: 1.0,
            SourceType.OFFICIAL: 0.9,
            SourceType.INDUSTRY: 0.7,
            SourceType.NEWS: 0.5,
            SourceType.SOCIAL: 0.2
        }
        base_weight = type_weights[self.source_type]

        # ‹2› 強度加成
        strength_multiplier = {
            EvidenceStrength.STRONG: 1.5,
            EvidenceStrength.MODERATE: 1.0,
            EvidenceStrength.WEAK: 0.5
        }
        strength_factor = strength_multiplier[self.strength]

        # ‹3› 時效性懲罰（假設越新越好）
        from datetime import datetime
        age_years = (datetime.now() -
                     datetime.fromisoformat(self.timestamp)).days / 365
        recency_factor = max(0.3, 1 - age_years * 0.1)  # 每年降 10%

        # ‹4› 綜合權重
        return (base_weight *
                strength_factor *
                recency_factor *
                self.author_credibility)
```

**標記說明**：
- ‹1› 不同來源類型有不同的基礎權重
- ‹2› 強證據獲得加成，弱證據被懲罰
- ‹3› 時效性：舊資訊的權重會降低
- ‹4› 綜合計算最終權重

---

## 3.4 處理不確定性與矛盾資訊

真實世界的研究充滿了不確定性。代理人必須學會優雅地處理這些情況。

### 3.4.1 不確定性的類型

```
┌──────────────────────────────────────────────────────────────────┐
│                    不確定性的三種類型                             │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 1. 資訊不足（Information Gap）                           │    │
│  │    • 特徵：找不到相關資訊                               │    │
│  │    • 處理：擴大搜尋範圍、使用替代資訊                   │    │
│  │    • 報告：明確標註「資料不足」                         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 2. 資訊矛盾（Conflicting Information）                   │    │
│  │    • 特徵：不同來源說法不一致                           │    │
│  │    • 處理：評估來源權威、分析差異原因                   │    │
│  │    • 報告：呈現不同觀點及其依據                         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 3. 固有模糊（Inherent Ambiguity）                        │    │
│  │    • 特徵：事物本身就是模糊的（如未來預測）             │    │
│  │    • 處理：提供範圍而非點估計                           │    │
│  │    • 報告：明確說明不確定性範圍                         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 3.4.2 矛盾消解策略

當遇到矛盾資訊時，代理人應該：

```python
# 矛盾消解策略
CONFLICT_RESOLUTION_PROMPT = """
你發現了以下矛盾資訊：

聲明 A（來源：{source_a}）：
{claim_a}

聲明 B（來源：{source_b}）：
{claim_b}

請按以下步驟分析矛盾：

1. **識別矛盾類型**：
   - 完全矛盾（A 說是，B 說否）
   - 程度矛盾（A 說很多，B 說很少）
   - 時間矛盾（A 說過去，B 說現在）
   - 範圍矛盾（A 說特定情況，B 說一般情況）

2. **評估來源權威**：
   - 來源 A 的可信度：{credibility_a}
   - 來源 B 的可信度：{credibility_b}
   - 哪個來源更接近第一手資料？

3. **分析可能原因**：
   - 定義不同？
   - 時間點不同？
   - 方法論不同？
   - 利益衝突？

4. **決定處理方式**：
   - 如果可以判斷哪個正確，採用正確的
   - 如果無法判斷，同時呈現兩種觀點
   - 如果涉及核心論點，需要尋找更多來源

請輸出你的分析和決定。
"""
```

矛盾處理決策樹：

```
                    發現矛盾
                        │
                        ▼
               ┌─────────────────┐
               │ 評估來源權威差距│
               └────────┬────────┘
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
    差距 > 0.3     差距 0.1-0.3   差距 < 0.1
          │             │             │
          ▼             ▼             ▼
    採用高權威      進一步分析      同時呈現
    來源說法        矛盾原因        兩種觀點
                        │
                        ▼
               ┌─────────────────┐
               │ 是否影響核心論點│
               └────────┬────────┘
                        │
              ┌─────────┴─────────┐
              ▼                   ▼
             是                  否
              │                   │
              ▼                   ▼
        尋找更多來源          標註矛盾存在
        再做判斷              繼續研究
```

### 3.4.3 置信度評估

代理人應該對每個結論標註置信度：

```python
@dataclass
class Conclusion:
    """研究結論"""
    statement: str           # 結論聲明
    confidence: float        # 置信度 (0-1)
    supporting_evidence: list[Evidence]  # 支持證據
    conflicting_evidence: list[Evidence]  # 矛盾證據
    uncertainty_type: str    # 不確定性類型

def assess_confidence(
    supporting: list[Evidence],
    conflicting: list[Evidence]
) -> float:
    """評估結論置信度"""

    # ‹1› 計算支持證據的總權重
    support_weight = sum(e.calculate_weight() for e in supporting)

    # ‹2› 計算反對證據的總權重
    conflict_weight = sum(e.calculate_weight() for e in conflicting)

    # ‹3› 計算淨置信度
    if support_weight + conflict_weight == 0:
        return 0.0  # 無證據，無置信度

    raw_confidence = support_weight / (support_weight + conflict_weight)

    # ‹4› 來源多樣性加成
    source_types = set(e.source_type for e in supporting)
    diversity_bonus = min(len(source_types) * 0.05, 0.15)

    # ‹5› 最終置信度（上限 0.95，表示「幾乎確定」）
    return min(raw_confidence + diversity_bonus, 0.95)
```

置信度等級對應的報告語言：

| 置信度範圍 | 等級 | 報告用語 |
|-----------|------|----------|
| 0.9 - 1.0 | 非常高 | 「可以確定...」「證據明確顯示...」 |
| 0.7 - 0.9 | 高 | 「很可能...」「多數證據支持...」 |
| 0.5 - 0.7 | 中等 | 「可能...」「部分證據顯示...」 |
| 0.3 - 0.5 | 低 | 「可能但不確定...」「有限證據顯示...」 |
| 0.0 - 0.3 | 非常低 | 「尚無定論...」「需要更多研究...」 |

---

## 3.5 動手實作：認知研究代理人

現在我們將所有理論付諸實踐，建構一個具備認知框架的研究代理人。

### 3.5.1 專案結構

```
chapter-03/
├── cognitive_research_agent.py  # 主程式
├── research_phases.py           # 研究階段定義
├── evidence_system.py           # 證據評估系統
├── prompts/                     # Prompt 模板
│   ├── decomposition.txt        # 問題分解
│   ├── exploration.txt          # 探索階段
│   ├── verification.txt         # 驗證階段
│   └── synthesis.txt            # 綜合階段
├── requirements.txt
├── .env.example
└── README.md
```

### 3.5.2 核心實作：認知研究代理人

```python
"""
cognitive_research_agent.py

具備認知框架的深度研究代理人
遵循 ISP 模型（資訊搜尋過程）進行系統性研究

使用方式：
    agent = CognitiveResearchAgent()
    report = agent.research("量子計算對金融業的影響")
"""

import os
import json
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


# =============================================================================
# 研究階段定義
# =============================================================================

class ResearchPhase(Enum):
    """研究階段枚舉"""
    INIT = "init"              # ‹1› 初始化：接收任務
    DECOMPOSE = "decompose"    # ‹2› 分解：拆分問題
    EXPLORE = "explore"        # ‹3› 探索：廣泛蒐集
    FOCUS = "focus"            # ‹4› 聚焦：深入驗證
    SYNTHESIZE = "synthesize"  # ‹5› 綜合：整合知識
    REPORT = "report"          # ‹6› 報告：產出結果


@dataclass
class PhaseConfig:
    """階段配置"""
    max_iterations: int = 5
    min_sources: int = 2
    confidence_threshold: float = 0.7
    allowed_tools: list = field(default_factory=lambda: ["search"])


# 各階段的預設配置
PHASE_CONFIGS = {
    ResearchPhase.DECOMPOSE: PhaseConfig(
        max_iterations=2,
        min_sources=0,
        confidence_threshold=0.8,
        allowed_tools=[]  # 純推理，不需工具
    ),
    ResearchPhase.EXPLORE: PhaseConfig(
        max_iterations=10,
        min_sources=3,
        confidence_threshold=0.5,
        allowed_tools=["search", "browse"]
    ),
    ResearchPhase.FOCUS: PhaseConfig(
        max_iterations=8,
        min_sources=2,
        confidence_threshold=0.7,
        allowed_tools=["search", "browse", "academic_search"]
    ),
    ResearchPhase.SYNTHESIZE: PhaseConfig(
        max_iterations=3,
        min_sources=0,
        confidence_threshold=0.8,
        allowed_tools=[]  # 純推理，不需工具
    ),
}


# =============================================================================
# 證據系統
# =============================================================================

class SourceType(Enum):
    """來源類型"""
    ACADEMIC = "academic"    # 學術論文
    OFFICIAL = "official"    # 官方機構
    INDUSTRY = "industry"    # 產業報告
    NEWS = "news"           # 新聞媒體
    SOCIAL = "social"       # 社群媒體
    UNKNOWN = "unknown"     # 未知


class EvidenceStrength(Enum):
    """證據強度"""
    STRONG = 3
    MODERATE = 2
    WEAK = 1


@dataclass
class Evidence:
    """證據資料結構"""
    claim: str                      # 聲明內容
    source_url: str                 # 來源網址
    source_type: SourceType         # 來源類型
    strength: EvidenceStrength      # 證據強度
    timestamp: str = ""             # 資料時間
    author: str = ""                # 作者

    def calculate_weight(self) -> float:
        """計算證據權重"""
        type_weights = {
            SourceType.ACADEMIC: 1.0,
            SourceType.OFFICIAL: 0.9,
            SourceType.INDUSTRY: 0.7,
            SourceType.NEWS: 0.5,
            SourceType.SOCIAL: 0.2,
            SourceType.UNKNOWN: 0.3
        }

        strength_multiplier = {
            EvidenceStrength.STRONG: 1.5,
            EvidenceStrength.MODERATE: 1.0,
            EvidenceStrength.WEAK: 0.5
        }

        base = type_weights.get(self.source_type, 0.3)
        multiplier = strength_multiplier.get(self.strength, 1.0)

        return base * multiplier


@dataclass
class Conclusion:
    """研究結論"""
    statement: str
    confidence: float
    supporting_evidence: list = field(default_factory=list)
    conflicting_evidence: list = field(default_factory=list)


# =============================================================================
# 搜尋工具
# =============================================================================

class SearchTool:
    """網路搜尋工具"""

    def __init__(self):
        self.api_key = os.getenv("SERPER_API_KEY")

    def search(self, query: str, num_results: int = 5) -> list[dict]:
        """執行搜尋"""
        if not self.api_key:
            return self._mock_search(query)

        import requests

        response = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": self.api_key},
            json={"q": query, "num": num_results}
        )

        if response.status_code == 200:
            data = response.json()
            results = []
            for item in data.get("organic", [])[:num_results]:
                results.append({
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "link": item.get("link", "")
                })
            return results

        return self._mock_search(query)

    def _mock_search(self, query: str) -> list[dict]:
        """模擬搜尋（用於測試）"""
        return [
            {
                "title": f"搜尋結果 1：{query}",
                "snippet": f"這是關於 {query} 的模擬搜尋結果。在實際環境中，這裡會顯示真實的搜尋結果。",
                "link": "https://example.com/result1"
            },
            {
                "title": f"搜尋結果 2：{query} 詳解",
                "snippet": f"深入分析 {query} 的各個面向，提供專業見解和數據支持。",
                "link": "https://example.com/result2"
            }
        ]


# =============================================================================
# Prompt 模板
# =============================================================================

DECOMPOSITION_PROMPT = """你是一位研究策略專家。請將以下複雜問題分解為可管理的子問題。

研究問題：{query}

請遵循以下步驟：

1. **識別核心概念**：找出問題中的 3-5 個關鍵術語

2. **分解子問題**：將問題拆分為 3-6 個具體的子問題
   - 每個子問題應該可以獨立研究
   - 子問題應該涵蓋問題的各個面向

3. **確定優先級**：標註哪些問題應該先回答

請以 JSON 格式輸出：
```json
{
  "core_concepts": ["概念1", "概念2", ...],
  "sub_questions": [
    {
      "id": "Q1",
      "question": "子問題描述",
      "priority": 1,
      "search_queries": ["建議的搜尋關鍵字"]
    }
  ],
  "research_strategy": "簡述研究策略"
}
```"""

EXPLORATION_PROMPT = """你是一位資深研究員，正在進行探索階段的研究。

研究問題：{query}
當前子問題：{sub_question}

你需要廣泛蒐集相關資訊。以下是搜尋結果：

{search_results}

請分析這些結果：

1. **關鍵發現**：提取 3-5 個重要的事實或觀點

2. **資訊缺口**：識別還需要進一步研究的方面

3. **矛盾之處**：標註任何矛盾或不一致的資訊

4. **下一步**：建議接下來的搜尋方向

請以 JSON 格式輸出：
```json
{
  "key_findings": [
    {
      "finding": "發現內容",
      "source": "來源",
      "confidence": 0.8
    }
  ],
  "information_gaps": ["缺口1", "缺口2"],
  "contradictions": ["矛盾1"],
  "next_searches": ["下一個搜尋詞"]
}
```"""

VERIFICATION_PROMPT = """你是一位事實查核專家，正在驗證研究發現。

原始聲明：{claim}

已蒐集的證據：
{evidence_list}

請進行嚴格驗證：

1. **證據評估**：評估每條證據的可信度和相關性

2. **交叉驗證**：不同來源是否支持相同結論？

3. **矛盾分析**：如有矛盾，分析可能原因

4. **置信度判定**：給出最終置信度（0-1）

請以 JSON 格式輸出：
```json
{
  "verification_result": "confirmed" | "partially_confirmed" | "unconfirmed" | "contradicted",
  "confidence": 0.75,
  "reasoning": "驗證推理過程",
  "verified_claim": "經驗證後的聲明（可能與原始有修正）"
}
```"""

SYNTHESIS_PROMPT = """你是一位知識綜合專家，正在整合研究成果。

研究問題：{query}

已驗證的發現：
{verified_findings}

請進行知識綜合：

1. **核心論點**：提煉 3-5 個核心結論

2. **關係梳理**：這些結論之間有什麼關聯？

3. **不確定性**：明確標註仍不確定的部分

4. **建議**：基於研究結果提出建議

請以 JSON 格式輸出：
```json
{
  "core_conclusions": [
    {
      "conclusion": "結論內容",
      "confidence": 0.8,
      "supporting_evidence": ["證據1", "證據2"]
    }
  ],
  "relationships": "結論之間的關係說明",
  "uncertainties": ["不確定點1", "不確定點2"],
  "recommendations": ["建議1", "建議2"]
}
```"""

REPORT_PROMPT = """你是一位專業報告撰寫者。請基於研究結果撰寫結構化報告。

研究問題：{query}

研究結論：
{conclusions}

請撰寫一份專業的研究報告，包含：

1. **摘要**（100-150 字）：概述主要發現

2. **研究背景**：說明問題的重要性

3. **主要發現**：詳細說明核心結論
   - 每個發現需標註置信度
   - 提供支持證據

4. **討論**：分析發現的意義和局限

5. **結論與建議**：總結並提出行動建議

6. **參考來源**：列出主要資訊來源

請直接輸出 Markdown 格式的報告。"""


# =============================================================================
# 認知研究代理人
# =============================================================================

class CognitiveResearchAgent:
    """
    具備認知框架的深度研究代理人

    實現 ISP（資訊搜尋過程）模型的六個階段：
    初始化 → 問題分解 → 探索 → 聚焦驗證 → 綜合 → 報告
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        verbose: bool = True
    ):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model
        self.verbose = verbose
        self.search_tool = SearchTool()

        # 研究狀態
        self.current_phase = ResearchPhase.INIT
        self.query = ""
        self.sub_questions = []
        self.findings = []
        self.evidence_pool = []
        self.conclusions = []
        self.interaction_count = 0

    def research(self, query: str) -> str:
        """
        執行完整研究流程

        Args:
            query: 研究問題

        Returns:
            結構化研究報告（Markdown 格式）
        """
        start_time = time.time()
        self.query = query

        self._log(f"\n{'='*60}")
        self._log(f"🔬 開始研究：{query}")
        self._log(f"{'='*60}\n")

        try:
            # 階段 1：問題分解
            self._phase_decompose()

            # 階段 2：探索
            self._phase_explore()

            # 階段 3：聚焦驗證
            self._phase_focus()

            # 階段 4：綜合
            self._phase_synthesize()

            # 階段 5：生成報告
            report = self._phase_report()

            elapsed = time.time() - start_time
            self._log(f"\n{'='*60}")
            self._log(f"✅ 研究完成")
            self._log(f"⏱️  總耗時：{elapsed:.1f} 秒")
            self._log(f"🔄 總交互次數：{self.interaction_count}")
            self._log(f"{'='*60}\n")

            return report

        except Exception as e:
            self._log(f"❌ 研究過程發生錯誤：{e}")
            raise

    def _phase_decompose(self):
        """問題分解階段"""
        self.current_phase = ResearchPhase.DECOMPOSE
        self._log_phase("問題分解", "將複雜問題拆分為可管理的子問題")

        response = self._call_llm(
            DECOMPOSITION_PROMPT.format(query=self.query)
        )

        try:
            # 嘗試解析 JSON
            result = self._extract_json(response)
            self.sub_questions = result.get("sub_questions", [])

            self._log(f"   📋 核心概念：{result.get('core_concepts', [])}")
            self._log(f"   📋 子問題數量：{len(self.sub_questions)}")

            for i, sq in enumerate(self.sub_questions, 1):
                self._log(f"      Q{i}: {sq.get('question', '')}")

        except Exception as e:
            self._log(f"   ⚠️ 解析失敗，使用原始問題：{e}")
            self.sub_questions = [{
                "id": "Q1",
                "question": self.query,
                "priority": 1,
                "search_queries": [self.query]
            }]

    def _phase_explore(self):
        """探索階段：廣泛蒐集資訊"""
        self.current_phase = ResearchPhase.EXPLORE
        self._log_phase("探索階段", "廣泛蒐集相關資訊")

        config = PHASE_CONFIGS[ResearchPhase.EXPLORE]

        for sq in self.sub_questions[:3]:  # 最多處理 3 個子問題
            question = sq.get("question", "")
            search_queries = sq.get("search_queries", [question])

            self._log(f"\n   🔍 探索子問題：{question}")

            for search_query in search_queries[:2]:  # 每個子問題最多 2 次搜尋
                # 執行搜尋
                results = self.search_tool.search(search_query)
                self.interaction_count += 1

                # 分析結果
                results_text = self._format_search_results(results)

                analysis = self._call_llm(
                    EXPLORATION_PROMPT.format(
                        query=self.query,
                        sub_question=question,
                        search_results=results_text
                    )
                )

                try:
                    result = self._extract_json(analysis)
                    findings = result.get("key_findings", [])
                    self.findings.extend(findings)

                    self._log(f"      ✅ 發現 {len(findings)} 項")

                except Exception as e:
                    self._log(f"      ⚠️ 分析失敗：{e}")

    def _phase_focus(self):
        """聚焦驗證階段"""
        self.current_phase = ResearchPhase.FOCUS
        self._log_phase("聚焦驗證", "交叉驗證關鍵發現")

        verified_findings = []

        for i, finding in enumerate(self.findings[:5]):  # 最多驗證 5 項
            claim = finding.get("finding", "") if isinstance(finding, dict) else str(finding)

            self._log(f"\n   🔎 驗證：{claim[:50]}...")

            # 搜尋驗證資料
            verify_results = self.search_tool.search(f"verify {claim[:50]}")
            self.interaction_count += 1

            evidence_text = self._format_search_results(verify_results)

            # 驗證
            verification = self._call_llm(
                VERIFICATION_PROMPT.format(
                    claim=claim,
                    evidence_list=evidence_text
                )
            )

            try:
                result = self._extract_json(verification)
                confidence = result.get("confidence", 0.5)

                if confidence >= 0.6:
                    verified_findings.append({
                        "claim": result.get("verified_claim", claim),
                        "confidence": confidence,
                        "reasoning": result.get("reasoning", "")
                    })
                    self._log(f"      ✅ 已驗證（置信度：{confidence:.0%}）")
                else:
                    self._log(f"      ⚠️ 未通過驗證（置信度：{confidence:.0%}）")

            except Exception as e:
                self._log(f"      ❌ 驗證失敗：{e}")

        self.findings = verified_findings
        self._log(f"\n   📊 驗證通過：{len(verified_findings)} 項")

    def _phase_synthesize(self):
        """綜合階段：整合研究成果"""
        self.current_phase = ResearchPhase.SYNTHESIZE
        self._log_phase("知識綜合", "整合研究成果形成結論")

        findings_text = json.dumps(self.findings, ensure_ascii=False, indent=2)

        synthesis = self._call_llm(
            SYNTHESIS_PROMPT.format(
                query=self.query,
                verified_findings=findings_text
            )
        )

        try:
            result = self._extract_json(synthesis)
            self.conclusions = result.get("core_conclusions", [])

            self._log(f"   📝 形成 {len(self.conclusions)} 個核心結論")

            for i, c in enumerate(self.conclusions, 1):
                conclusion = c.get("conclusion", "")
                confidence = c.get("confidence", 0)
                self._log(f"      {i}. {conclusion[:50]}... (置信度：{confidence:.0%})")

        except Exception as e:
            self._log(f"   ⚠️ 綜合失敗：{e}")
            self.conclusions = [{
                "conclusion": f"關於「{self.query}」的研究結論需要進一步分析",
                "confidence": 0.5,
                "supporting_evidence": [f.get("claim", "") for f in self.findings]
            }]

    def _phase_report(self) -> str:
        """報告生成階段"""
        self.current_phase = ResearchPhase.REPORT
        self._log_phase("生成報告", "撰寫結構化研究報告")

        conclusions_text = json.dumps(self.conclusions, ensure_ascii=False, indent=2)

        report = self._call_llm(
            REPORT_PROMPT.format(
                query=self.query,
                conclusions=conclusions_text
            )
        )

        # 添加元資料
        report += f"\n\n---\n\n"
        report += f"**研究統計**\n\n"
        report += f"- 研究問題：{self.query}\n"
        report += f"- 子問題數：{len(self.sub_questions)}\n"
        report += f"- 已驗證發現：{len(self.findings)}\n"
        report += f"- 核心結論：{len(self.conclusions)}\n"
        report += f"- 總交互次數：{self.interaction_count}\n"
        report += f"- 使用模型：{self.model}\n"

        return report

    def _call_llm(self, prompt: str) -> str:
        """呼叫 LLM"""
        self.interaction_count += 1

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )

        return response.choices[0].message.content

    def _extract_json(self, text: str) -> dict:
        """從文字中提取 JSON"""
        import re

        # 嘗試找到 JSON 區塊
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
        if json_match:
            return json.loads(json_match.group(1))

        # 嘗試直接解析
        try:
            return json.loads(text)
        except:
            pass

        # 返回空字典
        return {}

    def _format_search_results(self, results: list[dict]) -> str:
        """格式化搜尋結果"""
        formatted = []
        for i, r in enumerate(results, 1):
            formatted.append(
                f"{i}. **{r.get('title', '')}**\n"
                f"   {r.get('snippet', '')}\n"
                f"   來源：{r.get('link', '')}"
            )
        return "\n\n".join(formatted)

    def _log(self, message: str):
        """輸出日誌"""
        if self.verbose:
            print(message)

    def _log_phase(self, phase_name: str, description: str):
        """輸出階段資訊"""
        self._log(f"\n📍 {phase_name}")
        self._log(f"   {description}")
        self._log(f"   {'─'*40}")


# =============================================================================
# 主程式
# =============================================================================

def main():
    """主程式入口"""
    import argparse

    parser = argparse.ArgumentParser(
        description="認知研究代理人 - 具備認知框架的深度研究工具"
    )
    parser.add_argument(
        "-q", "--query",
        type=str,
        help="研究問題"
    )
    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="互動模式"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4o-mini",
        help="使用的模型 (預設: gpt-4o-mini)"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        help="輸出報告到檔案"
    )

    args = parser.parse_args()

    # 檢查 API Key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ 錯誤：請設定 OPENAI_API_KEY 環境變數")
        print("   複製 .env.example 為 .env 並填入你的 API Key")
        return

    # 建立代理人
    agent = CognitiveResearchAgent(
        model=args.model,
        verbose=True
    )

    if args.interactive:
        # 互動模式
        print("\n🔬 認知研究代理人 - 互動模式")
        print("輸入研究問題，或輸入 'quit' 退出\n")

        while True:
            query = input("📝 研究問題：").strip()
            if query.lower() in ['quit', 'exit', 'q']:
                print("👋 再見！")
                break

            if query:
                report = agent.research(query)
                print(f"\n{report}\n")

                if args.output:
                    with open(args.output, 'w', encoding='utf-8') as f:
                        f.write(report)
                    print(f"📄 報告已保存至：{args.output}")

    elif args.query:
        # 指定問題模式
        report = agent.research(args.query)
        print(f"\n{report}")

        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"\n📄 報告已保存至：{args.output}")

    else:
        # 示範模式
        demo_query = "人工智慧對軟體工程師就業市場的影響是什麼？"
        print(f"\n🎯 示範研究問題：{demo_query}\n")

        report = agent.research(demo_query)
        print(f"\n{report}")


if __name__ == "__main__":
    main()
```

**關鍵設計說明**：

| 元件 | 功能 | 對應認知概念 |
|------|------|-------------|
| `ResearchPhase` | 研究階段枚舉 | ISP 模型的六個階段 |
| `PhaseConfig` | 階段配置 | 控制每個階段的行為 |
| `Evidence` | 證據資料結構 | 批判性思考的證據評估 |
| `_phase_decompose()` | 問題分解 | Bloom 的分析能力 |
| `_phase_explore()` | 廣泛探索 | ISP 的探索階段 |
| `_phase_focus()` | 聚焦驗證 | 批判性思考的驗證 |
| `_phase_synthesize()` | 知識綜合 | Bloom 的綜合能力 |

---

## 3.6 章節總結

本章我們深入探討了如何將認知科學的理論轉化為代理人的設計。

### 核心概念回顧

1. **ISP 模型**：人類研究員經歷的六個認知階段，從啟動到呈現

2. **批判性思維**：包含目的、問題、資訊、概念、假設、觀點、推論、影響等八個元素

3. **Bloom 認知分類**：從記憶到創造的六個層次，深度研究代理人需要達到分析和評估層次

4. **研究狀態機**：INIT → DECOMPOSE → EXPLORE → FOCUS → SYNTHESIZE → REPORT

5. **問題分解**：將複雜問題拆分為可管理的子問題，遵循 MECE 原則

6. **多來源驗證**：至少 2 個獨立來源，多種來源類型，權威優先

7. **證據權重**：基於來源類型、證據強度、時效性計算綜合權重

8. **不確定性處理**：區分資訊不足、資訊矛盾、固有模糊三種類型

### 學習檢查清單

- [ ] 理解 ISP 模型的六個階段及其情緒變化
- [ ] 掌握批判性思維的八個元素
- [ ] 能夠設計研究階段狀態機
- [ ] 理解問題分解的 MECE 原則
- [ ] 掌握多來源交叉驗證的規則
- [ ] 能夠實作證據權重計算
- [ ] 理解三種不確定性類型及處理策略
- [ ] 完成 `cognitive_research_agent.py` 的運行

### 進階思考

1. **個性化認知風格**：不同使用者可能有不同的研究偏好，如何讓代理人適應？

2. **領域專業化**：醫學研究和金融分析的認知框架是否應該不同？

3. **協作研究**：多個認知代理人如何協作完成更複雜的研究？

---

## 3.7 下一章預告

在第 4 章「核心調度器設計」中，我們將深入 MiroThinker 的架構核心——調度器。你將學習：

- 如何設計一個能處理複雜多步任務的調度系統
- MiroThinker Dispatcher 的原始碼剖析
- 任務分解與依賴關係管理
- 同步與異步執行策略
- 分散式調度的考量

從單一代理人的認知框架，我們將進入系統層面的架構設計。準備好深入技術細節了嗎？

---

## 本章程式碼清單

| 檔案 | 行數 | 說明 |
|------|------|------|
| `cognitive_research_agent.py` | ~450 | 完整的認知研究代理人 |
| `requirements.txt` | ~15 | Python 依賴清單 |
| `.env.example` | ~10 | 環境變數範例 |
| `README.md` | ~150 | 使用說明 |

**GitHub 位置**：`code-examples/chapter-03/`
