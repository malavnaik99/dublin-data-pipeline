"""Make a small Parquet sample of the public marts (last 14 days) for the SQL console on malavnaik.com.
Reads the published tables from the Hugging Face dataset; writes sample/*.parquet and sample/about.json."""
import json

import duckdb
from huggingface_hub import hf_hub_download

MARTS = "Malavnaik/dublin-bikes-weather-marts"
DAYS = 14
con = duckdb.connect()
for t in ("fct_station_hour", "dim_station", "dim_hour"):
    con.execute(f"create view {t}_all as select * from '{hf_hub_download(MARTS, f'marts/{t}.parquet', repo_type='dataset')}'")
# Times are compared and printed inside DuckDB, so Python never converts time-zone timestamps.
con.execute(f"create table fct_station_hour as select * from fct_station_hour_all where hour_utc > (select max(hour_utc) from fct_station_hour_all) - interval {DAYS} day")
con.execute("create table dim_hour as select * from dim_hour_all where hour_utc in (select distinct hour_utc from fct_station_hour)")
con.execute("create table dim_station as select * from dim_station_all")
about = {"source": f"huggingface.co/datasets/{MARTS} (marts/*.parquet)", "days": DAYS,
         "from_utc": con.execute("select strftime(min(hour_utc) at time zone 'UTC', '%Y-%m-%dT%H:%M:%SZ') from fct_station_hour").fetchone()[0],
         "to_utc": con.execute("select strftime(max(hour_utc) at time zone 'UTC', '%Y-%m-%dT%H:%M:%SZ') from fct_station_hour").fetchone()[0],
         "rows": {t: con.execute(f"select count(*) from {t}").fetchone()[0] for t in ("fct_station_hour", "dim_station", "dim_hour")}}
for t in about["rows"]:
    con.execute(f"copy {t} to 'sample/{t}.parquet' (format parquet, compression zstd)")
json.dump(about, open("sample/about.json", "w"), indent=1)
print(json.dumps(about, indent=1))
assert about["rows"]["fct_station_hour"] > 0
