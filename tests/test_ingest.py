import io, json, sys, unittest, urllib.error
from unittest import mock
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ingest


class TestIngest(unittest.TestCase):
    def test_feed_urls_v3_and_v2(self):
        v3 = {"data": {"feeds": [{"name": "station_status", "url": "https://x/s3"}]}}
        v2 = {"data": {"en": {"feeds": [{"name": "station_status", "url": "https://x/s2"}]}}}
        self.assertEqual(ingest.feed_urls(v3)["station_status"], "https://x/s3")
        self.assertEqual(ingest.feed_urls(v2)["station_status"], "https://x/s2")

    def test_flat_keeps_every_station_and_round_trips(self):
        rows = [
            {"station_id": "1", "num_vehicles_available": 4, "num_docks_available": 16, "is_renting": True,
             "vehicle_types_available": [{"vehicle_type_id": "bike", "count": 4}], "last_reported": "2026-10-16T10:00:00Z"},
            {"station_id": "2", "num_vehicles_available": 0, "num_docks_available": 20, "is_renting": False,
             "vehicle_types_available": [], "last_reported": "2026-10-16T10:01:00Z"},
        ]
        df = pd.read_parquet(io.BytesIO(ingest.parquet(ingest.flat(rows, "2026-10-16T10:02:00+00:00"))))
        self.assertEqual(len(df), 2)
        self.assertEqual(df.columns[0], "fetched_at")
        self.assertEqual(json.loads(df.loc[0, "vehicle_types_available"])[0]["count"], 4)
        self.assertEqual(df["num_vehicles_available"].tolist(), [4, 0])

    def test_get_retries_503_but_not_404(self):
        ok = mock.MagicMock()
        ok.__enter__.return_value = io.BytesIO(b'{"a": 1}')
        err = lambda code: urllib.error.HTTPError("u", code, "x", {}, None)
        with mock.patch("urllib.request.urlopen", side_effect=[err(503), err(503), ok]) as op, mock.patch("time.sleep"):
            self.assertEqual(ingest.get("https://x/u"), {"a": 1})
            self.assertEqual(op.call_count, 3)
        with mock.patch("urllib.request.urlopen", side_effect=[err(404)]), mock.patch("time.sleep"):
            self.assertRaises(urllib.error.HTTPError, ingest.get, "https://x/u")
        with mock.patch("urllib.request.urlopen", side_effect=[err(503)] * 4), mock.patch("time.sleep"):
            self.assertRaises(urllib.error.HTTPError, ingest.get, "https://x/u")


if __name__ == "__main__":
    unittest.main()
