"""
Carrigtwohill Research Repository – Web Interface (Flask)
Run with:  python app.py
Then open: http://localhost:5050
"""

import os
import sys
import json
import threading
from pathlib import Path
from datetime import datetime, timedelta

from flask import (Flask, render_template, request, jsonify,
                   redirect, url_for, Response, send_file)

# allow running from any working directory
sys.path.insert(0, str(Path(__file__).parent))
import db
import collect as clt

# ── APScheduler for automatic background collection ──────────────────────────
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    HAS_SCHEDULER = True
except ImportError:
    HAS_SCHEDULER = False

app = Flask(__name__, template_folder="templates")
app.secret_key = "carrigtwohill-research-key"


@app.template_filter("fmt_date")
def fmt_date(value):
    """Format date_pub to 'DD Mon YYYY' or just 'YYYY' for year-only values."""
    if not value:
        return ""
    s = value.strip()
    # Year-only: '1989', '2024'
    if len(s) <= 4 and s.isdigit():
        return s
    # Try RFC 2822: 'Thu, 26 Feb 2026 00:27:05 GMT'
    from email.utils import parsedate_to_datetime
    try:
        dt = parsedate_to_datetime(s)
        return dt.strftime("%d %b %Y").lstrip("0")
    except Exception:
        pass
    # Try ISO 8601: '1999-01-01T00:00:00Z'
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%d %b %Y").lstrip("0")
        except ValueError:
            continue
    # Fallback: return raw value
    return s


# ─────────────────────────────────────────────────────────────────────────────
# Startup
# ─────────────────────────────────────────────────────────────────────────────

@app.before_request
def startup():
    db.init_db()
    # Seed notable persons on first run
    try:
        from persons.seed_data import seed_persons_table
        seeded, existed = seed_persons_table(db)
        if seeded > 0:
            print(f"  ↳ Seeded {seeded} notable persons ({existed} already existed)")
    except Exception as e:
        print(f"  ↳ Persons seeding skipped: {e}")
    app.before_request_funcs[None].remove(startup)


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    query      = request.args.get("q", "").strip()
    category   = request.args.get("cat", "all")
    src_type   = request.args.get("type", "all")
    src_filter = request.args.get("src", "").strip()
    page       = max(1, int(request.args.get("page", 1)))
    per_page   = 20

    articles, total = db.search(
        query=query,
        category=category if category != "all" else None,
        source_type=src_type if src_type != "all" else None,
        source=src_filter if src_filter else None,
        page=page,
        per_page=per_page,
    )
    total_pages = max(1, (total + per_page - 1) // per_page)
    stats       = db.get_stats()

    # unique filter options
    conn  = db.get_conn()
    cats  = [r[0] for r in conn.execute("SELECT DISTINCT category FROM articles ORDER BY category").fetchall() if r[0]]
    types = [r[0] for r in conn.execute("SELECT DISTINCT source_type FROM articles ORDER BY source_type").fetchall() if r[0]]
    conn.close()

    return render_template(
        "index.html",
        articles=articles,
        total=total,
        page=page,
        total_pages=total_pages,
        query=query,
        category=category,
        src_type=src_type,
        categories=cats,
        source_types=types,
        stats=stats,
        per_page=per_page,
    )


@app.route("/article/<int:aid>")
def article_detail(aid):
    article = db.get_article(aid)
    if not article:
        return redirect(url_for("index"))
    # parse tags from JSON string to list
    try:
        article["tags"] = json.loads(article["tags"]) if article.get("tags") else []
    except Exception:
        article["tags"] = []
    # load archived text if available (skip raw PDF binary)
    archived_text = ""
    if article.get("archived"):
        try:
            raw = Path(article["archived"]).read_bytes()[:200]
            if raw.lstrip().startswith(b"%PDF"):
                archived_text = ""  # PDF binary — not displayable as text
            else:
                archived_text = raw.decode("utf-8", errors="replace") + \
                    Path(article["archived"]).read_text(encoding="utf-8", errors="replace")[200:30000]
        except Exception:
            pass
    return render_template("article.html", article=article, archived_text=archived_text)


@app.route("/stats")
def stats_page():
    return jsonify(db.get_stats())


@app.route("/export/csv")
def export_csv():
    csv_data = db.export_csv()
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": 'attachment; filename="carrigtwohill_articles.csv"'},
    )


@app.route("/api/collect", methods=["POST"])
def trigger_collect():
    """Run the collector in a background thread so the UI doesn't hang."""
    def run():
        clt.run_all(verbose=False)
    t = threading.Thread(target=run, daemon=True)
    t.start()
    return jsonify({"status": "started", "message": "Collection running in background."})


@app.route("/api/search")
def api_search():
    """JSON search endpoint for AJAX calls."""
    q      = request.args.get("q", "")
    cat    = request.args.get("cat", None)
    stype  = request.args.get("type", None)
    page   = int(request.args.get("page", 1))
    rows, total = db.search(query=q, category=cat, source_type=stype, page=page)
    return jsonify({"results": rows, "total": total})


@app.route("/api/article/<int:aid>")
def api_article(aid):
    a = db.get_article(aid)
    return jsonify(a) if a else (jsonify({"error": "not found"}), 404)


# ─────────────────────────────────────────────────────────────────────────────
# Notable Persons Routes
# ─────────────────────────────────────────────────────────────────────────────

TIER_LABELS = {1: "Internationally Notable", 2: "Nationally Notable", 3: "Regionally Notable"}
CONFIDENCE_COLOURS = {"high": "#2a7a4e", "medium": "#c8941a", "low": "#a0522d"}

@app.route("/persons")
def persons_list():
    """Browse and search notable persons connected to Carrigtwohill."""
    query      = request.args.get("q", "").strip()
    tier       = request.args.get("tier", None)
    confidence = request.args.get("confidence", None)
    category   = request.args.get("category", "all")
    page       = max(1, int(request.args.get("page", 1)))
    per_page   = 20

    persons, total = db.search_persons(
        query=query,
        tier=tier,
        confidence=confidence if confidence != "all" else None,
        category=category if category != "all" else None,
        page=page,
        per_page=per_page,
    )

    # Parse sources JSON for each person
    for p in persons:
        try:
            p["sources_list"] = json.loads(p.get("sources", "[]")) if p.get("sources") else []
        except (json.JSONDecodeError, TypeError):
            p["sources_list"] = []

    total_pages = max(1, (total + per_page - 1) // per_page)
    stats = db.get_persons_stats()

    return render_template(
        "persons.html",
        persons=persons,
        total=total,
        page=page,
        total_pages=total_pages,
        query=query,
        tier_filter=tier,
        confidence_filter=confidence,
        category_filter=category,
        stats=stats,
        tier_labels=TIER_LABELS,
        confidence_colours=CONFIDENCE_COLOURS,
    )


@app.route("/person/<int:pid>")
def person_detail(pid):
    """Detail page for a single notable person."""
    person = db.get_person(pid)
    if not person:
        return redirect(url_for("persons_list"))

    # Parse sources JSON
    try:
        person["sources_list"] = json.loads(person.get("sources", "[]")) if person.get("sources") else []
    except (json.JSONDecodeError, TypeError):
        person["sources_list"] = []

    # Get linked articles from person_sources bridge table
    linked_articles = db.get_person_sources(pid)

    # Get confidence audit history
    audit_history = db.get_confidence_history(pid)

    return render_template(
        "person_detail.html",
        person=person,
        linked_articles=linked_articles,
        audit_history=audit_history,
        tier_labels=TIER_LABELS,
        confidence_colours=CONFIDENCE_COLOURS,
    )


@app.route("/api/persons")
def api_persons():
    """JSON endpoint for persons search."""
    q    = request.args.get("q", "")
    tier = request.args.get("tier", None)
    conf = request.args.get("confidence", None)
    cat  = request.args.get("category", None)
    page = int(request.args.get("page", 1))
    rows, total = db.search_persons(query=q, tier=tier, confidence=conf,
                                     category=cat, page=page)
    return jsonify({"results": rows, "total": total})


@app.route("/api/person/<int:pid>")
def api_person(pid):
    """JSON detail for a single person."""
    p = db.get_person(pid)
    return jsonify(p) if p else (jsonify({"error": "not found"}), 404)


# ─────────────────────────────────────────────────────────────────────────────
# Interactive Historical Map Routes
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/map")
def map_page():
    """Interactive historical map of Carrigtwohill parish."""
    return render_template("map.html")


@app.route("/api/map/townlands")
def api_map_townlands():
    """GeoJSON FeatureCollection of townland boundaries."""
    return jsonify(db.get_townlands_geojson())


@app.route("/api/map/pois")
def api_map_pois():
    """GeoJSON FeatureCollection of points of interest, optionally filtered."""
    poi_type = request.args.get("type", None)
    era = request.args.get("era", None)
    return jsonify(db.get_pois(poi_type=poi_type, era=era))


@app.route("/api/map/poi/<int:pid>")
def api_map_poi(pid):
    """Single POI detail with linked articles and persons."""
    poi = db.get_poi(pid)
    return jsonify(poi) if poi else (jsonify({"error": "not found"}), 404)


@app.route("/api/map/whatwashere")
def api_map_whatwashere():
    """Townland info + POIs + persons for a clicked location."""
    townland = request.args.get("townland", "")
    era = request.args.get("era", None)
    return jsonify(db.get_whatwashere(townland=townland, era=era))


# ─────────────────────────────────────────────────────────────────────────────
# Scheduler
# ─────────────────────────────────────────────────────────────────────────────

def start_scheduler():
    if not HAS_SCHEDULER:
        return
    scheduler = BackgroundScheduler()
    # Run collection every 24 hours
    scheduler.add_job(
        lambda: clt.run_all(verbose=False),
        trigger="interval",
        hours=24,
        next_run_time=datetime.now() + timedelta(seconds=30),   # first run 30s after start
        id="auto_collect",
    )
    scheduler.start()
    print("⏰ Scheduler started — collection runs every 24 hours")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    db.init_db()
    start_scheduler()
    print("━" * 60)
    print("  🏰 Carrigtwohill Historical Research Repository")
    print("  🌐 Open your browser at: http://localhost:5050")
    print("━" * 60)
    app.run(host="0.0.0.0", port=5050, debug=False, use_reloader=False)
