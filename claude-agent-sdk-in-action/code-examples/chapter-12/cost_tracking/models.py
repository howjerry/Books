"""
成本追蹤數據模型

本模块定义了成本追蹤系統的 SQLAlchemy 數據模型，支持多維度的成本分析。
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Index, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class APIUsageLog(Base):
    """
    API 使用日誌表

    記錄每次 API 呼叫的詳細資訊，支持成本分析和使用追蹤。
    """
    __tablename__ = "api_usage_logs"

    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # 歸屬資訊（多維度成本歸集）
    user_id = Column(String(100), nullable=False, index=True)
    team_id = Column(String(100), nullable=False, index=True)
    project_id = Column(String(100), nullable=False, index=True)

    # 模型資訊
    model = Column(String(50), nullable=False, index=True)

    # Token 使用量
    input_tokens = Column(Integer, nullable=False)
    output_tokens = Column(Integer, nullable=False)
    cached_tokens = Column(Integer, default=0)  # Prompt Caching 命中的 Token

    # 成本（USD）
    input_cost = Column(Float, nullable=False)
    output_cost = Column(Float, nullable=False)
    cache_savings = Column(Float, default=0.0)  # 緩存節省的成本
    total_cost = Column(Float, nullable=False, index=True)

    # 任务資訊
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
    成本預算表

    定义團隊/專案的月度預算限制，支持自动預警和限流。
    """
    __tablename__ = "cost_budgets"

    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 預算歸屬
    entity_type = Column(String(20), nullable=False)  # team, project, user
    entity_id = Column(String(100), nullable=False)

    # 預算限制（USD）
    monthly_limit = Column(Float, nullable=False)

    # 預警閾值
    warning_threshold = Column(Float, default=0.8)  # 80% 時發出預警
    critical_threshold = Column(Float, default=0.95)  # 95% 時限流

    # 時間範圍
    effective_from = Column(DateTime, nullable=False)
    effective_to = Column(DateTime, nullable=True)

    # 狀態
    is_active = Column(String(10), default="active")

    # 創建時間
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
    成本告警記錄表

    記錄預算超限告警歷史，支持告警分析和審計。
    """
    __tablename__ = "cost_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # 關聯的預算
    budget_id = Column(Integer, ForeignKey('cost_budgets.id'), nullable=False)
    budget = relationship("CostBudget")

    # 告警級別
    severity = Column(String(20), nullable=False)  # warning, critical

    # 使用情況
    current_usage = Column(Float, nullable=False)
    budget_limit = Column(Float, nullable=False)
    usage_percentage = Column(Float, nullable=False)

    # 告警消息
    message = Column(String(500), nullable=False)

    # 處理狀態
    is_acknowledged = Column(String(10), default="no")
    acknowledged_by = Column(String(100), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<CostAlert(severity={self.severity}, usage={self.usage_percentage:.1f}%)>"
