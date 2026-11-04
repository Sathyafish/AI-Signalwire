# Laptop demo design (Jupyter notebook)

## Goal

A demo of AI Signalwire that runs from a Jupyter notebook on a laptop and shows the full flow in the README: fetch real articles, filter for AI relevance, draft posts, evaluate them independently, take human approval, and publish to a local blog.

## Decisions

- **Interface:** A Jupyter notebook (`demo.ipynb`). Each pipeline stage is a cell the presenter runs and shows results from. There is no web server.
- **LLM provider:** Azure OpenAI or OpenAI, chosen from a `.env` file. If `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_API_KEY` are set, use Azure. Otherwise use `OPENAI_API_KEY`. The evaluator can use a different model or deployment name (`EVALUATOR_MODEL`).
- **Language and frameworks:** Python, LangGraph for the workflow, LangChain for the LLM agents.
- **Storage:** SQLite (file in `data/`), in place of PostgreSQL, so nothing needs installing.
- **Trigger:** Running the "Run pipeline" cell replaces the daily scheduler. The scheduler is out of scope for the demo.
- **Sources:** Two groups, listed in `config/sources.yaml` (see Sources below), with a per-source item limit per run (default 3) to keep demo cost and time low.

## Sources

**Frontier labs (model, tool, framework and protocol announcements):** OpenAI, Google DeepMind, Google AI, Anthropic, Meta AI, Microsoft, AWS ML, NVIDIA, Mistral.

**Framework releases (GitHub, catches framework shifts on release day):** MCP, LangChain, LangGraph, LlamaIndex, CrewAI, OpenAI Agents SDK, plus a watchlist that is easy to extend in the config.

How each is read:

- **GitHub releases:** the `releases.atom` feed of each repository. This is a stable, official feed.
- **Lab blogs with an RSS/Atom feed** (expected: OpenAI, Google DeepMind, Google AI, Microsoft, AWS ML, NVIDIA): read the feed.
- **Lab sites without an official feed** (expected: Anthropic, Meta AI, Mistral): a small per-site page adapter that reads the news index page, with rate limiting and robots.txt respected. These are the most fragile part, so they are marked `adapter: html` in the config and can be switched off individually.
- Feed URLs are checked when building the code; any that don't work are fixed or disabled in the config rather than guessed.
- Each record carries a `source_type` (`lab_post` or `release`). The writer agent uses a release-notes style for releases (version, key changes, link to the release), and the relevance agent still runs on all items, since a release for an unrelated project should not publish.

## Logic lives in modules, not the notebook

The notebook stays short and readable. All logic is in importable modules under `src/`, so it can be tested and later reused by a real service. The notebook only calls them and displays results.

## Pipeline

One LangGraph graph, matching the README workflow:

1. **Fetch and extract** (code): read feeds, fetch article text, normalize into a record.
2. **Deduplicate** (code): canonical URL and content fingerprint against stored items.
3. **Relevance agent** (LLM): label, score, evidence. Unrelated or ambiguous goes to the review queue.
4. **Writer agent** (LLM): summary returned directly as the blog payload.
5. **Validation** (code): required fields, link status, date format, schema. Failures go to the review queue.
6. **Independent evaluator** (LLM): `pass`, `reject_non_ai`, or `needs_review`, with reason and evidence. Anything other than `pass` goes to the review queue.
7. **Human approval** (notebook): approve publishes, reject or revise returns the item to the queue.

Each step persists its result and status, so a rerun skips completed stages and cannot create duplicate posts.

## Notebook layout

1. **Setup:** install check, load `.env`, show which provider is active (no keys printed).
2. **Configure:** show sources and the article limit.
3. **Run pipeline:** run the graph and display a status table (pandas DataFrame) with one row per article.
4. **Inspect:** show one article's relevance evidence, draft, validation result, and evaluator verdict.
5. **Review queue:** passing drafts shown with Approve and Reject buttons (ipywidgets). Items needing investigation are listed separately.
6. **Blog:** published posts rendered as HTML with source link, publisher attribution, and publication date.
7. **Reset:** optional cell that clears the database for a fresh demo.

## Data

One `articles` table holding source and canonical URL, fingerprint, extracted text, relevance result, post payload, validation result, evaluator result, status, attempt count, error, and publication fields. Statuses use the README names.

## Error handling

- Feed or fetch failure: mark the item `failed` with the error and continue with other articles.
- LLM error or malformed structured output: retry once, then `needs_review`.
- Article text is treated as untrusted input; prompts instruct agents to ignore instructions inside it.

## Demo mode

`DEMO_MODE=1` loads a few canned articles (AI and non-AI) so the demo works without network access to the feeds. LLM calls still use the configured provider.

## Testing

- Unit tests: dedupe, validation, routing logic.
- Agent tests with a fake LLM that returns fixed structured outputs.
- One end-to-end test of the graph using the fake LLM and canned articles.
- The notebook is run top to bottom once with `nbconvert` and the fake LLM to confirm every cell executes.

## Layout

Follows the README: `config/sources.yaml`, `src/{discovery,agents,validation,evaluation,review,publishing,storage}`, `demo.ipynb`, `tests/`, `.env.example`, `requirements.txt` (includes `jupyter` and `ipywidgets`). The README gains a "Run the demo" section.

## Out of scope

Daily scheduler, web server, PostgreSQL, real CMS publishing, authentication, automatic publishing.
