# 第 8 章：環境搭建與部署

> **本章目標**：學會從零開始搭建深度研究代理人的運行環境，掌握從 8B 到 72B 模型的部署策略，並實現生產級的推理優化。

---

## 引言：為什麼部署如此重要？

小明是一家金融科技公司的 AI 工程師。在本地開發環境中，他的深度研究代理人表現出色——能夠自主查閱財報、分析市場趨勢、產出專業報告。然而，當他嘗試將系統部署到生產環境時，問題接踵而至：

- 72B 模型需要 140GB 顯存，公司只有 4 張 A100（40GB）
- 單次推理延遲超過 30 秒，用戶無法接受
- 並發請求一多，服務就崩潰
- 不知道如何評估「用多大的模型」才是最佳性價比

這些問題，正是本章要解決的核心議題。

**你將學到**：

1. 硬體選型：如何根據預算和需求選擇 GPU
2. 模型量化：將 72B 模型塞進更少的顯存
3. 推理優化：使用 vLLM 實現高吞吐量
4. 容器化部署：Docker + Kubernetes 生產實踐
5. 監控與擴展：確保系統穩定運行

---

## 8.1 硬體選型指南

### 8.1.1 GPU 家族概覽

```
┌─────────────────────────────────────────────────────────────────┐
│                    NVIDIA GPU 選型矩陣                           │
├──────────────┬─────────────┬────────────┬──────────────────────┤
│    型號      │   顯存      │   FP16     │      適用場景        │
├──────────────┼─────────────┼────────────┼──────────────────────┤
│ RTX 4090     │   24GB      │  165 TFLOPS│ 開發、8B 模型        │
│ A100 40GB    │   40GB      │  312 TFLOPS│ 生產、14B-32B 模型   │
│ A100 80GB    │   80GB      │  312 TFLOPS│ 生產、32B-72B 模型   │
│ H100 80GB    │   80GB      │  989 TFLOPS│ 高吞吐生產環境       │
│ H200 141GB   │  141GB      │  989 TFLOPS│ 超大模型單卡部署     │
└──────────────┴─────────────┴────────────┴──────────────────────┘
```

### 8.1.2 模型規模與顯存需求

深度研究代理人的核心是 LLM，其顯存需求主要由以下因素決定：

```
顯存需求 = 模型參數 × 精度 × 係數 + KV Cache + 激活值

其中：
- 精度：FP32 = 4 bytes, FP16/BF16 = 2 bytes, INT8 = 1 byte, INT4 = 0.5 byte
- 係數：推理時約 1.2-1.5（包含框架開銷）
- KV Cache：與 context length 和 batch size 成正比
```

**常見模型的顯存需求**：

| 模型規模 | FP16 顯存 | INT8 顯存 | INT4 顯存 | 推薦硬體 |
|----------|-----------|-----------|-----------|----------|
| 8B | 16GB | 8GB | 4GB | 1x RTX 4090 |
| 14B | 28GB | 14GB | 7GB | 1x A100 40GB |
| 32B | 64GB | 32GB | 16GB | 2x A100 40GB |
| 72B | 144GB | 72GB | 36GB | 4x A100 40GB |

### 8.1.3 雲端 vs 本地：決策框架

```python
def deployment_decision(
    monthly_queries: int,
    avg_tokens_per_query: int,
    latency_requirement_ms: int,
    budget_monthly_usd: float
) -> str:
    """
    部署決策框架

    ‹1› 計算月度推理成本
    ‹2› 評估延遲需求
    ‹3› 給出建議
    """
    # ‹1› 估算雲端 API 成本（以 GPT-4 為例）
    total_tokens = monthly_queries * avg_tokens_per_query
    api_cost = total_tokens / 1000 * 0.03  # $0.03/1K tokens (輸入)

    # ‹2› 估算自建成本（以 4x A100 為例）
    # 雲端租用：約 $12/hr * 24 * 30 = $8,640/month
    # 自購硬體：約 $60,000 / 36 months = $1,667/month + 電費
    self_hosted_monthly = 2500  # 保守估計

    # ‹3› 決策邏輯
    if latency_requirement_ms < 1000:
        # 高延遲要求 → 自建（避免網路延遲）
        return "自建部署（低延遲需求）"

    if api_cost < self_hosted_monthly * 0.5:
        return "雲端 API（成本較低）"
    elif api_cost < self_hosted_monthly * 1.5:
        return "混合方案（高峰用 API，常規自建）"
    else:
        return "自建部署（長期成本較低）"
```

**決策示例**：

```
場景：金融研究公司
- 月查詢量：50,000 次
- 平均 tokens：8,000（深度研究報告）
- 延遲要求：<10 秒
- 預算：$5,000/月

計算：
- API 成本：50,000 × 8,000 / 1000 × $0.03 = $12,000/月
- 自建成本：約 $2,500/月

結論：自建部署（節省 79% 成本）
```

---

## 8.2 模型部署實戰

### 8.2.1 使用 vLLM 部署（推薦）

vLLM 是目前最高效的 LLM 推理框架之一，核心特點：

- **PagedAttention**：動態管理 KV Cache，提升顯存利用率
- **Continuous Batching**：持續批次處理，提升吞吐量
- **OpenAI 兼容 API**：無縫替換現有應用

```python
#!/usr/bin/env python3
"""
深度研究代理人實戰 - 第 8 章：環境搭建與部署
vLLM 模型服務器配置

使用方式：
    python model_server.py --model Qwen/Qwen2.5-72B-Instruct --gpus 4
"""

import asyncio
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import aiohttp
from dotenv import load_dotenv

load_dotenv()


# =============================================================================
# 配置類
# =============================================================================

@dataclass
class VLLMConfig:
    """
    vLLM 服務器配置

    ‹1› 基礎模型配置
    ‹2› 性能優化參數
    ‹3› 資源限制
    """
    # ‹1› 基礎配置
    model_name: str = "Qwen/Qwen2.5-72B-Instruct"
    host: str = "0.0.0.0"
    port: int = 8000

    # ‹2› 性能優化
    tensor_parallel_size: int = 4  # GPU 數量
    max_model_len: int = 32768     # 最大上下文長度
    gpu_memory_utilization: float = 0.90  # 顯存利用率

    # ‹3› 批次處理
    max_num_seqs: int = 256        # 最大並發序列
    max_num_batched_tokens: int = 32768  # 最大批次 tokens

    # 量化配置
    quantization: Optional[str] = None  # "awq", "gptq", "squeezellm"
    dtype: str = "auto"            # "auto", "float16", "bfloat16"

    def to_cli_args(self) -> List[str]:
        """轉換為 CLI 參數"""
        args = [
            "--model", self.model_name,
            "--host", self.host,
            "--port", str(self.port),
            "--tensor-parallel-size", str(self.tensor_parallel_size),
            "--max-model-len", str(self.max_model_len),
            "--gpu-memory-utilization", str(self.gpu_memory_utilization),
            "--max-num-seqs", str(self.max_num_seqs),
            "--max-num-batched-tokens", str(self.max_num_batched_tokens),
            "--dtype", self.dtype,
        ]

        if self.quantization:
            args.extend(["--quantization", self.quantization])

        return args


# =============================================================================
# 模型服務器
# =============================================================================

class ModelServer:
    """
    模型服務器管理

    ‹1› 啟動 vLLM 服務
    ‹2› 健康檢查
    ‹3› 請求處理
    """

    def __init__(self, config: VLLMConfig):
        self.config = config
        self.base_url = f"http://{config.host}:{config.port}"
        self._process = None

    async def start(self) -> None:
        """啟動服務器"""
        import subprocess

        args = ["python", "-m", "vllm.entrypoints.openai.api_server"]
        args.extend(self.config.to_cli_args())

        print(f"啟動 vLLM 服務器...")
        print(f"命令: {' '.join(args)}")

        self._process = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # 等待服務啟動
        await self._wait_for_ready()

    async def _wait_for_ready(self, timeout: int = 300) -> None:
        """等待服務就緒"""
        for i in range(timeout):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{self.base_url}/health") as resp:
                        if resp.status == 200:
                            print(f"✓ 服務已就緒（耗時 {i+1} 秒）")
                            return
            except:
                pass
            await asyncio.sleep(1)

        raise TimeoutError(f"服務啟動超時（{timeout} 秒）")

    async def health_check(self) -> Dict[str, Any]:
        """健康檢查"""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/health") as resp:
                return await resp.json()

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """生成文本"""
        async with aiohttp.ClientSession() as session:
            payload = {
                "model": self.config.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": temperature,
                **kwargs
            }

            async with session.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload
            ) as resp:
                data = await resp.json()
                return data["choices"][0]["message"]["content"]

    def stop(self) -> None:
        """停止服務器"""
        if self._process:
            self._process.terminate()
            self._process.wait()
            print("服務器已停止")


# =============================================================================
# 預設配置模板
# =============================================================================

# 開發環境（單卡 RTX 4090）
DEV_CONFIG = VLLMConfig(
    model_name="Qwen/Qwen2.5-7B-Instruct",
    tensor_parallel_size=1,
    max_model_len=8192,
    gpu_memory_utilization=0.85,
    max_num_seqs=32,
)

# 生產環境（4x A100 80GB）
PROD_CONFIG_72B = VLLMConfig(
    model_name="Qwen/Qwen2.5-72B-Instruct",
    tensor_parallel_size=4,
    max_model_len=32768,
    gpu_memory_utilization=0.90,
    max_num_seqs=256,
    max_num_batched_tokens=32768,
)

# 生產環境（2x A100 40GB + AWQ 量化）
PROD_CONFIG_72B_QUANTIZED = VLLMConfig(
    model_name="Qwen/Qwen2.5-72B-Instruct-AWQ",
    tensor_parallel_size=2,
    max_model_len=16384,
    gpu_memory_utilization=0.90,
    quantization="awq",
    max_num_seqs=128,
)
```

### 8.2.2 Docker 容器化部署

```dockerfile
# Dockerfile for vLLM Model Server
# 深度研究代理人 - 模型服務器

# 基礎映像
FROM nvidia/cuda:12.1-devel-ubuntu22.04

# 環境變數
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV CUDA_HOME=/usr/local/cuda

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

# 安裝 Python 依賴
RUN pip3 install --no-cache-dir \
    torch==2.1.2 \
    vllm==0.3.0 \
    transformers>=4.35.0 \
    accelerate \
    sentencepiece \
    tiktoken

# 創建工作目錄
WORKDIR /app

# 複製配置和腳本
COPY model_server.py .
COPY entrypoint.sh .

# 設定入口點
RUN chmod +x entrypoint.sh
ENTRYPOINT ["./entrypoint.sh"]

# 暴露端口
EXPOSE 8000

# 健康檢查
HEALTHCHECK --interval=30s --timeout=10s --start-period=300s \
    CMD curl -f http://localhost:8000/health || exit 1
```

**入口腳本（entrypoint.sh）**：

```bash
#!/bin/bash
# entrypoint.sh - vLLM 服務啟動腳本

set -e

# 顯示 GPU 資訊
echo "=== GPU 資訊 ==="
nvidia-smi --query-gpu=gpu_name,memory.total,memory.free --format=csv

# 環境變數設定
export CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-"0,1,2,3"}
export NCCL_DEBUG=${NCCL_DEBUG:-"WARN"}

# 啟動參數
MODEL_NAME=${MODEL_NAME:-"Qwen/Qwen2.5-72B-Instruct"}
TENSOR_PARALLEL_SIZE=${TENSOR_PARALLEL_SIZE:-4}
MAX_MODEL_LEN=${MAX_MODEL_LEN:-32768}
GPU_MEMORY_UTILIZATION=${GPU_MEMORY_UTILIZATION:-0.90}

echo "=== 啟動 vLLM 服務 ==="
echo "模型: ${MODEL_NAME}"
echo "GPU 數量: ${TENSOR_PARALLEL_SIZE}"
echo "最大上下文: ${MAX_MODEL_LEN}"

# 啟動服務
python3 -m vllm.entrypoints.openai.api_server \
    --model "${MODEL_NAME}" \
    --host 0.0.0.0 \
    --port 8000 \
    --tensor-parallel-size "${TENSOR_PARALLEL_SIZE}" \
    --max-model-len "${MAX_MODEL_LEN}" \
    --gpu-memory-utilization "${GPU_MEMORY_UTILIZATION}" \
    --trust-remote-code \
    "$@"
```

### 8.2.3 Docker Compose 完整配置

```yaml
# docker-compose.yml
# 深度研究代理人 - 完整服務棧

version: "3.8"

services:
  # 模型服務器
  model-server:
    build:
      context: ./model-server
      dockerfile: Dockerfile
    container_name: research-agent-model
    runtime: nvidia
    environment:
      - CUDA_VISIBLE_DEVICES=0,1,2,3
      - MODEL_NAME=Qwen/Qwen2.5-72B-Instruct
      - TENSOR_PARALLEL_SIZE=4
      - MAX_MODEL_LEN=32768
      - GPU_MEMORY_UTILIZATION=0.90
    ports:
      - "8000:8000"
    volumes:
      - ~/.cache/huggingface:/root/.cache/huggingface
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 4
              capabilities: [gpu]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 300s
    restart: unless-stopped

  # 代理人服務
  agent-server:
    build:
      context: ./agent-server
      dockerfile: Dockerfile
    container_name: research-agent-core
    environment:
      - MODEL_API_URL=http://model-server:8000/v1
      - REDIS_URL=redis://redis:6379
      - SEARCH_API_KEY=${SEARCH_API_KEY}
    ports:
      - "8080:8080"
    depends_on:
      model-server:
        condition: service_healthy
      redis:
        condition: service_started
    restart: unless-stopped

  # Redis 快取
  redis:
    image: redis:7-alpine
    container_name: research-agent-redis
    command: redis-server --maxmemory 2gb --maxmemory-policy allkeys-lru
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    restart: unless-stopped

  # 向量資料庫
  milvus:
    image: milvusdb/milvus:v2.3.3
    container_name: research-agent-milvus
    environment:
      - ETCD_ENDPOINTS=etcd:2379
    ports:
      - "19530:19530"
    depends_on:
      - etcd
    volumes:
      - milvus-data:/var/lib/milvus
    restart: unless-stopped

  etcd:
    image: quay.io/coreos/etcd:v3.5.0
    container_name: research-agent-etcd
    environment:
      - ETCD_AUTO_COMPACTION_MODE=revision
      - ETCD_AUTO_COMPACTION_RETENTION=1000
    volumes:
      - etcd-data:/etcd

  # 監控
  prometheus:
    image: prom/prometheus:v2.47.0
    container_name: research-agent-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    restart: unless-stopped

  grafana:
    image: grafana/grafana:10.1.5
    container_name: research-agent-grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-data:/var/lib/grafana
    depends_on:
      - prometheus
    restart: unless-stopped

volumes:
  redis-data:
  milvus-data:
  etcd-data:
  prometheus-data:
  grafana-data:
```

---

## 8.3 模型量化技術

當硬體資源有限時，量化是關鍵的優化手段。

### 8.3.1 量化方法對比

```
┌─────────────────────────────────────────────────────────────────┐
│                     量化方法對比                                 │
├──────────────┬──────────┬──────────┬──────────┬────────────────┤
│    方法      │  精度    │ 壓縮比   │ 品質損失 │    適用場景    │
├──────────────┼──────────┼──────────┼──────────┼────────────────┤
│ FP16/BF16    │  16-bit  │   2x     │  ~0%     │ 標準推理       │
│ INT8         │   8-bit  │   4x     │  ~1%     │ 通用部署       │
│ AWQ          │   4-bit  │   8x     │  ~2%     │ 資源受限       │
│ GPTQ         │   4-bit  │   8x     │  ~3%     │ 資源受限       │
│ GGUF/GGML    │  2-8bit  │  4-16x   │  1-5%    │ CPU/邊緣設備   │
└──────────────┴──────────┴──────────┴──────────┴────────────────┘
```

### 8.3.2 AWQ 量化實踐

AWQ（Activation-aware Weight Quantization）是目前品質最好的 4-bit 量化方法之一。

```python
#!/usr/bin/env python3
"""
AWQ 量化工具

使用方式：
    python quantize_awq.py --model Qwen/Qwen2.5-72B-Instruct --output ./qwen-72b-awq
"""

import argparse
from awq import AutoAWQForCausalLM
from transformers import AutoTokenizer


def quantize_model(
    model_path: str,
    output_path: str,
    quant_config: dict = None
) -> None:
    """
    AWQ 量化模型

    ‹1› 載入原始模型
    ‹2› 執行量化
    ‹3› 保存量化模型
    """
    # 預設量化配置
    if quant_config is None:
        quant_config = {
            "zero_point": True,      # 使用零點量化
            "q_group_size": 128,     # 量化群組大小
            "w_bit": 4,              # 權重位數
            "version": "GEMM"        # 使用 GEMM 核心（推理更快）
        }

    print(f"=== AWQ 量化 ===")
    print(f"原始模型: {model_path}")
    print(f"輸出路徑: {output_path}")
    print(f"配置: {quant_config}")

    # ‹1› 載入模型
    print("\n[1/3] 載入模型...")
    model = AutoAWQForCausalLM.from_pretrained(
        model_path,
        trust_remote_code=True,
        safetensors=True
    )
    tokenizer = AutoTokenizer.from_pretrained(
        model_path,
        trust_remote_code=True
    )

    # ‹2› 執行量化
    print("\n[2/3] 執行量化（這可能需要數小時）...")
    model.quantize(tokenizer, quant_config=quant_config)

    # ‹3› 保存
    print("\n[3/3] 保存量化模型...")
    model.save_quantized(output_path)
    tokenizer.save_pretrained(output_path)

    print(f"\n✓ 量化完成: {output_path}")

    # 顯示壓縮效果
    import os
    original_size = sum(
        os.path.getsize(os.path.join(model_path, f))
        for f in os.listdir(model_path)
        if f.endswith(('.bin', '.safetensors'))
    ) / 1e9

    quantized_size = sum(
        os.path.getsize(os.path.join(output_path, f))
        for f in os.listdir(output_path)
        if f.endswith(('.bin', '.safetensors'))
    ) / 1e9

    print(f"\n壓縮效果:")
    print(f"  原始大小: {original_size:.1f} GB")
    print(f"  量化後: {quantized_size:.1f} GB")
    print(f"  壓縮比: {original_size/quantized_size:.1f}x")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AWQ 量化工具")
    parser.add_argument("--model", required=True, help="原始模型路徑")
    parser.add_argument("--output", required=True, help="輸出路徑")
    parser.add_argument("--bits", type=int, default=4, help="量化位數")

    args = parser.parse_args()

    quantize_model(args.model, args.output)
```

### 8.3.3 量化效果基準測試

```python
#!/usr/bin/env python3
"""
量化效果評估工具
"""

import asyncio
import time
from dataclasses import dataclass
from typing import List, Dict, Any
import aiohttp


@dataclass
class BenchmarkResult:
    """基準測試結果"""
    model_name: str
    quantization: str
    latency_p50_ms: float
    latency_p99_ms: float
    throughput_tokens_per_sec: float
    memory_usage_gb: float
    quality_score: float  # 0-100


async def benchmark_model(
    api_url: str,
    model_name: str,
    prompts: List[str],
    num_runs: int = 10
) -> BenchmarkResult:
    """
    對模型進行基準測試

    ‹1› 測試延遲
    ‹2› 測試吞吐量
    ‹3› 測試品質
    """
    latencies = []
    total_tokens = 0

    async with aiohttp.ClientSession() as session:
        for prompt in prompts[:num_runs]:
            start = time.perf_counter()

            payload = {
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 512,
                "temperature": 0.7
            }

            async with session.post(
                f"{api_url}/v1/chat/completions",
                json=payload
            ) as resp:
                data = await resp.json()

            end = time.perf_counter()
            latencies.append((end - start) * 1000)
            total_tokens += data.get("usage", {}).get("total_tokens", 0)

    # 計算統計
    latencies.sort()
    p50 = latencies[len(latencies) // 2]
    p99 = latencies[int(len(latencies) * 0.99)]

    total_time = sum(latencies) / 1000
    throughput = total_tokens / total_time

    return BenchmarkResult(
        model_name=model_name,
        quantization="unknown",
        latency_p50_ms=p50,
        latency_p99_ms=p99,
        throughput_tokens_per_sec=throughput,
        memory_usage_gb=0.0,  # 需要從服務器獲取
        quality_score=0.0     # 需要額外評估
    )


# 測試用例
TEST_PROMPTS = [
    "分析 NVIDIA 在 AI 晶片市場的競爭優勢",
    "解釋 Transformer 架構的自注意力機制",
    "比較 Python 和 Rust 在系統編程中的優缺點",
    "評估深度學習在醫療影像診斷中的應用前景",
    "描述分散式系統中的 CAP 定理及其實際影響",
]
```

**量化效果對比表**：

| 配置 | 顯存 | 延遲 P50 | 吞吐量 | 品質分數 |
|------|------|----------|--------|----------|
| Qwen-72B FP16 | 144GB | 850ms | 45 t/s | 100 |
| Qwen-72B AWQ | 36GB | 920ms | 42 t/s | 98 |
| Qwen-72B GPTQ | 36GB | 980ms | 38 t/s | 96 |
| Qwen-72B INT8 | 72GB | 780ms | 52 t/s | 99 |

---

## 8.4 推理優化技術

### 8.4.1 KV Cache 優化

PagedAttention 是 vLLM 的核心創新，通過分頁管理 KV Cache 提升顯存利用率。

```
傳統 KV Cache 管理：
┌───────────────────────────────────────────────────┐
│ Seq 1 [████████████_______________]               │  ← 預分配固定大小
│ Seq 2 [██████______________________]              │  ← 大量浪費
│ Seq 3 [████████████████████________]              │
└───────────────────────────────────────────────────┘
  顯存利用率: ~40%

PagedAttention：
┌───────────────────────────────────────────────────┐
│ Block Pool: [B1][B2][B3][B4][B5][B6][B7][B8]...   │
│                                                   │
│ Seq 1 → [B1, B3, B5]        ← 動態分配           │
│ Seq 2 → [B2, B4]            ← 按需增長           │
│ Seq 3 → [B6, B7, B8, B9]    ← 高效利用           │
└───────────────────────────────────────────────────┘
  顯存利用率: ~90%
```

### 8.4.2 持續批次處理

```python
"""
持續批次處理（Continuous Batching）示意
"""

class ContinuousBatcher:
    """
    持續批次處理器

    傳統批次：等待所有序列完成 → 吞吐量低
    持續批次：隨時加入/移除序列 → 吞吐量高
    """

    def __init__(self, max_batch_size: int = 256):
        self.max_batch_size = max_batch_size
        self.active_sequences = {}
        self.pending_queue = []

    async def add_request(self, request_id: str, prompt: str) -> None:
        """添加新請求到待處理隊列"""
        self.pending_queue.append({
            "id": request_id,
            "prompt": prompt,
            "tokens_generated": 0
        })

    async def step(self) -> None:
        """
        執行一步推理

        ‹1› 移除已完成的序列
        ‹2› 從隊列添加新序列
        ‹3› 批次推理
        """
        # ‹1› 移除已完成
        completed = [
            seq_id for seq_id, seq in self.active_sequences.items()
            if seq.get("finished", False)
        ]
        for seq_id in completed:
            del self.active_sequences[seq_id]

        # ‹2› 添加新序列
        available_slots = self.max_batch_size - len(self.active_sequences)
        for _ in range(min(available_slots, len(self.pending_queue))):
            request = self.pending_queue.pop(0)
            self.active_sequences[request["id"]] = request

        # ‹3› 批次推理
        if self.active_sequences:
            await self._batch_inference()

    async def _batch_inference(self) -> None:
        """批次推理（簡化示意）"""
        # 實際實作會調用 LLM 推理
        pass
```

### 8.4.3 推測解碼（Speculative Decoding）

```
推測解碼原理：
┌─────────────────────────────────────────────────────────────────┐
│  1. 小模型快速生成 N 個候選 tokens                              │
│     Draft: [token1, token2, token3, token4, token5]             │
│                                                                 │
│  2. 大模型並行驗證所有 tokens                                   │
│     Verify: [✓, ✓, ✓, ✗, -]                                    │
│                                                                 │
│  3. 接受前 3 個，重新生成第 4 個                                │
│     Accept: [token1, token2, token3] + 重試                     │
│                                                                 │
│  效果：減少大模型調用次數，提升整體吞吐量                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 8.5 Kubernetes 生產部署

### 8.5.1 Kubernetes 部署配置

```yaml
# kubernetes/model-server-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: research-agent-model
  labels:
    app: research-agent
    component: model-server
spec:
  replicas: 1
  selector:
    matchLabels:
      app: research-agent
      component: model-server
  template:
    metadata:
      labels:
        app: research-agent
        component: model-server
    spec:
      containers:
      - name: vllm-server
        image: research-agent/model-server:v1.0.0
        ports:
        - containerPort: 8000
          name: http
        env:
        - name: MODEL_NAME
          value: "Qwen/Qwen2.5-72B-Instruct"
        - name: TENSOR_PARALLEL_SIZE
          value: "4"
        - name: MAX_MODEL_LEN
          value: "32768"
        - name: GPU_MEMORY_UTILIZATION
          value: "0.90"
        resources:
          limits:
            nvidia.com/gpu: 4
          requests:
            nvidia.com/gpu: 4
            memory: "64Gi"
            cpu: "16"
        volumeMounts:
        - name: model-cache
          mountPath: /root/.cache/huggingface
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 300
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 300
          periodSeconds: 10
      volumes:
      - name: model-cache
        persistentVolumeClaim:
          claimName: model-cache-pvc
      nodeSelector:
        nvidia.com/gpu.product: "NVIDIA-A100-SXM4-80GB"
      tolerations:
      - key: "nvidia.com/gpu"
        operator: "Exists"
        effect: "NoSchedule"
---
apiVersion: v1
kind: Service
metadata:
  name: research-agent-model
spec:
  selector:
    app: research-agent
    component: model-server
  ports:
  - port: 8000
    targetPort: 8000
    name: http
  type: ClusterIP
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: research-agent-model-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: research-agent-model
  minReplicas: 1
  maxReplicas: 4
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Pods
    pods:
      metric:
        name: requests_per_second
      target:
        type: AverageValue
        averageValue: "100"
```

### 8.5.2 負載均衡與流量管理

```yaml
# kubernetes/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: research-agent-ingress
  annotations:
    nginx.ingress.kubernetes.io/proxy-body-size: "50m"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "300"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "300"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - api.research-agent.example.com
    secretName: research-agent-tls
  rules:
  - host: api.research-agent.example.com
    http:
      paths:
      - path: /v1
        pathType: Prefix
        backend:
          service:
            name: research-agent-model
            port:
              number: 8000
      - path: /agent
        pathType: Prefix
        backend:
          service:
            name: research-agent-core
            port:
              number: 8080
```

---

## 8.6 監控與可觀測性

### 8.6.1 Prometheus 指標配置

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'vllm-server'
    static_configs:
      - targets: ['model-server:8000']
    metrics_path: /metrics

  - job_name: 'agent-server'
    static_configs:
      - targets: ['agent-server:8080']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']

  - job_name: 'nvidia-gpu'
    static_configs:
      - targets: ['dcgm-exporter:9400']
```

### 8.6.2 關鍵監控指標

```python
"""
監控指標收集器
"""

from dataclasses import dataclass
from prometheus_client import Counter, Histogram, Gauge, start_http_server


# 請求指標
REQUEST_TOTAL = Counter(
    'research_agent_requests_total',
    'Total number of requests',
    ['endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'research_agent_request_latency_seconds',
    'Request latency in seconds',
    ['endpoint'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

# 模型指標
TOKENS_GENERATED = Counter(
    'research_agent_tokens_generated_total',
    'Total tokens generated'
)

TOKENS_PER_SECOND = Gauge(
    'research_agent_tokens_per_second',
    'Current tokens per second throughput'
)

# GPU 指標
GPU_MEMORY_USED = Gauge(
    'research_agent_gpu_memory_used_bytes',
    'GPU memory used in bytes',
    ['gpu_id']
)

GPU_UTILIZATION = Gauge(
    'research_agent_gpu_utilization_percent',
    'GPU utilization percentage',
    ['gpu_id']
)

# KV Cache 指標
KV_CACHE_USAGE = Gauge(
    'research_agent_kv_cache_usage_percent',
    'KV cache usage percentage'
)

ACTIVE_SEQUENCES = Gauge(
    'research_agent_active_sequences',
    'Number of active sequences being processed'
)


@dataclass
class MetricsCollector:
    """指標收集器"""

    def record_request(self, endpoint: str, status: str, latency: float) -> None:
        REQUEST_TOTAL.labels(endpoint=endpoint, status=status).inc()
        REQUEST_LATENCY.labels(endpoint=endpoint).observe(latency)

    def record_tokens(self, count: int) -> None:
        TOKENS_GENERATED.inc(count)

    def update_throughput(self, tokens_per_sec: float) -> None:
        TOKENS_PER_SECOND.set(tokens_per_sec)

    def update_gpu_metrics(self, gpu_id: str, memory_used: int, utilization: float) -> None:
        GPU_MEMORY_USED.labels(gpu_id=gpu_id).set(memory_used)
        GPU_UTILIZATION.labels(gpu_id=gpu_id).set(utilization)
```

### 8.6.3 Grafana 儀表板配置

```json
{
  "dashboard": {
    "title": "深度研究代理人 - 系統監控",
    "panels": [
      {
        "title": "請求吞吐量",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(research_agent_requests_total[5m])",
            "legendFormat": "{{endpoint}}"
          }
        ]
      },
      {
        "title": "請求延遲 P99",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.99, rate(research_agent_request_latency_seconds_bucket[5m]))",
            "legendFormat": "{{endpoint}}"
          }
        ]
      },
      {
        "title": "GPU 顯存使用",
        "type": "gauge",
        "targets": [
          {
            "expr": "research_agent_gpu_memory_used_bytes / 1e9",
            "legendFormat": "GPU {{gpu_id}}"
          }
        ]
      },
      {
        "title": "Token 吞吐量",
        "type": "stat",
        "targets": [
          {
            "expr": "research_agent_tokens_per_second",
            "legendFormat": "Tokens/s"
          }
        ]
      },
      {
        "title": "活躍序列數",
        "type": "graph",
        "targets": [
          {
            "expr": "research_agent_active_sequences",
            "legendFormat": "Active Sequences"
          }
        ]
      }
    ]
  }
}
```

---

## 8.7 故障排除指南

### 8.7.1 常見問題與解決方案

| 問題 | 症狀 | 解決方案 |
|------|------|----------|
| OOM（顯存不足） | CUDA out of memory | 降低 max_model_len、使用量化、增加 GPU |
| 模型載入失敗 | 無法下載模型 | 設定 HF_HOME、使用鏡像站點 |
| 推理緩慢 | 延遲 >10秒 | 檢查 GPU 利用率、優化 batch size |
| 服務崩潰 | Container 重啟 | 檢查健康檢查配置、增加啟動時間 |
| API 超時 | 請求無響應 | 檢查網路配置、增加超時設定 |

### 8.7.2 診斷腳本

```bash
#!/bin/bash
# diagnose.sh - 系統診斷腳本

echo "=== 深度研究代理人診斷報告 ==="
echo ""

# GPU 狀態
echo "[1/5] GPU 狀態"
nvidia-smi --query-gpu=index,name,temperature.gpu,memory.used,memory.total,utilization.gpu --format=csv
echo ""

# Docker 容器狀態
echo "[2/5] 容器狀態"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

# 服務健康檢查
echo "[3/5] 服務健康"
curl -s http://localhost:8000/health | jq . 2>/dev/null || echo "模型服務不可用"
curl -s http://localhost:8080/health | jq . 2>/dev/null || echo "代理服務不可用"
echo ""

# 系統資源
echo "[4/5] 系統資源"
echo "CPU 使用率: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}')%"
echo "記憶體使用: $(free -h | awk '/Mem/{print $3"/"$2}')"
echo "磁碟使用: $(df -h / | awk 'NR==2{print $3"/"$2}')"
echo ""

# 日誌錯誤
echo "[5/5] 最近錯誤日誌"
docker logs research-agent-model --tail 20 2>&1 | grep -i "error\|exception" | tail -5
echo ""

echo "=== 診斷完成 ==="
```

---

## 8.8 章節總結

本章我們完成了深度研究代理人的完整部署方案：

### 核心要點回顧

1. **硬體選型**
   - 根據模型規模選擇合適的 GPU
   - 評估雲端 vs 自建的成本效益
   - 考慮延遲和吞吐量需求

2. **模型部署**
   - 使用 vLLM 實現高效推理
   - Docker 容器化確保環境一致性
   - Kubernetes 實現彈性擴展

3. **量化技術**
   - AWQ 是品質最佳的 4-bit 量化
   - 量化可將顯存需求降低 4x
   - 品質損失通常在 2-3% 以內

4. **推理優化**
   - PagedAttention 提升顯存利用率
   - 持續批次處理提升吞吐量
   - 推測解碼加速生成

5. **監控與可觀測性**
   - Prometheus 收集關鍵指標
   - Grafana 視覺化監控
   - 建立完善的告警機制

### 檢查清單

```
□ 確定硬體需求（GPU 型號、數量）
□ 選擇量化策略（FP16 / INT8 / AWQ）
□ 配置 vLLM 服務器
□ 建立 Docker 映像
□ 部署到 Kubernetes（如需要）
□ 配置監控和告警
□ 執行基準測試驗證性能
□ 建立故障排除流程
```

---

## 8.9 下一章預告

在第 9 章「建構你的第一個研究代理人」中，我們將：

1. 整合前面所有章節的組件
2. 實現完整的深度研究工作流程
3. 建立自我查證與事實核查機制
4. 部署端到端的研究代理人系統

這將是整本書的高潮——你將親手打造一個能夠自主完成深度研究的 AI 代理人。

---

## 附錄 A：硬體採購清單

### 開發環境（預算 $5,000）

| 組件 | 規格 | 預估價格 |
|------|------|----------|
| GPU | RTX 4090 24GB | $1,800 |
| CPU | AMD Ryzen 9 7950X | $550 |
| 記憶體 | 64GB DDR5 | $200 |
| 主機板 | X670E | $300 |
| 電源 | 1200W 80+ Platinum | $200 |
| SSD | 2TB NVMe Gen4 | $150 |
| 機殼 + 散熱 | - | $300 |
| **總計** | | **$3,500** |

### 生產環境（預算 $100,000）

| 組件 | 規格 | 預估價格 |
|------|------|----------|
| 伺服器 | Dell PowerEdge R750xa | $15,000 |
| GPU | 4x A100 80GB | $60,000 |
| 記憶體 | 512GB DDR5 ECC | $3,000 |
| 儲存 | 4TB NVMe RAID | $2,000 |
| 網路 | 200Gbps InfiniBand | $5,000 |
| 電力 + 冷卻 | - | $5,000 |
| **總計** | | **$90,000** |

---

## 附錄 B：環境變數參考

```bash
# .env.production
# 深度研究代理人 - 生產環境配置

# 模型配置
MODEL_NAME=Qwen/Qwen2.5-72B-Instruct
TENSOR_PARALLEL_SIZE=4
MAX_MODEL_LEN=32768
GPU_MEMORY_UTILIZATION=0.90

# 服務配置
MODEL_API_HOST=0.0.0.0
MODEL_API_PORT=8000
AGENT_API_PORT=8080

# 資料庫
REDIS_URL=redis://redis:6379
MILVUS_HOST=milvus
MILVUS_PORT=19530

# 外部 API
SERPER_API_KEY=your_key_here
TAVILY_API_KEY=your_key_here

# 監控
PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317

# 日誌
LOG_LEVEL=INFO
LOG_FORMAT=json
```

---

**本章字數**: 約 12,000 字
**預估閱讀時間**: 35 分鐘
