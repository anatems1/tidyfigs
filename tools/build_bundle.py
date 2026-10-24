#!/usr/bin/env python3
"""
build_bundle.py — regenerate the single-file skill bundle from the readable sources.

    python tools/build_bundle.py            # writes skills/tidyfigs/drawio_toolkit.py
    python tools/build_bundle.py --check    # exit 1 if the committed bundle is out of date (CI)

src/ (scripts/, assets/, examples/) is the source of truth. The bundle embeds every file as a raw
string so the skill can ship as four files (SKILL.md, REFERENCE.md, EXAMPLES.md, drawio_toolkit.py)
and unpack itself on first use. Never edit the bundle by hand.
"""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
STUB = os.path.join(ROOT, "tools", "bundle_stub.py")
OUT = os.path.join(ROOT, "skills", "tidyfigs", "drawio_toolkit.py")
TOP_LEVEL = ("scripts", "assets", "examples")      # bundle order
SKIP_DIRS = {"__pycache__", "out", ".pytest_cache"}
SKIP_EXT = {".pyc", ".drawio", ".png"}               # build outputs never get bundled
SEP = "# " + "=" * 96 + "\n"
MARKER = "# @@BUNDLED_FILES@@\n"


def walk(rel_dir):
    """Files of a directory (sorted), then its subdirectories (sorted) — the bundle's order."""
    base = os.path.join(SRC, rel_dir)
    entries = sorted(os.listdir(base))
    files = [e for e in entries if os.path.isfile(os.path.join(base, e))
             and os.path.splitext(e)[1] not in SKIP_EXT and not e.startswith(".")]
    dirs = [e for e in entries if os.path.isdir(os.path.join(base, e)) and e not in SKIP_DIRS]
    for f in files:
        yield f"{rel_dir}/{f}"
    for sub in dirs:
        yield from walk(f"{rel_dir}/{sub}")


def build():
    parts = []
    for top in TOP_LEVEL:
        for rel in walk(top):
            with open(os.path.join(SRC, *rel.split("/")), encoding="utf-8") as f:
                text = f.read()
            if "'''" in text:
                sys.exit(f"build_bundle: {rel} contains ''' which cannot be embedded in a raw string")
            if text.endswith("\\"):
                sys.exit(f"build_bundle: {rel} ends with a backslash (breaks the raw string)")
            parts.append(f"{SEP}FILES['{rel}'] = r'''{text}'''\n\n")
    with open(STUB, encoding="utf-8") as f:
        stub = f.read()
    if MARKER not in stub:
        sys.exit("build_bundle: marker missing from tools/bundle_stub.py")
    return stub.replace(MARKER, "".join(parts) + "\n")


def embedded(text):
    """FILES dict of a bundle's source text (without running its dispatcher)."""
    ns = {"__name__": "bundle_check"}
    try:
        exec(compile(text, "bundle", "exec"), ns)
    except Exception as e:                      # noqa: BLE001
        print(f"  (committed bundle does not load: {e})")
        return {}
    return ns.get("FILES", {})


def explain(current):
    """Say which embedded files differ, so a failing CI check is self-explanatory."""
    old = embedded(current)
    new = {}
    for top in TOP_LEVEL:
        for rel in walk(top):
            with open(os.path.join(SRC, *rel.split("/")), encoding="utf-8") as f:
                new[rel] = f.read()
    for rel in sorted(set(old) - set(new)):
        print(f"  in bundle but missing from src/ : {rel}   (not committed? check .gitignore / git ls-files)")
    for rel in sorted(set(new) - set(old)):
        print(f"  in src/ but not in bundle       : {rel}")
    for rel in sorted(set(old) & set(new)):
        if old[rel] != new[rel]:
            a, b = old[rel], new[rel]
            i = next((k for k in range(min(len(a), len(b))) if a[k] != b[k]), min(len(a), len(b)))
            line = a[:i].count("\n") + 1
            print(f"  content differs                 : {rel}  (first difference at line {line}; "
                  f"bundle {len(a)} chars, src {len(b)} chars)")
    if set(old) == set(new) and all(old[k] == new[k] for k in old):
        print("  embedded files match — the difference is in tools/bundle_stub.py (header/footer)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="fail if the committed bundle differs from src/")
    ap.add_argument("-o", "--out", default=OUT)
    a = ap.parse_args()
    bundle = build()
    if a.check:
        current = open(a.out, encoding="utf-8").read() if os.path.exists(a.out) else ""
        if current != bundle:
            print(f"{os.path.relpath(a.out, ROOT)} is out of date — run: python tools/build_bundle.py")
            explain(current)
            return 1
        print("bundle up to date")
        return 0
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        f.write(bundle)
    print(f"wrote {os.path.relpath(a.out, ROOT)} ({bundle.count(chr(10))} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
