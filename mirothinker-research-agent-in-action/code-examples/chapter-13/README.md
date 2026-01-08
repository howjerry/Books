# 第 13 章：幻覺處理與事實查核 - 程式碼範例

## 概覽

本目錄包含第 13 章「幻覺處理與事實查核」的完整程式碼範例，實現了對抗 LLM 幻覺的多層次查核系統。

## 檔案結構

```
chapter-13/
├── fact_check_pipeline.py # 完整事實查核管道（~600 行）
├── requirements.txt       # Python 依賴
├── .env.example           # 環境變數範例
└── README.md              # 本文件
```

## 核心元件

### 1. 幻覺分析器 (`HallucinationAnalyzer`)

檢測和分類 LLM 幻覺：

**幻覺類型**：
- `FACTUAL`：事實性幻覺 - 事實錯誤
- `FABRICATION`：虛構性幻覺 - 完全虛構
- `TEMPORAL`：時序性幻覺 - 時間混淆
- `REASONING`：推理性幻覺 - 邏輯錯誤
- `SOURCE`：來源性幻覺 - 引用捏造

**使用範例**：
```python
from fact_check_pipeline import HallucinationAnalyzer

analyzer = HallucinationAnalyzer(model_cutoff="2024-01")
potential = analyzer.detect_potential_hallucinations(text)

# 使用 LLM 深度分析
detailed = await analyzer.analyze_with_llm(text)
```

### 2. 事實查核引擎 (`FactCheckEngine`)

提取和驗證可驗證聲明：

**功能**：
- 聲明提取（數字、時間、引用）
- 來源可信度評估
- 多源交叉驗證

**使用範例**：
```python
from fact_check_pipeline import FactCheckEngine

engine = FactCheckEngine(search_engine=search_client)
claims = engine.extract_claims(text)
result = await engine.check(text)

print(f"聲明數量：{result['claims_count']}")
print(f"可信度：{result['overall_credibility']:.2%}")
```

### 3. 時序敏感處理器 (`TemporalAwareProcessor`)

處理時間相關的資訊驗證：

**功能**：
- 識別時效性敏感詞彙
- 評估資訊新鮮度
- 生成時序免責聲明

**使用範例**：
```python
from fact_check_pipeline import TemporalAwareProcessor

processor = TemporalAwareProcessor(model_cutoff="2024-01-01")
sensitivity = processor.analyze_temporal_sensitivity(text)
age_info = processor.estimate_information_age(text)

if age_info["is_stale"]:
    print(f"資訊已過時 {age_info['age_days']} 天")
```

### 4. 因果推理驗證器 (`CausalReasoningValidator`)

驗證因果關係的邏輯正確性：

**檢測的謬誤**：
- 後此謬誤：僅因時序先後推斷因果
- 相關性謬誤：將相關性等同於因果性
- 單一原因謬誤：複雜現象歸因於單一原因

**使用範例**：
```python
from fact_check_pipeline import CausalReasoningValidator

validator = CausalReasoningValidator()
claims = validator.extract_causal_claims(text)

for claim in claims:
    result = validator.validate_causal_claim(claim)
    if not result["is_valid"]:
        print(f"問題：{result['issues']}")
```

### 5. 完整管道 (`FactCheckPipeline`)

整合所有查核功能：

**使用範例**：
```python
from fact_check_pipeline import FactCheckPipeline

pipeline = FactCheckPipeline(
    llm_client=llm,
    search_engine=search,
    model_cutoff="2024-01-01"
)

report = await pipeline.check(text)

print(f"可信度：{report.overall_credibility:.2%}")
print(f"風險等級：{report.risk_level}")
for rec in report.recommendations:
    print(f"  - {rec}")
```

## 快速開始

### 1. 安裝依賴

```bash
pip install -r requirements.txt
```

### 2. 運行示範

```bash
python fact_check_pipeline.py
```

### 3. 整合到專案

```python
import asyncio
from fact_check_pipeline import FactCheckPipeline

async def main():
    text = "你的待查核文本..."

    pipeline = FactCheckPipeline()
    report = await pipeline.check(text)

    if report.risk_level == "high":
        print("警告：內容可信度低")
        for rec in report.recommendations:
            print(f"  建議：{rec}")

asyncio.run(main())
```

## 報告結構

```python
@dataclass
class FactCheckReport:
    input_text: str              # 輸入文本
    check_time: datetime         # 查核時間
    duration_seconds: float      # 耗時

    # 各項分析結果
    hallucination_analysis: Dict  # 幻覺分析
    fact_verification: Dict       # 事實驗證
    temporal_analysis: Dict       # 時序分析
    causal_validation: Dict       # 因果驗證

    # 總體評估
    overall_credibility: float    # 整體可信度 (0-1)
    risk_level: str               # 風險等級 (low/medium/high)
    summary: str                  # 摘要
    recommendations: List[str]    # 建議
```

## 可信度計算

整體可信度由四個維度加權計算：

| 維度 | 權重 | 說明 |
|------|------|------|
| 幻覺分析 | 30% | 檢測到的幻覺數量 |
| 事實驗證 | 40% | 聲明驗證結果 |
| 時序新鮮度 | 15% | 資訊是否過時 |
| 因果正確性 | 15% | 邏輯推理品質 |

## 風險等級

| 等級 | 可信度範圍 | 建議行動 |
|------|-----------|----------|
| `low` | ≥ 80% | 可直接使用 |
| `medium` | 60-80% | 建議人工審查 |
| `high` | < 60% | 需要重大修正 |

## 擴展指南

### 添加自定義幻覺指標

```python
HallucinationAnalyzer.HALLUCINATION_INDICATORS["custom"] = [
    "你的自定義指標詞彙"
]
```

### 添加可信來源

```python
FactCheckEngine.SOURCE_CREDIBILITY["your_source"] = 0.85
```

### 自定義有效期

```python
TemporalAwareProcessor.VALIDITY_PERIODS["your_type"] = 14  # 天
```

## 相關章節

- **第 9 章**：建構你的第一個研究代理人
- **第 12 章**：基準測試全解析
- **第 14 章**：效能優化與成本控制

## 授權

本程式碼範例遵循書籍的授權條款，僅供學習和參考使用。
