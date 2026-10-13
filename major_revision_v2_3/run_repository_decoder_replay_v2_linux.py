"""Platform-manifest recovery only, before any diagnostic test was executed.

The first decoder lock was created on Windows; its relative-path keys use
backslashes and cannot match WSL's slash keys. Keep that lock unchanged and
freeze a separate Linux-only manifest. Neither patch algorithm nor tests change.
"""
import argparse
import json
import sys
from pathlib import Path
import run_repository_decoder_replay_v2 as replay

HERE = Path(__file__).resolve().parent
CAPSULE = HERE / "repository_decoder_replay_v2_linux_recovery.json"


def setup():
    if sys.platform != "linux":
        raise ValueError("run the platform-recovery entry point in Ubuntu WSL")
    values = {"status": "platform_manifest_revision_before_any_decoder_tests",
              "reason": "Windows relative-path keys differ from WSL slash keys; first invocation stopped before output directory or tests",
              "original_windows_lock_sha256": replay.sha(HERE / "repository_decoder_replay_v2_lock.json"),
              "unchanged_runner_sha256": replay.sha(HERE / "run_repository_decoder_replay_v2.py"),
              "linux_wrapper_sha256": replay.sha(Path(__file__)), "provider_calls": 0,
              "decoder_algorithm_changed": False, "test_or_source_changes": False}
    if CAPSULE.exists():
        if json.loads(CAPSULE.read_text(encoding="utf-8")) != values:
            raise ValueError("platform recovery wrapper changed")
    else:
        if replay.OUT.exists():
            raise ValueError("initial decoder output exists; investigate before recovery")
        replay.save(CAPSULE, values)
    replay.LOCK = HERE / "repository_decoder_replay_v2_linux_lock.json"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    setup()
    if args.freeze:
        print(json.dumps({"status": replay.freeze()["status"], "provider_calls": 0}))
    elif args.execute:
        replay.run()
    else:
        parser.error("choose --freeze or --execute")
