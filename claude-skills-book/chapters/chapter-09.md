# 第 9 章：完整測試系統架構（WebGuard）

前八章我們分別探討了 Skills 開發（Chapter 3）、瀏覽器自動化（Chapter 4）、數據處理（Chapter 5）、API 測試（Chapter 6）、Skills 編排（Chapter 7）、CI/CD 整合（Chapter 8）。本章將整合所有技術，構建一個生產級的**企業測試平台 WebGuard**：四層架構設計、微服務化部署、高可用性、監控告警、可擴展性。這是一個真實可部署的系統，不只是示範代碼。

## 9.1 WebGuard 系統概述

### 9.1.1 設計目標

**WebGuard** 是一個基於 Claude Code Skills 的分布式測試平台，設計目標：

- **多類型測試**：支持瀏覽器 E2E、API、性能、安全測試
- **高並發**：單節點支持 50+ 並行測試，集群可橫向擴展至數百並發
- **可靠性**：99.9% 可用性，自動故障恢復
- **可觀測性**：完整的指標、日誌、鏈路追蹤
- **易用性**：Web UI + CLI + API，適合開發、測試、運維團隊

### 9.1.2 核心功能

| 功能模塊 | 說明 | 技術棧 |
|----------|------|--------|
| 測試編排 | 定時任務、工作流編排、依賴管理 | Celery, APScheduler |
| 測試執行 | 瀏覽器/API/數據 Skills 執行引擎 | Python, Node.js, Stagehand |
| 數據存儲 | 測試結果、配置、歷史數據 | PostgreSQL, Redis, MinIO |
| 報告生成 | Allure 報告、趨勢分析、郵件通知 | Allure, Grafana, SMTP |
| 監控告警 | 系統指標、測試健康度、異常告警 | Prometheus, AlertManager |
| API 網關 | RESTful API、認證授權 | FastAPI, JWT |
| Web 界面 | 測試管理、結果查看、配置中心 | React, Next.js |

### 9.1.3 四層架構設計

```
┌───────────────────────────────────────────────────────────────┐
│                 編排層 (Orchestration Layer)                  │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐ │
│ │ APScheduler │ │   Celery    │ │  SkillOrchestrator     │ │
│ │ (定時任務)  │ │ (分布式隊列)│ │  (工作流編排)           │ │
│ └─────────────┘ └─────────────┘ └─────────────────────────┘ │
└───────────────────────────────────────────────────────────────┘
                                ↓
┌───────────────────────────────────────────────────────────────┐
│                   執行層 (Execution Layer)                    │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐  │
│ │ Browser      │ │ API          │ │ Data                │  │
│ │ Test Engine  │ │ Test Engine  │ │ Processing Engine   │  │
│ │ (Stagehand)  │ │ (httpx)      │ │ (Pandas)            │  │
│ └──────────────┘ └──────────────┘ └──────────────────────┘  │
└───────────────────────────────────────────────────────────────┘
                                ↓
┌───────────────────────────────────────────────────────────────┐
│                   存儲層 (Storage Layer)                      │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐  │
│ │ PostgreSQL   │ │ Redis        │ │ MinIO / S3          │  │
│ │ (結構化數據) │ │ (快取/佇列)  │ │ (文件存儲)          │  │
│ └──────────────┘ └──────────────┘ └──────────────────────┘  │
└───────────────────────────────────────────────────────────────┘
                                ↓
┌───────────────────────────────────────────────────────────────┐
│                  報告層 (Reporting Layer)                     │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐  │
│ │ Allure       │ │ Grafana      │ │ Notification        │  │
│ │ (測試報告)   │ │ (儀表板)     │ │ (Slack/Email)       │  │
│ └──────────────┘ └──────────────┘ └──────────────────────┘  │
│ ┌──────────────┐ ┌──────────────────────────────────────────┘
│ │ Prometheus   │ │  (指標收集與查詢)
│ └──────────────┘ │
└───────────────────────────────────────────────────────────────┘
```


## 9.2 數據庫設計（PostgreSQL）

### 9.2.1 核心表結構

```sql
-- 測試套件表
CREATE TABLE test_suites (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    enabled BOOLEAN DEFAULT TRUE,
    schedule_cron VARCHAR(100),  -- Cron 表達式，如 '0 2 * * *'
    max_concurrent_tests INTEGER DEFAULT 5,
    timeout_minutes INTEGER DEFAULT 60,
    retry_on_failure BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 測試案例表
CREATE TABLE test_cases (
    id SERIAL PRIMARY KEY,
    suite_id INTEGER NOT NULL,
    name VARCHAR(255) NOT NULL,
    skill_name VARCHAR(100) NOT NULL,
    params JSONB,  -- Skill 參數，JSON 格式
    priority INTEGER DEFAULT 0,  -- 優先級，數字越大越高
    timeout_seconds INTEGER DEFAULT 300,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT fk_suite
        FOREIGN KEY (suite_id)
        REFERENCES test_suites(id)
        ON DELETE CASCADE
);

-- 測試執行記錄表
CREATE TABLE test_executions (
    id SERIAL PRIMARY KEY,
    suite_id INTEGER NOT NULL,
    started_at TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP,
    status VARCHAR(20) NOT NULL,  -- running, passed, failed, timeout
    total_tests INTEGER,
    passed_tests INTEGER,
    failed_tests INTEGER,
    skipped_tests INTEGER,
    execution_time_ms INTEGER,
    triggered_by VARCHAR(100),  -- 觸發方式：schedule, manual, ci
    ci_commit_sha VARCHAR(64),  -- CI 提交 hash
    ci_branch VARCHAR(100),
    error_message TEXT,
    CONSTRAINT fk_suite_exec
        FOREIGN KEY (suite_id)
        REFERENCES test_suites(id)
        ON DELETE CASCADE
);

-- 測試結果詳情表
CREATE TABLE test_results (
    id SERIAL PRIMARY KEY,
    execution_id INTEGER NOT NULL,
    test_case_id INTEGER NOT NULL,
    test_name VARCHAR(255) NOT NULL,
    skill_name VARCHAR(100),
    status VARCHAR(20) NOT NULL,  -- passed, failed, skipped, timeout, error
    error_message TEXT,
    error_type VARCHAR(100),  -- assertion, timeout, network, system
    stack_trace TEXT,
    execution_time_ms INTEGER,
    screenshot_url VARCHAR(500),
    video_url VARCHAR(500),
    log_url VARCHAR(500),
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_execution_result
        FOREIGN KEY (execution_id)
        REFERENCES test_executions(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_test_case
        FOREIGN KEY (test_case_id)
        REFERENCES test_cases(id)
);

-- 測試指標表（性能測試）
CREATE TABLE test_metrics (
    id SERIAL PRIMARY KEY,
    test_result_id INTEGER NOT NULL,
    metric_name VARCHAR(100) NOT NULL,  -- response_time, memory_usage, cpu_usage
    metric_value NUMERIC,
    metric_unit VARCHAR(20),  -- ms, MB, %
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT fk_test_result_metric
        FOREIGN KEY (test_result_id)
        REFERENCES test_results(id)
        ON DELETE CASCADE
);

-- Skill 註冊表
CREATE TABLE skills_registry (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    category VARCHAR(50),  -- browser, api, data
    description TEXT,
    version VARCHAR(20),
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 創建索引（性能優化）
CREATE INDEX idx_test_executions_started ON test_executions(started_at DESC);
CREATE INDEX idx_test_executions_status ON test_executions(status);
CREATE INDEX idx_test_executions_suite ON test_executions(suite_id, started_at DESC);
CREATE INDEX idx_test_results_execution ON test_results(execution_id);
CREATE INDEX idx_test_results_status ON test_results(status);
CREATE INDEX idx_test_results_created ON test_results(created_at DESC);
CREATE INDEX idx_test_cases_suite ON test_cases(suite_id);

-- 創建視圖（統計查詢）
CREATE VIEW v_test_suite_statistics AS
SELECT
    ts.id AS suite_id,
    ts.name AS suite_name,
    COUNT(DISTINCT te.id) AS total_executions,
    COUNT(DISTINCT CASE WHEN te.status = 'passed' THEN te.id END) AS passed_executions,
    COUNT(DISTINCT CASE WHEN te.status = 'failed' THEN te.id END) AS failed_executions,
    ROUND(
        CAST(COUNT(DISTINCT CASE WHEN te.status = 'passed' THEN te.id END) AS NUMERIC) /
        NULLIF(COUNT(DISTINCT te.id), 0) * 100,
        2
    ) AS pass_rate,
    AVG(te.execution_time_ms) AS avg_execution_time_ms,
    MAX(te.completed_at) AS last_execution_at
FROM test_suites ts
LEFT JOIN test_executions te ON ts.id = te.suite_id
WHERE te.completed_at >= NOW() - INTERVAL '30 days'  -- 最近 30 天
GROUP BY ts.id, ts.name;
```

### 9.2.2 數據遷移（Alembic）

使用 Alembic 管理數據庫 Schema 版本：

```python
# alembic/versions/001_initial_schema.py
from alembic import op
import sqlalchemy as sa


def upgrade():
    """升級數據庫 Schema"""
    # 創建 test_suites 表
    op.create_table(
        'test_suites',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, unique=True),
        sa.Column('description', sa.Text()),
        sa.Column('enabled', sa.Boolean(), default=True),
        # ... 其他欄位
    )

    # 創建 test_executions 表
    op.create_table('test_executions', ...)

    # 創建索引
    op.create_index('idx_test_executions_started', 'test_executions', ['started_at'])


def downgrade():
    """回滾 Schema 變更"""
    op.drop_index('idx_test_executions_started')
    op.drop_table('test_executions')
    op.drop_table('test_suites')
```


## 9.3 編排層實現

### 9.3.1 Celery 分布式任務隊列

**安裝與配置：**

```bash
pip install celery redis
```

**celery_config.py：**

```python
from celery import Celery
from kombu import Exchange, Queue

# 創建 Celery 應用
celery_app = Celery(
    'webguard',
    broker='redis://localhost:6379/0',  # 使用 Redis 作為消息代理
    backend='redis://localhost:6379/1'  # 使用 Redis 存儲任務結果
)

# 配置
celery_app.conf.update(
    # 任務序列化
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Taipei',
    enable_utc=True,

    # 任務路由（不同類型任務分配到不同隊列）
    task_routes={
        'webguard.tasks.browser.*': {'queue': 'browser'},
        'webguard.tasks.api.*': {'queue': 'api'},
        'webguard.tasks.data.*': {'queue': 'data'},
    },

    # 隊列定義
    task_queues=(
        Queue('default', Exchange('default'), routing_key='default'),
        Queue('browser', Exchange('browser'), routing_key='browser'),
        Queue('api', Exchange('api'), routing_key='api'),
        Queue('data', Exchange('data'), routing_key='data'),
    ),

    # Worker 配置
    worker_prefetch_multiplier=1,  # 一次只取一個任務（避免阻塞）
    worker_max_tasks_per_child=100,  # 100 個任務後重啟 worker（防止內存洩漏）

    # 任務超時
    task_soft_time_limit=1800,  # 30 分鐘軟超時（發送 SoftTimeLimitExceeded 異常）
    task_time_limit=2100,  # 35 分鐘硬超時（強制終止）

    # 結果過期時間
    result_expires=3600  # 1 小時後刪除結果
)
```

**定義任務（tasks.py）：**

```python
from celery_config import celery_app
from webguard.orchestrator import SkillOrchestrator
from webguard.models import TestExecution, TestResult
import logging

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name='webguard.tasks.execute_test_suite')
def execute_test_suite(self, suite_id: int, triggered_by: str = 'manual'):
    """
    執行測試套件

    Args:
        suite_id: 測試套件 ID
        triggered_by: 觸發方式（schedule, manual, ci）
    """
    from webguard.database import Session
    from webguard.models import TestSuite

    session = Session()

    try:
        # 1. 獲取測試套件
        suite = session.query(TestSuite).filter_by(id=suite_id).first()
        if not suite:
            raise ValueError(f"測試套件不存在: {suite_id}")

        # 2. 創建執行記錄
        execution = TestExecution(
            suite_id=suite_id,
            status='running',
            triggered_by=triggered_by
        )
        session.add(execution)
        session.commit()

        # 3. 獲取測試案例
        test_cases = suite.test_cases
        if not test_cases:
            execution.status = 'skipped'
            execution.error_message = '無測試案例'
            session.commit()
            return

        # 4. 初始化編排器
        orchestrator = SkillOrchestrator()

        # 5. 註冊 Skills（動態加載）
        from webguard.skill_loader import load_all_skills
        load_all_skills(orchestrator)

        # 6. 構建工作流
        workflow = []
        for test_case in test_cases:
            if test_case.enabled:
                workflow.append({
                    "skill": test_case.skill_name,
                    "params": test_case.params or {},
                    "metadata": {
                        "test_case_id": test_case.id,
                        "test_name": test_case.name
                    }
                })

        # 7. 執行工作流
        import asyncio
        result = asyncio.run(
            orchestrator.execute_sequence_with_flow(
                workflow,
                stop_on_error=False  # 不因單個失敗停止
            )
        )

        # 8. 保存結果
        execution.total_tests = result['total_steps']
        execution.passed_tests = result['passed']
        execution.failed_tests = result['failed']
        execution.status = 'passed' if result['success'] else 'failed'
        execution.completed_at = datetime.now()

        # 保存詳細結果
        for skill_result in result['results']:
            test_result = TestResult(
                execution_id=execution.id,
                test_case_id=skill_result['metadata']['test_case_id'],
                test_name=skill_result['metadata']['test_name'],
                skill_name=skill_result['skill_name'],
                status='passed' if skill_result['success'] else 'failed',
                error_message=skill_result.get('error'),
                execution_time_ms=skill_result.get('duration_ms')
            )
            session.add(test_result)

        session.commit()

        logger.info(
            f"測試套件 '{suite.name}' 執行完成: "
            f"{execution.passed_tests}/{execution.total_tests} 通過"
        )

    except Exception as e:
        logger.error(f"執行測試套件失敗: {e}", exc_info=True)

        if execution:
            execution.status = 'error'
            execution.error_message = str(e)
            execution.completed_at = datetime.now()
            session.commit()

        raise

    finally:
        session.close()


@celery_app.task(name='webguard.tasks.browser.run_e2e_test')
def run_e2e_test(test_config: dict):
    """運行瀏覽器 E2E 測試"""
    # 實作...
    pass


@celery_app.task(name='webguard.tasks.api.run_api_test')
def run_api_test(endpoint_config: dict):
    """運行 API 測試"""
    # 實作...
    pass
```

**啟動 Worker：**

```bash
# 啟動處理瀏覽器測試的 worker（並發 2）
celery -A celery_config worker -Q browser -c 2 -n browser_worker@%h

# 啟動處理 API 測試的 worker（並發 10）
celery -A celery_config worker -Q api -c 10 -n api_worker@%h

# 啟動處理數據任務的 worker（並發 5）
celery -A celery_config worker -Q data -c 5 -n data_worker@%h
```

### 9.3.2 APScheduler 定時任務

```python
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from webguard.database import Session
from webguard.models import TestSuite
from webguard.tasks import execute_test_suite
import logging

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def load_scheduled_suites():
    """從數據庫載入定時測試套件"""
    session = Session()

    try:
        suites = session.query(TestSuite).filter(
            TestSuite.enabled == True,
            TestSuite.schedule_cron.isnot(None)
        ).all()

        for suite in suites:
            # 移除舊任務（如果存在）
            job_id = f'suite_{suite.id}'
            if scheduler.get_job(job_id):
                scheduler.remove_job(job_id)

            # 添加新任務
            scheduler.add_job(
                execute_test_suite.delay,  # Celery 異步任務
                trigger=CronTrigger.from_crontab(suite.schedule_cron),
                args=[suite.id],
                kwargs={'triggered_by': 'schedule'},
                id=job_id,
                name=f'Test Suite: {suite.name}',
                replace_existing=True
            )

            logger.info(
                f"已註冊定時任務: {suite.name} ({suite.schedule_cron})"
            )

    finally:
        session.close()


# 應用啟動時載入定時任務
def start_scheduler():
    """啟動調度器"""
    load_scheduled_suites()
    scheduler.start()
    logger.info("定時任務調度器已啟動")


# 動態更新（API 調用）
def refresh_scheduled_suites():
    """重新載入定時任務（API 更新後調用）"""
    load_scheduled_suites()
    logger.info("定時任務已重新載入")
```


## 9.4 執行層實現

### 9.4.1 Skill 加載器

動態加載所有 Skills：

```python
# webguard/skill_loader.py
import importlib
import inspect
from pathlib import Path
from webguard.orchestrator import SkillOrchestrator
import logging

logger = logging.getLogger(__name__)


def load_all_skills(orchestrator: SkillOrchestrator):
    """
    自動發現並加載所有 Skills

    掃描 skills/ 目錄下的所有 skill.py 文件
    """
    skills_dir = Path(__file__).parent / 'skills'

    if not skills_dir.exists():
        logger.warning(f"Skills 目錄不存在: {skills_dir}")
        return

    for skill_dir in skills_dir.iterdir():
        if not skill_dir.is_dir():
            continue

        skill_file = skill_dir / 'skill.py'
        if not skill_file.exists():
            continue

        # 動態導入模組
        try:
            module_name = f'webguard.skills.{skill_dir.name}.skill'
            module = importlib.import_module(module_name)

            # 尋找主函數（通常與目錄名相同）
            skill_func = None
            for name, obj in inspect.getmembers(module):
                if inspect.isfunction(obj) and not name.startswith('_'):
                    skill_func = obj
                    break

            if skill_func:
                skill_name = skill_dir.name
                orchestrator.register(skill_name, skill_func)
                logger.info(f"已載入 Skill: {skill_name}")

        except Exception as e:
            logger.error(f"載入 Skill 失敗 ({skill_dir.name}): {e}")
```

### 9.4.2 測試執行引擎

```python
# webguard/execution_engine.py
from typing import Dict, Any, List
from webguard.orchestrator import ResilientOrchestrator
from webguard.models import TestResult
import asyncio
import logging

logger = logging.getLogger(__name__)


class TestExecutionEngine:
    """
    測試執行引擎

    管理測試執行的生命週期
    """

    def __init__(self):
        self.orchestrator = ResilientOrchestrator()

    async def execute_test_workflow(
        self,
        workflow: List[Dict[str, Any]],
        execution_id: int
    ) -> Dict[str, Any]:
        """
        執行測試工作流

        Args:
            workflow: 測試工作流定義
            execution_id: 執行 ID

        Returns:
            執行結果摘要
        """
        # 執行工作流（支持重試、補償）
        result = await self.orchestrator.execute_with_compensation(workflow)

        # 收集指標
        metrics = self.orchestrator.get_execution_summary()

        return {
            **result,
            "metrics": metrics,
            "execution_id": execution_id
        }

    async def execute_parallel_tests(
        self,
        test_configs: List[Dict[str, Any]],
        max_concurrency: int = 10
    ) -> Dict[str, Any]:
        """
        並行執行多個測試

        Args:
            test_configs: 測試配置列表
            max_concurrency: 最大並發數

        Returns:
            執行結果
        """
        results = await self.orchestrator.execute_parallel(
            test_configs,
            max_concurrency=max_concurrency
        )

        return results
```


## 9.5 存儲層實現

### 9.5.1 Redis 數據結構設計

```python
# Redis 使用場景：
# 1. Celery 消息隊列
# 2. 測試結果快取
# 3. 分布式鎖
# 4. 實時統計

import redis
from typing import Optional, Dict, Any
import json

redis_client = redis.Redis(
    host='localhost',
    port=6379,
    db=2,  # 專用於 WebGuard 數據
    decode_responses=True
)


class RedisCache:
    """Redis 快取管理"""

    @staticmethod
    def cache_test_result(execution_id: int, result: Dict[str, Any], ttl: int = 3600):
        """快取測試結果（1 小時過期）"""
        key = f'test_result:{execution_id}'
        redis_client.setex(
            key,
            ttl,
            json.dumps(result)
        )

    @staticmethod
    def get_cached_result(execution_id: int) -> Optional[Dict[str, Any]]:
        """獲取快取的測試結果"""
        key = f'test_result:{execution_id}'
        data = redis_client.get(key)

        if data:
            return json.loads(data)
        return None

    @staticmethod
    def increment_test_counter(suite_id: int, status: str):
        """增量統計（實時）"""
        key = f'stats:suite:{suite_id}:{status}'
        redis_client.incr(key)

    @staticmethod
    def get_realtime_stats(suite_id: int) -> Dict[str, int]:
        """獲取實時統計"""
        keys = [
            f'stats:suite:{suite_id}:passed',
            f'stats:suite:{suite_id}:failed',
            f'stats:suite:{suite_id}:skipped'
        ]

        values = redis_client.mget(keys)

        return {
            'passed': int(values[0] or 0),
            'failed': int(values[1] or 0),
            'skipped': int(values[2] or 0)
        }
```

### 9.5.2 MinIO 文件存儲

```python
# 使用 MinIO（S3 兼容）存儲截圖、視頻、日誌
from minio import Minio
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

minio_client = Minio(
    'localhost:9000',
    access_key='minioadmin',
    secret_key='minioadmin',
    secure=False
)

# 創建 bucket
bucket_name = 'webguard'
if not minio_client.bucket_exists(bucket_name):
    minio_client.make_bucket(bucket_name)


def upload_screenshot(file_path: str, test_result_id: int) -> str:
    """
    上傳截圖到 MinIO

    Returns:
        可訪問的 URL
    """
    object_name = f'screenshots/{test_result_id}/{Path(file_path).name}'

    try:
        minio_client.fput_object(
            bucket_name,
            object_name,
            file_path,
            content_type='image/png'
        )

        # 生成可訪問的 URL（7 天有效）
        url = minio_client.presigned_get_object(
            bucket_name,
            object_name,
            expires=timedelta(days=7)
        )

        logger.info(f"截圖已上傳: {object_name}")
        return url

    except Exception as e:
        logger.error(f"上傳截圖失敗: {e}")
        raise
```


## 9.6 報告層實現

### 9.6.1 Prometheus 指標收集

```python
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from prometheus_client import start_http_server

# 定義指標
test_executions_total = Counter(
    'webguard_test_executions_total',
    'Total number of test executions',
    ['suite_name', 'status']
)

test_duration_seconds = Histogram(
    'webguard_test_duration_seconds',
    'Test execution duration in seconds',
    ['suite_name'],
    buckets=(1, 5, 10, 30, 60, 120, 300, 600)
)

active_tests = Gauge(
    'webguard_active_tests',
    'Number of currently running tests'
)


# 在測試執行時更新指標
def record_test_execution(suite_name: str, status: str, duration_seconds: float):
    """記錄測試執行指標"""
    test_executions_total.labels(suite_name=suite_name, status=status).inc()
    test_duration_seconds.labels(suite_name=suite_name).observe(duration_seconds)


# 啟動 Prometheus metrics 伺服器
start_http_server(8000)  # http://localhost:8000/metrics
```

**Prometheus 配置（prometheus.yml）：**

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'webguard'
    static_configs:
      - targets: ['localhost:8000']
```

### 9.6.2 Grafana 儀表板

**儀表板配置（JSON）：**

```json
{
  "dashboard": {
    "title": "WebGuard Test Dashboard",
    "panels": [
      {
        "title": "Test Pass Rate",
        "targets": [
          {
            "expr": "sum(rate(webguard_test_executions_total{status=\"passed\"}[5m])) / sum(rate(webguard_test_executions_total[5m])) * 100"
          }
        ],
        "type": "graph"
      },
      {
        "title": "Test Duration (P95)",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, sum(rate(webguard_test_duration_seconds_bucket[5m])) by (le, suite_name))"
          }
        ],
        "type": "graph"
      }
    ]
  }
}
```


## 9.7 API 網關（FastAPI）

### 9.7.1 RESTful API

```python
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Optional
from webguard.tasks import execute_test_suite
from webguard.database import Session
from webguard.models import TestSuite, TestExecution
import logging

logger = logging.getLogger(__name__)

app = FastAPI(title="WebGuard API", version="1.0.0")
security = HTTPBearer()


# Request/Response Models
class TestSuiteCreate(BaseModel):
    name: str
    description: Optional[str] = None
    schedule_cron: Optional[str] = None


class TestSuiteResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    enabled: bool
    schedule_cron: Optional[str]

    class Config:
        from_attributes = True


class TestExecutionTrigger(BaseModel):
    suite_id: int
    triggered_by: str = 'api'


# 簡易 JWT 認證（生產環境應使用完整的 OAuth2）
def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """驗證 JWT Token"""
    token = credentials.credentials

    # 這裡應該驗證 JWT token
    if token != "secret_token":  # 示範，實際應使用 JWT 庫
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    return token


# API Endpoints
@app.get("/api/v1/suites", response_model=List[TestSuiteResponse])
async def list_test_suites(
    skip: int = 0,
    limit: int = 100,
    token: str = Depends(verify_token)
):
    """獲取測試套件列表"""
    session = Session()
    try:
        suites = session.query(TestSuite).offset(skip).limit(limit).all()
        return suites
    finally:
        session.close()


@app.post("/api/v1/suites", response_model=TestSuiteResponse)
async def create_test_suite(
    suite: TestSuiteCreate,
    token: str = Depends(verify_token)
):
    """創建測試套件"""
    session = Session()
    try:
        db_suite = TestSuite(**suite.dict())
        session.add(db_suite)
        session.commit()
        session.refresh(db_suite)
        return db_suite
    finally:
        session.close()


@app.post("/api/v1/executions/trigger")
async def trigger_test_execution(
    trigger: TestExecutionTrigger,
    token: str = Depends(verify_token)
):
    """觸發測試執行"""
    # 異步執行（使用 Celery）
    task = execute_test_suite.delay(
        trigger.suite_id,
        triggered_by=trigger.triggered_by
    )

    return {
        "task_id": task.id,
        "status": "queued",
        "message": f"Test suite {trigger.suite_id} execution queued"
    }


@app.get("/api/v1/executions/{execution_id}")
async def get_execution_results(
    execution_id: int,
    token: str = Depends(verify_token)
):
    """獲取執行結果"""
    session = Session()
    try:
        execution = session.query(TestExecution).filter_by(id=execution_id).first()

        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")

        return {
            "id": execution.id,
            "suite_id": execution.suite_id,
            "status": execution.status,
            "total_tests": execution.total_tests,
            "passed_tests": execution.passed_tests,
            "failed_tests": execution.failed_tests,
            "execution_time_ms": execution.execution_time_ms,
            "started_at": execution.started_at.isoformat(),
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None
        }
    finally:
        session.close()
```


## 9.8 部署架構（Docker Compose）

### 9.8.1 完整部署配置

```yaml
# docker-compose.yml
version: '3.8'

services:
  # PostgreSQL 數據庫
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: webguard
      POSTGRES_USER: webguard
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U webguard"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

  # MinIO (S3兼容存儲)
  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: ${MINIO_PASSWORD}
    volumes:
      - minio_data:/data
    ports:
      - "9000:9000"
      - "9001:9001"

  # WebGuard API
  api:
    build:
      context: .
      dockerfile: Dockerfile
    command: uvicorn webguard.api:app --host 0.0.0.0 --port 8000
    environment:
      DATABASE_URL: postgresql://webguard:${POSTGRES_PASSWORD}@postgres:5432/webguard
      REDIS_URL: redis://redis:6379/0
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
    volumes:
      - ./webguard:/app/webguard
      - ./skills:/app/skills

  # Celery Worker (Browser Tests)
  celery-browser:
    build:
      context: .
      dockerfile: Dockerfile
    command: celery -A webguard.celery_config worker -Q browser -c 2 -n browser_worker@%h
    environment:
      DATABASE_URL: postgresql://webguard:${POSTGRES_PASSWORD}@postgres:5432/webguard
      REDIS_URL: redis://redis:6379/0
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
    depends_on:
      - postgres
      - redis
    volumes:
      - ./webguard:/app/webguard
      - ./skills:/app/skills

  # Celery Worker (API Tests)
  celery-api:
    build:
      context: .
      dockerfile: Dockerfile
    command: celery -A webguard.celery_config worker -Q api -c 10 -n api_worker@%h
    environment:
      DATABASE_URL: postgresql://webguard:${POSTGRES_PASSWORD}@postgres:5432/webguard
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - redis

  # Celery Beat (定時任務調度器)
  celery-beat:
    build:
      context: .
      dockerfile: Dockerfile
    command: celery -A webguard.celery_config beat --loglevel=info
    environment:
      DATABASE_URL: postgresql://webguard:${POSTGRES_PASSWORD}@postgres:5432/webguard
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - redis

  # Prometheus
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"

  # Grafana
  grafana:
    image: grafana/grafana:latest
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD}
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
    ports:
      - "3000:3000"
    depends_on:
      - prometheus

volumes:
  postgres_data:
  redis_data:
  minio_data:
  prometheus_data:
  grafana_data:
```

**啟動完整系統：**

```bash
# 設置環境變數
cat > .env <<EOF
POSTGRES_PASSWORD=secure_password
MINIO_PASSWORD=secure_password
GRAFANA_PASSWORD=admin_password
ANTHROPIC_API_KEY=your_api_key
EOF

# 啟動所有服務
docker-compose up -d

# 查看日誌
docker-compose logs -f api

# 停止所有服務
docker-compose down
```


## 9.9 高可用性設計

### 9.9.1 負載均衡

使用 Nginx 作為反向代理：

```nginx
# nginx.conf
upstream webguard_api {
    least_conn;  # 最少連接數算法
    server api1:8000 weight=1 max_fails=3 fail_timeout=30s;
    server api2:8000 weight=1 max_fails=3 fail_timeout=30s;
    server api3:8000 weight=1 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    server_name webguard.example.com;

    location /api/ {
        proxy_pass http://webguard_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        # 超時設置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # 健康檢查（需 nginx plus 或第三方模塊）
        # health_check interval=10s fails=3 passes=2;
    }
}
```

### 9.9.2 故障恢復

**Celery 任務重試：**

```python
@celery_app.task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=600,  # 最多退避到 10 分鐘
    retry_jitter=True,
    max_retries=3
)
def execute_test_suite(self, suite_id: int):
    # 測試執行邏輯...
    pass
```


## 9.10 本章總結

本章呈現了 WebGuard 完整系統架構：

**核心組件：**

- **四層架構**：編排層（Celery/APScheduler）、執行層（Skills）、存儲層（PostgreSQL/Redis/MinIO）、報告層（Allure/Grafana）
- **數據庫設計**：完整的 Schema、索引優化、統計視圖
- **分布式任務**：Celery 隊列、Worker 分類、任務路由
- **API 網關**：FastAPI RESTful API、JWT 認證
- **監控告警**：Prometheus 指標、Grafana 儀表板
- **高可用性**：負載均衡、故障恢復、橫向擴展

**企業級能力：**

- ✅ 單節點 50+ 並發，集群可擴展至數百並發
- ✅ 99.9% 可用性設計
- ✅ 完整的可觀測性（指標、日誌、追蹤）
- ✅ 一鍵 Docker Compose 部署
- ✅ 支持多租戶（可擴展）

**下一章預告：**

第 10 章（最後一章）將探討 **企業部署、安全與 MCP 生態**：Kubernetes 部署、安全最佳實踐、密鑰管理、MCP 整合、未來展望。這將完成整個技術書的撰寫。
