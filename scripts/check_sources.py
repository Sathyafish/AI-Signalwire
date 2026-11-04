"""Check each configured source. Run from the repo root: python scripts/check_sources.py"""
import sys

sys.path.insert(0, ".")

from src.config import load_sources  # noqa: E402
from src.discovery.feeds import fetch_feed_items  # noqa: E402
from src.discovery.html_adapter import fetch_html_items  # noqa: E402

failed = 0
for s in load_sources():
    try:
        items = (fetch_html_items if s.adapter == "html" else fetch_feed_items)(s, 1)
        ok = bool(items) and bool(items[0].body.strip())
        print(f"{'ok  ' if ok else 'FAIL'} {s.name}: {len(items)} item(s) {s.url}")
        failed += 0 if ok else 1
    except Exception as exc:
        print(f"FAIL {s.name}: {type(exc).__name__}: {exc} {s.url}")
        failed += 1
print(f"{failed} source(s) failed. Fix the URL or set enabled: false in config/sources.yaml.")
