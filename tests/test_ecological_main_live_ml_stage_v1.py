"""Paid main seam fails closed and replay excludes the current output."""
from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest.mock import patch

ECO = Path(__file__).resolve().parents[1] / 'major_revision_v2_3/ecological_v1'
sys.path.insert(0, str(ECO))
from main_artifact_chain_v1 import ARTIFACT, SCRIPT, sha256
from main_live_ml_stage_v1 import (execute_stage_once, make_replay_bundle,
                                   require_paid_lock)


class LiveMLStageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle = self.root / 'bundle'
        self.scope = {'bundle': self.bundle, 'run_id': 'R1', 'arm_id': 'CF_FIT',
                      'case_id': 'MAIN_ADULT_01', 'stage': 'ingest',
                      'model_slot': 'agent_1'}

    def test_no_paid_confirmation_rejects_before_other_checks(self):
        with self.assertRaisesRegex(PermissionError, 'confirmation'):
            require_paid_lock(self.root / 'missing.json', confirm_paid=False,
                              **self.scope)

    def test_no_frozen_lock_rejects_even_with_confirmation(self):
        with self.assertRaisesRegex(ValueError, 'lock is missing'):
            require_paid_lock(self.root / 'missing.json', confirm_paid=True,
                              **self.scope)

    def test_fresh_replay_copies_only_public_and_verified_parent_state(self):
        (self.bundle / 'input').mkdir(parents=True)
        (self.bundle / 'input/train.csv').write_text('row_id,x\n1,2\n', encoding='utf-8')
        (self.bundle / 'submission').mkdir()
        (self.bundle / 'submission/preprocess_split.py').write_text('code', encoding='utf-8')
        (self.bundle / 'dag_output/ingest').mkdir(parents=True)
        (self.bundle / 'dag_output/ingest/ingest.json').write_text('{}', encoding='utf-8')
        (self.bundle / 'dag_output/preprocess').mkdir()
        (self.bundle / 'dag_output/preprocess/preprocessor.joblib').write_bytes(b'current')
        (self.bundle / 'bundle_manifest.json').write_text('{}', encoding='utf-8')
        (self.bundle / 'main_bundle_origin.json').write_text('{}', encoding='utf-8')
        target = self.root / 'fresh'
        make_replay_bundle(self.bundle, 'preprocess', target)
        self.assertTrue((target / 'dag_output/ingest/ingest.json').is_file())
        self.assertFalse((target / 'dag_output/preprocess').exists())
        self.assertFalse((target / 'main_generation').exists())
        with self.assertRaises(FileExistsError):
            make_replay_bundle(self.bundle, 'preprocess', target)

    def fake_bundle(self):
        for folder in ('input', 'submission', 'dag_output', 'main_generation'):
            (self.bundle / folder).mkdir(parents=True)
        (self.bundle / 'input/train.csv').write_text('row_id,x\n1,2\n', encoding='utf-8')
        (self.bundle / 'bundle_manifest.json').write_text('{}', encoding='utf-8')
        (self.bundle / 'main_bundle_origin.json').write_text('{}', encoding='utf-8')

    def fake_checker(self, case_id, bundle, stage, label):
        out = Path(bundle) / 'dag_output' / stage
        out.mkdir()
        artifact = out / ARTIFACT[stage]
        artifact.write_text('{}', encoding='utf-8')
        source = Path(bundle) / 'submission' / SCRIPT[stage]
        (out / 'stage_report.json').write_text(json.dumps({
            'case_id': case_id, 'stage': stage, 'status': 'stage_verified',
            'verified': True, 'source_sha256': sha256(source),
            'artifact_sha256': sha256(artifact)}), encoding='utf-8')
        return {'verified': True, 'environment_unresolved': False,
                'stage_report': {'verified': True}, 'label': label}

    def test_fake_provider_and_verifier_seam_records_same_arm_origin(self):
        self.fake_bundle()
        sys.path.insert(0, str(ECO.parent))
        import run_ml_calibration
        import run_ml_dag_llm_feasibility
        model = {'slot': 'agent_1', 'model_id': 'fake', 'exact_version': 'version'}
        lock = {'generation': {'temperature': 0, 'max_output_tokens': 100,
                               'timeout_seconds': 10}}
        (self.root / 'fake_lock.json').write_text(json.dumps(lock), encoding='utf-8')
        response = {'content': '{"ingest_validate.py":"print(1)"}',
                    'finish_reason': 'stop', 'exact_model_version': 'version',
                    'input_tokens': 10, 'output_tokens': 5, 'response_cost': 0.1}
        with patch('main_live_ml_stage_v1.require_paid_lock',
                   return_value=(lock, {'base_url': 'unused'}, model)), \
                patch('main_live_ml_stage_v1.build_main_prompt', return_value='public prompt'), \
                patch.object(run_ml_dag_llm_feasibility, 'preflight_container'), \
                patch.object(run_ml_dag_llm_feasibility, 'invoke', return_value=response) as invoked, \
                patch.object(run_ml_calibration, 'check_stage', side_effect=self.fake_checker):
            result = execute_stage_once(self.bundle, 'ingest', run_id='R1',
                                        arm_id='CF_FIT', case_id='MAIN_ADULT_01',
                                        model_slot='agent_1', confirm_paid=True,
                                        lock_path=self.root / 'fake_lock.json')
        self.assertEqual(result['status'], 'VERIFIED')
        self.assertEqual(invoked.call_count, 1)
        self.assertTrue((self.bundle / 'dag_output/ingest/main_origin.json').is_file())
        self.assertTrue((self.bundle / 'main_generation/ingest/replay_gate.json').is_file())
        with self.assertRaises(PermissionError):
            execute_stage_once(self.bundle, 'ingest', run_id='R1', arm_id='CF_FIT',
                               case_id='MAIN_ADULT_01', model_slot='agent_1',
                               confirm_paid=False, lock_path=self.root / 'fake_lock.json')

    def test_provider_unknown_is_preserved_not_retried(self):
        self.fake_bundle()
        sys.path.insert(0, str(ECO.parent))
        import run_ml_dag_llm_feasibility
        lock = {'generation': {'temperature': 0, 'max_output_tokens': 100,
                               'timeout_seconds': 10}}
        lock_path = self.root / 'fake_lock.json'
        lock_path.write_text(json.dumps(lock), encoding='utf-8')
        model = {'slot': 'agent_1', 'model_id': 'fake', 'exact_version': 'version'}
        with patch('main_live_ml_stage_v1.require_paid_lock',
                   return_value=(lock, {'base_url': 'unused'}, model)), \
                patch('main_live_ml_stage_v1.build_main_prompt', return_value='public prompt'), \
                patch.object(run_ml_dag_llm_feasibility, 'preflight_container'), \
                patch.object(run_ml_dag_llm_feasibility, 'invoke',
                             side_effect=TimeoutError('unknown')) as invoked:
            arguments = dict(run_id='R1', arm_id='CF_FIT',
                             case_id='MAIN_ADULT_01', model_slot='agent_1',
                             confirm_paid=True, lock_path=lock_path)
            result = execute_stage_once(self.bundle, 'ingest', **arguments)
            self.assertEqual(result['status'], 'PROVIDER_UNRESOLVED')
            with self.assertRaises(FileExistsError):
                execute_stage_once(self.bundle, 'ingest', **arguments)
        self.assertEqual(invoked.call_count, 1)
        self.assertFalse((self.bundle / 'submission/ingest_validate.py').exists())
