"""
Carrigtwohill Research Repository - Database Layer
SQLite + FTS5 full-text search engine

v1.0 — Articles, collection log, FTS for articles
v2.0 — Notable Persons system: extended persons table, person_sources,
        confidence_audit, families, persons_fts
v3.0 — Interactive Historical Map: locations, pois, poi_links,
        townland_boundaries, geo columns on persons
"""

import sqlite3
import json
import os
import csv
import io
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent
DB_PATH   = BASE_DIR / "data" / "carrigtwohill.db"
ARCHIVE_DIR = BASE_DIR / "data" / "archives"

# Domains whose articles should never be collected
BLOCKED_DOMAINS = {
    "rip.ie",
    "legacy.com",
    "funeralnotices.ie",
    "deathnotices.ie",
    "familyannouncements.ie",
    "tributes.com",
    "everhere.ie",
}


# ─────────────────────────────────────────────────────────────────────────────
# Connection
# ─────────────────────────────────────────────────────────────────────────────

def get_conn():
    os.makedirs(DB_PATH.parent, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ─────────────────────────────────────────────────────────────────────────────
# Schema
# ─────────────────────────────────────────────────────────────────────────────

SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT    NOT NULL,
    url         TEXT    UNIQUE,
    source      TEXT    DEFAULT 'Unknown',
    source_type TEXT    DEFAULT 'general',
    category    TEXT    DEFAULT 'general',
    date_found  TEXT    DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
    date_pub    TEXT    DEFAULT '',
    author      TEXT    DEFAULT '',
    content     TEXT    DEFAULT '',
    summary     TEXT    DEFAULT '',
    tags        TEXT    DEFAULT '[]',
    score       REAL    DEFAULT 0.0,
    archived    TEXT    DEFAULT '',
    notes       TEXT    DEFAULT '',
    is_manual   INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS collection_log (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    run_at  TEXT    DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
    source  TEXT,
    term    TEXT,
    found   INTEGER DEFAULT 0,
    new     INTEGER DEFAULT 0,
    error   TEXT    DEFAULT ''
);

CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(
    title, content, summary, author, tags,
    content='articles',
    content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS trg_ai AFTER INSERT ON articles BEGIN
    INSERT INTO articles_fts(rowid, title, content, summary, author, tags)
    VALUES (new.id, COALESCE(new.title,''), COALESCE(new.content,''),
            COALESCE(new.summary,''), COALESCE(new.author,''), COALESCE(new.tags,''));
END;

CREATE TRIGGER IF NOT EXISTS trg_ad AFTER DELETE ON articles BEGIN
    INSERT INTO articles_fts(articles_fts, rowid, title, content, summary, author, tags)
    VALUES ('delete', old.id, COALESCE(old.title,''), COALESCE(old.content,''),
            COALESCE(old.summary,''), COALESCE(old.author,''), COALESCE(old.tags,''));
END;

CREATE TRIGGER IF NOT EXISTS trg_au AFTER UPDATE ON articles BEGIN
    INSERT INTO articles_fts(articles_fts, rowid, title, content, summary, author, tags)
    VALUES ('delete', old.id, COALESCE(old.title,''), COALESCE(old.content,''),
            COALESCE(old.summary,''), COALESCE(old.author,''), COALESCE(old.tags,''));
    INSERT INTO articles_fts(rowid, title, content, summary, author, tags)
    VALUES (new.id, COALESCE(new.title,''), COALESCE(new.content,''),
            COALESCE(new.summary,''), COALESCE(new.author,''), COALESCE(new.tags,''));
END;
"""

# ── Notable Persons Schema (v2.0) ───────────────────────────────────────────

PERSONS_SCHEMA = """
CREATE TABLE IF NOT EXISTS persons (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    name                   TEXT    NOT NULL,
    birth_year             TEXT    DEFAULT '',
    death_year             TEXT    DEFAULT '',
    birth_location         TEXT    DEFAULT '',
    death_location         TEXT    DEFAULT '',
    connection             TEXT    DEFAULT '',
    bio                    TEXT    DEFAULT '',
    sources                TEXT    DEFAULT '[]',
    tier                   INTEGER DEFAULT 3,
    confidence             TEXT    DEFAULT 'medium',
    category               TEXT    DEFAULT 'historical',
    privacy_flag           INTEGER DEFAULT 0,
    emigration_year        TEXT    DEFAULT '',
    emigration_destination TEXT    DEFAULT '',
    emigration_route       TEXT    DEFAULT '',
    country_of_residence   TEXT    DEFAULT '',
    notable_for            TEXT    DEFAULT '',
    image_url              TEXT    DEFAULT '',
    wikidata_id            TEXT    DEFAULT '',
    wikipedia_url          TEXT    DEFAULT '',
    verified_by            TEXT    DEFAULT '',
    verified_date          TEXT    DEFAULT '',
    notes                  TEXT    DEFAULT '',
    added                  TEXT    DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
    last_modified          TEXT    DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
);

CREATE TABLE IF NOT EXISTS person_sources (
    person_id  INTEGER NOT NULL,
    article_id INTEGER NOT NULL,
    role       TEXT    DEFAULT 'mentioned',
    page_ref   TEXT    DEFAULT '',
    created    TEXT    DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
    PRIMARY KEY (person_id, article_id),
    FOREIGN KEY (person_id)  REFERENCES persons(id),
    FOREIGN KEY (article_id) REFERENCES articles(id)
);

CREATE TABLE IF NOT EXISTS confidence_audit (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id      INTEGER NOT NULL,
    old_confidence TEXT,
    new_confidence TEXT,
    reason         TEXT    DEFAULT '',
    reviewer       TEXT    DEFAULT '',
    review_date    TEXT    DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
    FOREIGN KEY (person_id) REFERENCES persons(id)
);

CREATE TABLE IF NOT EXISTS families (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    surname             TEXT    NOT NULL,
    origin_townland     TEXT    DEFAULT '',
    origin_parish       TEXT    DEFAULT 'Carrigtwohill',
    first_recorded_year INTEGER DEFAULT NULL,
    last_recorded_year  INTEGER DEFAULT NULL,
    frequency_score     REAL    DEFAULT 0.0,
    notes               TEXT    DEFAULT ''
);

CREATE VIRTUAL TABLE IF NOT EXISTS persons_fts USING fts5(
    name, bio, connection, notable_for,
    content='persons',
    content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS trg_pi AFTER INSERT ON persons BEGIN
    INSERT INTO persons_fts(rowid, name, bio, connection, notable_for)
    VALUES (new.id, COALESCE(new.name,''), COALESCE(new.bio,''),
            COALESCE(new.connection,''), COALESCE(new.notable_for,''));
END;

CREATE TRIGGER IF NOT EXISTS trg_pd AFTER DELETE ON persons BEGIN
    INSERT INTO persons_fts(persons_fts, rowid, name, bio, connection, notable_for)
    VALUES ('delete', old.id, COALESCE(old.name,''), COALESCE(old.bio,''),
            COALESCE(old.connection,''), COALESCE(old.notable_for,''));
END;

CREATE TRIGGER IF NOT EXISTS trg_pu AFTER UPDATE ON persons BEGIN
    INSERT INTO persons_fts(persons_fts, rowid, name, bio, connection, notable_for)
    VALUES ('delete', old.id, COALESCE(old.name,''), COALESCE(old.bio,''),
            COALESCE(old.connection,''), COALESCE(old.notable_for,''));
    INSERT INTO persons_fts(rowid, name, bio, connection, notable_for)
    VALUES (new.id, COALESCE(new.name,''), COALESCE(new.bio,''),
            COALESCE(new.connection,''), COALESCE(new.notable_for,''));
END;
"""


# ── Interactive Map Schema (v3.0) ─────────────────────────────────────────

MAP_SCHEMA = """
CREATE TABLE IF NOT EXISTS locations (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    name_irish    TEXT DEFAULT '',
    location_type TEXT DEFAULT 'townland',
    lat           REAL NOT NULL,
    lng           REAL NOT NULL,
    logainm_id    TEXT DEFAULT '',
    osm_id        TEXT DEFAULT '',
    notes         TEXT DEFAULT '',
    UNIQUE(name, location_type)
);

CREATE TABLE IF NOT EXISTS pois (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    description TEXT DEFAULT '',
    poi_type    TEXT DEFAULT 'site',
    lat         REAL NOT NULL,
    lng         REAL NOT NULL,
    era_start   INTEGER DEFAULT NULL,
    era_end     INTEGER DEFAULT NULL,
    era_label   TEXT DEFAULT '',
    townland    TEXT DEFAULT '',
    image_url   TEXT DEFAULT '',
    source_url  TEXT DEFAULT '',
    added       TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
);

CREATE TABLE IF NOT EXISTS poi_links (
    poi_id       INTEGER NOT NULL,
    entity_type  TEXT NOT NULL,
    entity_id    INTEGER NOT NULL,
    relationship TEXT DEFAULT '',
    PRIMARY KEY (poi_id, entity_type, entity_id),
    FOREIGN KEY (poi_id) REFERENCES pois(id)
);

CREATE TABLE IF NOT EXISTS townland_boundaries (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL UNIQUE,
    name_irish    TEXT DEFAULT '',
    area_acres    REAL DEFAULT 0,
    county        TEXT DEFAULT 'Cork',
    barony        TEXT DEFAULT 'Barrymore',
    parish        TEXT DEFAULT 'Carrigtwohill',
    geometry_json TEXT NOT NULL,
    centroid_lat  REAL DEFAULT 0,
    centroid_lng  REAL DEFAULT 0,
    logainm_id    TEXT DEFAULT ''
);
"""


def _migrate_articles_link_status(conn):
    """Add link_status and link_checked_at columns to articles if not present."""
    cols = [r[1] for r in conn.execute("PRAGMA table_info(articles)").fetchall()]
    link_cols = [
        ("link_status", "TEXT DEFAULT 'unchecked'"),
        ("link_checked_at", "TEXT DEFAULT ''"),
    ]
    added = 0
    for col_name, col_type in link_cols:
        if col_name not in cols:
            conn.execute(f"ALTER TABLE articles ADD COLUMN {col_name} {col_type}")
            added += 1
    if added:
        print(f"  ↳ Added {added} link-status columns to articles table")


def _migrate_map_tables(conn):
    """Add geo columns to persons table if not present."""
    cols = [r[1] for r in conn.execute("PRAGMA table_info(persons)").fetchall()]
    geo_cols = [
        ("birth_lat", "REAL DEFAULT NULL"),
        ("birth_lng", "REAL DEFAULT NULL"),
        ("death_lat", "REAL DEFAULT NULL"),
        ("death_lng", "REAL DEFAULT NULL"),
    ]
    added = 0
    for col_name, col_type in geo_cols:
        if col_name not in cols:
            conn.execute(f"ALTER TABLE persons ADD COLUMN {col_name} {col_type}")
            added += 1
    if added:
        print(f"  ↳ Added {added} geo columns to persons table")


def _migrate_persons_table(conn):
    """
    Migrate old persons table (v1) to new schema (v2) if needed.
    The old table had: id, name, birth_year, death_year, connection, bio, sources, added.
    The new table adds: tier, confidence, category, privacy_flag, locations, emigration, etc.
    Since the old table is empty (0 rows), we drop and recreate.
    """
    # Check if the new columns already exist
    cols = [r[1] for r in conn.execute("PRAGMA table_info(persons)").fetchall()]
    if "tier" in cols:
        return  # already migrated

    row_count = conn.execute("SELECT COUNT(*) FROM persons").fetchone()[0]
    if row_count == 0:
        # Safe to drop and recreate
        conn.execute("DROP TABLE IF EXISTS persons")
        # Also drop old FTS if it exists
        try:
            conn.execute("DROP TABLE IF EXISTS persons_fts")
        except Exception:
            pass
        print("  ↳ Migrated empty persons table to v2 schema")
    else:
        # Add columns to existing table (preserve data)
        new_cols = [
            ("birth_location", "TEXT DEFAULT ''"),
            ("death_location", "TEXT DEFAULT ''"),
            ("tier", "INTEGER DEFAULT 3"),
            ("confidence", "TEXT DEFAULT 'medium'"),
            ("category", "TEXT DEFAULT 'historical'"),
            ("privacy_flag", "INTEGER DEFAULT 0"),
            ("emigration_year", "TEXT DEFAULT ''"),
            ("emigration_destination", "TEXT DEFAULT ''"),
            ("emigration_route", "TEXT DEFAULT ''"),
            ("country_of_residence", "TEXT DEFAULT ''"),
            ("notable_for", "TEXT DEFAULT ''"),
            ("image_url", "TEXT DEFAULT ''"),
            ("wikidata_id", "TEXT DEFAULT ''"),
            ("wikipedia_url", "TEXT DEFAULT ''"),
            ("verified_by", "TEXT DEFAULT ''"),
            ("verified_date", "TEXT DEFAULT ''"),
            ("notes", "TEXT DEFAULT ''"),
            ("last_modified", "TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))"),
        ]
        for col_name, col_type in new_cols:
            if col_name not in cols:
                conn.execute(f"ALTER TABLE persons ADD COLUMN {col_name} {col_type}")
        print(f"  ↳ Added {len(new_cols)} columns to existing persons table")


def init_db():
    conn = get_conn()
    # v1 schema (articles, collection_log, articles_fts)
    conn.executescript(SCHEMA)
    # v2 migration: upgrade persons table if needed
    _migrate_persons_table(conn)
    # v2 schema (persons, person_sources, confidence_audit, families, persons_fts)
    conn.executescript(PERSONS_SCHEMA)
    # v3 schema (locations, pois, poi_links, townland_boundaries)
    conn.executescript(MAP_SCHEMA)
    _migrate_map_tables(conn)
    _migrate_articles_link_status(conn)
    conn.commit()
    conn.close()
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    print("✓ Database initialised")


# ─────────────────────────────────────────────────────────────────────────────
# Write
# ─────────────────────────────────────────────────────────────────────────────

def _is_blocked(url: str, title: str = "") -> bool:
    """Return True if the URL belongs to a blocked domain or the title
    indicates a redirect to one (e.g. Google News → RIP.ie)."""
    from urllib.parse import urlparse
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        host = ""
    for domain in BLOCKED_DOMAINS:
        if host == domain or host.endswith("." + domain):
            return True
    # Catch redirects (Google News RSS → rip.ie etc.) by checking the title
    if title:
        title_lower = title.lower()
        for domain in BLOCKED_DOMAINS:
            if f"- {domain}" in title_lower or f"| {domain}" in title_lower:
                return True
    return False


def insert_article(data: dict) -> tuple:
    """
    Insert an article. Returns (is_new: bool, row_id: int).
    Silently ignores duplicates (same URL).
    """
    url = data.get("url") or ""
    title_check = data.get("title") or ""
    if _is_blocked(url, title_check):
        return False, 0

    tags = data.get("tags", [])
    if isinstance(tags, list):
        tags = json.dumps(tags)

    conn = get_conn()
    try:
        cur = conn.execute(
            """INSERT OR IGNORE INTO articles
               (title, url, source, source_type, category,
                date_pub, author, content, summary, tags, score, is_manual)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                (data.get("title") or "Untitled")[:500],
                data.get("url") or "",
                data.get("source") or "Unknown",
                data.get("source_type") or "general",
                data.get("category") or "general",
                data.get("date_published") or "",
                data.get("author") or "",
                data.get("content") or "",
                data.get("summary") or "",
                tags,
                float(data.get("relevance_score") or 0.0),
                int(data.get("is_manual") or 0),
            ),
        )
        conn.commit()
        return cur.rowcount > 0, cur.lastrowid
    except Exception as e:
        print(f"DB insert error: {e}")
        return False, 0
    finally:
        conn.close()


def update_archived_path(article_id: int, path: str):
    conn = get_conn()
    conn.execute("UPDATE articles SET archived=? WHERE id=?", (path, article_id))
    conn.commit()
    conn.close()


def purge_blocked_articles() -> int:
    """Delete articles from blocked domains and remove their archived files."""
    conn = get_conn()
    rows = conn.execute("SELECT id, title, url, archived FROM articles").fetchall()
    to_delete = [r for r in rows if _is_blocked(r["url"], r["title"])]
    if not to_delete:
        conn.close()
        return 0
    for r in to_delete:
        if r["archived"]:
            try:
                archive_path = Path(r["archived"])
                if archive_path.exists():
                    archive_path.unlink()
                parent = archive_path.parent
                if parent.exists() and not any(parent.iterdir()):
                    parent.rmdir()
            except OSError:
                pass  # OneDrive / permission lock — DB row still gets deleted
    ids = [r["id"] for r in to_delete]
    conn.execute(f"DELETE FROM articles WHERE id IN ({','.join('?' * len(ids))})", ids)
    conn.commit()
    conn.close()
    return len(to_delete)


def log_run(source, term, found, new, error=""):
    conn = get_conn()
    conn.execute(
        "INSERT INTO collection_log (source,term,found,new,error) VALUES (?,?,?,?,?)",
        (source, term, found, new, error),
    )
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# Read
# ─────────────────────────────────────────────────────────────────────────────

def search(query="", category=None, source_type=None, source=None, min_score=None, page=1, per_page=20):
    """Full-text search with optional filters. Returns (rows, total_count)."""
    conn = get_conn()
    offset = (page - 1) * per_page

    try:
        if query and query.strip():
            safe_q = query.replace('"', "").replace("'", "").strip()
            base = """
                SELECT a.*,
                       highlight(articles_fts, 0, '<mark>', '</mark>') AS title_hl,
                       snippet(articles_fts, 1, '<mark>', '</mark>', ' … ', 35) AS snippet
                FROM articles a
                JOIN articles_fts ON a.id = articles_fts.rowid
                WHERE articles_fts MATCH ?
            """
            params = [safe_q]
            join = True
        else:
            base = """
                SELECT *,
                       title AS title_hl,
                       COALESCE(summary, SUBSTR(content, 1, 300)) AS snippet
                FROM articles WHERE 1=1
            """
            params = []
            join = False

        filters = ""
        if category and category != "all":
            filters += " AND {}.category = ?".format("a" if join else "articles")
            params.append(category)
        if source_type and source_type != "all":
            filters += " AND {}.source_type = ?".format("a" if join else "articles")
            params.append(source_type)
        if source:
            filters += " AND {}.source = ?".format("a" if join else "articles")
            params.append(source)
        if min_score is not None:
            filters += " AND {}.score >= ?".format("a" if join else "articles")
            params.append(min_score)

        count_sql = f"SELECT COUNT(*) FROM ({base}{filters})"
        total = conn.execute(count_sql, params).fetchone()[0]

        order = " ORDER BY a.score DESC, a.date_found DESC" if join else " ORDER BY score DESC, date_found DESC"
        sql = base + filters + order + f" LIMIT {per_page} OFFSET {offset}"
        rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
        return rows, total

    except Exception as e:
        print(f"Search error: {e}")
        return [], 0
    finally:
        conn.close()


def get_article(article_id: int):
    conn = get_conn()
    row = conn.execute("SELECT * FROM articles WHERE id=?", (article_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_stats():
    conn = get_conn()
    s = {}
    s["total"]      = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    s["sources"]    = [dict(r) for r in conn.execute(
        "SELECT source, COUNT(*) n FROM articles GROUP BY source ORDER BY n DESC LIMIT 12").fetchall()]
    s["categories"] = [dict(r) for r in conn.execute(
        "SELECT category, COUNT(*) n FROM articles GROUP BY category ORDER BY n DESC").fetchall()]
    s["types"]      = [dict(r) for r in conn.execute(
        "SELECT source_type, COUNT(*) n FROM articles GROUP BY source_type ORDER BY n DESC").fetchall()]
    s["recent"]     = [dict(r) for r in conn.execute(
        "SELECT id,title,source,date_found FROM articles ORDER BY date_found DESC LIMIT 8").fetchall()]
    lr = conn.execute("SELECT run_at FROM collection_log ORDER BY run_at DESC LIMIT 1").fetchone()
    s["last_run"]   = lr[0] if lr else "Never"
    s["persons"]    = conn.execute("SELECT COUNT(*) FROM persons").fetchone()[0]
    s["archived"]   = conn.execute("SELECT COUNT(*) FROM articles WHERE archived != ''").fetchone()[0]
    conn.close()
    return s


def export_csv() -> str:
    """Return all articles as CSV text."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT id,title,url,source,source_type,category,date_found,date_pub,author,summary,tags,score "
        "FROM articles ORDER BY date_found DESC"
    ).fetchall()
    conn.close()
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=[r[0] for r in conn.execute(
        "PRAGMA table_info(articles)").fetchall()
        if r[1] in ("id","title","url","source","source_type","category",
                    "date_found","date_pub","author","summary","tags","score")
    ] if False else ["id","title","url","source","source_type","category",
                     "date_found","date_pub","author","summary","tags","score"])
    writer.writeheader()
    writer.writerows([dict(r) for r in rows])
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# Notable Persons — Write
# ─────────────────────────────────────────────────────────────────────────────

def insert_person(data: dict) -> tuple:
    """
    Insert a notable person. Returns (is_new: bool, row_id: int).
    Skips if a person with the same name already exists.
    """
    sources = data.get("sources", [])
    if isinstance(sources, list):
        sources = json.dumps(sources)

    conn = get_conn()
    try:
        # Check for duplicate
        existing = conn.execute(
            "SELECT id FROM persons WHERE name = ?", (data.get("name", ""),)
        ).fetchone()
        if existing:
            return False, existing[0]

        cur = conn.execute(
            """INSERT INTO persons
               (name, birth_year, death_year, birth_location, death_location,
                connection, bio, sources, tier, confidence, category,
                privacy_flag, emigration_year, emigration_destination,
                emigration_route, country_of_residence, notable_for,
                image_url, wikidata_id, wikipedia_url, verified_by,
                verified_date, notes)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                data.get("name", ""),
                data.get("birth_year", ""),
                data.get("death_year", ""),
                data.get("birth_location", ""),
                data.get("death_location", ""),
                data.get("connection", ""),
                data.get("bio", ""),
                sources,
                int(data.get("tier", 3)),
                data.get("confidence", "medium"),
                data.get("category", "historical"),
                int(data.get("privacy_flag", 0)),
                data.get("emigration_year", ""),
                data.get("emigration_destination", ""),
                data.get("emigration_route", ""),
                data.get("country_of_residence", ""),
                data.get("notable_for", ""),
                data.get("image_url", ""),
                data.get("wikidata_id", ""),
                data.get("wikipedia_url", ""),
                data.get("verified_by", ""),
                data.get("verified_date", ""),
                data.get("notes", ""),
            ),
        )
        conn.commit()
        return True, cur.lastrowid
    except Exception as e:
        print(f"Person insert error: {e}")
        return False, 0
    finally:
        conn.close()


def update_person_confidence(person_id: int, new_confidence: str,
                              reason: str = "", reviewer: str = ""):
    """Update a person's confidence level and log the change."""
    conn = get_conn()
    try:
        old = conn.execute(
            "SELECT confidence FROM persons WHERE id = ?", (person_id,)
        ).fetchone()
        old_conf = old[0] if old else ""

        conn.execute(
            "UPDATE persons SET confidence = ?, last_modified = strftime('%Y-%m-%dT%H:%M:%S','now') WHERE id = ?",
            (new_confidence, person_id),
        )
        conn.execute(
            """INSERT INTO confidence_audit
               (person_id, old_confidence, new_confidence, reason, reviewer)
               VALUES (?,?,?,?,?)""",
            (person_id, old_conf, new_confidence, reason, reviewer),
        )
        conn.commit()
    finally:
        conn.close()


def link_person_source(person_id: int, article_id: int,
                        role: str = "mentioned", page_ref: str = ""):
    """Create a link between a person and an article (evidence chain)."""
    conn = get_conn()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO person_sources (person_id, article_id, role, page_ref) VALUES (?,?,?,?)",
            (person_id, article_id, role, page_ref),
        )
        conn.commit()
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# Notable Persons — Read
# ─────────────────────────────────────────────────────────────────────────────

def search_persons(query="", tier=None, confidence=None, category=None,
                    page=1, per_page=20):
    """
    Search/browse notable persons with optional filters.
    Returns (rows, total_count).
    """
    conn = get_conn()
    offset = (page - 1) * per_page

    try:
        if query and query.strip():
            safe_q = query.replace('"', "").replace("'", "").strip()
            base = """
                SELECT p.*,
                       highlight(persons_fts, 0, '<mark>', '</mark>') AS name_hl
                FROM persons p
                JOIN persons_fts ON p.id = persons_fts.rowid
                WHERE persons_fts MATCH ?
            """
            params = [safe_q]
            tbl = "p"
        else:
            base = """
                SELECT *, name AS name_hl
                FROM persons WHERE 1=1
            """
            params = []
            tbl = "persons"

        filters = ""
        if tier is not None and str(tier) in ("1", "2", "3"):
            filters += f" AND {tbl}.tier = ?"
            params.append(int(tier))
        if confidence and confidence in ("high", "medium", "low"):
            filters += f" AND {tbl}.confidence = ?"
            params.append(confidence)
        if category and category != "all":
            filters += f" AND {tbl}.category = ?"
            params.append(category)

        # Privacy: hide living persons with privacy_flag unless specifically filtered
        # (for Phase 1 we show them but note the flag in the template)

        count_sql = f"SELECT COUNT(*) FROM ({base}{filters})"
        total = conn.execute(count_sql, params).fetchone()[0]

        order = f" ORDER BY {tbl}.tier ASC, {tbl}.name ASC"
        sql = base + filters + order + f" LIMIT {per_page} OFFSET {offset}"
        rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
        return rows, total

    except Exception as e:
        print(f"Persons search error: {e}")
        return [], 0
    finally:
        conn.close()


def get_person(person_id: int):
    """Get a single person by ID."""
    conn = get_conn()
    row = conn.execute("SELECT * FROM persons WHERE id = ?", (person_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_person_sources(person_id: int):
    """Get all articles linked to a person via person_sources."""
    conn = get_conn()
    rows = conn.execute(
        """SELECT a.id, a.title, a.url, a.source, a.source_type,
                  ps.role, ps.page_ref
           FROM person_sources ps
           JOIN articles a ON a.id = ps.article_id
           WHERE ps.person_id = ?
           ORDER BY ps.created DESC""",
        (person_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_confidence_history(person_id: int):
    """Get the audit trail for a person's confidence changes."""
    conn = get_conn()
    rows = conn.execute(
        """SELECT * FROM confidence_audit
           WHERE person_id = ?
           ORDER BY review_date DESC""",
        (person_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_persons_stats():
    """Summary statistics for the persons system."""
    conn = get_conn()
    s = {}
    s["total"] = conn.execute("SELECT COUNT(*) FROM persons").fetchone()[0]
    s["by_tier"] = [dict(r) for r in conn.execute(
        "SELECT tier, COUNT(*) n FROM persons GROUP BY tier ORDER BY tier"
    ).fetchall()]
    s["by_confidence"] = [dict(r) for r in conn.execute(
        "SELECT confidence, COUNT(*) n FROM persons GROUP BY confidence ORDER BY confidence"
    ).fetchall()]
    s["by_category"] = [dict(r) for r in conn.execute(
        "SELECT category, COUNT(*) n FROM persons GROUP BY category ORDER BY category"
    ).fetchall()]
    conn.close()
    return s


# ─────────────────────────────────────────────────────────────────────────────
# Interactive Map — Write
# ─────────────────────────────────────────────────────────────────────────────

def insert_poi(data: dict) -> tuple:
    """Insert a POI. Returns (is_new: bool, row_id: int)."""
    conn = get_conn()
    try:
        existing = conn.execute(
            "SELECT id FROM pois WHERE name = ? AND lat = ? AND lng = ?",
            (data.get("name", ""), data.get("lat", 0), data.get("lng", 0)),
        ).fetchone()
        if existing:
            return False, existing[0]

        cur = conn.execute(
            """INSERT INTO pois
               (name, description, poi_type, lat, lng,
                era_start, era_end, era_label, townland,
                image_url, source_url)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                data.get("name", ""),
                data.get("description", ""),
                data.get("poi_type", "site"),
                float(data.get("lat", 0)),
                float(data.get("lng", 0)),
                data.get("era_start"),
                data.get("era_end"),
                data.get("era_label", ""),
                data.get("townland", ""),
                data.get("image_url", ""),
                data.get("source_url", ""),
            ),
        )
        conn.commit()
        return True, cur.lastrowid
    except Exception as e:
        print(f"POI insert error: {e}")
        return False, 0
    finally:
        conn.close()


def insert_location(data: dict) -> tuple:
    """Insert a location reference. Returns (is_new: bool, row_id: int)."""
    conn = get_conn()
    try:
        cur = conn.execute(
            """INSERT OR IGNORE INTO locations
               (name, name_irish, location_type, lat, lng, logainm_id, osm_id, notes)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                data.get("name", ""),
                data.get("name_irish", ""),
                data.get("location_type", "townland"),
                float(data.get("lat", 0)),
                float(data.get("lng", 0)),
                data.get("logainm_id", ""),
                data.get("osm_id", ""),
                data.get("notes", ""),
            ),
        )
        conn.commit()
        return cur.rowcount > 0, cur.lastrowid
    except Exception as e:
        print(f"Location insert error: {e}")
        return False, 0
    finally:
        conn.close()


def insert_townland_boundary(data: dict) -> tuple:
    """Insert a townland boundary. Returns (is_new: bool, row_id: int)."""
    conn = get_conn()
    try:
        cur = conn.execute(
            """INSERT OR IGNORE INTO townland_boundaries
               (name, name_irish, area_acres, county, barony, parish,
                geometry_json, centroid_lat, centroid_lng, logainm_id)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                data.get("name", ""),
                data.get("name_irish", ""),
                float(data.get("area_acres", 0)),
                data.get("county", "Cork"),
                data.get("barony", "Barrymore"),
                data.get("parish", "Carrigtwohill"),
                data.get("geometry_json", "{}"),
                float(data.get("centroid_lat", 0)),
                float(data.get("centroid_lng", 0)),
                data.get("logainm_id", ""),
            ),
        )
        conn.commit()
        return cur.rowcount > 0, cur.lastrowid
    except Exception as e:
        print(f"Townland boundary insert error: {e}")
        return False, 0
    finally:
        conn.close()


def link_poi(poi_id: int, entity_type: str, entity_id: int,
             relationship: str = ""):
    """Link a POI to an article or person."""
    conn = get_conn()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO poi_links (poi_id, entity_type, entity_id, relationship) VALUES (?,?,?,?)",
            (poi_id, entity_type, entity_id, relationship),
        )
        conn.commit()
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# Interactive Map — Read
# ─────────────────────────────────────────────────────────────────────────────

def get_townlands_geojson():
    """Return all townland boundaries as a GeoJSON FeatureCollection."""
    conn = get_conn()
    rows = conn.execute(
        """SELECT name, name_irish, area_acres, county, barony, parish,
                  geometry_json, centroid_lat, centroid_lng, logainm_id
           FROM townland_boundaries ORDER BY name"""
    ).fetchall()
    conn.close()

    features = []
    for r in rows:
        r = dict(r)
        try:
            geometry = json.loads(r["geometry_json"])
        except (json.JSONDecodeError, TypeError):
            continue
        features.append({
            "type": "Feature",
            "geometry": geometry,
            "properties": {
                "name": r["name"],
                "name_irish": r["name_irish"],
                "area_acres": r["area_acres"],
                "county": r["county"],
                "barony": r["barony"],
                "parish": r["parish"],
                "centroid_lat": r["centroid_lat"],
                "centroid_lng": r["centroid_lng"],
                "logainm_id": r["logainm_id"],
            },
        })

    return {"type": "FeatureCollection", "features": features}


def get_pois(poi_type=None, era=None):
    """Return POIs as a GeoJSON FeatureCollection, optionally filtered."""
    conn = get_conn()
    sql = "SELECT * FROM pois WHERE 1=1"
    params = []

    if poi_type:
        sql += " AND poi_type = ?"
        params.append(poi_type)

    if era:
        era_ranges = {
            "norman":   (1177, 1350),
            "medieval": (1350, 1600),
            "tudor":    (1500, 1650),
            "famine":   (1845, 1852),
            "modern":   (1900, 2100),
        }
        if era.lower() in era_ranges:
            start, end = era_ranges[era.lower()]
            sql += " AND (era_start IS NULL OR era_start <= ?) AND (era_end IS NULL OR era_end >= ?)"
            params.append(end)
            params.append(start)

    sql += " ORDER BY name"
    rows = conn.execute(sql, params).fetchall()
    conn.close()

    features = []
    for r in rows:
        r = dict(r)
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [r["lng"], r["lat"]],
            },
            "properties": {
                "id": r["id"],
                "name": r["name"],
                "description": r["description"],
                "poi_type": r["poi_type"],
                "era_start": r["era_start"],
                "era_end": r["era_end"],
                "era_label": r["era_label"],
                "townland": r["townland"],
                "image_url": r["image_url"],
                "source_url": r["source_url"],
            },
        })

    return {"type": "FeatureCollection", "features": features}


def get_poi(poi_id: int):
    """Get a single POI with linked articles and persons."""
    conn = get_conn()
    row = conn.execute("SELECT * FROM pois WHERE id = ?", (poi_id,)).fetchone()
    if not row:
        conn.close()
        return None

    poi = dict(row)

    # Get linked entities
    links = conn.execute(
        "SELECT entity_type, entity_id, relationship FROM poi_links WHERE poi_id = ?",
        (poi_id,),
    ).fetchall()

    linked_articles = []
    linked_persons = []
    for link in links:
        link = dict(link)
        if link["entity_type"] == "article":
            article = conn.execute(
                "SELECT id, title, url, source FROM articles WHERE id = ?",
                (link["entity_id"],),
            ).fetchone()
            if article:
                a = dict(article)
                a["relationship"] = link["relationship"]
                linked_articles.append(a)
        elif link["entity_type"] == "person":
            person = conn.execute(
                "SELECT id, name, birth_year, death_year, birth_location FROM persons WHERE id = ?",
                (link["entity_id"],),
            ).fetchone()
            if person:
                p = dict(person)
                p["relationship"] = link["relationship"]
                linked_persons.append(p)

    conn.close()
    poi["linked_articles"] = linked_articles
    poi["linked_persons"] = linked_persons
    return poi


def get_whatwashere(townland=None, era=None):
    """Get historical data for a townland, optionally filtered by era."""
    conn = get_conn()
    result = {"townland": None, "pois": [], "persons": [], "articles": []}

    if townland:
        # Get townland info
        tb = conn.execute(
            "SELECT * FROM townland_boundaries WHERE LOWER(name) = LOWER(?)",
            (townland,),
        ).fetchone()
        if tb:
            result["townland"] = {
                "name": tb["name"],
                "name_irish": tb["name_irish"],
                "area_acres": tb["area_acres"],
                "barony": tb["barony"],
                "parish": tb["parish"],
            }

        # Get POIs in this townland
        poi_sql = "SELECT * FROM pois WHERE LOWER(townland) = LOWER(?)"
        poi_params = [townland]

        if era:
            era_ranges = {
                "norman":   (1177, 1350),
                "medieval": (1350, 1600),
                "famine":   (1845, 1852),
                "modern":   (1900, 2100),
            }
            if era.lower() in era_ranges:
                start, end = era_ranges[era.lower()]
                poi_sql += " AND (era_start IS NULL OR era_start <= ?) AND (era_end IS NULL OR era_end >= ?)"
                poi_params.extend([end, start])

        pois = conn.execute(poi_sql, poi_params).fetchall()
        result["pois"] = [dict(r) for r in pois]

        # Get persons born in this townland
        persons = conn.execute(
            """SELECT id, name, birth_year, death_year, birth_location,
                      notable_for, tier, confidence, category
               FROM persons
               WHERE LOWER(birth_location) LIKE LOWER(?)
               ORDER BY birth_year""",
            (f"%{townland}%",),
        ).fetchall()
        result["persons"] = [dict(r) for r in persons]

    conn.close()
    return result


def get_persons_with_coords():
    """Get all persons that have birth coordinates set."""
    conn = get_conn()
    rows = conn.execute(
        """SELECT id, name, birth_year, death_year, birth_location,
                  birth_lat, birth_lng, notable_for, tier, confidence
           FROM persons
           WHERE birth_lat IS NOT NULL AND birth_lng IS NOT NULL
           ORDER BY name"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
