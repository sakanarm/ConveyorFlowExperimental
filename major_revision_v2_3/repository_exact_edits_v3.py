"""Convert explicit model text replacements to a strict existing-file diff."""
import difflib
from repository_patch_guard_v1 import apply_text, parse_patch


def to_patch(answer, sources, allowed):
    if not isinstance(answer, dict) or set(answer) != {"edits"}:
        raise ValueError("expected exactly the edits JSON key")
    edits = answer["edits"]
    if not isinstance(edits, list) or not 1 <= len(edits) <= 8:
        raise ValueError("expected one to eight explicit edits")
    changed = dict(sources)
    original_spans = {}
    for edit in edits:
        if not isinstance(edit, dict) or set(edit) != {"path", "before", "after"}:
            raise ValueError("edit schema mismatch")
        name, before, after = edit["path"], edit["before"], edit["after"]
        if name not in allowed or name not in sources or not isinstance(before, str) or not isinstance(after, str):
            raise ValueError("invalid edit path or text")
        if not before or before == after or "\x00" in before + after or "\r" in before + after:
            raise ValueError("empty, no-op or invalid edit")
        if sources[name].count(before) != 1:
            raise ValueError("before text must appear exactly once in original buggy source")
        start = sources[name].index(before)
        end = start + len(before)
        spans = original_spans.setdefault(name, [])
        if any(start < b and end > a for a, b in spans):
            raise ValueError("overlapping edit spans")
        spans.append((start, end))
        # A previous edit must not create a duplicate anchor or destroy it.
        if changed[name].count(before) != 1:
            raise ValueError("edit interaction or duplicate anchor")
        changed[name] = changed[name].replace(before, after, 1)
    chunks = []
    for name in allowed:
        if changed[name] == sources[name]:
            continue
        if not sources[name].endswith("\n") or not changed[name].endswith("\n"):
            raise ValueError("source edits must retain the final newline")
        chunks.append(f"diff --git a/{name} b/{name}\n")
        chunks.extend(difflib.unified_diff(sources[name].splitlines(keepends=True),
                                          changed[name].splitlines(keepends=True),
                                          fromfile="a/" + name, tofile="b/" + name))
    patch = "".join(chunks).encode("utf-8")
    parsed = parse_patch(patch, allowed)
    for file in parsed:
        if apply_text(sources[file["path"]], file["hunks"]) != changed[file["path"]]:
            raise ValueError("canonical diff differs from explicit edits")
    return patch
