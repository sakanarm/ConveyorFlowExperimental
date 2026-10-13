"""No-provider structural check for the user-pause replacement amendment."""
from copy import deepcopy
import json

from main_block05_replacement_contract_v1 import (
    ORIGINAL_LOCK, REPLACEMENT_ID, REPLACEMENT_LOCK, expected_lock, read,
    verify_replacement_lock,
)


def check():
    old = read(ORIGINAL_LOCK)
    new = expected_lock()
    if len(new['blocks']) != len(old['blocks']) + 1:
        raise AssertionError('Not exactly one technical replacement')
    original5 = next(row for row in old['blocks'] if row['block_id'] == 'MAIN_BLOCK_05')
    replacement = next(row for row in new['blocks'] if row['block_id'] == REPLACEMENT_ID)
    exact = deepcopy(original5)
    exact['block_id'] = REPLACEMENT_ID
    exact['run_id'] = REPLACEMENT_ID
    if (replacement != exact or new['blocks'][:-1] != old['blocks']
            or new['run_ids'][:-1] != old['run_ids']
            or new['run_ids'][-1] != REPLACEMENT_ID
            or new['agents'] != old['agents'] or new['models'] != old['models']
            or new['limits'] != old['limits']
            or new['generation'] != old['generation']):
        raise AssertionError('Replacement changed experimental factors')
    if REPLACEMENT_LOCK.exists():
        verify_replacement_lock()
    return {'status': 'replacement_delta_checked_no_provider_calls',
            'replacement_id': REPLACEMENT_ID,
            'original_blocks': len(old['blocks']),
            'candidate_blocks_in_amended_lock': len(new['blocks']),
            'amended_lock_exists': REPLACEMENT_LOCK.exists()}


if __name__ == '__main__':
    print(json.dumps(check(), sort_keys=True))
