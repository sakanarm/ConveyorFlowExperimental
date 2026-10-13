"""Strict, no-fuzz unified diffs for a frozen Python source allowlist.

Host use parses patch data only. Application to repository source takes place
inside the candidate container; never import or execute the submitted source.
"""
from __future__ import annotations
import re
from pathlib import Path, PurePosixPath

MAX_BYTES = 200_000
HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(?:.*)$")


def parse_patch(raw: bytes, allowed: list[str]) -> list[dict]:
    if not raw or len(raw) > MAX_BYTES or b"\x00" in raw:
        raise ValueError("empty, oversized or binary patch")
    text = raw.decode("utf-8")
    if "\r" in text:
        raise ValueError("patch must use LF line endings")
    lines = text.splitlines(keepends=True)
    files, index, seen = [], 0, set()
    while index < len(lines):
        header = lines[index].rstrip("\n")
        match = re.fullmatch(r"diff --git a/([^ ]+) b/([^ ]+)", header)
        if not match or match[1] != match[2]:
            raise ValueError("each file must begin with a same-path git diff header")
        name = match[1]
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or "\\" in name or name not in allowed or name in seen:
            raise ValueError("patch path outside allowlist or duplicated")
        seen.add(name)
        index += 1
        if index < len(lines) and lines[index].startswith("index "):
            if not re.fullmatch(r"index [0-9a-f]+\.\.[0-9a-f]+(?: 100644)?\n?", lines[index]):
                raise ValueError("unsupported index/mode metadata")
            index += 1
        if lines[index:index + 2] != [f"--- a/{name}\n", f"+++ b/{name}\n"]:
            raise ValueError("only existing-file changes with canonical headers are supported")
        index += 2
        hunks = []
        while index < len(lines) and not lines[index].startswith("diff --git "):
            m = HUNK.fullmatch(lines[index].rstrip("\n"))
            if not m:
                raise ValueError("invalid hunk header or unsupported patch metadata")
            old_start, old_count, new_start, new_count = (int(m[1]), int(m[2] or 1), int(m[3]), int(m[4] or 1))
            index += 1
            body = []
            old_seen = new_seen = 0
            while index < len(lines) and not lines[index].startswith(("@@ ", "diff --git ")):
                line = lines[index]
                if line.startswith("\\ No newline at end of file"):
                    if not body:
                        raise ValueError("orphan no-newline marker")
                    body[-1] = body[-1][:-1] if body[-1].endswith("\n") else body[-1]
                elif line.startswith((" ", "-", "+")):
                    body.append(line)
                    old_seen += line[0] in {" ", "-"}
                    new_seen += line[0] in {" ", "+"}
                else:
                    raise ValueError("invalid hunk content")
                index += 1
            if (old_seen, new_seen) != (old_count, new_count):
                raise ValueError("hunk line counts are inconsistent")
            added = "\n".join(line[1:] for line in body if line.startswith("+"))
            # Localized repairs need no test-runner/report manipulation.
            if re.search(r"/protected|/reports|MFEC_LITELLM|pytest|sys\.exit|os\._exit|sys\.modules|subprocess|exec\s*\(|eval\s*\(", added):
                raise ValueError("added source contains test/report or execution-control manipulation")
            hunks.append({"old_start": old_start, "old_count": old_count,
                          "new_start": new_start, "new_count": new_count, "lines": body})
        if not hunks:
            raise ValueError("file has no hunks")
        files.append({"path": name, "hunks": hunks})
    return files


def apply_text(original: str, hunks: list[dict]) -> str:
    source = original.splitlines(keepends=True)
    result, cursor = [], 0
    for hunk in hunks:
        start = hunk["old_start"] - 1 if hunk["old_count"] else hunk["old_start"]
        if start < cursor or start > len(source):
            raise ValueError("overlapping/out-of-bounds hunk")
        result.extend(source[cursor:start])
        cursor = start
        expected_new = hunk["new_start"] - 1 if hunk["new_count"] else hunk["new_start"]
        if expected_new != len(result):
            raise ValueError("inconsistent new hunk offset")
        for line in hunk["lines"]:
            if line[0] in {" ", "-"}:
                if cursor >= len(source) or source[cursor] != line[1:]:
                    raise ValueError("context mismatch; fuzzy matching is forbidden")
                cursor += 1
            if line[0] in {" ", "+"}:
                result.append(line[1:])
    result.extend(source[cursor:])
    return "".join(result)


def apply_in_container(root: Path, patch: Path, allowed: list[str]):
    if str(root) != "/tmp/work" or str(patch) != "/submission/patch.diff":
        raise ValueError("application is restricted to the isolated evaluator paths")
    changes = []
    for file in parse_patch(patch.read_bytes(), allowed):
        target = root / file["path"]
        if target.is_symlink() or root.resolve() not in target.resolve().parents or not target.is_file():
            raise ValueError("source file missing or follows an escaping link")
        original = target.read_text(encoding="utf-8")
        changed = apply_text(original, file["hunks"])
        # Syntax check is compile only, not import/execution.
        compile(changed, file["path"], "exec")
        changes.append((target, changed))
    for target, changed in changes:
        target.write_text(changed, encoding="utf-8")


if __name__ == "__main__":
    import json
    import sys
    if sys.platform != "linux":
        raise SystemExit("repository patch application is Linux-container-only")
    apply_in_container(Path("/tmp/work"), Path("/submission/patch.diff"), json.loads(sys.argv[1]))
