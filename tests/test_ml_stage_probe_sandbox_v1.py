import importlib.util
import sys
import unittest
from unittest.mock import patch
from pathlib import Path

HERE = Path(__file__).resolve().parents[1] / "major_revision_v2_3"
sys.path.insert(0, str(HERE))
import ml_stage_probe_sandbox_v1 as sandbox


class ProbeSandboxTests(unittest.TestCase):
    def test_named_podman_and_thread_limits(self):
        c = sandbox.named_command(["podman", "run", "--rm", "image", "python", "x.py"], "cf-ml-stage-v1-test")
        self.assertEqual(c[:4], ["podman", "run", "--name", "cf-ml-stage-v1-test"])
        for v in ("OMP_NUM_THREADS=2", "OPENBLAS_NUM_THREADS=2", "MKL_NUM_THREADS=2", "NUMEXPR_NUM_THREADS=2"):
            self.assertIn(v, c)

    def test_rejects_other_runtime_or_broad_name(self):
        with self.assertRaises(ValueError):
            sandbox.named_command(["docker", "run"], "cf-ml-stage-v1-test")
        with self.assertRaises(ValueError):
            sandbox.named_command(["podman", "run"], "all")

    def test_verifier_is_not_imported_on_host(self):
        self.assertNotIn("ml_stage_probe_verifier_v1", sys.modules)

    def test_timeout_stops_only_exact_named_container_and_confirms_absence(self):
        import subprocess
        from types import SimpleNamespace
        records = []
        def fake_run(command, **kwargs):
            records.append(command)
            if command[:2] == ["podman", "run"]:
                raise subprocess.TimeoutExpired(command, 360)
            return SimpleNamespace(returncode=1 if command[:3] == ["podman", "container", "exists"] else 0,
                                   stderr="", stdout="")
        with patch.object(sandbox.subprocess, "run", side_effect=fake_run):
            result = sandbox.execute(["podman", "run", "--rm", "image", "python", "x.py"])
        self.assertTrue(result["container_absence_confirmed"])
        name = result["container_name"]
        self.assertEqual(records[1], ["podman", "stop", "--time", "1", name])
        self.assertEqual(records[2], ["podman", "rm", "--force", name])
        self.assertEqual(records[3], ["podman", "container", "exists", name])


if __name__ == "__main__":
    unittest.main()
