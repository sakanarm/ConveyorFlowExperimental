"""Event dispatch correctness with trusted fixtures; no provider calls."""
import hashlib
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ECO = Path(__file__).resolve().parents[1] / 'major_revision_v2_3/ecological_v1'
sys.path.insert(0, str(ECO))
from belt_contract import Agent, Task
import integration_backend_v2 as backend


def verified(task, _claim, _predecessors):
    time.sleep(0.03)
    return {'outcome': 'VERIFIED', 'artifact': hashlib.sha256(task.task_id.encode()).hexdigest()}


class EventDrivenFixtureTests(unittest.TestCase):
    def test_fast_claim_dispatches_before_slow_claimant_returns(self):
        agents = [Agent('A1', 'fixture1', {'*': 1}), Agent('A2', 'fixture2', {'*': 3})]
        tasks = [Task('T1', 'J1', 'fixture', 'ingest', 1),
                 Task('T2', 'J2', 'fixture', 'ingest', 1)]
        original = backend.child

        def delayed(role, message):
            if role == 'agent' and message['agents'][0]['agent_id'] == 'A2':
                time.sleep(0.45)
            return original(role, message)

        with tempfile.TemporaryDirectory() as tmp, patch.object(backend, 'child', delayed):
            root = Path(tmp) / 'run'
            result = backend.run_event_fixture_backend('CF_FIT', agents, tasks, root, verified)
            self.assertEqual(result['jobs'], {'J1': 'VERIFIED', 'J2': 'VERIFIED'})
            events = backend.validate_ledger(root / 'events.jsonl')
            first_start = next(e['sequence'] for e in events
                               if e['event'] == 'execution_started' and e['agent_id'] == 'A1')
            slow_return = next(e['sequence'] for e in events
                               if e['event'] == 'agent_claim_component' and e['agent_id'] == 'A2')
            self.assertLess(first_start, slow_return)

    def test_dependency_and_central_locus(self):
        agents = [Agent('A1', 'fixture1', {'*': 1}), Agent('A2', 'fixture2', {'*': 3})]
        tasks = [Task('T1', 'J', 'fixture', 'ingest', 1),
                 Task('T2', 'J', 'fixture', 'train', 3, dependencies=('T1',))]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'run'
            result = backend.run_event_fixture_backend('CENTRAL_RULE_MATCHED', agents, tasks, root, verified)
            self.assertEqual(result['jobs'], {'J': 'VERIFIED'})
            events = backend.validate_ledger(root / 'events.jsonl')
            claims = [e for e in events if e['event'] == 'agent_claim_component']
            self.assertTrue(any(e['event'] == 'coordinator_choice' for e in events))
            self.assertTrue(all(e['decision_actor'] == 'coordinator' for e in claims))
            parent = next(e for e in events if e['event'] == 'verified_execution_result'
                          and e['task_id'] == 'T1')
            child = next(e for e in events if e['event'] == 'execution_started'
                         and e['task_id'] == 'T2')
            self.assertLess(parent['sequence'], child['sequence'])

    def test_unknown_propagates_and_overwrite_refused(self):
        agents = [Agent('A1', 'fixture', {'*': 2})]
        tasks = [Task('T1', 'J', 'fixture', 'ingest', 1),
                 Task('T2', 'J', 'fixture', 'train', 1, dependencies=('T1',))]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'run'
            result = backend.run_event_fixture_backend(
                'CF_FIT', agents, tasks, root,
                lambda *_: {'outcome': 'PROVIDER_UNRESOLVED'})
            self.assertEqual(result['task_states'], {'T1': 'UNSETTLED', 'T2': 'UNSETTLED'})
            with self.assertRaises(FileExistsError):
                backend.run_event_fixture_backend('CF_FIT', agents, tasks, root, verified)

    def test_static_preassigned_owners_run_concurrently(self):
        agents = [Agent('A1', 'fixture1', {'*': 2}), Agent('A2', 'fixture2', {'*': 2})]
        tasks = [Task('T1', 'J1', 'fixture', 'ingest', 1),
                 Task('T2', 'J2', 'fixture', 'ingest', 1)]

        def delayed(task, claim, parents):
            time.sleep(0.15)
            return verified(task, claim, parents)

        with tempfile.TemporaryDirectory() as tmp:
            result = backend.run_event_fixture_backend('STATIC_OWNERS', agents, tasks,
                                                       Path(tmp) / 'run', delayed)
            windows = result['execution_windows_ns']
            self.assertEqual({(a, t) for a, t, _, _ in windows},
                             {('A1', 'T1'), ('A2', 'T2')})
            self.assertLess(max(start for _, _, start, _ in windows),
                            min(finish for _, _, _, finish in windows))

    def test_failure_and_no_volunteer_bounds(self):
        agent = Agent('A1', 'fixture', {'*': 2})
        tasks = [Task('T1', 'J', 'fixture', 'ingest', 1),
                 Task('T2', 'J', 'fixture', 'train', 1, dependencies=('T1',))]
        with tempfile.TemporaryDirectory() as tmp:
            failure = backend.run_event_fixture_backend('CF_FIT', [agent], tasks,
                Path(tmp) / 'failure', lambda *_: {'outcome': 'MODEL_FAILED'})
            self.assertEqual(failure['task_states'],
                             {'T1': 'DEAD_LETTER', 'T2': 'DEAD_LETTER'})
            self.assertEqual(failure['attempts'], {'T1': 2, 'T2': 0})
            declined = Agent('A1', 'fixture', {'*': 2}, frozenset({'T1'}))
            no_volunteer = backend.run_event_fixture_backend('CF_FIT', [declined],
                [Task('T1', 'J', 'fixture', 'ingest', 1)], Path(tmp) / 'no_volunteer', verified)
            self.assertEqual(no_volunteer['task_states'], {'T1': 'DEAD_LETTER'})
            self.assertEqual(no_volunteer['attempts'], {'T1': 0})


if __name__ == '__main__':
    unittest.main()
