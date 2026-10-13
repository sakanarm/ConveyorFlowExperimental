"""Supplemental read-only diagnosis of a pre-XML patch-application failure.

This post-block-1 rule never changes the frozen allocator, request count,
raw outcome, primary metrics, or independent audit. It reports whether an
UNRESOLVED verifier status was caused by the candidate patch failing the
strict trusted context matcher before tests could start.
"""
import argparse
import json
from pathlib import Path

from audit_ecological_main_v1 import AUDIT_ROOT, host_path
from freeze_ecological_main_v1 import LOCK, read
from main_artifact_chain_v1 import sha256
from main_live_repository_repair_v1 import MAIN_ROOT


OUT = LOCK.parent / 'main_repository_guard_diagnostics_v1'
SIGNATURE = 'ValueError: context mismatch; fuzzy matching is forbidden'


def diagnose(block_id):
    lock = read(LOCK)
    blocks = [row for row in lock['blocks'] if row['block_id'] == block_id]
    audit_path = AUDIT_ROOT / (block_id + '.json')
    audit = read(audit_path)
    if (len(blocks) != 1 or audit['status'] != 'main_block_independently_audited'
            or audit['lock_sha256'] != sha256(LOCK)):
        raise ValueError('Independent block audit required before diagnosis')
    block = blocks[0]
    case_id = next(case for case in block['case_ids']
                   if case in lock['repository_case_ids'])
    rows = []
    for arm in block['arm_order']:
        base = host_path(MAIN_ROOT / block_id / arm / case_id)
        summary_path = base / 'summary.json'
        summary = read(summary_path)
        audited = [row for row in audit['arms'][arm]['attempts']
                   if row['task_id'] == case_id + ':repair']
        if (len(audited) != 1 or audited[0]['summary_sha256'] != sha256(summary_path)
                or audited[0]['stage_status'] != summary['status']):
            raise ValueError('Repair attempt not bound to independent audit')
        status = summary['status']
        row = {'arm': arm, 'case_id': case_id, 'raw_status_unchanged': status,
               'raw_summary_sha256': sha256(summary_path),
               'diagnostic_status': 'NO_SUPPLEMENTAL_RECLASSIFICATION'}
        if status == 'VERIFIER_ENVIRONMENT_UNRESOLVED':
            verifier_path = base / 'verifier.json'
            verifier = read(verifier_path)
            if (summary['verifier_sha256'] != sha256(verifier_path)
                    or not verifier['checks']):
                raise ValueError('Missing verifier linkage')
            first = verifier['checks'][0]
            execution_path = base / first['label'] / 'execution.json'
            execution = read(execution_path)
            if first['execution_sha256'] != sha256(execution_path):
                raise ValueError('Trusted guard execution changed')
            signature_seen = (first['label'] == 'visible'
                              and first['xml_sha256'] is None
                              and first['return_code'] == 1
                              and not first['timeout']
                              and SIGNATURE in execution.get('stderr', ''))
            row.update(verifier_sha256=sha256(verifier_path),
                       guard_execution_sha256=sha256(execution_path),
                       diagnostic_status=('MODEL_PATCH_CONTEXT_MISMATCH'
                                          if signature_seen else 'UNRESOLVED_CAUSE_NOT_ADJUDICATED'),
                       strict_signature_seen=signature_seen)
        rows.append(row)
    return {'status': 'supplemental_guard_diagnosis_not_raw_rewrite',
            'post_block_1_rule_frozen_before_subsequent_blocks': True,
            'block_id': block_id, 'lock_sha256': sha256(LOCK),
            'independent_audit_sha256': sha256(audit_path),
            'primary_metrics_unchanged': True,
            'provider_call_count_unchanged': True,
            'raw_ledger_and_summary_unchanged': True,
            'arms': rows}


def write(block_id):
    record = diagnose(block_id)
    OUT.mkdir(exist_ok=True)
    path = OUT / (block_id + '.json')
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(record, sort_keys=True, indent=2) + '\n')
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--block', required=True)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    result = write(args.block) if args.write else diagnose(args.block)
    print(json.dumps({'status': result['status'], 'block_id': args.block,
                      'diagnoses': {row['arm']: row['diagnostic_status']
                                    for row in result['arms']}}, sort_keys=True))
