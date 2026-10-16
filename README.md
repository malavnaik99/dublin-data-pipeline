# Dublin data pipeline

Collects public Dublin open data on a schedule, for free, and (next) models it with dbt + DuckDB.

**Question:** how do weather and time of day change how many Dublinbikes are free at each station?

## Step 1: collection (running)
- [`ingest.py`](ingest.py) runs every ~15 minutes on GitHub Actions ([`ingest.yml`](.github/workflows/ingest.yml)).
- Each run saves a snapshot of every station, plus the latest Dublin weather once an hour, as date-partitioned Parquet in the Hugging Face dataset [Malavnaik/dublin-bikes-weather-raw](https://huggingface.co/datasets/Malavnaik/dublin-bikes-weather-raw). Files are only added, never overwritten.
- After 3 failed runs in a row the workflow disables itself and sends a Telegram alert.
- Cost: €0 (public repo Actions minutes and a free Hugging Face dataset).

## Data sources and licences
- Bikes: Dublinbikes GBFS feed, Dublin City Council / JCDecaux, [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- Weather: Source: Met Éireann, [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

## Tests
```bash
pip install -r requirements.txt
python -m unittest discover -s tests
```
