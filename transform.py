"""Daily: download the raw snapshots and yesterday's warehouse, run dbt (models + tests), publish the marts.
The DuckDB warehouse file is kept in a Hugging Face dataset so the incremental fact table carries over between runs."""
import json, os, subprocess, sys
from datetime import datetime, timezone

import duckdb
from huggingface_hub import HfApi, hf_hub_download, snapshot_download
from huggingface_hub.errors import EntryNotFoundError, RepositoryNotFoundError

MARTS = os.environ.get("HF_MARTS", "Malavnaik/dublin-bikes-weather-marts")
RAW = os.environ.get("HF_DATASET", "Malavnaik/dublin-bikes-weather-raw")
DOCS = "Malavnaik/dublin-bikes-dbt-docs"  # static Space with the dbt docs and lineage graph
CARD = """---
license: cc-by-4.0
pretty_name: Dublin Bikes + Weather (modelled)
tags: [dublin, bikes, weather, dbt, duckdb]
---
# Dublin Bikes + Weather (modelled)

Daily output of the dbt models in [dublin-data-pipeline](https://github.com/malavnaik99/dublin-data-pipeline), built from
[the raw snapshots](https://huggingface.co/datasets/Malavnaik/dublin-bikes-weather-raw).

| File | Grain |
|---|---|
| `marts/fct_station_hour.parquet` | one row per station per hour: average/min/max bikes, free docks, share of time empty/full |
| `marts/dim_station.parquet` | one row per station: name, location, capacity |
| `marts/dim_hour.parquet` | one row per hour: Dublin local time, weekday, weather |
| `run_log.json` | the latest run: time, row counts, tests passed |
| `dublin.duckdb` | the whole warehouse (DuckDB file) |

Sources: Dublinbikes GBFS feed, Dublin City Council / JCDecaux, CC BY 4.0; weather: Source: Met Éireann, CC BY 4.0.
"""


def dashboard(con):
    """Small summary the website's dashboard reads directly from Hugging Face."""
    q = lambda sql: [dict(zip([d[0] for d in r.description], row)) for r in [con.execute(sql)] for row in r.fetchall()]
    base = """from fct_station_hour f join dim_station s using (station_id) join dim_hour h using (hour_utc)
              where s.capacity > 0
                and f.station_id in (select station_id from fct_station_hour group by 1 having max(max_bikes) > 0)"""
    # ^ leaves out stations that never had a bike in the period (e.g. a placeholder "STATION118" that is always empty)
    return {
        "summary": q(f"""select count(distinct f.station_id) AS stations, count(distinct f.hour_utc) AS n_hours,
                        min(h.local_date) AS first_day, max(h.local_date) AS last_day,
                        round(avg(f.share_empty) * 100, 1) pct_time_empty {base}""")[0],
        "by_local_hour": q(f"""select h.local_hour, h.is_weekend,
                              round(avg(f.avg_bikes / s.capacity) * 100, 1) pct_bikes_available,
                              round(avg(f.share_empty) * 100, 1) pct_time_empty
                              {base} group by all order by 2, 1"""),
        "rain": q(f"""select case when h.rainfall_mm > 0 then 'raining' else 'dry' end as weather, count(distinct f.hour_utc) AS n_hours,
                     round(avg(f.avg_bikes / s.capacity) * 100, 1) pct_bikes_available
                     {base} and h.rainfall_mm is not null group by 1 order by 1"""),
        "most_often_empty": q(f"""select s.station_name, round(avg(f.share_empty) * 100, 1) pct_time_empty
                                 {base} group by 1 order by 2 desc limit 10"""),
    }


def main():
    api = HfApi()
    snapshot_download(RAW, repo_type="dataset", local_dir="raw_data", allow_patterns=["raw/*"])
    os.makedirs("warehouse", exist_ok=True)
    api.create_repo(MARTS, repo_type="dataset", exist_ok=True)
    try:
        hf_hub_download(MARTS, "dublin.duckdb", repo_type="dataset", local_dir="warehouse")
    except (EntryNotFoundError, RepositoryNotFoundError):
        print("No warehouse yet: full build")

    build = subprocess.run(["dbt", "build", "--profiles-dir", "."], cwd="dbt")
    results = json.load(open("dbt/target/run_results.json"))["results"]
    tests = [r for r in results if r["unique_id"].startswith("test.")]
    con = duckdb.connect("warehouse/dublin.duckdb")
    os.makedirs("warehouse/marts", exist_ok=True)
    counts = {}
    for t in ["fct_station_hour", "dim_station", "dim_hour"]:
        con.execute(f"COPY {t} TO 'warehouse/marts/{t}.parquet' (FORMAT parquet)")
        counts[t] = con.execute(f"select count(*) from {t}").fetchone()[0]
    newest = con.execute("select max(hour_utc) from fct_station_hour").fetchone()[0]
    dash = dashboard(con)
    json.dump(dash, open("warehouse/dashboard.json", "w"), indent=1, default=str)
    print("DASHBOARD", json.dumps(dash, default=str))
    con.close()
    log = {"run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "ok": build.returncode == 0,
           "tests_passed": sum(r["status"] == "pass" for r in tests), "tests_total": len(tests),
           "failed": [r["unique_id"].split(".")[2] for r in results if r["status"] in ("fail", "error")],
           "rows": counts, "newest_hour_utc": str(newest)}
    json.dump(log, open("warehouse/run_log.json", "w"), indent=1)
    open("warehouse/README.md", "w").write(CARD)
    print(json.dumps(log, indent=1))
    if subprocess.run(["dbt", "docs", "generate", "--static"], cwd="dbt").returncode == 0:
        api.create_repo(DOCS, repo_type="space", space_sdk="static", exist_ok=True)
        api.update_repo_settings(DOCS, repo_type="space", private=False)  # approved by Malav on 21 Oct
        api.upload_file(path_or_fileobj="dbt/target/static_index.html", path_in_repo="index.html",
                        repo_id=DOCS, repo_type="space", commit_message="dbt docs")
    # Publish even when a check failed, so the run log shows what broke; the workflow then alerts.
    api.upload_folder(repo_id=MARTS, repo_type="dataset", folder_path="warehouse", commit_message=f"dbt run {log['run_at']}")
    sys.exit(build.returncode)


if __name__ == "__main__":
    main()
