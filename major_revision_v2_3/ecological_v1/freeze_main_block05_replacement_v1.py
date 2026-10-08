"""Freeze the explicitly disclosed block-05 replacement; never call provider."""
import argparse
import json

from main_block05_replacement_contract_v1 import (
    REPLACEMENT_LOCK, verify_replacement_lock, write_replacement_lock,
)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--freeze', action='store_true')
    args = parser.parse_args()
    if args.freeze:
        print(json.dumps(write_replacement_lock(), sort_keys=True))
    else:
        lock = verify_replacement_lock()
        print(json.dumps({'status': 'replacement_lock_verified_not_executed',
                          'run_id': lock['replacement_amendment']['new_run_id'],
                          'path': str(REPLACEMENT_LOCK)}, sort_keys=True))
