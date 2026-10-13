import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "major_revision_v2_3"))
from repository_patch_guard_v1 import apply_text, parse_patch


def patch(path="pkg/source.py", body="@@ -1,2 +1,2 @@\n first\n-old\n+new\n"):
    return (f"diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n" + body).encode()


class PatchGuardTests(unittest.TestCase):
    def test_exact_change(self):
        parsed = parse_patch(patch(), ["pkg/source.py"])
        self.assertEqual(apply_text("first\nold\n", parsed[0]["hunks"]), "first\nnew\n")

    def test_path_scope(self):
        for path in ("../source.py", "/source.py", "pkg/tests/test_x.py", "pkg\\source.py"):
            with self.assertRaises(ValueError):
                parse_patch(patch(path), ["pkg/source.py"])

    def test_bad_counts(self):
        with self.assertRaises(ValueError):
            parse_patch(patch(body="@@ -1,3 +1,2 @@\n first\n-old\n+new\n"), ["pkg/source.py"])

    def test_no_fuzz(self):
        parsed = parse_patch(patch(), ["pkg/source.py"])
        with self.assertRaises(ValueError):
            apply_text("different\nold\n", parsed[0]["hunks"])

    def test_test_manipulation(self):
        for added in ("os._exit(0)", "open('/reports/tests.xml','w')", "pytest.skip()"):
            with self.assertRaises(ValueError):
                parse_patch(patch(body="@@ -1 +1 @@\n-old\n+" + added + "\n"), ["pkg/source.py"])

    def test_modes_binary_and_duplicate_files(self):
        for value in (patch() + patch(), b"GIT binary patch\n", b"\x00"):
            with self.assertRaises(ValueError):
                parse_patch(value, ["pkg/source.py"])

    def test_insertion(self):
        parsed = parse_patch(patch(body="@@ -1,0 +2 @@\n+inserted\n"), ["pkg/source.py"])
        self.assertEqual(apply_text("first\nlast\n", parsed[0]["hunks"]), "first\ninserted\nlast\n")

    def test_no_newline_marker(self):
        parsed = parse_patch(patch(body="@@ -1 +1 @@\n-old\n\\ No newline at end of file\n+new\n\\ No newline at end of file\n"), ["pkg/source.py"])
        self.assertEqual(apply_text("old", parsed[0]["hunks"]), "new")


if __name__ == "__main__":
    unittest.main()
