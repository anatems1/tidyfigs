#!/usr/bin/env python3
"""
drawio_toolkit.py — single-file bundle of the draw.io academic-figure toolkit
(modes: image -> drawio, text -> drawio, enhance for publication). See SKILL.md / REFERENCE.md.

USAGE
  python drawio_toolkit.py <tool> [args...]     run a tool (auto-unpacks once to a cache dir)
  python drawio_toolkit.py unpack [DIR] [--force]  write scripts/ assets/ examples/ to DIR
                                                 (default ./tidyfigs) — a normal skill folder
  python drawio_toolkit.py path                  print the unpacked scripts/ dir (for sys.path)
  python drawio_toolkit.py list                  list tools and bundled files

  From Python:  import drawio_toolkit; drawio_toolkit.setup()   # unpacks + adds scripts/ to sys.path
                from drawio_kit import Diagram;  from figlib import *;  from drawio_doc import Doc

TOOLS (python drawio_toolkit.py <tool> --help for options)
  image mode : new_build  inspect_image  iterate  compare
  text mode  : analyze_text  new_figures  prototype  finalize
  enhance    : start_enhance  brief  rebuild  enhance  audit_drawio  report
  shared     : render_preview  lint_drawio  faithful
  libraries  : drawio_kit (builder)  figlib (figure components)  drawio_doc (edit existing files)

Cache dir: $DRAWIO_TOOLKIT_HOME, else ~/.cache/drawio_toolkit/<version>-<hash>, else a temp dir.
Requires Python 3.9+, numpy, pillow; matplotlib (math), pyyaml (YAML themes / enhance).
Optional: scipy or opencv-python, pytesseract + tesseract (OCR), python-docx / pypdf, draw.io desktop CLI.
"""
import hashlib
import os
import subprocess
import sys
import tempfile

VERSION = "2.0"
FILES = {}

# @@BUNDLED_FILES@@
LIBS = {"drawio_kit", "figlib", "drawio_doc", "faithful"}
TOOLS = sorted(p[len("scripts/"):-3] for p in FILES if p.startswith("scripts/") and p.endswith(".py"))


def _digest():
    h = hashlib.sha1()
    for k in sorted(FILES):
        h.update(k.encode()); h.update(FILES[k].encode("utf-8"))
    return h.hexdigest()[:10]


def unpack(dest, force=False, quiet=False):
    """Write every bundled file under dest/. Existing files are kept unless force=True."""
    dest = os.path.abspath(dest)
    written = 0
    for rel, text in FILES.items():
        p = os.path.join(dest, *rel.split("/"))
        if os.path.exists(p) and not force:
            continue
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        written += 1
    with open(os.path.join(dest, ".toolkit_version"), "w") as f:
        f.write(f"{VERSION}-{_digest()}\n")
    if not quiet:
        print(f"unpacked {written} file(s) to {dest}  (skill root: scripts/ assets/ examples/)")
    return dest


def home():
    """Unpacked copy used by the dispatcher (created on first use)."""
    tag = f"{VERSION}-{_digest()}"
    cands = [os.environ.get("DRAWIO_TOOLKIT_HOME"),
             os.path.join(os.path.expanduser("~"), ".cache", "drawio_toolkit", tag),
             os.path.join(tempfile.gettempdir(), "drawio_toolkit", tag)]
    for c in cands:
        if not c:
            continue
        marker = os.path.join(c, ".toolkit_version")
        try:
            if os.path.exists(marker) and open(marker).read().strip() == tag:
                return c
            os.makedirs(c, exist_ok=True)
            return unpack(c, force=True, quiet=True)
        except OSError:
            continue
    raise SystemExit("drawio_toolkit: no writable location to unpack to (set DRAWIO_TOOLKIT_HOME)")


def setup():
    """Unpack (if needed) and put scripts/ on sys.path. Returns the scripts directory."""
    s = os.path.join(home(), "scripts")
    if s not in sys.path:
        sys.path.insert(0, s)
    return s


def main(argv):
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__); return 0
    cmd, rest = argv[0], argv[1:]
    if cmd == "unpack":
        force = "--force" in rest
        dirs = [a for a in rest if not a.startswith("--")]
        unpack(dirs[0] if dirs else "tidyfigs", force=force); return 0
    if cmd == "path":
        print(os.path.join(home(), "scripts")); return 0
    if cmd == "list":
        print("tools:", " ".join(t for t in TOOLS if t not in LIBS))
        print("libraries:", " ".join(sorted(LIBS)))
        print("files:"); [print("  " + k) for k in FILES]; return 0
    tool = cmd[:-3] if cmd.endswith(".py") else cmd
    if tool not in TOOLS:
        print(f"unknown tool '{cmd}'. Tools: {', '.join(TOOLS)}", file=sys.stderr); return 2
    script = os.path.join(home(), "scripts", tool + ".py")
    return subprocess.call([sys.executable, script] + rest)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
