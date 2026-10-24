"""
Prototypes for passage: __TITLE__
Edit v1 / v2 / v3 below, then run:   python __SCRIPTS__/prototype.py __PASSAGE_DIR__
Coordinates are px on each variant's canvas; colors / sizes are theme roles (theme.yaml).
Every label must come from passage.md. Anything you infer goes in INFERRED (it is reported to the user).
"""
from figlib import *   # NODE, SOFT, DARK, MUTED, GHOST, pill, lane, chain, cycle, layers, frame, bracket,
                       # spread, annotated_equation, rating_dots, card, continuum, legend, axes, table, connect

# Claims shown in a figure that the passage does NOT state (judgments, added categories, guessed ratings).
INFERRED = [
    # "v1: rating 'moderate' cost for X (not stated)",
]
# Structural words used in labels that are not content claims (e.g. "layer", "input", "output").
ALLOWED_TERMS = []
# Lint warnings you have looked at and accept on purpose (substring match), e.g. ["uneven gaps"].
LINT_IGNORE = []


def v1(d):
    """__FAMILY1__"""
    # d.rect(...), chain(d, [...], x, y, w, h), d.edge([], src=..., tgt=...), d.equation(r"...", x, y) ...
    pass


def v2(d):
    """__FAMILY2__"""
    pass


def v3(d):
    """__FAMILY3__"""
    pass


VARIANTS = [
    # key, file-name style, canvas (w, h), function, one-line description, draft caption (from the text)
    dict(key="v1", name="__FAMILY1__", size=(1100, 500), build=v1, about="", caption=""),
    dict(key="v2", name="__FAMILY2__", size=(1100, 500), build=v2, about="", caption=""),
    dict(key="v3", name="__FAMILY3__", size=(1100, 500), build=v3, about="", caption=""),
]
