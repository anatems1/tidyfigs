# Contributing

1. Edit the readable sources in `src/` (scripts, assets, examples) and the docs in `skills/tidyfigs/`.
   **Never edit `skills/tidyfigs/drawio_toolkit.py` by hand** — it is generated.
2. Regenerate the bundle: `python tools/build_bundle.py`
3. Run the checks: `python tools/build_bundle.py --check && pytest -q`
4. Commit `src/` changes **and** the regenerated bundle in the same commit.

Embedded files may not contain `'''` (they are stored as raw triple-quoted strings); the bundler
refuses them.

New example? Put it under `src/examples/`, add a row to the index in `skills/tidyfigs/EXAMPLES.md`,
and keep its build outputs out of git (see `.gitignore`).

When you change behaviour, update `SKILL.md` / `REFERENCE.md` so the instructions Claude reads match
the code, and add a line to `CHANGELOG.md`.
