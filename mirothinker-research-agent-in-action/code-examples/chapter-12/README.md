# 第 12 章：基準測試全解析 - 程式碼範例

## 概覽

本目錄包含第 12 章「基準測試全解析」的完整程式碼範例，實現了深度研究代理人的評測框架。

## 檔案結構

```
chapter-12/
├── hle_evaluator.py       # HLE 評測框架（~350 行）
├── gaia_benchmark.py      # GAIA 基準測試（~300 行）
├── unified_evaluator.py   # 統一評測框架（~400 行）
├── requirements.txt       # Python 依賴
├── .env.example           # 環境變數範例
└── README.md              # 本文件
```

## 核心元件

### 1. HLE 評測器 (`hle_evaluator.py`)

人類水準評測框架，特點：
- 六維度品質評估（準確性、完整性、相關性、連貫性、深度、時效性）
- LLM 驅動的自動評分
- 標準測試套件

**主要類別**：
- `QualityDimension`：品質評估維度枚舉
- `HLEScore`：評分結果
- `HLETestCase`：測試案例
- `HLEEvaluator`：評測器
- `HLETestSuite`：測試套件
- `HLERunner`：執行器

### 2. GAIA 基準測試 (`gaia_benchmark.py`)

GAIA 風格的客觀評測，特點：
- 三級難度分層（Level 1-3）
- 客觀可驗證的答案
- 多種答案類型驗證（數字、字串、列表、布爾）

**主要類別**：
- `GAIALevel`：難度等級
- `GAIAQuestion`：測試問題
- `GAIABenchmark`：基準測試執行器

### 3. 統一評測框架 (`unified_evaluator.py`)

整合多種基準測試，特點：
- 統一的配置和報告格式
- HTML 視覺化儀表板
- 結果比較器

**主要類別**：
- `EvaluationConfig`：評測配置
- `EvaluationResult`：評測結果
- `UnifiedEvaluator`：統一評測器
- `EvaluationDashboard`：視覺化儀表板
- `ResultComparator`：結果比較器

## 快速開始

### 1. 環境準備

```bash
# 複製環境變數範例
cp .env.example .env

# 安裝依賴
pip install -r requirements.txt
```

### 2. 運行示範

```bash
# HLE 評測示範
python hle_evaluator.py

# GAIA 基準測試示範
python gaia_benchmark.py

# 統一評測框架示範
python unified_evaluator.py
```

## 使用範例

### HLE 評測

```python
from hle_evaluator import (
    HLEEvaluator, HLETestSuite, HLERunner
)

# 創建測試套件
suite = HLETestSuite.create_standard_suite()

# 創建評測器（需要 LLM 客戶端）
evaluator = HLEEvaluator(llm_client)

# 創建執行器
runner = HLERunner(agent, evaluator, suite)

# 運行評測
results = await runner.run_all(concurrency=5)

print(f"總體平均分: {results['summary']['overall_average']:.1f}")
```

### GAIA 基準測試

```python
from gaia_benchmark import GAIABenchmark, GAIALevel

# 創建基準測試
benchmark = GAIABenchmark.create_sample_benchmark()

# 運行測試（可選擇難度等級）
results = await benchmark.run(
    agent,
    levels=[GAIALevel.LEVEL_1, GAIALevel.LEVEL_2]
)

print(f"準確率: {results['summary']['overall_accuracy']:.2%}")
```

### 統一評測

```python
from unified_evaluator import (
    UnifiedEvaluator, EvaluationConfig, BenchmarkType
)

# 配置評測
config = EvaluationConfig(
    benchmarks=[BenchmarkType.HLE, BenchmarkType.GAIA],
    agent_name="MiroThinker",
    agent_version="1.0.0",
    output_dir="./results"
)

# 運行評測
evaluator = UnifiedEvaluator(config)
report = await evaluator.evaluate(agent)

# 生成 HTML 報告
from unified_evaluator import EvaluationDashboard
dashboard = EvaluationDashboard(report)
dashboard.save("report.html")
```

## 評測維度說明

### HLE 六維度

| 維度 | 說明 | 權重範例 |
|------|------|----------|
| 準確性 | 事實是否正確 | 0.4 |
| 完整性 | 是否涵蓋所有重要面向 | 0.2 |
| 相關性 | 內容是否與問題高度相關 | 0.15 |
| 連貫性 | 邏輯是否清晰 | 0.1 |
| 深度 | 分析是否深入 | 0.1 |
| 時效性 | 資訊是否最新 | 0.05 |

### GAIA 難度等級

| 等級 | 步驟數 | 特點 |
|------|--------|------|
| Level 1 | 1-2 | 簡單，單一工具 |
| Level 2 | 3-5 | 中等，需要多工具 |
| Level 3 | 5+ | 困難，複雜推理鏈 |

## 自定義測試案例

### 添加 HLE 測試案例

```python
from hle_evaluator import HLETestCase, HLETestSuite

suite = HLETestSuite()

suite.add_test_case(HLETestCase(
    test_id="CUSTOM-001",
    question="你的自定義問題",
    category="custom",
    difficulty="medium",
    reference_answer="參考答案...",
    evaluation_criteria={
        "required_facts": ["事實1", "事實2"],
        "accuracy_weight": 0.5,
        "completeness_weight": 0.5
    }
))
```

### 添加 GAIA 測試問題

```python
from gaia_benchmark import GAIAQuestion, GAIALevel, GAIABenchmark

benchmark = GAIABenchmark()

benchmark.add_question(GAIAQuestion(
    question_id="CUSTOM-001",
    question="你的自定義問題",
    level=GAIALevel.LEVEL_2,
    expected_answer="42",
    answer_type="number",
    required_capabilities=["calculation"],
    expected_tools=["calculator"]
))
```

## 輸出格式

### JSON 報告結構

```json
{
  "agent": {
    "name": "MiroThinker",
    "version": "1.0.0"
  },
  "evaluation": {
    "started_at": "2024-01-15T10:00:00",
    "completed_at": "2024-01-15T10:15:00",
    "duration_seconds": 900
  },
  "scores": {
    "overall": 0.75,
    "by_benchmark": {
      "hle": 0.72,
      "gaia": 0.78
    }
  },
  "detailed_results": { ... }
}
```

## 相關章節

- **第 9 章**：建構你的第一個研究代理人
- **第 10 章**：多代理人協作系統
- **第 13 章**：幻覺處理與事實查核

## 授權

本程式碼範例遵循書籍的授權條款，僅供學習和參考使用。
