#!/usr/bin/env python3
"""
package_skill.py — build dist/tidyfigs.zip, ready to upload as a Claude skill.

    python tools/package_skill.py          # rebuilds the bundle first, then zips skills/tidyfigs/

The zip contains a single top-level folder `tidyfigs/` with SKILL.md, REFERENCE.md, EXAMPLES.md,
drawio_toolkit.py and LICENSE.
"""
import os
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(ROOT, "skills", "tidyfigs")
DIST = os.path.join(ROOT, "dist")
FILES = ["SKILL.md", "REFERENCE.md", "EXAMPLES.md", "drawio_toolkit.py"]


def main():
    subprocess.check_call([sys.executable, os.path.join(ROOT, "tools", "build_bundle.py")])
    os.makedirs(DIST, exist_ok=True)
    out = os.path.join(DIST, "tidyfigs.zip")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for name in FILES:
            z.write(os.path.join(SKILL, name), f"tidyfigs/{name}")
        z.write(os.path.join(ROOT, "LICENSE"), "tidyfigs/LICENSE")
    print(f"wrote {os.path.relpath(out, ROOT)} ({os.path.getsize(out) // 1024} KB)")


if __name__ == "__main__":
    main()
