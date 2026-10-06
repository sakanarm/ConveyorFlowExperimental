"""Metadata-only patch recovery against unique exact buggy-source context.

This diagnostic decoder never invents an addition/deletion, uses no fixed
source or tests, and rejects ambiguous, whitespace-different or missing context.
The original strict guard still applies to the resulting canonical patch.
"""
import re
from repository_patch_guard_v1 import MAX_BYTES, apply_text, parse_patch


def sections(raw, allowed):
    if not raw or len(raw.encode("utf-8")) > MAX_BYTES or "\r" in raw or "\x00" in raw:
        raise ValueError("empty, oversized or non-LF patch")
    lines = raw.splitlines(keepends=True)
    alternate = lines[0].rstrip("\n") == "*** Begin Patch"
    if alternate:
        if lines[-1].rstrip("\n") != "*** End Patch":
            raise ValueError("missing patch end marker")
        lines = lines[1:-1]
    result, seen, index = [], set(), 0
    while index < len(lines):
        if alternate:
            match = re.fullmatch(r"\*\*\* Update File: (.+)", lines[index].rstrip("\n"))
            if not match:
                raise ValueError("only existing-file update markers are supported")
            name = match[1]
            index += 1
        else:
            match = re.fullmatch(r"diff --git a/([^ ]+) b/([^ ]+)", lines[index].rstrip("\n"))
            if not match or match[1] != match[2]:
                raise ValueError("invalid same-path diff header")
            name = match[1]
            index += 1
            if index < len(lines) and lines[index].startswith("index "):
                if not re.fullmatch(r"index [0-9a-f]+\.\.[0-9a-f]+(?: 100644)?\n?", lines[index]):
                    raise ValueError("invalid index metadata")
                index += 1
            if lines[index:index + 2] != ["--- a/" + name + "\n", "+++ b/" + name + "\n"]:
                raise ValueError("noncanonical file headers")
            index += 2
        if name not in allowed or name in seen:
            raise ValueError("path outside allowlist or duplicated")
        seen.add(name)
        bodies = []
        while index < len(lines) and not lines[index].startswith(("diff --git ", "*** Update File:")):
            header = lines[index].rstrip("\n")
            if alternate:
                if header != "@@" and not header.startswith("@@ "):
                    raise ValueError("invalid alternate hunk marker")
            elif not re.fullmatch(r"@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@.*", header):
                raise ValueError("invalid unified hunk marker")
            index += 1
            body = []
            while index < len(lines) and not lines[index].startswith(("@@", "diff --git ", "*** Update File:")):
                line = lines[index]
                if not line.startswith((" ", "+", "-")) or not line.endswith("\n"):
                    raise ValueError("unsupported hunk content or newline marker")
                body.append(line)
                index += 1
            if not body:
                raise ValueError("empty hunk")
            bodies.append(body)
        if not bodies:
            raise ValueError("file has no hunks")
        result.append((name, bodies))
    return result


def normalize(raw, sources, allowed):
    output, audit = [], []
    for name, bodies in sections(raw, allowed):
        if name not in sources:
            raise ValueError("missing original buggy source")
        source = sources[name].splitlines(keepends=True)
        output.extend([f"diff --git a/{name} b/{name}\n", f"--- a/{name}\n", f"+++ b/{name}\n"])
        delta, cursor, locations = 0, 0, []
        for body in bodies:
            old = [line[1:] for line in body if line[0] in " -"]
            new_count = sum(line[0] in " +" for line in body)
            if not old:
                raise ValueError("insertion without exact old context is unsupported")
            hits = [i for i in range(len(source) - len(old) + 1) if source[i:i + len(old)] == old]
            if len(hits) != 1:
                raise ValueError("old context must match exactly once; no fuzzy matching")
            start = hits[0]
            if start < cursor:
                raise ValueError("overlapping or reversed hunks")
            output.append(f"@@ -{start + 1},{len(old)} +{start + delta + 1},{new_count} @@\n")
            output.extend(body)
            locations.append({"old_start": start + 1, "old_count": len(old),
                              "new_start": start + delta + 1, "new_count": new_count})
            cursor = start + len(old)
            delta += new_count - len(old)
        audit.append({"path": name, "locations": locations})
    canonical = "".join(output).encode("utf-8")
    parsed = parse_patch(canonical, allowed)
    for file in parsed:
        apply_text(sources[file["path"]], file["hunks"])
    return canonical, audit
