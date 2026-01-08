# 第 8 章：環境搭建與部署 - 程式碼範例

本目錄包含第 8 章「環境搭建與部署」的完整程式碼範例。

## 檔案結構

```
chapter-08/
├── model_server.py       # vLLM 模型服務器配置
├── quantize_awq.py       # AWQ 量化工具
├── metrics_collector.py  # 監控指標收集器
├── requirements.txt      # Python 依賴套件
├── .env.example          # 環境變數範例
└── README.md             # 本文件
```

## 快速開始

### 1. 安裝依賴

```bash
cd chapter-08
pip install -r requirements.txt

# 如需實際部署，安裝 vLLM
pip install vllm transformers
```

### 2. 設定環境變數

```bash
cp .env.example .env
# 編輯 .env 填入你的配置
```

### 3. 執行示範

```bash
# 模型服務器配置示範
python model_server.py --demo

# 量化工具示範
python quantize_awq.py --demo

# 監控指標示範
python metrics_collector.py --demo
```

## 模組說明

### 模型服務器 (model_server.py)

vLLM 模型服務器的配置與管理：

```python
from model_server import VLLMConfig, ModelServer, CONFIGS

# 使用預設配置
config = CONFIGS["dev"]  # dev, test, prod, prod-quantized

# 自訂配置
config = VLLMConfig(
    model_name="Qwen/Qwen2.5-7B-Instruct",
    tensor_parallel_size=1,
    max_model_len=8192,
    gpu_memory_utilization=0.85
)

# 部署決策分析
from model_server import deployment_decision
result = deployment_decision(
    monthly_queries=50000,
    avg_tokens_per_query=5000,
    latency_requirement_ms=3000,
    budget_monthly_usd=5000
)
print(result["recommendation"])
```

### 量化工具 (quantize_awq.py)

AWQ 4-bit 量化實現：

```python
from quantize_awq import AWQQuantizer, QuantizationConfig

# 配置量化參數
config = QuantizationConfig(
    w_bit=4,           # 4-bit 量化
    q_group_size=128,  # 群組大小
    version="GEMM"     # GEMM 核心
)

# 執行量化
quantizer = AWQQuantizer(config)
result = quantizer.quantize(
    model_path="Qwen/Qwen2.5-72B-Instruct",
    output_path="./qwen-72b-awq"
)

print(f"壓縮比: {result.compression_ratio}x")
```

### 監控指標 (metrics_collector.py)

Prometheus 風格的監控指標收集：

```python
from metrics_collector import MetricsCollector, PerformanceTracker, AlertManager

# 收集指標
collector = MetricsCollector()
collector.record_request("/v1/chat", "success", 1.5)
collector.update_gpu_metrics("0", memory_used=70e9, utilization=85.0)

# 導出 Prometheus 格式
print(collector.to_prometheus())

# 效能追蹤
tracker = PerformanceTracker()
tracker.record(latency_ms=1500, tokens=300, success=True)
print(tracker.generate_report())

# 告警管理
alert_manager = AlertManager()
alerts = alert_manager.evaluate({"latency_p99": 6000})
```

## 預設配置模板

### 開發環境（單卡 RTX 4090）

```python
DEV_CONFIG = VLLMConfig(
    model_name="Qwen/Qwen2.5-7B-Instruct",
    tensor_parallel_size=1,
    max_model_len=8192,
    gpu_memory_utilization=0.85,
)
```

### 生產環境（4x A100 80GB）

```python
PROD_CONFIG_72B = VLLMConfig(
    model_name="Qwen/Qwen2.5-72B-Instruct",
    tensor_parallel_size=4,
    max_model_len=32768,
    gpu_memory_utilization=0.90,
)
```

### 生產環境量化版（2x A100 40GB）

```python
PROD_CONFIG_72B_QUANTIZED = VLLMConfig(
    model_name="Qwen/Qwen2.5-72B-Instruct-AWQ",
    tensor_parallel_size=2,
    max_model_len=16384,
    quantization="awq",
)
```

## 硬體需求對照表

| 模型規模 | FP16 顯存 | INT8 顯存 | AWQ 顯存 | 推薦硬體 |
|----------|-----------|-----------|----------|----------|
| 7B-8B | 16GB | 8GB | 4GB | 1x RTX 4090 |
| 14B | 28GB | 14GB | 7GB | 1x A100 40GB |
| 32B | 64GB | 32GB | 16GB | 2x A100 40GB |
| 72B | 144GB | 72GB | 36GB | 4x A100 40GB |

## 量化方法對比

| 方法 | 精度 | 壓縮比 | 品質損失 | 適用場景 |
|------|------|--------|----------|----------|
| FP16 | 16-bit | 2x | ~0% | 標準推理 |
| INT8 | 8-bit | 4x | ~1% | 通用部署 |
| AWQ | 4-bit | 8x | ~2% | 資源受限 |
| GPTQ | 4-bit | 8x | ~3% | 資源受限 |

## Docker 部署

### 構建映像

```bash
docker build -t research-agent/model-server:v1.0.0 -f Dockerfile .
```

### 運行容器

```bash
docker run --gpus all \
  -e MODEL_NAME=Qwen/Qwen2.5-72B-Instruct \
  -e TENSOR_PARALLEL_SIZE=4 \
  -p 8000:8000 \
  research-agent/model-server:v1.0.0
```

## 監控指標

### 請求指標

| 指標 | 類型 | 說明 |
|------|------|------|
| `requests_total` | Counter | 總請求數 |
| `request_latency_seconds` | Histogram | 請求延遲 |

### 模型指標

| 指標 | 類型 | 說明 |
|------|------|------|
| `tokens_generated_total` | Counter | 生成的 tokens |
| `tokens_per_second` | Gauge | 吞吐量 |
| `active_sequences` | Gauge | 活躍序列數 |

### GPU 指標

| 指標 | 類型 | 說明 |
|------|------|------|
| `gpu_memory_used_bytes` | Gauge | GPU 顯存使用 |
| `gpu_utilization_percent` | Gauge | GPU 利用率 |
| `kv_cache_usage_percent` | Gauge | KV Cache 使用率 |

## 告警規則

| 告警名稱 | 條件 | 嚴重度 |
|----------|------|--------|
| high_latency | P99 > 5000ms | warning |
| critical_latency | P99 > 10000ms | critical |
| high_error_rate | 錯誤率 > 5% | warning |
| gpu_memory_high | 顯存 > 95% | warning |

## 學習要點

完成本章後，你將掌握：

1. **硬體選型**
   - 根據模型規模選擇合適的 GPU
   - 評估雲端 vs 自建的成本效益

2. **模型部署**
   - vLLM 高效推理框架
   - Docker 容器化部署

3. **量化技術**
   - AWQ 4-bit 量化
   - 量化對品質和性能的影響

4. **監控與可觀測性**
   - Prometheus 指標收集
   - 效能追蹤與告警

## 下一步

完成本章範例後，建議：

1. 在本地環境嘗試部署 7B 模型
2. 比較不同量化方法的效果
3. 設置完整的監控儀表板

## 相關章節

- **第 7 章**：搜尋與檢索引擎（代理人核心能力）
- **第 9 章**：建構你的第一個研究代理人（整合部署）
- **第 11 章**：生產環境部署（進階部署）
