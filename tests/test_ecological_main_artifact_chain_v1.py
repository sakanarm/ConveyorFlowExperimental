"""Main stage provenance cannot silently accept a calibration predecessor."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ECO = Path(__file__).resolve().parents[1] / 'major_revision_v2_3/ecological_v1'
sys.path.insert(0, str(ECO))
from main_artifact_chain_v1 import (ARTIFACT, SCRIPT, record_verified_stage,
                                    sha256, verify_parents)


class MainArtifactChainTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.bundle = Path(self.temp.name) / 'bundle'
        self.scope = {'run_id': 'R1', 'arm_id': 'CF_FIT', 'case_id': 'MAIN_ADULT_01'}

    def stage(self, name):
        out = self.bundle / 'dag_output' / name
        gen = self.bundle / 'main_generation' / name
        source = self.bundle / 'submission' / SCRIPT[name]
        out.mkdir(parents=True)
        gen.mkdir(parents=True)
        source.parent.mkdir(parents=True, exist_ok=True)
        artifact = out / ARTIFACT[name]
        artifact.write_bytes(name.encode())
        source.write_text('print(1)', encoding='utf-8')
        response = gen / 'response.txt'
        response.write_text('model output', encoding='utf-8')
        (gen / 'generation.json').write_text(json.dumps({**self.scope, 'stage': name,
            'request_sha256': 'a' * 64, 'response_sha256': sha256(response),
            'source_sha256': sha256(source)}), encoding='utf-8')
        (out / 'stage_report.json').write_text(json.dumps({
            'case_id': self.scope['case_id'], 'stage': name,
            'status': 'stage_verified', 'verified': True,
            'source_sha256': sha256(source), 'artifact_sha256': sha256(artifact)}), encoding='utf-8')
        return out

    def test_full_four_stage_chain_and_tamper(self):
        for name in ('ingest', 'preprocess', 'train', 'package'):
            self.stage(name)
            record = record_verified_stage(self.bundle, name, **self.scope)
            self.assertEqual(record['origin'], 'main_agent_generated_verified')
        self.assertEqual(len(verify_parents(self.bundle, 'package', **self.scope)), 3)
        (self.bundle / 'dag_output/train/model.joblib').write_bytes(b'tampered')
        with self.assertRaisesRegex(ValueError, 'not verified'):
            verify_parents(self.bundle, 'package', **self.scope)

    def test_trusted_reference_report_without_main_origin_is_rejected(self):
        self.stage('ingest')
        with self.assertRaisesRegex(ValueError, 'provenance'):
            verify_parents(self.bundle, 'preprocess', **self.scope)

    def test_other_arm_origin_is_rejected(self):
        self.stage('ingest')
        record_verified_stage(self.bundle, 'ingest', **self.scope)
        with self.assertRaisesRegex(ValueError, 'not verified'):
            verify_parents(self.bundle, 'preprocess', run_id='R1',
                           arm_id='CENTRAL_RULE_MATCHED', case_id='MAIN_ADULT_01')

    def test_predecessor_source_tamper_is_rejected(self):
        self.stage('ingest')
        record_verified_stage(self.bundle, 'ingest', **self.scope)
        (self.bundle / 'submission/ingest_validate.py').write_text('changed', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'not verified'):
            verify_parents(self.bundle, 'preprocess', **self.scope)

    def test_response_hash_mismatch_and_no_overwrite(self):
        self.stage('ingest')
        (self.bundle / 'main_generation/ingest/response.txt').write_text('changed', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'mismatch'):
            record_verified_stage(self.bundle, 'ingest', **self.scope)
        (self.bundle / 'main_generation/ingest/response.txt').write_text('model output', encoding='utf-8')
        record_verified_stage(self.bundle, 'ingest', **self.scope)
        with self.assertRaises(FileExistsError):
            record_verified_stage(self.bundle, 'ingest', **self.scope)
