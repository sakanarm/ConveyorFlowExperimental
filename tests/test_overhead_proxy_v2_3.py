import sys
import unittest
from pathlib import Path


MAJOR = Path(__file__).resolve().parents[1] / "major_revision_v2_3"
sys.path.insert(0, str(MAJOR))

from measure_overhead_proxy_v1 import _percentile, summarize
from measure_overhead_load_v1 import summarize as summarize_load


class OverheadProxyTests(unittest.TestCase):
    def test_linear_percentile(self):
        self.assertEqual(_percentile([4.0, 1.0, 3.0, 2.0], 0.5), 2.5)

    def test_summary_preserves_paired_difference(self):
        rows = [
            {"local_ms": 1.0, "central_ms": 2.0,
             "central_minus_local_ms": 1.0},
            {"local_ms": 3.0, "central_ms": 2.0,
             "central_minus_local_ms": -1.0},
        ]
        result = summarize(rows, seed=7)
        self.assertEqual(result["pairs"], 2)
        self.assertEqual(result["paired_mean_central_minus_local_ms"], 0.0)
        self.assertEqual(result["negative_pair_differences"], 1)
        self.assertTrue(result["not_provider_latency"])
        self.assertTrue(result["not_real_outage_evidence"])

    def test_load_summary_requires_balanced_sessions(self):
        settings = {"concurrent_clients": [2], "repetitions_per_level": 1}
        rows = [{"clients": 2, "repetition": 0, "route": "local",
                 "median_ms": 1.0}]
        with self.assertRaises(ValueError):
            summarize_load(rows, settings)
        rows.append({"clients": 2, "repetition": 0, "route": "central",
                     "median_ms": 1.5})
        result = summarize_load(rows, settings)
        self.assertEqual(result["load_levels"][0]["median_paired_session_difference_ms"],
                         0.5)


if __name__ == "__main__":
    unittest.main()
