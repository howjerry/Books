"""
预算感知限流器

根据预算使用情况自动调整 API 调用策略。
"""

from datetime import datetime, timedelta
from typing import Dict, Optional
from enum import Enum


class BudgetStatus(Enum):
    """预算状态"""
    NORMAL = "normal"          # 正常（< 80%）
    WARNING = "warning"        # 预警（80-95%）
    CRITICAL = "critical"      # 严重（95-100%）
    EXCEEDED = "exceeded"      # 超限（> 100%）


class ThrottleStrategy(Enum):
    """限流策略"""
    NONE = "none"              # 不限流
    REDUCE_RATE = "reduce"     # 降低调用频率
    DOWNGRADE_MODEL = "downgrade"  # 降级模型
    BLOCK = "block"            # 完全阻止


class BudgetThrottler:
    """
    预算感知限流器

    核心功能：
    1. 实时监控预算使用
    2. 自动调整调用策略
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
            monthly_budget: 月度预算（USD）
            warning_threshold: 预警阈值（默认 80%）
            critical_threshold: 严重阈值（默认 95%）
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
        检查当前预算状态

        Returns:
            预算状态
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
            requested_cost: 本次请求预估成本
            priority: 请求优先级（low, normal, high, critical）

        Returns:
            限流决策
        """
        status = self.check_budget_status()

        # 预估请求后的使用率
        projected_usage = self.current_month_usage + requested_cost
        projected_percentage = projected_usage / self.monthly_budget

        # 决策逻辑
        if status == BudgetStatus.EXCEEDED:
            if priority == "critical":
                return {
                    "allow": True,
                    "strategy": ThrottleStrategy.DOWNGRADE_MODEL,
                    "reason": "预算已超限，但允许关键请求使用降级模型",
                    "suggested_model": "claude-haiku-3-20250307"
                }
            else:
                return {
                    "allow": False,
                    "strategy": ThrottleStrategy.BLOCK,
                    "reason": f"预算已超限（{projected_percentage*100:.1f}%），阻止非关键请求"
                }

        elif status == BudgetStatus.CRITICAL:
            if priority in ["high", "critical"]:
                return {
                    "allow": True,
                    "strategy": ThrottleStrategy.REDUCE_RATE,
                    "reason": "预算临近上限，允许高优先级请求但降低频率"
                }
            else:
                return {
                    "allow": True,
                    "strategy": ThrottleStrategy.DOWNGRADE_MODEL,
                    "reason": "预算临近上限，建议降级模型",
                    "suggested_model": "claude-haiku-3-20250307"
                }

        elif status == BudgetStatus.WARNING:
            return {
                "allow": True,
                "strategy": ThrottleStrategy.REDUCE_RATE,
                "reason": f"预算使用 {projected_percentage*100:.1f}%，建议降低调用频率"
            }

        else:
            return {
                "allow": True,
                "strategy": ThrottleStrategy.NONE,
                "reason": "预算充足"
            }

    def record_usage(self, cost: float):
        """
        记录使用情况

        Args:
            cost: 本次请求成本
        """
        now = datetime.utcnow()

        self.usage_history.append({
            "timestamp": now,
            "cost": cost
        })

        self.current_month_usage += cost

        # 清理过期记录（保留本月数据）
        month_start = datetime(now.year, now.month, 1)
        self.usage_history = [
            record for record in self.usage_history
            if record["timestamp"] >= month_start
        ]

    def get_sliding_window_usage(self, minutes: int = 60) -> Dict:
        """
        获取滑动窗口使用情况

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
        获取预算汇总

        Returns:
            预算使用汇总
        """
        status = self.check_budget_status()
        usage_percentage = (self.current_month_usage / self.monthly_budget) * 100
        remaining_budget = self.monthly_budget - self.current_month_usage

        # 计算预计耗尽日期
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
        获取优化建议

        Args:
            status: 当前预算状态

        Returns:
            建议列表
        """
        recommendations = []

        if status == BudgetStatus.EXCEEDED:
            recommendations.append("立即停止非关键调用")
            recommendations.append("审查所有进行中的任务")
            recommendations.append("考虑申请额外预算")

        elif status == BudgetStatus.CRITICAL:
            recommendations.append("启用 Prompt Caching 以节省成本")
            recommendations.append("降级为更便宜的模型（Haiku）")
            recommendations.append("减少非必要的 API 调用")
            recommendations.append("启用批量处理")

        elif status == BudgetStatus.WARNING:
            recommendations.append("监控使用趋势")
            recommendations.append("优化提示词以减少 Token 使用")
            recommendations.append("考虑启用缓存")

        else:
            recommendations.append("预算使用正常")

        return recommendations

    def reset_monthly_budget(self):
        """重置月度预算（在新月份开始时调用）"""
        self.current_month_usage = 0.0
        self.usage_history = []


# 使用示例
def example_usage():
    """
    预算限流器使用示例
    """
    # 创建限流器（月预算 $1000）
    throttler = BudgetThrottler(
        monthly_budget=1000.0,
        warning_threshold=0.8,
        critical_threshold=0.95
    )

    # 模拟一些请求
    print("=== 模拟 API 请求 ===\n")

    # 请求 1：正常请求
    decision = throttler.should_throttle(requested_cost=5.0, priority="normal")
    print(f"请求 1: {decision}")
    if decision["allow"]:
        throttler.record_usage(5.0)

    # 模拟使用了 900 美元
    throttler.current_month_usage = 900.0

    # 请求 2：预算预警状态
    decision = throttler.should_throttle(requested_cost=10.0, priority="normal")
    print(f"\n请求 2 (预算 90%): {decision}")

    # 模拟使用了 980 美元
    throttler.current_month_usage = 980.0

    # 请求 3：预算严重状态
    decision = throttler.should_throttle(requested_cost=10.0, priority="low")
    print(f"\n请求 3 (预算 98%): {decision}")

    # 请求 4：关键请求
    decision = throttler.should_throttle(requested_cost=10.0, priority="critical")
    print(f"\n请求 4 (关键请求): {decision}")

    # 查看预算汇总
    summary = throttler.get_budget_summary()
    print(f"\n=== 预算汇总 ===")
    print(f"月度预算: ${summary['monthly_budget']}")
    print(f"已使用: ${summary['current_usage']} ({summary['usage_percentage']}%)")
    print(f"剩余: ${summary['remaining_budget']}")
    print(f"状态: {summary['status']}")
    print(f"\n建议:")
    for rec in summary['recommendations']:
        print(f"  - {rec}")


if __name__ == "__main__":
    example_usage()
