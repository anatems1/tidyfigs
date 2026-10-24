#!/usr/bin/env python3
"""
analyze_text.py — read academic prose and suggest which figures it supports.

    python analyze_text.py paper_section.md            # .md .txt .tex (.docx/.pdf if libs present)
    python analyze_text.py --text "We propose ..."     # inline text
    python analyze_text.py file.tex --split --json out.json

For each passage it reports: word count, display/inline equations, structure cues per figure
family (process, feedback, causal, comparison, hierarchy, temporal, quantitative, architecture,
equation), enumerations, acronyms, numbers, and the three suggested figure types (always from
different layouts). The agent still reads the passage itself — this is a checklist, not a parser.
"""
from __future__ import annotations

import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):
    _sys.stdout.reconfigure(encoding="utf-8")
import argparse
import json
import os
import re
import subprocess
import sys

CUES = {
    "process": [r"\bthen\b", r"\bnext\b", r"\bfinally\b", r"\bfirst(ly)?\b", r"\bsecond(ly)?\b", r"\bsubsequently\b",
                r"\bafter\b", r"\bbefore\b", r"\bstages?\b", r"\bsteps?\b", r"\bpipeline\b", r"\bworkflow\b",
                r"\b(converted|passed|fed|inserted|encoded|segmented|stored|retrieved|re-?ranked|embedded|generated|reviewed|logged|extracted|filtered|aggregated|trained|evaluated)\b",
                r"\bat (query|run|inference|training) time\b", r"\b(offline|online)\b",
                r"\binputs?\b", r"\boutputs?\b", r"\bprocedure\b"],
    "feedback": [r"\bloop\b", r"\bfeedback\b", r"\biterat", r"\brefine", r"\btune[sd]?\b", r"\bupdate[sd]?\b", r"\bcycle\b"],
    "causal": [r"\bdriv(e|es|en)\b", r"\bleads? to\b", r"\bresults? in\b", r"\bcaus", r"\baffect", r"\binfluenc",
               r"\bmoderat", r"\bmediat", r"\bmanifest", r"\bcontribut", r"\bdetermin", r"\binforms?\b", r"\bdue to\b",
               r"\bbecause\b", r"\bin turn\b", r"\boutcome\b"],
    "comparison": [r"\bwhereas\b", r"\bwhile\b", r"\bcompared\b", r"\bin contrast\b", r"\bunlike\b", r"\btrade-?offs?\b",
                   r"\bversus\b", r"\bvs\.?", r"\boutperform", r"\bbetter\b", r"\bworse\b", r"\badvantages?\b",
                   r"\blimitations?\b", r"\b(two|three|four|several) (families|approaches|methods|models|types)\b",
                   r"\bbest\b", r"\bleast\b", r"\bhighest\b", r"\blowest\b", r"\bdominates?\b"],
    "hierarchy": [r"\bconsists? of\b", r"\bcompris", r"\bcomposed of\b", r"\bcategor", r"\btypes? of\b", r"\bclassif",
                  r"\btaxonom", r"\bincludes?\b", r"\bsubsets?\b", r"\bsub-?(types|classes|categories)\b", r"\bhierarch"],
    "temporal": [r"\b(1[89]|20)\d\d\b", r"\bdecades?\b", r"\bsince\b", r"\bhistor", r"\btimeline\b", r"\beras?\b",
                 r"\bphases?\b", r"\bearly\b", r"\blater\b", r"\brecently\b", r"\bevolv"],
    "quantitative": [r"\d+(\.\d+)?\s?%", r"\bpercent", r"\bincreas", r"\bdecreas", r"\baccuracy\b", r"\bF1\b", r"\bmean\b",
                     r"\bmedian\b", r"\bstatistically\b", r"\bp\s?[<=]", r"\bimprov", r"\breduc"],
    "architecture": [r"\blayers?\b", r"\bmodules?\b", r"\bcomponents?\b", r"\bsystem\b", r"\barchitecture\b", r"\bframework\b",
                     r"\binterfaces?\b"],
    "matrix_computation": [r"\b(matrix|matrices|tensor|factoriz|decompos|singular value|svd|eigenvector|eigenvalue|spectral|inner product|dot product|outer product|hadamard|rank|subspace|low-rank|projection)\b"],
    "geometric_metric_space": [r"\b(metric|distance|euclidean|cosine|manifold|neighborhood|geodesic|coordinate|vector space|angle|unit sphere|hypersphere|chord|dimension|embedding|topology|topological|phase space|trajectory|centroid|clustering)\b"],
    "mechanistic_causal": [r"\b(pathway|reaction|stoichiometry|enzyme|kinetics|concentration|substrate|flux|sir model|compartmental|dag\b|directed acyclic|causal graph|instrumental variable|treatment effect|endogeneity|structural equation)\b"],
    "probabilistic_graphical": [r"\b(bayesian|dirichlet|prior|posterior|likelihood|generative|latent|plate notation|markov|mcmc|stochastic|sampling|discrete distribution|bernoulli|poisson)\b"],
}

# figure families per structure: (key, description). The first entries are preferred.
FAMILIES = {
    "process": [("swimlane_pipeline", "stages as lanes (two phases / actors) with routed connectors"),
                ("layered_architecture", "system layers stacked top-to-bottom with components"),
                ("stage_chain", "single left-to-right chain of numbered stage cards"),
                ("timeline", "stages on a time axis")],
    "feedback": [("numbered_cycle", "stages around a hub; closing arrow = feedback")],
    "causal": [("causal_columns", "drivers -> mechanisms -> indicators -> decisions columns"),
               ("concept_map", "hub entity with labeled relations"),
               ("stepped_funnel", "stages narrowing top-to-bottom (compact overview)"),
               ("nested_containers", "factors grouped inside containers")],
    "comparison": [("rating_matrix", "items x criteria with ordinal dots + source wording"),
                   ("method_cards", "one card per item: how / strengths / limitations / best fit"),
                   ("positioning_chart", "two criteria as axes, third as bubble size")],
    "hierarchy": [("tree", "top-down taxonomy tree"), ("nested_boxes", "containment boxes"),
                  ("outline_columns", "indented columns per level")],
    "temporal": [("timeline", "milestones on a horizontal axis"), ("phase_bands", "eras as colored bands"),
                 ("swimlane_pipeline", "actors as lanes over time")],
    "quantitative": [("dot_or_bar_chart", "only values stated in the text"), ("results_table", "values with units"),
                     ("before_after", "slope chart for two conditions")],
    "architecture": [("layered_architecture", "system layers"), ("block_diagram", "components and interfaces")],
    "equation": [("annotated_equation", "each term color-coded with bracketed explanations"),
                 ("computation_graph", "how the quantity is assembled from inputs"),
                 ("intuition_glossary", "geometric/continuum intuition + symbol table")],
    "matrix_computation": [("matrix_factorization_grid", "populated 2D matrix grids with cell reconstruction dot-product arithmetic"),
                           ("comparative_state_spaces", "orthogonal high-D failure vs compressed low-rank semantic subspace"),
                           ("spectral_decomposition", "eigenvector projection and singular value decomposition axes")],
    "geometric_metric_space": [("metric_geometry_clusters", "continuous 2D metric space with unit sphere arc, chord vs cosine, and cluster centroid attraction"),
                               ("divisive_density_clustering", "hyperplane cutting vs density cores and outlier noise segregation"),
                               ("manifold_projection_spaces", "high-D to 2D projection showing local neighborhood vs global geometry preservation")],
    "mechanistic_causal": [("causal_dag", "directed acyclic graph with signed paths and confounder conditioning"),
                           ("reaction_pathway", "reaction network with stoichiometric fluxes, activation and inhibition"),
                           ("compartmental_flow", "state transition boxes with differential rates and feedback")],
    "probabilistic_graphical": [("hierarchical_generative_plate", "Bayesian plate notation with hyperparameter priors and discrete sampling"),
                                ("markov_state_graph", "transition probability states with emission nodes"),
                                ("probabilistic_simplex", "Dirichlet topic mixture simplices and distribution boundaries")],
}

DISPLAY_EQ = [r"\$\$(.+?)\$\$", r"\\\[(.+?)\\\]", r"\\begin\{(equation|align|gather|multline)\*?\}(.+?)\\end\{\1\*?\}"]
INLINE_EQ = r"(?<![\\$])\$(?!\$)(.+?)(?<!\\)\$"


def read_input(path=None, text=None):
    if text is not None:
        return text
    ext = os.path.splitext(path)[1].lower()
    if ext == ".docx":
        try:
            import docx  # python-docx
            return "\n\n".join(p.text for p in docx.Document(path).paragraphs)
        except ImportError:
            sys.exit("reading .docx needs python-docx (pip install python-docx), or paste the text")
    if ext == ".pdf":
        try:
            return subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True, text=True, check=True).stdout
        except Exception:
            try:
                import pypdf
                return "\n\n".join(p.extract_text() or "" for p in pypdf.PdfReader(path).pages)
            except ImportError:
                sys.exit("reading .pdf needs pdftotext or pypdf, or paste the text")
    return open(path, encoding="utf-8", errors="replace").read()


def clean_tex(t):
    t = re.sub(r"(?<!\\)%.*", "", t)                                   # comments
    t = re.sub(r"\\(cite|ref|eqref|label)\{[^}]*\}", "", t)
    t = re.sub(r"\\(emph|textit|textbf|underline)\{([^}]*)\}", r"\2", t)
    return t


def split_passages(text):
    """Split into passages at headings / blank lines; keep display equations with their paragraph."""
    text = text.replace("\r\n", "\n")
    blocks, cur, heading = [], [], None
    lines = text.split("\n")
    in_eq = False
    for ln in lines:
        s = ln.strip()
        if re.match(r"^(#{1,6}\s|\\(sub)*section\*?\{)", s):
            if cur:
                blocks.append((heading, "\n".join(cur).strip())); cur = []
            heading = re.sub(r"^#+\s*|\\(sub)*section\*?\{|\}$", "", s)
            continue
        if s.count("$$") % 2 == 1 or re.match(r"\\begin\{(equation|align)", s) or re.match(r"\\end\{(equation|align)", s):
            in_eq = not in_eq if "$$" in s or "\\begin" in s else False
        if not s and not in_eq:
            if cur:
                blocks.append((heading, "\n".join(cur).strip())); cur = []
            continue
        cur.append(ln)
    if cur:
        blocks.append((heading, "\n".join(cur).strip()))
    # merge a block that is only a display equation into the previous paragraph
    merged = []
    for h, b in blocks:
        if merged and re.fullmatch(r"\s*(\$\$.+?\$\$|\\\[.+?\\\]|\\begin\{.+?\\end\{[a-z*]+\})\s*[.,]?\s*", b, re.S):
            ph, pb = merged[-1]; merged[-1] = (ph, pb + "\n" + b)
        else:
            merged.append((h, b))
    return merged


def analyze_passage(t):
    plain = re.sub(r"\$\$.+?\$\$|\\\[.+?\\\]", " EQUATION ", t, flags=re.S)
    words = re.findall(r"[A-Za-z][A-Za-z\-']*", plain)
    disp = []
    for pat in DISPLAY_EQ:
        for m in re.finditer(pat, t, re.S):
            disp.append(m.group(m.lastindex).strip())
    inline = [m.group(1).strip() for m in re.finditer(INLINE_EQ, re.sub(r"\$\$.+?\$\$", "", t, flags=re.S))]
    low = plain.lower()
    cues = {k: sum(len(re.findall(p, low)) for p in pats) for k, pats in CUES.items()}
    cues["architecture"] = cues["architecture"] // 2          # generic words; weak evidence on its own
    if disp or len(inline) >= 3:
        cues["equation"] = 6 + 3 * len(disp) + len(inline) // 2
    enums = re.findall(r"\((?:i{1,3}|iv|v|[a-e]|\d)\)|\b(?:first|second|third|finally)\b", low)
    acr = sorted(set(re.findall(r"\b[A-Z][A-Z0-9\-]{1,}[a-z]?\b", plain)) - {"EQUATION"})
    nums = re.findall(r"\b\d[\d,]*(?:\.\d+)?\s?(?:%|-dimensional|D\b|[a-zA-Z]{1,3}\b)?", plain)
    sentences = [s.strip() for s in re.split(r"(?<=[.;:])\s+(?=[A-Z(])", plain) if len(s.split()) > 3]
    return dict(words=len(words), sentences=len(sentences), display_equations=disp, inline_math=inline,
                cues=cues, enumerations=len(enums), acronyms=acr, numbers=[n.strip() for n in nums][:30])


def suggest(cues):
    """Three distinct figure types. Default: three layouts of the dominant structure; if a second
    structure is strong (>= half the dominant score) use two + one alternative lens from it."""
    ranked = [k for v, k in sorted(((v, k) for k, v in cues.items() if v > 0), reverse=True)]
    if not ranked:
        return [("concept_map", "fallback"), ("stage_chain", "fallback"), ("method_cards", "fallback")]
    # Active scientific/computational families take precedence over generic cards/timelines
    sci_fams = ["geometric_metric_space", "matrix_computation", "mechanistic_causal", "probabilistic_graphical", "equation"]
    sci_candidates = [(cues[k], k) for k in sci_fams if k in cues and cues[k] >= 2]
    if sci_candidates:
        sci_candidates.sort(reverse=True)
        best_sci = sci_candidates[0][1]
        if best_sci in ranked:
            ranked.remove(best_sci)
            ranked.insert(0, best_sci)
    dom = ranked[0]
    second = next((k for k in ranked[1:] if cues[k] >= 0.5 * cues[dom] and k not in ("architecture",)), None)
    if dom in sci_fams and second not in sci_fams:
        second = None
    picks, seen = [], set()

    def take(fam_key, n):
        for fam, desc in FAMILIES.get(fam_key, []):
            if len(picks) < n and fam not in seen:
                picks.append((fam, f"{fam_key}: {desc}")); seen.add(fam)
    take(dom, 2 if second else 3)
    if second:
        take(second, 3)
    for k in ranked[1:]:
        take(k, 3)
    if dom in ("process", "architecture") and cues.get("feedback", 0) >= 2 and "numbered_cycle" not in seen:
        picks[-1] = ("numbered_cycle", "feedback: stages around a hub; closing arrow = feedback")
    return picks[:3]


def slugify(t, n=4):
    w = [x.lower() for x in re.findall(r"[A-Za-z0-9]+", t) if x.lower() not in STOP][:n]
    return "_".join(w) or "passage"


STOP = set("a an the of and or to in on for with by from as at is are was were be been this that these those we our "
           "it its each such their which into using use used than then also both can may".split())


def analyze(text, split=None, min_words=40):
    text = clean_tex(text)
    blocks = split_passages(text)
    total = sum(len(b.split()) for _, b in blocks)
    if split is None:   # long input, or several headed sections -> one passage per paragraph/section
        split = total > 350 or len({h for h, _ in blocks}) >= 2
    if not split:
        blocks = [(blocks[0][0] if blocks else None, "\n\n".join(b for _, b in blocks))]
    out = []
    for i, (h, b) in enumerate(blocks):
        a = analyze_passage(b)
        if a["words"] < min_words and split:
            continue
        a.update(index=len(out) + 1, heading=h, text=b, slug=slugify(h or b), suggestions=suggest(a["cues"]))
        out.append(a)
    return out


def to_markdown(passages):
    md = []
    for p in passages:
        md += [f"## Passage {p['index']}: {p['heading'] or p['slug']}", "",
               f"- words: {p['words']}, sentences: {p['sentences']}, enumerations: {p['enumerations']}",
               f"- display equations: {len(p['display_equations'])}" + "".join(f"\n  - `{e}`" for e in p["display_equations"]),
               f"- inline math: {', '.join('`' + m + '`' for m in p['inline_math'][:12]) or '—'}",
               f"- acronyms: {', '.join(p['acronyms']) or '—'}",
               f"- numbers: {', '.join(p['numbers'][:15]) or '—'}",
               "- structure cues: " + ", ".join(f"{k} {v}" for k, v in sorted(p["cues"].items(), key=lambda kv: -kv[1]) if v),
               "- suggested prototypes:"] + [f"  {j + 1}. **{f}** — {why}" for j, (f, why) in enumerate(p["suggestions"])] + [""]
    return "\n".join(md)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", nargs="?"); ap.add_argument("--text")
    ap.add_argument("--split", action="store_true", help="force one passage per paragraph/section")
    ap.add_argument("--whole", action="store_true", help="force the whole input as one passage")
    ap.add_argument("--min-words", type=int, default=40); ap.add_argument("--json")
    a = ap.parse_args()
    if not a.path and a.text is None:
        a.text = sys.stdin.read()
    t = read_input(a.path, a.text)
    ps = analyze(t, True if a.split else False if a.whole else None, a.min_words)
    print(to_markdown(ps))
    if a.json:
        json.dump(ps, open(a.json, "w"), indent=1)


if __name__ == "__main__":
    main()
