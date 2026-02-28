# Carrigtwohill Research System — Next Phase: Notable Persons
## Context Notes for Next Session
*Written end of session, February 2026*

---

## Background & Motivation

The St. Patrick's Day parade in Carrigtwohill prompted a discussion about finding **living or historically notable people whose roots can be traced back to Carrigtwohill**. The concept: "you might be from Carrigtwohill and not even know it." This is intended as a slow, careful genealogical matching pipeline — not a quick search tool.

The `persons` table already exists in `carrigtwohill.db` but has **0 entries**. Populating it is the primary goal of this phase.

---

## persons Table Schema (already in DB)

```sql
CREATE TABLE IF NOT EXISTS persons (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    birth_year  TEXT    DEFAULT '',
    death_year  TEXT    DEFAULT '',
    connection  TEXT    DEFAULT '',   -- how they connect to Carrigtwohill
    bio         TEXT    DEFAULT '',
    sources     TEXT    DEFAULT '[]', -- JSON array of source URLs
    added       TEXT    DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
);
```

Consider extending with fields: `confidence` (high/medium/low), `category` (historical/diaspora/living), `country_of_residence`, `emigration_year`, `emigration_destination`.

---

## Immediate Seeds — Add These First

These are verified, high-confidence persons with documented Carrigtwohill connections. They should be seeded into the `persons` table immediately as a starting point.

### 1. Garrett Standish Barry of Leamlara
- **Connection:** Born and lived in Leamlara, Carrigtwohill area, Barrymore barony
- **Born:** c.1790 | **Died:** 1864
- **Notable for:** First Catholic Member of Parliament elected for County Cork after the Catholic Emancipation Act of 1829. Served 1832–1841. Contemporary and associate of Daniel O'Connell.
- **Estate:** Leamlara, over 2,500 acres in Barrymore barony
- **Died without issue** — estate passed to brother Henry Standish
- **Primary sources:**
  - Carrigtwohill Historical Society website (already in DB)
  - John Burke, *A Genealogical and Heraldic History of Landed Gentry* (1834)
  - National Folklore Collection, Volume 0387 (Tithe War accounts)
  - Wikipedia article (already in DB, article id 72)
- **Confidence:** HIGH

### 2. The de Barry Family (medieval founders)
- **Connection:** Norman family who received Carrigtwohill lands from 1177. Founded the Franciscan Abbey c.1350. Barryscourt Castle is their seat.
- **Key individual:** Ellice Barry, birth recorded c.1423 at Barryscourt Castle (Ancestry member tree — treat as lead, not confirmed)
- **Notable for:** The de Barry family are the origin of the Barrymore barony name. Garrett Standish Barry above descends from this line.
- **Sources:** Wikipedia article on De Barry family (already in DB, article id 75), Barryscourt Castle (id 66)
- **Confidence:** HIGH for family connection, MEDIUM for specific individual dates from Ancestry trees

### 3. William 'The Harper' Fitzgerald
- **Connection:** Born 1720 at Woodstock, Carrigtwohill, Clonmult Parish
- **Notable for:** Married Lady Margaret Lawton, had six children — potential diaspora line
- **Source:** Ancestry public member tree (treat as lead requiring primary source verification)
- **Confidence:** MEDIUM — requires verification against Carrigtwohill parish registers

### 4. Bartholomew Hartnett & Honora (Norry) Kennedy
- **Connection:** Married in Carrigtwohill 21 February 1811
- **Notable for:** Best-documented emigration template from Carrigtwohill. Children:
  - Patrick (baptised 30 Jan 1820)
  - Joseph (baptised 5 May 1823)
  - Bartholomew (baptised 8 Sep 1828)
  - Maurice (baptised 24 Jul 1832)
- **Migration path:** A Joseph F. Hartnett married in Limerick in 1851 — likely Joseph baptised 1823 — showing internal migration before potential overseas emigration
- **Source:** SYNGENEIA genealogical database (sourced directly from NLI Carrigtwohill parish register images)
- **Confidence:** HIGH for Carrigtwohill origin, MEDIUM for Limerick connection

---

## New Data Sources Identified (add to collectors)

### registers.nli.ie — CRITICAL, not yet in system
The National Library of Ireland's **dedicated parish register viewer** — separate from the main catalogue. This is the single most important new source identified.

**Carrigtwohill RC Parish Records available:**
| Record Type | Date Coverage | Repository |
|---|---|---|
| Baptisms | 2 Dec 1817 – 18 Jul 1873 | NLI (registers.nli.ie) |
| Baptisms | 19 Jul 1873 – 5 Nov 1880 | NLI (registers.nli.ie) |
| Marriages | 22 Nov 1817 – 13 Oct 1878 | NLI (registers.nli.ie) |
| Baptisms & Marriages | 1817 – 1922 | Mallow Heritage Centre (physical copy) |

**Carrigtwohill Church of Ireland Records:**
| Record Type | Date Coverage | Repository |
|---|---|---|
| Baptisms | 1776–1844, 1863–1877 | Public Record Office Dublin / NLI manuscript copy |
| Marriages | 1779–1844 | Public Record Office Dublin / NLI manuscript copy |
| Burials | 1776–1863 | Public Record Office Dublin / NLI manuscript copy |
| Baptisms (Mogeasha) | 1852–1875 | Public Record Office Dublin |

**Note:** Church of Ireland records back to 1776 predate Catholic Emancipation — these are the Protestant family names in Carrigtwohill before the main Famine emigration waves. Important for tracing landlord-class and artisan Protestant families.

**Seed URL to add:** `https://registers.nli.ie/parishes/0449` (Carrigtwohill RC parish code — verify this code)
**Also add:** Mallow Heritage Centre as a physical archive contact for records not yet digitised.

### SYNGENEIA Database
- A sourced genealogical database with verified Carrigtwohill entries
- Has the Hartnett family fully documented with NLI register image citations
- URL: search for "SYNGENEIA genealogy Ireland" — not yet in system
- Add as a seed source and manual-review target

---

## The Three-Stage Pipeline Architecture

This was discussed and agreed across multiple AI responses. The program should run as a **slow, patient pipeline** — not a fast search tool.

### Stage 1 — Build the Carrigtwohill Name Pool
Extract every family name from Carrigtwohill records across a century of emigration:
- Griffith's Valuation 1851 (already seeded in system)
- Tithe Applotment Books 1823–37 (already seeded)
- 1901 and 1911 Census (already seeded)
- NLI parish registers 1776–1922 (NEW — registers.nli.ie)

Weight surnames by: frequency in records, time period (Famine era highest priority), townland specificity. Rarer surnames that are unique to the Carrigtwohill area are more diagnostic than Murphys and O'Briens.

### Stage 2 — Emigration Trace
Follow families from Carrigtwohill to their destinations. Key emigration waves:
1. **Famine period 1845–52** — heaviest emigration, many through Cobh (Queenstown)
2. **Post-Famine 1850s–60s** — continued chain migration, families following earlier emigrants
3. **Land League era 1870s–80s** — evictions from Smith-Barry estate triggered further emigration

**Key advantage specific to Carrigtwohill:** Almost the entire parish was within Smith-Barry estate ownership. Landlord-assisted emigration schemes in the 1840s–50s created paper trails — the estate sometimes paid passage, which was recorded. Smith-Barry estate papers are held at the NLI (already in system as a seed).

**Cobh Heritage Centre** — most Carrigtwohill emigrants left through Cobh (4 miles away). Cobh holds localised departure records not in general Ellis Island data. Add as a new source.

**Destination databases to query:**
- Boston Pilot Missing Persons Database (already seeded — Harvard Dataverse)
- Ellis Island / Statue of Liberty Foundation passenger records
- Trove (NLA Australia) — Irish-Australian diaspora (collector already in system, awaiting API key)
- Findmypast passenger manifests
- "British 1820 Settlers to South Africa" — flagged by DeepSeek, Eveleen Barry born Carrigtwohill c.1849 in this database (needs verification)

### Stage 3 — Notable Person Matching
Two approaches, both needed:

**Bottom-up:** Trace emigrant family lines forward through genealogy databases until a notable descendant appears.

**Top-down (faster when it works):** Take known Irish-American or Irish-diaspora notable figures who claim Cork/East Cork ancestry and trace backwards to Carrigtwohill. Best targets: Irish-American politicians (often have genealogy done publicly as part of their image), people who appeared on *Who Do You Think You Are?* or equivalent TV programmes, published family histories.

**Wikidata query approach:** Wikidata has structured birthplace and ancestry data. Query for notable people with: nationality=Irish-American AND ancestry=County Cork. This returns a tractable list for follow-up.

---

## Key Technical Elements Required

From synthesis of our discussion plus ChatGPT and DeepSeek comparisons:

1. **Surname extractor** — reads existing archived content and parish register data, builds weighted frequency table of Carrigtwohill family names by era

2. **GEDCOM export** — the persons table and family tree data should be exportable in GEDCOM format so it can talk to FamilySearch, Ancestry, and desktop genealogy tools. This is a standard format not currently in the system.

3. **Entity resolution engine** — the hardest problem. Must decide whether "Denis Dennehy, Carrigtoole, 1849" and "Daniel Dennehy, Carrigtwohill, 1851" are probably the same family. Requires:
   - Fuzzy name matching (Levenshtein distance or similar)
   - Date proximity scoring
   - Address/townland proximity
   - Family member cross-referencing
   - Irish name variant dictionaries (Honora/Norry/Honor, Denis/Daniel, etc.)

4. **Graph layer for family trees** — relational DB handles records but family trees are a graph problem. Even a lightweight in-memory `networkx` graph works for traversal. Parent/child/spouse as edges, persons as nodes. The "shortest path" between a Carrigtwohill ancestor and a notable descendant is literally a graph pathfinding problem.

5. **Migration tracker** — follows a family node across geography. Carrigtwohill → Cork → Cobh → Boston/Melbourne/Liverpool. Each step needs a source citation.

6. **Confidence scorer** — every claimed connection graded high/medium/low. Factors: primary source vs. Ancestry tree, number of confirming records, specificity of townland, number of generational gaps without evidence.

7. **Human review dashboard** — genealogy always needs manual checks before publishing. A simple Flask page listing "proposed connections awaiting review" with evidence links is enough for v1.

8. **Ethical output rules** — living people: no publication without consent, confidence must be high, privacy flags. Historical persons (pre-1923): publish freely with source citations. Always state "probable" vs "confirmed" links clearly.

---

## What Already Exists in the System (Don't Rebuild)

- `persons` table in carrigtwohill.db — just needs populating
- Flask web interface with article detail pages — persons page can follow same pattern
- Article seed infrastructure — persons seed function modelled on `seed_database()` in collect.py
- 174 articles already collected, many containing family name data
- OpenAlex collector returning academic papers on Irish famine/genealogy
- Dúchas oral history entries (Famine accounts from Carrigtwohill families)
- Wikipedia articles on Barry family, De Barry family, Garrett Standish Barry, Barryscourt Castle

---

## Suggested v1 Scope for Next Session

Keep it achievable. Do not try to build the full pipeline. v1 should:

1. **Seed the persons table** with the 4 verified entries above (Garrett Standish Barry, de Barry family, William Fitzgerald, Hartnett family)
2. **Add registers.nli.ie as a new seed source** in collect.py SEED_ARTICLES
3. **Add a persons page** to the Flask web interface (list view + detail view, same pattern as articles)
4. **Add a simple persons seeder** function in collect.py — modelled on `seed_database()`
5. **Add SYNGENEIA** as a manual-review seed source

Full pipeline (surname extraction, entity resolution, graph traversal, GEDCOM export) is v2+.

---

## Open Questions for Next Session

- What is the correct parish code on registers.nli.ie for Carrigtwohill? (search: "Carrigtwohill" on registers.nli.ie)
- Does the Carrigtwohill Historical Society website have a dedicated persons/families section that could be scraped?
- Is the Mallow Heritage Centre accessible via an online catalogue for their 1817–1922 copies?
- The "Eveleen Barry born Carrigtwohill c.1849, British 1820 Settlers South Africa" entry from DeepSeek — needs verification. If real, this is a concrete emigration record.
- Cobh Heritage Centre — do they have an online searchable database of departure records?

---

## Files Modified in This Session (for reference)

- `collect.py` — CELT collector rewritten, IrishGenealogy updated, AskAboutIreland updated, SEED_ARTICLES IrishGenealogy URL updated
- `new_collectors.py` — HathiTrust rewritten with known records seeds, HistoricGraves updated to new domain, IrishArchivesResource updated with NAI replacement URL, ChroniclingAmerica hardened, NLICatalogueCollector updated with HTML fallback and seed
- `carrigtwohill.db` — article id 2 (IrishGenealogy) and id 15 (IAR) URLs updated in-place
- `requirements.txt` — feedparser installed and verified (v6.0.12)

---

*End of session notes — next session should start by reading this file.*
