"""Every run: save one snapshot of every Dublinbikes station (and the latest Dublin weather)
to a public Hugging Face dataset as date-partitioned Parquet. Files are new each run; nothing is overwritten."""
import io, json, os, sys, urllib.request
from datetime import datetime, timezone

import pandas as pd

GBFS = "https://api.cyclocity.fr/contracts/dublin/gbfs/v3/gbfs.json"
# Met Éireann observation stations tried in order; the first that answers is used.
WEATHER = [f"https://prodapi.metweb.ie/observations/{s}/today" for s in ("dublin-airport", "dublin", "phoenix-park", "casement")]
REPO = os.environ.get("HF_DATASET", "Malavnaik/dublin-bikes-weather-raw")

CARD = """---
license: cc-by-4.0
pretty_name: Dublin Bikes + Weather (raw snapshots)
tags: [dublin, bikes, weather, gbfs, time-series]
---
# Dublin Bikes + Weather (raw snapshots)

Raw, untouched snapshots collected every ~15 minutes by [dublin-data-pipeline](https://github.com/malavnaik99/dublin-data-pipeline).

| Folder | What | Source and licence |
|---|---|---|
| `raw/bikes/date=YYYY-MM-DD/HHMMSS.parquet` | Bikes and free stands at every station (one file per run) | Dublinbikes GBFS feed, Dublin City Council / JCDecaux, CC BY 4.0 |
| `raw/stations/date=YYYY-MM-DD/stations.parquet` | Station names, locations and capacity (once a day) | same |
| `raw/weather/date=YYYY-MM-DD/HH.parquet` | Today's hourly observations so far (once an hour) | Met Éireann, CC BY 4.0. "Source: Met Éireann" |

Files are only ever added, never changed. `fetched_at` is UTC. Weather rows repeat across hourly files; deduplicate on date + reportTime.
"""


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "dublin-data-pipeline (github.com/malavnaik99)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def feed_urls(discovery):
    """GBFS v3 lists feeds under data.feeds; v2 under data.<language>.feeds."""
    data = discovery["data"]
    feeds = data.get("feeds") or next(v["feeds"] for v in data.values() if isinstance(v, dict) and "feeds" in v)
    return {f["name"]: f["url"] for f in feeds}


def flat(rows, fetched_at):
    df = pd.json_normalize(rows)
    for c in df.columns:  # nested lists (e.g. vehicle types, multilingual names) stay as JSON text
        if df[c].map(lambda v: isinstance(v, (list, dict))).any():
            df[c] = df[c].map(json.dumps)
    df.insert(0, "fetched_at", fetched_at)
    return df


def parquet(df):
    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    return buf.getvalue()


def main():
    from huggingface_hub import CommitOperationAdd, HfApi
    api = HfApi()
    now = datetime.now(timezone.utc)
    fetched_at = now.isoformat(timespec="seconds")
    day = now.strftime("%Y-%m-%d")
    exists = lambda p: api.file_exists(REPO, p, repo_type="dataset")
    files = {}

    api.create_repo(REPO, repo_type="dataset", exist_ok=True)
    if not exists("README.md"):
        files["README.md"] = CARD.encode()

    urls = feed_urls(get(GBFS))
    stations = get(urls["station_status"])["data"]["stations"]
    if not stations:
        sys.exit("Bike feed returned no stations")
    files[f"raw/bikes/date={day}/{now:%H%M%S}.parquet"] = parquet(flat(stations, fetched_at))
    print(f"Bikes: {len(stations)} stations")

    path = f"raw/stations/date={day}/stations.parquet"
    if not exists(path):
        files[path] = parquet(flat(get(urls["station_information"])["data"]["stations"], fetched_at))

    path = f"raw/weather/date={day}/{now:%H}.parquet"
    if not exists(path):
        for url in WEATHER:  # weather is a bonus: a failure here never stops the bike snapshot
            try:
                rows = get(url)
                if rows:
                    files[path] = parquet(flat(rows, fetched_at))
                    print(f"Weather: {len(rows)} observations from {url}")
                    break
            except Exception as e:
                print(f"Weather not available from {url}: {e}")
        else:
            print("::warning::No weather this run")

    ops = [CommitOperationAdd(p, b) for p, b in files.items()]
    api.create_commit(REPO, ops, commit_message=f"Snapshot {fetched_at}", repo_type="dataset")
    print(f"Saved {len(ops)} file(s) to https://huggingface.co/datasets/{REPO}")


if __name__ == "__main__":
    main()
