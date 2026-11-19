# Tests for the Kaggle kernel builder (WS9 task 1): one notebook per GPU shard, filled in with the job and the shard,
# plus the kernel-metadata.json the Kaggle API needs (GPU on, internet on, private).
import json

from tc import kaggle_kernel as kk


def test_notebook_is_filled_in_and_valid_json(tmp_path):
    folder = kk.write_kernel("20261119-1824-xerxes", 1, "someone", tmp_path)
    nb = json.loads((folder / "tc-render.ipynb").read_text())
    code = "".join("".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code")
    assert 'JOB = "20261119-1824-xerxes"' in code and "INDEX = 1" in code
    assert "{{" not in code                                   # no placeholder left behind


def test_metadata_turns_on_gpu_and_internet_and_stays_private(tmp_path):
    folder = kk.write_kernel("20261119-1824-xerxes", 0, "someone", tmp_path)
    meta = json.loads((folder / "kernel-metadata.json").read_text())
    assert meta["enable_gpu"] is True and meta["enable_internet"] is True and meta["is_private"] is True
    assert meta["id"].startswith("someone/") and meta["code_file"] == "tc-render.ipynb"
    assert len(meta["id"].split("/")[1]) <= 50                # Kaggle slug limit


def test_resume_input_is_attached_when_given(tmp_path):
    folder = kk.write_kernel("j", 0, "someone", tmp_path, resume_from="someone/tc-j-k0")
    meta = json.loads((folder / "kernel-metadata.json").read_text())
    assert meta["kernel_sources"] == ["someone/tc-j-k0"]      # last session's output, mounted under /kaggle/input
