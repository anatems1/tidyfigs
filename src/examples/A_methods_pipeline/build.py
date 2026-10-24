"""Prototypes for passage A (methods: RAG pipeline). Run: python ../../scripts/prototype.py ."""
from figlib import *

INFERRED = []
ALLOWED_TERMS = ["layer", "representation", "retrieval", "evaluation", "data", "parameter", "tuning",
                 "practitioner", "online", "answering", "database", "human", "loop", "ingest"]

HL = style(DARK, bold=False)


def v1(d):
    """Swimlane pipeline: offline indexing lane above, online answering lane below, feedback loop."""
    lane(d, 20, 20, 1060, 175, "Offline indexing")
    lane(d, 20, 215, 1060, 170, "Online answering")
    X = [x for x, _, _, _ in d.row(80, 0, 6, 140, 60, gap=30)]
    off = chain(d, ["Inspection reports\n(scanned)", "OCR\nto text", "Semantic\nchunking",
                    "Embedding model\n(3,072-D)", "Vector database"], 80, 78, 140, 60, gap=30,
                shapes=["document", None, None, None, "cylinder"], ids=["o_rep", "o_ocr", "o_chk", "o_emb", "o_db"])
    d.text("*+ route · milepost · year*", X[4] + 64, 154, anchor="e", size="small", color="primary")
    d.rect(X[5], 78, 140, 60, "**Parameter tuning**\nchunk size · k · prompt", id="tune",
           **style(SOFT, dashed=True, size="label"))
    on = chain(d, ["Practitioner\nquestion", "Query\nembedding", "Retrieve top-k\nsimilar chunks", "Cross-encoder\nre-ranking",
                   "Prompt + LLM\ncited answer", "**Engineer review**\naccuracy · usefulness"], 80, 270, 140, 60, gap=30,
               styles=[SOFT] * 5 + [HL], ids=["n_q", "n_emb", "n_topk", "n_rr", "n_llm", "n_rev"])
    d.text("*same embedding model*", X[1] + 70, 346, size="small", color="secondary")
    d.edge([(X[4] + 70, 205), (X[2] + 70, 205)], src="o_db", tgt="n_topk", color="primary", sw="thick",
           exit=(.5, 1), entry=(.5, 0), label="*retrieve*", label_size="small")
    d.edge([], src="n_rev", tgt="tune", color="secondary", sw="thick", dashed=True, exit=(.5, 0), entry=(.5, 1), label="ratings")
    d.edge([(X[5] + 70, 50), (X[2] + 70, 50)], src="tune", tgt="o_chk", color="secondary", sw="thick", dashed=True,
           exit=(.5, 0), entry=(.5, 0))
    d.text("*closes the loop between system output and expert judgment*", (X[2] + X[5]) / 2 + 70, 38, size="small", color="secondary")


def v2(d):
    """Layered architecture: five layers, flow downward, tuning feedback on the right."""
    spec = [("Data\nlayer", ["Scanned inspection\nreports", "OCR\nto text", "Metadata\nroute · milepost · year"]),
            ("Representation\nlayer", ["Semantic\nchunks", "Embeddings\n(3,072-D)", "Vector\ndatabase"]),
            ("Retrieval\nlayer", ["Query\nembedding", "Retrieve top-k\nsimilar chunks", "Cross-encoder\nre-ranking"]),
            ("Generation\nlayer", ["Structured\nprompt", "Large language\nmodel", "Answer with\ncitations"]),
            ("Evaluation\nlayer", ["**Engineer review**\naccuracy · usefulness", "Ratings\nlog", "Parameter\ntuning"])]
    ids, boxes = layers(d, 40, 20, 940, spec, styles={2: SOFT, 3: SOFT})
    d.get(ids[(4, 0)])["style"].update(fillColor=d.theme.color("primary"), fontColor=d.theme.color("background"))
    yb = boxes[4][1] + boxes[4][3] / 2; yr = boxes[1][1] + boxes[1][3] / 2
    d.edge([(980, yb), (1015, yb), (1015, yr), (980, yr)], color="secondary", sw="thick", dashed=True)
    d.text("{secondary|*tune chunk size · k · prompt*}", 1032, (yb + yr) / 2, rotation=-90, size="label")


def v3(d):
    """Numbered cycle around a human-in-the-loop hub; closing arrow = tuning feedback."""
    labels = ["Ingest & OCR\nscanned reports", "Semantic\nchunking", "Embed chunks\n(3,072-D)", "Vector index\n+ metadata",
              "Embed question,\nretrieve top-k", "Cross-encoder\nre-ranking", "LLM answer\nwith citations", "**Engineer**\n**review**"]
    cycle(d, labels, 470, 320, 330, 240, styles=[NODE] * 4 + [SOFT] * 3 + [HL])
    d.text("{secondary|*tune chunk size · k · prompt*}", 245, 58, size="label")
    d.circle(470, 320, 108, "**Human-in-the-loop RAG**\nfor pavement\ninspection reports", fill="primary", stroke="primary",
             color="background", size="subheading")
    legend(d, 220, 648, [(NODE, "Offline indexing"), (SOFT, "Online answering"), (HL, "Expert judgment")])


VARIANTS = [
    dict(key="v1", name="swimlane_pipeline", size=(1100, 400), build=v1,
         about="Offline and online stages as two lanes; retrieval and the tuning loop drawn as routed connectors.",
         caption="Retrieval-augmented generation framework for pavement inspection reports: offline indexing (top) and online answering with engineer review and parameter tuning (bottom)."),
    dict(key="v2", name="layered_architecture", size=(1060, 600), build=v2,
         about="Five system layers stacked top to bottom with their components; tuning feedback on the side.",
         caption="Layered view of the proposed RAG framework, from scanned reports to expert evaluation; engineer ratings tune chunk size, k and the prompt template."),
    dict(key="v3", name="numbered_cycle", size=(940, 680), build=v3,
         about="Eight stages around a human-in-the-loop hub; offline, online and expert stages styled differently.",
         caption="The RAG workflow as a closed loop: engineer review of cited answers feeds back into chunking, retrieval depth and prompting."),
]
