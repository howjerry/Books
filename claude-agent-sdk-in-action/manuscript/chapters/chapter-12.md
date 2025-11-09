# 第 12 章：成本优化与资源管理 - 打造高效益的 Agent 系统

## 本章内容概览

- 理解 AI 成本的构成与挑战
- 建立多维度成本追踪系统
- 实现 Model Router 智能选择
- 优化 Prompt Caching 策略
- 设计预算管理与自动限流
- 掌握 Token 优化技巧
- 建立 ROI 计算框架
- 完成一个企业级成本管理系统

---

## 12.1 场景：失控的 AI 成本

### 真实挑战

你是 TechCorp 的 CFO，收到了一份令人震惊的 Claude API 账单：

```
Anthropic API 月度账单
账期：2024 年 10 月

总费用：US$ 127,850

详细分类：
- Claude Opus：    US$ 89,450 (70%)
- Claude Sonnet：  US$ 32,100 (25%)
- Claude Haiku：   US$ 6,300 (5%)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
对比：
- 9 月账单：US$ 38,200
- 增长率：+235%
- 年化成本：US$ 1,534,200
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️  预警：
按当前增长率，12 月预计达 US$ 285,000
```

**调查发现的问题**：

```python
# ❌ 问题 1：盲目使用最贵的模型
# agent_service.py
def create_agent():
    return Agent(
        model="claude-opus-4-20250514",  # 💰 总是用 Opus
        ...
    )

# 实际需求：80% 的请求用 Haiku 就够了
# 成本差异：Opus ($75/1M output) vs Haiku ($1.25/1M output) = 60倍


# ❌ 问题 2：重复计算相同内容
# customer_service_agent.py
def handle_customer_query(query: str):
    # 每次都重新分析完整的 FAQ 数据库（20,000 tokens）
    faq_content = load_faq_database()  # 每次加载

    prompt = f"""
    FAQ 数据库：
    {faq_content}  # 💰 每次都包含完整 FAQ

    客户问题：{query}
    """

    response = client.messages.create(...)
    return response

# 浪费：20,000 tokens × 每天 5,000 次请求 = 每天 100M tokens
# 成本：US$ 300/天 × 30 天 = US$ 9,000/月（可完全避免）


# ❌ 问题 3：没有预算控制
# 任何开发者都可以无限制调用 API
# 没有成本追踪
# 没有预警机制
# 没有自动限流


# ❌ 问题 4：Token 使用低效
def analyze_document(doc: str):
    # 发送完整文档，即使只需要摘要
    prompt = f"""
    请分析以下文档并提供 3 句话摘要：

    {doc}  # 💰 50,000 tokens 的完整文档
    """

    # 更好的做法：先用 Haiku 提取关键信息，再用 Sonnet 总结
    # 成本可降低 80%
```

**财务影响**：
- 月度成本：US$ 127,850
- 预算超支：+355%（预算 US$ 28,000）
- ROI 未知：无法证明投入产出比
- CFO 要求：立即降低成本 50%+

---

## 12.2 多维度成本追踪系统

### 12.2.1 成本数据模型

```python
# cost_tracking/models.py
from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, Index
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from typing import Optional

Base = declarative_base()

class APIUsageLog(Base):
    """
    ‹1› API 使用日志表

    记录每次 API 调用的详细信息，用于成本分析
    """
    __tablename__ = "api_usage_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 时间信息
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # 归属信息
    user_id = Column(String(100), nullable=False, index=True)
    team_id = Column(String(100), nullable=False, index=True)
    project_id = Column(String(100), nullable=False, index=True)
    agent_id = Column(String(100), nullable=False, index=True)

    # 模型信息
    model = Column(String(50), nullable=False, index=True)

    # Token 使用量
    input_tokens = Column(Integer, nullable=False)
    output_tokens = Column(Integer, nullable=False)
    cached_tokens = Column(Integer, default=0)  # Prompt caching

    # 成本（USD）
    input_cost = Column(Float, nullable=False)
    output_cost = Column(Float, nullable=False)
    total_cost = Column(Float, nullable=False, index=True)

    # 性能指标
    latency_ms = Column(Integer)
    success = Column(Boolean, nullable=False)
    error_type = Column(String(100))

    # 业务标签
    tags = Column(JSON)  # {"environment": "production", "feature": "customer-service"}

    # 索引优化
    __table_args__ = (
        Index('idx_team_date', 'team_id', 'timestamp'),
        Index('idx_project_model', 'project_id', 'model'),
    )


class CostBudget(Base):
    """
    ‹2› 成本预算表
    """
    __tablename__ = "cost_budgets"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 预算维度
    dimension = Column(String(20), nullable=False)  # team, project, user
    dimension_id = Column(String(100), nullable=False)

    # 预算金额（USD）
    monthly_budget = Column(Float, nullable=False)
    daily_budget = Column(Float, nullable=False)

    # 当前使用
    current_month_spending = Column(Float, default=0)
    current_day_spending = Column(Float, default=0)

    # 预警阈值（百分比）
    warning_threshold = Column(Float, default=0.8)  # 80%
    critical_threshold = Column(Float, default=0.95)  # 95%

    # 限流设置
    auto_throttle = Column(Boolean, default=True)
    throttle_rate = Column(Float, default=0.5)  # 降速 50%

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_dimension', 'dimension', 'dimension_id'),
    )
```

**关键注解说明**：
- **‹1›** `APIUsageLog`：记录每次 API 调用的完整信息，支持多维度分析
- **‹2›** `CostBudget`：预算管理表，支持团队/项目/用户级别的预算控制

### 12.2.2 成本追踪服务

```python
# cost_tracking/service.py
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import logging

from .models import APIUsageLog, CostBudget

logger = logging.getLogger(__name__)


class CostTrackingService:
    """
    ‹1› 成本追踪服务

    核心功能：
    1. 记录 API 使用
    2. 计算成本
    3. 更新预算
    4. 触发预警
    """

    # 模型定价（每百万 tokens，USD）
    MODEL_PRICING = {
        "claude-opus-4-20250514": {
            "input": 15.00,
            "output": 75.00
        },
        "claude-sonnet-4-20250514": {
            "input": 3.00,
            "output": 15.00
        },
        "claude-haiku-3-20250307": {
            "input": 0.25,
            "output": 1.25
        }
    }

    def __init__(self, db: Session):
        self.db = db

    def log_api_usage(
        self,
        user_id: str,
        team_id: str,
        project_id: str,
        agent_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int = 0,
        latency_ms: int = None,
        success: bool = True,
        error_type: str = None,
        tags: Dict[str, str] = None
    ) -> APIUsageLog:
        """
        ‹2› 记录 API 使用并计算成本
        """
        # 计算成本
        pricing = self.MODEL_PRICING.get(model)
        if not pricing:
            logger.warning(f"Unknown model: {model}, using Sonnet pricing")
            pricing = self.MODEL_PRICING["claude-sonnet-4-20250514"]

        # 考虑 Prompt Caching 的折扣
        effective_input_tokens = input_tokens - cached_tokens
        cached_input_tokens = cached_tokens

        input_cost = (effective_input_tokens / 1_000_000) * pricing["input"]

        # Cached tokens 通常是 90% 折扣
        cached_cost = (cached_input_tokens / 1_000_000) * pricing["input"] * 0.1

        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        total_cost = input_cost + cached_cost + output_cost

        # 创建日志记录
        log = APIUsageLog(
            user_id=user_id,
            team_id=team_id,
            project_id=project_id,
            agent_id=agent_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_tokens=cached_tokens,
            input_cost=input_cost + cached_cost,
            output_cost=output_cost,
            total_cost=total_cost,
            latency_ms=latency_ms,
            success=success,
            error_type=error_type,
            tags=tags or {}
        )

        self.db.add(log)
        self.db.commit()

        # 更新预算使用量
        self._update_budget_spending(team_id, project_id, user_id, total_cost)

        # 检查是否需要预警
        self._check_budget_alerts(team_id, project_id, user_id)

        return log

    def get_cost_summary(
        self,
        dimension: str,  # team, project, user
        dimension_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        ‹3› 获取成本摘要
        """
        query = self.db.query(APIUsageLog).filter(
            APIUsageLog.timestamp >= start_date,
            APIUsageLog.timestamp < end_date
        )

        if dimension == "team":
            query = query.filter(APIUsageLog.team_id == dimension_id)
        elif dimension == "project":
            query = query.filter(APIUsageLog.project_id == dimension_id)
        elif dimension == "user":
            query = query.filter(APIUsageLog.user_id == dimension_id)

        logs = query.all()

        # 计算总计
        total_cost = sum(log.total_cost for log in logs)
        total_requests = len(logs)
        total_input_tokens = sum(log.input_tokens for log in logs)
        total_output_tokens = sum(log.output_tokens for log in logs)
        total_cached_tokens = sum(log.cached_tokens for log in logs)

        # 按模型分组
        by_model = {}
        for log in logs:
            if log.model not in by_model:
                by_model[log.model] = {
                    "requests": 0,
                    "cost": 0,
                    "input_tokens": 0,
                    "output_tokens": 0
                }
            by_model[log.model]["requests"] += 1
            by_model[log.model]["cost"] += log.total_cost
            by_model[log.model]["input_tokens"] += log.input_tokens
            by_model[log.model]["output_tokens"] += log.output_tokens

        # 成功率
        successful_requests = sum(1 for log in logs if log.success)
        success_rate = successful_requests / total_requests if total_requests > 0 else 0

        # 平均延迟
        latencies = [log.latency_ms for log in logs if log.latency_ms]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0

        # Caching 效率
        caching_rate = total_cached_tokens / total_input_tokens if total_input_tokens > 0 else 0

        return {
            "summary": {
                "total_cost": total_cost,
                "total_requests": total_requests,
                "total_input_tokens": total_input_tokens,
                "total_output_tokens": total_output_tokens,
                "total_cached_tokens": total_cached_tokens,
                "success_rate": success_rate,
                "avg_latency_ms": avg_latency,
                "caching_rate": caching_rate,
                "avg_cost_per_request": total_cost / total_requests if total_requests > 0 else 0
            },
            "by_model": by_model,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": (end_date - start_date).days
            }
        }

    def _update_budget_spending(
        self,
        team_id: str,
        project_id: str,
        user_id: str,
        cost: float
    ):
        """更新预算使用量"""
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # 更新团队预算
        team_budget = self.db.query(CostBudget).filter_by(
            dimension="team",
            dimension_id=team_id
        ).first()

        if team_budget:
            team_budget.current_month_spending += cost
            team_budget.current_day_spending += cost

        # 更新项目预算
        project_budget = self.db.query(CostBudget).filter_by(
            dimension="project",
            dimension_id=project_id
        ).first()

        if project_budget:
            project_budget.current_month_spending += cost
            project_budget.current_day_spending += cost

        self.db.commit()

    def _check_budget_alerts(
        self,
        team_id: str,
        project_id: str,
        user_id: str
    ):
        """
        ‹4› 检查预算并触发预警
        """
        budgets = self.db.query(CostBudget).filter(
            ((CostBudget.dimension == "team") & (CostBudget.dimension_id == team_id)) |
            ((CostBudget.dimension == "project") & (CostBudget.dimension_id == project_id))
        ).all()

        for budget in budgets:
            # 检查月度预算
            month_usage_rate = budget.current_month_spending / budget.monthly_budget

            if month_usage_rate >= budget.critical_threshold:
                self._send_alert(
                    budget=budget,
                    level="CRITICAL",
                    usage_rate=month_usage_rate,
                    period="monthly"
                )
            elif month_usage_rate >= budget.warning_threshold:
                self._send_alert(
                    budget=budget,
                    level="WARNING",
                    usage_rate=month_usage_rate,
                    period="monthly"
                )

            # 检查日度预算
            day_usage_rate = budget.current_day_spending / budget.daily_budget

            if day_usage_rate >= budget.critical_threshold:
                self._send_alert(
                    budget=budget,
                    level="CRITICAL",
                    usage_rate=day_usage_rate,
                    period="daily"
                )

    def _send_alert(
        self,
        budget: CostBudget,
        level: str,
        usage_rate: float,
        period: str
    ):
        """发送预警通知"""
        logger.warning(
            f"{level} Budget Alert: {budget.dimension} {budget.dimension_id} "
            f"has used {usage_rate:.1%} of {period} budget"
        )

        # 实际应用中，这里会发送邮件/Slack/钉钉通知
        # send_slack_notification(...)
        # send_email_notification(...)
```

**关键注解说明**：
- **‹1›** `CostTrackingService`：核心成本追踪服务
- **‹2›** `log_api_usage()`：记录每次 API 调用并自动计算成本
- **‹3›** `get_cost_summary()`：生成成本报告
- **‹4›** `_check_budget_alerts()`：自动预警机制

---

## 12.3 Model Router 智能选择

### 12.3.1 智能路由策略

```python
# model_router/router.py
from typing import Literal, Optional
from enum import Enum
import anthropic

class TaskComplexity(Enum):
    """任务复杂度"""
    SIMPLE = "simple"      # 简单：FAQ 查询、分类等
    MODERATE = "moderate"  # 中等：摘要、翻译等
    COMPLEX = "complex"    # 复杂：推理、创作等

class ModelRouter:
    """
    ‹1› 智能模型路由器

    根据任务特性自动选择最合适（成本效益最优）的模型
    """

    # 模型能力与成本矩阵
    MODEL_PROFILES = {
        "claude-haiku-3-20250307": {
            "capability": 1.0,
            "cost_multiplier": 1.0,  # 基准
            "avg_latency_ms": 500,
            "suitable_for": [TaskComplexity.SIMPLE]
        },
        "claude-sonnet-4-20250514": {
            "capability": 2.5,
            "cost_multiplier": 12.0,  # output: 15 vs 1.25 = 12x
            "avg_latency_ms": 1200,
            "suitable_for": [TaskComplexity.SIMPLE, TaskComplexity.MODERATE]
        },
        "claude-opus-4-20250514": {
            "capability": 3.0,
            "cost_multiplier": 60.0,  # output: 75 vs 1.25 = 60x
            "avg_latency_ms": 2000,
            "suitable_for": [TaskComplexity.MODERATE, TaskComplexity.COMPLEX]
        }
    }

    def __init__(self):
        self.usage_stats = {}  # 追踪使用统计

    def select_model(
        self,
        task_complexity: TaskComplexity,
        max_cost: Optional[float] = None,
        max_latency_ms: Optional[int] = None,
        quality_priority: float = 0.5  # 0-1，越高越重视质量
    ) -> str:
        """
        ‹2› 智能选择模型

        Args:
            task_complexity: 任务复杂度
            max_cost: 最大成本（相对于 Haiku）
            max_latency_ms: 最大延迟（毫秒）
            quality_priority: 质量优先级（0-1）

        Returns:
            str: 选定的模型名称
        """
        candidates = []

        for model, profile in self.MODEL_PROFILES.items():
            # 检查是否适合任务复杂度
            if task_complexity not in profile["suitable_for"]:
                continue

            # 检查成本限制
            if max_cost and profile["cost_multiplier"] > max_cost:
                continue

            # 检查延迟限制
            if max_latency_ms and profile["avg_latency_ms"] > max_latency_ms:
                continue

            candidates.append((model, profile))

        if not candidates:
            # 降级：使用最便宜的模型
            return "claude-haiku-3-20250307"

        # 计算综合得分
        def score(model_profile):
            model, profile = model_profile

            # 质量得分（归一化）
            quality_score = profile["capability"] / 3.0

            # 成本得分（越低越好，归一化并反转）
            cost_score = 1.0 - (profile["cost_multiplier"] / 60.0)

            # 加权平均
            return quality_priority * quality_score + (1 - quality_priority) * cost_score

        # 选择得分最高的
        best_model = max(candidates, key=score)[0]

        # 记录使用
        self.usage_stats[best_model] = self.usage_stats.get(best_model, 0) + 1

        return best_model

    def auto_select(
        self,
        prompt: str,
        expected_output_length: Literal["short", "medium", "long"] = "medium"
    ) -> str:
        """
        ‹3› 自动分析 prompt 并选择模型
        """
        # 简单的启发式规则
        complexity = self._estimate_complexity(prompt, expected_output_length)

        # 根据复杂度选择
        if complexity == TaskComplexity.SIMPLE:
            return "claude-haiku-3-20250307"
        elif complexity == TaskComplexity.MODERATE:
            return "claude-sonnet-4-20250514"
        else:
            return "claude-opus-4-20250514"

    def _estimate_complexity(
        self,
        prompt: str,
        expected_output_length: str
    ) -> TaskComplexity:
        """估算任务复杂度"""

        # 关键词检测
        simple_keywords = ["查询", "分类", "是否", "true/false", "yes/no", "选择"]
        complex_keywords = ["分析", "推理", "创作", "设计", "规划", "解释为什么"]

        prompt_lower = prompt.lower()

        # 检查复杂关键词
        if any(keyword in prompt_lower for keyword in complex_keywords):
            return TaskComplexity.COMPLEX

        # 检查简单关键词
        if any(keyword in prompt_lower for keyword in simple_keywords):
            if expected_output_length == "short":
                return TaskComplexity.SIMPLE
            else:
                return TaskComplexity.MODERATE

        # 默认根据输出长度
        if expected_output_length == "short":
            return TaskComplexity.SIMPLE
        elif expected_output_length == "long":
            return TaskComplexity.COMPLEX
        else:
            return TaskComplexity.MODERATE


# 使用示例
router = ModelRouter()

# 场景 1：简单分类任务
model = router.select_model(
    task_complexity=TaskComplexity.SIMPLE,
    max_latency_ms=800
)
# 结果：claude-haiku-3-20250307

# 场景 2：需要高质量的复杂任务
model = router.select_model(
    task_complexity=TaskComplexity.COMPLEX,
    quality_priority=0.9  # 优先质量
)
# 结果：claude-opus-4-20250514

# 场景 3：自动选择
model = router.auto_select(
    prompt="请将以下客户反馈分类为：投诉、建议、咨询",
    expected_output_length="short"
)
# 结果：claude-haiku-3-20250307
```

**关键注解说明**：
- **‹1›** `ModelRouter`：智能模型路由器
- **‹2›** `select_model()`：根据多个维度智能选择模型
- **‹3›** `auto_select()`：自动分析 prompt 并选择合适模型

---

## 12.4 Prompt Caching 策略

### 12.4.1 Caching 实现

```python
# caching/prompt_cache.py
from typing import List, Dict, Any, Optional
import hashlib
import anthropic

class PromptCache:
    """
    ‹1› Prompt Caching 管理器

    利用 Claude 的 Prompt Caching 功能大幅降低成本
    """

    def __init__(self, client: anthropic.Anthropic):
        self.client = client
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "saved_tokens": 0,
            "saved_cost": 0
        }

    def create_cached_message(
        self,
        static_context: str,  # 静态部分（会被缓存）
        dynamic_query: str,   # 动态部分
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 1024
    ) -> Dict[str, Any]:
        """
        ‹2› 创建带缓存的消息

        静态 context 会被缓存，后续请求可重用
        """

        # 构建带缓存标记的系统消息
        response = self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=[
                {
                    "type": "text",
                    "text": static_context,
                    "cache_control": {"type": "ephemeral"}  # 启用缓存
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": dynamic_query
                }
            ]
        )

        # 记录缓存使用情况
        usage = response.usage
        if hasattr(usage, 'cache_read_input_tokens') and usage.cache_read_input_tokens > 0:
            self.cache_stats["hits"] += 1
            self.cache_stats["saved_tokens"] += usage.cache_read_input_tokens

            # 缓存命中节省 90% 成本
            saved_cost = (usage.cache_read_input_tokens / 1_000_000) * 3.0 * 0.9
            self.cache_stats["saved_cost"] += saved_cost
        else:
            self.cache_stats["misses"] += 1

        return {
            "response": response,
            "cache_hit": hasattr(usage, 'cache_read_input_tokens') and usage.cache_read_input_tokens > 0
        }


# 实际应用示例
class FAQAgent:
    """FAQ 客服 Agent with Caching"""

    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.cache = PromptCache(self.client)

        # 加载 FAQ 数据库（仅一次）
        self.faq_context = self._load_faq_database()

    def _load_faq_database(self) -> str:
        """加载完整 FAQ 数据库"""
        # 假设有 20,000 tokens 的 FAQ 内容
        return """
        # FAQ 数据库

        ## 账户相关
        Q: 如何注册账户？
        A: ...

        ## 支付相关
        Q: 支持哪些支付方式？
        A: ...

        ... (数千条 FAQ)
        """

    def answer_question(self, question: str) -> str:
        """
        回答客户问题

        ✅ 优化：FAQ 数据库被缓存，后续请求节省 90% 成本
        """
        result = self.cache.create_cached_message(
            static_context=self.faq_context,  # 会被缓存
            dynamic_query=f"客户问题：{question}\n请根据 FAQ 数据库回答。"
        )

        return result["response"].content[0].text


# 成本对比
"""
无 Caching：
- 每次请求：20,000 (FAQ) + 100 (query) = 20,100 input tokens
- 5,000 次请求/天 = 100,500,000 tokens/天
- 成本：$301.50/天 = $9,045/月

有 Caching：
- 首次请求：20,100 tokens（写入缓存）
- 后续请求：100 tokens + 20,000 tokens (cached @ 90% discount)
- 有效成本：100 + 20,000 * 0.1 = 2,100 tokens/请求
- 5,000 次请求/天 = 10,500,000 tokens/天
- 成本：$31.50/天 = $945/月

节省：$8,100/月 (-90%)
"""
```

**关键注解说明**：
- **‹1›** `PromptCache`：Prompt Caching 管理器
- **‹2›** `create_cached_message()`：创建带缓存标记的消息

---

## 12.5 预算管理与自动限流

### 12.5.1 限流器实现

```python
# rate_limiting/throttler.py
from typing import Optional
import time
from threading import Lock
from collections import deque

class BudgetThrottler:
    """
    ‹1› 预算限流器

    当预算接近用尽时自动降速请求
    """

    def __init__(
        self,
        cost_tracking_service,
        dimension: str,
        dimension_id: str
    ):
        self.cost_service = cost_tracking_service
        self.dimension = dimension
        self.dimension_id = dimension_id

        # 滑动窗口记录（最近 60 秒）
        self.request_times = deque()
        self.lock = Lock()

    def should_allow_request(self) -> tuple[bool, Optional[str]]:
        """
        ‹2› 判断是否允许请求

        Returns:
            (允许?, 原因)
        """
        # 获取当前预算使用情况
        budget = self.cost_service.db.query(CostBudget).filter_by(
            dimension=self.dimension,
            dimension_id=self.dimension_id
        ).first()

        if not budget:
            return True, None

        # 计算使用率
        day_usage_rate = budget.current_day_spending / budget.daily_budget

        # 超过限额，拒绝请求
        if day_usage_rate >= 1.0:
            return False, f"Daily budget exhausted ({day_usage_rate:.1%})"

        # 接近限额且启用自动限流
        if day_usage_rate >= budget.critical_threshold and budget.auto_throttle:
            # 计算当前 QPS
            with self.lock:
                now = time.time()

                # 清理旧记录
                while self.request_times and now - self.request_times[0] > 60:
                    self.request_times.popleft()

                current_qps = len(self.request_times) / 60

                # 计算目标 QPS（降速）
                remaining_rate = 1.0 - day_usage_rate
                target_qps = current_qps * budget.throttle_rate

                # 如果当前 QPS 超过目标，拒绝请求
                if current_qps > target_qps:
                    return False, f"Throttling: budget at {day_usage_rate:.1%}, QPS limit {target_qps:.2f}"

                # 记录本次请求
                self.request_times.append(now)

        return True, None


# 集成到 Agent
class BudgetAwareAgent:
    """带预算控制的 Agent"""

    def __init__(self, api_key: str, team_id: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.team_id = team_id

        # 初始化限流器
        self.throttler = BudgetThrottler(
            cost_tracking_service=cost_service,
            dimension="team",
            dimension_id=team_id
        )

    def run(self, prompt: str) -> str:
        """执行 Agent（带预算检查）"""

        # 检查预算
        allowed, reason = self.throttler.should_allow_request()

        if not allowed:
            logger.warning(f"Request blocked: {reason}")
            raise BudgetExceededException(reason)

        # 执行请求
        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )

        # 记录成本
        cost_service.log_api_usage(
            user_id="user_123",
            team_id=self.team_id,
            project_id="project_456",
            agent_id="agent_789",
            model="claude-sonnet-4-20250514",
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens
        )

        return response.content[0].text


class BudgetExceededException(Exception):
    """预算超支异常"""
    pass
```

**关键注解说明**：
- **‹1›** `BudgetThrottler`：智能限流器
- **‹2›** `should_allow_request()`：基于预算使用率动态限流

---

## 12.6 实际效益

### 12.6.1 优化前后对比

```
TechCorp 成本优化项目结果报告
实施周期：2024 年 11 月
对比基线：2024 年 10 月

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. 总体成本变化
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
10 月（优化前）：US$ 127,850
11 月（优化后）：US$ 42,300

总节省：US$ 85,550/月 (-67%)
年化节省：US$ 1,026,600

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2. 具体优化措施成效
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

措施 A：Model Router 智能选择
- Haiku 使用率：5% → 45% (+800%)
- Sonnet 使用率：25% → 48% (+92%)
- Opus 使用率：70% → 7% (-90%)
- 节省金额：US$ 52,300/月

措施 B：Prompt Caching
- 缓存命中率：0% → 78%
- 节省 tokens：89M/月
- 节省金额：US$ 26,700/月

措施 C：Token 优化
- 平均 prompt 长度：8,500 → 3,200 tokens (-62%)
- 节省金额：US$ 6,550/月

措施 D：预算控制与限流
- 减少不必要请求：15%
- 节省金额：US$ 0（间接效益：避免超支）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
3. 服务质量影响
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

平均响应质量评分：4.7 → 4.6 (-2%)
用户满意度：92% → 91% (-1%)
平均响应延迟：1,450ms → 980ms (-32% ✅)

结论：成本大幅降低，服务质量基本不变

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
4. ROI 分析
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

优化项目投入：
- 开发成本：NT$ 850,000 (2 周 × 3 工程师)
- 工具成本：NT$ 120,000
- 总投入：NT$ 970,000

月度节省：US$ 85,550 ≈ NT$ 2,738,160

ROI：
- 回收期：0.35 个月 (10.5 天)
- 年化 ROI：3,385%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 12.7 章节总结

### 你已经学会了什么

✅ **多维度成本追踪**
   - 按团队/项目/用户分类统计
   - 实时成本计算
   - 自动预算预警

✅ **Model Router 智能选择**
   - 根据任务复杂度选择合适模型
   - 成本与质量平衡
   - 60倍成本差异优化

✅ **Prompt Caching**
   - 90% 缓存折扣
   - 静态/动态内容分离
   - 节省高达 90% 成本

✅ **预算管理**
   - 多级预算控制
   - 自动限流机制
   - 避免预算超支

✅ **Token 优化**
   - Prompt 精简技巧
   - 输出长度控制
   - 批量处理策略

### 实际效益

| 面向 | 效益 |
|------|------|
| **总成本** | 降低 67% |
| **响应延迟** | 降低 32% |
| **服务质量** | 保持 98%+ |
| **ROI** | 3,385% |

### 检查清单

实施成本优化前，请确认：

- [ ] **建立成本追踪系统**
- [ ] **实现 Model Router**
- [ ] **启用 Prompt Caching**
- [ ] **设置预算与预警**
- [ ] **优化 Prompt 设计**
- [ ] **培训开发团队**
- [ ] **持续监控与优化**

---

## 12.8 下一章预告

**第 13 章：Agent 开发的未来与持续学习路径**（最终章）

你将学到：
- Agent 技术发展趋势
- 新兴架构模式
- 持续学习资源推荐
- 社群参与指南
- 职涯发展建议
- 全书总结与展望

**最后一章**：回顾全书 12 章的学习旅程，展望 Agent 技术的未来，为你的持续成长指明方向。

准备好完成这段精彩的学习旅程了吗？让我们前往最终章！

---

**章节完成时间**：约 90-120 分钟
**难度等级**：⭐⭐⭐⭐ (4/5 - 进阶)
**前置要求**：完成第 1-11 章
