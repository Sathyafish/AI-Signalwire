# AI Signalwire

An automated AI news publishing pipeline that discovers recent posts from leading AI organizations, turns them into concise, source-linked briefings, and publishes approved articles to a blog.

## What it does

AI Signalwire monitors official news and research channels from organizations such as Google, OpenAI, and Anthropic. An agent workflow collects new items, checks and summarizes them, and sends publication-ready drafts to the blog frontend.

The project is designed to make AI news easier to follow while keeping every summary traceable to its original source.

## Initial workflow

1. **Discover** — Check configured official feeds and pages for new articles. Prefer RSS feeds, sitemaps, or documented APIs where available; use respectful, rate-limited page fetching when needed.
2. **Normalize** — Extract title, publisher, URL, publication date, and article text into a common format.
3. **Deduplicate** — Compare canonical URLs and content fingerprints so the same story is not processed twice.
4. **Classify** — Tag articles by topic, such as models, research, products, policy, safety, and infrastructure.
5. **Summarize** — Create an original, concise summary grounded in the source, with links and attribution. Do not reproduce full source articles.
6. **Review** — Validate dates, claims, source links, and summary quality. Send drafts for editorial review before publication by default.
7. **Publish** — Upload approved posts through the blog's publishing API or content management system.
8. **Track** — Record processing status, errors, and published post URLs so each item can be audited and retried safely.

## Proposed architecture

- **Scheduler** starts periodic collection runs.
- **Source adapters** retrieve content from each configured publisher.
- **Processing agents** normalize, deduplicate, classify, summarize, and validate articles.
- **Review queue** holds drafts that need approval or correction.
- **Publisher adapter** sends approved posts to the blog frontend or CMS.
- **Database** stores source items, summaries, review state, and publication records.

Keep each stage independently retryable. A failed upload should not cause the article to be collected or summarized again, and repeated runs should not create duplicate posts.

## Suggested MVP stack

These are starting points and can be swapped to fit the existing frontend:

- **Language:** Python or TypeScript
- **Workflow:** a job queue or a durable workflow runner
- **Storage:** PostgreSQL for article and job state
- **Content retrieval:** RSS/Atom first, then source-specific adapters
- **Blog integration:** a small publisher interface backed by the chosen CMS or frontend API
- **Deployment:** scheduled container or worker service

## Repository layout

```text
.
├── README.md
├── config/
│   └── sources.yaml          # Publisher names, feed URLs, polling settings
├── src/
│   ├── discovery/             # Feed and page adapters
│   ├── pipeline/              # Normalize, deduplicate, classify, summarize
│   ├── review/                # Draft status and editorial actions
│   ├── publishing/            # Blog/CMS integration
│   └── storage/               # Persistence and migrations
└── tests/
```

## Getting started

Implementation setup will be added with the first working pipeline. Before running it, configure:

- The official source feeds or pages to monitor
- Database connection details
- Model provider and credentials for summarization, if used
- Blog/CMS endpoint and credentials
- Polling interval and editorial review settings

Keep credentials in environment variables or a secrets manager. Never commit API keys or publishing tokens.

## Article record

Each discovered article should retain at least:

- `source_name`
- `source_url` and canonical URL
- `title`
- `published_at` and `discovered_at`
- `content_hash`
- `topics`
- `summary` and source attribution
- `status` (for example: discovered, processed, needs_review, approved, published, failed)
- `published_url`, when available

## Editorial and reliability principles

- Use official publisher sources as the source of record.
- Preserve the source URL and publication date on every post.
- Clearly distinguish source facts from generated commentary.
- Do not invent details when the source is unclear; flag uncertainty for review.
- Respect publisher terms, robots guidance, rate limits, and copyright. Prefer feeds and APIs over scraping where available.
- Start with human approval before publishing; enable automatic publication only after quality checks and operating rules are established.
- Log enough information to explain what was published and which source material informed it.

## Initial milestones

1. Add a source registry and collect items from one official feed.
2. Store normalized items and prevent duplicates.
3. Generate a short, attributed draft and validate its source link.
4. Add a review queue.
5. Publish an approved draft to a test blog endpoint.
6. Add more sources, monitoring, retries, and operational alerts.

## Project status

**Stage:** Initial project definition. The source list, frontend/CMS, workflow runner, and deployment target are still to be selected.
