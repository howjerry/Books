# 第 8 章：個人化與適應性學習：讓 Agent 越用越聰明

> 本章學習目標：
> - 設計多維度的使用者偏好模型
> - 實作隱式反饋收集與解釋機制
> - 建立偏好的持續學習與更新系統
> - 掌握個人化效果的評估方法

---

## 8.1 為什麼需要個人化？

每個使用者都是獨特的。一個真正智慧的 Agent 應該能夠：

- 記住使用者的溝通風格偏好
- 了解使用者的專業領域
- 適應使用者的工作習慣
- 從互動中持續學習

### 8.1.1 個人化的價值

```
無個人化:
使用者 A（工程師）：「解釋 Kubernetes」
Agent：「Kubernetes 是一個容器編排平台...」（簡潔技術說明）

使用者 B（產品經理）：「解釋 Kubernetes」
Agent：「Kubernetes 是一個容器編排平台...」（同樣的回答）

有個人化:
使用者 A（工程師）：「解釋 Kubernetes」
Agent：「K8s 的核心組件包括 Pod、Service、Deployment...」（技術細節）

使用者 B（產品經理）：「解釋 Kubernetes」
Agent：「Kubernetes 讓我們能更高效地部署和管理應用...」（業務視角）
```

---

## 8.2 使用者偏好的多維度建模

```python
# personalization/preference_model.py
"""
使用者偏好模型
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime


@dataclass
class UserPreference:
    """
    使用者偏好模型
    ‹1› 多維度追蹤使用者偏好
    """
    user_id: str

    # ‹2› 風格偏好
    response_length: float = 0.0        # -1 (簡潔) 到 1 (詳細)
    formality: float = 0.0              # -1 (非正式) 到 1 (正式)
    technical_depth: float = 0.0        # -1 (淺顯) 到 1 (深入)

    # ‹3› 內容偏好
    topic_weights: Dict[str, float] = field(default_factory=dict)
    preferred_formats: List[str] = field(default_factory=list)  # markdown, bullets, code

    # ‹4› 行為偏好
    active_hours: List[int] = field(default_factory=list)
    preferred_tools: Dict[str, float] = field(default_factory=dict)
    tool_success_rates: Dict[str, float] = field(default_factory=dict)

    # ‹5› 學習狀態
    interaction_count: int = 0
    confidence: float = 0.1  # 偏好模型的信心度
    last_updated: datetime = field(default_factory=datetime.now)


class PreferenceModelingSystem:
    """
    偏好建模系統
    ‹6› 從使用者行為中學習偏好
    """

    def __init__(self, db_pool, learning_rate: float = 0.1):
        self.db = db_pool
        self.learning_rate = learning_rate

    async def get_preference(self, user_id: str) -> UserPreference:
        """獲取使用者偏好"""
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM user_preferences WHERE user_id = $1",
                user_id
            )
            if row:
                return self._row_to_preference(row)
            return self._get_default_preference(user_id)

    async def update_from_interaction(
        self,
        user_id: str,
        interaction: Dict[str, Any]
    ):
        """
        從互動中更新偏好
        ‹7› 使用指數移動平均 (EMA)
        """
        pref = await self.get_preference(user_id)
        changes = self._infer_preference_changes(interaction)

        # EMA 更新
        for dimension, change in changes.items():
            if hasattr(pref, dimension):
                current = getattr(pref, dimension)
                new_value = (1 - self.learning_rate) * current + self.learning_rate * change
                setattr(pref, dimension, new_value)

        # 更新信心度
        pref.confidence = min(1.0, pref.confidence + 0.01)
        pref.interaction_count += 1

        await self._save_preference(pref)

    def _infer_preference_changes(
        self,
        interaction: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        從互動推斷偏好變化
        ‹8› 隱式反饋解釋
        """
        changes = {}

        # 分析回應長度偏好
        if "user_requested_brief" in interaction:
            changes["response_length"] = -0.2
        elif "user_requested_detailed" in interaction:
            changes["response_length"] = 0.2

        # 分析反饋
        if interaction.get("feedback") == "positive":
            # 強化當前設定
            changes["confidence_boost"] = 0.05
        elif interaction.get("feedback") == "negative":
            # 可能需要調整
            changes["confidence_boost"] = -0.02

        # 分析停留時間
        dwell_time = interaction.get("dwell_time_seconds", 0)
        if dwell_time < 5:
            changes["topic_relevance"] = -0.1
        elif dwell_time > 60:
            changes["topic_relevance"] = 0.1

        return changes
```

---

## 8.3 隱式反饋的收集與解釋

```python
# personalization/feedback_collector.py
"""
隱式反饋收集器
"""


class ImplicitFeedbackCollector:
    """
    隱式反饋收集器
    ‹1› 不打擾使用者的情況下收集反饋信號
    """

    def __init__(self, event_store):
        self.events = event_store

    async def record_interaction(
        self,
        user_id: str,
        session_id: str,
        interaction_type: str,
        data: Dict[str, Any]
    ):
        """
        記錄互動事件
        ‹2› 儲存原始事件用於後續分析
        """
        event = {
            "user_id": user_id,
            "session_id": session_id,
            "type": interaction_type,
            "timestamp": datetime.now(),
            "data": data
        }
        await self.events.store(event)

    async def analyze_session_feedback(
        self,
        user_id: str,
        session_id: str
    ) -> Dict[str, Any]:
        """
        分析會話中的隱式反饋
        ‹3› 從行為模式中提取信號
        """
        events = await self.events.get_session_events(session_id)

        signals = {
            "satisfaction_score": 0.5,
            "engagement_level": "medium",
            "inferred_preferences": {}
        }

        # 分析回應時間
        response_times = [e["data"].get("response_time") for e in events if "response_time" in e.get("data", {})]
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            if avg_response_time < 2:
                signals["engagement_level"] = "high"
            elif avg_response_time > 10:
                signals["engagement_level"] = "low"

        # 分析會話長度
        if len(events) > 10:
            signals["satisfaction_score"] += 0.1
        elif len(events) < 3:
            signals["satisfaction_score"] -= 0.1

        # 分析是否有明確的正面/負面信號
        for event in events:
            if event["type"] == "explicit_feedback":
                if event["data"].get("rating", 0) > 3:
                    signals["satisfaction_score"] += 0.2
                elif event["data"].get("rating", 0) < 3:
                    signals["satisfaction_score"] -= 0.2

        return signals
```

---

## 8.4 偏好模型的訓練與更新

```python
# personalization/preference_updater.py
"""
偏好更新系統
"""


class PreferenceUpdater:
    """
    偏好更新器
    ‹1› 根據反饋調整偏好模型
    """

    def __init__(
        self,
        preference_system: PreferenceModelingSystem,
        feedback_collector: ImplicitFeedbackCollector
    ):
        self.prefs = preference_system
        self.feedback = feedback_collector

    async def process_session_end(
        self,
        user_id: str,
        session_id: str,
        conversation: List[Dict]
    ):
        """
        會話結束時處理
        ‹2› 分析會話並更新偏好
        """
        # 收集隱式反饋
        signals = await self.feedback.analyze_session_feedback(user_id, session_id)

        # 分析對話模式
        patterns = self._analyze_conversation_patterns(conversation)

        # 更新偏好
        await self.prefs.update_from_interaction(user_id, {
            **signals,
            **patterns
        })

    def _analyze_conversation_patterns(
        self,
        conversation: List[Dict]
    ) -> Dict[str, Any]:
        """
        分析對話模式
        ‹3› 從對話中提取偏好信號
        """
        patterns = {}

        # 分析使用者訊息長度
        user_messages = [m["content"] for m in conversation if m["role"] == "user"]
        if user_messages:
            avg_length = sum(len(m) for m in user_messages) / len(user_messages)
            if avg_length < 50:
                patterns["user_prefers_concise"] = True
            elif avg_length > 200:
                patterns["user_prefers_detailed"] = True

        # 分析是否有追問（表示回答不夠清楚）
        follow_up_count = 0
        for i, msg in enumerate(conversation[:-1]):
            if msg["role"] == "user":
                next_msg = conversation[i + 1]
                if next_msg["role"] == "assistant" and i + 2 < len(conversation):
                    after_next = conversation[i + 2]
                    if after_next["role"] == "user" and "?" in after_next["content"]:
                        follow_up_count += 1

        if follow_up_count > 2:
            patterns["needs_clearer_answers"] = True

        return patterns
```

---

## 8.5 冷啟動策略

```python
# personalization/cold_start.py
"""
冷啟動策略
"""


class ColdStartHandler:
    """
    冷啟動處理器
    ‹1› 處理新使用者的偏好初始化
    """

    def __init__(self, preference_system: PreferenceModelingSystem):
        self.prefs = preference_system

    async def initialize_user(
        self,
        user_id: str,
        initial_context: Dict[str, Any] = None
    ) -> UserPreference:
        """
        初始化新使用者
        ‹2› 基於上下文設定初始偏好
        """
        pref = UserPreference(user_id=user_id)

        if initial_context:
            # 根據職位調整
            role = initial_context.get("role", "").lower()
            if "engineer" in role or "developer" in role:
                pref.technical_depth = 0.3
                pref.formality = -0.2
            elif "manager" in role or "director" in role:
                pref.response_length = -0.2
                pref.formality = 0.3
            elif "analyst" in role:
                pref.technical_depth = 0.2

            # 根據部門調整
            dept = initial_context.get("department", "").lower()
            if "engineering" in dept:
                pref.topic_weights["technology"] = 0.7
            elif "sales" in dept:
                pref.topic_weights["business"] = 0.7
            elif "hr" in dept:
                pref.topic_weights["policy"] = 0.7

        await self.prefs._save_preference(pref)
        return pref

    async def onboard_questions(self) -> List[Dict[str, Any]]:
        """
        引導問題
        ‹3› 可選的主動收集偏好
        """
        return [
            {
                "question": "你希望回答的詳細程度如何？",
                "options": ["簡潔扼要", "適中", "詳細深入"],
                "maps_to": "response_length",
                "values": [-0.5, 0, 0.5]
            },
            {
                "question": "你的主要工作領域是？",
                "options": ["技術開發", "產品管理", "業務銷售", "行政支援"],
                "maps_to": "domain_preference",
                "values": ["engineering", "product", "business", "admin"]
            }
        ]
```

---

## 8.6 個人化的評估指標

```python
# personalization/evaluation.py
"""
個人化效果評估
"""


class PersonalizationEvaluator:
    """
    個人化評估器
    ‹1› 量化個人化效果
    """

    async def calculate_metrics(
        self,
        user_id: str,
        period_days: int = 30
    ) -> Dict[str, float]:
        """
        計算個人化指標
        ‹2› 多維度評估
        """
        return {
            "satisfaction_score": await self._calc_satisfaction(user_id, period_days),
            "engagement_rate": await self._calc_engagement(user_id, period_days),
            "task_completion_rate": await self._calc_completion(user_id, period_days),
            "preference_stability": await self._calc_stability(user_id, period_days)
        }

    async def run_ab_test(
        self,
        experiment_name: str,
        control_group: List[str],
        treatment_group: List[str],
        metric: str = "satisfaction_score"
    ) -> Dict[str, Any]:
        """
        A/B 測試
        ‹3› 比較個人化效果
        """
        control_metrics = [
            await self.calculate_metrics(uid) for uid in control_group
        ]
        treatment_metrics = [
            await self.calculate_metrics(uid) for uid in treatment_group
        ]

        control_avg = sum(m[metric] for m in control_metrics) / len(control_metrics)
        treatment_avg = sum(m[metric] for m in treatment_metrics) / len(treatment_metrics)

        improvement = (treatment_avg - control_avg) / control_avg * 100

        return {
            "experiment": experiment_name,
            "control_avg": control_avg,
            "treatment_avg": treatment_avg,
            "improvement_pct": improvement,
            "statistically_significant": improvement > 5  # 簡化判斷
        }
```

---

## 8.7 隱私保護與使用者控制

```python
# personalization/privacy.py
"""
個人化隱私保護
"""


class PersonalizationPrivacy:
    """
    個人化隱私管理
    ‹1› 讓使用者掌控自己的偏好資料
    """

    async def get_preference_summary(self, user_id: str) -> Dict[str, Any]:
        """
        獲取偏好摘要
        ‹2› 讓使用者了解系統對他的理解
        """
        pref = await self.prefs.get_preference(user_id)

        return {
            "response_style": self._describe_response_style(pref),
            "topics_of_interest": list(pref.topic_weights.keys()),
            "interaction_count": pref.interaction_count,
            "data_collected_since": pref.last_updated.isoformat()
        }

    async def reset_preferences(self, user_id: str) -> bool:
        """
        重置偏好
        ‹3› 使用者可以重新開始
        """
        default_pref = self.prefs._get_default_preference(user_id)
        await self.prefs._save_preference(default_pref)
        return True

    async def adjust_preference(
        self,
        user_id: str,
        dimension: str,
        value: float
    ) -> bool:
        """
        手動調整偏好
        ‹4› 使用者可以主動修改
        """
        pref = await self.prefs.get_preference(user_id)
        if hasattr(pref, dimension):
            setattr(pref, dimension, value)
            await self.prefs._save_preference(pref)
            return True
        return False
```

---

## 8.8 總結與下一步

### 本章回顧

1. **設計了多維度偏好模型**：風格、內容、行為偏好
2. **實作了隱式反饋收集**：停留時間、互動模式、會話分析
3. **建立了偏好更新機制**：EMA 更新、信心度追蹤
4. **解決了冷啟動問題**：上下文初始化、引導問題
5. **掌握了評估方法**：滿意度、參與度、A/B 測試

### 下一章預告

在第 9 章「多模態記憶」中，我們將學習處理文本、圖像、程式碼等多種資料類型的記憶系統。

---

完整程式碼請參見 `code-examples/chapter-08/` 目錄。
