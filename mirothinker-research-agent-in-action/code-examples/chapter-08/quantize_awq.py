#!/usr/bin/env python3
"""
深度研究代理人實戰 - 第 8 章：環境搭建與部署
AWQ 量化工具

這個模組實現了 AWQ 量化功能：
1. 模型量化
2. 效果評估
3. 基準測試

使用方式：
    python quantize_awq.py --demo
    python quantize_awq.py --model Qwen/Qwen2.5-7B-Instruct --output ./qwen-7b-awq
"""

import argparse
import asyncio
import json
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

load_dotenv()


# =============================================================================
# 資料結構
# =============================================================================

@dataclass
class QuantizationConfig:
    """量化配置"""
    zero_point: bool = True          # 使用零點量化
    q_group_size: int = 128          # 量化群組大小
    w_bit: int = 4                   # 權重位數
    version: str = "GEMM"            # 核心版本 (GEMM 或 GEMV)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "zero_point": self.zero_point,
            "q_group_size": self.q_group_size,
            "w_bit": self.w_bit,
            "version": self.version
        }


@dataclass
class QuantizationResult:
    """量化結果"""
    model_path: str
    output_path: str
    original_size_gb: float
    quantized_size_gb: float
    compression_ratio: float
    quantization_time_seconds: float


@dataclass
class BenchmarkResult:
    """基準測試結果"""
    model_name: str
    quantization: str
    latency_p50_ms: float
    latency_p99_ms: float
    throughput_tokens_per_sec: float
    memory_usage_gb: float
    quality_score: float


# =============================================================================
# 量化器
# =============================================================================

class AWQQuantizer:
    """
    AWQ 量化器

    ‹1› 載入原始模型
    ‹2› 執行量化
    ‹3› 保存量化模型
    """

    def __init__(self, config: Optional[QuantizationConfig] = None):
        self.config = config or QuantizationConfig()

    def quantize(
        self,
        model_path: str,
        output_path: str,
        calibration_data: Optional[List[str]] = None
    ) -> QuantizationResult:
        """
        執行 AWQ 量化

        ‹1› 載入模型和 tokenizer
        ‹2› 使用校準資料進行量化
        ‹3› 保存量化後的模型
        """
        try:
            from awq import AutoAWQForCausalLM
            from transformers import AutoTokenizer
        except ImportError:
            raise ImportError(
                "請安裝 awq 套件: pip install autoawq transformers"
            )

        print(f"=== AWQ 量化 ===")
        print(f"原始模型: {model_path}")
        print(f"輸出路徑: {output_path}")
        print(f"配置: {self.config.to_dict()}")

        start_time = time.time()

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
        model.quantize(
            tokenizer,
            quant_config=self.config.to_dict()
        )

        # ‹3› 保存
        print("\n[3/3] 保存量化模型...")
        os.makedirs(output_path, exist_ok=True)
        model.save_quantized(output_path)
        tokenizer.save_pretrained(output_path)

        end_time = time.time()

        # 計算壓縮效果
        original_size = self._get_model_size(model_path)
        quantized_size = self._get_model_size(output_path)
        compression_ratio = original_size / quantized_size if quantized_size > 0 else 0

        print(f"\n✓ 量化完成!")
        print(f"  原始大小: {original_size:.1f} GB")
        print(f"  量化後: {quantized_size:.1f} GB")
        print(f"  壓縮比: {compression_ratio:.1f}x")
        print(f"  耗時: {end_time - start_time:.0f} 秒")

        return QuantizationResult(
            model_path=model_path,
            output_path=output_path,
            original_size_gb=original_size,
            quantized_size_gb=quantized_size,
            compression_ratio=compression_ratio,
            quantization_time_seconds=end_time - start_time
        )

    def _get_model_size(self, model_path: str) -> float:
        """獲取模型大小（GB）"""
        total_size = 0
        if os.path.isdir(model_path):
            for f in os.listdir(model_path):
                if f.endswith(('.bin', '.safetensors', '.pt')):
                    total_size += os.path.getsize(os.path.join(model_path, f))
        return total_size / 1e9


# =============================================================================
# 模擬量化器（用於示範）
# =============================================================================

class MockQuantizer:
    """模擬量化器（不需要實際安裝 AWQ）"""

    def __init__(self, config: Optional[QuantizationConfig] = None):
        self.config = config or QuantizationConfig()

    def quantize(
        self,
        model_path: str,
        output_path: str,
        calibration_data: Optional[List[str]] = None
    ) -> QuantizationResult:
        """模擬量化過程"""
        print(f"=== AWQ 量化（模擬模式）===")
        print(f"原始模型: {model_path}")
        print(f"輸出路徑: {output_path}")
        print(f"配置: {self.config.to_dict()}")

        # 根據模型名稱估算大小
        if "72B" in model_path or "72b" in model_path:
            original_size = 144.0
        elif "32B" in model_path or "32b" in model_path:
            original_size = 64.0
        elif "14B" in model_path or "14b" in model_path:
            original_size = 28.0
        elif "7B" in model_path or "7b" in model_path:
            original_size = 14.0
        else:
            original_size = 14.0

        # 4-bit 量化約 1/4 大小
        quantized_size = original_size * 0.25
        compression_ratio = original_size / quantized_size

        print(f"\n模擬結果:")
        print(f"  原始大小: {original_size:.1f} GB")
        print(f"  量化後: {quantized_size:.1f} GB")
        print(f"  壓縮比: {compression_ratio:.1f}x")

        return QuantizationResult(
            model_path=model_path,
            output_path=output_path,
            original_size_gb=original_size,
            quantized_size_gb=quantized_size,
            compression_ratio=compression_ratio,
            quantization_time_seconds=0
        )


# =============================================================================
# 基準測試
# =============================================================================

class QuantizationBenchmark:
    """
    量化效果基準測試

    ‹1› 延遲測試
    ‹2› 吞吐量測試
    ‹3› 品質評估
    """

    # 測試用例
    TEST_PROMPTS = [
        "分析 NVIDIA 在 AI 晶片市場的競爭優勢",
        "解釋 Transformer 架構的自注意力機制",
        "比較 Python 和 Rust 在系統編程中的優缺點",
        "評估深度學習在醫療影像診斷中的應用前景",
        "描述分散式系統中的 CAP 定理及其實際影響",
    ]

    def __init__(self, api_url: str = "http://localhost:8000"):
        self.api_url = api_url

    async def benchmark(
        self,
        model_name: str,
        quantization: str = "none",
        num_runs: int = 10
    ) -> BenchmarkResult:
        """執行基準測試"""
        import aiohttp

        latencies = []
        total_tokens = 0

        async with aiohttp.ClientSession() as session:
            for i in range(num_runs):
                prompt = self.TEST_PROMPTS[i % len(self.TEST_PROMPTS)]

                start = time.perf_counter()

                payload = {
                    "model": model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 256,
                    "temperature": 0.7
                }

                async with session.post(
                    f"{self.api_url}/v1/chat/completions",
                    json=payload
                ) as resp:
                    data = await resp.json()

                end = time.perf_counter()
                latencies.append((end - start) * 1000)
                total_tokens += data.get("usage", {}).get("total_tokens", 0)

        # 計算統計
        latencies.sort()
        p50 = latencies[len(latencies) // 2]
        p99 = latencies[int(len(latencies) * 0.99)] if len(latencies) >= 100 else latencies[-1]

        total_time = sum(latencies) / 1000
        throughput = total_tokens / total_time if total_time > 0 else 0

        return BenchmarkResult(
            model_name=model_name,
            quantization=quantization,
            latency_p50_ms=p50,
            latency_p99_ms=p99,
            throughput_tokens_per_sec=throughput,
            memory_usage_gb=0.0,
            quality_score=0.0
        )

    def generate_report(self, results: List[BenchmarkResult]) -> str:
        """生成基準測試報告"""
        lines = [
            "=" * 70,
            "量化效果基準測試報告",
            "=" * 70,
            "",
            f"{'模型':<30} {'量化':<10} {'P50(ms)':<10} {'P99(ms)':<10} {'吞吐量':<15}",
            "-" * 70
        ]

        for r in results:
            lines.append(
                f"{r.model_name:<30} {r.quantization:<10} "
                f"{r.latency_p50_ms:<10.1f} {r.latency_p99_ms:<10.1f} "
                f"{r.throughput_tokens_per_sec:<15.1f}"
            )

        lines.append("-" * 70)
        return "\n".join(lines)


# =============================================================================
# 量化效果對比表
# =============================================================================

QUANTIZATION_COMPARISON = {
    "FP16": {
        "precision": "16-bit",
        "compression": "2x",
        "quality_loss": "~0%",
        "use_case": "標準推理"
    },
    "INT8": {
        "precision": "8-bit",
        "compression": "4x",
        "quality_loss": "~1%",
        "use_case": "通用部署"
    },
    "AWQ": {
        "precision": "4-bit",
        "compression": "8x",
        "quality_loss": "~2%",
        "use_case": "資源受限"
    },
    "GPTQ": {
        "precision": "4-bit",
        "compression": "8x",
        "quality_loss": "~3%",
        "use_case": "資源受限"
    },
    "GGUF": {
        "precision": "2-8 bit",
        "compression": "4-16x",
        "quality_loss": "1-5%",
        "use_case": "CPU/邊緣設備"
    }
}


def print_comparison_table():
    """打印量化方法對比表"""
    print("\n" + "=" * 70)
    print("量化方法對比")
    print("=" * 70)
    print(f"{'方法':<10} {'精度':<12} {'壓縮比':<10} {'品質損失':<10} {'適用場景':<15}")
    print("-" * 70)

    for method, info in QUANTIZATION_COMPARISON.items():
        print(
            f"{method:<10} {info['precision']:<12} {info['compression']:<10} "
            f"{info['quality_loss']:<10} {info['use_case']:<15}"
        )

    print("-" * 70)


# =============================================================================
# 示範
# =============================================================================

async def demo():
    """示範量化功能"""
    print("=" * 60)
    print("🔧 AWQ 量化工具示範")
    print("=" * 60)

    # 顯示量化方法對比
    print_comparison_table()

    # 模擬量化不同大小的模型
    print("\n" + "-" * 40)
    print("📊 模型量化效果估算")
    print("-" * 40)

    models = [
        ("Qwen/Qwen2.5-7B-Instruct", "7B"),
        ("Qwen/Qwen2.5-14B-Instruct", "14B"),
        ("Qwen/Qwen2.5-32B-Instruct", "32B"),
        ("Qwen/Qwen2.5-72B-Instruct", "72B"),
    ]

    quantizer = MockQuantizer()

    print(f"\n{'模型':<35} {'原始大小':<12} {'量化後':<12} {'壓縮比':<10}")
    print("-" * 70)

    for model_path, size in models:
        result = quantizer.quantize(model_path, f"./output-{size}-awq")
        print(
            f"{model_path:<35} {result.original_size_gb:<12.1f} GB "
            f"{result.quantized_size_gb:<12.1f} GB {result.compression_ratio:<10.1f}x"
        )

    # 顯示量化配置選項
    print("\n" + "-" * 40)
    print("⚙️ 量化配置選項")
    print("-" * 40)

    configs = [
        QuantizationConfig(w_bit=4, q_group_size=128, version="GEMM"),
        QuantizationConfig(w_bit=4, q_group_size=64, version="GEMM"),
        QuantizationConfig(w_bit=8, q_group_size=128, version="GEMM"),
    ]

    for i, config in enumerate(configs, 1):
        print(f"\n配置 {i}:")
        for key, value in config.to_dict().items():
            print(f"  {key}: {value}")


def main():
    parser = argparse.ArgumentParser(description="AWQ 量化工具")
    parser.add_argument("--demo", action="store_true", help="執行示範")
    parser.add_argument("--model", type=str, help="原始模型路徑")
    parser.add_argument("--output", type=str, help="輸出路徑")
    parser.add_argument("--bits", type=int, default=4, help="量化位數")
    parser.add_argument("--mock", action="store_true", help="使用模擬模式")

    args = parser.parse_args()

    if args.model and args.output:
        config = QuantizationConfig(w_bit=args.bits)
        if args.mock:
            quantizer = MockQuantizer(config)
        else:
            quantizer = AWQQuantizer(config)
        quantizer.quantize(args.model, args.output)
    else:
        asyncio.run(demo())


if __name__ == "__main__":
    main()
