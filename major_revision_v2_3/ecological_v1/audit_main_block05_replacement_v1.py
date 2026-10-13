"""Independently audit the full-block replacement using the original auditor.

No provider calls are made. Interrupted MAIN_BLOCK_05 remains excluded.
"""
import argparse
import json

import audit_ecological_main_v1 as original_audit
from main_artifact_chain_v1 import sha256
from main_block05_replacement_contract_v1 import (
    INCIDENT, ORIGINAL_LOCK, PROTOCOL, REPLACEMENT_ID, REPLACEMENT_LOCK,
    verify_replacement_lock,
)


def audit(write=False):
    lock = verify_replacement_lock()
    if lock['replacement_amendment']['incident_sha256'] != sha256(INCIDENT):
        raise ValueError('Replacement incident provenance drift')
    # Run the exact original independent audit rules with an explicit amended
    # lock binding; only the lock path and replacement run identity differ.
    original_audit.LOCK = REPLACEMENT_LOCK
    record = original_audit.audit_block(REPLACEMENT_ID)
    if (record['lock_sha256'] != sha256(REPLACEMENT_LOCK)
            or record['block_id'] != REPLACEMENT_ID
            or set(record['arms']) != set(lock['arm_ids'])
            or record['research_results'] is not True):
        raise ValueError('Replacement audit scope mismatch')
    record['technical_replacement_of'] = 'MAIN_BLOCK_05'
    record['interrupted_block_excluded'] = True
    record['original_lock_sha256'] = sha256(ORIGINAL_LOCK)
    record['incident_sha256'] = sha256(INCIDENT)
    record['protocol_sha256'] = sha256(PROTOCOL)
    if write:
        target = original_audit.AUDIT_ROOT / (REPLACEMENT_ID + '.json')
        with target.open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(json.dumps(record, sort_keys=True, indent=2) + '\n')
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    result = audit(args.write)
    print(json.dumps({'status': result['status'],
                      'block_id': result['block_id'],
                      'provider_attempts': result['provider_attempts'],
                      'technical_replacement_of': result['technical_replacement_of']}))
