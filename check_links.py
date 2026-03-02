"""
Carrigtwohill Research Repository — Link Health Checker

Checks every article URL and classifies its status:
  ok               — 200-299, source reachable
  access_restricted — 401/403, needs login or subscription
  unavailable       — 404/410/5xx/timeout/DNS failure

Run:  python check_links.py          (unchecked only)
      python check_links.py --all    (re-check everything)
"""

import sys
import time
import argparse
from datetime import datetime
from collections import defaultdict
from urllib.parse import urlparse
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
import db

# ── Config ──────────────────────────────────────────────────────────────────

TIMEOUT = 15  # seconds per request
DOMAIN_DELAY = 3  # seconds between requests to same domain
RETRY_DELAY = 5  # seconds before retrying a 5xx

HEADERS = {
    "User-Agent": (
        "CarrigtwohillHistoricalResearch/1.0 "
        "(Educational & genealogical research; contact: duinneacha@gmail.com)"
    ),
    "Accept-Language": "en-IE,en;q=0.9",
}


# ── Classification ──────────────────────────────────────────────────────────

def classify(status_code):
    """Map an HTTP status code to a link_status value."""
    if 200 <= status_code <= 299:
        return "ok"
    if status_code in (401, 403):
        return "access_restricted"
    # 404, 410, and everything else we can't handle
    return "unavailable"


def check_url(url):
    """
    Check a single URL. Returns (status_label, http_code_or_error).
    Uses HEAD first, falls back to GET if HEAD returns 405.
    """
    try:
        resp = requests.head(url, headers=HEADERS, timeout=TIMEOUT,
                             allow_redirects=True)
        if resp.status_code == 405:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT,
                                allow_redirects=True, stream=True)
            resp.close()

        code = resp.status_code

        # Retry once on server errors
        if 500 <= code <= 599:
            time.sleep(RETRY_DELAY)
            resp = requests.head(url, headers=HEADERS, timeout=TIMEOUT,
                                 allow_redirects=True)
            if resp.status_code == 405:
                resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT,
                                    allow_redirects=True, stream=True)
                resp.close()
            code = resp.status_code

        return classify(code), code

    except requests.exceptions.Timeout:
        return "unavailable", "timeout"
    except requests.exceptions.ConnectionError:
        return "unavailable", "connection_error"
    except requests.exceptions.TooManyRedirects:
        return "unavailable", "too_many_redirects"
    except Exception as e:
        return "unavailable", str(e)[:60]


# ── Main ────────────────────────────────────────────────────────────────────

def run(check_all=False):
    db.init_db()
    conn = db.get_conn()

    if check_all:
        rows = conn.execute(
            "SELECT id, url FROM articles WHERE url != '' ORDER BY id"
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, url FROM articles WHERE url != '' AND link_status = 'unchecked' ORDER BY id"
        ).fetchall()

    articles = [(r["id"], r["url"]) for r in rows]
    conn.close()

    total = len(articles)
    if total == 0:
        print("No articles to check.")
        return

    print(f"Checking {total} article URL{'s' if total != 1 else ''}...\n")

    # Group by domain for rate-limiting
    last_hit = defaultdict(float)  # domain -> timestamp of last request
    counts = defaultdict(int)  # status -> count

    for i, (aid, url) in enumerate(articles, 1):
        domain = urlparse(url).netloc

        # Per-domain rate limit
        elapsed = time.time() - last_hit[domain]
        if elapsed < DOMAIN_DELAY:
            time.sleep(DOMAIN_DELAY - elapsed)

        status, code = check_url(url)
        last_hit[domain] = time.time()
        counts[status] += 1

        # Update DB
        now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
        conn = db.get_conn()
        conn.execute(
            "UPDATE articles SET link_status = ?, link_checked_at = ? WHERE id = ?",
            (status, now, aid),
        )
        conn.commit()
        conn.close()

        # Progress
        label_map = {
            "ok": "ok",
            "access_restricted": "access_restricted",
            "unavailable": "unavailable",
        }
        print(f"  [{i}/{total}] {domain[:40]:40s}  {code} -> {label_map[status]}")

    # Summary
    print(f"\n{'=' * 52}")
    print(f"  OK: {counts['ok']}  |  "
          f"Own Access Required: {counts['access_restricted']}  |  "
          f"Unavailable: {counts['unavailable']}")
    print(f"{'=' * 52}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check article link health")
    parser.add_argument("--all", action="store_true",
                        help="Re-check all articles, not just unchecked")
    args = parser.parse_args()
    run(check_all=args.all)
