"""
Carrigtwohill Research Repository - Database Layer
SQLite + FTS5 full-text search engine

v1.0 — Articles, collection log, FTS for articles
v2.0 — Notable Persons system: extended persons table, person_sources,
        confidence_audit, families, persons_fts
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
    conn.commit()
    conn.close()
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    print("✓ Database initialised")


# ─────────────────────────────────────────────────────────────────────────────
# Write
# ─────────────────────────────────────────────────────────────────────────────

def insert_article(data: dict) -> tuple:
    """
    Insert an article. Returns (is_new: bool, row_id: int).
    Silently ignores duplicates (same URL).
    """
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

def search(query="", category=None, source_type=None, source=None, page=1, per_page=20):
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

        count_sql = f"SELECT COUNT(*) FROM ({base}{filters})"
        total = conn.execute(count_sql, params).fetchone()[0]

        order = " ORDER BY a.date_found DESC" if join else " ORDER BY date_found DESC"
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
