# Dublin data pipeline

Collects public Dublin open data on a schedule, models it with dbt + DuckDB and tests it, for free.

**Question:** how do weather and time of day change how many Dublinbikes are free at each station?

## How it works
1. **Collect** ([`ingest.py`](ingest.py), every ~15 minutes, [`ingest.yml`](.github/workflows/ingest.yml)): a snapshot of every station, plus the Dublin weather once an hour, as date-partitioned Parquet in the Hugging Face dataset [Malavnaik/dublin-bikes-weather-raw](https://huggingface.co/datasets/Malavnaik/dublin-bikes-weather-raw). Files are only added, never overwritten. After 3 failed runs in a row the workflow disables itself and sends a Telegram alert.
2. **Model** ([`dbt/`](dbt), daily, [`transform.yml`](.github/workflows/transform.yml) via [`transform.py`](transform.py)): dbt on DuckDB.
   - `staging`: types, UTC time stamps, de-duplication (`stg_bikes`, `stg_stations`, `stg_weather`)
   - `intermediate`: `int_bikes_hourly`, station x hour
   - `marts` (star schema): `fct_station_hour` (incremental, idempotent: recomputes the last 3 hours), `dim_station`, `dim_hour` (Dublin local time + weather)
3. **Test**: 14 dbt data tests on every run, including **freshness** (newest data < 2 h old) and **volume** (≥ 75% of the expected snapshots in 24 h). A failure sends a Telegram alert.
4. **Publish**: the DuckDB warehouse, the marts as Parquet, `run_log.json` and `dashboard.json` go to [Malavnaik/dublin-bikes-weather-marts](https://huggingface.co/datasets/Malavnaik/dublin-bikes-weather-marts) (the warehouse file carries the incremental state between runs). [dbt docs with lineage](https://huggingface.co/spaces/Malavnaik/dublin-bikes-dbt-docs). The [live dashboard](https://malavnaik99.github.io/projects/dublin-bikes-pipeline/) reads `dashboard.json` directly.

**Cost: €0.** Public-repo GitHub Actions minutes, free Hugging Face datasets and a static Space; a free cron-job.org job starts the collector every 15 minutes.

## Data sources and licences
- Bikes: Dublinbikes GBFS feed, Dublin City Council / JCDecaux, [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- Weather: Source: Met Éireann, [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

## Tests
```bash
pip install -r requirements.txt dbt-duckdb
python -m unittest discover -s tests          # collector
cd dbt && dbt build --profiles-dir .           # models + data tests (needs ../raw_data/raw from the HF dataset)
```
