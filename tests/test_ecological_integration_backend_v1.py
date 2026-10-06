import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest

ECO = Path(__file__).resolve().parents[1] / 'major_revision_v2_3/ecological_v1'
sys.path.insert(0, str(ECO))
from belt_contract import Agent, Limits, Task
from integration_backend_v1 import run_fixture_backend, validate_ledger


def verified(task, claim, predecessors):
    time.sleep(0.04)
    return {'outcome': 'VERIFIED', 'artifact': hashlib.sha256(task.task_id.encode()).hexdigest()}


class IntegratedBackendTests(unittest.TestCase):
    def test_decision_locus_same_rule_actual_processes_and_dependencies(self):
        agents = [Agent('A1', 'fixture1', {'*': 1}), Agent('A2', 'fixture2', {'*': 3})]
        tasks = [Task('T1', 'J', 'fixture', 'ingest', 1), Task('T2', 'J', 'fixture', 'train', 3, dependencies=('T1',))]
        with tempfile.TemporaryDirectory() as tmp:
            for policy in ('CF_FIT', 'CENTRAL_RULE_MATCHED'):
                root = Path(tmp) / policy
                result = run_fixture_backend(policy, agents, tasks, root, verified)
                self.assertEqual(result['jobs'], {'J': 'VERIFIED'})
                events = validate_ledger(root / 'events.jsonl')
                start = events[0]['parent_process_id']
                workers = [e for e in events if e['event'] == 'agent_claim_component']
                self.assertTrue(all(w['process_id'] != start for w in workers))
                if policy == 'CF_FIT':
                    self.assertTrue(all(w['decision_actor'] == w['agent_id'] for w in workers))
                    self.assertFalse(any(e['event'] == 'coordinator_choice' for e in events))
                else:
                    self.assertTrue(all(w['decision_actor'] == 'coordinator' for w in workers))
                    self.assertTrue(any(e['event'] == 'coordinator_choice' for e in events))
                downstream = next(e for e in events if e['event'] == 'execution_started' and e['task_id'] == 'T2')
                upstream = next(e for e in events if e['event'] == 'verified_execution_result' and e['task_id'] == 'T1')
                self.assertEqual(downstream['predecessors'], {'T1': upstream['artifact']})
                self.assertGreater(downstream['sequence'], upstream['sequence'])

    def test_concurrent_execution_static_ownership_and_no_double_task(self):
        agents = [Agent('A1', 'fixture1', {'*': 2}), Agent('A2', 'fixture2', {'*': 2})]
        tasks = [Task('T1', 'J1', 'fixture', 'ingest', 1), Task('T2', 'J2', 'fixture', 'ingest', 1)]
        def delayed(*args):
            time.sleep(0.15)
            return verified(*args)
        with tempfile.TemporaryDirectory() as tmp:
            result = run_fixture_backend('STATIC_OWNERS', agents, tasks, Path(tmp) / 'run', delayed)
            windows = result['execution_windows_ns']
            self.assertEqual({(a, t) for a, t, _, _ in windows}, {('A1', 'T1'), ('A2', 'T2')})
            self.assertLess(max(w[2] for w in windows), min(w[3] for w in windows))

    def test_bounded_failures_propagate_not_reported_as_verified(self):
        agents = [Agent('A1', 'fixture1', {'*': 2})]
        tasks = [Task('T1', 'J', 'fixture', 'ingest', 1), Task('T2', 'J', 'fixture', 'train', 1, dependencies=('T1',))]
        with tempfile.TemporaryDirectory() as tmp:
            result = run_fixture_backend('CF_FIT', agents, tasks, Path(tmp) / 'run', lambda *_: {'outcome': 'MODEL_FAILED'})
            self.assertEqual(result['task_states'], {'T1': 'DEAD_LETTER', 'T2': 'DEAD_LETTER'})
            self.assertEqual(result['attempts'], {'T1': 2, 'T2': 0})

    def test_provider_unknown_remains_unknown_for_job(self):
        agents = [Agent('A1', 'fixture1', {'*': 2})]
        tasks = [Task('T1', 'J', 'fixture', 'ingest', 1), Task('T2', 'J', 'fixture', 'train', 1, dependencies=('T1',))]
        with tempfile.TemporaryDirectory() as tmp:
            result = run_fixture_backend('CF_FIT', agents, tasks, Path(tmp) / 'run', lambda *_: {'outcome': 'PROVIDER_UNRESOLVED'})
            self.assertEqual(result['task_states'], {'T1': 'UNSETTLED', 'T2': 'UNSETTLED'})
            self.assertEqual(result['attempts'], {'T1': 1, 'T2': 0})

    def test_no_volunteer_ends_at_frozen_bound(self):
        agents = [Agent('A1', 'fixture1', {'*': 2}, frozenset({'T1'}))]
        with tempfile.TemporaryDirectory() as tmp:
            result = run_fixture_backend('CF_FIT', agents, [Task('T1', 'J', 'fixture', 'ingest', 1)], Path(tmp) / 'run', verified)
            self.assertEqual(result['task_states'], {'T1': 'DEAD_LETTER'})
            self.assertEqual(result['attempts'], {'T1': 0})

    def test_refuses_overwrite_and_detects_ledger_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'run'
            agents, tasks = [Agent('A', 'fixture', {'*': 1})], [Task('T', 'J', 'fixture', 'ingest', 1)]
            run_fixture_backend('CF_FIT', agents, tasks, root, verified)
            with self.assertRaises(FileExistsError):
                run_fixture_backend('CF_FIT', agents, tasks, root, verified)
            path = root / 'events.jsonl'
            lines = path.read_text(encoding='utf-8').splitlines()
            altered = json.loads(lines[-1]); altered['jobs'] = {'J': 'DEAD_LETTER'}
            lines[-1] = json.dumps(altered)
            path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
            with self.assertRaises(ValueError):
                validate_ledger(path)


if __name__ == '__main__':
    unittest.main()
