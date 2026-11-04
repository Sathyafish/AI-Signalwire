"""Generate demo.ipynb. Run from the repo root: python scripts/make_notebook.py"""
import nbformat as nbf

md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell

cells = [
    md("# AI Signalwire demo\n\nRun the cells top to bottom. The pipeline fetches AI news and framework releases, "
       "checks relevance, drafts posts, validates and evaluates them, then waits for your approval."),
    md("## Setup"),
    code(
        "import os, sys\n"
        "sys.path.insert(0, os.getcwd())\n"
        "from dotenv import load_dotenv\n"
        "load_dotenv()\n"
        "import pandas as pd\n"
        "from IPython.display import HTML, display\n"
        "import ipywidgets as widgets\n"
        "from src.config import load_settings, load_sources\n"
        "from src.llm import get_llm\n"
        "from src.storage.db import Database\n"
        "from src.pipeline import run_pipeline\n"
        "from src.review.queue import pending_review, needs_attention, approve, reject\n"
        "from src.publishing.local_blog import render_blog_html\n"
        "\n"
        "settings = load_settings()\n"
        "db = Database(settings.db_path)\n"
        "llm = get_llm(settings, 'agent')\n"
        "eval_llm = get_llm(settings, 'evaluator')\n"
        "mode = 'fake model' if settings.fake_llm else f'{settings.provider} ({settings.agent_model}, evaluator {settings.evaluator_model})'\n"
        "print('LLM:', mode)\n"
        "print('Articles:', 'canned demo set' if settings.demo_mode else 'live sources')\n"
    ),
    md("## Configure\n\nSources come from `config/sources.yaml`. Disable any you don't want there."),
    code(
        "sources = load_sources()\n"
        "print(f'{len(sources)} sources, up to {settings.items_per_source} items each')\n"
        "pd.DataFrame([s.model_dump() for s in sources])[['name', 'type', 'adapter', 'url']]\n"
    ),
    md("## Run pipeline"),
    code(
        "result = run_pipeline(db, settings, sources, llm, eval_llm)\n"
        "print({k: v for k, v in result.items() if k != 'article_ids'})\n"
        "def status_table():\n"
        "    rows = db.list_articles()\n"
        "    return pd.DataFrame([{'id': r['id'], 'source': r['source_name'], 'title': r['title'][:70], 'status': r['status']} for r in rows])\n"
        "status_table()\n"
    ),
    md("## Inspect one article"),
    code(
        "def show(article_id):\n"
        "    r = db.get(article_id)\n"
        "    print(f\"#{r['id']} {r['title']}  [{r['status']}]\")\n"
        "    print('Relevance:', r['relevance'])\n"
        "    print('Draft:', r['post'])\n"
        "    print('Validation errors:', r['validation'])\n"
        "    print('Evaluator:', r['evaluation'])\n"
        "    print('Error:', r['error'])\n"
        "rows = pending_review(db) or db.list_articles()\n"
        "if rows:\n"
        "    show(rows[0]['id'])\n"
    ),
    md("## Review queue\n\nApprove publishes to the local blog. Reject sends the item back for investigation."),
    code(
        "blog_out = widgets.Output()\n"
        "def refresh_blog():\n"
        "    with blog_out:\n"
        "        blog_out.clear_output()\n"
        "        display(HTML(render_blog_html(db)))\n"
        "\n"
        "def queue_row(r):\n"
        "    post = r['post']\n"
        "    label = widgets.HTML(f\"<b>{post['title']}</b><br>Evaluator: {r['evaluation']['verdict']}, {r['evaluation']['reason']}\")\n"
        "    ok, no = widgets.Button(description='Approve', button_style='success'), widgets.Button(description='Reject', button_style='danger')\n"
        "    def done(text):\n"
        "        ok.disabled = no.disabled = True\n"
        "        label.value += f'<br><i>{text}</i>'\n"
        "        refresh_blog()\n"
        "    ok.on_click(lambda b: (approve(db, r['id']), done('Approved and published')))\n"
        "    no.on_click(lambda b: (reject(db, r['id'], 'Rejected in review'), done('Rejected')))\n"
        "    return widgets.HBox([label, ok, no])\n"
        "\n"
        "pending = pending_review(db)\n"
        "display(widgets.VBox([queue_row(r) for r in pending]) if pending else widgets.HTML('No drafts waiting for review.'))\n"
        "print('Needs attention:')\n"
        "pd.DataFrame([{'id': r['id'], 'title': r['title'][:60], 'status': r['status'], 'reason': (r['error'] or '')[:80]} for r in needs_attention(db)])\n"
    ),
    md("## Blog\n\nPublished posts appear here. Run this cell again after approving."),
    code("refresh_blog()\nblog_out\n"),
    md("## Reset\n\nUncomment to clear the database for a fresh demo."),
    code("# db.reset()\n"),
]

nb = nbf.v4.new_notebook(cells=cells)
nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
nbf.write(nb, "demo.ipynb")
print("wrote demo.ipynb")
