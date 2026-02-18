# feature_repo.py
# -*- coding: utf-8 -*-
"""
Feature repository for Feast (local provider + SQLite online store).

Содержит:
- Entity: driver (driver_id)
- FileSource: data/driver_stats.parquet (event_timestamp, created*)
- 2 FeatureView:
    1) driver_quality_metrics (conv_rate, acc_rate)
    2) driver_activity_metrics (avg_daily_trips)
- 1 RequestSource: request_context (mean/std для real-time нормализации)
- 1 OnDemandFeatureView: driver_realtime_features (создаёт новые признаки на лету)
- (Опционально) FeatureService: driver_activity_v1

*Если в parquet нет колонки `created`, удалите параметр created_timestamp_column.
"""

import os
from datetime import timedelta

import numpy as np
import pandas as pd

from feast import Entity, FeatureService, FeatureView, Field, FileSource, RequestSource
from feast.on_demand_feature_view import on_demand_feature_view
from feast.types import Float32, Float64, Int64

# ----------------------------
# Paths
# ----------------------------
REPO_PATH = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(REPO_PATH, "data")

# ----------------------------
# Entity
# ----------------------------
driver = Entity(
    name="driver",
    join_keys=["driver_id"],
    description="Сущность водитель (ключ: driver_id)",
)

# ----------------------------
# Offline source (parquet)
# ----------------------------
driver_stats_source = FileSource(
    name="driver_stats_source",
    path=os.path.join(DATA_PATH, "driver_stats.parquet"),
    timestamp_field="event_timestamp",
    created_timestamp_column="created",  # удалите, если колонки 'created' нет
)

# ============================================================
# 2 FeatureView (логически связанные наборы признаков)
# ============================================================

# 1) Quality: метрики качества/успешности
driver_quality_metrics = FeatureView(
    name="driver_quality_metrics",
    entities=[driver],
    ttl=timedelta(days=1),
    schema=[
        Field(name="conv_rate", dtype=Float32, description="Конверсия/успешность"),
        Field(name="acc_rate", dtype=Float32, description="Acceptance rate"),
    ],
    online=True,
    source=driver_stats_source,
    tags={"domain": "quality", "team": "driver_performance"},
)

# 2) Activity: метрики активности/нагрузки
driver_activity_metrics = FeatureView(
    name="driver_activity_metrics",
    entities=[driver],
    ttl=timedelta(days=1),
    schema=[
        Field(name="avg_daily_trips", dtype=Int64, description="Среднее число поездок в день"),
    ],
    online=True,
    source=driver_stats_source,
    tags={"domain": "activity", "team": "driver_performance"},
)

# ============================================================
# RequestSource: данные, доступные только во время запроса
# (в historical retrieval — приходят как колонки в entity_df)
# ============================================================
request_context = RequestSource(
    name="request_context",
    schema=[
        Field(name="conv_rate_mean", dtype=Float64),
        Field(name="conv_rate_std", dtype=Float64),
        Field(name="acc_rate_mean", dtype=Float64),
        Field(name="acc_rate_std", dtype=Float64),
    ],
)

# ============================================================
# 1 On-Demand Feature View (real-time вычисления)
# ============================================================
@on_demand_feature_view(
    sources=[driver_quality_metrics, driver_activity_metrics, request_context],
    schema=[
        Field(name="conv_rate_z", dtype=Float64),
        Field(name="acc_rate_z", dtype=Float64),
        Field(name="workload_adjusted_quality", dtype=Float64),
    ],
)
def driver_realtime_features(inputs: pd.DataFrame) -> pd.DataFrame:
    """
    Real-time признаки на основе:
    - базовых признаков из FeatureView (conv_rate, acc_rate, avg_daily_trips)
    - контекста запроса из RequestSource (mean/std)

    В historical retrieval request-поля должны присутствовать колонками в entity_df.
    """
    out = pd.DataFrame(index=inputs.index)

    # Z-score нормализация (защита от std=0)
    conv_std = inputs["conv_rate_std"].replace(0, np.nan).astype(float)
    acc_std = inputs["acc_rate_std"].replace(0, np.nan).astype(float)

    out["conv_rate_z"] = (
        (inputs["conv_rate"].astype(float) - inputs["conv_rate_mean"].astype(float)) / conv_std
    ).fillna(0.0)
    out["acc_rate_z"] = (
        (inputs["acc_rate"].astype(float) - inputs["acc_rate_mean"].astype(float)) / acc_std
    ).fillna(0.0)

    # Качество с учётом нагрузки
    base_quality = inputs["conv_rate"].astype(float) * 0.6 + inputs["acc_rate"].astype(float) * 0.4
    workload_factor = 1.0 / (1.0 + np.log1p(inputs["avg_daily_trips"].astype(float)))
    out["workload_adjusted_quality"] = (base_quality * workload_factor).astype(float)

    return out

# ============================================================
# FeatureService (опционально)
# ============================================================
driver_activity_v1 = FeatureService(
    name="driver_activity_v1",
    features=[
        driver_quality_metrics,
        driver_activity_metrics,
        driver_realtime_features,
    ],
)
