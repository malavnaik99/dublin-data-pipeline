"""Daily: download the raw snapshots and yesterday's warehouse, run dbt (models + tests), publish the marts.
The DuckDB warehouse file is kept in a Hugging Face dataset so the incremental fact table carries over between runs."""
import json, os, subprocess, sys
from datetime import datetime, timezone

import duckdb
from huggingface_hub import HfApi, hf_hub_download, snapshot_download
from huggingface_hub.errors import EntryNotFoundError, RepositoryNotFoundError

MARTS = os.environ.get("HF_MARTS", "Malavnaik/dublin-bikes-weather-marts")
RAW = os.environ.get("HF_DATASET", "Malavnaik/dublin-bikes-weather-raw")
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
        con.sql(f"COPY {t} TO 'warehouse/marts/{t}.parquet' (FORMAT parquet)")
        counts[t] = con.sql(f"select count(*) from {t}").fetchone()[0]
    newest = con.sql("select max(hour_utc) from fct_station_hour").fetchone()[0]
    con.close()
    log = {"run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "ok": build.returncode == 0,
           "tests_passed": sum(r["status"] == "pass" for r in tests), "tests_total": len(tests),
           "failed": [r["unique_id"].split(".")[2] for r in results if r["status"] in ("fail", "error")],
           "rows": counts, "newest_hour_utc": str(newest)}
    json.dump(log, open("warehouse/run_log.json", "w"), indent=1)
    open("warehouse/README.md", "w").write(CARD)
    print(json.dumps(log, indent=1))
    # Publish even when a check failed, so the run log shows what broke; the workflow then alerts.
    api.upload_folder(repo_id=MARTS, repo_type="dataset", folder_path="warehouse", commit_message=f"dbt run {log['run_at']}")
    sys.exit(build.returncode)


if __name__ == "__main__":
    main()
