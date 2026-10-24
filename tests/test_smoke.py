"""
Smoke tests: the shipped bundle is in sync with src/, unpacks, and its core tools run end to end.
Run:  pytest -q
"""
import os
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUNDLE = os.path.join(ROOT, "skills", "tidyfigs", "drawio_toolkit.py")
sys.path.insert(0, os.path.join(ROOT, "tools"))


@pytest.fixture(scope="session")
def env(tmp_path_factory):
    e = dict(os.environ)
    e["DRAWIO_TOOLKIT_HOME"] = str(tmp_path_factory.mktemp("toolkit_home"))  # keep ~/.cache clean
    e["MPLBACKEND"] = "Agg"
    return e


def T(env, *args, cwd=None, check=True):
    r = subprocess.run([sys.executable, BUNDLE, *map(str, args)], cwd=cwd, env=env,
                       capture_output=True, text=True, timeout=600)
    if check and r.returncode != 0:
        raise AssertionError(f"T {' '.join(map(str, args))} failed ({r.returncode}):\n{r.stdout}\n{r.stderr}")
    return r


def test_bundle_in_sync_with_src():
    import build_bundle
    with open(BUNDLE, encoding="utf-8") as f:
        assert f.read() == build_bundle.build(), "run: python tools/build_bundle.py"


def test_list_tools(env):
    out = T(env, "list").stdout
    for tool in ("new_build", "prototype", "start_enhance", "lint_drawio", "render_preview"):
        assert tool in out


def test_unpack(env, tmp_path):
    T(env, "unpack", tmp_path / "fw")
    for rel in ("scripts/drawio_kit.py", "assets/theme.yaml", "examples/A_methods_pipeline/build.py"):
        assert (tmp_path / "fw" / rel).exists()


def test_image_mode_example_builds_lints_renders(env, tmp_path):
    T(env, "unpack", tmp_path / "fw")
    out = tmp_path / "01.drawio"
    subprocess.run([sys.executable, tmp_path / "fw" / "examples" / "01_two_panel_simple.py", "--out", out],
                   env=env, check=True, capture_output=True)
    assert out.exists()
    lint = T(env, "lint_drawio", out)                    # exit 1 only on errors
    assert "0 errors" in lint.stdout
    T(env, "render_preview", out, "-o", tmp_path / "01.png")
    assert (tmp_path / "01.png").stat().st_size > 10_000


def test_text_mode_prototype_and_finalize(env, tmp_path):
    T(env, "unpack", tmp_path / "fw")
    passage = tmp_path / "A"
    shutil.copytree(tmp_path / "fw" / "examples" / "A_methods_pipeline", passage)
    T(env, "prototype", passage, "--note", "ci")
    assert (passage / "prototypes.png").exists()
    T(env, "finalize", passage, "--pick", "v1", "--name", "rag_pipeline")
    assert (passage / "rag_pipeline.drawio").exists()


def test_enhance_mode_starts(env, tmp_path):
    T(env, "unpack", tmp_path / "fw")
    fig = tmp_path / "fig.drawio"
    subprocess.run([sys.executable, tmp_path / "fw" / "examples" / "03_vector_space_plot.py", "--out", fig],
                   env=env, check=True, capture_output=True)
    T(env, "start_enhance", fig)
    work = tmp_path / "fig_enhance_work"
    assert (work / "brief.yaml").exists() and (work / "questions.md").exists()
