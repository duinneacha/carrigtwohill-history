# Collector Health Report — 26 February 2026 (11:30pm run)

## Summary
- **Total articles now:** 206
- **New this run:** 6 (2 seeds + 4 from collectors)
- **Working collectors:** 5 of 31
- **Broken collectors:** 17 of 31
- **Nothing-new-but-functional:** 9 of 31

---

## What Produced Results (6 new)

| Collector | New | Notes |
|---|---|---|
| Seed database | 2 | 2 of 49 seeds were new |
| Wikipedia | 1 | Archived article 948 |
| Irish Archives Resource | 1 | From seed URL |
| HistoricGraves.com | 2 | From seed URLs (search still 404) |

---

## Broken Collectors — Needs Fixing

### Missing Dependencies (easy fix)
| Collector | Issue | Fix |
|---|---|---|
| **Google News RSS** | `feedparser` not installed | `pip install feedparser` |

### Missing API Keys (need registration)
| Collector | Issue | Fix |
|---|---|---|
| **Logainm** | 401 Unauthorized | Register for API key at logainm.ie |
| **Trove (Australia)** | 401 Unauthorized | Register at trove.nla.gov.au for free key |
| **CORE** | No API key set | Register at core.ac.uk |
| **DRI** | No DRI_API_KEY | Register at repository.dri.ie |

### URL/API Changes (code needs updating)
| Collector | Issue | Details |
|---|---|---|
| **CELT (UCC)** | 404 on all search URLs | `/Search/Results` endpoint gone — UCC restructured |
| **Chronicling America** | 404 on all queries | Library of Congress changed URL structure — redirects to www.loc.gov |
| **National Monuments** | WFS parse error | Response not valid JSON — API format changed |
| **Irish Archives Resource** | 404 on seed URL | `/article/midleton-poor-law-union/` no longer exists |
| **National Famine (UCC)** | 404 | `/en/news/2018/the-famine-in-cork.html` moved |
| **HistoricGraves search** | 404 on all searches | Domain changed `.ie` → `.com`, search API changed |
| **NLI Catalogue** | 403 Forbidden on all searches | API endpoint blocked — may need different approach |
| **HathiTrust search** | 403 Forbidden on all searches | Blocking automated requests |
| **Ask About Ireland** | 403 on Griffith's page | Blocking automated access |

### Remote Server Errors (their problem, not ours)
| Collector | Issue |
|---|---|
| **Dúchas** | 500 Internal Server Error |
| **Buildings of Ireland** | 500 Internal Server Error |
| **IrelandXO** | 500 Internal Server Error on both endpoints |
| **IrishGraveyards.ie** | 500 on all three search queries |

---

## Collectors Returning 0 But Not Broken

These ran without errors but found nothing new (everything already in DB):

- Internet Archive
- OpenLibrary
- IrishGenealogy.ie
- Europeana
- OpenAlex
- British History Online
- Carrigtwohill Historical Society
- Carrigtwohill Community Council
- Workhouses.org.uk
- Cork City & County Archives
- IGP Free Irish Genealogy
- Find A Grave
- Skibbereen Heritage Centre

---

## Priority Fixes for Tomorrow

### Quick Wins (high impact, low effort)
1. **Install feedparser** — `pip install feedparser` — unlocks Google News RSS
2. **Fix Chronicling America URLs** — Library of Congress URL change is documented
3. **Fix HistoricGraves search domain** — change `.ie` to `.com` in search URLs
4. **Register for Trove API key** — free, opens up Irish-Australian newspaper archive

### Medium Effort
5. **Fix CELT search** — need to find new search endpoint on celt.ucc.ie
6. **Fix NLI Catalogue** — try HTML scraping fallback instead of blocked API
7. **Fix National Monuments WFS** — check current API format at archaeology.ie

### Also Notable
- The Tithe Applotment Books seed URL is still the old dead PDF reel link in `collect.py` SEED_ARTICLES — the DB was fixed but the seed code wasn't
- The collector is still trying old `historicgraves.ie` and `iar.ie` URLs in the seed list

---

## Database URL Fixes Already Applied This Session

| ID | Article | Old URL | New URL |
|---|---|---|---|
| 4 | Tithe Applotment Books | titheapplotmentbooks...reels/tab/...pdf | .../pagestab/Cork/Carrigtohill/ |
| 15 | Midleton Board of Guardians | nationalarchives.ie/article/midleton-poor-law-union/ | .../guide-to-poor-law-records/ |
| 393 | Midleton Board of Guardians (IAR) | iar.ie/archive/midleton-board-guardians/ | .../guide-to-poor-law-records/#midleton |
| 853 | Templecurraheen Graveyard | historicgraves.ie/graveyard/templecurraheen | historicgraves.com/... |
| 854 | Carrigtwohill Abbey Graveyard | historicgraves.ie/graveyard/carrigtwohill-abbey | historicgraves.com/... |

---

## Reminder: Upload Updated DB

After the URL fixes, the local `carrigtwohill.db` has the corrected links but this hasn't been uploaded to PythonAnywhere yet. Upload to `/home/duinneacha/carrigtwohill/data/` and reload.

---

*Report generated end of session, 26 Feb 2026*
