"""Offline repository-adapter fixture; fake provider, real isolated verifier.

Uses the already-audited no-op patch as test data, not a repair solution.
Neither outcome is a main job result or an LLM/model observation.
"""
import argparse
import json
from pathlib import Path
import sys

import main_live_repository_repair_v1 as adapter
from main_artifact_chain_v1 import sha256
from prepare_repository_main_contexts_recovery_v2 import OUT as CONTEXT_ROOT


CASE_ID = 'luigi_3'


def check(out):
    out = Path(out).resolve()
    if sys.platform != 'linux' or out.exists():
        raise ValueError('NEW Linux fixture output required')
    out.mkdir(parents=True)
    case = adapter.read(CONTEXT_ROOT / 'lock.json')['cases'][0]
    if case['case_id'] != CASE_ID:
        raise ValueError('Frozen context order changed')
    baseline = adapter.read(adapter.CANDIDATES / CASE_ID / 'summary.json')
    lock = {'generation': {'temperature': 0, 'max_output_tokens': 1024,
                           'timeout_seconds': 30},
            'repository_test_timeout_seconds': 180}
    model = {'slot': 'fixture', 'model_id': 'trusted_fixture_no_provider',
             'exact_version': 'fixture-version'}
    config = {'base_url': 'no-provider-fixture'}
    old_guard = adapter.require_lock
    major = adapter.MAJOR
    if str(major) not in sys.path:
        sys.path.insert(0, str(major))
    import run_ml_dag_llm_feasibility as provider_module
    old_invoke = provider_module.invoke

    def fake_guard(bundle, **kwargs):
        if kwargs['case_id'] != CASE_ID or kwargs['confirm_paid'] is not True:
            raise ValueError('Fixture scope changed')
        return lock, config, model, case, baseline

    def fake_invoke_factory(content):
        def fake_invoke(**kwargs):
            if kwargs['model']['model_id'] != model['model_id']:
                raise ValueError('Fixture provider mapping changed')
            return {'content': content, 'finish_reason': 'stop',
                    'exact_model_version': model['exact_version'],
                    'input_tokens': 0, 'output_tokens': 0,
                    'response_cost': 0, 'provider_request_id': 'NO_PROVIDER_FIXTURE'}
        return fake_invoke

    try:
        adapter.require_lock = fake_guard
        provider_module.invoke = fake_invoke_factory('{"not_patch": true}')
        invalid = adapter.run_once(out / 'FAKE_RUN' / 'BAD_FORMAT' / CASE_ID,
                                   run_id='FAKE_RUN', arm_id='BAD_FORMAT',
                                   case_id=CASE_ID, model_slot='fixture',
                                   confirm_paid=True, lock_path=Path(__file__))
        if invalid['status'] != 'PATCH_FORMAT_FAILED':
            raise AssertionError('Invalid JSON patch was not rejected')
        no_op = (CONTEXT_ROOT / CASE_ID / 'identity.diff').read_text(encoding='utf-8')
        provider_module.invoke = fake_invoke_factory(json.dumps({'patch': no_op}))
        unchanged = adapter.run_once(out / 'FAKE_RUN' / 'NO_OP' / CASE_ID,
                                     run_id='FAKE_RUN', arm_id='NO_OP',
                                     case_id=CASE_ID, model_slot='fixture',
                                     confirm_paid=True, lock_path=Path(__file__))
        if unchanged['status'] != 'VISIBLE_TEST_FAILED':
            raise AssertionError('No-op patch did not preserve the visible bug')
    finally:
        adapter.require_lock = old_guard
        provider_module.invoke = old_invoke
    result = {'status': 'offline_repository_adapter_fixture_passed',
              'research_results': False, 'no_provider_calls': True,
              'no_llm_generated_patch': True, 'not_allocation_main': True,
              'invalid_schema': invalid['status'],
              'no_op_patch': unchanged['status'],
              'real_offline_visible_verifier_invoked': True,
              'adapter_sha256': sha256(Path(adapter.__file__)),
              'fixture_sha256': sha256(Path(__file__))}
    with (out / 'summary.json').open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    check(parser.parse_args().out)
