# 第 12 章：成本優化與資源管理 - 打造高效益的 Agent 系統

## 本章內容概覽

- 理解 AI 成本的構成與挑戰
- 建立多維度成本追蹤系統
- 實現 Model Router 智能選擇
- 優化 Prompt Caching 策略
- 設計預算管理與自動限流
- 掌握 Token 優化技巧
- 建立 ROI 計算框架
- 完成一個企業級成本管理系統

---

## 12.1 場景：失控的 AI 成本

### 真實挑戰

你是 TechCorp 的 CFO，收到了一份令人震驚的 Claude API 帳單：

```
Anthropic API 月度帳單
帳期：2024 年 10 月

總費用：US$ 127,850

詳細分類：
- Claude Opus：    US$ 89,450 (70%)
- Claude Sonnet：  US$ 32,100 (25%)
- Claude Haiku：   US$ 6,300 (5%)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
對比：
- 9 月帳單：US$ 38,200
- 增長率：+235%
- 年化成本：US$ 1,534,200
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️  預警：
按當前增長率，12 月預計達 US$ 285,000
```

**調查發現的問題**：

```python
# ❌ 問題 1：盲目使用最貴的模型
# agent_service.py
def create_agent():
    return Agent(
        model="claude-opus-4-20250514",  # 💰 總是用 Opus
        ...
    )

# 實際需求：80% 的請求用 Haiku 就夠了
# 成本差異：Opus ($75/1M output) vs Haiku ($1.25/1M output) = 60倍


# ❌ 問題 2：重複計算相同內容
# customer_service_agent.py
def handle_customer_query(query: str):
    # 每次都重新分析完整的 FAQ 資料庫（20,000 tokens）
    faq_content = load_faq_database()  # 每次載入

    prompt = f"""
    FAQ 資料庫：
    {faq_content}  # 💰 每次都包含完整 FAQ

    客戶問題：{query}
    """

    response = client.messages.create(...)
    return response

# 浪費：20,000 tokens × 每天 5,000 次請求 = 每天 100M tokens
# 成本：US$ 300/天 × 30 天 = US$ 9,000/月（可完全避免）


# ❌ 問題 3：沒有預算控制
# 任何開發者都可以無限制呼叫 API
# 沒有成本追蹤
# 沒有預警機制
# 沒有自動限流


# ❌ 問題 4：Token 使用低效
def analyze_document(doc: str):
    # 發送完整文檔，即使只需要摘要
    prompt = f"""
    請分析以下文檔並提供 3 句話摘要：

    {doc}  # 💰 50,000 tokens 的完整文檔
    """

    # 更好的做法：先用 Haiku 提取關鍵資訊，再用 Sonnet 總結
    # 成本可降低 80%
```

**財務影響**：
- 月度成本：US$ 127,850
- 預算超支：+355%（預算 US$ 28,000）
- ROI 未知：無法證明投入產出比
- CFO 要求：立即降低成本 50%+

---

## 12.2 多維度成本追蹤系統

### 12.2.1 成本資料模型

```python
# cost_tracking/models.py
from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, Index
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from typing import Optional

Base = declarative_base()

class APIUsageLog(Base):
    """
    ‹1› API 使用日誌表

    記錄每次 API 呼叫的詳細資訊，用於成本分析
    """
    __tablename__ = "api_usage_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 時間資訊
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # 歸屬資訊
    user_id = Column(String(100), nullable=False, index=True)
    team_id = Column(String(100), nullable=False, index=True)
    project_id = Column(String(100), nullable=False, index=True)
    agent_id = Column(String(100), nullable=False, index=True)

    # 模型資訊
    model = Column(String(50), nullable=False, index=True)

    # Token 使用量
    input_tokens = Column(Integer, nullable=False)
    output_tokens = Column(Integer, nullable=False)
    cached_tokens = Column(Integer, default=0)  # Prompt caching

    # 成本（USD）
    input_cost = Column(Float, nullable=False)
    output_cost = Column(Float, nullable=False)
    total_cost = Column(Float, nullable=False, index=True)

    # 性能指標
    latency_ms = Column(Integer)
    success = Column(Boolean, nullable=False)
    error_type = Column(String(100))

    # 業務標籤
    tags = Column(JSON)  # {"environment": "production", "feature": "customer-service"}

    # 索引優化
    __table_args__ = (
        Index('idx_team_date', 'team_id', 'timestamp'),
        Index('idx_project_model', 'project_id', 'model'),
    )


class CostBudget(Base):
    """
    ‹2› 成本預算表
    """
    __tablename__ = "cost_budgets"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 預算維度
    dimension = Column(String(20), nullable=False)  # team, project, user
    dimension_id = Column(String(100), nullable=False)

    # 預算金額（USD）
    monthly_budget = Column(Float, nullable=False)
    daily_budget = Column(Float, nullable=False)

    # 當前使用
    current_month_spending = Column(Float, default=0)
    current_day_spending = Column(Float, default=0)

    # 預警閾值（百分比）
    warning_threshold = Column(Float, default=0.8)  # 80%
    critical_threshold = Column(Float, default=0.95)  # 95%

    # 限流設定
    auto_throttle = Column(Boolean, default=True)
    throttle_rate = Column(Float, default=0.5)  # 降速 50%

    # 時間戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_dimension', 'dimension', 'dimension_id'),
    )
```

**關鍵註解說明**：
- **‹1›** `APIUsageLog`：記錄每次 API 呼叫的完整資訊，支援多維度分析
- **‹2›** `CostBudget`：預算管理表，支援團隊/專案/用戶級別的預算控制

### 12.2.2 成本追蹤服務

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
    ‹1› 成本追蹤服務

    核心功能：
    1. 記錄 API 使用
    2. 計算成本
    3. 更新預算
    4. 觸發預警
    """

    # 模型定價（每百萬 tokens，USD）
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
        ‹2› 記錄 API 使用並計算成本
        """
        # 計算成本
        pricing = self.MODEL_PRICING.get(model)
        if not pricing:
            logger.warning(f"Unknown model: {model}, using Sonnet pricing")
            pricing = self.MODEL_PRICING["claude-sonnet-4-20250514"]

        # 考慮 Prompt Caching 的折扣
        effective_input_tokens = input_tokens - cached_tokens
        cached_input_tokens = cached_tokens

        input_cost = (effective_input_tokens / 1_000_000) * pricing["input"]

        # Cached tokens 通常是 90% 折扣
        cached_cost = (cached_input_tokens / 1_000_000) * pricing["input"] * 0.1

        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        total_cost = input_cost + cached_cost + output_cost

        # 創建日誌記錄
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

        # 更新預算使用量
        self._update_budget_spending(team_id, project_id, user_id, total_cost)

        # 檢查是否需要預警
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
        ‹3› 獲取成本摘要
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

        # 計算總計
        total_cost = sum(log.total_cost for log in logs)
        total_requests = len(logs)
        total_input_tokens = sum(log.input_tokens for log in logs)
        total_output_tokens = sum(log.output_tokens for log in logs)
        total_cached_tokens = sum(log.cached_tokens for log in logs)

        # 按模型分組
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

        # 平均延遲
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
        """更新預算使用量"""
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # 更新團隊預算
        team_budget = self.db.query(CostBudget).filter_by(
            dimension="team",
            dimension_id=team_id
        ).first()

        if team_budget:
            team_budget.current_month_spending += cost
            team_budget.current_day_spending += cost

        # 更新專案預算
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
        ‹4› 檢查預算并觸發預警
        """
        budgets = self.db.query(CostBudget).filter(
            ((CostBudget.dimension == "team") & (CostBudget.dimension_id == team_id)) |
            ((CostBudget.dimension == "project") & (CostBudget.dimension_id == project_id))
        ).all()

        for budget in budgets:
            # 檢查月度預算
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

            # 檢查日度預算
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
        """發送預警通知"""
        logger.warning(
            f"{level} Budget Alert: {budget.dimension} {budget.dimension_id} "
            f"has used {usage_rate:.1%} of {period} budget"
        )

        # 實際應用中，这里会發送郵件/Slack/釘釘通知
        # send_slack_notification(...)
        # send_email_notification(...)
```

**關鍵注解說明**：
- **‹1›** `CostTrackingService`：核心成本追蹤服務
- **‹2›** `log_api_usage()`：記錄每次 API 呼叫并自动計算成本
- **‹3›** `get_cost_summary()`：生成成本報告
- **‹4›** `_check_budget_alerts()`：自动預警机制

---

## 12.3 Model Router 智能選擇

### 12.3.1 智能路由策略

```python
# model_router/router.py
from typing import Literal, Optional
from enum import Enum
import anthropic

class TaskComplexity(Enum):
    """任务複雜度"""
    SIMPLE = "simple"      # 簡單：FAQ 查詢、分类等
    MODERATE = "moderate"  # 中等：摘要、翻译等
    COMPLEX = "complex"    # 複雜：推理、创作等

class ModelRouter:
    """
    ‹1› 智能模型路由器

    根据任务特性自动選擇最合适（成本效益最优）的模型
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
        self.usage_stats = {}  # 追蹤使用统计

    def select_model(
        self,
        task_complexity: TaskComplexity,
        max_cost: Optional[float] = None,
        max_latency_ms: Optional[int] = None,
        quality_priority: float = 0.5  # 0-1，越高越重视質量
    ) -> str:
        """
        ‹2› 智能選擇模型

        Args:
            task_complexity: 任务複雜度
            max_cost: 最大成本（相對于 Haiku）
            max_latency_ms: 最大延遲（毫秒）
            quality_priority: 質量优先级（0-1）

        Returns:
            str: 选定的模型名称
        """
        candidates = []

        for model, profile in self.MODEL_PROFILES.items():
            # 檢查是否適合任务複雜度
            if task_complexity not in profile["suitable_for"]:
                continue

            # 檢查成本限制
            if max_cost and profile["cost_multiplier"] > max_cost:
                continue

            # 檢查延遲限制
            if max_latency_ms and profile["avg_latency_ms"] > max_latency_ms:
                continue

            candidates.append((model, profile))

        if not candidates:
            # 降级：使用最便宜的模型
            return "claude-haiku-3-20250307"

        # 計算综合得分
        def score(model_profile):
            model, profile = model_profile

            # 質量得分（归一化）
            quality_score = profile["capability"] / 3.0

            # 成本得分（越低越好，归一化并反转）
            cost_score = 1.0 - (profile["cost_multiplier"] / 60.0)

            # 加权平均
            return quality_priority * quality_score + (1 - quality_priority) * cost_score

        # 選擇得分最高的
        best_model = max(candidates, key=score)[0]

        # 記錄使用
        self.usage_stats[best_model] = self.usage_stats.get(best_model, 0) + 1

        return best_model

    def auto_select(
        self,
        prompt: str,
        expected_output_length: Literal["short", "medium", "long"] = "medium"
    ) -> str:
        """
        ‹3› 自动分析 prompt 并選擇模型
        """
        # 簡單的启发式规则
        complexity = self._estimate_complexity(prompt, expected_output_length)

        # 根据複雜度選擇
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
        """估算任务複雜度"""

        # 關鍵词检测
        simple_keywords = ["查詢", "分类", "是否", "true/false", "yes/no", "選擇"]
        complex_keywords = ["分析", "推理", "创作", "设计", "规划", "解释为什么"]

        prompt_lower = prompt.lower()

        # 檢查複雜關鍵词
        if any(keyword in prompt_lower for keyword in complex_keywords):
            return TaskComplexity.COMPLEX

        # 檢查簡單關鍵词
        if any(keyword in prompt_lower for keyword in simple_keywords):
            if expected_output_length == "short":
                return TaskComplexity.SIMPLE
            else:
                return TaskComplexity.MODERATE

        # 默認根据输出長度
        if expected_output_length == "short":
            return TaskComplexity.SIMPLE
        elif expected_output_length == "long":
            return TaskComplexity.COMPLEX
        else:
            return TaskComplexity.MODERATE


# 使用示例
router = ModelRouter()

# 場景 1：簡單分类任务
model = router.select_model(
    task_complexity=TaskComplexity.SIMPLE,
    max_latency_ms=800
)
# 结果：claude-haiku-3-20250307

# 場景 2：需要高質量的複雜任务
model = router.select_model(
    task_complexity=TaskComplexity.COMPLEX,
    quality_priority=0.9  # 优先質量
)
# 结果：claude-opus-4-20250514

# 場景 3：自动選擇
model = router.auto_select(
    prompt="请将以下客戶反馈分类为：投诉、建议、咨询",
    expected_output_length="short"
)
# 结果：claude-haiku-3-20250307
```

**關鍵注解說明**：
- **‹1›** `ModelRouter`：智能模型路由器
- **‹2›** `select_model()`：根据多个維度智能選擇模型
- **‹3›** `auto_select()`：自动分析 prompt 并選擇合适模型

---

## 12.4 Prompt Caching 策略

### 12.4.1 Caching 實現

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
        static_context: str,  # 靜態部分（会被緩存）
        dynamic_query: str,   # 動態部分
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 1024
    ) -> Dict[str, Any]:
        """
        ‹2› 創建带緩存的消息

        靜態 context 会被緩存，後續請求可重用
        """

        # 构建带緩存标记的系統消息
        response = self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=[
                {
                    "type": "text",
                    "text": static_context,
                    "cache_control": {"type": "ephemeral"}  # 启用緩存
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": dynamic_query
                }
            ]
        )

        # 記錄緩存使用情况
        usage = response.usage
        if hasattr(usage, 'cache_read_input_tokens') and usage.cache_read_input_tokens > 0:
            self.cache_stats["hits"] += 1
            self.cache_stats["saved_tokens"] += usage.cache_read_input_tokens

            # 緩存命中節省 90% 成本
            saved_cost = (usage.cache_read_input_tokens / 1_000_000) * 3.0 * 0.9
            self.cache_stats["saved_cost"] += saved_cost
        else:
            self.cache_stats["misses"] += 1

        return {
            "response": response,
            "cache_hit": hasattr(usage, 'cache_read_input_tokens') and usage.cache_read_input_tokens > 0
        }


# 實際應用示例
class FAQAgent:
    """FAQ 客服 Agent with Caching"""

    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.cache = PromptCache(self.client)

        # 加载 FAQ 數據库（仅一次）
        self.faq_context = self._load_faq_database()

    def _load_faq_database(self) -> str:
        """加载完整 FAQ 數據库"""
        # 假设有 20,000 tokens 的 FAQ 內容
        return """
        # FAQ 數據库

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
        回答客戶問題

        ✅ 優化：FAQ 數據库被緩存，後續請求節省 90% 成本
        """
        result = self.cache.create_cached_message(
            static_context=self.faq_context,  # 会被緩存
            dynamic_query=f"客戶問題：{question}\n请根据 FAQ 數據库回答。"
        )

        return result["response"].content[0].text


# 成本對比
"""
无 Caching：
- 每次請求：20,000 (FAQ) + 100 (query) = 20,100 input tokens
- 5,000 次請求/天 = 100,500,000 tokens/天
- 成本：$301.50/天 = $9,045/月

有 Caching：
- 首次請求：20,100 tokens（写入緩存）
- 後續請求：100 tokens + 20,000 tokens (cached @ 90% discount)
- 有效成本：100 + 20,000 * 0.1 = 2,100 tokens/請求
- 5,000 次請求/天 = 10,500,000 tokens/天
- 成本：$31.50/天 = $945/月

節省：$8,100/月 (-90%)
"""
```

**關鍵注解說明**：
- **‹1›** `PromptCache`：Prompt Caching 管理器
- **‹2›** `create_cached_message()`：創建带緩存标记的消息

---

## 12.5 預算管理与自动限流

### 12.5.1 限流器實現

```python
# rate_limiting/throttler.py
from typing import Optional
import time
from threading import Lock
from collections import deque

class BudgetThrottler:
    """
    ‹1› 預算限流器

    当預算接近用尽时自动降速請求
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

        # 滑动窗口記錄（最近 60 秒）
        self.request_times = deque()
        self.lock = Lock()

    def should_allow_request(self) -> tuple[bool, Optional[str]]:
        """
        ‹2› 判断是否允许請求

        Returns:
            (允许?, 原因)
        """
        # 獲取當前預算使用情况
        budget = self.cost_service.db.query(CostBudget).filter_by(
            dimension=self.dimension,
            dimension_id=self.dimension_id
        ).first()

        if not budget:
            return True, None

        # 計算使用率
        day_usage_rate = budget.current_day_spending / budget.daily_budget

        # 超过限额，拒绝請求
        if day_usage_rate >= 1.0:
            return False, f"Daily budget exhausted ({day_usage_rate:.1%})"

        # 接近限额且启用自动限流
        if day_usage_rate >= budget.critical_threshold and budget.auto_throttle:
            # 計算當前 QPS
            with self.lock:
                now = time.time()

                # 清理旧記錄
                while self.request_times and now - self.request_times[0] > 60:
                    self.request_times.popleft()

                current_qps = len(self.request_times) / 60

                # 計算目标 QPS（降速）
                remaining_rate = 1.0 - day_usage_rate
                target_qps = current_qps * budget.throttle_rate

                # 如果當前 QPS 超过目标，拒绝請求
                if current_qps > target_qps:
                    return False, f"Throttling: budget at {day_usage_rate:.1%}, QPS limit {target_qps:.2f}"

                # 記錄本次請求
                self.request_times.append(now)

        return True, None


# 集成到 Agent
class BudgetAwareAgent:
    """带預算控制的 Agent"""

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
        """执行 Agent（带預算檢查）"""

        # 檢查預算
        allowed, reason = self.throttler.should_allow_request()

        if not allowed:
            logger.warning(f"Request blocked: {reason}")
            raise BudgetExceededException(reason)

        # 执行請求
        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )

        # 記錄成本
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
    """預算超支异常"""
    pass
```

**關鍵注解說明**：
- **‹1›** `BudgetThrottler`：智能限流器
- **‹2›** `should_allow_request()`：基于預算使用率動態限流

---

## 12.6 實際效益

### 12.6.1 優化前后對比

```
TechCorp 成本優化專案结果報告
实施周期：2024 年 11 月
對比基线：2024 年 10 月

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. 总体成本变化
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
10 月（優化前）：US$ 127,850
11 月（優化后）：US$ 42,300

总節省：US$ 85,550/月 (-67%)
年化節省：US$ 1,026,600

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2. 具体優化措施成效
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

措施 A：Model Router 智能選擇
- Haiku 使用率：5% → 45% (+800%)
- Sonnet 使用率：25% → 48% (+92%)
- Opus 使用率：70% → 7% (-90%)
- 節省金额：US$ 52,300/月

措施 B：Prompt Caching
- 緩存命中率：0% → 78%
- 節省 tokens：89M/月
- 節省金额：US$ 26,700/月

措施 C：Token 優化
- 平均 prompt 長度：8,500 → 3,200 tokens (-62%)
- 節省金额：US$ 6,550/月

措施 D：預算控制与限流
- 减少不必要請求：15%
- 節省金额：US$ 0（间接效益：避免超支）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
3. 服務質量影響
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

平均響應質量评分：4.7 → 4.6 (-2%)
用戶满意度：92% → 91% (-1%)
平均響應延遲：1,450ms → 980ms (-32% ✅)

结论：成本大幅降低，服務質量基本不变

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
4. ROI 分析
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

優化專案投入：
- 開發成本：NT$ 850,000 (2 周 × 3 工程师)
- 工具成本：NT$ 120,000
- 总投入：NT$ 970,000

月度節省：US$ 85,550 ≈ NT$ 2,738,160

ROI：
- 回收期：0.35 个月 (10.5 天)
- 年化 ROI：3,385%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 12.7 章节總結

### 你已经学会了什么

✅ **多維度成本追蹤**
   - 按團隊/專案/用戶分类统计
   - 实时成本計算
   - 自动預算預警

✅ **Model Router 智能選擇**
   - 根据任务複雜度選擇合适模型
   - 成本与質量平衡
   - 60倍成本差異優化

✅ **Prompt Caching**
   - 90% 緩存折扣
   - 靜態/動態內容分离
   - 節省高达 90% 成本

✅ **預算管理**
   - 多级預算控制
   - 自动限流机制
   - 避免預算超支

✅ **Token 優化**
   - Prompt 精简技巧
   - 输出長度控制
   - 批量處理策略

### 實際效益

| 面向 | 效益 |
|------|------|
| **总成本** | 降低 67% |
| **響應延遲** | 降低 32% |
| **服務質量** | 保持 98%+ |
| **ROI** | 3,385% |

### 檢查清单

实施成本優化前，请確認：

- [ ] **建立成本追蹤系統**
- [ ] **實現 Model Router**
- [ ] **启用 Prompt Caching**
- [ ] **設定預算与預警**
- [ ] **優化 Prompt 设计**
- [ ] **培训開發團隊**
- [ ] **持续監控与優化**

---

## 12.8 下一章预告

**第 13 章：Agent 開發的未来与持续学习路径**（最终章）

你将学到：
- Agent 技术发展趋势
- 新兴架构模式
- 持续学习資源推荐
- 社群参与指南
- 职涯发展建议
- 全书總結与展望

**最后一章**：回顾全书 12 章的学习旅程，展望 Agent 技术的未来，为你的持续成长指明方向。

准备好完成这段精彩的学习旅程了吗？让我们前往最终章！

---

**章节完成時間**：约 90-120 分钟
**难度等级**：⭐⭐⭐⭐ (4/5 - 進阶)
**前置要求**：完成第 1-11 章
