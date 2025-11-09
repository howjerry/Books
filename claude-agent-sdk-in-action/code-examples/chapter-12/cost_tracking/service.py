"""
成本追踪服务

提供完整的成本追踪、分析和预算管理功能。
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, Session
from .models import Base, APIUsageLog, CostBudget, CostAlert


class CostTrackingService:
    """
    成本追踪服务

    核心功能：
    1. 记录 API 使用日志
    2. 多维度成本分析
    3. 预算管理和告警
    4. 成本优化建议
    """

    # Claude 模型定价（每百万 Token，USD）
    MODEL_PRICING = {
        "claude-haiku-3-20250307": {
            "input": 0.25,
            "output": 1.25,
            "cache_write": 0.30,
            "cache_read": 0.03
        },
        "claude-sonnet-4-20250514": {
            "input": 3.00,
            "output": 15.00,
            "cache_write": 3.75,
            "cache_read": 0.30
        },
        "claude-opus-4-20250514": {
            "input": 15.00,
            "output": 75.00,
            "cache_write": 18.75,
            "cache_read": 1.50
        }
    }

    def __init__(self, database_url: str):
        """
        初始化成本追踪服务

        Args:
            database_url: 数据库连接字符串
        """
        self.engine = create_engine(database_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def log_api_usage(
        self,
        user_id: str,
        team_id: str,
        project_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int = 0,
        task_type: Optional[str] = None,
        task_complexity: Optional[str] = None,
        response_time_ms: Optional[int] = None
    ) -> APIUsageLog:
        """
        记录一次 API 调用

        Args:
            user_id: 用户 ID
            team_id: 团队 ID
            project_id: 项目 ID
            model: 模型名称
            input_tokens: 输入 Token 数
            output_tokens: 输出 Token 数
            cached_tokens: 缓存命中 Token 数
            task_type: 任务类型
            task_complexity: 任务复杂度
            response_time_ms: 响应时间（毫秒）

        Returns:
            创建的日志记录
        """
        pricing = self.MODEL_PRICING.get(model, self.MODEL_PRICING["claude-sonnet-4-20250514"])

        # 计算成本
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        # 缓存节省：正常价格 - 缓存价格
        if cached_tokens > 0:
            normal_cache_cost = (cached_tokens / 1_000_000) * pricing["input"]
            actual_cache_cost = (cached_tokens / 1_000_000) * pricing["cache_read"]
            cache_savings = normal_cache_cost - actual_cache_cost
        else:
            cache_savings = 0.0

        total_cost = input_cost + output_cost - cache_savings

        # 创建日志
        log = APIUsageLog(
            timestamp=datetime.utcnow(),
            user_id=user_id,
            team_id=team_id,
            project_id=project_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_tokens=cached_tokens,
            input_cost=input_cost,
            output_cost=output_cost,
            cache_savings=cache_savings,
            total_cost=total_cost,
            task_type=task_type,
            task_complexity=task_complexity,
            response_time_ms=response_time_ms
        )

        with self.Session() as session:
            session.add(log)
            session.commit()
            session.refresh(log)

        # 检查预算
        self._check_budget(team_id, project_id, session)

        return log

    def get_cost_summary(
        self,
        start_date: datetime,
        end_date: datetime,
        group_by: str = "team"
    ) -> List[Dict]:
        """
        获取成本汇总报告

        Args:
            start_date: 开始日期
            end_date: 结束日期
            group_by: 分组维度（team, project, user, model）

        Returns:
            成本汇总列表
        """
        with self.Session() as session:
            group_column = getattr(APIUsageLog, f"{group_by}_id" if group_by != "model" else "model")

            results = session.query(
                group_column.label('entity'),
                func.sum(APIUsageLog.total_cost).label('total_cost'),
                func.sum(APIUsageLog.input_tokens).label('total_input_tokens'),
                func.sum(APIUsageLog.output_tokens).label('total_output_tokens'),
                func.sum(APIUsageLog.cached_tokens).label('total_cached_tokens'),
                func.sum(APIUsageLog.cache_savings).label('total_cache_savings'),
                func.count(APIUsageLog.id).label('request_count')
            ).filter(
                APIUsageLog.timestamp >= start_date,
                APIUsageLog.timestamp < end_date
            ).group_by(group_column).all()

            return [
                {
                    'entity': r.entity,
                    'total_cost': round(r.total_cost, 2),
                    'total_input_tokens': r.total_input_tokens,
                    'total_output_tokens': r.total_output_tokens,
                    'total_cached_tokens': r.total_cached_tokens,
                    'cache_savings': round(r.total_cache_savings, 2),
                    'request_count': r.request_count,
                    'avg_cost_per_request': round(r.total_cost / r.request_count, 4)
                }
                for r in results
            ]

    def create_budget(
        self,
        entity_type: str,
        entity_id: str,
        monthly_limit: float,
        warning_threshold: float = 0.8,
        critical_threshold: float = 0.95
    ) -> CostBudget:
        """
        创建预算限制

        Args:
            entity_type: 实体类型（team, project, user）
            entity_id: 实体 ID
            monthly_limit: 月度预算限制（USD）
            warning_threshold: 预警阈值（默认 80%）
            critical_threshold: 严重阈值（默认 95%）

        Returns:
            创建的预算记录
        """
        budget = CostBudget(
            entity_type=entity_type,
            entity_id=entity_id,
            monthly_limit=monthly_limit,
            warning_threshold=warning_threshold,
            critical_threshold=critical_threshold,
            effective_from=datetime.utcnow(),
            is_active="active"
        )

        with self.Session() as session:
            session.add(budget)
            session.commit()
            session.refresh(budget)

        return budget

    def _check_budget(self, team_id: str, project_id: str, session: Session):
        """
        检查预算使用情况，必要时发出告警

        Args:
            team_id: 团队 ID
            project_id: 项目 ID
            session: 数据库会话
        """
        # 获取本月起始时间
        now = datetime.utcnow()
        month_start = datetime(now.year, now.month, 1)

        # 检查团队预算
        team_budget = session.query(CostBudget).filter(
            CostBudget.entity_type == "team",
            CostBudget.entity_id == team_id,
            CostBudget.is_active == "active"
        ).first()

        if team_budget:
            current_usage = session.query(func.sum(APIUsageLog.total_cost)).filter(
                APIUsageLog.team_id == team_id,
                APIUsageLog.timestamp >= month_start
            ).scalar() or 0.0

            usage_pct = current_usage / team_budget.monthly_limit

            # 触发告警
            if usage_pct >= team_budget.critical_threshold:
                self._create_alert(session, team_budget, current_usage, "critical")
            elif usage_pct >= team_budget.warning_threshold:
                self._create_alert(session, team_budget, current_usage, "warning")

    def _create_alert(
        self,
        session: Session,
        budget: CostBudget,
        current_usage: float,
        severity: str
    ):
        """
        创建成本告警

        Args:
            session: 数据库会话
            budget: 预算记录
            current_usage: 当前使用量
            severity: 严重级别
        """
        usage_pct = (current_usage / budget.monthly_limit) * 100

        # 检查是否已有未确认的告警
        existing = session.query(CostAlert).filter(
            CostAlert.budget_id == budget.id,
            CostAlert.severity == severity,
            CostAlert.is_acknowledged == "no",
            CostAlert.timestamp >= datetime.utcnow() - timedelta(hours=1)
        ).first()

        if not existing:
            alert = CostAlert(
                budget_id=budget.id,
                severity=severity,
                current_usage=current_usage,
                budget_limit=budget.monthly_limit,
                usage_percentage=usage_pct,
                message=f"{budget.entity_type.upper()} {budget.entity_id} has used {usage_pct:.1f}% of monthly budget (${current_usage:.2f}/${budget.monthly_limit:.2f})"
            )
            session.add(alert)
            session.commit()

            print(f"🚨 {severity.upper()} ALERT: {alert.message}")

    def get_optimization_suggestions(
        self,
        team_id: str,
        days: int = 30
    ) -> List[Dict]:
        """
        获取成本优化建议

        Args:
            team_id: 团队 ID
            days: 分析天数

        Returns:
            优化建议列表
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        suggestions = []

        with self.Session() as session:
            # 1. 检查模型使用分布
            model_usage = session.query(
                APIUsageLog.model,
                APIUsageLog.task_complexity,
                func.count(APIUsageLog.id).label('count'),
                func.sum(APIUsageLog.total_cost).label('cost')
            ).filter(
                APIUsageLog.team_id == team_id,
                APIUsageLog.timestamp >= start_date
            ).group_by(APIUsageLog.model, APIUsageLog.task_complexity).all()

            # 检查是否在简单任务上使用了昂贵模型
            for usage in model_usage:
                if usage.task_complexity == "simple" and "opus" in usage.model.lower():
                    suggestions.append({
                        "type": "model_downgrade",
                        "priority": "high",
                        "message": f"检测到 {usage.count} 个简单任务使用 Opus 模型，建议降级为 Haiku",
                        "estimated_savings": usage.cost * 0.98  # 约 98% 成本节省
                    })

            # 2. 检查缓存使用率
            cache_stats = session.query(
                func.sum(APIUsageLog.cached_tokens).label('cached'),
                func.sum(APIUsageLog.input_tokens).label('total'),
                func.sum(APIUsageLog.cache_savings).label('savings')
            ).filter(
                APIUsageLog.team_id == team_id,
                APIUsageLog.timestamp >= start_date
            ).first()

            if cache_stats.cached == 0:
                suggestions.append({
                    "type": "enable_caching",
                    "priority": "high",
                    "message": "未检测到 Prompt Caching 使用，建议启用以节省高达 90% 的重复内容成本",
                    "estimated_savings": cache_stats.total * 0.5 * 0.9  # 假设 50% 内容可缓存
                })

            # 3. 检查高频调用
            high_freq_users = session.query(
                APIUsageLog.user_id,
                func.count(APIUsageLog.id).label('count')
            ).filter(
                APIUsageLog.team_id == team_id,
                APIUsageLog.timestamp >= start_date
            ).group_by(APIUsageLog.user_id).having(
                func.count(APIUsageLog.id) > 1000
            ).all()

            if high_freq_users:
                suggestions.append({
                    "type": "batch_processing",
                    "priority": "medium",
                    "message": f"检测到 {len(high_freq_users)} 个用户高频调用，建议使用批量处理",
                    "estimated_savings": None
                })

        return suggestions
