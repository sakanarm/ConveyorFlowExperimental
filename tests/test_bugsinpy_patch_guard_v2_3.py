"""Source-only patch guard checks for the v2.3 BugsInPy harness."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


V2 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(V2 / "major_revision_v2_3"))
from run_bugsinpy_patch import REFERENCE_PATCH, validate_patch_content  # noqa: E402

# Structural guard fixture, deliberately not an actual repair or gold patch.
ALLOWED_FIXTURE = ("diff --git a/tornado/websocket.py b/tornado/websocket.py\n"
                   "--- a/tornado/websocket.py\n+++ b/tornado/websocket.py\n"
                   "@@ -1 +1 @@\n-fixture_before\n+fixture_after\n")


class PatchGuardTests(unittest.TestCase):
    def test_allowed_source_fixture(self) -> None:
        validate_patch_content(ALLOWED_FIXTURE.encode())

    @unittest.skipUnless(REFERENCE_PATCH.is_file(), 'Requires the separately fetched pinned BugsInPy checkout')
    def test_trusted_reference_modifies_only_allowed_source(self) -> None:
        validate_patch_content(REFERENCE_PATCH.read_bytes())

    def test_test_file_tampering_is_rejected(self) -> None:
        text = (
            "diff --git a/tornado/test/websocket_test.py b/tornado/test/websocket_test.py\n"
            "--- a/tornado/test/websocket_test.py\n"
            "+++ b/tornado/test/websocket_test.py\n"
            "@@ -1 +1 @@\n-a\n+b\n"
        )
        with self.assertRaises(ValueError):
            validate_patch_content(text.encode())

    def test_second_file_and_path_traversal_are_rejected(self) -> None:
        trusted = ALLOWED_FIXTURE
        for extra in (
            "diff --git a/../test.py b/../test.py\n--- a/../test.py\n+++ b/../test.py\n@@ -1 +1 @@\n-a\n+b\n",
            "diff --git a/tornado/web.py b/tornado/web.py\n--- a/tornado/web.py\n+++ b/tornado/web.py\n@@ -1 +1 @@\n-a\n+b\n",
        ):
            with self.subTest(extra=extra.splitlines()[0]):
                with self.assertRaises(ValueError):
                    validate_patch_content((trusted + extra).encode())

    def test_binary_and_rename_are_rejected(self) -> None:
        trusted = ALLOWED_FIXTURE.encode()
        with self.assertRaises(ValueError):
            validate_patch_content(trusted + b"\x00")
        with self.assertRaises(ValueError):
            validate_patch_content(trusted + b"rename to tornado/websocket.py\n")


if __name__ == "__main__":
    unittest.main()
