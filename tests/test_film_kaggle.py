# Tests for the Kaggle side of film renders: the notebook that renders frame ranges on Kaggle's free CPUs.
import json

from tc import film_kaggle as fk


def _code(nb: dict) -> list[str]:
    return ["".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code"]


def test_kaggle_metadata_internet_on():
    m = fk.film_metadata("someone", "tc-film-fleettest-0")
    assert m["enable_internet"] is True and m["enable_gpu"] is False and m["is_private"] is True
    assert m["id"] == "someone/tc-film-fleettest-0" and m["kernel_type"] == "notebook"


def test_notebook_first_cell_checks_internet():
    first = _code(fk.film_notebook("FleetTest", [(0, 95)]))[0]
    assert 'urllib.request.urlopen("https://github.com"' in first and "Kaggle internet is off" in first


def test_notebook_renders_every_range():
    code = "\n".join(_code(fk.film_notebook("FleetTest", [(0, 95), (96, 191)], ref="master")))
    assert "render-part.mjs FleetTest 0 95 /kaggle/working/parts" in code
    assert "render-part.mjs FleetTest 96 191 /kaggle/working/parts" in code
    assert "--branch master" in code


def test_slug_is_short_and_safe():
    s = fk.film_slug("FleetTestLong", [(20000, 21599)])
    assert len(s) <= 50 and s == s.lower() and " " not in s


def test_write_kernel_files(tmp_path):
    d = fk.write_film_kernel("FleetTest", [(0, 9)], "someone", tmp_path)
    meta = json.loads((d / "kernel-metadata.json").read_text(encoding="utf-8"))
    assert (d / meta["code_file"]).exists()


def test_unsafe_names_rejected():
    import pytest
    with pytest.raises(ValueError):
        fk.film_notebook("Fleet; rm -rf /", [(0, 1)])
