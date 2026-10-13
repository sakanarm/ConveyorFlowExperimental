import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "major_revision_v2_3"))
from prepare_repository_first_attempt_v1 import excerpts


class Excerpts(unittest.TestCase):
    def test_small_verbatim(self):
        text = 'def foo():\n    return 3\n'
        self.assertEqual(excerpts(text, ["foo"])[0]["text"], text)

    def test_long_exact_lines(self):
        text = '# padding\n' * 7000 + '@staticmethod\ndef foo():\n    return 3\n'
        chunks = excerpts(text, ["foo"])
        self.assertEqual(len(chunks), 2)
        for c in chunks:
            self.assertEqual(c["text"], ''.join(text.splitlines(keepends=True)[c["start_line"]-1:c["end_line"]]))
        self.assertIn('@staticmethod\ndef foo()', chunks[-1]["text"])

    def test_long_missing_public_symbol_rejected(self):
        with self.assertRaises(ValueError):
            excerpts('# padding\n' * 7000 + 'def foo():\n    pass\n', ["other"])


if __name__ == '__main__':
    unittest.main()
