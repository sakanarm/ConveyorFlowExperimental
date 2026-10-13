"""Independent read-only evidence audit of six gold-free main repair contexts."""
import hashlib
import json
from pathlib import Path

from amend_repository_main_regression_gate_v1 import CASES
from build_repository_main_candidates_podman_recovery_v2 import OUT as BUILDS
from main_artifact_chain_v1 import sha256
from prepare_design import HERE
from prepare_repository_main_contexts_recovery_v2 import OUT, ORIGINAL_ROOT, read


HOME = HERE / 'main_repository_contexts_audit_v1'
SUMMARY = HOME / 'summary.json'


def audit():
    locked = read(OUT / 'lock.json')
    original = read(ORIGINAL_ROOT / 'lock.json')
    amendment_path = HERE / 'main_repository_regression_gate_amendment_v1/summary.json'
    amendment = read(amendment_path)
    if (locked['status'] != 'class_qualified_main_context_recovery_frozen_before_model_calls'
            or locked['original_context_lock_sha256'] != sha256(ORIGINAL_ROOT / 'lock.json')
            or original['candidate_amendment_sha256'] != sha256(amendment_path)
            or not amendment['eligible_for_context_preparation']
            or [c['case_id'] for c in amendment['cases']] != list(CASES)):
        raise ValueError('Context lock and prior six-case amendment do not match')
    rows = []
    for case_id in CASES:
        case = next(row for row in locked['cases'] if row['case_id'] == case_id)
        root = OUT / case_id
        summary_path = root / 'summary.json'
        summary = read(summary_path)
        full_path, prompt_path = root / 'full_buggy_context.json', root / 'prompt_context.json'
        full, prompt = read(full_path), read(prompt_path)
        candidate = read(BUILDS / case_id / 'summary.json')
        selected = read(BUILDS / case_id / 'regression_selection.json')['nodeids']
        if (root.is_symlink() or summary['status'] != 'context_identity_passed'
                or summary['provider_calls'] != 0
                or summary['source_mutation_import_confirmed'] is not True
                or summary['trusted_mutation_not_a_repair'] is not True
                or summary['no_op_patch_not_a_repair'] is not True
                or summary['lock_sha256'] != sha256(OUT / 'lock.json')
                or summary['candidate_summary_sha256'] != sha256(BUILDS / case_id / 'summary.json')
                or summary['full_context_sha256'] != sha256(full_path)
                or summary['prompt_context_sha256'] != sha256(prompt_path)
                or full['case_id'] != case_id or prompt['case_id'] != case_id
                or prompt['allowed_paths'] != case['allowed_files']
                or 'allowed_source_files' in prompt
                or set(full['allowed_source_files']) != set(case['allowed_files'])
                or set(prompt['buggy_source_excerpts']) != set(case['allowed_files'])
                or summary['source_excerpts_characters'] > 160000
                or full['visible_failure'] != prompt['visible_failure']
                or full['visible_test_source'] != prompt['visible_test_source']):
            raise ValueError('Gold-free context scope/identity mismatch: ' + case_id)
        for path, content in full['allowed_source_files'].items():
            digest = hashlib.sha256(content.encode('utf-8')).hexdigest()
            if digest != candidate['candidate_audit']['allowed_source_sha256'][path]:
                raise ValueError('Prompt source differs from buggy candidate: ' + case_id)
        if (summary['identity_patch_sha256'] != sha256(root / 'identity.diff')
                or summary['mutation_patch_sha256'] != sha256(root / 'identity_mutation.diff')
                or summary['mutation_execution_sha256'] != sha256(
                    root / 'identity_mutation_visible/execution.json')
                or summary['visible_xml_sha256'] != sha256(root / 'identity_visible/reports/tests.xml')
                or summary['regression_xml_sha256'] != sha256(root / 'identity_regression/reports/tests.xml')):
            raise ValueError('No-op/import-sentinel evidence drift: ' + case_id)
        rows.append({'case_id': case_id, 'status': summary['status'],
                     'context_summary_sha256': sha256(summary_path),
                     'prompt_context_sha256': sha256(prompt_path),
                     'allowed_paths': case['allowed_files'],
                     'selected_regressions': len(selected),
                     'active_regression_passes': candidate['active_passes'],
                     'common_environment_skips': candidate['reports']['candidate_buggy_regression']['counts']['skipped'],
                     'no_op_bug_reproduced': True, 'source_import_confirmed': True})
    result = {'status': 'six_gold_free_main_repository_contexts_audited',
              'research_results': False, 'no_provider_calls_by_auditor': True,
              'eligible_for_repository_main_execution_lock': True,
              'post_preflight_common_skip_amendment_disclosed': True,
              'context_lock_sha256': sha256(OUT / 'lock.json'),
              'amendment_summary_sha256': sha256(amendment_path),
              'cases': rows}
    if SUMMARY.exists():
        if read(SUMMARY) != result:
            raise ValueError('Frozen context audit summary changed')
    else:
        HOME.mkdir()
        with SUMMARY.open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(json.dumps(result, sort_keys=True, indent=2) + '\n')
    return result


if __name__ == '__main__':
    print(json.dumps(audit(), indent=2))
