from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "real_llm_pilot"))

from validator_contract import validate_bundle  # noqa: E402


VALIDATOR = """\
import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--candidate', required=True)
args = parser.parse_args()
value = Path(args.candidate).read_text(encoding='utf-8')
print(json.dumps({'passed': value == 'expected', 'length': len(value)}))
"""


def test_validator_runs_in_isolated_copy(tmp_path: Path) -> None:
    bundle = tmp_path / "frozen_bundle"
    bundle.mkdir()
    (bundle / "validator.py").write_text(VALIDATOR, encoding="utf-8")
    work = tmp_path / "attempt"

    result = validate_bundle(
        bundle_path=bundle,
        validator_command="python validator.py --candidate {candidate}",
        candidate_content="expected",
        work_path=work,
    )

    assert result["passed"] is True
    assert json.loads(result["validator_stdout"])["length"] == 8
    assert not (bundle / "candidate_output.txt").exists()
    assert (work / "candidate_output.txt").read_text(encoding="utf-8") == "expected"


def test_validator_rejects_arbitrary_shell_command(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "validator.py").write_text(VALIDATOR, encoding="utf-8")

    with pytest.raises(ValueError, match="must equal"):
        validate_bundle(
            bundle_path=bundle,
            validator_command="python validator.py; echo unsafe",
            candidate_content="anything",
            work_path=tmp_path / "attempt",
        )


def test_nonzero_validator_exit_cannot_pass(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "validator.py").write_text(
        "import json, sys\nprint(json.dumps({'passed': True}))\nsys.exit(2)\n",
        encoding="utf-8",
    )

    result = validate_bundle(
        bundle_path=bundle,
        validator_command="python validator.py --candidate {candidate}",
        candidate_content="anything",
        work_path=tmp_path / "attempt",
    )
    assert result["passed"] is False
    assert result["validator_exit_code"] == 2
