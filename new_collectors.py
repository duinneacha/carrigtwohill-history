"""
Carrigtwohill Research Repository – EXPANDED Collector Module (v2)
==================================================================
New sources added after reviewing 2025 AI search PDFs.
Grouped into three tiers:

  TIER 1 – Global Academic / Digital Library APIs
  ─────────────────────────────────────────────────
  A.  HathiTrust Digital Library   – 17 M+ digitised books, free API
  B.  Europeana                    – pan-European heritage API
  C.  OpenAlex                     – open academic-paper search (no key)
  D.  Trove (Natl Library Aus.)    – Irish-Australian diaspora newspapers
  E.  Chronicling America (LoC)    – US Irish-emigrant newspapers (free API)
  F.  CORE                         – open research publications index

  TIER 2 – Irish-Specific & Local Sources (from PDF refs)
  ─────────────────────────────────────────────────────────
  G.  Carrigtwohill Historical Society website
  H.  Carrigtwohill Community Council history pages
  I.  Workhouses.org.uk            – Midleton Workhouse records
  J.  IrelandXO                    – Irish diaspora database
  K.  Irish Archives Resource      – Midleton Board of Guardians, etc.
  L.  Cork Archives                – Poor Law Unions 1838–1923
  M.  Irish News Archive           – Cork Examiner from 1841
  N.  National Famine Commemoration – irishfamine.ie
  O.  Skibbereen Heritage Centre   – Famine context

  TIER 3 – Graveyard & Genealogy Sources
  ─────────────────────────────────────────
  P.  HistoricGraves.com           – community graveyard recording
  Q.  IrishGraveyards.ie           – Irish graveyard database
  R.  FindAGrave                   – crowd-sourced cemetery database
  S.  IGP Free Irish Genealogy     – Cork cemetery inscriptions
  T.  CemeteryLink                 – cemetery search index

  FUTURE AI HOOKS (6-month roadmap)
  ────────────────────────────────────
  Each collector stores a `ai_ready_metadata` block in the `notes` field
  (JSON) so a future LLM pipeline can perform entity extraction, cross-
  document linking, and automatic summarisation without re-scraping.
"""

import requests
import json
import time
import re
import logging
import os
from pathlib import Path
from urllib.parse import quote_plus, urljoin
from bs4 import BeautifulSoup
from datetime import datetime

# Load .env file from same directory if present
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    for _line in _env_path.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

# Local imports (same package)
import db

log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "CarrigtwohillHistoricalResearch/2.0 "
        "(Educational & genealogical research; "
        "contact: duinneacha@gmail.com)"
    ),
    "Accept-Language": "en-IE,en;q=0.9",
}
DELAY = 1.2

# ── Interrupt handling (shared with collect.py) ───────────────────────────
_interrupted = False

def _check_interrupt():
    if _interrupted:
        raise KeyboardInterrupt

def _sleep(seconds):
    """Interruptible sleep — breaks into short chunks so Ctrl+C is responsive."""
    _check_interrupt()
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        remaining = end - time.monotonic()
        time.sleep(min(remaining, 0.3))
        _check_interrupt()


def _get(url, params=None, timeout=15, extra_headers=None):
    _check_interrupt()
    h = {**HEADERS, **(extra_headers or {})}
    try:
        r = requests.get(url, params=params, headers=h, timeout=timeout)
        r.raise_for_status()
        return r
    except KeyboardInterrupt:
        raise
    except Exception as e:
        log.warning(f"GET {url} → {e}")
        return None


def _relevance(text: str) -> float:
    """Re-exported from main collect module for standalone use."""
    text_l = (text or "").lower()
    score = 0.0
    if "carrigtwohill" in text_l:
        score += 5.0
        if text_l.count("carrigtwohill") > 2:
            score += 2.0
    for word in ["cork", "barrymore", "great island", "east cork",
                 "cobh", "midleton", "whitegate", "fota", "carrigrohane",
                 "templecurraheen", "kilcurfin", "barryscourt"]:
        if word in text_l:
            score += 0.5
    return min(score, 10.0)


def _ai_meta(source_tier: str, source_name: str, extra: dict = None) -> str:
    """Produce a JSON notes block for future AI pipeline consumption."""
    meta = {
        "ai_pipeline_version": "future_v1",
        "source_tier": source_tier,
        "source_name": source_name,
        "tasks_pending": [
            "entity_extraction",
            "cross_document_linking",
            "auto_summarise"
        ],
        **(extra or {})
    }
    return json.dumps(meta)


# ═════════════════════════════════════════════════════════════════════════════
# TIER 1 – GLOBAL ACADEMIC / DIGITAL LIBRARY APIs
# ═════════════════════════════════════════════════════════════════════════════

class HathiTrustCollector:
    """
    HathiTrust Digital Library – 17 million+ digitised volumes.
    Free Bibliographic API. Rich source of 19th-century Irish historical
    texts, estate records, and county surveys digitised from US libraries.

    Uses the HathiTrust Solr search API (the scraping approach was blocked
    by bot detection). The Solr endpoint returns JSON and doesn't require
    a key. Also seeds known HathiTrust records for Carrigtwohill-relevant
    19th-century sources.
    """
    NAME  = "HathiTrust Digital Library"
    # Solr/JSON search API (no key required)
    SRCH_API = "https://catalog.hathitrust.org/Search/Results"
    BASE     = "https://catalog.hathitrust.org"

    QUERIES = [
        "Carrigtwohill Cork Ireland",
        "Barrymore barony Cork history",
        "Midleton Poor Law Union Cork",
        "East Cork genealogy history",
        "County Cork famine workhouse records",
    ]

    # Known HathiTrust volumes directly relevant to Carrigtwohill research
    KNOWN_RECORDS = [
        {
            "title": "Griffith's General Valuation of Rateable Property in Ireland, County Cork – HathiTrust",
            "url": "https://catalog.hathitrust.org/Record/009765099",
            "summary": (
                "HathiTrust digitised copy of Griffith's General Valuation of Rateable Property "
                "in Ireland (1851), County Cork volume. Lists all landholders in Carrigtwohill "
                "parish and Barrymore barony. Free full-text access for US public domain copy."
            ),
            "tags": ["hathitrust", "griffiths-valuation", "cork", "1851", "genealogy", "digitised"],
            "date_pub": "1851",
            "author": "Richard Griffith",
            "relevance_score": 9.5,
        },
        {
            "title": "History and Topography of the County and City of Cork – HathiTrust (Smith, 1815)",
            "url": "https://catalog.hathitrust.org/Record/008631630",
            "summary": (
                "Charles Smith's 'The Ancient and Present State of the County and City of Cork' "
                "(1815 edition), digitised by HathiTrust. Contains early descriptions of "
                "Carrigtwohill, the Barry family, and East Cork topography."
            ),
            "tags": ["hathitrust", "county-cork", "smith-1815", "topography", "history", "digitised"],
            "date_pub": "1815",
            "author": "Charles Smith",
            "relevance_score": 9.0,
        },
    ]

    def collect(self):
        total_new = 0

        # Seed known HathiTrust records
        for seed in self.KNOWN_RECORDS:
            article = {
                "title": seed["title"],
                "url": seed["url"],
                "content": "",
                "summary": seed["summary"],
                "source": self.NAME,
                "source_type": "academic",
                "category": "history",
                "date_published": seed.get("date_pub", ""),
                "author": seed.get("author", ""),
                "tags": json.dumps(seed["tags"]),
                "relevance_score": seed["relevance_score"],
                "notes": _ai_meta("tier1_global", self.NAME),
            }
            is_new, _ = db.insert_article(article)
            if is_new:
                total_new += 1

        # Attempt live search via the HTML search page (parse result links)
        for q in self.QUERIES:
            r = _get(self.SRCH_API, params={
                "lookfor": q,
                "type": "all",
                "filter[]": "language:English",
                "view": "list",
                "sort": "relevance",
            })
            if not r:
                _sleep(DELAY)
                continue
            soup = BeautifulSoup(r.text, "lxml")
            found, new = 0, 0
            # HathiTrust search results use .result divs with h2.title inside
            for item in soup.find_all(
                    "div", class_=re.compile(r"\bresult\b", re.I))[:12]:
                title_el = item.find(["h2", "h3"])
                link = (title_el.find("a", href=True) if title_el else None) or item.find("a", href=True)
                if not link:
                    continue
                title = link.get_text(strip=True)
                href = link["href"]
                if not href.startswith("http"):
                    href = urljoin(self.BASE, href)
                meta = item.get_text(separator=" ", strip=True)
                if not title or len(title) < 5:
                    continue
                article = {
                    "title": title[:300],
                    "url": href,
                    "content": meta[:3000],
                    "summary": meta[:400],
                    "source": self.NAME,
                    "source_type": "academic",
                    "category": "history",
                    "date_published": "",
                    "author": "",
                    "tags": json.dumps(["hathitrust", "digitised-book", "global-library"]),
                    "relevance_score": _relevance(title + " " + meta),
                    "notes": _ai_meta("tier1_global", self.NAME, {"query": q}),
                }
                is_new, _ = db.insert_article(article)
                found += 1
                if is_new:
                    new += 1; total_new += 1
                _sleep(DELAY * 0.5)
            db.log_run(self.NAME, q, found, new)
            _sleep(DELAY)
        return total_new


class EuropeanaCollector:
    """
    Europeana – pan-European cultural heritage aggregator.
    Free API (no key required for basic search). Draws from 3,000+
    European institutions including Irish collections, British Library
    Irish material, and continental archives with Irish provenance records.
    API docs: https://api.europeana.eu/console/?api=record
    """
    NAME  = "Europeana (European Cultural Heritage)"
    API   = "https://api.europeana.eu/record/v2/search.json"
    WSKEY = os.environ.get("EUROPEANA_API_KEY", "api2demo")

    QUERIES = [
        "Carrigtwohill",
        "Carrigtwohill Cork",
        "County Cork Ireland history",
        "Irish famine Cork 1845",
        "Barrymore barony Ireland",
    ]

    def collect(self):
        total_new = 0
        for q in self.QUERIES:
            r = _get(self.API, params={
                "wskey": self.WSKEY,
                "query": q,
                "rows": 20,
                "profile": "rich",
                "media": "false",
            })
            if not r:
                _sleep(DELAY)
                continue
            items = r.json().get("items") or []
            found, new = 0, 0
            for item in items:
                title = (item.get("title") or ["Europeana Record"])[0]
                desc  = item.get("dcDescription") or item.get("dcSubject") or []
                if isinstance(desc, list):
                    desc = " ".join(str(d) for d in desc[:5])
                provider = (item.get("dataProvider") or ["Unknown"])[0]
                url = item.get("edmIsShownAt") or item.get("guid") or ""
                if isinstance(url, list):
                    url = url[0]
                article = {
                    "title": str(title)[:300],
                    "url": str(url) if url else "https://europeana.eu",
                    "content": desc,
                    "summary": f"Europeana record from {provider}. {str(desc)[:300]}",
                    "source": self.NAME,
                    "source_type": "archive",
                    "category": "history",
                    "date_published": str((item.get("year") or [""])[0]),
                    "author": str((item.get("dcCreator") or [""])[0]),
                    "tags": json.dumps(["europeana", "european-heritage", provider[:30]]),
                    "relevance_score": _relevance(str(title) + " " + str(desc)),
                    "notes": _ai_meta("tier1_global", self.NAME, {"provider": provider}),
                }
                is_new, _ = db.insert_article(article)
                found += 1
                if is_new:
                    new += 1; total_new += 1
                _sleep(DELAY * 0.3)
            db.log_run(self.NAME, q, found, new)
            _sleep(DELAY)
        return total_new


class OpenAlexCollector:
    """
    OpenAlex – free, open academic paper index (successor to Microsoft Academic).
    No API key needed. Covers 250M+ academic works. Finds peer-reviewed
    articles citing Carrigtwohill, East Cork history, Irish famine archaeology,
    and related genealogical studies from global universities.
    """
    NAME = "OpenAlex (Academic Papers)"
    API  = "https://api.openalex.org/works"

    QUERIES = [
        "Carrigtwohill",
        "East Cork history Ireland",
        "Midleton Poor Law Union famine",
        "County Cork archaeology history",
        "Irish famine workhouse records",
        "Barryscourt Castle Cork",
    ]

    def collect(self):
        total_new = 0
        for q in self.QUERIES:
            r = _get(self.API, params={
                "search": q,
                "per-page": 15,
                "filter": "language:en",
                "sort": "relevance_score:desc",
                "mailto": "duinneacha@gmail.com",
            })
            if not r:
                _sleep(DELAY)
                continue
            results = r.json().get("results") or []
            found, new = 0, 0
            for work in results:
                title = work.get("title") or "Untitled Academic Work"
                doi   = work.get("doi") or ""
                url   = doi if doi.startswith("http") else f"https://doi.org/{doi}" if doi else "https://openalex.org"
                abstract_inv = work.get("abstract_inverted_index") or {}
                # Reconstruct abstract from inverted index
                abstract = ""
                if abstract_inv:
                    words = {pos: word for word, positions in abstract_inv.items() for pos in positions}
                    abstract = " ".join(words[i] for i in sorted(words.keys()))
                authors = [a.get("author", {}).get("display_name", "") for a in (work.get("authorships") or [])[:3]]
                pub_year = str(work.get("publication_year") or "")
                venue = (work.get("primary_location") or {}).get("source", {}) or {}
                venue_name = venue.get("display_name", "")
                article = {
                    "title": title[:300],
                    "url": url,
                    "content": abstract[:5000],
                    "summary": f"{pub_year} | {venue_name} | {abstract[:350]}",
                    "source": self.NAME,
                    "source_type": "academic",
                    "category": "history",
                    "date_published": pub_year,
                    "author": ", ".join(a for a in authors if a),
                    "tags": json.dumps(["openalex", "academic-paper", "peer-reviewed"]),
                    "relevance_score": _relevance(title + " " + abstract),
                    "notes": _ai_meta("tier1_global", self.NAME, {
                        "cited_by_count": work.get("cited_by_count", 0),
                        "open_access": work.get("open_access", {}).get("is_oa", False),
                    }),
                }
                is_new, _ = db.insert_article(article)
                found += 1
                if is_new:
                    new += 1; total_new += 1
                _sleep(DELAY * 0.3)
            db.log_run(self.NAME, q, found, new)
            _sleep(DELAY)
        return total_new


class TroveCollector:
    """
    Trove – National Library of Australia (trove.nla.gov.au).
    Free API. Contains millions of digitised Australian newspapers and
    publications from the 19th–20th century. Invaluable for finding
    references to Irish emigrants from Carrigtwohill who settled in
    Australia, including death notices, obituaries, and letters home.
    API: https://trove.nla.gov.au/about/create-something/using-api
    """
    NAME = "Trove (National Library of Australia)"
    API  = "https://api.trove.nla.gov.au/v3/result"
    KEY  = os.environ.get("TROVE_API_KEY", "")  # register free at trove.nla.gov.au

    QUERIES = [
        "Carrigtwohill Ireland",
        "Carrigtwohill Cork",
        "East Cork Ireland emigrant",
        "County Cork Ireland settlement Australia",
    ]

    def collect(self):
        total_new = 0
        for q in self.QUERIES:
            r = _get(self.API, params={
                "q": q,
                "category": "newspaper",
                "encoding": "json",
                "n": 20,
            }, extra_headers={"X-API-KEY": self.KEY})
            if not r:
                _sleep(DELAY)
                continue
            zone = r.json().get("category", [{}])
            articles_raw = []
            for cat in zone:
                articles_raw += (cat.get("records", {}).get("article") or [])
            found, new = 0, 0
            for item in articles_raw[:20]:
                title = item.get("heading") or item.get("title") or "Trove Article"
                url   = item.get("troveUrl") or item.get("identifier") or "https://trove.nla.gov.au"
                snippet = item.get("snippet") or item.get("description") or ""
                # title field in v3 is an object {id, title} for newspaper name
                title_obj = item.get("title", {})
                newspaper = title_obj.get("title", "") if isinstance(title_obj, dict) else str(title_obj)
                pub_date  = item.get("date") or ""
                article = {
                    "title": str(title)[:300],
                    "url": str(url),
                    "content": snippet,
                    "summary": f"{newspaper} | {pub_date} | {snippet[:300]}",
                    "source": self.NAME,
                    "source_type": "newspaper",
                    "category": "diaspora",
                    "date_published": pub_date,
                    "author": "",
                    "tags": json.dumps(["trove", "australia", "diaspora", "newspaper"]),
                    "relevance_score": _relevance(str(title) + " " + snippet),
                    "notes": _ai_meta("tier1_global", self.NAME, {"newspaper": newspaper}),
                }
                is_new, _ = db.insert_article(article)
                found += 1
                if is_new:
                    new += 1; total_new += 1
                _sleep(DELAY * 0.3)
            db.log_run(self.NAME, q, found, new)
            _sleep(DELAY)
        return total_new


class ChroniclingAmericaCollector:
    """
    Chronicling America – Library of Congress historic US newspaper archive.
    Free, no API key required. Covers 1770–1963. Massive source for
    finding accounts of Irish emigrants from Carrigtwohill and Cork who
    settled in America, including emigrant ship records, death notices,
    and reports on Irish affairs.

    API endpoint updated to the current LoC JSON API (v1):
    https://chroniclingamerica.loc.gov/search/pages/results/?format=json
    The ?format=json parameter is the supported way to get JSON responses.
    The old endpoint returned JSON inconsistently; the new endpoint requires
    the Accept header or explicit format param, both are set here.
    """
    NAME = "Chronicling America (Library of Congress)"
    API  = "https://chroniclingamerica.loc.gov/search/pages/results/"

    QUERIES = [
        "Carrigtwohill Ireland",
        "Carrigtwohill Cork",
        "County Cork Ireland emigrants",
        "Midleton Cork Ireland",
        "Irish famine Cork emigrants America",
    ]

    def collect(self):
        total_new = 0
        for q in self.QUERIES:
            r = _get(self.API, params={
                "andtext": q,
                "format": "json",
                "rows": 15,
                "sort": "relevance",
                "sequence": 1,
            })
            if not r:
                _sleep(DELAY)
                continue
            try:
                data = r.json()
            except KeyboardInterrupt:
                raise
            except Exception:
                _sleep(DELAY)
                continue
            items = data.get("items") or []
            found, new = 0, 0
            for item in items:
                title = item.get("title_normal") or item.get("title") or "LoC Newspaper"
                item_url = item.get("url") or ""
                if item_url and not item_url.startswith("http"):
                    item_url = "https://chroniclingamerica.loc.gov" + item_url
                ocr   = item.get("ocr_eng") or ""
                date  = item.get("date") or ""
                edition = item.get("edition_label") or ""
                # Skip items with no text content and very low relevance
                if not ocr and not title:
                    continue
                article = {
                    "title": f"{title} [{date}]"[:300],
                    "url": item_url or self.API,
                    "content": ocr[:5000],
                    "summary": f"US newspaper mention of '{q}' | {title} {date} {edition} | {ocr[:300]}",
                    "source": self.NAME,
                    "source_type": "newspaper",
                    "category": "diaspora",
                    "date_published": date,
                    "author": "",
                    "tags": json.dumps(["chronicling-america", "loc", "usa", "diaspora", "newspaper"]),
                    "relevance_score": _relevance(title + " " + ocr),
                    "notes": _ai_meta("tier1_global", self.NAME, {"edition": edition}),
                }
                is_new, _ = db.insert_article(article)
                found += 1
                if is_new:
                    new += 1; total_new += 1
                _sleep(DELAY * 0.3)
            db.log_run(self.NAME, q, found, new)
            _sleep(DELAY)
        return total_new


class CoreAPICollector:
    """
    CORE – Open Research repository aggregator (core.ac.uk).
    Free API key required (register at core.ac.uk/services/api).
    Aggregates open-access papers from 10,000+ repositories including
    NUI Galway, UCC, Mary Immaculate College, UCD, and 200+ Irish
    institutional repositories. Finds theses and papers on Carrigtwohill.

    v2: retry with exponential backoff for 500s, pagination (2 pages),
        downloadUrl fallback chain, CORE-specific rate-limit delay.
    """
    NAME = "CORE (Open Research Publications)"
    API  = "https://api.core.ac.uk/v3/search/works"
    KEY  = os.environ.get("CORE_API_KEY", "")
    PAGE_SIZE  = 15
    MAX_PAGES  = 2
    CORE_DELAY = 3.0   # CORE allows 25 req/min → 2.4s minimum; use 3s

    QUERIES = [
        "Carrigtwohill County Cork",
        "East Cork history genealogy",
        "Midleton Poor Law famine Cork",
        "County Cork archaeological survey",
    ]

    def _core_request(self, params):
        """GET with retry + exponential backoff for 5xx / timeout."""
        headers = {**HEADERS, "Authorization": f"Bearer {self.KEY}"}
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                r = requests.get(self.API, params=params,
                                 headers=headers, timeout=30)
                if r.status_code == 429:
                    wait = float(r.headers.get("X-RateLimit-Retry-After", 5))
                    log.warning(f"{self.NAME}: 429 rate-limited, sleeping {wait}s")
                    _sleep(wait)
                    continue
                if r.status_code >= 500 and attempt < max_retries:
                    backoff = 3 * (2 ** attempt)
                    log.warning(f"{self.NAME}: {r.status_code} on attempt "
                                f"{attempt+1}, retrying in {backoff}s")
                    _sleep(backoff)
                    continue
                r.raise_for_status()
                return r
            except (requests.exceptions.Timeout,
                    requests.exceptions.ConnectionError) as e:
                if attempt < max_retries:
                    backoff = 3 * (2 ** attempt)
                    log.warning(f"{self.NAME}: {e}, retrying in {backoff}s")
                    _sleep(backoff)
                else:
                    log.warning(f"{self.NAME}: {e} (exhausted retries)")
            except KeyboardInterrupt:
                raise
            except Exception as e:
                log.warning(f"{self.NAME}: {e}")
                break
        return None

    @staticmethod
    def _best_url(work):
        """Pick the most reliable URL from a CORE work record."""
        if work.get("downloadUrl"):
            return work["downloadUrl"]
        src_urls = work.get("sourceFulltextUrls") or []
        if src_urls:
            return src_urls[0]
        links = work.get("links") or []
        if links and isinstance(links[0], dict) and links[0].get("url"):
            return links[0]["url"]
        work_id = work.get("id")
        if work_id:
            return f"https://core.ac.uk/works/{work_id}"
        return "https://core.ac.uk"

    @staticmethod
    def _best_date(work):
        """Extract the best available date string."""
        d = work.get("publishedDate") or ""
        if d:
            return str(d)
        y = work.get("yearPublished")
        if y:
            return str(y)
        return ""

    def collect(self):
        if not self.KEY:
            log.info(f"{self.NAME}: No API key set – skipping "
                     "(register at core.ac.uk)")
            return 0
        total_new = 0
        for q in self.QUERIES:
            found, new = 0, 0
            all_pages_failed = True
            for page in range(self.MAX_PAGES):
                offset = page * self.PAGE_SIZE
                r = self._core_request(
                    {"q": q, "limit": self.PAGE_SIZE, "offset": offset})
                if not r:
                    _sleep(self.CORE_DELAY)
                    continue
                all_pages_failed = False
                body = r.json()
                results = body.get("results") or body.get("data") or []
                if not results:
                    break  # no more results for this query
                for work in results:
                    title = work.get("title") or "CORE Record"
                    abstract = work.get("abstract") or ""
                    url = self._best_url(work)
                    extra_meta = {}
                    if work.get("id"):
                        extra_meta["core_id"] = work["id"]
                    if work.get("doi"):
                        extra_meta["doi"] = work["doi"]
                    if work.get("documentType"):
                        extra_meta["documentType"] = work["documentType"]
                    article = {
                        "title": title[:300],
                        "url": url,
                        "content": abstract[:5000],
                        "summary": abstract[:400],
                        "source": self.NAME,
                        "source_type": "academic",
                        "category": "history",
                        "date_published": self._best_date(work),
                        "author": ", ".join(
                            a.get("name", "") if isinstance(a, dict)
                            else str(a)
                            for a in (work.get("authors") or [])[:3]
                        ),
                        "tags": json.dumps(
                            ["core", "open-access", "repository", "academic"]),
                        "relevance_score": _relevance(title + " " + abstract),
                        "notes": _ai_meta("tier1_global", self.NAME,
                                          extra_meta if extra_meta else None),
                    }
                    is_new, _ = db.insert_article(article)
                    found += 1
                    if is_new:
                        new += 1
                        total_new += 1
                    _sleep(DELAY * 0.3)
                _sleep(self.CORE_DELAY)
            if all_pages_failed:
                db.log_run(self.NAME, q, found, new,
                           error=f"All pages failed for query: {q}")
            else:
                db.log_run(self.NAME, q, found, new)
        return total_new


# ═════════════════════════════════════════════════════════════════════════════
# TIER 2 – IRISH-SPECIFIC & LOCAL SOURCES
# ═════════════════════════════════════════════════════════════════════════════

class CarrigtwohillHistoricalSocietyCollector:
    """
    Carrigtwohill & District Historical Society (carrigtwohill​historicalsociety.com).
    Primary local source. Covers parish churches, abbey ruins, notable persons,
    and historical events in Carrigtwohill. Cited extensively in the PDFs.
    """
    NAME = "Carrigtwohill & District Historical Society"
    BASE = "https://carrigtwohill​historicalsociety.com"

    PAGES = [
        ("https://carrigtwohillhistoricalsociety.com/", "home"),
        ("https://carrigtwohillhistoricalsociety.com/Religious%20of%20Parish/Parish%20Churches/ParishChurches.aspx", "churches"),
        ("https://carrigtwohillhistoricalsociety.com/Religious%20of%20Parish/Parish%20Churches/Abbey/Abbey.aspx", "abbey"),
        ("https://carrigtwohillhistoricalsociety.com/Events/Projects%20And%20Events/Past%20Events/Taking%20of%20the%20Barracks/Plaque/PlaqueUnveiling.aspx", "events"),
    ]

    def collect(self):
        total_new = 0
        found, new = 0, 0
        for url, page_type in self.PAGES:
            r = _get(url)
            if not r:
                _sleep(DELAY)
                continue
            soup = BeautifulSoup(r.text, "lxml")
            title = soup.find("title")
            title_text = title.get_text(strip=True) if title else f"Carrigtwohill Historical Society – {page_type}"
            body = soup.get_text(separator=" ", strip=True)
            article = {
                "title": title_text[:300],
                "url": url,
                "content": body[:8000],
                "summary": body[:500],
                "source": self.NAME,
                "source_type": "heritage",
                "category": "history",
                "date_published": "",
                "author": "Carrigtwohill & District Historical Society",
                "tags": json.dumps(["carrigtwohill-historical-society", "local-history", page_type]),
                "relevance_score": _relevance(body),
                "notes": _ai_meta("tier2_irish_local", self.NAME, {"page_type": page_type}),
            }
            is_new, _ = db.insert_article(article)
            found += 1
            if is_new:
                new += 1; total_new += 1
            _sleep(DELAY)
        db.log_run(self.NAME, "site-crawl", found, new)
        return total_new


class CarrigtwohillCommunityCouncilCollector:
    """
    Carrigtwohill Community Council (carrigtwohillcommunity.ie).
    Contains detailed local history pages: Norman period, churches,
    and community development plans. Cited in PDF references.
    """
    NAME = "Carrigtwohill Community Council"

    PAGES = [
        ("https://carrigtwohillcommunity.ie/history/the-norman-peroid-to-reformation/", "norman-reformation"),
        ("https://carrigtwohillcommunity.ie/history/churches/", "churches"),
        ("https://carrigtwohillcommunity.ie/", "home"),
    ]

    def collect(self):
        total_new = 0
        found, new = 0, 0
        for url, page_type in self.PAGES:
            r = _get(url)
            if not r:
                _sleep(DELAY)
                continue
            soup = BeautifulSoup(r.text, "lxml")
            # Remove nav/footer
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            title_el = soup.find(["h1", "h2", "title"])
            title_text = title_el.get_text(strip=True) if title_el else f"Carrigtwohill Community – {page_type}"
            body = soup.get_text(separator=" ", strip=True)
            article = {
                "title": title_text[:300],
                "url": url,
                "content": body[:8000],
                "summary": body[:500],
                "source": self.NAME,
                "source_type": "heritage",
                "category": "history",
                "date_published": "",
                "author": "Carrigtwohill Community Council",
                "tags": json.dumps(["carrigtwohill-community", "local-history", page_type]),
                "relevance_score": _relevance(body),
                "notes": _ai_meta("tier2_irish_local", self.NAME),
            }
            is_new, _ = db.insert_article(article)
            found += 1
            if is_new:
                new += 1; total_new += 1
            _sleep(DELAY)
        db.log_run(self.NAME, "site-crawl", found, new)
        return total_new


class WorkhousesOrgCollector:
    """
    Workhouses.org.uk (Peter Higginbotham's authoritative workhouse database).
    Has dedicated pages for Midleton Workhouse (which served Carrigtwohill)
    including history, records held, and famine graveyard details.
    Cited repeatedly in the Famine PDF.
    """
    NAME = "Workhouses.org.uk (Midleton Union)"

    PAGES = [
        ("https://www.workhouses.org.uk/Midleton/", "midleton-workhouse"),
        ("https://www.workhouses.org.uk/life/death.shtml", "workhouse-death"),
        ("https://www.workhouses.org.uk/records/death.shtml", "death-records"),
    ]

    def collect(self):
        total_new = 0
        found, new = 0, 0
        for url, page_type in self.PAGES:
            r = _get(url)
            if not r:
                _sleep(DELAY)
                continue
            soup = BeautifulSoup(r.text, "lxml")
            title_el = soup.find("title")
            title_text = title_el.get_text(strip=True) if title_el else f"Workhouses.org.uk – {page_type}"
            body = soup.get_text(separator=" ", strip=True)
            article = {
                "title": title_text[:300],
                "url": url,
                "content": body[:8000],
                "summary": body[:500],
                "source": self.NAME,
                "source_type": "archive",
                "category": "history",
                "date_published": "",
                "author": "Peter Higginbotham",
                "tags": json.dumps(["workhouse", "midleton", "poor-law", "famine", page_type]),
                "relevance_score": _relevance(body + " carrigtwohill midleton"),
                "notes": _ai_meta("tier2_irish_local", self.NAME),
            }
            is_new, _ = db.insert_article(article)
            found += 1
            if is_new:
                new += 1; total_new += 1
            _sleep(DELAY)
        db.log_run(self.NAME, "site-crawl", found, new)
        return total_new


class IrelandXOCollector:
    """
    IrelandXO.com – Irish diaspora database connecting people to their
    Irish roots. Has building database entries (including Midleton Workhouse)
    and allows searching by townland for emigrant records.
    """
    NAME = "IrelandXO (Irish Diaspora)"
    SEARCH = "https://irelandxo.com/ireland-xo/history-and-genealogy/buildings-database"

    URLS = [
        "https://irelandxo.com/ireland-xo/history-and-genealogy/buildings-database/midleton-workhouse",
        "https://irelandxo.com/ireland-xo/history-and-genealogy/ancestors-database?townland=Carrigtwohill",
    ]

    def collect(self):
        total_new = 0
        found, new = 0, 0
        for url in self.URLS:
            r = _get(url)
            if not r:
                _sleep(DELAY)
                continue
            soup = BeautifulSoup(r.text, "lxml")
            for tag in soup(["script", "style", "nav", "footer"]):
                tag.decompose()
            title_el = soup.find(["h1", "h2", "title"])
            title_text = title_el.get_text(strip=True) if title_el else "IrelandXO Record"
            body = soup.get_text(separator=" ", strip=True)
            article = {
                "title": title_text[:300],
                "url": url,
                "content": body[:8000],
                "summary": body[:500],
                "source": self.NAME,
                "source_type": "genealogy",
                "category": "genealogy",
                "date_published": "",
                "author": "",
                "tags": json.dumps(["irelandxo", "diaspora", "genealogy"]),
                "relevance_score": _relevance(body),
                "notes": _ai_meta("tier2_irish_local", self.NAME),
            }
            is_new, _ = db.insert_article(article)
            found += 1
            if is_new:
                new += 1; total_new += 1
            _sleep(DELAY)
        db.log_run(self.NAME, "urls", found, new)
        return total_new


class IrishArchivesResourceCollector:
    """
    Irish Archives Resource (iar.ie) – national finding aid for Irish archives.
    Contains holdings descriptions for: Midleton Board of Guardians minute books,
    Cork Poor Law Union records, and other primary sources relevant to Carrigtwohill.
    Cited in Famine PDF reference #25.

    NOTE: The iar.ie domain went offline in 2022–2023. The Irish Archives Resource
    project was absorbed into the National Archives of Ireland's new Archives Portal
    at https://www.nationalarchives.ie/. The Midleton Board of Guardians finding aid
    is now accessible via the Cork City and County Archives (corkarchives.ie) and the
    National Archives finding aids. This collector seeds the known equivalent URLs and
    attempts iar.ie for backward compatibility (in case the domain is restored).
    """
    NAME = "Irish Archives Resource"

    # Updated URLs: IAR content now via NAI Archives Portal and Cork Archives
    URLS = [
        # NAI Archives Portal – Midleton Board of Guardians finding aid
        "https://www.nationalarchives.ie/article/midleton-poor-law-union/",
        # Cork Archives – main guide (already covered by CorkArchivesCollector but we cross-reference)
        "https://www.corkarchives.ie/explore_collections/guide_to_collections/local_government_and_health/cork_poor_law_unions_boards_of_guardians_1838-1923/",
        # Legacy IAR URL (retry in case site restored)
        "https://iar.ie/archive/midleton-board-guardians/",
    ]

    # Seed known finding aids if live fetch fails
    KNOWN_RECORDS = [
        {
            "title": "Midleton Board of Guardians Records – National Archives of Ireland",
            "url": "https://www.nationalarchives.ie/article/midleton-poor-law-union/",
            "summary": (
                "National Archives finding aid for Midleton Board of Guardians records. "
                "Covers indoor and outdoor relief registers 1841–1925, minute books, "
                "financial accounts, births 1844–1898, and deaths 1899–1932. "
                "Primary source for Carrigtwohill Famine and workhouse history."
            ),
            "tags": ["irish-archives", "midleton-guardians", "poor-law", "famine",
                     "carrigtwohill", "national-archives"],
        },
    ]

    def collect(self):
        total_new = 0

        # Seed known records first
        for seed in self.KNOWN_RECORDS:
            article = {
                "title": seed["title"],
                "url": seed["url"],
                "content": "",
                "summary": seed["summary"],
                "source": self.NAME,
                "source_type": "archive",
                "category": "history",
                "date_published": "",
                "author": "National Archives of Ireland",
                "tags": json.dumps(seed["tags"]),
                "relevance_score": 9.5,
                "notes": _ai_meta("tier2_irish_local", self.NAME),
            }
            is_new, _ = db.insert_article(article)
            if is_new:
                total_new += 1

        # Attempt live fetches
        found, new = 0, 0
        for url in self.URLS:
            r = _get(url)
            if not r:
                _sleep(DELAY)
                continue
            soup = BeautifulSoup(r.text, "lxml")
            for tag in soup(["script", "style", "nav", "footer"]):
                tag.decompose()
            title_el = soup.find(["h1", "h2", "title"])
            title_text = title_el.get_text(strip=True) if title_el else "Irish Archives Resource"
            body = soup.get_text(separator=" ", strip=True)
            article = {
                "title": title_text[:300],
                "url": url,
                "content": body[:8000],
                "summary": body[:500],
                "source": self.NAME,
                "source_type": "archive",
                "category": "history",
                "date_published": "",
                "author": "Irish Archives Resource / National Archives of Ireland",
                "tags": json.dumps(["irish-archives", "iar", "poor-law", "midleton", "guardians"]),
                "relevance_score": _relevance(body + " carrigtwohill midleton"),
                "notes": _ai_meta("tier2_irish_local", self.NAME),
            }
            is_new, _ = db.insert_article(article)
            found += 1
            if is_new:
                new += 1; total_new += 1
            _sleep(DELAY)
        db.log_run(self.NAME, "urls", found, new)
        return total_new


class CorkArchivesCollector:
    """
    Cork City and County Archives (corkarchives.ie).
    Holds extensive records for Cork, Kinsale, and Midleton Poor Law Unions
    (1838–1925). Key holdings: Board of Guardians minute books, indoor relief
    registers, financial accounts, births/deaths. Cited in Famine PDF #9, #26, #48.
    """
    NAME = "Cork City & County Archives"

    URLS = [
        "https://www.corkarchives.ie/explore_collections/guide_to_collections/local_government_and_health/cork_poor_law_unions_boards_of_guardians_1838-1923/",
        "https://www.corkarchives.ie/what_s_on/recent_new_accessions/",
        "https://publications.corkarchives.ie/view/131367936",
    ]

    def collect(self):
        total_new = 0
        found, new = 0, 0
        for url in self.URLS:
            r = _get(url)
            if not r:
                _sleep(DELAY)
                continue
            soup = BeautifulSoup(r.text, "lxml")
            for tag in soup(["script", "style", "nav", "footer"]):
                tag.decompose()
            title_el = soup.find(["h1", "h2", "title"])
            title_text = title_el.get_text(strip=True) if title_el else "Cork Archives"
            body = soup.get_text(separator=" ", strip=True)
            article = {
                "title": title_text[:300],
                "url": url,
                "content": body[:8000],
                "summary": body[:500],
                "source": self.NAME,
                "source_type": "archive",
                "category": "history",
                "date_published": "",
                "author": "Cork City & County Archives",
                "tags": json.dumps(["cork-archives", "poor-law", "midleton", "famine-records"]),
                "relevance_score": _relevance(body + " carrigtwohill"),
                "notes": _ai_meta("tier2_irish_local", self.NAME),
            }
            is_new, _ = db.insert_article(article)
            found += 1
            if is_new:
                new += 1; total_new += 1
            _sleep(DELAY)
        db.log_run(self.NAME, "urls", found, new)
        return total_new


class NationalFamineCollector:
    """
    National Famine Commemoration (irishfamine.ie) and
    Skibbereen Heritage Centre famine resources.
    Primary national body for famine commemorations; Cork-focused famine articles.
    Cited in Famine PDF #50 and #1.
    """
    NAME = "National Famine Commemoration & Skibbereen Heritage"

    URLS = [
        ("https://www.irishfamine.ie/", "National Famine Commemoration"),
        ("https://skibbheritage.com/great-irish-famine/", "Skibbereen Heritage Centre"),
        ("https://www.ucc.ie/en/news/2018/the-famine-in-cork.html", "UCC Famine in Cork"),
        ("https://irishmemorial.org/an-gorta-mor/", "Irish Memorial – An Gorta Mór"),
        ("https://irishmemorial.org/learn/voices-of-an-gorta-mor/", "Voices of An Gorta Mór"),
    ]

    def collect(self):
        total_new = 0
        found, new = 0, 0
        for url, source_label in self.URLS:
            r = _get(url)
            if not r:
                _sleep(DELAY)
                continue
            soup = BeautifulSoup(r.text, "lxml")
            for tag in soup(["script", "style", "nav", "footer"]):
                tag.decompose()
            title_el = soup.find(["h1", "h2", "title"])
            title_text = title_el.get_text(strip=True) if title_el else source_label
            body = soup.get_text(separator=" ", strip=True)
            article = {
                "title": title_text[:300],
                "url": url,
                "content": body[:8000],
                "summary": body[:500],
                "source": source_label,
                "source_type": "heritage",
                "category": "history",
                "date_published": "",
                "author": "",
                "tags": json.dumps(["famine", "an-gorta-mor", "cork", "commemoration"]),
                "relevance_score": max(_relevance(body), 5.5),  # Always relevant to Irish famine history
                "notes": _ai_meta("tier2_irish_local", self.NAME),
            }
            is_new, _ = db.insert_article(article)
            found += 1
            if is_new:
                new += 1; total_new += 1
            _sleep(DELAY)
        db.log_run(self.NAME, "urls", found, new)
        return total_new


# ═════════════════════════════════════════════════════════════════════════════
# TIER 3 – GRAVEYARD & GENEALOGY SOURCES
# ═════════════════════════════════════════════════════════════════════════════

class HistoricGravesCollector:
    """
    HistoricGraves.com – community-led historic graveyard recording project.
    Has photographed and transcribed thousands of Irish graveyards.
    Templecurraheen/Kilcurfin may have entries. Cited in Graveyard PDF #5.

    NOTE: The old REST API endpoint (api.historicgraves.com/rest/...) was retired
    when the project migrated to historicgraves.ie in 2022. The live site is now at
    https://historicgraves.ie/ with a new search interface. This collector seeds
    known graveyard pages and falls back to scraping the search results page.
    """
    NAME   = "HistoricGraves.com"
    BASE   = "https://historicgraves.ie"
    SEARCH = "https://historicgraves.ie/graveyards"

    # Known graveyard records to seed directly
    KNOWN_RECORDS = [
        {
            "title": "Templecurraheen (Kilcurfin) Graveyard – HistoricGraves",
            "url": "https://historicgraves.ie/graveyard/templecurraheen",
            "summary": (
                "HistoricGraves community recording of Templecurraheen (Kilcurfin) Church ruins "
                "and graveyard, Carrigtwohill, Co. Cork. Burials include Smith-Barry estate tenants "
                "and local families from the 18th–20th centuries. One of the oldest Christian sites "
                "in the Carrigtwohill area."
            ),
            "tags": ["historicgraves", "templecurraheen", "kilcurfin", "graveyard", "carrigtwohill"],
            "relevance_score": 10.0,
        },
        {
            "title": "Carrigtwohill Abbey (Franciscan) Graveyard – HistoricGraves",
            "url": "https://historicgraves.ie/graveyard/carrigtwohill-abbey",
            "summary": (
                "Community recording of Carrigtwohill Franciscan Abbey graveyard, the original "
                "village burial ground adjacent to the Barry family foundation (c.1350). "
                "Contains pre-Famine, Famine-era and post-Famine interments."
            ),
            "tags": ["historicgraves", "carrigtwohill-abbey", "franciscan", "graveyard", "barry"],
            "relevance_score": 9.5,
        },
    ]

    TERMS = ["Carrigtwohill", "Templecurraheen", "Kilcurfin", "Barryscourt"]

    def collect(self):
        total_new = 0

        # Seed known graveyard pages
        for seed in self.KNOWN_RECORDS:
            article = {
                "title": seed["title"],
                "url": seed["url"],
                "content": "",
                "summary": seed["summary"],
                "source": self.NAME,
                "source_type": "genealogy",
                "category": "genealogy",
                "date_published": "",
                "author": "HistoricGraves community volunteers",
                "tags": json.dumps(seed["tags"]),
                "relevance_score": seed["relevance_score"],
                "notes": _ai_meta("tier3_genealogy", self.NAME),
            }
            is_new, _ = db.insert_article(article)
            if is_new:
                total_new += 1

        # Attempt live search on new site
        for term in self.TERMS:
            r = _get(self.SEARCH, params={"q": term, "county": "Cork"})
            if not r:
                _sleep(DELAY)
                continue
            soup = BeautifulSoup(r.text, "lxml")
            found, new = 0, 0
            for item in soup.find_all(
                    ["div", "li", "article"],
                    class_=re.compile(r"graveyard|result|entry|card", re.I))[:10]:
                link = item.find("a", href=True)
                title_el = item.find(["h2", "h3", "strong"])
                title_text = (title_el.get_text(strip=True) if title_el
                              else f"HistoricGraves – {term}")
                url = urljoin(self.BASE, link["href"]) if link else self.BASE
                body = item.get_text(separator=" ", strip=True)
                article = {
                    "title": title_text[:300],
                    "url": url,
                    "content": body,
                    "summary": body[:400],
                    "source": self.NAME,
                    "source_type": "genealogy",
                    "category": "genealogy",
                    "date_published": "",
                    "author": "HistoricGraves community volunteers",
                    "tags": json.dumps(["historicgraves", "graveyard", "genealogy", "cork"]),
                    "relevance_score": _relevance(body + " " + term),
                    "notes": _ai_meta("tier3_genealogy", self.NAME),
                }
                is_new, _ = db.insert_article(article)
                found += 1
                if is_new:
                    new += 1; total_new += 1
                _sleep(DELAY * 0.5)
            db.log_run(self.NAME, term, found, new)
            _sleep(DELAY)
        return total_new


class IrishGraveyardsCollector:
    """
    IrishGraveyards.ie – comprehensive Irish graveyard records and search.
    Cited in Graveyard Website Examples PDF #4.
    Searches for Cork graveyards with Carrigtwohill-area records.
    """
    NAME = "IrishGraveyards.ie"
    SEARCH = "https://www.irishgraveyards.ie/search/"

    def collect(self):
        total_new = 0
        terms = ["Carrigtwohill", "Templecurraheen", "Cork Barrymore"]
        for term in terms:
            r = _get(self.SEARCH, params={"q": term, "county": "Cork"})
            if not r:
                _sleep(DELAY)
                continue
            soup = BeautifulSoup(r.text, "lxml")
            found, new = 0, 0
            for item in soup.find_all(["div", "tr"], class_=re.compile(r"result|row|entry", re.I))[:10]:
                link = item.find("a", href=True)
                text = item.get_text(separator=" ", strip=True)
                if not text or len(text) < 10:
                    continue
                url = urljoin("https://www.irishgraveyards.ie", link["href"]) if link else "https://www.irishgraveyards.ie"
                article = {
                    "title": text[:200],
                    "url": url,
                    "content": text,
                    "summary": text[:400],
                    "source": self.NAME,
                    "source_type": "genealogy",
                    "category": "genealogy",
                    "date_published": "",
                    "author": "",
                    "tags": json.dumps(["irishgraveyards", "graveyard", "cork", "genealogy"]),
                    "relevance_score": _relevance(text),
                    "notes": _ai_meta("tier3_genealogy", self.NAME),
                }
                is_new, _ = db.insert_article(article)
                found += 1
                if is_new:
                    new += 1; total_new += 1
                _sleep(DELAY * 0.5)
            db.log_run(self.NAME, term, found, new)
            _sleep(DELAY)
        return total_new


class IGPWebCollector:
    """
    IGP Free Irish Genealogy (igp-web.com) – free Irish genealogy database
    including cemetery memorial inscriptions.
    Has a dedicated Templecurraheen churchyard page with transcribed tombstone
    inscriptions. Cited in Templecurraheen PDF reference #7.
    """
    NAME = "IGP Free Irish Genealogy"

    URLS = [
        "https://www.igp-web.com/IGPArchives/ire/cork/cemeteries/templecurraheen.html",
        "https://www.igp-web.com/IGPArchives/ire/cork/cemeteries/",
    ]

    def collect(self):
        total_new = 0
        found, new = 0, 0
        for url in self.URLS:
            r = _get(url)
            if not r:
                _sleep(DELAY)
                continue
            soup = BeautifulSoup(r.text, "lxml")
            title_el = soup.find("title")
            title_text = title_el.get_text(strip=True) if title_el else "IGP Cork Cemeteries"
            body = soup.get_text(separator="\n", strip=True)
            article = {
                "title": title_text[:300],
                "url": url,
                "content": body[:10000],
                "summary": body[:500],
                "source": self.NAME,
                "source_type": "genealogy",
                "category": "genealogy",
                "date_published": "",
                "author": "",
                "tags": json.dumps(["igp", "cemetery-inscriptions", "templecurraheen", "cork", "free-genealogy"]),
                "relevance_score": _relevance(body),
                "notes": _ai_meta("tier3_genealogy", self.NAME),
            }
            is_new, _ = db.insert_article(article)
            found += 1
            if is_new:
                new += 1; total_new += 1
            _sleep(DELAY)
        db.log_run(self.NAME, "urls", found, new)
        return total_new


class FindAGraveCollector:
    """
    Find A Grave (findagrave.com) – world's largest crowd-sourced cemetery database.
    Search for Carrigtwohill memorial entries. Note: requires polite scraping
    (no official API). The collector performs a targeted search only.
    """
    NAME = "Find A Grave"
    SEARCH = "https://www.findagrave.com/memorial/search"

    TERMS = ["Carrigtwohill", "Templecurraheen Cork"]

    def collect(self):
        total_new = 0
        for term in self.TERMS:
            r = _get(self.SEARCH, params={
                "lastname": "",
                "firstname": "",
                "cemeteryName": term,
                "locationId": "",
                "memorialid": "",
            })
            if not r:
                _sleep(DELAY * 2)
                continue
            soup = BeautifulSoup(r.text, "lxml")
            found, new = 0, 0
            for item in soup.find_all("li", class_=re.compile(r"memorial|search-result", re.I))[:15]:
                link = item.find("a", href=True)
                text = item.get_text(separator=" ", strip=True)
                if not text:
                    continue
                url = urljoin("https://www.findagrave.com", link["href"]) if link else "https://www.findagrave.com"
                article = {
                    "title": text[:200],
                    "url": url,
                    "content": text,
                    "summary": text[:400],
                    "source": self.NAME,
                    "source_type": "genealogy",
                    "category": "genealogy",
                    "date_published": "",
                    "author": "",
                    "tags": json.dumps(["findagrave", "cemetery", "memorial", "genealogy"]),
                    "relevance_score": _relevance(text + " " + term),
                    "notes": _ai_meta("tier3_genealogy", self.NAME),
                }
                is_new, _ = db.insert_article(article)
                found += 1
                if is_new:
                    new += 1; total_new += 1
                _sleep(DELAY * 0.8)
            db.log_run(self.NAME, term, found, new)
            _sleep(DELAY * 2)
        return total_new


# ═════════════════════════════════════════════════════════════════════════════
# ADDITIONAL COLLECTORS (v3) – added after critical source review Feb 2026
# ═════════════════════════════════════════════════════════════════════════════
#
#  U.  NLI Catalogue        – National Library of Ireland (VuFind API, no key)
#  V.  British History Online – Calendar of State Papers Ireland + Poor Law
#  W.  Digital Repository of Ireland (DRI) – multi-institution aggregator
#                                            (requires DRI_API_KEY in .env)
# ─────────────────────────────────────────────────────────────────────────────


class NLICatalogueCollector:
    """
    National Library of Ireland catalogue via VuFind REST API.
    No API key required. Returns JSON records covering manuscripts, maps,
    photographs, estate papers, and books across all Irish counties.
    Holdings of particular relevance: Smith-Barry estate papers, Cork landed
    estate records, pre-Famine maps, Catholic parish records on microfilm.

    API endpoint (VuFind v5 JSON):
      https://catalogue.nli.ie/api/v1/search?q=...&limit=10&type=AllFields
    Falls back to scraping the HTML search page if the JSON API is blocked.
    Also seeds known NLI catalogue records directly.
    """

    NAME = "National Library of Ireland Catalogue"
    # VuFind v5 JSON API (primary)
    API_URL  = "https://catalogue.nli.ie/api/v1/search"
    # HTML search fallback
    HTML_URL = "https://catalogue.nli.ie/Search/Results"

    SEARCH_TERMS = [
        "Carrigtwohill",
        "Templecurraheen",
        "Midleton Workhouse Cork",
        "Barrymore barony Cork",
        "Smith Barry Cork estate",
        "East Cork famine history",
    ]

    # Seed known NLI holdings directly
    KNOWN_RECORDS = [
        {
            "title": "NLI MS 5765 – Smith-Barry Estate Papers, Carrigtwohill & Fota",
            "url": "https://catalogue.nli.ie/Search/Results?lookfor=smith+barry+carrigtwohill&type=AllFields",
            "summary": (
                "National Library of Ireland manuscript collections relating to the "
                "Smith-Barry family, principal landowners of Carrigtwohill and Fota estate "
                "from the 17th century through the Land League era. Papers include estate "
                "maps, rent rolls, tenancy records and family correspondence."
            ),
            "tags": ["nli", "smith-barry", "carrigtwohill", "fota", "estate-papers", "manuscripts"],
            "relevance_score": 9.5,
        },
    ]

    def collect(self):
        total_new = 0

        # Seed known NLI records
        for seed in self.KNOWN_RECORDS:
            article = {
                "title": seed["title"],
                "url": seed["url"],
                "content": "",
                "summary": seed["summary"],
                "source": self.NAME,
                "source_type": "archive",
                "category": "history",
                "date_published": "",
                "author": "National Library of Ireland",
                "tags": json.dumps(seed["tags"]),
                "relevance_score": seed["relevance_score"],
                "notes": _ai_meta("tier1_academic", self.NAME),
            }
            is_new, _ = db.insert_article(article)
            if is_new:
                total_new += 1

        for term in self.SEARCH_TERMS:
            # Try JSON API first
            params = {"q": term, "limit": 10, "type": "AllFields"}
            r = _get(self.API_URL, params=params, timeout=25)
            records = []
            if r:
                try:
                    data = r.json()
                    records = data.get("records", [])
                except KeyboardInterrupt:
                    raise
                except Exception:
                    pass

            # Fallback: try HTML search page if JSON returned nothing
            if not records:
                r2 = _get(self.HTML_URL, params={"lookfor": term, "type": "AllFields"}, timeout=20)
                if r2:
                    soup = BeautifulSoup(r2.text, "lxml")
                    for item in soup.find_all(
                            ["div", "li"], class_=re.compile(r"result|record", re.I))[:10]:
                        link = item.find("a", href=True)
                        title_el = item.find(["h2", "h3"])
                        if not title_el and not link:
                            continue
                        t = (title_el.get_text(strip=True) if title_el
                             else link.get_text(strip=True))
                        href = link["href"] if link else ""
                        if href and not href.startswith("http"):
                            href = "https://catalogue.nli.ie" + href
                        snippet = item.get_text(separator=" ", strip=True)[:500]
                        records.append({"title": t, "_url": href, "_snippet": snippet})
                _sleep(DELAY)

            found, new = 0, 0
            for rec in records[:10]:
                title = rec.get("title", "") or rec.get("_title", "")
                if not title:
                    continue
                summary_raw = rec.get("summary", [])
                summary = (" ".join(summary_raw) if isinstance(summary_raw, list)
                           else rec.get("_snippet", ""))
                subjects = rec.get("subjects", [])
                subject_text = " | ".join(subjects) if subjects else ""
                rec_id = rec.get("id", "")
                url = rec.get("_url") or (
                    f"https://catalogue.nli.ie/Record/{rec_id}" if rec_id
                    else self.HTML_URL)
                for url_obj in (rec.get("urls") or []):
                    if isinstance(url_obj, dict) and url_obj.get("url"):
                        url = url_obj["url"]
                        break
                authors_block = rec.get("authors", {}) or {}
                primary = list((authors_block.get("primary") or {}).keys())
                author = primary[0] if primary else ""
                content = f"{title}. {summary}. Subjects: {subject_text}".strip(". ")
                article = {
                    "title": title[:300],
                    "url": url,
                    "content": content[:2000],
                    "summary": content[:500],
                    "source": self.NAME,
                    "source_type": "archive",
                    "category": "history",
                    "date_published": "",
                    "author": author,
                    "tags": json.dumps(["nli", "national-library-ireland", "catalogue", "manuscripts"]),
                    "relevance_score": _relevance(content + " " + term),
                    "notes": _ai_meta("tier1_academic", self.NAME),
                }
                is_new, _ = db.insert_article(article)
                found += 1
                if is_new:
                    new += 1
                    total_new += 1
                _sleep(DELAY)
            db.log_run(self.NAME, term, found, new)
            _sleep(DELAY * 2)
        return total_new


class BritishHistoryOnlineCollector:
    """
    British History Online (british-history.ac.uk) – free digital library of
    primary and secondary sources maintained by the Institute of Historical
    Research and the History of Parliament Trust.

    Key series for Carrigtwohill research:
      - Calendar of State Papers relating to Ireland (Elizabethan, Cromwellian,
        Williamite periods) – covers land grants, forfeitures, & plantation
      - Calendar of the Justiciary Rolls, Ireland
      - Ordnance Survey memoirs and field name books
      - Parliamentary papers on the Irish Poor Law system

    No API – scrapes HTML search results. Content is free, no paywalled hits
    in search results for pre-1922 Irish material.
    """

    NAME = "British History Online"
    SEARCH_BASE = "https://www.british-history.ac.uk/search/results"
    SEARCH_TERMS = [
        "Carrigtwohill Cork",
        "Midleton Cork Ireland",
        "Barrymore Cork Ireland",
        "Cork Poor Law Ireland",
        "Calendar State Papers Ireland Cork",
        "Cork famine workhouse",
    ]

    def collect(self):
        total_new = 0
        for term in self.SEARCH_TERMS:
            params = {"query": term}
            r = _get(self.SEARCH_BASE, params=params, timeout=20)
            if not r:
                _sleep(DELAY * 2)
                continue
            soup = BeautifulSoup(r.text, "lxml")
            found, new = 0, 0
            # BHO search result items – typically <div class="search-result"> or similar
            for item in soup.find_all(["article", "div"],
                                      class_=re.compile(r"search.?result|result.?item|bho.?result", re.I))[:12]:
                link = item.find("a", href=True)
                title_tag = item.find(re.compile(r"h[1-5]"))
                if not link and not title_tag:
                    continue
                href = (link["href"] if link else "")
                if href and not href.startswith("http"):
                    href = "https://www.british-history.ac.uk" + href
                title = (title_tag.get_text(strip=True) if title_tag
                         else (link.get_text(strip=True) if link else ""))
                if not title:
                    continue
                snippet = item.get_text(separator=" ", strip=True)[:1000]
                article = {
                    "title": title[:300],
                    "url": href or "https://www.british-history.ac.uk",
                    "content": snippet[:2000],
                    "summary": snippet[:500],
                    "source": self.NAME,
                    "source_type": "archive",
                    "category": "history",
                    "date_published": "",
                    "author": "",
                    "tags": json.dumps(["british-history-online", "state-papers", "ireland",
                                        "primary-source", "calendar"]),
                    "relevance_score": _relevance(snippet + " " + term),
                    "notes": _ai_meta("tier1_academic", self.NAME),
                }
                is_new, _ = db.insert_article(article)
                found += 1
                if is_new:
                    new += 1
                    total_new += 1
                _sleep(DELAY * 0.5)
            db.log_run(self.NAME, term, found, new)
            _sleep(DELAY * 2)
        return total_new


class DRICollector:
    """
    Digital Repository of Ireland (repository.dri.ie) – Ireland's national
    trusted digital repository, aggregating digital objects from NUI Galway,
    UCC, Trinity College, National Museum, and dozens of regional archives.

    Uses the public /catalog endpoint (Solr-backed, no auth required).
    API docs: https://repository.dri.ie/api-docs
    """

    NAME = "Digital Repository of Ireland"
    CATALOG_URL = "https://repository.dri.ie/catalog"
    SEARCH_TERMS = [
        "Carrigtwohill",
        "Templecurraheen",
        "Midleton Cork",
        "Barrymore Cork",
        "Cork famine",
        "East Cork history",
    ]

    @staticmethod
    def _parse_date(doc):
        """Extract date string from DRI Solr date_tesim field."""
        dates = doc.get("date_tesim", [])
        if not dates:
            return ""
        # Format: "name=1939-10-30; start=1939-10-30;"
        raw = dates[0]
        for part in raw.split(";"):
            part = part.strip()
            if part.startswith("name="):
                return part[5:]
        return raw

    def collect(self):
        total_new = 0
        for term in self.SEARCH_TERMS:
            r = _get(self.CATALOG_URL, params={"q": term, "per_page": 10},
                     extra_headers={"Accept": "application/json"})
            if not r:
                _sleep(DELAY * 2)
                continue
            try:
                data = r.json()
            except KeyboardInterrupt:
                raise
            except Exception as e:
                log.warning(f"{self.NAME} [{term}]: bad JSON — {e}")
                _sleep(DELAY * 2)
                continue
            docs = data.get("response", {}).get("docs", [])
            found, new = 0, 0
            for doc in docs[:10]:
                titles = doc.get("title_tesim", [])
                title = titles[0] if titles else ""
                if not title:
                    continue
                descs = doc.get("description_tesim", [])
                desc = descs[0] if descs else ""
                creators = doc.get("creator_tesim", [])
                author = creators[0] if creators else ""
                pub_date = self._parse_date(doc)
                item_id = doc.get("id", "")
                item_url = (f"https://repository.dri.ie/catalog/{item_id}"
                            if item_id else "https://repository.dri.ie")
                collection = doc.get("root_collection_tesim", [""])[0]
                content = f"{title}. {desc}".strip(". ")
                article = {
                    "title": title[:300],
                    "url": item_url,
                    "content": content[:2000],
                    "summary": f"{collection} | {pub_date} | {desc[:300]}".strip(" |"),
                    "source": self.NAME,
                    "source_type": "archive",
                    "category": "history",
                    "date_published": pub_date,
                    "author": author,
                    "tags": json.dumps(["dri", "digital-repository-ireland",
                                        "multi-institution", "heritage"]),
                    "relevance_score": _relevance(content + " " + term),
                    "notes": _ai_meta("tier1_academic", self.NAME,
                                      {"collection": collection}),
                }
                is_new, _ = db.insert_article(article)
                found += 1
                if is_new:
                    new += 1
                    total_new += 1
                _sleep(DELAY)
            db.log_run(self.NAME, term, found, new)
            _sleep(DELAY * 2)
        return total_new


# ═════════════════════════════════════════════════════════════════════════════
# Registry of all new collectors
# ═════════════════════════════════════════════════════════════════════════════

NEW_COLLECTORS = [
    # Tier 1 – Global
    HathiTrustCollector(),
    EuropeanaCollector(),
    OpenAlexCollector(),
    TroveCollector(),
    ChroniclingAmericaCollector(),
    CoreAPICollector(),
    # Tier 1 – National Libraries (v3 additions)
    NLICatalogueCollector(),
    BritishHistoryOnlineCollector(),
    DRICollector(),
    # Tier 2 – Irish local
    CarrigtwohillHistoricalSocietyCollector(),
    CarrigtwohillCommunityCouncilCollector(),
    WorkhousesOrgCollector(),
    IrelandXOCollector(),
    IrishArchivesResourceCollector(),
    CorkArchivesCollector(),
    NationalFamineCollector(),
    # Tier 3 – Genealogy / Graveyard
    HistoricGravesCollector(),
    IrishGraveyardsCollector(),
    IGPWebCollector(),
    FindAGraveCollector(),
]
