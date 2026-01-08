# 程式碼索引表 (Code Index)

> 本索引收錄《深度研究代理人實戰》全書所有程式碼範例，按章節組織。

---

## 總覽統計

| 統計項目 | 數量 |
|----------|------|
| 總章節數 | 14 章 |
| Python 檔案 | 30 個 |
| 總類別數 | 140+ 個 |
| 總行數（估計） | ~15,000 行 |

---

## 第 1 章：AI 代理人的基礎

**檔案**: `chapter-01/simple_react_agent.py`

### 類別

| 類別名稱 | 說明 | 行號 |
|----------|------|------|
| `Tool` | 工具基礎結構 | 29 |
| `ToolCall` | 工具調用記錄 | 37 |
| `AgentTrace` | 代理人追蹤日誌 | 46 |
| `SearchTool` | 搜尋工具實作 | 58 |
| `SimpleReActAgent` | 簡單 ReAct 代理人 | 143 |

### 函數

| 函數名稱 | 說明 |
|----------|------|
| `interactive_mode()` | 互動模式入口 |
| `main()` | 主程式入口 |

---

## 第 2 章：縮放定律與交互式縮放

**檔案**: `chapter-02/scaling_experiment.py`

### 類別

| 類別名稱 | 說明 | 行號 |
|----------|------|------|
| `ExperimentConfig` | 實驗配置 | 34 |
| `TaskResult` | 任務結果 | 47 |
| `ExperimentResult` | 實驗結果 | 74 |
| `SearchTool` | 搜尋工具 | 123 |
| `ConfigurableAgent` | 可配置代理人 | 181 |
| `ScalingExperiment` | 縮放實驗主類別 | 326 |

### 函數

| 函數名稱 | 說明 |
|----------|------|
| `main()` | 主程式入口 |

---

## 第 3 章：深度研究的認知框架

**檔案**: `chapter-03/cognitive_research_agent.py`

### 類別

| 類別名稱 | 說明 | 行號 |
|----------|------|------|
| `ResearchPhase(Enum)` | 研究階段枚舉 | 28 |
| `PhaseConfig` | 階段配置 | 39 |
| `SourceType(Enum)` | 資訊來源類型 | 80 |
| `EvidenceStrength(Enum)` | 證據強度枚舉 | 90 |
| `Evidence` | 證據資料結構 | 98 |
| `Conclusion` | 結論資料結構 | 131 |
| `SearchTool` | 搜尋工具 | 143 |
| `CognitiveResearchAgent` | 認知研究代理人主類別 | 355 |

### 函數

| 函數名稱 | 說明 |
|----------|------|
| `main()` | 主程式入口 |

---

## 第 4 章：系統架構設計

**檔案**: `chapter-04/dispatcher.py`

### 核心功能

- 任務調度器實作
- 子任務分解邏輯
- 執行狀態管理

### 函數

| 函數名稱 | 說明 |
|----------|------|
| `main()` | 異步主程式入口 |

---

## 第 5 章：工具生態系統

### 檔案 1: `chapter-05/tool_manager.py`

#### 類別

| 類別名稱 | 說明 | 行號 |
|----------|------|------|
| `ParameterSchema` | 參數結構定義 | 45 |
| `ToolDefinition` | 工具定義 | 73 |
| `ToolResultType(Enum)` | 結果類型枚舉 | 116 |
| `ToolResult` | 工具執行結果 | 125 |
| `BaseTool(ABC)` | 工具抽象基類 | 158 |
| `WebSearchTool` | 網頁搜尋工具 | 258 |
| `WebBrowserTool` | 網頁瀏覽工具 | 324 |
| `PythonInterpreterTool` | Python 解譯器工具 | 419 |
| `FileReaderTool` | 檔案讀取工具 | 521 |
| `ToolRegistry` | 工具註冊表 | 626 |
| `ToolManager` | 工具管理器主類別 | 681 |

#### 函數

| 函數名稱 | 說明 |
|----------|------|
| `demo_tools()` | 工具示範 |
| `demo_with_llm()` | 結合 LLM 示範 |
| `main()` | 主程式入口 |

### 檔案 2: `chapter-05/trajectory_collector.py`

#### 類別

| 類別名稱 | 說明 | 行號 |
|----------|------|------|
| `StepType(Enum)` | 步驟類型枚舉 | 38 |
| `TrajectoryStep` | 軌跡步驟 | 46 |
| `ToolCall` | 工具調用記錄 | 77 |
| `Trajectory` | 完整軌跡 | 103 |
| `RewardCalculator` | 獎勵計算器 | 223 |
| `TrajectoryCollector` | 軌跡收集器主類別 | 422 |
| `TrajectoryReplayer` | 軌跡重播器 | 628 |

#### 函數

| 函數名稱 | 說明 |
|----------|------|
| `demo_trajectory_collection()` | 軌跡收集示範 |
| `main()` | 主程式入口 |

---

## 第 6 章：記憶體系統

### 檔案 1: `chapter-06/memory_manager.py`

#### 類別

| 類別名稱 | 說明 | 行號 |
|----------|------|------|
| `MemoryType(Enum)` | 記憶體類型枚舉 | 40 |
| `MemoryPriority(Enum)` | 優先級枚舉 | 47 |
| `MemoryItem` | 記憶項目 | 56 |
| `WorkingMemory` | 工作記憶 | 131 |
| `Episode` | 情節記錄 | 294 |
| `EpisodicMemory` | 情節記憶 | 359 |
| `KnowledgeChunk` | 知識區塊 | 518 |
| `SemanticMemory` | 語義記憶 | 545 |
| `EpisodeCompressor` | 情節壓縮器 | 716 |
| `EmbeddingGenerator` | 嵌入產生器 | 758 |
| `UnifiedMemoryManager` | 統一記憶管理器 | 794 |

#### 函數

| 函數名稱 | 說明 |
|----------|------|
| `demo_memory_system()` | 記憶系統示範 |
| `main()` | 主程式入口 |

### 檔案 2: `chapter-06/compressor.py`

#### 類別

| 類別名稱 | 說明 | 行號 |
|----------|------|------|
| `CompressionLevel(Enum)` | 壓縮等級枚舉 | 29 |
| `CompressionResult` | 壓縮結果 | 37 |
| `ProgressiveCompressor` | 漸進式壓縮器 | 55 |
| `AdaptiveCompressor` | 自適應壓縮器 | 197 |

### 檔案 3: `chapter-06/embedder.py`

#### 類別

| 類別名稱 | 說明 | 行號 |
|----------|------|------|
| `EmbeddingResult` | 嵌入結果 | 30 |
| `EmbeddingGenerator` | 嵌入產生器 | 41 |
| `SimilarityCalculator` | 相似度計算器 | 169 |
| `SimpleEmbedder` | 簡單嵌入器 | 249 |

---

## 第 7 章：資訊檢索與知識整合

### 檔案 1: `chapter-07/search_engine.py`

#### 類別

| 類別名稱 | 說明 | 行號 |
|----------|------|------|
| `SearchEngine(Enum)` | 搜尋引擎枚舉 | 34 |
| `SearchResult` | 搜尋結果 | 42 |
| `BaseSearchProvider(ABC)` | 搜尋提供者基類 | 73 |
| `SerperSearchProvider` | Serper API 提供者 | 95 |
| `TavilySearchProvider` | Tavily API 提供者 | 169 |
| `DuckDuckGoSearchProvider` | DuckDuckGo 提供者 | 235 |
| `MockSearchProvider` | 模擬搜尋提供者 | 288 |
| `SearchManager` | 搜尋管理器 | 324 |

### 檔案 2: `chapter-07/web_browser.py`

#### 類別

| 類別名稱 | 說明 | 行號 |
|----------|------|------|
| `WebPage` | 網頁資料結構 | 34 |
| `WebBrowser` | 網頁瀏覽器 | 77 |
| `ContentExtractor` | 內容提取器 | 237 |

### 檔案 3: `chapter-07/rag_retriever.py`

#### 類別

| 類別名稱 | 說明 | 行號 |
|----------|------|------|
| `DocumentChunk` | 文件區塊 | 33 |
| `DocumentChunker` | 文件切分器 | 71 |
| `VectorIndex` | 向量索引 | 152 |
| `Embedder` | 嵌入器 | 229 |
| `SimpleEmbedder` | 簡單嵌入器 | 262 |
| `RAGRetriever` | RAG 檢索器主類別 | 300 |

### 檔案 4: `chapter-07/knowledge_graph.py`

#### 類別

| 類別名稱 | 說明 | 行號 |
|----------|------|------|
| `Entity` | 實體 | 33 |
| `Relation` | 關係 | 56 |
| `KnowledgeGraph` | 知識圖譜 | 79 |
| `EntityRelationExtractor` | 實體關係提取器 | 237 |
| `SimpleExtractor` | 簡單提取器 | 324 |

---

## 第 8 章：本地模型部署

### 檔案 1: `chapter-08/model_server.py`

#### 類別

| 類別名稱 | 說明 | 行號 |
|----------|------|------|
| `VLLMConfig` | vLLM 配置 | 36 |
| `ModelServer` | 模型伺服器 | 187 |

#### 函數

| 函數名稱 | 說明 |
|----------|------|
| `deployment_decision()` | 部署決策建議 |
| `demo()` | 示範函數 |
| `main()` | 主程式入口 |

### 檔案 2: `chapter-08/quantize_awq.py`

#### 類別

| 類別名稱 | 說明 | 行號 |
|----------|------|------|
| `QuantizationConfig` | 量化配置 | 34 |
| `QuantizationResult` | 量化結果 | 51 |
| `BenchmarkResult` | 基準測試結果 | 62 |
| `AWQQuantizer` | AWQ 量化器 | 77 |
| `MockQuantizer` | 模擬量化器 | 178 |
| `QuantizationBenchmark` | 量化基準測試 | 231 |

#### 函數

| 函數名稱 | 說明 |
|----------|------|
| `print_comparison_table()` | 輸出對照表 |

### 檔案 3: `chapter-08/metrics_collector.py`

#### 類別

| 類別名稱 | 說明 | 行號 |
|----------|------|------|
| `MetricPoint` | 指標點 | 34 |
| `HealthStatus` | 健康狀態 | 43 |
| `Counter` | 計數器 | 55 |
| `Gauge` | 量規 | 89 |
| `Histogram` | 直方圖 | 123 |
| `MetricsCollector` | 指標收集器 | 188 |
| `HealthChecker` | 健康檢查器 | 296 |
| `PerformanceTracker` | 效能追蹤器 | 368 |
| `AlertRule` | 告警規則 | 460 |
| `AlertManager` | 告警管理器 | 468 |

---

## 第 9 章：整合實作 - MiroThinker

### 檔案 1: `chapter-09/research_agent.py`

#### 核心功能

- MiroThinker 代理人主實作
- 研究流程整合
- 結果輸出格式化

### 檔案 2: `chapter-09/verification.py`

#### 核心功能

- 驗證模組
- 事實核查整合
- 來源追蹤

### 檔案 3: `chapter-09/session.py`

#### 核心功能

- 會話管理
- 狀態持久化
- 上下文追蹤

---

## 第 10 章：多代理人協作

### 檔案 1: `chapter-10/coordinator.py`

#### 類別

| 類別名稱 | 說明 | 行號 |
|----------|------|------|
| `TaskStatus(Enum)` | 任務狀態枚舉 | 33 |
| `MessageType(Enum)` | 訊息類型枚舉 | 42 |
| `SubTask` | 子任務 | 52 |
| `AgentMessage` | 代理人訊息 | 89 |
| `CoordinationResult` | 協調結果 | 117 |
| `ExpertAgent` | 專家代理人基類 | 152 |
| `IndustryAnalystAgent` | 產業分析師代理人 | 242 |
| `TechExpertAgent` | 技術專家代理人 | 330 |
| `FinancialAnalystAgent` | 財務分析師代理人 | 418 |
| `GeopoliticalAdvisorAgent` | 地緣政治顧問代理人 | 509 |
| `ResearchCoordinator` | 研究協調器主類別 | 625 |
| `ReportGenerator` | 報告產生器 | 1032 |

### 檔案 2: `chapter-10/scheduler.py`

#### 類別

| 類別名稱 | 說明 | 行號 |
|----------|------|------|
| `TaskStatus(Enum)` | 任務狀態枚舉 | 28 |
| `SchedulableTask` | 可調度任務 | 39 |
| `DependencyGraph` | 依賴圖 | 81 |
| `TaskScheduler` | 任務調度器 | 216 |
| `PriorityScheduler` | 優先級調度器 | 467 |

### 檔案 3: `chapter-10/conflict_resolver.py`

#### 類別

| 類別名稱 | 說明 | 行號 |
|----------|------|------|
| `ConflictType(Enum)` | 衝突類型枚舉 | 29 |
| `ConflictSeverity(Enum)` | 衝突嚴重度枚舉 | 38 |
| `ResolutionMethod(Enum)` | 解決方法枚舉 | 46 |
| `Conflict` | 衝突 | 56 |
| `ResolutionResult` | 解決結果 | 93 |
| `ConflictDetector` | 衝突偵測器 | 124 |
| `ConflictResolver` | 衝突解決器基類 | 402 |
| `WeightedAverageResolver` | 加權平均解決器 | 419 |
| `MajorityVoteResolver` | 多數決解決器 | 478 |
| `PresentationResolver` | 呈現型解決器 | 524 |
| `IntegratedConflictResolver` | 整合衝突解決器 | 571 |

---

## 第 11 章：生產環境部署

### 檔案 1: `chapter-11/api_server.py`

#### 類別

| 類別名稱 | 說明 | 行號 |
|----------|------|------|
| `ResearchRequest` | 研究請求模型 | 46 |
| `ResearchResponse` | 研究回應模型 | 54 |
| `HealthResponse` | 健康檢查回應 | 67 |
| `ErrorResponse` | 錯誤回應模型 | 75 |

#### API 端點

| 端點 | 方法 | 說明 |
|------|------|------|
| `/health` | GET | 健康檢查 |
| `/ready` | GET | 就緒檢查 |
| `/metrics` | GET | Prometheus 指標 |
| `/research` | POST | 建立研究任務 |
| `/research/{id}` | GET | 查詢研究結果 |
| `/research` | GET | 列出研究任務 |
| `/research/{id}/execute` | POST | 執行研究任務 |

### 檔案 2: `chapter-11/metrics.py`

#### 類別

| 類別名稱 | 說明 | 行號 |
|----------|------|------|
| `MetricsCache` | 指標快取 | 246 |
| `HealthMetrics` | 健康指標 | 294 |

#### 函數

| 函數名稱 | 說明 |
|----------|------|
| `setup_metrics()` | 設置指標系統 |
| `track_request()` | 追蹤請求裝飾器 |
| `track_research_task()` | 追蹤研究任務裝飾器 |
| `track_llm_call()` | 追蹤 LLM 調用裝飾器 |

### 檔案 3: `chapter-11/logging_module.py`

#### 類別

| 類別名稱 | 說明 | 行號 |
|----------|------|------|
| `StructuredFormatter` | 結構化格式器 | 38 |
| `PrettyFormatter` | 美觀格式器 | 81 |
| `LogManager` | 日誌管理器 | 117 |
| `LoggingMiddleware` | 日誌中介層 | 288 |
| `AuditLogger` | 審計日誌器 | 356 |

#### 函數

| 函數名稱 | 說明 |
|----------|------|
| `get_logger()` | 取得 Logger |
| `log_with_context()` | 帶上下文日誌 |
| `log_operation()` | 操作日誌裝飾器 |
| `set_request_id()` | 設置請求 ID |
| `get_request_id()` | 取得請求 ID |

---

## 第 12 章：基準測試全解析

### 檔案 1: `chapter-12/hle_evaluator.py`

#### 類別

| 類別名稱 | 說明 | 行號 |
|----------|------|------|
| `QualityDimension(Enum)` | 品質維度枚舉 | 28 |
| `HLEScore` | HLE 評分 | 47 |
| `HLETestCase` | HLE 測試案例 | 80 |
| `HLEEvaluator` | HLE 評估器 | 102 |
| `HLETestSuite` | HLE 測試套件 | 225 |
| `HLERunner` | HLE 執行器 | 425 |

### 檔案 2: `chapter-12/gaia_benchmark.py`

#### 類別

| 類別名稱 | 說明 | 行號 |
|----------|------|------|
| `GAIALevel(Enum)` | GAIA 難度等級枚舉 | 29 |
| `GAIAQuestion` | GAIA 問題資料結構 | 41 |
| `GAIABenchmark` | GAIA 基準測試主類別 | 165 |

### 檔案 3: `chapter-12/unified_evaluator.py`

#### 類別

| 類別名稱 | 說明 | 行號 |
|----------|------|------|
| `BenchmarkType(Enum)` | 基準測試類型枚舉 | 29 |
| `EvaluationConfig` | 評估配置 | 41 |
| `EvaluationResult` | 評估結果 | 68 |
| `UnifiedEvaluator` | 統一評估器 | 95 |
| `EvaluationDashboard` | 評估儀表板 | 248 |
| `ResultComparator` | 結果比較器 | 509 |

---

## 第 13 章：幻覺處理與事實查核

**檔案**: `chapter-13/fact_check_pipeline.py`

### 類別

| 類別名稱 | 說明 | 行號 |
|----------|------|------|
| `HallucinationType(Enum)` | 幻覺類型枚舉 | 33 |
| `VerificationStatus(Enum)` | 驗證狀態枚舉 | 42 |
| `CausalRelationType(Enum)` | 因果關係類型枚舉 | 51 |
| `HallucinationInstance` | 幻覺實例 | 65 |
| `Claim` | 聲明 | 85 |
| `Evidence` | 證據 | 94 |
| `VerificationResult` | 驗證結果 | 104 |
| `CausalClaim` | 因果聲明 | 115 |
| `FactCheckReport` | 事實查核報告 | 125 |
| `HallucinationAnalyzer` | 幻覺分析器 | 144 |
| `FactCheckEngine` | 事實查核引擎 | 303 |
| `TemporalAwareProcessor` | 時效感知處理器 | 442 |
| `CausalReasoningValidator` | 因果推理驗證器 | 571 |
| `FactCheckPipeline` | 事實查核管線主類別 | 690 |

---

## 第 14 章：效能優化與成本控制

**檔案**: `chapter-14/cost_optimizer.py`

### 類別

| 類別名稱 | 說明 | 行號 |
|----------|------|------|
| `OptimizationProfile(Enum)` | 優化配置枚舉 | 33 |
| `OptimizationTarget` | 優化目標 | 42 |
| `TokenUsage` | Token 使用統計 | 80 |
| `TokenAnalyzer` | Token 分析器 | 112 |
| `TokenOptimizer` | Token 優化器 | 155 |
| `CacheEntry` | 快取項目 | 214 |
| `MemoryCache` | 記憶體快取 (L1) | 227 |
| `MultiLayerCache` | 多層快取 | 264 |
| `BudgetPeriod(Enum)` | 預算週期枚舉 | 303 |
| `Budget` | 預算 | 312 |
| `CostRecord` | 成本記錄 | 321 |
| `CostTracker` | 成本追蹤器 | 331 |
| `TaskComplexity(Enum)` | 任務複雜度枚舉 | 414 |
| `ModelProfile` | 模型配置 | 423 |
| `ModelRouter` | 模型路由器 | 432 |
| `ParallelExecutor` | 並行執行器 | 492 |
| `RateLimiter` | 速率限制器 | 516 |
| `CostOptimizer` | 成本優化器主類別 | 544 |

### 函數

| 函數名稱 | 說明 |
|----------|------|
| `generate_cache_key()` | 產生快取鍵 |
| `demo()` | 示範函數 |

---

## 設計模式索引

### 策略模式 (Strategy Pattern)

| 章節 | 實作 | 說明 |
|------|------|------|
| 7 | `BaseSearchProvider` | 搜尋引擎可替換 |
| 10 | `ConflictResolver` | 衝突解決策略 |
| 14 | `OptimizationProfile` | 優化策略 |

### 工廠模式 (Factory Pattern)

| 章節 | 實作 | 說明 |
|------|------|------|
| 5 | `ToolRegistry` | 工具註冊與建立 |
| 7 | `SearchManager` | 搜尋提供者工廠 |
| 14 | `ModelRouter` | 模型選擇工廠 |

### 裝飾器模式 (Decorator Pattern)

| 章節 | 實作 | 說明 |
|------|------|------|
| 11 | `track_request()` | 請求追蹤裝飾器 |
| 11 | `track_llm_call()` | LLM 調用追蹤 |
| 11 | `log_operation()` | 操作日誌裝飾器 |

### 觀察者模式 (Observer Pattern)

| 章節 | 實作 | 說明 |
|------|------|------|
| 8 | `AlertManager` | 告警訂閱機制 |
| 11 | `MetricsCache` | 指標更新通知 |

### 單例模式 (Singleton Pattern)

| 章節 | 實作 | 說明 |
|------|------|------|
| 6 | `UnifiedMemoryManager` | 統一記憶管理 |
| 11 | `LogManager` | 日誌管理器 |

---

## 依賴關係圖

```
chapter-01 (基礎)
    ↓
chapter-02 (縮放定律)
    ↓
chapter-03 (認知框架)
    ↓
chapter-04 (架構設計)
    ↓
chapter-05 ─→ chapter-06 ─→ chapter-07
(工具系統)   (記憶系統)   (資訊檢索)
    ↓           ↓           ↓
    └───────────┼───────────┘
                ↓
            chapter-08
           (本地模型)
                ↓
            chapter-09
           (MiroThinker)
                ↓
            chapter-10
           (多代理人)
                ↓
            chapter-11
           (部署)
                ↓
            chapter-12
           (基準測試)
                ↓
            chapter-13
           (幻覺處理)
                ↓
            chapter-14
           (效能優化)
```

---

## 快速參考

### 核心類別（必讀）

| 類別 | 章節 | 檔案 |
|------|------|------|
| `SimpleReActAgent` | 1 | simple_react_agent.py |
| `CognitiveResearchAgent` | 3 | cognitive_research_agent.py |
| `ToolManager` | 5 | tool_manager.py |
| `UnifiedMemoryManager` | 6 | memory_manager.py |
| `RAGRetriever` | 7 | rag_retriever.py |
| `ResearchCoordinator` | 10 | coordinator.py |
| `FactCheckPipeline` | 13 | fact_check_pipeline.py |
| `CostOptimizer` | 14 | cost_optimizer.py |

### 運行示範

每個章節都包含 `main()` 或 `demo()` 函數，可直接運行：

```bash
# 運行第 N 章示範
cd code-examples/chapter-XX
python main_file.py
```

---

**最後更新**: 2026-01-08
