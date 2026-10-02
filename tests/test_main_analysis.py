from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from analyze_main import (  # noqa: E402
    METRICS,
    bootstrap_ci,
    difference_in_differences_rows,
    holm_adjust,
    midranks,
    wilcoxon_signed_rank,
)


class MainAnalysisTests(unittest.TestCase):
    def test_midranks_handle_ties(self) -> None:
        self.assertEqual(midranks([1.0, 1.0, 3.0]), [1.5, 1.5, 3.0])

    def test_wilcoxon_direction(self) -> None:
        _, p_value, effect = wilcoxon_signed_rank([1, 2, 3, 4, 5])
        self.assertGreater(effect, 0)
        self.assertLess(p_value, 0.10)

    def test_holm_is_monotone_and_bounded(self) -> None:
        rows = [
            {"family": "R", "metric": "m", "p_value": value}
            for value in (0.01, 0.03, 0.20)
        ]
        holm_adjust(rows)
        adjusted = [row["p_holm"] for row in rows]
        self.assertEqual(adjusted, [0.03, 0.06, 0.20])

    def test_bootstrap_is_deterministic(self) -> None:
        first = bootstrap_ci([1, 2, 3, 4, 5], salt="test")
        second = bootstrap_ci([1, 2, 3, 4, 5], salt="test")
        self.assertEqual(first, second)

    def test_difference_in_differences_uses_matched_seed_cells(self) -> None:
        def rows(cf_value: float, control_value: float) -> list[dict]:
            output = []
            for seed in range(5):
                for strategy, value in (("CF_FIT", cf_value), ("S1", control_value)):
                    row = {"seed": seed, "strategy": strategy}
                    row.update({metric: value for metric in METRICS})
                    output.append(row)
            return output

        result = difference_in_differences_rows(
            family="TEST",
            contrast="left_minus_right",
            policy="CF_FIT",
            comparator="S1",
            left_context=rows(10.0, 6.0),
            right_context=rows(7.0, 5.0),
            keys=("seed",),
            stratum="test",
        )
        self.assertEqual(len(result), len(METRICS))
        self.assertTrue(
            all(row["paired_seed_median_difference"] == 2.0 for row in result)
        )


if __name__ == "__main__":
    unittest.main()
