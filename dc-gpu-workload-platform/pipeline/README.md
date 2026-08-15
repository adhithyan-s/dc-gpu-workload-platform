# pipeline/

- `transforms/` — raw -> curated -> feature-layer transform logic
  (dbt models or PySpark jobs).
- `dags/` — Airflow DAGs orchestrating ingestion -> transform -> training
  on a schedule.
