"""Vector analysis of five original audited blocks plus disclosed replacement.

The interrupted original block is never treated as a paired result. The
original metric formulas and contrast/bootstrap functions are reused exactly.
"""
import argparse
import json
from pathlib import Path

import analyze_ecological_main_v1 as original_analysis
from integration_backend_v1 import validate_ledger
from main_artifact_chain_v1 import sha256
from main_block05_replacement_contract_v1 import (
    INCIDENT, ORIGINAL_LOCK, ORIGINAL_ID, PROTOCOL, REPLACEMENT_ID, REPLACEMENT_LOCK,
    verify_replacement_lock,
)
from prepare_design import HERE


AUDITS = HERE / 'main_block_audits_v1'
RAW_ROOT = Path('/mnt/d/ConveyorFlowRuntime/v2_3/candidate_workspaces/ecological_main_v1')
OUTPUT = HERE / 'main_analysis_with_replacement_v1.json'


def analyze(output=OUTPUT):
    amended = verify_replacement_lock()
    original = original_analysis.read(ORIGINAL_LOCK)
    if len(original['blocks']) != 6 or len(amended['blocks']) != 7:
        raise ValueError('Six original blocks and one replacement required')
    if (AUDITS / (ORIGINAL_ID + '.json')).exists():
        raise ValueError('Interrupted block must not have an audit capsule')
    old_sha, new_sha = sha256(ORIGINAL_LOCK), sha256(REPLACEMENT_LOCK)
    blocks = []
    original_complete = []
    for old_spec in original['blocks']:
        old_id = old_spec['block_id']
        block_id = REPLACEMENT_ID if old_id == ORIGINAL_ID else old_id
        lock_sha = new_sha if old_id == ORIGINAL_ID else old_sha
        capsule = original_analysis.read(AUDITS / (block_id + '.json'))
        if (capsule.get('status') != 'main_block_independently_audited'
                or capsule.get('block_id') != block_id
                or capsule.get('lock_sha256') != lock_sha
                or capsule.get('research_results') is not True):
            raise ValueError('Missing/mismatched independent audit: ' + block_id)
        if old_id == ORIGINAL_ID and (capsule.get('technical_replacement_of') != ORIGINAL_ID
                or capsule.get('incident_sha256') != sha256(INCIDENT)
                or capsule.get('protocol_sha256') != sha256(PROTOCOL)
                or capsule.get('interrupted_block_excluded') is not True):
            raise ValueError('Replacement disclosure missing from audit')
        arm_metrics = {}
        for policy in old_spec['arm_order']:
            base = RAW_ROOT / block_id / policy / 'allocation'
            summary_path, ledger_path = base / 'summary.json', base / 'events.jsonl'
            sealed = capsule['arms'][policy]
            if (sealed['summary_sha256'] != sha256(summary_path)
                    or sealed['ledger_sha256'] != sha256(ledger_path)):
                raise ValueError('Audited arm bytes changed: ' + block_id + '/' + policy)
            arm_metrics[policy] = original_analysis.derive(
                validate_ledger(ledger_path), original_analysis.read(summary_path),
                expected_policy=policy, lock_sha256=lock_sha,
                horizon_ticks=original['limits']['horizon'])
        row = {'block_id': block_id, 'original_block_id': old_id,
               'technical_replacement': old_id == ORIGINAL_ID,
               'arms': arm_metrics, 'cases': old_spec['case_ids'],
               'arm_order': old_spec['arm_order']}
        blocks.append(row)
        if old_id != ORIGINAL_ID:
            original_complete.append(row)
    result = {
        'status': 'audited_main_vector_analysis_with_disclosed_replacement',
        'research_results': True,
        'original_lock_sha256': old_sha,
        'replacement_lock_sha256': new_sha,
        'incident_sha256': sha256(INCIDENT),
        'replacement_protocol_sha256': sha256(PROTOCOL),
        'interrupted_original_block_excluded': True,
        'primary_metrics': list(original_analysis.PRIMARY),
        'secondary_metrics': list(original_analysis.SECONDARY),
        'no_scalar_superiority_score': True,
        'no_equivalence_or_fault_tolerance_proof': True,
        'fixed_horizon_rule': 'Only jobs completed before each arm fixed horizon count as primary successes.',
        'blocks': blocks,
        'paired_contrasts_six_including_replacement':
            original_analysis.paired_differences(blocks),
        'sensitivity_paired_contrasts_five_original_complete':
            original_analysis.paired_differences(original_complete),
        'caveats': [
            'The user-paused original MAIN_BLOCK_05 has an in-flight request with unknown billing outcome and is not a research result.',
            'MAIN_BLOCK_05_R1 repeats all three arms after an interruption; time/provider-state differences are possible.',
            'Two ML corpora and three repositories are reused; block bootstrap is descriptive, not a population confidence interval.',
            'Provider response_cost units are used as reported; currency is unverified.',
        ],
    }
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise FileExistsError('Analysis output already exists; never overwrite')
    with output.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(result, sort_keys=True, indent=2) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    result = analyze(args.output)
    print(json.dumps({'status': result['status'], 'blocks': len(result['blocks']),
                      'technical_replacement': REPLACEMENT_ID}))
