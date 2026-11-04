# AI Signalwire: setup, testing and demo guide

Follow this guide top to bottom. Part 1 sets up the project, Part 2 tests it, Part 3 rehearses the demo offline, and Part 4 runs the live demo with a real model.

All commands run from the project folder:

```bash
cd "/Users/narayas/Documents/DES Project Sathya/AI-Signalwire"
```

## Part 1: setup (about 10 minutes)

### 1.1 What you need

- Python 3.11 or newer. This project was built with Python 3.13. Check with `python3.13 --version`.
- Internet access to install packages and to fetch live articles.
- For the live demo only: an Azure OpenAI or OpenAI API key.

### 1.2 Create the environment and install packages

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If `pip` fails on the Autodesk network with a certificate error or "connection reset" on `files.pythonhosted.org`:

- Connect to the VPN or office network and retry.
- If your team has an internal PyPI mirror, install with `pip install --index-url <mirror-url> -r requirements.txt`.
- Try `pip install --index-url https://pypi.org/simple -r requirements.txt`. This worked during the build when the default index did not.

Check the install:

```bash
python -c "import langgraph, langchain_openai, feedparser, trafilatura, ipywidgets; print('ok')"
```

Expected: `ok`.

### 1.3 Add your model key (live demo only)

```bash
cp .env.example .env
```

Open `.env` and fill in **one** of these:

| Provider | Set these |
|---|---|
| Azure OpenAI | `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, and `AGENT_MODEL` set to your **deployment name** |
| OpenAI | `OPENAI_API_KEY`, and `AGENT_MODEL` such as `gpt-4o-mini` |

Notes:

- If both Azure variables are set, Azure is used. Otherwise OpenAI is used.
- `EVALUATOR_MODEL` is optional. Set it to a different model or deployment so the evaluator is truly independent. If empty, it uses `AGENT_MODEL`.
- `ITEMS_PER_SOURCE` controls how many items are fetched per source (default 3). Use 1 for a faster demo.
- Never commit `.env`. It is already in `.gitignore`.

## Part 2: testing (about 5 minutes)

### 2.1 Run the automated tests

```bash
pytest
```

Expected: `76 passed`. These tests use a fake model and canned articles, so they need no key and no network, apart from the notebook test starting a local Jupyter kernel.

What they cover:

| Area | What is checked |
|---|---|
| Config | Azure versus OpenAI selection, defaults, disabled sources |
| Storage | Duplicate URL and fingerprint blocking, status validation |
| Discovery | Feed and page readers, robots.txt, one broken source not stopping the rest |
| Agents | Short articles skip the model, long text is cut at 12,000 characters, one retry on failure, prompt-injection wrapper |
| Validation and evaluator | Required fields, dead links, dates, evaluator verdicts |
| Pipeline | Each article type ends in the right status, reruns create no duplicates, failures go to review |
| Review and blog | Approve and reject rules, source link and attribution on every post, unsafe HTML and links removed |
| Notebook | `demo.ipynb` runs top to bottom without errors |

### 2.2 Check that the live sources work

```bash
python scripts/check_sources.py
```

Expected: one line per source starting with `ok`, and `0 source(s) failed`. If a source fails, fix its URL or set `enabled: false` for it in `config/sources.yaml`.

## Part 3: offline rehearsal (about 5 minutes)

Do this before any live demo. It needs no key and no network.

### 3.1 Start Jupyter in offline mode

```bash
source .venv/bin/activate
DEMO_MODE=1 FAKE_LLM=1 DB_PATH=data/rehearsal.db jupyter notebook demo.ipynb
```

If Jupyter asks for a kernel, choose **Python 3**. It must be the one from `.venv`.

### 3.2 Run the cells

Run each cell in order with Shift+Enter. Expected results:

| Cell | Expected |
|---|---|
| Setup | `LLM: fake model` and `Articles: canned demo set` |
| Configure | A table of 15 sources |
| Run pipeline | `new: 5`, and a table of 5 articles: 3 `pending_review`, 1 `rejected_non_ai`, 1 `needs_review` |
| Inspect | Relevance evidence, draft, validation errors and evaluator verdict for one article |
| Review queue | 3 drafts with **Approve** and **Reject** buttons, and a "needs attention" table with the empty article |
| Blog | "No published posts yet" until you approve something |

Click **Approve** on one draft. It becomes a published post in the blog cell, with the publisher name, date and a "Read the original" link.

Run the Run pipeline cell a second time. Expected: `new: 0` and `duplicates: 5`. Nothing is duplicated.

### 3.3 Clean up after the rehearsal

Stop Jupyter with Ctrl+C in the terminal, then:

```bash
rm data/rehearsal.db
```

## Part 4: live demo with a real model (about 15 minutes)

### 4.1 Before you present

1. Confirm `.env` has your key (Part 1.3) and run `python scripts/check_sources.py`.
2. Start from a clean database so the demo is fresh:

```bash
rm -f data/signalwire.db
```

3. Set `ITEMS_PER_SOURCE=1` in `.env` for a short first run (15 items). Live runs make about 3 model calls per relevant article, so a full run with 3 per source takes several minutes.
4. Do one full dry run the day before. Real results vary, so don't promise exact counts.

### 4.2 Start the notebook

```bash
source .venv/bin/activate
jupyter notebook demo.ipynb
```

### 4.3 Suggested demo script

Tell the story in this order. Each step maps to one notebook cell.

1. **Setup** (1 min). "This runs on my laptop. The setup cell shows which model provider is active. No keys are printed."
2. **Configure** (1 min). "These are our sources: the frontier labs and the GitHub release feeds for the agent frameworks we watch. Anyone can switch a source off in one config file."
3. **Run pipeline** (3 to 8 min, depending on `ITEMS_PER_SOURCE`). "Code fetches and removes duplicates. Then two agents run: one decides if the article is really about AI, the other writes the post. Code checks the draft. A third, independent agent checks the draft against the original source." While it runs, point out that only three steps use a model; the rest is plain code.
4. **Status table** (2 min). Explain the statuses: `pending_review` passed everything, `rejected_non_ai` was filtered out, `needs_review` was uncertain or invalid.
5. **Inspect** (2 min). The cell shows the first draft by default. In a new cell, run `show(<id>)` with an `id` from the status table to look at one `pending_review` item and one `needs_review` item. Show the relevance evidence, the draft, and the evaluator's reason. Then show a rejected item to prove non-AI articles are blocked.
6. **Review queue** (2 min). "A human always approves before anything publishes." Click **Approve** on a good draft and **Reject** on another.
7. **Blog** (1 min). Show the published post with attribution and a link to the original. "Every post carries the source link, the publisher and the original date."
8. **Rerun** (1 min). Run the Run pipeline cell again. "Nothing is duplicated. Only new articles are processed."

### 4.4 Reset between demos

Run the last cell after removing the `#` in front of `db.reset()`, or stop Jupyter and run:

```bash
rm -f data/signalwire.db
```

## Troubleshooting

| Problem | Fix |
|---|---|
| `pip install` fails with a certificate or reset error | See Part 1.2: VPN, internal mirror, or `--index-url https://pypi.org/simple` |
| `ModuleNotFoundError` in the notebook | Jupyter is using the wrong Python. Start it from the activated `.venv`, and pick the **Python 3** kernel from it |
| Setup cell says `openai` but you meant Azure | Both `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_API_KEY` must be set in `.env` |
| Azure error about a model or deployment | `AGENT_MODEL` must be your Azure **deployment name**, not the model family name |
| `AuthenticationError` or 401 | The key in `.env` is wrong or expired. Fix it and restart the kernel, because `.env` is read when the Setup cell runs |
| Run pipeline reports `source_errors` | One source is down or blocked. The others still ran. Rerun later, or set `enabled: false` for it in `config/sources.yaml` |
| Almost everything lands in `needs_review` | Some sites block automatic page fetching and feeds give only short summaries. Read the reason in the Inspect cell. Items with a very short body are sent to review on purpose |
| Buttons in the review cell do nothing | Run `pip install ipywidgets`, restart the kernel, and run the cells again. In some viewers, such as VS Code, widgets need the Jupyter extension |
| Nothing new appears after a second run | Expected. Already stored articles are skipped. Reset the database for a fresh run |

## Known limits to mention honestly

- There is no daily scheduler yet. A notebook cell starts each run.
- The demo has not been run end to end against a real key by the build; do your own dry run first.
- Pages that block bots, or feeds with short summaries, produce thin drafts or go to review.
- Some review edge cases are deferred, such as rejecting an already published post.
