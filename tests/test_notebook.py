import os

import nbformat
from nbclient import NotebookClient


def test_notebook_runs_top_to_bottom(tmp_path):
    os.environ.update({"DEMO_MODE": "1", "FAKE_LLM": "1", "DB_PATH": str(tmp_path / "nb.db")})
    nb = nbformat.read("demo.ipynb", as_version=4)
    NotebookClient(nb, timeout=120, kernel_name="python3", resources={"metadata": {"path": "."}}).execute()
    text = "".join(
        o.get("text", "") + str(o.get("data", {}).get("text/plain", ""))
        for c in nb.cells if c.cell_type == "code" for o in c.get("outputs", [])
    )
    assert "pending_review" in text and "rejected_non_ai" in text and "needs_review" in text
