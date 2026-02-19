# Feast feature-store (local + SQLite)

Учебный проект Feast: 2 FeatureView из `driver_stats.parquet` + 1 OnDemandFeatureView; в ноутбуке показаны historical (train) и online (serve) запросы.

## Состав
- `feature_store/feature_repo/feature_repo.py` — Entity/Source/FeatureView/OnDemand/Service
- `feature_store/feature_repo/feature_store.yaml` — registry + online store (SQLite)
- `feature_store/feature_repo/data/driver_stats.parquet` — offline данные
- `feast_feature_views_demo.ipynb` — примеры запросов

## Команды (Poetry)
Запускать из `feature_store/feature_repo`:

```bash
cd feature_store/feature_repo
poetry run feast apply                          # записать определения в registry (data/registry.db)
poetry run feast materialize 2021-04-11T00:00:00 2021-04-13T00:00:00  # загрузить offline фичи в online store (data/online_store.db)
poetry run feast feature-views list             # показать зарегистрированные FeatureView
poetry run feast ui --port 8889                 # запустить UI (порт можно менять)
```