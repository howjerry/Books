#!/usr/bin/env python3
"""
深度研究代理人實戰 - 第 8 章：環境搭建與部署
vLLM 模型服務器配置

這個模組實現了模型服務器的配置與管理：
1. vLLM 服務器配置
2. 健康檢查
3. 請求處理

使用方式：
    python model_server.py --demo
    python model_server.py --config prod
"""

import asyncio
import argparse
import json
import os
import subprocess
import time
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
    model_name: str = "Qwen/Qwen2.5-7B-Instruct"
    host: str = "0.0.0.0"
    port: int = 8000

    # ‹2› 性能優化
    tensor_parallel_size: int = 1       # GPU 數量
    max_model_len: int = 8192           # 最大上下文長度
    gpu_memory_utilization: float = 0.85  # 顯存利用率

    # ‹3› 批次處理
    max_num_seqs: int = 64              # 最大並發序列
    max_num_batched_tokens: int = 8192  # 最大批次 tokens

    # 量化配置
    quantization: Optional[str] = None  # "awq", "gptq", "squeezellm"
    dtype: str = "auto"                 # "auto", "float16", "bfloat16"

    # 額外選項
    trust_remote_code: bool = True
    enforce_eager: bool = False

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

        if self.trust_remote_code:
            args.append("--trust-remote-code")

        if self.enforce_eager:
            args.append("--enforce-eager")

        return args

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "model_name": self.model_name,
            "host": self.host,
            "port": self.port,
            "tensor_parallel_size": self.tensor_parallel_size,
            "max_model_len": self.max_model_len,
            "gpu_memory_utilization": self.gpu_memory_utilization,
            "max_num_seqs": self.max_num_seqs,
            "quantization": self.quantization,
            "dtype": self.dtype
        }

    def estimate_memory_gb(self) -> float:
        """估算顯存需求（GB）"""
        # 簡化估算：根據模型名稱推測參數量
        if "72B" in self.model_name or "72b" in self.model_name:
            base_memory = 144
        elif "32B" in self.model_name or "32b" in self.model_name:
            base_memory = 64
        elif "14B" in self.model_name or "14b" in self.model_name:
            base_memory = 28
        elif "7B" in self.model_name or "7b" in self.model_name:
            base_memory = 14
        elif "8B" in self.model_name or "8b" in self.model_name:
            base_memory = 16
        else:
            base_memory = 16

        # 量化影響
        if self.quantization in ["awq", "gptq"]:
            base_memory *= 0.25
        elif self.quantization == "squeezellm":
            base_memory *= 0.25

        # KV Cache 額外開銷（約 20%）
        return base_memory * 1.2


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
    enforce_eager=True,  # 開發時使用，方便調試
)

# 測試環境（單卡 A100 40GB）
TEST_CONFIG = VLLMConfig(
    model_name="Qwen/Qwen2.5-14B-Instruct",
    tensor_parallel_size=1,
    max_model_len=16384,
    gpu_memory_utilization=0.88,
    max_num_seqs=64,
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

# 配置映射
CONFIGS = {
    "dev": DEV_CONFIG,
    "test": TEST_CONFIG,
    "prod": PROD_CONFIG_72B,
    "prod-quantized": PROD_CONFIG_72B_QUANTIZED,
}


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
        self._started = False

    async def start(self, wait_ready: bool = True) -> None:
        """啟動服務器"""
        args = ["python", "-m", "vllm.entrypoints.openai.api_server"]
        args.extend(self.config.to_cli_args())

        print(f"啟動 vLLM 服務器...")
        print(f"配置: {json.dumps(self.config.to_dict(), indent=2, ensure_ascii=False)}")
        print(f"命令: {' '.join(args)}")

        self._process = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        if wait_ready:
            await self._wait_for_ready()

        self._started = True

    async def _wait_for_ready(self, timeout: int = 300) -> None:
        """等待服務就緒"""
        print(f"等待服務就緒（最多 {timeout} 秒）...")

        for i in range(timeout):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{self.base_url}/health",
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as resp:
                        if resp.status == 200:
                            print(f"✓ 服務已就緒（耗時 {i+1} 秒）")
                            return
            except Exception:
                pass

            await asyncio.sleep(1)

            if i > 0 and i % 30 == 0:
                print(f"  仍在啟動中... ({i} 秒)")

        raise TimeoutError(f"服務啟動超時（{timeout} 秒）")

    async def health_check(self) -> Dict[str, Any]:
        """健康檢查"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/health",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        return {"status": "healthy", "code": 200}
                    else:
                        return {"status": "unhealthy", "code": resp.status}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def get_models(self) -> List[str]:
        """獲取可用模型列表"""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/v1/models") as resp:
                data = await resp.json()
                return [m["id"] for m in data.get("data", [])]

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        stream: bool = False,
        **kwargs
    ) -> str:
        """生成文本"""
        async with aiohttp.ClientSession() as session:
            payload = {
                "model": self.config.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": stream,
                **kwargs
            }

            async with session.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=300)
            ) as resp:
                if resp.status != 200:
                    error = await resp.text()
                    raise Exception(f"API 錯誤: {resp.status} - {error}")

                data = await resp.json()
                return data["choices"][0]["message"]["content"]

    async def generate_stream(
        self,
        prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ):
        """串流生成文本"""
        async with aiohttp.ClientSession() as session:
            payload = {
                "model": self.config.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": True,
                **kwargs
            }

            async with session.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload
            ) as resp:
                async for line in resp.content:
                    line = line.decode("utf-8").strip()
                    if line.startswith("data: ") and line != "data: [DONE]":
                        data = json.loads(line[6:])
                        delta = data["choices"][0].get("delta", {})
                        if "content" in delta:
                            yield delta["content"]

    def stop(self) -> None:
        """停止服務器"""
        if self._process:
            self._process.terminate()
            try:
                self._process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._process.kill()
            print("服務器已停止")

    @property
    def is_running(self) -> bool:
        return self._started and self._process and self._process.poll() is None


# =============================================================================
# 部署決策工具
# =============================================================================

def deployment_decision(
    monthly_queries: int,
    avg_tokens_per_query: int,
    latency_requirement_ms: int,
    budget_monthly_usd: float
) -> Dict[str, Any]:
    """
    部署決策框架

    ‹1› 計算月度推理成本
    ‹2› 評估延遲需求
    ‹3› 給出建議
    """
    # ‹1› 估算雲端 API 成本（以 GPT-4o 為例）
    total_tokens = monthly_queries * avg_tokens_per_query
    api_cost_input = (total_tokens * 0.6) / 1_000_000 * 2.50  # 輸入 $2.50/M
    api_cost_output = (total_tokens * 0.4) / 1_000_000 * 10.00  # 輸出 $10.00/M
    api_cost = api_cost_input + api_cost_output

    # ‹2› 估算自建成本（以 4x A100 雲端租用為例）
    # 雲端租用：約 $4/hr × 4 GPU × 24hr × 30 days = $11,520/month
    self_hosted_cloud = 11520

    # 自購硬體（攤提 3 年）+ 電費
    # $60,000 / 36 months + $500/month 電費 = $2,167/month
    self_hosted_owned = 2167

    # ‹3› 決策邏輯
    result = {
        "monthly_queries": monthly_queries,
        "avg_tokens_per_query": avg_tokens_per_query,
        "total_tokens": total_tokens,
        "api_cost": round(api_cost, 2),
        "self_hosted_cloud_cost": self_hosted_cloud,
        "self_hosted_owned_cost": self_hosted_owned,
        "budget": budget_monthly_usd,
        "latency_requirement_ms": latency_requirement_ms
    }

    if latency_requirement_ms < 500:
        result["recommendation"] = "自建部署（低延遲需求）"
        result["reason"] = "低於 500ms 延遲需求，網路延遲不可接受"
    elif api_cost < budget_monthly_usd * 0.3:
        result["recommendation"] = "雲端 API"
        result["reason"] = f"API 成本 ${api_cost:.0f}/月 遠低於預算"
    elif api_cost < self_hosted_owned * 0.8:
        result["recommendation"] = "雲端 API"
        result["reason"] = f"API 成本 ${api_cost:.0f}/月 低於自建成本"
    elif api_cost < self_hosted_owned * 2:
        result["recommendation"] = "混合方案"
        result["reason"] = "API 與自建成本相近，建議混合使用"
    else:
        result["recommendation"] = "自建部署（自購硬體）"
        result["reason"] = f"API 成本 ${api_cost:.0f}/月 遠高於自建成本 ${self_hosted_owned}/月"

    return result


# =============================================================================
# 示範
# =============================================================================

async def demo():
    """示範模型服務器功能"""
    print("=" * 60)
    print("🚀 vLLM 模型服務器示範")
    print("=" * 60)

    # 顯示可用配置
    print("\n📋 可用配置:")
    for name, config in CONFIGS.items():
        memory = config.estimate_memory_gb()
        print(f"  {name}:")
        print(f"    模型: {config.model_name}")
        print(f"    GPU 數量: {config.tensor_parallel_size}")
        print(f"    最大上下文: {config.max_model_len}")
        print(f"    預估顯存: {memory:.1f} GB")

    # 部署決策示範
    print("\n" + "-" * 40)
    print("📊 部署決策分析")
    print("-" * 40)

    scenarios = [
        {"name": "小型團隊", "queries": 5000, "tokens": 2000, "latency": 5000, "budget": 500},
        {"name": "中型企業", "queries": 50000, "tokens": 5000, "latency": 3000, "budget": 5000},
        {"name": "大型企業", "queries": 500000, "tokens": 8000, "latency": 1000, "budget": 50000},
    ]

    for scenario in scenarios:
        print(f"\n場景: {scenario['name']}")
        result = deployment_decision(
            monthly_queries=scenario["queries"],
            avg_tokens_per_query=scenario["tokens"],
            latency_requirement_ms=scenario["latency"],
            budget_monthly_usd=scenario["budget"]
        )
        print(f"  月查詢量: {result['monthly_queries']:,}")
        print(f"  API 成本: ${result['api_cost']:,.0f}/月")
        print(f"  自建成本: ${result['self_hosted_owned_cost']:,}/月")
        print(f"  ✓ 建議: {result['recommendation']}")
        print(f"    原因: {result['reason']}")

    # 配置生成示範
    print("\n" + "-" * 40)
    print("⚙️ CLI 參數生成")
    print("-" * 40)

    config = CONFIGS["dev"]
    args = config.to_cli_args()
    print(f"\n開發環境啟動命令:")
    print(f"  python -m vllm.entrypoints.openai.api_server \\")
    for i, arg in enumerate(args):
        if arg.startswith("--"):
            print(f"    {arg}", end="")
        else:
            print(f" {arg} \\")
    print()


def main():
    parser = argparse.ArgumentParser(description="vLLM 模型服務器")
    parser.add_argument("--demo", action="store_true", help="執行示範")
    parser.add_argument("--config", type=str, choices=list(CONFIGS.keys()),
                        default="dev", help="使用預設配置")
    parser.add_argument("--start", action="store_true", help="啟動服務器")

    args = parser.parse_args()

    if args.start:
        config = CONFIGS[args.config]
        server = ModelServer(config)
        asyncio.run(server.start())
    else:
        asyncio.run(demo())


if __name__ == "__main__":
    main()
