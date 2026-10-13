"""Disk guard cannot pause a missing or completed batch and preserves markers."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

ECO = Path(__file__).resolve().parents[1] / 'major_revision_v2_3/ecological_v1'
sys.path.insert(0, str(ECO))
import watch_ml_disk_v3 as guard


class DiskGuardTests(unittest.TestCase):
    def test_no_controller_does_not_create_pause(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with patch.object(guard.ctl, 'STARTED', root / 'started.json'), \
                    patch.object(guard.ctl, 'FINISHED', root / 'finished.json'), \
                    patch.object(guard.ctl, 'PAUSE_REQUEST', root / 'pause.json'):
                self.assertEqual(guard.check_once(10**18)['status'], 'no_live_controller')
                self.assertFalse((root / 'pause.json').exists())

    def test_existing_pause_is_left_untouched(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            started, pause = root / 'started.json', root / 'pause.json'
            started.write_text('{}', encoding='utf-8')
            pause.write_text('{"reason":"user"}', encoding='utf-8')
            with patch.object(guard.ctl, 'STARTED', started), \
                    patch.object(guard.ctl, 'FINISHED', root / 'finished.json'), \
                    patch.object(guard.ctl, 'PAUSE_REQUEST', pause):
                self.assertEqual(guard.check_once(10**18)['status'], 'pause_already_requested')
                self.assertEqual(pause.read_text(encoding='utf-8'), '{"reason":"user"}')

    def test_low_disk_requests_bounded_pause_once(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            started, lock, pause = root / 'started.json', root / 'lock.json', root / 'pause.json'
            lock.write_text('frozen', encoding='utf-8')
            started.write_text(
                '{"continuation_lock_sha256":"' + guard.ctl.sha256(lock) + '"}',
                encoding='utf-8')
            with patch.object(guard.ctl, 'ROOT', root), \
                    patch.object(guard.ctl, 'STARTED', started), \
                    patch.object(guard.ctl, 'FINISHED', root / 'finished.json'), \
                    patch.object(guard.ctl, 'PAUSE_REQUEST', pause), \
                    patch.object(guard.ctl, 'CONTINUATION_LOCK', lock), \
                    patch.object(guard.shutil, 'disk_usage', return_value=SimpleNamespace(free=9)):
                report = guard.check_once(10)
                self.assertEqual(report['status'], 'disk_guard_pause_requested_wait_for_finished_ack')
                self.assertEqual(guard.ctl.read(pause)['reason'], 'local_disk_guard')
                self.assertEqual(guard.check_once(10)['status'], 'pause_already_requested')

    def test_lock_mismatch_cannot_request_pause(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            started, lock, pause = root / 'started.json', root / 'lock.json', root / 'pause.json'
            lock.write_text('frozen', encoding='utf-8')
            started.write_text('{"continuation_lock_sha256":"wrong"}', encoding='utf-8')
            with patch.object(guard.ctl, 'STARTED', started), \
                    patch.object(guard.ctl, 'FINISHED', root / 'finished.json'), \
                    patch.object(guard.ctl, 'PAUSE_REQUEST', pause), \
                    patch.object(guard.ctl, 'CONTINUATION_LOCK', lock):
                with self.assertRaisesRegex(ValueError, 'identity mismatch'):
                    guard.check_once(10)
                self.assertFalse(pause.exists())


if __name__ == '__main__':
    unittest.main()
