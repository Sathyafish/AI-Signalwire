# AI Signalwire laptop demo implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Jupyter notebook demo that fetches AI news and framework releases, filters, drafts, evaluates, takes human approval, and publishes to a local blog.

**Architecture:** Logic lives in importable `src/` modules. A LangGraph graph runs the per-article steps (dedupe, relevance agent, writer agent, validation, evaluator) and routes failures to review states. `demo.ipynb` only calls these modules and displays results. SQLite persists every step.

**Tech Stack:** Python 3.11+, LangGraph, LangChain (`langchain-openai`, `AzureChatOpenAI` or `ChatOpenAI`), pydantic, feedparser, trafilatura, httpx, BeautifulSoup, SQLite, pandas, ipywidgets, Jupyter, pytest.

**Spec:** `docs/superpowers/specs/2026-11-03-laptop-demo-design.md`

## Global Constraints

- LLM provider from `.env`: if `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_API_KEY` are set use Azure, otherwise `OPENAI_API_KEY`. Evaluator model name from `EVALUATOR_MODEL`.
- SQLite file at `data/signalwire.db`. No PostgreSQL, no web server, no scheduler.
- Default limit of 3 items per source per run (`ITEMS_PER_SOURCE`).
- `DEMO_MODE=1` loads canned articles instead of the network. `FAKE_LLM=1` swaps in a fake model that needs no key.
- Statuses: `discovered`, `extracted`, `duplicate`, `rejected_non_ai`, `needs_review`, `summarized`, `formatted`, `evaluation_failed`, `pending_review`, `approved`, `published`, `failed`.
- Article text is untrusted: wrapped in delimiters in every prompt, and prompts tell the model to ignore instructions inside it.
- LLM error or malformed structured output: retry once, then `needs_review`.
- Never print API keys.
- UI copy uses sentence case, with no spaces around dashes or slashes.

## Review Focus

- Article with an empty or very short body: goes to `needs_review`, no crash, no LLM call.
- Article body far over the model limit: truncated to 12,000 characters before any prompt.
- One feed unreachable or malformed: that source is skipped and recorded, other sources still run.
- Running the pipeline twice on the same items: no duplicate rows, drafts, or posts.
- LLM raises or returns malformed output: retried once, then `needs_review` with the error stored.

## File structure

- `src/models.py` — pydantic models and status constants.
- `src/config.py` — settings and source loading.
- `src/llm.py`, `src/fake_llm.py` — model factory and the offline fake.
- `src/storage/db.py` — SQLite access.
- `src/discovery/` — `feeds.py`, `html_adapter.py`, `extract.py`, `dedupe.py`, `demo.py`, `__init__.py` (`discover`).
- `src/agents/relevance.py`, `src/agents/writer.py`, `src/agents/common.py` (shared prompt and retry helper).
- `src/validation/checks.py`, `src/evaluation/evaluator.py`.
- `src/pipeline.py` — LangGraph graph and `run_pipeline`.
- `src/review/queue.py`, `src/publishing/local_blog.py`.
- `config/sources.yaml`, `.env.example`, `requirements.txt`, `scripts/make_notebook.py`, `scripts/check_sources.py`, `demo.ipynb`, `tests/`.

---

### Task 1: Scaffold, models, config, LLM factory

**Files:**
- Create: `requirements.txt`, `.env.example`, `.gitignore`, `config/sources.yaml`, `src/__init__.py` (and `__init__.py` in each `src/` subpackage), `src/models.py`, `src/config.py`, `src/llm.py`, `src/fake_llm.py`, `tests/test_config.py`, `tests/test_fake_llm.py`

**Interfaces:**
- Produces (`src/models.py`):
  - `ArticleRecord(source_name: str, source_type: Literal["lab_post","release"], title: str, canonical_url: str, published_at: str, body: str, fingerprint: str = "")`
  - `Relevance(label: Literal["ai","not_ai","ambiguous"], score: float, evidence: str)`
  - `BlogPost(title, slug, excerpt, body_markdown: str, topics: list[str], source_name, source_url, source_published_at: str, status: str = "pending_review")`
  - `Evaluation(verdict: Literal["pass","reject_non_ai","needs_review"], reason: str, evidence: str)`
  - `STATUSES: tuple[str, ...]` (the list in Global Constraints)
- Produces (`src/config.py`):
  - `Source(name: str, type: str, url: str, adapter: Literal["feed","html"] = "feed", enabled: bool = True)`
  - `Settings(provider: Literal["azure","openai"], agent_model: str, evaluator_model: str, items_per_source: int, demo_mode: bool, fake_llm: bool, db_path: str)`
  - `load_settings(env: Mapping[str,str] | None = None) -> Settings`
  - `load_sources(path: str = "config/sources.yaml") -> list[Source]` (enabled only)
- Produces (`src/llm.py`): `get_llm(settings: Settings, role: Literal["agent","evaluator"]) -> BaseChatModel`
- Produces (`src/fake_llm.py`): `FakeLLM(fail_times: int = 0)`; `.with_structured_output(schema)` returns an object whose `.invoke(messages)` returns a `schema` instance. For `Relevance`: label `ai` if the text contains "AI" or "model" or "LLM" (word match, case-insensitive), else `not_ai`. For `BlogPost`: fills fields from the prompt's title and url. For `Evaluation`: `pass` unless the text contains "NEEDS_REVIEW_MARKER". Raises `RuntimeError` for the first `fail_times` calls.

- [ ] **Step 1: Write failing tests**

`tests/test_config.py`: `test_azure_chosen_when_azure_vars_set`, `test_openai_chosen_otherwise`, `test_evaluator_model_defaults_to_agent_model`, `test_items_per_source_default_is_3`, `test_load_sources_skips_disabled`. `tests/test_fake_llm.py`: `test_relevance_ai_text_is_ai`, `test_relevance_cooking_text_is_not_ai`, `test_fail_times_raises_then_succeeds`.

- [ ] **Step 2: Run `pytest tests/test_config.py tests/test_fake_llm.py -v`; expected: FAIL (modules missing)**

- [ ] **Step 3: Implement the modules above.** `requirements.txt` pins nothing exotic: `langgraph langchain langchain-openai pydantic feedparser trafilatura httpx beautifulsoup4 pyyaml python-dotenv pandas ipywidgets jupyter nbconvert nbformat pytest`. `.gitignore` covers `.env`, `data/`, `__pycache__/`, `.ipynb_checkpoints/`. `.env.example` lists every variable with placeholder values only. `config/sources.yaml` lists these sources (fields `name, type, url, adapter, enabled`):
  - `lab_post`, feed: OpenAI `https://openai.com/news/rss.xml`; Google DeepMind `https://deepmind.google/blog/rss.xml`; Google AI `https://blog.google/technology/ai/rss/`; Microsoft `https://blogs.microsoft.com/ai/feed/`; AWS ML `https://aws.amazon.com/blogs/machine-learning/feed/`; NVIDIA `https://blogs.nvidia.com/feed/`.
  - `lab_post`, html: Anthropic `https://www.anthropic.com/news`; Meta AI `https://ai.meta.com/blog/`; Mistral `https://mistral.ai/news`.
  - `release`, feed (`https://github.com/<repo>/releases.atom`): `modelcontextprotocol/modelcontextprotocol`, `langchain-ai/langchain`, `langchain-ai/langgraph`, `run-llama/llama_index`, `crewAIInc/crewAI`, `openai/openai-agents-python`.

- [ ] **Step 4: Run the same pytest command; expected: PASS**

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: scaffold, models, config, llm factory"
```

---

### Task 2: Storage

**Files:**
- Create: `src/storage/db.py`, `tests/test_db.py`

**Interfaces:**
- Consumes: `ArticleRecord`, `STATUSES` from Task 1.
- Produces: `Database(path: str)` (creates parent dir and table on init; `":memory:"` allowed) with:
  - `add_article(rec: ArticleRecord) -> int | None` — inserts with status `discovered`; returns `None` if the canonical URL or fingerprint already exists.
  - `get(article_id: int) -> dict` — columns plus JSON fields decoded (`relevance`, `post`, `validation`, `evaluation` are dict/list or `None`).
  - `update(article_id: int, **fields) -> None` — dict/list/pydantic values stored as JSON; `status` must be in `STATUSES` else `ValueError`.
  - `list_articles(status: str | None = None) -> list[dict]`
  - `exists(canonical_url: str, fingerprint: str) -> bool`
  - `reset() -> None`

- [ ] **Step 1: Write failing tests**: `test_add_article_returns_id`, `test_duplicate_url_returns_none`, `test_duplicate_fingerprint_returns_none`, `test_update_status_validates`, `test_update_json_roundtrip`, `test_list_filters_by_status`, `test_reset_empties_table`.
- [ ] **Step 2: Run `pytest tests/test_db.py -v`; expected: FAIL**
- [ ] **Step 3: Implement `Database`** with one `articles` table (columns: id, source_name, source_type, title, canonical_url unique, published_at, body, fingerprint unique, status, relevance, post, validation, evaluation, attempts, error, post_url, published_time).
- [ ] **Step 4: Run again; expected: PASS**
- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: sqlite storage"`

---

### Task 3: Discovery, extraction, dedupe helpers, demo data

**Files:**
- Create: `src/discovery/feeds.py`, `src/discovery/html_adapter.py`, `src/discovery/extract.py`, `src/discovery/dedupe.py`, `src/discovery/demo.py`, `src/discovery/__init__.py`, `scripts/check_sources.py`, `tests/test_discovery.py`, `tests/fixtures/sample_feed.xml`, `tests/fixtures/sample_news_index.html`

**Interfaces:**
- Consumes: `ArticleRecord`, `Source`, `Settings`.
- Produces:
  - `canonicalize(url: str) -> str` (lowercase host, drop fragment and `utm_*` params, strip trailing slash) and `fingerprint(text: str) -> str` (sha256 of whitespace-normalized lowercase text) in `dedupe.py`.
  - `extract_text(url: str, client: httpx.Client | None = None) -> str` in `extract.py` (trafilatura; returns `""` on failure).
  - `fetch_feed_items(source: Source, limit: int, parse=feedparser.parse) -> list[ArticleRecord]` — uses the entry's content or summary as body for releases; for lab posts uses `extract_text` when the feed body is shorter than 500 characters. Raises nothing: a malformed feed returns `[]`.
  - `fetch_html_items(source: Source, limit: int, client: httpx.Client | None = None) -> list[ArticleRecord]` — reads the index page, collects up to `limit` same-site article links, extracts each. Checks `robots.txt` first and sleeps 1 second between requests.
  - `canned_items() -> list[ArticleRecord]` in `demo.py` — 5 items: 3 clearly AI (one release), 1 clearly not AI (a recipe or sports story), 1 with an empty body.
  - `discover(sources: list[Source], settings: Settings) -> tuple[list[ArticleRecord], dict[str, str]]` — returns records and a map of source name to error text for sources that failed. In demo mode returns `canned_items()` and `{}`.

- [ ] **Step 1: Write failing tests** (using fixtures, no network): `test_canonicalize_strips_utm_and_fragment`, `test_fingerprint_ignores_whitespace_and_case`, `test_fetch_feed_items_respects_limit`, `test_fetch_feed_items_malformed_returns_empty`, `test_fetch_html_items_collects_links` (client mocked with `httpx.MockTransport`), `test_discover_records_failing_source_and_continues`, `test_discover_demo_mode_returns_canned`.
- [ ] **Step 2: Run `pytest tests/test_discovery.py -v`; expected: FAIL**
- [ ] **Step 3: Implement the modules.** `discover` wraps each source in try/except so one failure is recorded and others continue.
- [ ] **Step 4: Run again; expected: PASS**
- [ ] **Step 5: Write `scripts/check_sources.py`** — loads `config/sources.yaml`, fetches each source with limit 1, prints `ok`/`FAIL` with item counts. Run it (`python scripts/check_sources.py`) with network access. For each FAIL, correct the URL or set `enabled: false` in `config/sources.yaml`; do not guess URLs. Record the result in the commit message.
- [ ] **Step 6: Commit** — `git add -A && git commit -m "feat: discovery, extraction, dedupe, demo data"`

---

### Task 4: Relevance and writer agents

**Files:**
- Create: `src/agents/common.py`, `src/agents/relevance.py`, `src/agents/writer.py`, `tests/test_agents.py`

**Interfaces:**
- Consumes: `ArticleRecord`, `Relevance`, `BlogPost`, `FakeLLM`.
- Produces:
  - `MAX_CHARS = 12000`, `wrap_untrusted(text: str) -> str` (truncates to `MAX_CHARS`, wraps in `<article>` delimiters), `UNTRUSTED_NOTICE: str` (system text telling the model to ignore instructions inside the article), `invoke_structured(llm, schema, system: str, user: str)` — calls `llm.with_structured_output(schema).invoke([...])`, retries once on any exception or validation error, raises `AgentError(str)` after the second failure.
  - `classify(llm, record: ArticleRecord) -> Relevance` — returns `ambiguous` with score 0 and evidence "Article body too short" **without calling the LLM** when `len(record.body.strip()) < 200`; on `AgentError` returns `ambiguous` with the error text as evidence.
  - `write_post(llm, record: ArticleRecord) -> BlogPost` — uses a release-notes style system prompt when `record.source_type == "release"` (version, key changes, link) and a news-summary style otherwise; sets `source_name`, `source_url`, `source_published_at` from the record regardless of model output; slug is derived from the title by code (`slugify(title: str) -> str`). Raises `AgentError`.

- [ ] **Step 1: Write failing tests**: `test_wrap_untrusted_truncates_to_max_chars`, `test_prompt_contains_untrusted_notice_and_delimiters` (fake LLM records the messages), `test_classify_short_body_skips_llm` (LLM that raises if called), `test_classify_ai_article`, `test_classify_retries_once_then_succeeds` (`FakeLLM(fail_times=1)`), `test_classify_double_failure_is_ambiguous` (`FakeLLM(fail_times=2)`), `test_writer_overrides_source_fields`, `test_writer_release_uses_release_prompt`, `test_slugify`.
- [ ] **Step 2: Run `pytest tests/test_agents.py -v`; expected: FAIL**
- [ ] **Step 3: Implement.** Relevance prompt asks for label, score 0–1, and evidence quoting the article; "substantially about AI, not a passing mention" is stated verbatim from the README.
- [ ] **Step 4: Run again; expected: PASS**
- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: relevance and writer agents"`

---

### Task 5: Validation and evaluator

**Files:**
- Create: `src/validation/checks.py`, `src/evaluation/evaluator.py`, `tests/test_validation.py`, `tests/test_evaluator.py`

**Interfaces:**
- Consumes: `BlogPost`, `Relevance`, `ArticleRecord`, `invoke_structured`, `wrap_untrusted`, `AgentError`.
- Produces:
  - `validate_post(post: BlogPost, check_links: bool = True, client: httpx.Client | None = None) -> list[str]` — returns error strings, empty if valid. Checks: non-empty title, slug (lowercase, hyphens only), excerpt, body, `source_name`; `source_url` starts with http(s) and, when `check_links`, responds with status below 400 (HEAD, falling back to GET); `source_published_at` parses as ISO 8601 or RFC 2822; at least one topic.
  - `evaluate(llm, record: ArticleRecord, relevance: Relevance, post: BlogPost) -> Evaluation` — prompt contains the source text (wrapped), the relevance label and evidence, and the draft, and asks the four README questions. Any `AgentError` returns `needs_review` with the error as reason.

- [ ] **Step 1: Write failing tests**: `test_valid_post_has_no_errors`, `test_missing_source_url_flagged`, `test_bad_slug_flagged`, `test_bad_date_flagged`, `test_dead_link_flagged` (MockTransport 404), `test_check_links_false_skips_network`, `test_evaluate_pass`, `test_evaluate_marker_needs_review`, `test_evaluate_llm_failure_is_needs_review`, `test_evaluator_prompt_includes_four_questions`.
- [ ] **Step 2: Run both test files; expected: FAIL**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run again; expected: PASS**
- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: validation and independent evaluator"`

---

### Task 6: LangGraph pipeline

**Files:**
- Create: `src/pipeline.py`, `tests/test_pipeline.py`

**Interfaces:**
- Consumes: everything above.
- Produces:
  - `build_graph(db: Database, llm, eval_llm, check_links: bool = True)` — compiled LangGraph over a `TypedDict` state `{article_id: int}`. Nodes: `relevance`, `writer`, `validation`, `evaluator`, with conditional edges. Each node reads its inputs from the DB and writes results and status back, so a rerun resumes from the stored status. Routing:
    - relevance `ai` → writer; `not_ai` → status `rejected_non_ai`, end; `ambiguous` → `needs_review`, end.
    - writer success → status `formatted`, then validation; `AgentError` → `needs_review`.
    - validation errors → `needs_review` with errors stored; none → evaluator.
    - evaluator `pass` → `pending_review`; `reject_non_ai` → `rejected_non_ai`; `needs_review` → `needs_review`.
    - Any unexpected exception → status `failed` with error text, attempts incremented.
  - `run_pipeline(db: Database, settings: Settings, sources: list[Source], llm, eval_llm, check_links: bool = True) -> dict` — calls `discover`, adds each record (duplicates are skipped and counted), runs the graph for each new article and any article in a resumable status (`discovered`, `formatted`), and returns `{"new": int, "duplicates": int, "source_errors": dict[str,str], "article_ids": list[int]}`. Discovery runs before the graph because it produces the batch the graph processes.

- [ ] **Step 1: Write failing tests** (FakeLLM, `DEMO_MODE`, `check_links=False`): `test_demo_run_routes_each_canned_item` (AI items end `pending_review`, non-AI `rejected_non_ai`, empty body `needs_review`), `test_rerun_creates_no_duplicates` (second run: `new == 0`, same row count), `test_writer_failure_goes_to_needs_review`, `test_validation_failure_goes_to_needs_review`, `test_evaluator_needs_review_routes`, `test_unexpected_exception_marks_failed_and_continues`, `test_source_errors_reported`.
- [ ] **Step 2: Run `pytest tests/test_pipeline.py -v`; expected: FAIL**
- [ ] **Step 3: Implement** with `langgraph.graph.StateGraph`.
- [ ] **Step 4: Run again; expected: PASS**
- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: langgraph pipeline"`

---

### Task 7: Review queue and local blog

**Files:**
- Create: `src/review/queue.py`, `src/publishing/local_blog.py`, `tests/test_review_publish.py`

**Interfaces:**
- Consumes: `Database`.
- Produces:
  - `pending_review(db) -> list[dict]` (status `pending_review`); `needs_attention(db) -> list[dict]` (status `needs_review`, `evaluation_failed`, `failed`).
  - `approve(db, article_id: int) -> None` — only valid from `pending_review` (else `ValueError`); sets `approved` then calls `publish`.
  - `reject(db, article_id: int, reason: str = "") -> None` — sets `needs_review` with the reason stored in `error`.
  - `publish(db, article_id: int) -> str` — sets status `published`, `published_time` (UTC ISO), `post_url` `local://blog/<slug>`; returns the URL. Idempotent: publishing an already published article returns the stored URL and changes nothing.
  - `render_blog_html(db) -> str` — HTML for all published posts: title, body (markdown converted to HTML), "Source: <publisher>" with a link to `source_url`, and the source publication date. All text is HTML-escaped.

- [ ] **Step 1: Write failing tests**: `test_approve_publishes_pending_item`, `test_approve_rejects_wrong_status`, `test_reject_moves_to_needs_review`, `test_publish_is_idempotent`, `test_blog_html_has_source_link_and_attribution`, `test_blog_html_escapes_markup_in_title`.
- [ ] **Step 2: Run `pytest tests/test_review_publish.py -v`; expected: FAIL**
- [ ] **Step 3: Implement** (use the `markdown` package; add it to `requirements.txt`).
- [ ] **Step 4: Run again; expected: PASS**
- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: review queue and local blog"`

---

### Task 8: Notebook, README, end-to-end test

**Files:**
- Create: `scripts/make_notebook.py`, `demo.ipynb` (generated), `tests/test_notebook.py`
- Modify: `README.md` (add "Run the demo" section; update repo layout to match the real tree)

**Interfaces:**
- Consumes: `load_settings`, `load_sources`, `get_llm`, `Database`, `run_pipeline`, `pending_review`, `needs_attention`, `approve`, `reject`, `render_blog_html`.
- Produces: `demo.ipynb` with these cells in order: Setup (load `.env` via `python-dotenv`, print provider name only); Configure (show enabled sources and `items_per_source`); Run pipeline (call `run_pipeline`, show a pandas DataFrame of id, source, title, status, plus any `source_errors`); Inspect (a function `show(article_id)` displaying relevance evidence, draft, validation errors, evaluator verdict); Review queue (for each pending item an ipywidgets row with Approve and Reject buttons wired to `approve`/`reject`; the needs-attention list below it); Blog (`IPython.display.HTML(render_blog_html(db))`); Reset (commented-out `db.reset()` cell). Cell text uses sentence case.

- [ ] **Step 1: Write failing test** `tests/test_notebook.py::test_notebook_runs_top_to_bottom` — sets `DEMO_MODE=1`, `FAKE_LLM=1`, a temporary `DB_PATH`, runs `nbconvert --execute` (via `nbclient`) on `demo.ipynb`, asserts no cell errors.
- [ ] **Step 2: Run `pytest tests/test_notebook.py -v`; expected: FAIL (notebook missing)**
- [ ] **Step 3: Write `scripts/make_notebook.py`** using `nbformat` to produce `demo.ipynb`; run `python scripts/make_notebook.py`.
- [ ] **Step 4: Run `pytest -v`; expected: all tests PASS**
- [ ] **Step 5: Update `README.md`** with: install (`pip install -r requirements.txt`), `.env` setup from `.env.example`, `jupyter notebook demo.ipynb`, an offline rehearsal using `DEMO_MODE=1 FAKE_LLM=1`, and a note that `check_sources.py` verifies feeds.
- [ ] **Step 6: Commit** — `git add -A && git commit -m "feat: demo notebook and docs"`

---

## Self-review notes

- Spec coverage: sources and adapters (Task 3), pipeline steps (Tasks 4–6), review and blog (Task 7), notebook layout, demo mode, fake-LLM notebook test (Tasks 1, 8), error handling (Tasks 4, 6), testing list (all tasks).
- Spec deviation to confirm: discovery runs before the graph (the graph handles each fetched article), not as a graph node. Behavior is the same.
- Live LLM calls and live feeds are not covered by automated tests; they are checked manually with a real `.env` and `scripts/check_sources.py`.
