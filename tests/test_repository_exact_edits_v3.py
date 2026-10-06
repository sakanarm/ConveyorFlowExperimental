import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "major_revision_v2_3"))
from repository_exact_edits_v3 import to_patch
from repository_patch_guard_v1 import parse_patch, apply_text


class EditsTests(unittest.TestCase):
    source = {"x.py": "a = 1\nb = 2\nc = 3\n"}

    def test_exact_replacement(self):
        p = to_patch({"edits": [{"path": "x.py", "before": "b = 2", "after": "b = 7"}]}, self.source, ["x.py"])
        self.assertEqual(apply_text(self.source["x.py"], parse_patch(p, ["x.py"])[0]["hunks"]), "a = 1\nb = 7\nc = 3\n")

    def test_ambiguous(self):
        with self.assertRaises(ValueError):
            to_patch({"edits": [{"path": "x.py", "before": " = ", "after": " = 7"}]}, self.source, ["x.py"])

    def test_path(self):
        with self.assertRaises(ValueError):
            to_patch({"edits": [{"path": "../x.py", "before": "b = 2", "after": "b = 7"}]}, self.source, ["x.py"])

    def test_fuzzy_rejected(self):
        with self.assertRaises(ValueError):
            to_patch({"edits": [{"path": "x.py", "before": "b=2", "after": "b=7"}]}, self.source, ["x.py"])

    def test_manipulation_rejected(self):
        with self.assertRaises(ValueError):
            to_patch({"edits": [{"path": "x.py", "before": "b = 2", "after": "sys.exit(0)"}]}, self.source, ["x.py"])

    def test_overlapping_rejected(self):
        with self.assertRaises(ValueError):
            to_patch({"edits": [{"path": "x.py", "before": "b = 2", "after": "b = 7"},
                                {"path": "x.py", "before": "b = 2\nc = 3", "after": "z = 0"}]}, self.source, ["x.py"])


if __name__ == "__main__":
    unittest.main()
