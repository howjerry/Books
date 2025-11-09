"""
成本追踪数据模型

本模块定义了成本追踪系统的 SQLAlchemy 数据模型，支持多维度的成本分析。
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Index, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class APIUsageLog(Base):
    """
    API 使用日志表

    记录每次 API 调用的详细信息，支持成本分析和使用追踪。
    """
    __tablename__ = "api_usage_logs"

    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # 归属信息（多维度成本归集）
    user_id = Column(String(100), nullable=False, index=True)
    team_id = Column(String(100), nullable=False, index=True)
    project_id = Column(String(100), nullable=False, index=True)

    # 模型信息
    model = Column(String(50), nullable=False, index=True)

    # Token 使用量
    input_tokens = Column(Integer, nullable=False)
    output_tokens = Column(Integer, nullable=False)
    cached_tokens = Column(Integer, default=0)  # Prompt Caching 命中的 Token

    # 成本（USD）
    input_cost = Column(Float, nullable=False)
    output_cost = Column(Float, nullable=False)
    cache_savings = Column(Float, default=0.0)  # 缓存节省的成本
    total_cost = Column(Float, nullable=False, index=True)

    # 任务信息
    task_type = Column(String(50), nullable=True)
    task_complexity = Column(String(20), nullable=True)  # simple, moderate, complex

    # 性能指标
    response_time_ms = Column(Integer, nullable=True)

    # 索引
    __table_args__ = (
        Index('idx_team_project_timestamp', 'team_id', 'project_id', 'timestamp'),
        Index('idx_user_timestamp', 'user_id', 'timestamp'),
        Index('idx_model_timestamp', 'model', 'timestamp'),
    )

    def __repr__(self):
        return f"<APIUsageLog(id={self.id}, model={self.model}, cost=${self.total_cost:.4f})>"


class CostBudget(Base):
    """
    成本预算表

    定义团队/项目的月度预算限制，支持自动预警和限流。
    """
    __tablename__ = "cost_budgets"

    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 预算归属
    entity_type = Column(String(20), nullable=False)  # team, project, user
    entity_id = Column(String(100), nullable=False)

    # 预算限制（USD）
    monthly_limit = Column(Float, nullable=False)

    # 预警阈值
    warning_threshold = Column(Float, default=0.8)  # 80% 时发出预警
    critical_threshold = Column(Float, default=0.95)  # 95% 时限流

    # 时间范围
    effective_from = Column(DateTime, nullable=False)
    effective_to = Column(DateTime, nullable=True)

    # 状态
    is_active = Column(String(10), default="active")

    # 创建时间
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 索引
    __table_args__ = (
        Index('idx_entity', 'entity_type', 'entity_id'),
    )

    def __repr__(self):
        return f"<CostBudget(entity={self.entity_type}:{self.entity_id}, limit=${self.monthly_limit})>"


class CostAlert(Base):
    """
    成本告警记录表

    记录预算超限告警历史，支持告警分析和审计。
    """
    __tablename__ = "cost_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # 关联的预算
    budget_id = Column(Integer, ForeignKey('cost_budgets.id'), nullable=False)
    budget = relationship("CostBudget")

    # 告警级别
    severity = Column(String(20), nullable=False)  # warning, critical

    # 使用情况
    current_usage = Column(Float, nullable=False)
    budget_limit = Column(Float, nullable=False)
    usage_percentage = Column(Float, nullable=False)

    # 告警消息
    message = Column(String(500), nullable=False)

    # 处理状态
    is_acknowledged = Column(String(10), default="no")
    acknowledged_by = Column(String(100), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<CostAlert(severity={self.severity}, usage={self.usage_percentage:.1f}%)>"
