import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'major_revision_v2_3/ecological_v1'))
import stage_gate
from public_probe_bundle import public_report


class EcologicalMLLiveGateTests(unittest.TestCase):
    def setup_gate(self, root, rows, corpus='adult'):
        label = root / 'ml_cases/hidden' / corpus / 'test_labels.csv'
        label.parent.mkdir(parents=True)
        label.write_text('row_id,target\na,0\nb,1\nc,1\n', encoding='utf-8')
        path = root / 'ml_preparation/CAL_TEST/verifier/quality_gate.json'
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({'case_id': 'CAL_TEST', 'corpus': corpus,
             'no_provider_calls': True, 'hidden_labels_sha256': stage_gate.sha256(label),
             'quality': {'metric': 'roc_auc', 'quality_floor': 0.75}}), encoding='utf-8')
        predictions = root / 'predictions.csv'
        predictions.write_text('row_id,prediction\n' + rows, encoding='utf-8')
        model = root / 'model.joblib'
        model.write_bytes(b'opaque bytes; never deserialized by this host test')
        return predictions, model

    def test_public_predecessor_report_drops_verifier_scores(self):
        report = {k: 'fixture' for k in ('status','case_id','stage','image_id','source_sha256','artifact_sha256')}
        report.update(verified=True, hidden_validator={'score': 0.99, 'threshold': 0.7}, execution={'private': True})
        result = public_report(report)
        self.assertEqual(len(result), 7)
        self.assertNotIn('hidden_validator', result)
        self.assertNotIn('execution', result)

    def test_numeric_score_uses_opaque_model_bytes_without_loading(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            predictions, model = self.setup_gate(root, 'a,0.1\nb,0.9\nc,0.8\n')
            with patch.object(stage_gate, 'HERE', root), patch.object(stage_gate, 'MAJOR', root):
                self.assertTrue(stage_gate.score('CAL_TEST', predictions, model)['verified'])

    def test_nonfinite_duplicate_out_of_range_and_missing_rows_fail(self):
        for rows in ('a,nan\nb,0.8\nc,0.9\n', 'a,0.1\na,0.8\nc,0.9\n',
                     'a,-1\nb,0.8\nc,0.9\n', 'a,0.1\nb,0.8\n'):
            with self.subTest(rows=rows), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                predictions, model = self.setup_gate(root, rows)
                with patch.object(stage_gate, 'HERE', root), patch.object(stage_gate, 'MAJOR', root):
                    self.assertFalse(stage_gate.score('CAL_TEST', predictions, model)['verified'])

    def test_hidden_label_drift_stops_instrument_before_scoring(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            predictions, model = self.setup_gate(root, 'a,0.1\nb,0.8\nc,0.9\n')
            (root / 'ml_cases/hidden/adult/test_labels.csv').write_text('changed', encoding='utf-8')
            with patch.object(stage_gate, 'HERE', root), patch.object(stage_gate, 'MAJOR', root):
                with self.assertRaisesRegex(ValueError, 'identity changed'):
                    stage_gate.score('CAL_TEST', predictions, model)


if __name__ == '__main__':
    unittest.main()
