import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "major_revision_v2_3"))
from repository_patch_normalizer_v2 import normalize
from repository_patch_guard_v1 import apply_text, parse_patch


class NormalizerTests(unittest.TestCase):
    def setUp(self):
        self.source = {"x.py": "a = 1\nb = 2\nc = 3\n"}

    def run_patch(self, body):
        return normalize("*** Begin Patch\n*** Update File: x.py\n@@\n" + body + "*** End Patch", self.source, ["x.py"])[0]

    def test_metadata_only_alternate(self):
        patch = self.run_patch(" a = 1\n-b = 2\n+b = 4\n c = 3\n")
        self.assertEqual(apply_text(self.source["x.py"], parse_patch(patch, ["x.py"])[0]["hunks"]), "a = 1\nb = 4\nc = 3\n")

    def test_wrong_counts_and_offsets(self):
        raw = "diff --git a/x.py b/x.py\n--- a/x.py\n+++ b/x.py\n@@ -90,42 +90,99 @@\n a = 1\n-b = 2\n+b = 4\n c = 3\n"
        fixed, audit = normalize(raw, self.source, ["x.py"])
        self.assertIn(b"@@ -1,3 +1,3 @@", fixed)
        self.assertEqual(audit[0]["locations"][0]["old_start"], 1)

    def test_multiple_hunks_offsets(self):
        raw = "*** Begin Patch\n*** Update File: x.py\n@@\n a = 1\n+z = 7\n@@\n-c = 3\n+c = 8\n*** End Patch"
        patch, _ = normalize(raw, self.source, ["x.py"])
        self.assertEqual(apply_text(self.source["x.py"], parse_patch(patch, ["x.py"])[0]["hunks"]), "a = 1\nz = 7\nb = 2\nc = 8\n")

    def test_missing_exact_context(self):
        with self.assertRaises(ValueError):
            self.run_patch("-b=2\n+b = 4\n")

    def test_ambiguous_context(self):
        self.source["x.py"] = "b = 2\nb = 2\n"
        with self.assertRaises(ValueError):
            self.run_patch("-b = 2\n+b = 4\n")

    def test_no_context_insertion(self):
        with self.assertRaises(ValueError):
            self.run_patch("+z = 4\n")

    def test_forbidden_added_code(self):
        with self.assertRaises(ValueError):
            self.run_patch(" a = 1\n+sys.exit(0)\n")

    def test_path_escape(self):
        with self.assertRaises(ValueError):
            normalize("*** Begin Patch\n*** Update File: ../x.py\n@@\n-a = 1\n+a = 2\n*** End Patch", self.source, ["x.py"])

    def test_delete_marker_rejected(self):
        with self.assertRaises(ValueError):
            normalize("*** Begin Patch\n*** Delete File: x.py\n*** End Patch", self.source, ["x.py"])

    def test_overlapping_hunks(self):
        with self.assertRaises(ValueError):
            normalize("*** Begin Patch\n*** Update File: x.py\n@@\n-a = 1\n+a = 2\n@@\n-a = 1\n+a = 4\n*** End Patch", self.source, ["x.py"])


if __name__ == "__main__":
    unittest.main()
