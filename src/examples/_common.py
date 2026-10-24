"""Shared CLI for the example builds:  python 0X_example.py [--image SRC] [--out OUT.drawio] [--theme T] [--scale S]"""
import argparse
import os
import sys

SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
sys.path.insert(0, SCRIPTS)
from drawio_kit import Diagram, Theme  # noqa: E402


def run(layout, size, theme_overrides=None, name="example", coord_scale=(1.0, 1.0)):
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", help="source image (needed for image_crop; also sets page size)")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", name + ".drawio"))
    ap.add_argument("--theme", default=None, help="theme file (default: assets/theme_image.yaml)")
    ap.add_argument("--scale", type=float, default=1.0)
    a = ap.parse_args()
    theme = Theme.load(a.theme or os.path.join(os.path.dirname(SCRIPTS), "assets", "theme_image.yaml"), overrides=theme_overrides)
    if a.image:
        d = Diagram.from_source(a.image, theme=theme, scale=a.scale, coord_scale=coord_scale)
    else:
        d = Diagram(*size, theme=theme, scale=a.scale, coord_scale=coord_scale)
    layout(d)
    d.save(a.out)
    return a.out
