"""Read-only continuation boundaries after a user pause; no provider calls."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ECO = Path(__file__).resolve().parents[1] / 'major_revision_v2_3/ecological_v1'
sys.path.insert(0, str(ECO))
import continue_ml_calibration_v3 as ctl


class ContinuationThreeTests(unittest.TestCase):
    def test_snapshot_excludes_both_interrupted_pairs_from_pending(self):
        frozen = {'cases': [{'case_id': 'CAL_BEIJING_04'}],
                  'models': [{'slot': 'agent_1'}, {'slot': 'agent_2'}, {'slot': 'agent_3'}]}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            done = root / 'CAL_BEIJING_04_ingest_agent_1'
            done.mkdir()
            (done / 'request_started.json').write_text('{}', encoding='utf-8')
            (done / 'summary.json').write_text('{}', encoding='utf-8')
            interrupted = root / 'CAL_BEIJING_04_preprocess_agent_3'
            interrupted.mkdir()
            (interrupted / 'request_started.json').write_text('{}', encoding='utf-8')
            completed, active, pending = ctl.snapshot(frozen, root)
            self.assertEqual(list(completed), ['CAL_BEIJING_04_ingest_agent_1'])
            self.assertEqual(list(active), ['CAL_BEIJING_04_preprocess_agent_3'])
            self.assertNotIn('CAL_BEIJING_04_preprocess_agent_3', pending)
            self.assertEqual(len(pending), 10)

    def test_pause_request_is_create_once_and_requires_started_batch(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            started, pause, finished = (root / n for n in
                ('started.json', 'pause.json', 'finished.json'))
            with patch.object(ctl, 'STARTED', started), patch.object(ctl, 'PAUSE_REQUEST', pause), \
                    patch.object(ctl, 'FINISHED', finished):
                with self.assertRaises(ValueError):
                    ctl.request_pause()
                started.write_text('{}', encoding='utf-8')
                ctl.request_pause()
                first = pause.read_bytes()
                ctl.request_pause()
                self.assertEqual(pause.read_bytes(), first)
                self.assertEqual(json.loads(first)['reason'], 'explicit_user_pause')


if __name__ == '__main__':
    unittest.main()
