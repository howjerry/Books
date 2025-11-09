"""
預算感知限流器

根据預算使用情況自动调整 API 呼叫策略。
"""

from datetime import datetime, timedelta
from typing import Dict, Optional
from enum import Enum


class BudgetStatus(Enum):
    """預算狀態"""
    NORMAL = "normal"          # 正常（< 80%）
    WARNING = "warning"        # 預警（80-95%）
    CRITICAL = "critical"      # 嚴重（95-100%）
    EXCEEDED = "exceeded"      # 超限（> 100%）


class ThrottleStrategy(Enum):
    """限流策略"""
    NONE = "none"              # 不限流
    REDUCE_RATE = "reduce"     # 降低呼叫頻率
    DOWNGRADE_MODEL = "downgrade"  # 降级模型
    BLOCK = "block"            # 完全阻止


class BudgetThrottler:
    """
    預算感知限流器

    核心功能：
    1. 实时監控預算使用
    2. 自动调整呼叫策略
    3. 滑动窗口限流
    4. 优先级管理
    """

    def __init__(
        self,
        monthly_budget: float,
        warning_threshold: float = 0.8,
        critical_threshold: float = 0.95
    ):
        """
        初始化限流器

        Args:
            monthly_budget: 月度預算（USD）
            warning_threshold: 預警閾值（默認 80%）
            critical_threshold: 嚴重閾值（默認 95%）
        """
        self.monthly_budget = monthly_budget
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold

        # 使用统计（滑动窗口）
        self.usage_history: List[Dict] = []
        self.current_month_usage = 0.0

        # 限流配置
        self.rate_limits = {
            BudgetStatus.NORMAL: {"max_requests_per_minute": 100},
            BudgetStatus.WARNING: {"max_requests_per_minute": 50},
            BudgetStatus.CRITICAL: {"max_requests_per_minute": 10},
            BudgetStatus.EXCEEDED: {"max_requests_per_minute": 0}
        }

    def check_budget_status(self) -> BudgetStatus:
        """
        檢查當前預算狀態

        Returns:
            預算狀態
        """
        usage_percentage = self.current_month_usage / self.monthly_budget

        if usage_percentage >= 1.0:
            return BudgetStatus.EXCEEDED
        elif usage_percentage >= self.critical_threshold:
            return BudgetStatus.CRITICAL
        elif usage_percentage >= self.warning_threshold:
            return BudgetStatus.WARNING
        else:
            return BudgetStatus.NORMAL

    def should_throttle(
        self,
        requested_cost: float,
        priority: str = "normal"
    ) -> Dict:
        """
        判断是否需要限流

        Args:
            requested_cost: 本次請求预估成本
            priority: 請求优先级（low, normal, high, critical）

        Returns:
            限流决策
        """
        status = self.check_budget_status()

        # 预估請求后的使用率
        projected_usage = self.current_month_usage + requested_cost
        projected_percentage = projected_usage / self.monthly_budget

        # 决策逻辑
        if status == BudgetStatus.EXCEEDED:
            if priority == "critical":
                return {
                    "allow": True,
                    "strategy": ThrottleStrategy.DOWNGRADE_MODEL,
                    "reason": "預算已超限，但允许關鍵請求使用降级模型",
                    "suggested_model": "claude-haiku-3-20250307"
                }
            else:
                return {
                    "allow": False,
                    "strategy": ThrottleStrategy.BLOCK,
                    "reason": f"預算已超限（{projected_percentage*100:.1f}%），阻止非關鍵請求"
                }

        elif status == BudgetStatus.CRITICAL:
            if priority in ["high", "critical"]:
                return {
                    "allow": True,
                    "strategy": ThrottleStrategy.REDUCE_RATE,
                    "reason": "預算临近上限，允许高优先级請求但降低頻率"
                }
            else:
                return {
                    "allow": True,
                    "strategy": ThrottleStrategy.DOWNGRADE_MODEL,
                    "reason": "預算临近上限，建議降级模型",
                    "suggested_model": "claude-haiku-3-20250307"
                }

        elif status == BudgetStatus.WARNING:
            return {
                "allow": True,
                "strategy": ThrottleStrategy.REDUCE_RATE,
                "reason": f"預算使用 {projected_percentage*100:.1f}%，建議降低呼叫頻率"
            }

        else:
            return {
                "allow": True,
                "strategy": ThrottleStrategy.NONE,
                "reason": "預算充足"
            }

    def record_usage(self, cost: float):
        """
        記錄使用情況

        Args:
            cost: 本次請求成本
        """
        now = datetime.utcnow()

        self.usage_history.append({
            "timestamp": now,
            "cost": cost
        })

        self.current_month_usage += cost

        # 清理過期記錄（保留本月數據）
        month_start = datetime(now.year, now.month, 1)
        self.usage_history = [
            record for record in self.usage_history
            if record["timestamp"] >= month_start
        ]

    def get_sliding_window_usage(self, minutes: int = 60) -> Dict:
        """
        獲取滑动窗口使用情況

        Args:
            minutes: 窗口大小（分钟）

        Returns:
            窗口内的使用统计
        """
        now = datetime.utcnow()
        window_start = now - timedelta(minutes=minutes)

        window_records = [
            record for record in self.usage_history
            if record["timestamp"] >= window_start
        ]

        total_cost = sum(r["cost"] for r in window_records)
        request_count = len(window_records)

        return {
            "window_minutes": minutes,
            "request_count": request_count,
            "total_cost": round(total_cost, 4),
            "avg_cost_per_request": round(total_cost / request_count, 4) if request_count > 0 else 0,
            "requests_per_minute": round(request_count / minutes, 2)
        }

    def get_budget_summary(self) -> Dict:
        """
        獲取預算匯總

        Returns:
            預算使用匯總
        """
        status = self.check_budget_status()
        usage_percentage = (self.current_month_usage / self.monthly_budget) * 100
        remaining_budget = self.monthly_budget - self.current_month_usage

        # 計算预计耗尽日期
        now = datetime.utcnow()
        days_passed = now.day
        if days_passed > 0 and self.current_month_usage > 0:
            daily_burn_rate = self.current_month_usage / days_passed
            days_until_exhausted = remaining_budget / daily_burn_rate if daily_burn_rate > 0 else float('inf')
        else:
            days_until_exhausted = float('inf')

        return {
            "monthly_budget": self.monthly_budget,
            "current_usage": round(self.current_month_usage, 2),
            "remaining_budget": round(remaining_budget, 2),
            "usage_percentage": round(usage_percentage, 1),
            "status": status.value,
            "days_until_exhausted": int(days_until_exhausted) if days_until_exhausted != float('inf') else None,
            "recommendations": self._get_recommendations(status)
        }

    def _get_recommendations(self, status: BudgetStatus) -> List[str]:
        """
        獲取優化建議

        Args:
            status: 當前預算狀態

        Returns:
            建議列表
        """
        recommendations = []

        if status == BudgetStatus.EXCEEDED:
            recommendations.append("立即停止非關鍵呼叫")
            recommendations.append("審查所有進行中的任务")
            recommendations.append("考慮申请额外預算")

        elif status == BudgetStatus.CRITICAL:
            recommendations.append("啟用 Prompt Caching 以節省成本")
            recommendations.append("降级为更便宜的模型（Haiku）")
            recommendations.append("减少非必要的 API 呼叫")
            recommendations.append("啟用批量處理")

        elif status == BudgetStatus.WARNING:
            recommendations.append("監控使用趋势")
            recommendations.append("優化提示词以减少 Token 使用")
            recommendations.append("考慮啟用緩存")

        else:
            recommendations.append("預算使用正常")

        return recommendations

    def reset_monthly_budget(self):
        """重置月度預算（在新月份開始時呼叫）"""
        self.current_month_usage = 0.0
        self.usage_history = []


# 使用示例
def example_usage():
    """
    預算限流器使用示例
    """
    # 創建限流器（月預算 $1000）
    throttler = BudgetThrottler(
        monthly_budget=1000.0,
        warning_threshold=0.8,
        critical_threshold=0.95
    )

    # 模拟一些請求
    print("=== 模拟 API 請求 ===\n")

    # 請求 1：正常請求
    decision = throttler.should_throttle(requested_cost=5.0, priority="normal")
    print(f"請求 1: {decision}")
    if decision["allow"]:
        throttler.record_usage(5.0)

    # 模拟使用了 900 美元
    throttler.current_month_usage = 900.0

    # 請求 2：預算預警狀態
    decision = throttler.should_throttle(requested_cost=10.0, priority="normal")
    print(f"\n請求 2 (預算 90%): {decision}")

    # 模拟使用了 980 美元
    throttler.current_month_usage = 980.0

    # 請求 3：預算嚴重狀態
    decision = throttler.should_throttle(requested_cost=10.0, priority="low")
    print(f"\n請求 3 (預算 98%): {decision}")

    # 請求 4：關鍵請求
    decision = throttler.should_throttle(requested_cost=10.0, priority="critical")
    print(f"\n請求 4 (關鍵請求): {decision}")

    # 查看預算匯總
    summary = throttler.get_budget_summary()
    print(f"\n=== 預算匯總 ===")
    print(f"月度預算: ${summary['monthly_budget']}")
    print(f"已使用: ${summary['current_usage']} ({summary['usage_percentage']}%)")
    print(f"剩余: ${summary['remaining_budget']}")
    print(f"狀態: {summary['status']}")
    print(f"\n建議:")
    for rec in summary['recommendations']:
        print(f"  - {rec}")


if __name__ == "__main__":
    example_usage()
