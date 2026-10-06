"""A main bundle must not inherit calibration's trusted predecessors."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ECO = Path(__file__).resolve().parents[1] / 'major_revision_v2_3/ecological_v1'
sys.path.insert(0, str(ECO))
from main_artifact_chain_v1 import sha256
from main_live_ml_bundle_v1 import build_main_prompt, copy_public_only


class MainLiveMLBundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.prepared = self.root / 'prepared'
        public = self.prepared / 'public'
        (public / 'input').mkdir(parents=True)
        digests = {}
        for name in ('train', 'validation', 'test_features'):
            path = public / 'input' / (name + '.csv')
            path.write_text('row_id,x\n1,2\n', encoding='utf-8')
            digests[name] = sha256(path)
        (public / 'bundle_manifest.json').write_text(json.dumps({
            'case_id': 'MAIN_ADULT_01', 'split': 'main',
            'corpus': 'adult', 'excluded_features': [],
            'design_sha256': 'a' * 64, 'hidden_labels_included': False,
            'public_input_sha256': digests}), encoding='utf-8')
        (self.prepared / 'summary.json').write_text(json.dumps({
            'case_id': 'MAIN_ADULT_01', 'no_provider_calls': True,
            'paid_execution_allowed': False,
            'public_input_sha256': digests}), encoding='utf-8')
        self.destination = self.root / 'main' / 'R1' / 'CF_FIT' / 'MAIN_ADULT_01'
        self.destination.parent.mkdir(parents=True)
        self.kwargs = {'allowed_root': self.root / 'main', 'run_id': 'R1',
                       'arm_id': 'CF_FIT', 'case_id': 'MAIN_ADULT_01',
                       'design_sha256': 'a' * 64}

    def test_only_public_input_is_copied(self):
        copy_public_only(self.prepared, self.destination, **self.kwargs)
        self.assertTrue((self.destination / 'input/train.csv').is_file())
        self.assertEqual(list((self.destination / 'dag_output').iterdir()), [])
        self.assertEqual(list((self.destination / 'submission').iterdir()), [])
        self.assertFalse((self.destination / 'verifier').exists())
        with self.assertRaises(FileExistsError):
            copy_public_only(self.prepared, self.destination, **self.kwargs)

    def test_hidden_labels_or_trusted_files_are_rejected(self):
        (self.prepared / 'public/hidden_labels.csv').write_text('secret', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'unexpected'):
            copy_public_only(self.prepared, self.destination, **self.kwargs)

    def test_wrong_scope_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'workspace'):
            copy_public_only(self.prepared, self.root / 'elsewhere', **self.kwargs)

    def test_prompt_exposes_only_same_arm_verified_predecessors(self):
        copy_public_only(self.prepared, self.destination, **self.kwargs)
        scope = {key: self.kwargs[key] for key in ('run_id', 'arm_id', 'case_id')}
        prompt = build_main_prompt(self.destination, 'ingest', **scope)
        self.assertIn('268435456 bytes', prompt)
        with self.assertRaisesRegex(ValueError, 'predecessor'):
            build_main_prompt(self.destination, 'preprocess', **scope)
