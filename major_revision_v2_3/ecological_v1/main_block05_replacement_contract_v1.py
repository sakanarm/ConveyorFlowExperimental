"""Fail-closed, append-only full-block replacement contract for the paused block.

This module has no provider entry point. The original lock and interrupted raw
evidence remain immutable; only MAIN_BLOCK_05_R1 may be added under a new lock.
"""
from copy import deepcopy
import json
from pathlib import Path

from main_artifact_chain_v1 import sha256
from prepare_design import HERE


ORIGINAL_LOCK = HERE / 'main_allocation_execution_lock_v1.json'
REPLACEMENT_LOCK = HERE / 'main_block05_replacement_lock_v1.json'
INCIDENT = HERE / 'MAIN_BLOCK_05_INTERRUPTION_20261007_TH.md'
PROTOCOL = HERE / 'MAIN_BLOCK_05_REPLACEMENT_PROTOCOL_V1_TH.md'
REPLACEMENT_ID = 'MAIN_BLOCK_05_R1'
ORIGINAL_ID = 'MAIN_BLOCK_05'
ORIGINAL_LOCK_SHA256 = '2206d6dde060cf467b920745ef3912d3da4269b8ceda4d3a9c45f3f82386efe2'
INCIDENT_SHA256 = 'c14ec23b81f6c18ab241539ef8b48753c4f1fe439ddab1c2492f44a6dd0c8402'
PROTOCOL_SHA256 = '1b67207a685f13ca0b1693e5a574a85db0e8d8b69ffd5d447ec53fd6eb72d717'

# Exact read-only anchors captured after the user-directed stop. Paths are
# workspace-relative to the short D: runtime, not source files for publication.
INTERRUPTED = {
    'ecological_main_v1/MAIN_BLOCK_05/started.json':
        '07c3249b0a3188d64b83ea24e6281470e5c30a5f4b3e290e8b1d961cc1323240',
    'ecological_main_v1/MAIN_BLOCK_05/CENTRAL_RULE_MATCHED/allocation/summary.json':
        '659bd78725e349fadc4121833d4dc151bf85793e16c41e3bac626329258d06b2',
    'ecological_main_v1/MAIN_BLOCK_05/CENTRAL_RULE_MATCHED/allocation/events.jsonl':
        '3bb194d6e4430d91f902200a98c9935eecdd043e898496fb0ce96da8ad67d57a',
    'ecological_main_v1/MAIN_BLOCK_05/CF_FIT/allocation/events.jsonl':
        '20f1834685e06e3e479fe9ebae224aeb06d6ac3a1b6d4d058b98b8db26b3d6a5',
    'ecological_repository_main_v1/MAIN_BLOCK_05/CF_FIT/pandas_82/request_started.json':
        '077d3a34514eec98dff5f8faaa7a0023fe94d0d88790cd2ec33919d92cf71e79',
}
SOURCE_NAMES = (
    'main_block05_replacement_contract_v1.py',
    'freeze_main_block05_replacement_v1.py',
    'run_main_block05_replacement_v1.py',
    'audit_main_block05_replacement_v1.py',
    'analyze_main_with_replacement_v1.py',
    'wsl_main_block05_replacement_bridge_v1.py',
    'check_main_block05_replacement_v1.py',
)


def read(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('Missing or symlinked replacement evidence: ' + str(path))
    return json.loads(path.read_text(encoding='utf-8'))


def verify_interruption():
    if sha256(ORIGINAL_LOCK) != ORIGINAL_LOCK_SHA256:
        raise ValueError('Original frozen lock changed')
    if sha256(INCIDENT) != INCIDENT_SHA256:
        raise ValueError('User-pause incident record changed')
    if sha256(PROTOCOL) != PROTOCOL_SHA256:
        raise ValueError('Replacement protocol changed')
    runtime = Path('/mnt/d/ConveyorFlowRuntime/v2_3/candidate_workspaces')
    for relative, expected in INTERRUPTED.items():
        target = runtime / relative
        if target.is_symlink() or not target.is_file() or sha256(target) != expected:
            raise ValueError('Interrupted raw evidence changed: ' + relative)
    original = runtime / 'ecological_main_v1' / ORIGINAL_ID
    pending = runtime / 'ecological_repository_main_v1' / ORIGINAL_ID / 'CF_FIT' / 'pandas_82'
    if (original / 'raw_complete.json').exists() or (original / 'instrument_unresolved.json').exists():
        raise ValueError('Interrupted block status changed; manual review needed')
    if (pending / 'response.txt').exists() or (pending / 'summary.json').exists():
        raise ValueError('Interrupted in-flight request acquired a response; manual review needed')


def expected_lock():
    verify_interruption()
    lock = deepcopy(read(ORIGINAL_LOCK))
    if (lock.get('status') != 'ecological_main_execution_frozen_v1'
            or [row['block_id'] for row in lock['blocks']]
            != [f'MAIN_BLOCK_0{i}' for i in range(1, 7)]
            or lock['run_ids'] != [f'MAIN_BLOCK_0{i}' for i in range(1, 7)]):
        raise ValueError('Unexpected original main design')
    old = next(row for row in lock['blocks'] if row['block_id'] == ORIGINAL_ID)
    replacement = deepcopy(old)
    replacement['block_id'] = REPLACEMENT_ID
    replacement['run_id'] = REPLACEMENT_ID
    lock['blocks'].append(replacement)
    lock['run_ids'].append(REPLACEMENT_ID)
    lock['replacement_amendment'] = {
        'status': 'user_pause_full_block_technical_replacement_v1',
        'replaces': ORIGINAL_ID,
        'new_run_id': REPLACEMENT_ID,
        'original_lock_sha256': ORIGINAL_LOCK_SHA256,
        'incident_sha256': INCIDENT_SHA256,
        'protocol_sha256': PROTOCOL_SHA256,
        'interrupted_raw_sha256': INTERRUPTED,
        'old_partial_block_excluded_from_paired_analysis': True,
        'all_three_arms_rerun_without_reusing_old_outputs': True,
        'single_started_repository_call_has_unknown_billable_outcome': True,
    }
    lock['replacement_source_sha256'] = {
        name: sha256(HERE / name) for name in SOURCE_NAMES
    }
    return lock


def verify_replacement_lock():
    lock = read(REPLACEMENT_LOCK)
    if lock != expected_lock():
        raise ValueError('Replacement lock or source drift; fail closed')
    return lock


def write_replacement_lock():
    lock = expected_lock()
    with REPLACEMENT_LOCK.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(lock, sort_keys=True, indent=2) + '\n')
    return {'status': 'replacement_frozen_not_executed',
            'path': str(REPLACEMENT_LOCK), 'sha256': sha256(REPLACEMENT_LOCK),
            'run_id': REPLACEMENT_ID}
