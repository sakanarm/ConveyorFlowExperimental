"""One frozen environment recovery with ordered-prefix provenance; no LLM."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import run_bugsinpy_preflight as engine
from select_bugsinpy_pilot import MANIFEST, select

HERE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze(path, value):
    if path.exists():
        assert json.loads(path.read_text(encoding='utf-8')) == value, 'Frozen input changed'
    else:
        path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, required=True)
    args = parser.parse_args()
    config = args.config.resolve()
    assert config.is_relative_to(HERE)
    policy = json.loads(config.read_text(encoding='utf-8'))
    ledger = HERE / policy['source_ledger']
    previous = [json.loads(line) for line in ledger.read_text(encoding='utf-8').splitlines() if line.strip()]
    select(MANIFEST, ledger)
    assert len(previous) == policy['expected_prefix_length']
    index = policy['candidate_index']
    assert previous[index]['status'] == 'environment_excluded'
    candidate = json.loads(MANIFEST.read_text(encoding='utf-8'))['candidates'][index]
    assert previous[index]['selection_hash'] == candidate['selection_hash']
    label = policy['artifact_prefix']
    assert label.isidentifier()
    root = HERE / 'results' / (label + '_protocol')
    root.mkdir(exist_ok=True)
    settings = json.loads((HERE / policy['source_config']).read_text(encoding='utf-8'))
    settings['max_candidates'] = 1
    settings['compile_flags'] = policy['overrides']['compile_flags']
    settings['profiles'][candidate['project']]['build'] = policy['overrides']['project_build']
    settings['environment_deviation'] += ' Recovery: ' + policy['reason']
    freeze(root / 'lock.json', {'config_sha256': digest(config), 'source_ledger_sha256': digest(ledger),
                              'source_manifest_sha256': digest(MANIFEST), 'runner_sha256': digest(Path(__file__)),
                              'engine_sha256': digest(Path(engine.__file__)), 'llm_calls': 0})
    effective = root / 'config.json'
    subset = root / 'manifest.json'
    freeze(effective, settings)
    freeze(subset, {'status': 'metadata_only_not_preflighted', 'candidates': [candidate]})
    recovery = root / 'new_case_ledger.jsonl'
    if not recovery.exists():
        print(json.dumps({'status': 'frozen_environment_recovery_started', 'index': index,
                          'project': candidate['project'], 'bug_id': candidate['bug_id'], 'llm_calls': 0}), flush=True)
        original = engine.MANIFEST
        engine.MANIFEST = subset
        try:
            engine.run_next(effective, recovery, label)
        finally:
            engine.MANIFEST = original
    records = [json.loads(line) for line in recovery.read_text(encoding='utf-8').splitlines() if line.strip()]
    assert len(records) == 1
    record = copy.deepcopy(records[0])
    assert record['config_sha256'] == digest(effective)
    assert record['selection_hash'] == candidate['selection_hash']
    record['original_manifest_index'] = index
    record['prior_record_sha256'] = hashlib.sha256(json.dumps(previous[index], sort_keys=True).encode()).hexdigest()
    record['source_prefix_sha256'] = digest(ledger)
    previous[index] = record
    combined = root / 'combined_prefix_ledger.jsonl'
    content = ''.join(json.dumps(item, sort_keys=True) + '\n' for item in previous)
    if combined.exists():
        assert combined.read_text(encoding='utf-8') == content
    else:
        combined.write_text(content, encoding='utf-8')
    state = select(MANIFEST, combined)
    freeze(root / 'selection.json', state)
    print(json.dumps(state, indent=2), flush=True)


if __name__ == '__main__':
    main()
