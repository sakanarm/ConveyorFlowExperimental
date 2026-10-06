import importlib
from pathlib import Path
import sys
import tempfile
import unittest

ECO = Path(__file__).resolve().parents[1] / 'major_revision_v2_3/ecological_v1'
sys.path.insert(0, str(ECO))
continuation = importlib.import_module('continue_ml_calibration')


class ContinuationTests(unittest.TestCase):
    def plan(self):
        return {'cases': [{'case_id': 'CAL_ADULT_01'}], 'models': [{'slot': 'agent_1'}]}

    def test_missing_only(self):
        with tempfile.TemporaryDirectory() as folder:
            started, pending = continuation.classify_pairs(self.plan(), Path(folder))
            self.assertFalse(started)
            self.assertEqual(len(pending), 4)

    def test_started_summary_never_selected(self):
        with tempfile.TemporaryDirectory() as folder:
            job = Path(folder) / 'CAL_ADULT_01_ingest_agent_1'
            job.mkdir()
            for name in ('summary.json', 'request_started.json'):
                (job / name).write_text('{}', encoding='utf-8')
            started, pending = continuation.classify_pairs(self.plan(), Path(folder))
            self.assertEqual(len(started), 1)
            self.assertNotIn(job.name, pending)

    def test_incomplete_request_stops(self):
        with tempfile.TemporaryDirectory() as folder:
            job = Path(folder) / 'CAL_ADULT_01_ingest_agent_1'
            job.mkdir()
            (job / 'request_started.json').write_text('{}', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'no final summary'):
                continuation.classify_pairs(self.plan(), Path(folder))

    def test_partial_prepare_stops(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / 'CAL_ADULT_01_ingest_agent_1').mkdir()
            with self.assertRaisesRegex(ValueError, 'Partial preparation'):
                continuation.classify_pairs(self.plan(), Path(folder))
