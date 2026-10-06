from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
import sqlite3
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'major_revision_v2_3/ecological_v1'))
from claim_store import ClaimStore


class EcologicalClaimStoreTests(unittest.TestCase):
    def test_concurrent_same_task_exactly_one_winner(self):
        with tempfile.TemporaryDirectory() as temp:
            store = ClaimStore.create(Path(temp)/'claims.db', ['A','B','C','D'], [{'task_id':'T'}])
            with ThreadPoolExecutor(max_workers=4) as pool:
                claims = list(pool.map(lambda a: store.claim('T', a), ['A','B','C','D']))
            self.assertEqual(sum(c['won'] for c in claims), 1)
            self.assertEqual(sum(e['event']=='claim_win' for e in store.snapshot()['events']), 1)

    def test_concurrent_same_agent_cannot_hold_two_tasks(self):
        with tempfile.TemporaryDirectory() as temp:
            store = ClaimStore.create(Path(temp)/'claims.db', ['A'], [{'task_id':'T1'}, {'task_id':'T2'}])
            with ThreadPoolExecutor(max_workers=2) as pool:
                claims = list(pool.map(lambda t: store.claim(t, 'A'), ['T1','T2']))
            self.assertEqual(sum(c['won'] for c in claims), 1)

    def test_dependency_artifact_and_arrival_guards(self):
        with tempfile.TemporaryDirectory() as temp:
            store = ClaimStore.create(Path(temp)/'claims.db', ['A'],
                 [{'task_id':'parent'}, {'task_id':'child','dependencies':['parent']},
                  {'task_id':'future','release_ns':time.monotonic_ns()+10**12}])
            self.assertEqual(store.claim('child','A')['reason'], 'dependencies_unverified')
            self.assertEqual(store.claim('future','A')['reason'], 'not_arrived')
            claim = store.claim('parent','A')
            with self.assertRaises(ValueError):
                store.complete(claim,'VERIFIED',artifact='wrong')
            store.complete(claim,'VERIFIED',artifact='a'*64)
            self.assertTrue(store.claim('child','A')['won'])

    def test_retry_bound_unresolved_and_stale_completions(self):
        with tempfile.TemporaryDirectory() as temp:
            store = ClaimStore.create(Path(temp)/'claims.db', ['A'], [{'task_id':'T'}, {'task_id':'U'}])
            first = store.claim('T','A')
            store.complete(first,'MODEL_FAILED')
            second = store.claim('T','A')
            with self.assertRaises(ValueError):
                store.complete(first,'VERIFIED',artifact='a'*64)
            store.complete(second,'MODEL_FAILED')
            self.assertEqual(store.claim('T','A')['reason'], 'task_unavailable')
            unknown = store.claim('U','A')
            store.complete(unknown,'PROVIDER_UNRESOLVED')
            self.assertIn(('U','UNSETTLED',None,1), store.snapshot()['tasks'])

    def test_append_only_events_and_preserved_store(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'claims.db'
            store = ClaimStore.create(path, ['A'], [{'task_id':'T'}])
            store.claim('T','A')
            with closing(sqlite3.connect(path)) as db, self.assertRaises(sqlite3.IntegrityError):
                db.execute('DELETE FROM events')
            with self.assertRaises(ValueError):
                ClaimStore.create(path, ['A'], [{'task_id':'T'}])

    def test_cycle_rejected_before_database_is_created(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'claims.db'
            with self.assertRaisesRegex(ValueError, 'Cyclic'):
                ClaimStore.create(path, ['A'], [
                    {'task_id':'T1', 'dependencies':['T2']},
                    {'task_id':'T2', 'dependencies':['T1']}])
            self.assertFalse(path.exists())


if __name__ == '__main__':
    unittest.main()
