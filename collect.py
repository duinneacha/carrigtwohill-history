"""
Carrigtwohill Research Repository - Automated Content Collector  v2.0
Searches multiple free/open sources for content about Carrigtwohill, Co. Cork, Ireland.

ORIGINAL SOURCES (v1):
  1.  Wikipedia            – encyclopedia articles
  2.  Internet Archive     – digitised historical texts & books
  3.  OpenLibrary          – book catalogue with publication data
  4.  DÚCHás              – Irish Folklore Commission (Schools Collection)
  5.  Logainm             – Irish Placenames Database
  6.  Google News RSS      – current & recent news articles
  7.  CELT (UCC)          – Corpus of Electronic Texts (historical Irish sources)
  8.  IrishGenealogy.ie   – civil registration, census, church records search
  9.  National Monuments  – archaeological survey database (archaeology.ie)
  10. Buildings of Ireland – architectural heritage records
  11. Ask About Ireland    – digitised local studies material (Griffith's etc.)

NEW SOURCES (v2) – see new_collectors.py for full documentation:
  TIER 1 – Global Academic / Digital Libraries:
  12. HathiTrust           – 17M+ digitised books, free API
  13. Europeana            – pan-European cultural heritage API
  14. OpenAlex             – open academic paper index (no key needed)
  15. Trove (NLA)          – Irish-Australian diaspora newspapers
  16. Chronicling America  – Library of Congress US newspapers (free API)
  17. CORE                 – open research publications (register for key)

  TIER 2 – Irish-Specific Local Sources (extracted from 2025 AI search PDFs):
  18. Carrigtwohill Historical Society website
  19. Carrigtwohill Community Council history pages
  20. Workhouses.org.uk    – Midleton Workhouse / Famine records
  21. IrelandXO            – Irish diaspora connections
  22. Irish Archives Resource – Midleton Board of Guardians records
  23. Cork City & County Archives – Poor Law Unions 1838–1923
  24. National Famine Commemoration – irishfamine.ie + Skibbereen

  TIER 3 – Graveyard & Genealogy (from PDF refs):
  25. HistoricGraves.com   – community graveyard recording project
  26. IrishGraveyards.ie   – Irish graveyard database
  27. IGP Free Irish Genealogy – Cork cemetery inscriptions incl. Templecurraheen
  28. Find A Grave         – crowd-sourced global cemetery database

  v3 ADDITIONS – National Libraries & Critical Source Review (Feb 2026):
  29. NLI Catalogue        – National Library of Ireland (VuFind API, no key)
  30. British History Online – Calendar of State Papers Ireland + Poor Law
  31. Digital Repository of Ireland (DRI) – multi-institution aggregator (key needed)
"""

import requests
import json
import time
import re
import os
import logging
from pathlib import Path
from urllib.parse import quote_plus, urljoin, urlparse
from datetime import datetime
from bs4 import BeautifulSoup

# Optional: trafilatura for cleaner full-text extraction
try:
    import trafilatura
    HAS_TRAFILATURA = True
except ImportError:
    HAS_TRAFILATURA = False

# Load .env file from same directory if present
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    for _line in _env_path.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

import db
from new_collectors import NEW_COLLECTORS

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "CarrigtwohillHistoricalResearch/1.0 "
        "(Educational & genealogical research; contact: duinneacha@gmail.com)"
    ),
    "Accept-Language": "en-IE,en;q=0.9",
}

SEARCH_TERMS = [
    "Carrigtwohill",
    "Carrigtwohill Cork",
    "Carrigtwohill history",
    "Carrigtwohill heritage",
    "Carrigtwohill genealogy",
    "Carrigtwohill parish",
    "Carrigtwohill castle",
    "Carrigtwohill estate",
    "Carrigtwohill railway",
    "Carrigtwohill family",
]

# Delay between requests (seconds) – be polite
DELAY = 1.2


def _get(url, params=None, timeout=15):
    """Safe HTTP GET with headers."""
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        return r
    except Exception as e:
        log.warning(f"GET {url} → {e}")
        return None


def _relevance(text: str) -> float:
    """Score 0–10 based on how closely text relates to Carrigtwohill."""
    text_l = (text or "").lower()
    score = 0.0
    if "carrigtwohill" in text_l:
        score += 5.0
        if text_l.count("carrigtwohill") > 2:
            score += 2.0
    for word in ["cork", "barryroe", "barrymore", "great island", "east cork",
                 "cobh", "midleton", "whitegate", "carrigrohane", "fota"]:
        if word in text_l:
            score += 0.5
    return min(score, 10.0)


def _archive_article(url: str, article_id: int):
    """Fetch and store a local plain-text copy of an article."""
    if not url:
        return
    try:
        r = _get(url, timeout=20)
        if not r:
            return
        if HAS_TRAFILATURA:
            text = trafilatura.extract(r.text, include_comments=False, include_tables=True)
        else:
            soup = BeautifulSoup(r.text, "lxml")
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)

        if text:
            archive_dir = db.ARCHIVE_DIR / str(article_id)
            archive_dir.mkdir(parents=True, exist_ok=True)
            fpath = archive_dir / "content.txt"
            fpath.write_text(text[:500_000], encoding="utf-8")
            db.update_archived_path(article_id, str(fpath))
            log.info(f"  📄 Archived article {article_id}")
    except Exception as e:
        log.warning(f"Archive failed for {url}: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# 1. Wikipedia
# ─────────────────────────────────────────────────────────────────────────────

class WikipediaCollector:
    NAME = "Wikipedia"
    API  = "https://en.wikipedia.org/w/api.php"

    def _get_page(self, title: str) -> dict | None:
        r = _get(self.API, params={
            "action": "query", "titles": title,
            "prop": "extracts|info|revisions",
            "exintro": False, "explaintext": True,
            "inprop": "url", "format": "json",
        })
        if not r:
            return None
        pages = r.json().get("query", {}).get("pages", {})
        for pid, page in pages.items():
            if pid == "-1":
                continue
            content = page.get("extract", "")
            return {
                "title": page.get("title", title),
                "url": page.get("fullurl", f"https://en.wikipedia.org/wiki/{quote_plus(title)}"),
                "content": content,
                "summary": content[:500] if content else "",
                "source": self.NAME,
                "source_type": "encyclopedia",
                "category": "general",
                "date_published": "",
                "author": "Wikipedia contributors",
                "tags": json.dumps(["wikipedia", "encyclopedia"]),
                "relevance_score": _relevance(content + " " + title),
            }
        return None

    def collect(self):
        total_new = 0
        seen_titles = set()
        for term in SEARCH_TERMS[:5]:   # limit API calls
            r = _get(self.API, params={
                "action": "query", "list": "search",
                "srsearch": term, "srlimit": 10,
                "format": "json", "srprop": "snippet",
            })
            if not r:
                continue
            results = r.json().get("query", {}).get("search", [])
            found, new = 0, 0
            for item in results:
                title = item["title"]
                if title in seen_titles:
                    continue
                seen_titles.add(title)
                page = self._get_page(title)
                if page:
                    is_new, aid = db.insert_article(page)
                    found += 1
                    if is_new:
                        new += 1
                        total_new += 1
                        _archive_article(page["url"], aid)
                time.sleep(DELAY)
            db.log_run(self.NAME, term, found, new)
        return total_new


# ─────────────────────────────────────────────────────────────────────────────
# 2. Internet Archive
# ─────────────────────────────────────────────────────────────────────────────

class InternetArchiveCollector:
    NAME    = "Internet Archive"
    SEARCH  = "https://archive.org/advancedsearch.php"
    DETAILS = "https://archive.org/details/{}"
    TEXT    = "https://archive.org/download/{}/{}_djvu.txt"  # fallback

    def collect(self):
        total_new = 0
        for term in ["Carrigtwohill", "Carrigtwohill Cork", "Carrigtwohill Ireland"]:
            r = _get(self.SEARCH, params={
                "q": f'"{term}" AND (subject:Ireland OR subject:Cork OR subject:history)',
                "fl[]": ["identifier", "title", "description", "date", "creator",
                         "subject", "mediatype"],
                "sort[]": "date desc",
                "rows": 30,
                "output": "json",
            })
            if not r:
                continue

            docs = r.json().get("response", {}).get("docs", [])
            found, new = 0, 0
            for doc in docs:
                ident = doc.get("identifier", "")
                if not ident:
                    continue
                desc = doc.get("description") or ""
                if isinstance(desc, list):
                    desc = " ".join(desc)
                subj = doc.get("subject") or []
                if isinstance(subj, str):
                    subj = [subj]

                article = {
                    "title": doc.get("title") or ident,
                    "url": self.DETAILS.format(ident),
                    "content": desc,
                    "summary": desc[:400],
                    "source": self.NAME,
                    "source_type": "archive",
                    "category": "history",
                    "date_published": str(doc.get("date", "")),
                    "author": doc.get("creator") or "",
                    "tags": json.dumps(["internet-archive"] + subj[:5]),
                    "relevance_score": _relevance(desc + " " + (doc.get("title") or "")),
                }
                is_new, aid = db.insert_article(article)
                found += 1
                if is_new:
                    new += 1
                    total_new += 1
                time.sleep(DELAY)

            db.log_run(self.NAME, term, found, new)
        return total_new


# ─────────────────────────────────────────────────────────────────────────────
# 3. OpenLibrary
# ─────────────────────────────────────────────────────────────────────────────

class OpenLibraryCollector:
    NAME   = "OpenLibrary"
    SEARCH = "https://openlibrary.org/search.json"

    def collect(self):
        total_new = 0
        for term in ["Carrigtwohill", "Carrigtwohill Cork history"]:
            r = _get(self.SEARCH, params={"q": term, "limit": 20})
            if not r:
                continue
            found, new = 0, 0
            for doc in r.json().get("docs", []):
                authors = doc.get("author_name") or []
                subjects = doc.get("subject") or []
                key = doc.get("key") or ""
                article = {
                    "title": doc.get("title") or "Untitled",
                    "url": f"https://openlibrary.org{key}" if key else "",
                    "content": " ".join(subjects[:20]),
                    "summary": f"Published {doc.get('first_publish_year','')}. "
                               f"Authors: {', '.join(authors[:3])}. "
                               f"Subjects: {', '.join(subjects[:5])}",
                    "source": self.NAME,
                    "source_type": "book",
                    "category": "history",
                    "date_published": str(doc.get("first_publish_year") or ""),
                    "author": ", ".join(authors[:3]),
                    "tags": json.dumps(["openlibrary", "book"] + subjects[:4]),
                    "relevance_score": _relevance(" ".join(subjects) + " " + (doc.get("title") or "")),
                }
                is_new, _ = db.insert_article(article)
                found += 1
                if is_new:
                    new += 1
                    total_new += 1
                time.sleep(DELAY * 0.5)
            db.log_run(self.NAME, term, found, new)
        return total_new


# ─────────────────────────────────────────────────────────────────────────────
# 4. DÚCHás – Irish Folklore Commission Schools Collection
# ─────────────────────────────────────────────────────────────────────────────

class DuchasCollector:
    """
    Searches the DÚCHás API for folklore stories from Cork that mention
    Carrigtwohill. Requires a Gaois API key (apiKey query parameter).
    """
    NAME    = "DÚCHás (Irish Folklore Commission)"
    API     = "https://www.duchas.ie/api/v0.6/cbes"
    DETAIL  = "https://www.duchas.ie/en/cbes/story/{}"

    def collect(self):
        api_key = os.environ.get("GAOIS_API_KEY", "")
        if not api_key:
            log.warning(f"{self.NAME}: No GAOIS_API_KEY in .env — skipping.")
            return 0
        total_new = 0
        # Fetch Cork entries and filter by content
        page = 1
        while page <= 5:   # max 5 pages to avoid hammering
            r = _get(self.API, params={
                "County": "Cork", "Page": page, "PerPage": 50,
                "apiKey": api_key,
            })
            if not r:
                break
            data = r.json()
            stories = data if isinstance(data, list) else data.get("data", [])
            if not stories:
                break

            found, new = 0, 0
            for story in stories:
                title = story.get("Title") or story.get("titleEN") or "Untitled Folklore Entry"
                content = story.get("TranscriptText") or story.get("transcript") or ""
                if isinstance(content, list):
                    content = " ".join(str(c) for c in content)
                combined = (title + " " + content).lower()
                if "carrigtwohill" not in combined and "carrigtwohill" not in combined:
                    # Still store if it looks related
                    score = _relevance(combined)
                    if score < 1.0:
                        continue
                else:
                    score = _relevance(combined)

                sid = story.get("ID") or story.get("id") or ""
                url = self.DETAIL.format(sid) if sid else "https://www.duchas.ie"

                article = {
                    "title": title,
                    "url": url,
                    "content": content[:5000],
                    "summary": content[:400],
                    "source": self.NAME,
                    "source_type": "folklore",
                    "category": "history",
                    "date_published": str(story.get("DateCreated") or ""),
                    "author": story.get("CollectorName") or "",
                    "tags": json.dumps(["duchas", "folklore", "schools-collection", "cork"]),
                    "relevance_score": score,
                }
                is_new, aid = db.insert_article(article)
                found += 1
                if is_new:
                    new += 1
                    total_new += 1
            db.log_run(self.NAME, f"Cork page {page}", found, new)
            page += 1
            time.sleep(DELAY)
        return total_new


# ─────────────────────────────────────────────────────────────────────────────
# 5. Logainm – Irish Placenames Database
# ─────────────────────────────────────────────────────────────────────────────

class LogainmCollector:
    """Fetches official placename data for Carrigtwohill and related townlands.
    Requires a Gaois API key (apiKey query parameter).
    Docs: https://docs.gaois.ie/en/data/logainm/v1.0/api"""
    NAME   = "Logainm (Irish Placenames Database)"
    API    = "https://www.logainm.ie/api/v1.0/"

    def collect(self):
        api_key = os.environ.get("GAOIS_API_KEY", "")
        if not api_key:
            log.warning(f"{self.NAME}: No GAOIS_API_KEY in .env — skipping.")
            return 0
        total_new = 0
        for term in ["Carrigtwohill", "Carraig Thuathail"]:
            r = _get(self.API, params={"Query": term, "apiKey": api_key}, timeout=30)
            if not r:
                continue
            try:
                data = r.json()
                # v1.0 returns a list of place objects directly
                if isinstance(data, list):
                    items = data
                elif isinstance(data, dict):
                    items = data.get("results") or data.get("features") or [data]
                else:
                    items = []
            except Exception:
                continue

            found, new = 0, 0
            for item in items:
                # v1.0 response: placenames are in a nested array
                placenames = item.get("placenames") or []
                name_en = ""
                name_ga = ""
                for pn in placenames:
                    wording = pn.get("wording", "")
                    lang = pn.get("language", "")
                    if lang == "en" and not name_en:
                        name_en = wording
                    elif lang == "ga" and not name_ga:
                        name_ga = wording
                if not name_en:
                    name_en = str(item.get("id", "Unknown"))
                place_id = item.get("id") or ""
                content = json.dumps(item, ensure_ascii=False)
                article = {
                    "title": f"Logainm: {name_en}" + (f" / {name_ga}" if name_ga else ""),
                    "url": "https://www.logainm.ie/en/" + str(place_id),
                    "content": content,
                    "summary": f"Irish placename record for {name_en}. Irish form: {name_ga}.",
                    "source": self.NAME,
                    "source_type": "heritage",
                    "category": "history",
                    "date_published": "",
                    "author": "Logainm / Fiontar & Scoil na Gaeilge",
                    "tags": json.dumps(["logainm", "placenames", "gaeilge"]),
                    "relevance_score": _relevance(content),
                }
                is_new, _ = db.insert_article(article)
                found += 1
                if is_new:
                    new += 1
                    total_new += 1
                time.sleep(DELAY * 0.5)
            db.log_run(self.NAME, term, found, new)
        return total_new


# ─────────────────────────────────────────────────────────────────────────────
# 6. Google News (RSS)
# ─────────────────────────────────────────────────────────────────────────────

class RSSCollector:
    NAME  = "Google News RSS"

    FEEDS = [
        ("https://news.google.com/rss/search?q=Carrigtwohill+Cork&hl=en-IE&gl=IE&ceid=IE:en",
         "Google News", "news"),
        ("https://news.google.com/rss/search?q=Carrigtwohill+history&hl=en-IE&gl=IE&ceid=IE:en",
         "Google News", "news"),
        ("https://news.google.com/rss/search?q=Carrigtwohill+genealogy&hl=en-IE&gl=IE&ceid=IE:en",
         "Google News", "news"),
        ("https://www.independent.ie/feeds/ece-breaking-news-ireland.rss",
         "Irish Independent", "news"),
        ("https://www.irishexaminer.com/rss/news/ireland/", "Irish Examiner", "news"),
    ]

    def collect(self):
        try:
            import feedparser
        except ImportError:
            log.warning("feedparser not installed")
            return 0

        total_new = 0
        for feed_url, source_name, stype in self.FEEDS:
            try:
                feed = feedparser.parse(feed_url)
                found, new = 0, 0
                for entry in feed.entries:
                    text = (entry.get("title", "") + " " + entry.get("summary", "")).lower()
                    score = _relevance(text)
                    if score < 1.0 and "carrigtwohill" not in text:
                        continue
                    article = {
                        "title": entry.get("title") or "Untitled",
                        "url": entry.get("link") or "",
                        "content": entry.get("summary") or "",
                        "summary": entry.get("summary") or "",
                        "source": source_name,
                        "source_type": stype,
                        "category": "general",
                        "date_published": entry.get("published") or "",
                        "author": entry.get("author") or "",
                        "tags": json.dumps(["rss", "news"]),
                        "relevance_score": score,
                    }
                    is_new, aid = db.insert_article(article)
                    found += 1
                    if is_new:
                        new += 1
                        total_new += 1
                        _archive_article(article["url"], aid)
                db.log_run(source_name, feed_url, found, new)
                time.sleep(DELAY)
            except Exception as e:
                log.warning(f"RSS feed error {feed_url}: {e}")
        return total_new


# ─────────────────────────────────────────────────────────────────────────────
# 7. CELT – Corpus of Electronic Texts (University College Cork)
# ─────────────────────────────────────────────────────────────────────────────

class CELTCollector:
    """
    Seeds and scrapes the CELT catalogue (celt.ucc.ie) for texts mentioning
    Carrigtwohill. CELT publishes digitised Irish historical, literary and
    legal texts freely.

    NOTE: The old CGI search endpoint (celt.ucc.ie/cgi-bin/celt.cgi) was
    retired circa 2018 when UCC migrated CELT to a new platform. The current
    live search is at https://celt.ucc.ie/index.html with JavaScript rendering.
    This collector uses the VuFind-style JSON endpoint introduced in the 2018
    migration, and falls back to seeding known CELT records if the API is
    unavailable.
    """
    NAME   = "CELT – Corpus of Electronic Texts (UCC)"
    BASE   = "https://celt.ucc.ie"
    # New search endpoint post-2018 migration (VuFind JSON API)
    SEARCH = "https://celt.ucc.ie/Search/Results"

    # Known CELT records relevant to Carrigtwohill / East Cork
    KNOWN_RECORDS = [
        {
            "title": "Annals of the Four Masters (AFM) – CELT Edition",
            "url": "https://celt.ucc.ie/published/T100005A/index.html",
            "summary": (
                "Digitised edition of the Annals of the Four Masters from CELT (UCC). "
                "Contains early medieval references to the Barrymore area and the de Barry family "
                "whose descendants held Carrigtwohill castle and lands."
            ),
            "tags": ["celt", "ucc", "annals", "four-masters", "medieval", "de-barry"],
        },
        {
            "title": "Calendar of State Papers Ireland 1509–1573 – CELT",
            "url": "https://celt.ucc.ie/published/E100042/index.html",
            "summary": (
                "CELT edition of the Calendar of State Papers relating to Ireland 1509–1573. "
                "Contains references to Carrigtwohill, the Barry estates, and Cork plantations."
            ),
            "tags": ["celt", "ucc", "state-papers", "ireland", "plantation", "barry"],
        },
    ]

    def collect(self):
        total_new = 0

        # Seed known CELT records first
        for seed in self.KNOWN_RECORDS:
            article = {
                "title": seed["title"],
                "url": seed["url"],
                "content": "",
                "summary": seed["summary"],
                "source": self.NAME,
                "source_type": "academic",
                "category": "history",
                "date_published": "",
                "author": "Corpus of Electronic Texts (UCC)",
                "tags": json.dumps(seed["tags"]),
                "relevance_score": 8.0,
            }
            is_new, aid = db.insert_article(article)
            if is_new:
                total_new += 1
                _archive_article(seed["url"], aid)

        # Attempt live VuFind search (post-2018 CELT platform)
        for term in ["Carrigtwohill", "Barrymore Cork", "Barry Cork medieval"]:
            r = _get(self.SEARCH, params={"lookfor": term, "type": "AllFields", "view": "list"})
            if not r:
                time.sleep(DELAY)
                continue
            soup = BeautifulSoup(r.text, "lxml")
            found, new = 0, 0
            # VuFind result structure: .result or .record divs with .title links
            for item in soup.find_all(["div", "li"],
                                      class_=re.compile(r"result|record|celt-item", re.I))[:12]:
                link = item.find("a", href=True)
                if not link:
                    continue
                title_text = link.get_text(strip=True)
                href = link["href"]
                if not title_text or len(title_text) < 8:
                    continue
                full_url = urljoin(self.BASE, href)
                article = {
                    "title": title_text[:300],
                    "url": full_url,
                    "content": item.get_text(separator=" ", strip=True)[:2000],
                    "summary": f"CELT text result for '{term}'",
                    "source": self.NAME,
                    "source_type": "academic",
                    "category": "history",
                    "date_published": "",
                    "author": "",
                    "tags": json.dumps(["celt", "ucc", "academic", "historical-text"]),
                    "relevance_score": _relevance(title_text),
                }
                is_new, aid = db.insert_article(article)
                found += 1
                if is_new:
                    new += 1
                    total_new += 1
                    _archive_article(full_url, aid)
            db.log_run(self.NAME, term, found, new)
            time.sleep(DELAY)
        return total_new


# ─────────────────────────────────────────────────────────────────────────────
# 8. IrishGenealogy.ie  – Civil Registration & Church Records Search
# ─────────────────────────────────────────────────────────────────────────────

class IrishGenealogyCollector:
    """
    Seeds and scrapes IrishGenealogy.ie for Carrigtwohill parish records.
    IrishGenealogy.ie is the official Irish government genealogy portal,
    providing free access to civil registration (from 1864) and Catholic
    parish registers (from c.1740 for Cork parishes).

    NOTE: The old churchrecords.irishgenealogy.ie sub-domain was retired and
    merged into the unified irishgenealogy.ie portal in 2021. Church record
    search is now at https://www.irishgenealogy.ie/en/search/?type=church
    Civil records are at https://www.irishgenealogy.ie/en/search/?type=civil
    Direct scraping is limited by JavaScript rendering; this collector seeds
    the key landing pages and attempts to fetch the static search results page.
    """
    NAME   = "IrishGenealogy.ie"
    # Updated URLs post-2021 portal unification
    BASE   = "https://www.irishgenealogy.ie"
    CHURCH = "https://www.irishgenealogy.ie/en/search/?county=Cork&type=church&location=Carrigtwohill"
    CIVIL  = "https://www.irishgenealogy.ie/en/search/?county=Cork&type=civil"

    # Seed records for well-known Carrigtwohill parish register collections
    KNOWN_RECORDS = [
        {
            "title": "Carrigtwohill RC Parish Registers – IrishGenealogy.ie (Baptisms from 1741)",
            "url": "https://www.irishgenealogy.ie/en/search/?county=Cork&type=church&location=Carrigtwohill",
            "summary": (
                "Roman Catholic parish registers for Carrigtwohill (Kilmoney Union), "
                "Cork Diocese. Baptisms from c.1741, Marriages from c.1754. "
                "Free access via IrishGenealogy.ie."
            ),
            "tags": ["genealogy", "parish-records", "baptisms", "marriages", "carrigtwohill", "cork"],
            "relevance_score": 10.0,
        },
        {
            "title": "Carrigtwohill Church of Ireland Registers – IrishGenealogy.ie",
            "url": "https://www.irishgenealogy.ie/en/search/?county=Cork&type=church&location=Carrigtwohill&religion=CoI",
            "summary": (
                "Church of Ireland registers for Carrigtwohill parish, Cork. "
                "Includes baptisms, marriages and burials relevant to Protestant "
                "families in the Carrigtwohill area."
            ),
            "tags": ["genealogy", "church-of-ireland", "carrigtwohill", "cork", "registers"],
            "relevance_score": 9.0,
        },
    ]

    def collect(self):
        total_new = 0

        # Seed known portal pages
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
                "author": "IrishGenealogy.ie (Department of Social Protection)",
                "tags": json.dumps(seed["tags"]),
                "relevance_score": seed["relevance_score"],
            }
            is_new, _ = db.insert_article(article)
            if is_new:
                total_new += 1

        # Attempt live search page
        r = _get(self.CHURCH)
        found, new = 0, 0
        if r and len(r.text) > 500:
            soup = BeautifulSoup(r.text, "lxml")
            for row in soup.find_all("tr"):
                cells = row.find_all("td")
                if len(cells) < 3:
                    continue
                texts = [c.get_text(strip=True) for c in cells]
                a = {
                    "title": f"Church Record: {texts[0]} – {texts[1] if len(texts)>1 else ''}",
                    "url": self.CHURCH,
                    "content": " | ".join(texts),
                    "summary": " | ".join(texts[:5]),
                    "source": self.NAME,
                    "source_type": "genealogy",
                    "category": "genealogy",
                    "date_published": texts[2] if len(texts) > 2 else "",
                    "author": "",
                    "tags": json.dumps(["genealogy", "church-records", "carrigtwohill", "cork"]),
                    "relevance_score": 7.0,
                }
                is_new, _ = db.insert_article(a)
                found += 1
                if is_new:
                    new += 1
                    total_new += 1
        db.log_run(self.NAME, "Carrigtwohill church records", found, new)
        return total_new


# ─────────────────────────────────────────────────────────────────────────────
# 9. National Monuments Service – archaeology.ie
# ─────────────────────────────────────────────────────────────────────────────

class NationalMonumentsCollector:
    """
    Searches the National Monuments Service (SMR) for archaeological
    monuments in the Carrigtwohill townland area.
    """
    NAME   = "National Monuments Service (archaeology.ie)"
    SMR    = "https://www.archaeology.ie/archaeological-survey-database"
    API    = "https://maps.archaeology.ie/HistoricEnvironment/WFS"

    def _wfs_search(self):
        params = {
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "typeName": "SMR",
            "outputFormat": "application/json",
            "CQL_FILTER": "COUNTY='CO. CORK' AND PARISH like '%CARRIGTWOHILL%'",
            "count": 100,
        }
        r = _get(self.API, params=params)
        if not r:
            return []
        try:
            data = r.json()
            features = data.get("features") or []
            results = []
            for feat in features:
                props = feat.get("properties") or {}
                title = f"Monument: {props.get('SITE_NAME','Unknown')} – {props.get('SMR_NUM','')}"
                content = json.dumps(props, ensure_ascii=False)
                results.append({
                    "title": title,
                    "url": f"https://www.archaeology.ie/archaeological-survey-database#{props.get('SMR_NUM','')}",
                    "content": content,
                    "summary": f"{props.get('MON_TYPE','')} in {props.get('PARISH','')} townland.",
                    "source": self.NAME,
                    "source_type": "heritage",
                    "category": "archaeology",
                    "date_published": "",
                    "author": "National Monuments Service",
                    "tags": json.dumps(["archaeology", "national-monuments", "smu", "cork"]),
                    "relevance_score": 8.0,
                })
            return results
        except Exception as e:
            log.warning(f"NMS WFS parse error: {e}")
            return []

    def collect(self):
        results = self._wfs_search()
        found, new = len(results), 0
        for a in results:
            is_new, _ = db.insert_article(a)
            if is_new:
                new += 1
        db.log_run(self.NAME, "Carrigtwohill", found, new)
        return new


# ─────────────────────────────────────────────────────────────────────────────
# 10. Buildings of Ireland (buildingsofireland.ie)
# ─────────────────────────────────────────────────────────────────────────────

class BuildingsOfIrelandCollector:
    """Searches the National Inventory of Architectural Heritage."""
    NAME   = "Buildings of Ireland (NIAH)"
    SEARCH = "https://www.buildingsofireland.ie/buildings-search/buildings"

    def collect(self):
        r = _get(self.SEARCH, params={
            "townCounty": "Carrigtwohill",
            "county": "Cork",
            "format": "json"
        })
        total_new = 0
        found, new = 0, 0
        if r:
            soup = BeautifulSoup(r.text, "lxml")
            for item in soup.find_all("div", class_=re.compile(r"building|result|entry", re.I)):
                title = item.find(["h2", "h3", "strong"])
                title_text = title.get_text(strip=True) if title else "Building Record"
                link = item.find("a", href=True)
                url = urljoin(self.SEARCH, link["href"]) if link else self.SEARCH
                content = item.get_text(separator=" ", strip=True)
                article = {
                    "title": title_text or "NIAH Building Record",
                    "url": url,
                    "content": content,
                    "summary": content[:400],
                    "source": self.NAME,
                    "source_type": "heritage",
                    "category": "archaeology",
                    "date_published": "",
                    "author": "National Inventory of Architectural Heritage",
                    "tags": json.dumps(["niah", "buildings", "architecture", "heritage"]),
                    "relevance_score": _relevance(content),
                }
                is_new, _ = db.insert_article(article)
                found += 1
                if is_new:
                    new += 1
                    total_new += 1
        db.log_run(self.NAME, "Carrigtwohill", found, new)
        return total_new


# ─────────────────────────────────────────────────────────────────────────────
# 11. Ask About Ireland – digitised local studies
# ─────────────────────────────────────────────────────────────────────────────

class AskAboutIrelandCollector:
    """
    Seeds and scrapes Ask About Ireland (askaboutireland.ie) for digitised
    local studies material, in particular Griffith's Valuation and digitised
    local history collections relevant to Carrigtwohill and East Cork.

    NOTE: Ask About Ireland underwent a major redesign in 2022–2023. The old
    Griffith's Valuation path (/reading-room/history-heritage/griffiths-valuation)
    was retired. Griffith's Valuation is now hosted at a dedicated portal:
    https://www.askaboutireland.ie/griffith-valuation/
    The main reading room for local studies has moved to:
    https://www.askaboutireland.ie/reading-room/
    """
    NAME   = "Ask About Ireland"
    # Updated URL post-2022 redesign
    GRIFFITHS = "https://www.askaboutireland.ie/griffith-valuation/"
    READING_ROOM = "https://www.askaboutireland.ie/reading-room/"

    # Known records to seed if the live fetch fails
    KNOWN_RECORDS = [
        {
            "title": "Griffith's Primary Valuation – Carrigtwohill Parish, Cork (Ask About Ireland)",
            "url": "https://www.askaboutireland.ie/griffith-valuation/index.xml?Action=doNameSearch&surname=&firstname=&barony=Barrymore&county=Cork&parish=Carrigtwohill&townland=",
            "summary": (
                "Griffith's Primary Valuation of Ireland (1847–1864), Carrigtwohill parish, "
                "Barony of Barrymore, County Cork. Lists all landholders and rateable property "
                "circa 1851. Essential primary source for pre-Famine and Famine-era genealogy. "
                "Available freely via Ask About Ireland."
            ),
            "tags": ["griffiths-valuation", "genealogy", "carrigtwohill", "barrymore", "cork"],
            "relevance_score": 10.0,
            "date_pub": "1851",
            "author": "Richard Griffith",
        },
        {
            "title": "Ask About Ireland – Local Studies Reading Room (Cork Collections)",
            "url": "https://www.askaboutireland.ie/reading-room/",
            "summary": (
                "Ask About Ireland's digitised local studies reading room, providing access to "
                "local history and genealogy collections from Irish libraries and archives. "
                "Includes Cork County Library digitised holdings relevant to Carrigtwohill."
            ),
            "tags": ["ask-about-ireland", "local-studies", "cork", "reading-room"],
            "relevance_score": 7.5,
            "date_pub": "",
            "author": "",
        },
    ]

    def collect(self):
        total_new = 0

        # Seed known pages
        for seed in self.KNOWN_RECORDS:
            article = {
                "title": seed["title"],
                "url": seed["url"],
                "content": "",
                "summary": seed["summary"],
                "source": self.NAME,
                "source_type": "archive",
                "category": "genealogy",
                "date_published": seed.get("date_pub", ""),
                "author": seed.get("author", ""),
                "tags": json.dumps(seed["tags"]),
                "relevance_score": seed["relevance_score"],
            }
            is_new, _ = db.insert_article(article)
            if is_new:
                total_new += 1

        # Attempt live fetch of the Griffith's portal
        r = _get(self.GRIFFITHS)
        found, new = 0, 0
        if r and len(r.text) > 500:
            found = 1  # we fetched it, but results are JS-rendered
        db.log_run(self.NAME, "Griffiths Valuation Cork", found, new)
        return total_new


# ─────────────────────────────────────────────────────────────────────────────
# Seed – important known URLs about Carrigtwohill
# ─────────────────────────────────────────────────────────────────────────────

SEED_ARTICLES = [
    {
        "title": "Carrigtwohill – Wikipedia",
        "url": "https://en.wikipedia.org/wiki/Carrigtwohill",
        "source": "Wikipedia",
        "source_type": "encyclopedia",
        "category": "general",
        "summary": "Wikipedia article about Carrigtwohill, a town in County Cork, Ireland.",
        "tags": ["wikipedia", "overview"],
        "relevance_score": 10.0,
    },
    {
        # NOTE: Old URL (churchrecords.irishgenealogy.ie) was retired in 2021.
        # Updated to the unified IrishGenealogy.ie portal (launched 2021).
        "title": "Carrigtwohill RC Parish Registers – IrishGenealogy.ie (Baptisms from 1741)",
        "url": "https://www.irishgenealogy.ie/en/search/?county=Cork&type=church&location=Carrigtwohill",
        "source": "IrishGenealogy.ie",
        "source_type": "genealogy",
        "category": "genealogy",
        "summary": (
            "Roman Catholic parish registers for Carrigtwohill (Kilmoney Union), Cork Diocese. "
            "Baptisms from c.1741, Marriages from c.1754. Free access via IrishGenealogy.ie."
        ),
        "tags": ["genealogy", "parish-records", "baptisms", "marriages", "carrigtwohill", "cork"],
        "relevance_score": 10.0,
    },
    {
        "title": "Carrigtwohill Castle (SMR) – National Monuments Service",
        "url": "https://www.archaeology.ie/archaeological-survey-database#CO074-003",
        "source": "National Monuments Service (archaeology.ie)",
        "source_type": "heritage",
        "category": "archaeology",
        "summary": "National Monuments Service record for Carrigtwohill Castle, a tower house.",
        "tags": ["archaeology", "castle", "national-monuments"],
        "relevance_score": 10.0,
    },
    {
        "title": "Tithe Applotment Books, Co. Cork – Carrigtwohill",
        "url": "https://titheapplotmentbooks.nationalarchives.ie/reels/tab//004617685/004617685_00001.pdf",
        "source": "National Archives of Ireland",
        "source_type": "archive",
        "category": "genealogy",
        "summary": "Tithe Applotment Books for Carrigtwohill parish (c.1823–1837). "
                   "Lists landholders and tithe amounts paid.",
        "tags": ["tithe-applotment", "genealogy", "carrigtwohill", "1820s"],
        "relevance_score": 10.0,
    },
    {
        "title": "Carrigtwohill 1901 Census – National Archives of Ireland",
        "url": "https://www.census.nationalarchives.ie/search/results.jsp?county=Cork&townland=Carrigtwohill",
        "source": "National Archives of Ireland",
        "source_type": "archive",
        "category": "genealogy",
        "summary": "1901 Census returns for Carrigtwohill, County Cork.",
        "tags": ["census-1901", "genealogy", "carrigtwohill"],
        "relevance_score": 10.0,
    },
    {
        "title": "Carrigtwohill 1911 Census – National Archives of Ireland",
        "url": "https://www.census.nationalarchives.ie/search/results.jsp?year=1911&county=Cork&townland=Carrigtwohill",
        "source": "National Archives of Ireland",
        "source_type": "archive",
        "category": "genealogy",
        "summary": "1911 Census returns for Carrigtwohill, County Cork.",
        "tags": ["census-1911", "genealogy", "carrigtwohill"],
        "relevance_score": 10.0,
    },
    {
        "title": "Cork County Library – Carrigtwohill Local Studies",
        "url": "https://www.corklibrary.ie/local-studies/",
        "source": "Cork County Library",
        "source_type": "heritage",
        "category": "history",
        "summary": "Cork County Library Local Studies collection covering Carrigtwohill and East Cork.",
        "tags": ["cork-library", "local-studies", "east-cork"],
        "relevance_score": 7.0,
    },
    {
        "title": "Journal of the Cork Historical & Archaeological Society",
        "url": "https://www.corkhist.ie/journal/",
        "source": "Cork Historical & Archaeological Society",
        "source_type": "academic",
        "category": "history",
        "summary": "Peer-reviewed journal covering Cork history and archaeology. "
                   "Searchable back-catalogue contains many Carrigtwohill references.",
        "tags": ["cork-history", "academic", "journal", "archaeology"],
        "relevance_score": 8.0,
    },
    {
        "title": "Carrigtwohill Townlands – townlands.ie",
        "url": "https://www.townlands.ie/cork/barrymore/carrigtwohill/carrigtwohill/",
        "source": "Townlands.ie",
        "source_type": "heritage",
        "category": "history",
        "summary": "Townland data for Carrigtwohill, barony of Barrymore, County Cork.",
        "tags": ["townlands", "barony-barrymore", "geography"],
        "relevance_score": 9.0,
    },
    {
        "title": "Fota Estate & Island – Cork Heritage",
        "url": "https://fotahouse.com/history/",
        "source": "Fota House",
        "source_type": "heritage",
        "category": "history",
        "summary": "History of the Fota Estate, adjacent to Carrigtwohill. "
                   "The Smith Barry family were major landowners in the Carrigtwohill area.",
        "tags": ["fota", "smith-barry", "estate", "east-cork"],
        "relevance_score": 7.5,
    },
    {
        "title": "General Valuation of Rateable Property in Ireland (Griffith's), Cork – IrishOrigins",
        "url": "https://www.findmypast.ie/articles/world-records/full-list-of-the-irish-family-history-records/census-land-and-surveys/griffiths-valuation-of-ireland-1847-1864",
        "source": "FindMyPast",
        "source_type": "genealogy",
        "category": "genealogy",
        "summary": "Griffith's Valuation searchable database. Look for Carrigtwohill parish entries.",
        "tags": ["griffiths-valuation", "genealogy", "findmypast"],
        "relevance_score": 8.0,
    },
    # ── New seeds extracted from 2025 AI search PDFs ──────────────────────
    {
        "title": "Templecurraheen Graveyard – IGP Free Irish Genealogy (Cork Inscriptions)",
        "url": "https://www.igp-web.com/IGPArchives/ire/cork/cemeteries/templecurraheen.html",
        "source": "IGP Free Irish Genealogy",
        "source_type": "genealogy",
        "category": "genealogy",
        "summary": "Transcribed tombstone inscriptions from Templecurraheen Churchyard, Carrigtwohill. "
                   "Includes burials dating from 1768 to 19th century. Key genealogical primary source.",
        "tags": ["templecurraheen", "inscriptions", "genealogy", "graveyard", "igp"],
        "relevance_score": 10.0,
    },
    {
        "title": "Templecurraheen Graveyard – CemeteryLink",
        "url": "https://cemeterylink.com/cemetery/templecurraheen-graveyard-cork-cork-ireland/",
        "source": "CemeteryLink",
        "source_type": "genealogy",
        "category": "genealogy",
        "summary": "CemeteryLink index entry for Templecurraheen Graveyard, Cork, Ireland.",
        "tags": ["templecurraheen", "graveyard", "cemeterylink", "genealogy"],
        "relevance_score": 10.0,
    },
    {
        "title": "Midleton Workhouse – Workhouses.org.uk",
        "url": "https://www.workhouses.org.uk/Midleton/",
        "source": "Workhouses.org.uk",
        "source_type": "archive",
        "category": "history",
        "summary": "Peter Higginbotham's authoritative entry on Midleton Workhouse (1840–41). "
                   "Served Carrigtwohill and 17 surrounding electoral divisions. "
                   "Includes famine graveyard, indoor relief registers (1841–1925).",
        "tags": ["midleton-workhouse", "poor-law", "famine", "carrigtwohill"],
        "relevance_score": 9.5,
    },
    {
        "title": "Midleton Board of Guardians – Irish Archives Resource",
        "url": "https://iar.ie/archive/midleton-board-guardians/",
        "source": "Irish Archives Resource",
        "source_type": "archive",
        "category": "history",
        "summary": "Finding aid for Midleton Board of Guardians records held at Cork Archives Institute. "
                   "Covers minute books, financial accounts, indoor relief registers 1841–1925, "
                   "births 1844–1898 and deaths 1899–1932.",
        "tags": ["midleton-guardians", "poor-law", "cork-archives", "famine", "carrigtwohill"],
        "relevance_score": 9.5,
    },
    {
        "title": "Cork Poor Law Unions – Boards of Guardians 1838–1923 (Cork Archives)",
        "url": "https://www.corkarchives.ie/explore_collections/guide_to_collections/local_government_and_health/cork_poor_law_unions_boards_of_guardians_1838-1923/",
        "source": "Cork City & County Archives",
        "source_type": "archive",
        "category": "history",
        "summary": "Cork Archives guide to Poor Law Union records covering Cork, Kinsale, and Midleton. "
                   "Primary research pathway for Carrigtwohill Famine and workhouse history.",
        "tags": ["cork-archives", "poor-law", "midleton", "famine", "1838-1923"],
        "relevance_score": 9.0,
    },
    {
        "title": "Carrigtwohill & District Historical Society – Parish Churches",
        "url": "https://carrigtwohillhistoricalsociety.com/Religious%20of%20Parish/Parish%20Churches/ParishChurches.aspx",
        "source": "Carrigtwohill & District Historical Society",
        "source_type": "heritage",
        "category": "history",
        "summary": "Parish churches of Carrigtwohill including Kilcurfin/Templecurraheen, St David's, "
                   "and St Mary's. Covers Norman period to present day.",
        "tags": ["carrigtwohill-historical-society", "churches", "kilcurfin", "templecurraheen"],
        "relevance_score": 10.0,
    },
    {
        "title": "Carrigtwohill & District Historical Society – Abbey Ruins",
        "url": "https://carrigtwohillhistoricalsociety.com/Religious%20of%20Parish/Parish%20Churches/Abbey/Abbey.aspx",
        "source": "Carrigtwohill & District Historical Society",
        "source_type": "heritage",
        "category": "archaeology",
        "summary": "History of the Franciscan Abbey ruins in Carrigtwohill, founded by the Barry family. "
                   "Original village cemetery adjacent to the abbey.",
        "tags": ["abbey", "barry-family", "franciscan", "carrigtwohill-historical-society"],
        "relevance_score": 10.0,
    },
    {
        "title": "The Norman Period to the Reformation – Carrigtwohill Community Council",
        "url": "https://carrigtwohillcommunity.ie/history/the-norman-peroid-to-reformation/",
        "source": "Carrigtwohill Community Council",
        "source_type": "heritage",
        "category": "history",
        "summary": "Norman history of Carrigtwohill including de Barry family connections (1177–), "
                   "Kilcurfin church grant c.1183–1185, and Reformation impact.",
        "tags": ["norman", "de-barry", "carrigtwohill-community", "kilcurfin", "reformation"],
        "relevance_score": 9.5,
    },
    {
        "title": "Famine Times – Carraig Thuathail (Carrigtwohill) – Dúchas Schools Collection",
        "url": "https://www.duchas.ie/en/cbes/4921870/4897371/5190387",
        "source": "DÚCHás (Irish Folklore Commission)",
        "source_type": "folklore",
        "category": "history",
        "summary": "Oral history account from Carrigtwohill recounting Famine experiences, "
                   "including the tragic story of food diverted from starving people to England.",
        "tags": ["duchas", "famine", "oral-history", "carrigtwohill", "an-gorta-mor"],
        "relevance_score": 10.0,
    },
    {
        "title": "Famine – Carraig Thuathail (Carrigtwohill) – Dúchas Schools Collection #2",
        "url": "https://www.duchas.ie/en/cbes/4921870/4897465/5190530",
        "source": "DÚCHás (Irish Folklore Commission)",
        "source_type": "folklore",
        "category": "history",
        "summary": "Second oral history account from Carrigtwohill in the Irish Folklore Commission "
                   "Schools Collection. Personal family Famine narratives.",
        "tags": ["duchas", "famine", "oral-history", "carrigtwohill"],
        "relevance_score": 10.0,
    },
    {
        "title": "Midleton Workhouse – IrelandXO Diaspora Database",
        "url": "https://irelandxo.com/ireland-xo/history-and-genealogy/buildings-database/midleton-workhouse",
        "source": "IrelandXO",
        "source_type": "genealogy",
        "category": "genealogy",
        "summary": "IrelandXO entry for Midleton Workhouse with links to diaspora connections "
                   "for families from Carrigtwohill and the Midleton Poor Law Union.",
        "tags": ["irelandxo", "midleton-workhouse", "diaspora", "genealogy"],
        "relevance_score": 8.5,
    },
    {
        "title": "Famine Records: Distress Papers & Relief Commission – National Archives Ireland",
        "url": "https://nationalarchives.ie/help-with-research/research-guides/famine-records-distress-papers-and-the-relief-commission/",
        "source": "National Archives of Ireland",
        "source_type": "archive",
        "category": "history",
        "summary": "National Archives research guide to Famine-era distress papers and Relief Commission "
                   "records. Includes townland-level returns for Carrigtwohill and Midleton Union.",
        "tags": ["national-archives", "famine-records", "distress-papers", "relief-commission"],
        "relevance_score": 8.5,
    },
    {
        "title": "Great Famine Facsimile Pack – Cork City and County Archives",
        "url": "https://publications.corkarchives.ie/view/131367936",
        "source": "Cork City & County Archives",
        "source_type": "archive",
        "category": "history",
        "summary": "Digital facsimile publication from Cork Archives covering the Great Famine in Cork. "
                   "Primary documents relating to Cork, Kinsale, and Midleton Poor Law Unions.",
        "tags": ["cork-archives", "famine", "facsimile", "midleton", "poor-law"],
        "relevance_score": 8.5,
    },
    {
        "title": "Carrigtwohill GAA – History: Prologue",
        "url": "https://carrigtwohillgaa.com/content_page/10062611/",
        "source": "Carrigtwohill GAA",
        "source_type": "heritage",
        "category": "history",
        "summary": "Historical prologue from Carrigtwohill GAA website covering the town's history "
                   "and community identity.",
        "tags": ["carrigtwohill-gaa", "local-history", "community"],
        "relevance_score": 9.0,
    },
    {
        "title": "Irish Examiner Newspaper Archive from 1841 – Irish News Archive",
        "url": "https://www.irishnewsarchive.com/irish-examiner-newspaper-archive",
        "source": "Irish News Archive",
        "source_type": "newspaper",
        "category": "history",
        "summary": "Digitised archive of the Cork Examiner (later Irish Examiner) from its founding "
                   "in 1841. Invaluable for Famine-era and local Carrigtwohill coverage.",
        "tags": ["cork-examiner", "irish-examiner", "newspaper-archive", "1841"],
        "relevance_score": 8.0,
    },
    {
        "title": "Carrigtwohill Community Council – History: Churches",
        "url": "https://carrigtwohillcommunity.ie/history/churches/",
        "source": "Carrigtwohill Community Council",
        "source_type": "heritage",
        "category": "history",
        "summary": "History of churches in Carrigtwohill: St David's, Templecurraheen/Kilcurfin, "
                   "St Mary's Catholic Church (1869). Reformation, Cromwellian destruction, and revival.",
        "tags": ["carrigtwohill-community", "churches", "st-davids", "st-marys", "templecurraheen"],
        "relevance_score": 9.5,
    },
    {
        "title": "Care of Historic Graveyards – Cork County Council Heritage Guide",
        "url": "https://www.corkcoco.ie/sites/default/files/2022-10/care_of_historic_graveyards_-_a_heritage_guide_by_cork_county_council.pdf",
        "source": "Cork County Council",
        "source_type": "heritage",
        "category": "archaeology",
        "summary": "Cork County Council's comprehensive guidance on care and conservation of historic "
                   "graveyards. Relevant to Templecurraheen and all Cork historic burial grounds.",
        "tags": ["cork-county-council", "graveyard-conservation", "heritage-guide"],
        "relevance_score": 7.5,
    },
    {
        "title": "Ireland's Historic Churches and Graveyards – Heritage Council",
        "url": "https://www.heritagecouncil.ie/content/files/irelands_historic_churches_graveyards_2006_2gb.pdf",
        "source": "Heritage Council of Ireland",
        "source_type": "heritage",
        "category": "archaeology",
        "summary": "Heritage Council guide to Ireland's historic churches and graveyards. "
                   "Framework for recording, conservation, and management of sites like Templecurraheen.",
        "tags": ["heritage-council", "historic-graveyards", "churches", "conservation"],
        "relevance_score": 7.5,
    },
    {
        "title": "Carr's Hill Famine Graveyard – Cork Historical Society Journal (1996)",
        "url": "https://corkhist.ie/wp-content/uploads/jfiles/1996/b1996-003.pdf",
        "source": "Cork Historical & Archaeological Society",
        "source_type": "academic",
        "category": "history",
        "summary": "1996 journal article about the Carr's Hill famine graveyard near Cork City. "
                   "Context for understanding Carrigtwohill's relationship with Cork Workhouse burials.",
        "tags": ["carrs-hill", "famine-graveyard", "cork-historical-society", "1996"],
        "relevance_score": 8.0,
    },
    {
        "title": "Oral History, Oral Tradition and the Great Famine – MIC Research Repository",
        "url": "https://dspace.mic.ul.ie/bitstream/handle/10395/1205/Cronin%2C%20M.%20%282012%29%20%27Oral%20History%2C%20Oral%20Tradition%20and%20the%20Great%20Famine%27.%28Pre-published%20%20Version%29%28Book%20Chapter%29pdf?sequence=2&isAllowed=y",
        "source": "Mary Immaculate College (MIC) Research Repository",
        "source_type": "academic",
        "category": "history",
        "summary": "Academic chapter by M. Cronin on oral history and the Great Famine. "
                   "Relevant to Dúchas.ie folklore accounts from Carrigtwohill.",
        "tags": ["oral-history", "famine", "academic", "mic", "cronin"],
        "relevance_score": 7.0,
    },
    {
        "title": "Victims of Ireland's Great Famine: Bioarchaeology of Mass Burials – Kilkenny Workhouse",
        "url": "https://minds.wisconsin.edu/bitstream/handle/1793/94621/anthony_v9.pdf?sequence=1&isAllowed=y",
        "source": "University of Wisconsin Digital Repository",
        "source_type": "academic",
        "category": "history",
        "summary": "Academic bioarchaeological study of mass famine burials at Kilkenny Union Workhouse. "
                   "Directly comparable to Midleton Workhouse famine graveyard serving Carrigtwohill.",
        "tags": ["famine-burial", "bioarchaeology", "workhouse", "academic", "kilkenny"],
        "relevance_score": 7.5,
    },
    {
        "title": "Historic Maps and Data – Tailte Éireann (Ordnance Survey Ireland)",
        "url": "https://tailte.ie/map-shop/professional-map-products/historic-maps-and-data/",
        "source": "Tailte Éireann (OSi)",
        "source_type": "heritage",
        "category": "history",
        "summary": "Historic Ordnance Survey maps for Ireland including the 6-inch series (1829–1842). "
                   "Essential for mapping pre-Famine Carrigtwohill townlands and features.",
        "tags": ["ordnance-survey", "historic-maps", "osi", "tailte-eireann"],
        "relevance_score": 8.0,
    },
    {
        "title": "Ordnance Survey Ireland – Virtual Treasury (Townland Index Maps)",
        "url": "https://virtualtreasury.ie/item/LBC-Townland",
        "source": "Virtual Treasury (OSi)",
        "source_type": "heritage",
        "category": "history",
        "summary": "Ordnance Survey townland index maps for Ireland. "
                   "Maps all 37 townlands within Carrigtwohill parish, barony of Barrymore.",
        "tags": ["ordnance-survey", "townland-maps", "virtual-treasury"],
        "relevance_score": 8.0,
    },
    {
        "title": "HistoricGraves.com – Community Graveyard Recording Project",
        "url": "https://historicgraves.com/",
        "source": "HistoricGraves.com",
        "source_type": "genealogy",
        "category": "genealogy",
        "summary": "Community-led project to photograph, transcribe, and publish Irish graveyard records. "
                   "May hold records for Templecurraheen and other Carrigtwohill burial grounds.",
        "tags": ["historicgraves", "graveyard", "community-recording", "genealogy"],
        "relevance_score": 8.5,
    },
    {
        "title": "Midletonwith1d – Local Blog: Workhouse Category",
        "url": "https://midletonwith1d.wordpress.com/category/workhouse/",
        "source": "Midleton with 1 d (Local Blog)",
        "source_type": "heritage",
        "category": "history",
        "summary": "Local Midleton blog with articles on the Midleton Workhouse history, "
                   "including references to Carrigtwohill and District Historical Society events.",
        "tags": ["midleton-blog", "workhouse", "local-history"],
        "relevance_score": 8.0,
    },
    {
        "title": "Midletonwith1d – Carrigtwohill and District Historical Society Tag",
        "url": "https://midletonwith1d.wordpress.com/tag/carrigtwohill-and-district-historical-society/",
        "source": "Midleton with 1 d (Local Blog)",
        "source_type": "heritage",
        "category": "history",
        "summary": "Collection of posts from local Midleton blog tagged 'Carrigtwohill and District "
                   "Historical Society'. Covers plaque unveilings, local events, and history.",
        "tags": ["midleton-blog", "carrigtwohill-historical-society", "local-events"],
        "relevance_score": 9.0,
    },
    # ── Additional seeds from Famine PDF evaluation (Feb 2026) ───────────────
    {
        "title": "Great Irish Famine – Skibbereen Heritage Centre",
        "url": "https://skibbheritage.com/great-irish-famine/",
        "source": "Skibbereen Heritage Centre",
        "source_type": "heritage",
        "category": "history",
        "summary": "Skibbereen Heritage Centre resource on the Great Irish Famine, covering County Cork's "
                   "experience during 1845–1852. Essential comparative context for Carrigtwohill Famine "
                   "research, as Skibbereen was among the worst-affected areas in Ireland.",
        "tags": ["famine", "skibbereen", "county-cork", "an-gorta-mor", "heritage"],
        "relevance_score": 7.5,
    },
    {
        "title": "Reminders of Famine in Cork still visible 180 years later – The Echo",
        "url": "https://www.echolive.ie/corklives/arid-41482117.html",
        "source": "The Echo (Cork)",
        "source_type": "newspaper",
        "category": "history",
        "summary": "Echo (Cork local newspaper) feature on surviving Famine-era sites in County Cork, "
                   "including workhouse buildings and famine graveyards. Contemporary coverage of "
                   "the Famine's lasting physical legacy across the county.",
        "tags": ["echo-cork", "famine", "famine-graveyard", "cork", "heritage"],
        "relevance_score": 7.5,
    },
    {
        "title": "The Great Famine in Cork City – Cork Heritage",
        "url": "http://corkheritage.ie/?page_id=7179",
        "source": "Cork Heritage",
        "source_type": "heritage",
        "category": "history",
        "summary": "Cork Heritage's dedicated page on the Great Famine in Cork City. Covers the Cork "
                   "Workhouse, Carr's Hill Famine Graveyard, and the experience of rural poor like "
                   "those from Carrigtwohill parish who converged on the city during the crisis.",
        "tags": ["cork-heritage", "famine", "cork-city", "workhouse", "carrs-hill"],
        "relevance_score": 8.0,
    },
    {
        "title": "The workhouse cemetery: 'Clonakilty, God help us' – Irish Heritage News",
        "url": "https://irishheritagenews.ie/workhouse-cemetery-clonakilty/",
        "source": "Irish Heritage News",
        "source_type": "heritage",
        "category": "history",
        "summary": "Irish Heritage News account of the Clonakilty workhouse famine cemetery. "
                   "Direct comparative context for the Midleton Workhouse famine graveyard "
                   "that served Carrigtwohill — similar conditions, similar unmarked mass burials.",
        "tags": ["workhouse-cemetery", "famine", "clonakilty", "cork", "poor-law"],
        "relevance_score": 7.0,
    },
    {
        "title": "Poverty and the Poor Laws – UK National Archives Research Guide",
        "url": "https://www.nationalarchives.gov.uk/help-with-your-research/research-guides/poverty-poor-laws/",
        "source": "UK National Archives",
        "source_type": "archive",
        "category": "history",
        "summary": "UK National Archives research guide to Poor Law records. Complementary to the Irish "
                   "National Archives holdings — relevant for understanding the Westminster policy "
                   "framework that shaped Irish Poor Law Unions including Midleton Union.",
        "tags": ["uk-national-archives", "poor-law", "poverty", "research-guide"],
        "relevance_score": 6.5,
    },
    # ── Additional seeds from critical source review (Feb 2026) ─────────────
    {
        "title": "Irish Landed Estates Database – Smith-Barry Family (NUI Galway)",
        "url": "https://www.landedestates.ie/landedestates/db/family/search?keyword=smith+barry",
        "source": "Irish Landed Estates Database (NUI Galway)",
        "source_type": "archive",
        "category": "history",
        "summary": "NUI Galway's Irish Landed Estates Database record for the Smith-Barry family, "
                   "the principal landowners of Carrigtwohill and Fota Estate. Contains estate maps, "
                   "tenancy records, and family history. Carrigtwohill was almost entirely within "
                   "Smith-Barry ownership from the 17th century through the Land League era.",
        "tags": ["landed-estates", "smith-barry", "fota", "landlord", "carrigtwohill", "nuigalway"],
        "relevance_score": 9.5,
    },
    {
        "title": "Irish Landed Estates – Barrymore Barony, County Cork (NUI Galway)",
        "url": "https://www.landedestates.ie/landedestates/db/estate/search?keyword=barrymore+cork",
        "source": "Irish Landed Estates Database (NUI Galway)",
        "source_type": "archive",
        "category": "history",
        "summary": "NUI Galway database of landed estates in the Barrymore barony, County Cork. "
                   "Carrigtwohill lies within Barrymore. Records cover estate boundaries, "
                   "landlord families, and tenancy details relevant to Famine and post-Famine history.",
        "tags": ["landed-estates", "barrymore", "cork", "landlord-history", "nuigalway"],
        "relevance_score": 9.0,
    },
    {
        "title": "Boston Pilot Missing Persons Database – Cork Emigrants (1831–1921)",
        "url": "https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/UNJU3N",
        "source": "Boston Pilot Missing Persons Database (Harvard Dataverse)",
        "source_type": "genealogy",
        "category": "genealogy",
        "summary": "Harvard Dataverse archive of 31,000+ 'Missing Friends' advertisements from the "
                   "Boston Pilot newspaper (1831–1921), placed by Irish emigrants seeking lost relatives. "
                   "Unique primary source for Famine-era emigration from Cork, including families "
                   "from Carrigtwohill and Midleton Poor Law Union who emigrated to the United States.",
        "tags": ["boston-pilot", "famine-emigration", "missing-persons", "cork", "genealogy", "diaspora"],
        "relevance_score": 8.0,
    },
    {
        "title": "NLI Historical Newspapers – Cork Papers Digitisation List",
        "url": "https://www.nli.ie/en/udlist-digitised-newspapers.aspx",
        "source": "National Library of Ireland – Historical Newspapers",
        "source_type": "newspaper",
        "category": "history",
        "summary": "National Library of Ireland's free digitised newspaper collection. Includes the "
                   "Cork Examiner from 1841 and the Cork Constitution — both cited as primary sources "
                   "for Famine-era conditions in County Cork. The Cork Constitution's coverage of "
                   "Carr's Hill graveyard (1847) is a key primary source for Carrigtwohill research.",
        "tags": ["nli-newspapers", "cork-examiner", "cork-constitution", "famine", "primary-source"],
        "relevance_score": 8.5,
    },
    {
        "title": "History Ireland – Great Famine and Cork",
        "url": "https://www.historyireland.com/?s=famine+cork",
        "source": "History Ireland Magazine",
        "source_type": "academic",
        "category": "history",
        "summary": "History Ireland magazine's peer-reviewed articles on the Great Famine in County Cork. "
                   "Published since 1993, it bridges popular and academic history. Articles cover "
                   "workhouses, mortality, emigration, and commemoration relevant to Carrigtwohill.",
        "tags": ["history-ireland", "famine", "cork", "academic", "peer-reviewed"],
        "relevance_score": 7.5,
    },
    {
        "title": "Calendar of State Papers relating to Ireland – British History Online",
        "url": "https://www.british-history.ac.uk/cal-state-papers/ireland/1601-3",
        "source": "British History Online",
        "source_type": "archive",
        "category": "history",
        "summary": "Full text of the Calendar of State Papers relating to Ireland, covering 1509 to 1670. "
                   "Essential for Carrigtwohill's plantation-era history — the Barry family land grants, "
                   "Cromwellian forfeitures, and Williamite settlements that defined the area's "
                   "landlord structure through to the Famine period.",
        "tags": ["british-history-online", "state-papers", "ireland", "plantation", "calendar"],
        "relevance_score": 7.5,
    },
    {
        "title": "NLI Catalogue – Carrigtwohill Holdings Search",
        "url": "https://catalogue.nli.ie/Search/Results?lookfor=carrigtwohill&type=AllFields",
        "source": "National Library of Ireland Catalogue",
        "source_type": "archive",
        "category": "history",
        "summary": "National Library of Ireland catalogue search for Carrigtwohill. "
                   "The NLI holds manuscripts, maps, photographs, microfilm of parish records, "
                   "and estate papers relevant to Carrigtwohill, the Smith-Barry family, and "
                   "the broader Barrymore barony of County Cork.",
        "tags": ["nli", "national-library-ireland", "catalogue", "carrigtwohill", "manuscripts"],
        "relevance_score": 9.0,
    },
]


def seed_database():
    """Insert known important Carrigtwohill sources into the database."""
    added = 0
    for a in SEED_ARTICLES:
        a["tags"] = json.dumps(a.get("tags", []))
        is_new, aid = db.insert_article(a)
        if is_new:
            added += 1
            _archive_article(a.get("url", ""), aid)
    log.info(f"Seed: added {added} / {len(SEED_ARTICLES)} articles")
    return added


# ─────────────────────────────────────────────────────────────────────────────
# Master run
# ─────────────────────────────────────────────────────────────────────────────

ALL_COLLECTORS = [
    WikipediaCollector(),
    InternetArchiveCollector(),
    OpenLibraryCollector(),
    DuchasCollector(),
    LogainmCollector(),
    RSSCollector(),
    CELTCollector(),
    IrishGenealogyCollector(),
    NationalMonumentsCollector(),
    BuildingsOfIrelandCollector(),
    AskAboutIrelandCollector(),
] + NEW_COLLECTORS  # 17 additional collectors from new_collectors.py (Tier 1–3)


def run_all(verbose=True):
    db.init_db()
    total = 0
    print("\n🔍 Starting Carrigtwohill content collection …\n")

    # Seed first
    s = seed_database()
    total += s
    if verbose:
        print(f"  📌 Seeded {s} known reference articles")

    for collector in ALL_COLLECTORS:
        try:
            if verbose:
                print(f"  ⏳ {collector.NAME} …", end=" ", flush=True)
            n = collector.collect()
            total += n
            if verbose:
                print(f"{n} new")
        except Exception as e:
            log.error(f"Collector {collector.NAME} failed: {e}")
            if verbose:
                print(f"ERROR: {e}")

    stats = db.get_stats()
    print(f"\n✅ Collection complete. Total articles in repository: {stats['total']}")
    print(f"   New this run: {total}\n")
    return total


if __name__ == "__main__":
    run_all()
