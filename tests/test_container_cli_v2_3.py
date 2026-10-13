import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "major_revision_v2_3"))
from container_cli import canonical_image_id, executable, working_directory


class ContainerCliTests(unittest.TestCase):
    def test_backend_must_be_explicit_and_allowed(self):
        with patch.dict("os.environ", {"CONVEYORFLOW_CONTAINER_COMMAND": "podman"}):
            self.assertEqual(executable(), "podman")
            self.assertEqual(working_directory(), "/tmp")
        with patch.dict("os.environ", {"CONVEYORFLOW_CONTAINER_COMMAND": "docker"}):
            self.assertEqual(working_directory(), "/work")
        with patch.dict("os.environ", {"CONVEYORFLOW_CONTAINER_COMMAND": "sh"}):
            with self.assertRaises(ValueError):
                executable()

    def test_bare_podman_digest_is_canonicalized(self):
        digest = "a" * 64
        self.assertEqual(canonical_image_id(digest + "\n"), "sha256:" + digest)
        self.assertEqual(canonical_image_id("sha256:" + digest), "sha256:" + digest)


if __name__ == "__main__":
    unittest.main()
