# Feast Feature Store (local + SQLite)

Небольшой учебный проект на **Feast**, который показывает базовый workflow:

- описание сущностей и признаков в `feature_repo.py`
- получение **исторических** признаков для обучения (`get_historical_features`)
- получение **online** признаков для инференса (`get_online_features`)
- вычисление **on-demand** признаков (real-time трансформации) через `OnDemandFeatureView`

## Структура

Рекомендуемая структура папки `feature_store/feature_repo`:

```
feature_store/feature_repo/
  feature_store.yaml
  feature_repo.py
  data/
    driver_stats.parquet
    registry.db          # создаётся командой feast apply
    online_store.db      # создаётся/заполняется materialize
```

## Что определено в feature_repo.py

- **Entity**
  - `driver` (join key: `driver_id`)

- **FeatureView**
  - `driver_quality_metrics` — качество/успешность (`conv_rate`, `acc_rate`)
  - `driver_activity_metrics` — активность/нагрузка (`avg_daily_trips`)

- **RequestSource**
  - `request_context` — параметры запроса для нормализации (`mean/std`)

- **OnDemandFeatureView**
  - `driver_realtime_features` — вычисляемые признаки:
    - `conv_rate_z`, `acc_rate_z`
    - `workload_adjusted_quality`

- (Опционально) **FeatureService**
  - `driver_activity_v1` — консистентный набор признаков

## Требования

- Python 3.11
- Feast (версия фиксируется в Poetry)
- Данные: `data/driver_stats.parquet` должны содержать колонки:
  - `driver_id`, `event_timestamp`, `conv_rate`, `acc_rate`, `avg_daily_trips`
  - (опционально) `created` — если её нет, уберите `created_timestamp_column` в `FileSource`

## Установка (Poetry)

```bash
poetry install
poetry shell
```

Проверить версию Feast:

```bash
python -c "import feast; print(feast.__version__)"
feast version
```

## Применить определения (registry)

Выполнять из директории, где лежит `feature_store.yaml`:

```bash
cd feature_store/feature_repo
poetry run feast apply
```

После этого появится/обновится файл:

- `data/registry.db`

## Заполнить online store (materialize)

Данные примера находятся в диапазоне около `2021-04-12`, поэтому окно materialize должно покрывать эти даты:

```bash
cd feature_store/feature_repo
poetry run feast materialize 2021-04-11T00:00:00 2021-04-13T00:00:00
```

После этого появится/обновится файл:

- `data/online_store.db`

## Быстрая проверка online-фич

```bash
cd feature_store/feature_repo
poetry run python -c "from feast import FeatureStore; s=FeatureStore('.'); print(s.get_online_features(features=['driver_quality_metrics:conv_rate','driver_quality_metrics:acc_rate','driver_activity_metrics:avg_daily_trips'], entity_rows=[{'driver_id':1001},{'driver_id':1002}]).to_dict())"
```

Если вместо значений будут `None`, значит online store ещё не заполнен (или materialize был не на тот диапазон дат).

## Ноутбук

Пример ноутбука:
- `feast_feature_views_demo_no_val_to_add.ipynb`

В нём показано:
- `get_historical_features` (для обучения) — базовые FV + on-demand
- `get_online_features` (для инференса) — базовые FV из online store

## Полезные команды

Список FeatureView:

```bash
cd feature_store/feature_repo
poetry run feast feature-views list
```

Запуск UI (если нужно):

```bash
cd feature_store/feature_repo
poetry run feast ui
```

> Если порт занят (например, 8888), можно попробовать:
> `poetry run feast ui --port 8889`

## Troubleshooting

### `feast: command not found`
Запускайте через Poetry:

```bash
poetry run feast apply
```

или войдите в окружение:

```bash
poetry shell
feast apply
```

### Online-фичи возвращают `None`
Проверьте, что:
1) `feast apply` выполнен в правильной папке
2) `feast materialize ...` выполнен на диапазон дат, который реально есть в parquet
