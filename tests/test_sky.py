import sys, unittest
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import transform


class TestSky(unittest.TestCase):
    def test_leaves_out_placeholder_and_zero_dock_stations(self):
        con = duckdb.connect()
        con.execute("""create table dim_station as select * from (values
            (1, 'PARNELL SQUARE NORTH', 53.35374, -6.2653, 0),
            (2, 'STATION118', 53.3, -6.2, 20),
            (3, 'SMITHFIELD', 53.3477, -6.2782, 30)) t(station_id, station_name, lat, lon, capacity)""")
        con.execute("alter table dim_station alter lat type double; alter table dim_station alter lon type double")
        con.execute("create table dim_hour as select timestamp '2026-11-16 09:00' hour_utc, timestamp '2026-11-16 09:00' hour_local")
        con.execute("create table fct_station_hour as select * from (values (1, timestamp '2026-11-16 09:00', 4.0), (3, timestamp '2026-11-16 09:00', 12.4)) t(station_id, hour_utc, avg_bikes)")
        d = transform.sky(con)
        self.assertEqual(d["stations"], [["Smithfield", 53.3477, -6.2782, 30]])
        self.assertEqual(d["bikes"], [[12]])


if __name__ == "__main__":
    unittest.main()
