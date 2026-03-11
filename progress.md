# Carrigtwohill Interactive Historical Map — Implementation Progress

**Last updated:** 2026-03-02 (end of session 6)

---

## Status Summary

**Phase 1 (MVP Map) is COMPLETE.** All code is written, all routes verified, POIs seeded with verified OSM coordinates, and the map is ready to use at `/map`.

---

## What's Done

### Session 1 (2026-02-28)

#### 1. db.py — MAP_SCHEMA + query functions (COMPLETE)
- 4 new tables: `locations`, `pois`, `poi_links`, `townland_boundaries`
- Migration: `_migrate_map_tables()` adds geo columns to `persons`
- 4 write functions: `insert_poi`, `insert_location`, `insert_townland_boundary`, `link_poi`
- 5 read functions: `get_townlands_geojson`, `get_pois`, `get_poi`, `get_whatwashere`, `get_persons_with_coords`

#### 2. Townland research — all 38 townlands identified

### Session 2 (2026-03-01)

#### 3. Nav updated in all 4 templates (COMPLETE)
Added `<a href="/map">Historical Map</a>` to:
- `templates/index.html`
- `templates/persons.html`
- `templates/person_detail.html`
- `templates/article.html`

#### 4. confidence.py townlands expanded (COMPLETE)
Expanded `carrigtwohill_townlands` from 11 to 41 entries (38 townlands + spelling variants).

#### 5. Map routes added to app.py (COMPLETE)
5 new routes:
- `GET /map` — renders map.html
- `GET /api/map/townlands` — GeoJSON townland boundaries
- `GET /api/map/pois` — GeoJSON POIs (filterable by type, era)
- `GET /api/map/poi/<id>` — single POI detail with linked entities
- `GET /api/map/whatwashere` — townland + POIs + persons for a location

#### 6. templates/map.html (COMPLETE)
Standalone Leaflet map page with:
- CDN includes: Leaflet 1.9.4, MarkerCluster, GestureHandling, Turf.js
- Header/nav matching existing UI (green gradient, gold border)
- Map + sidebar layout
- Era filter controls, layer toggles, "What Was Here?" button

#### 7. static/css/map.css (COMPLETE)
- Map fills `calc(100vh - 120px)`
- Sidebar + map side-by-side on desktop, stacked on mobile
- 44px touch targets
- Leaflet popup and tooltip overrides
- Uses existing CSS variable palette

#### 8. static/js/map.js (COMPLETE)
- OSM base layer
- Townland GeoJSON overlay (green fill 8%, gold dashed border)
- NLS 6-inch historic map overlay with opacity slider
- Clustered POI markers with emoji icons per type
- Click popups with links to /person/ and /article/
- "What Was Here?" mode using Turf.js point-in-polygon
- Era filter buttons (All, Norman, Medieval, Tudor, Famine, Modern)
- Layer toggles (Townlands, POIs, Historic Map)
- Sidebar population on click
- Static fallback for townland data

#### 9. geo/ data scripts (COMPLETE)
- `geo/seed_pois.py` — Seeds 7 POIs with verified OSM coordinates
- `geo/geocode_persons.py` — Matches person birth_location against DB
- `geo/prepare_townlands.py` — Downloads/filters Cork GeoJSON from townlands.ie

#### 10. static/data/townlands.geojson (COMPLETE)
39 real townland boundaries from OSM Overpass API (Carrigtohill civil parish, relation 6514363).

### Session 3 (2026-03-01)

#### 11. Data accuracy audit & fixes (COMPLETE)
- Replaced 12 placeholder townland polygons with 39 real boundaries from OSM Overpass API
- Cross-checked all 7 POI coordinates against OSM — found 5 were 363m–1225m off
- Corrected all POI coordinates in `seed_pois.py` using verified OSM data
- Fixed Fota House townland assignment (was "Barryscourt", corrected to "Foaty")
- Re-seeded database with corrected coordinates
- Updated map center from [51.9089, -8.2534] to [51.9101, -8.2612] (village centroid)
- Replaced broken NLS Scotland-only tile layer with Esri satellite + GeoHive 25-inch Irish historic tiles
- Added `crossOrigin: 'anonymous'` to tile layers to fix OpaqueResponseBlocking warnings

### Session 4 (2026-03-01 continued)

#### 12. API key configuration (COMPLETE)
- Added `GAOIS_API_KEY` to `.env` for Logainm and Dúchas APIs
- Added `CORE_API_KEY` to `.env` for CORE open research API
- Verified `.env` is in `.gitignore` (confirmed safe)
- Added `.env` loader to `collect.py` (was only in `new_collectors.py`)

#### 13. Collector bug fixes (COMPLETE)
- **Logainm API (collect.py)**: Fixed URL from `/api/v1.0/search` to `/api/v1.0/`,
  fixed query param from `query` to `Query`, increased timeout to 30s,
  rewrote response parser for actual v1.0 JSON structure (placenames array with language/wording fields).
  Now returns 200 and collects 4 placename records.
- **CORE API (new_collectors.py)**: Fixed `KEY = ""` hardcoded to `KEY = os.environ.get("CORE_API_KEY", "")`.
  Fixed author parsing crash ("expected str instance, dict found") — authors are dicts with `name` field,
  not plain strings.
- **Dúchas API (collect.py)**: Added `apiKey` query parameter to API calls,
  added skip-with-warning when key is missing. (Dúchas server currently returning 500 — their issue.)
- **feedparser**: Installed `feedparser-6.0.12` (was already in requirements.txt).

#### 14. Collector run results (COMPLETE)
Latest run: 30 new articles (343 total in repository).
Working collectors: Wikipedia, Logainm, Google News RSS, OpenLibrary, Internet Archive,
  Europeana, OpenAlex, British History Online, Carrigtwohill Historical Society,
  Carrigtwohill Community Council, Workhouses.org.uk, Cork Archives, IGP, Find A Grave.

---

## Verification Results (all passing)

```
Python syntax:     6/6 files compile OK
GeoJSON:           39 real features in townlands.geojson (OSM sourced)
DB init:           OK
POI seeding:       7/7 POIs inserted (verified OSM coordinates)
POI queries:       get_pois() -> 7, era=medieval -> 3, era=modern -> 6
What Was Here:     Carrigtohill -> 5 POIs found
Townland bounds:   39 features in DB
Townland assign:   Fota House -> Foaty, Barryscourt Castle -> Barryscourt (correct)
Flask routes:      GET /map -> 200, all /api/map/* endpoints -> correct responses
Nav links:         "Historical Map" present in / and /persons
Confidence:        New townlands (Anngrove, Garrancloyne, etc.) score 1.0 specificity
```

---

## Collector Health (as of session 4)

| Collector | Status | Notes |
|-----------|--------|-------|
| Wikipedia | ✅ Working | |
| Internet Archive | ✅ Working | |
| OpenLibrary | ✅ Working | |
| Dúchas | ❌ Server 500 | Their server error, not our code |
| Logainm | ✅ Working | Fixed in session 4 |
| Google News RSS | ✅ Working | feedparser installed |
| CELT (UCC) | ❌ 404 | Endpoint URL has changed |
| IrishGenealogy.ie | ✅ Working | |
| NMS (archaeology.ie) | ⚠️ Parse error | WFS response empty |
| Buildings of Ireland | ❌ Server 500 | Their server error |
| Ask About Ireland | ❌ 403 | Blocking automated requests |
| HathiTrust | ❌ 403 | Blocking automated requests |
| Europeana | ✅ Working | |
| OpenAlex | ✅ Working | |
| Trove | ❌ 401 | No API key yet (awaiting approval) |
| Chronicling America | ❌ 404 | URL redirect changed |
| CORE | ❌ Server 500 | Was working in session 4; now returning 500 on all queries (their issue) |
| NLI Catalogue | ❌ 403 | API path likely wrong |
| British History Online | ✅ Working | |
| DRI | ⏸️ Skipped | No API key yet |
| Carrigtwohill Hist. Soc. | ✅ Working | |
| Community Council | ✅ Working | |
| Workhouses.org.uk | ✅ Working | |
| IrelandXO | ❌ Server 500 | Angular SSR bug (NG0210) on their end |
| Irish Archives Resource | ❌ 404 | Dead link |
| Cork City & County Archives | ✅ Working | |
| National Famine (UCC) | ❌ 404 | Dead link |
| HistoricGraves.com | ❌ 404 | Endpoint URL changed |
| IrishGraveyards.ie | ❌ Server 500 | Their server error |
| IGP Free Irish Genealogy | ✅ Working | |
| Find A Grave | ✅ Working | |

### Session 5 (2026-03-01)

#### 15. Link Health Checker & Status Labels (COMPLETE)

**Problem:** Many collected article URLs (especially CORE, DOI, academic repos) return 401/403 when clicked — users hit a wall with no warning.

**Solution:** Standalone link checker + UI status badges.

- **`db.py`**: Added `_migrate_articles_link_status()` migration — two new columns on `articles`:
  - `link_status TEXT DEFAULT 'unchecked'` (values: `unchecked`, `ok`, `access_restricted`, `unavailable`)
  - `link_checked_at TEXT DEFAULT ''` (ISO timestamp)
- **`check_links.py`** (new): Standalone script, run with `python check_links.py` (or `--all` to re-check).
  HEAD-first with GET fallback on 405, 3s per-domain rate limit, 15s timeout, 5s retry on 5xx.
  Classifies: 2xx=ok, 401/403=access_restricted, 404/410/timeout/DNS/5xx=unavailable.
  Prints per-URL progress and summary counts.
- **`templates/article.html`**: Status-aware source link on detail page:
  - `access_restricted`: amber "Own Access Required" button (still clickable) + explanatory note
  - `unavailable`: grey "Source Unavailable" label (not clickable) + note + URL shown as text
  - `ok`/`unchecked`: unchanged green "View Original Source" button
- **`templates/index.html`**: Badge pills on article cards:
  - `access_restricted`: amber "Own Access Required" pill
  - `unavailable`: grey "Source Unavailable" pill
- **No `app.py` changes needed** — `SELECT *` already returns `link_status` in both routes.

**First run results (400 articles):**
```
OK: 270  |  Own Access Required: 27  |  Unavailable: 103
```

Access-restricted: mostly DOI/journal articles and Cork Historical Society (paywalled/institutional).
Unavailable: includes archaeology.ie fragment URLs, restructured sites, dead links.

### Session 6 (2026-03-02)

#### 16. URL Domain Blocklist & Purge (COMPLETE)

**Problem:** 36 death-notice articles from RIP.ie were collected via Google News RSS redirects (`news.google.com/rss/articles/...` → `rip.ie`). These aren't relevant to historical research.

**Solution:** Blocklist in `db.py` that filters at insert time + cleanup function for existing data.

- **`db.py`**: Added `BLOCKED_DOMAINS` set (7 domains: rip.ie, legacy.com, funeralnotices.ie, deathnotices.ie, familyannouncements.ie, tributes.com, everhere.ie)
- **`db.py`**: Added `_is_blocked(url, title)` helper — checks URL domain AND title text for patterns like `- RIP.ie` to catch Google News redirects
- **`db.py`**: Added guard at top of `insert_article()` — returns `(False, 0)` for blocked URLs/titles, same shape as a duplicate so no callers need changes
- **`db.py`**: Added `purge_blocked_articles()` — scans all articles, deletes DB rows matching blocklist, removes archived files from disk (with OSError handling for OneDrive locks)
- **`run.py`**: Added `--purge-blocked` CLI command — calls `db.purge_blocked_articles()`, prints summary, exits

**Purge results:** 36 RIP.ie death notices removed. Article count: 438 → 402.

#### 17. Ctrl+C Interrupt Responsiveness (COMPLETE)

**Problem:** Pressing Ctrl+C during collection had no effect — the program continued through retry loops, `time.sleep()` calls, and `except Exception` blocks for 30+ seconds before responding. On Windows, `time.sleep()` blocks for the full duration before Python checks for signals.

**Solution:** Three-part fix across `collect.py` and `new_collectors.py`:

1. **`_sleep()` function** (both files): Replaces all `time.sleep()` calls throughout both collector modules. Sleeps in 0.3s chunks, checking an `_interrupted` flag between each. Maximum delay before responding to Ctrl+C: **0.3 seconds**.
2. **SIGINT signal handler**: `run_all()` installs a signal handler (`_set_interrupted()`) that immediately sets `_interrupted = True` in both `collect.py` and `new_collectors.py` when Ctrl+C is pressed — works even during blocking network requests.
3. **`except KeyboardInterrupt: raise`**: Added before every `except Exception` block in both files (6 in `collect.py`, 5 in `new_collectors.py`) so the interrupt can never be accidentally swallowed.
4. **`run_all()` loop**: Checks `_interrupted` flag before each collector, breaks immediately on interrupt, prints summary of what was collected before stopping.

**Test results:**
- Flag already set → `_sleep()` raises immediately (0ms)
- Flag set mid-sleep → interrupts within 0.3s
- Normal sleep unaffected (0.50s for 0.5s sleep)

#### 18. Fix signal handler crash in APScheduler thread (COMPLETE)

**Problem:** `app.py` runs `collect.run_all()` via APScheduler in a background thread. The SIGINT signal handler added in item 17 crashed with `ValueError: signal only works in main thread of the main interpreter`.

**Fix:** Wrapped `signal.signal()` install/restore in `threading.current_thread() is threading.main_thread()` check. Signal handler is only installed for CLI use (`python run.py collect`); safely skipped when APScheduler calls `run_all()` from a background thread. The `_sleep()` chunking still provides interrupt responsiveness from CLI.

#### 19. Purge irrelevant zero-score articles (COMPLETE)

**Problem:** 158 articles had a relevance score of 0.0 — no mention of Carrigtwohill or related keywords at all. Mostly false-positive academic papers from CORE (90) and OpenAlex (59) on unrelated topics (retinal imaging, cystic fibrosis, plasminogen research, etc.), plus a few broad Wikipedia/Internet Archive results.

**Fix:** Deleted all 158 zero-score articles from the database and their archived files from disk. Article count: 402 → 244. All remaining articles now have a relevance score > 0 and display a score badge in the UI.

#### 20. Deploy folder updated (COMPLETE)

Refreshed `deploy/` folder with all current files for PythonAnywhere upload:
- Updated Python files: `app.py`, `db.py`, `collect.py`, `new_collectors.py`, `check_links.py`, `run.py`
- Added missing templates: `map.html`, `persons.html`, `person_detail.html`
- Added missing static assets: `static/js/map.js`, `static/css/map.css`, `static/data/townlands.geojson`
- Added missing module: `persons/__init__.py`, `confidence.py`, `seed_data.py`
- Fresh database copy (244 articles, no RIP.ie, no zero-score)
- Updated `requirements.txt` (was just `flask`, now has all 8 dependencies)

---

## What Could Come Next (Phase 2 — Future Work)

1. **More POIs** — Add archaeological sites from archaeology.ie, buildings from NIAH
2. **Person geocoding** — Run `geo/geocode_persons.py` after adding location entries
3. **POI-Article linking** — Connect POIs to existing articles via `link_poi()`
4. **Timeline slider** — Animated era filter showing changes over centuries
5. **Walking routes** — Heritage trail overlays
6. **Fix broken collector URLs** — CELT, Chronicling America, HistoricGraves, NLI Catalogue need updated endpoints

---

## Files Modified

| File | Change |
|------|--------|
| `db.py` | MAP_SCHEMA, _migrate_map_tables(), 9 new functions (session 1); _migrate_articles_link_status() (session 5); BLOCKED_DOMAINS, _is_blocked(), insert_article guard, purge_blocked_articles() (session 6) |
| `app.py` | 5 new map routes (session 2) |
| `persons/confidence.py` | Townlands list expanded 11 -> 41 entries (session 2) |
| `templates/index.html` | Nav link added (session 2); link status pills (session 5) |
| `templates/persons.html` | Nav link added (session 2) |
| `templates/person_detail.html` | Nav link added (session 2) |
| `templates/article.html` | Nav link added (session 2); link status badges (session 5) |
| `collect.py` | `.env` loader, Logainm URL/parser fix, Dúchas apiKey auth, timeout increase (session 4); _sleep(), SIGINT handler, KeyboardInterrupt re-raises, interrupt-aware run_all() (session 6) |
| `new_collectors.py` | CORE API key from env, author parsing fix (session 4); _sleep(), _check_interrupt(), KeyboardInterrupt re-raises (session 6) |
| `run.py` | Added `--purge-blocked` CLI command (session 6) |
| `.env` | Added GAOIS_API_KEY, CORE_API_KEY (session 4) |

## Files Created

| File | Status |
|------|--------|
| `templates/map.html` | Complete — Leaflet map page |
| `static/js/map.js` | Complete — Map logic |
| `static/css/map.css` | Complete — Map styles |
| `static/data/townlands.geojson` | Complete — 12 townland placeholder polygons |
| `geo/seed_pois.py` | Complete — Seeds 7 POIs |
| `geo/geocode_persons.py` | Complete — Person geocoding script |
| `geo/prepare_townlands.py` | Complete — Townland boundary pipeline |
| `check_links.py` | Complete — Link health checker script |
| `progress.md` | This file |
